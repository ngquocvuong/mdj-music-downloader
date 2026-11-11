import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import threading
import json
import sys
import shutil
import queue
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
import re
import shlex
import tempfile
import itertools
import signal
import urllib.parse
import time
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════
# DEBUG MODE - Set to True for debugging, False for production release
# ═══════════════════════════════════════════════════════════════════
DEBUG = False
DEBUG_LOG_FILE = "/tmp/mdj-music-downloader-debug.log"

def debug(msg, level="INFO"):
    """
    Comprehensive debug logging system.
    Only active when DEBUG = True.
    Logs to both console and file for persistence.
    """
    if DEBUG:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"[{timestamp}] [{level}] {msg}"

        # Console output
        print(log_msg)

        # File output for persistence
        try:
            with open(DEBUG_LOG_FILE, "a") as f:
                f.write(log_msg + "\n")
        except Exception as e:
            print(f"[DEBUG] Failed to write to log file: {e}")

# Initialize debug log
if DEBUG:
    # Clear previous log on startup
    try:
        with open(DEBUG_LOG_FILE, "w") as f:
            f.write(f"{'='*70}\n")
            f.write(f"MDJ Music Downloader Debug Log - Started: {datetime.now()}\n")
            f.write(f"{'='*70}\n\n")
    except:
        pass

# App version
APP_VERSION = "1.0.3"

# Running inside a Flatpak sandbox (e.g. installed from Flathub)? Flatpak creates this file.
# There, yt-dlp and ffmpeg are bundled in /app/bin and updated with the Flatpak itself,
# so the in-app yt-dlp updater is hidden (Flathub apps must not download and run code).
IS_FLATPAK = os.path.exists("/.flatpak-info")

# Per-user yt-dlp copy, used when the user can't (or doesn't want to) update the
# system-wide copy next to the app (e.g. a standard user on a shared computer).
USER_DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
    "mdj-music-downloader")
USER_YTDLP_PATH = os.path.join(USER_DATA_DIR, "yt-dlp")
YTDLP_DOWNLOAD_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux"


def parse_ytdlp_version(text):
    """'2026.10.26' -> (2026, 10, 26); '2026.10.26.1' -> (2026, 10, 26, 1); None if unparseable."""
    m = re.search(r"\d{4}\.\d{1,2}\.\d{1,2}(?:\.\d+)*", text or "")
    return tuple(int(x) for x in m.group(0).split(".")) if m else None


def get_ytdlp_version(path, timeout=30):
    """Run `path --version`. Returns (version_tuple, version_string) or (None, None) if it doesn't run."""
    try:
        if not (os.path.isfile(path) and os.access(path, os.X_OK)):
            return None, None
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return None, None
        out = r.stdout.strip()
        return parse_ytdlp_version(out), out
    except Exception:
        return None, None


def external_env():
    """Environment for launching *other* programs (file manager, browser).

    A PyInstaller build points LD_LIBRARY_PATH at its own bundled libraries; programs we
    launch would inherit that and can crash loading the wrong libraries. Restore the original."""
    env = dict(os.environ)
    if getattr(sys, "frozen", False):
        orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is not None:
            env["LD_LIBRARY_PATH"] = orig
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


def native_dialog_command(kind, title, initialdir, filetypes=None, parent_xid=None, initialfile=""):
    """Command line for the desktop's own file chooser (GTK via zenity, or KDE's kdialog).

    kind is "dir", "open" or "save". Returns None when neither program is installed,
    in which case the caller falls back to the built-in Tk dialog."""
    # In the Flatpak, zenity's dialog is drawn by the desktop's file chooser portal, so it is
    # the real system dialog. See portal_can_open_in_folder() for its start-folder limit.
    initialdir = initialdir if initialdir and os.path.isdir(initialdir) else os.path.expanduser("~")
    start = os.path.join(initialdir, initialfile) if initialfile else initialdir.rstrip("/") + "/"
    filetypes = filetypes or []
    if shutil.which("zenity"):
        cmd = ["zenity", "--file-selection", f"--title={title}", f"--filename={start}", "--modal"]
        if parent_xid:
            cmd.append(f"--attach={parent_xid}")
        if kind == "dir":
            cmd.append("--directory")
        elif kind == "save":
            cmd += ["--save", "--confirm-overwrite"]
        if kind != "dir":
            for name, pattern in filetypes:
                pattern = " ".join("*" if p == "*.*" else p for p in pattern.split())
                cmd.append(f"--file-filter={name} | {pattern}")
        return cmd
    if shutil.which("kdialog"):
        filt = "\n".join(f"{p} |{n}" for n, p in filetypes)
        cmd = ["kdialog", "--title", title]
        if parent_xid:
            cmd += ["--attach", str(parent_xid)]
        if kind == "dir":
            cmd += ["--getexistingdirectory", initialdir]
        elif kind == "open":
            cmd += ["--getopenfilename", initialdir] + ([filt] if filt else [])
        else:
            cmd += ["--getsavefilename", start] + ([filt] if filt else [])
        return cmd
    return None


# ---- Album folders: track numbers ("01.Title.mp3") and the .m3u playlist ----
MEDIA_EXTS = (".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac", ".alac",
              ".mp4", ".mkv", ".webm", ".mov")
# "01.Song", "7.Song", "120.Song". Not "99.9 FM" (a digit right after the dot).
_TRACK_RE = re.compile(r"^(\d{1,3})\.(?!\d)")


def is_media_file(name):
    return name.lower().endswith(MEDIA_EXTS) and not name.startswith(".")


def track_number_of(name):
    """Track number of a numbered media file name, else None."""
    m = _TRACK_RE.match(name)
    return int(m.group(1)) if m and is_media_file(name) else None


def strip_track_prefix(name):
    """"01.Song.mp3" / "1. Song.mp3" -> "Song.mp3". Names that would end up empty are kept."""
    rest = re.sub(r"^\d{1,3}\.(?!\d)\s*", "", name)
    return rest if os.path.splitext(rest)[0].strip() else name


def next_track_number(folder):
    """One more than the highest track number in folder (1 for none). Gaps are not refilled,
    so a new song never takes a number that belonged to another one."""
    try:
        numbers = [track_number_of(f) for f in os.listdir(folder)]
    except OSError:
        return 1
    return max([n for n in numbers if n is not None], default=0) + 1


def number_downloaded_file(path, existed_before):
    """Give a downloaded file the next track number in its folder.

    existed_before: the file was already there before this download (yt-dlp skipped it).
    Returns (final path, what happened): "numbered", "kept" (already numbered, or nothing
    to do) or "duplicate" (the album already has this title under a number; the new copy
    is removed, the way yt-dlp itself skips a title that is already in the folder)."""
    folder, name = os.path.split(path)
    if existed_before and track_number_of(name) is not None:
        return path, "kept"
    clean = strip_track_prefix(name)
    try:
        others = os.listdir(folder)
    except OSError:
        return path, "kept"
    for other in sorted(others):
        if other != name and track_number_of(other) is not None and strip_track_prefix(other) == clean:
            if existed_before:          # both were already there: leave the user's files alone
                return path, "kept"
            try:
                os.remove(path)
            except OSError:
                return path, "kept"
            return os.path.join(folder, other), "duplicate"
    n = next_track_number(folder)
    while True:
        target = os.path.join(folder, f"{n:02d}.{clean}")
        if not os.path.exists(target):  # rename() would silently replace an existing file
            break
        n += 1
    os.rename(path, target)
    return target, "numbered"


def write_album_playlist(folder):
    """(Re)write <folder name>.m3u: numbered tracks in number order, then the other songs
    by name. Returns its path, or None when the folder has no songs."""
    try:
        names = [f for f in os.listdir(folder)
                 if is_media_file(f) and os.path.isfile(os.path.join(folder, f))]
    except OSError:
        return None
    if not names:
        return None

    def natural(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

    def order(f):
        n = track_number_of(f)
        return (0, n, natural(f)) if n is not None else (1, 0, natural(f))

    names.sort(key=order)
    path = os.path.join(folder, os.path.basename(os.path.normpath(folder)) + ".m3u")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name in names:
            f.write(name + "\n")
    os.replace(tmp, path)
    return path


TRACKS_FILE = ".mdj-tracks.json"     # hidden, in each download folder
# Printed by yt-dlp for every file it saves: "MDJ<tab>Youtube<tab><video id><tab><final path>"
SAVED_PRINT = "after_move:MDJ\t%(extractor_key)s\t%(id)s\t%(filepath)s"


def load_track_map(folder):
    """{"youtube <id>": file name} of the videos already saved in folder.

    Entries whose file is gone (deleted or renamed by hand) are dropped, so those videos
    can be downloaded again."""
    try:
        with open(os.path.join(folder, TRACKS_FILE), encoding="utf-8") as f:
            tracks = json.load(f).get("tracks", {})
    except (OSError, ValueError, AttributeError):
        return {}
    if not isinstance(tracks, dict):
        return {}
    return {k: v for k, v in tracks.items()
            if isinstance(k, str) and isinstance(v, str) and "/" not in v
            and os.path.isfile(os.path.join(folder, v))}


def save_track_map(folder, tracks):
    path = os.path.join(folder, TRACKS_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "tracks": tracks}, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def parse_saved_lines(stdout):
    """[(archive key, path)] from yt-dlp's SAVED_PRINT lines, in order."""
    saved = []
    for line in stdout.splitlines():
        parts = line.rstrip("\r\n").split("\t", 3)
        if len(parts) == 4 and parts[0] == "MDJ" and parts[3]:
            saved.append((f"{parts[1].lower()} {parts[2]}", parts[3]))
    return saved


def safe_folder_name(name):
    """Album/Folder name usable as one folder: no "/" (would make sub-folders), no "." / ".."."""
    name = name.strip().replace("/", "-").replace("\0", "")
    return "" if name in (".", "..") else name


_portal_version = []


def portal_can_open_in_folder():
    """Can the system dialog's Open mode start in a given folder?

    Always outside Flatpak. Inside, the dialog comes from the file chooser portal, which
    only accepts a start folder for Open from version 4 (xdg-desktop-portal 1.18, e.g. Mint 22,
    Ubuntu 24.04). Older ones (Mint 21) always open the home folder. Save works on all."""
    if not IS_FLATPAK:
        return True
    if not _portal_version:
        version = 0
        try:
            out = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
                 "--object-path", "/org/freedesktop/portal/desktop", "--method",
                 "org.freedesktop.DBus.Properties.Get", "org.freedesktop.portal.FileChooser",
                 "version"], capture_output=True, text=True, timeout=3).stdout
            m = re.search(r"uint32 (\d+)", out)
            version = int(m.group(1)) if m else 0
        except Exception:
            pass
        _portal_version.append(version)
    return _portal_version[0] >= 4


_item_ids = itertools.count(1)


def new_queue_item(url):
    """A queue entry. 'id' identifies it for the download thread (positions change when
    items are removed or added during a download)."""
    return {'id': next(_item_ids), 'url': url, 'status': 'waiting', 'widget': None}


def url_key(url):
    """Key for duplicate detection: the same YouTube video counts once, whatever the link
    style (youtu.be / watch?v= / shorts / music.youtube) or share/tracking parameters."""
    try:
        u = urllib.parse.urlsplit(url.strip())
        host = u.netloc.lower().split("@")[-1].split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if host.startswith("m."):
            host = host[2:]
        vid = None
        if host == "youtu.be":
            vid = u.path.strip("/").split("/")[0]
        elif host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
            if u.path == "/watch":
                vid = urllib.parse.parse_qs(u.query).get("v", [None])[0]
            elif u.path.startswith(("/shorts/", "/embed/", "/live/")):
                vid = u.path.split("/")[2]
        if vid:
            return "youtube:" + vid
        query = "&".join(q for q in u.query.split("&") if q and not q.startswith(("si=", "utm_")))
        return f"{host}{u.path.rstrip('/')}?{query}"
    except Exception:
        return url.strip()


_monitor_cache = []


def xinerama_monitors():
    """Monitor rectangles [(x, y, width, height)] straight from the X server (libXinerama).

    Works without the xrandr program, which the Flatpak runtime doesn't include.
    Returns [] if the libraries or the display aren't available."""
    import ctypes
    try:
        x11 = ctypes.CDLL("libX11.so.6")
        xin = ctypes.CDLL("libXinerama.so.1")
    except OSError:
        return []

    class ScreenInfo(ctypes.Structure):
        _fields_ = [("screen_number", ctypes.c_int), ("x_org", ctypes.c_short),
                    ("y_org", ctypes.c_short), ("width", ctypes.c_short), ("height", ctypes.c_short)]

    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XFree.argtypes = [ctypes.c_void_p]
    xin.XineramaIsActive.argtypes = [ctypes.c_void_p]
    xin.XineramaQueryScreens.restype = ctypes.POINTER(ScreenInfo)
    xin.XineramaQueryScreens.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
    dpy = x11.XOpenDisplay(None)
    if not dpy:
        return []
    try:
        if not xin.XineramaIsActive(dpy):
            return []
        count = ctypes.c_int(0)
        screens = xin.XineramaQueryScreens(dpy, ctypes.byref(count))
        if not screens:
            return []
        result = [(screens[i].x_org, screens[i].y_org, screens[i].width, screens[i].height)
                  for i in range(count.value)]
        x11.XFree(screens)
        return result
    finally:
        x11.XCloseDisplay(dpy)


def monitor_at_pointer(widget):
    """(x, y, width, height) of the monitor under the mouse, or None (Xinerama, else xrandr)."""
    try:
        px, py = widget.winfo_pointerx(), widget.winfo_pointery()
        if not _monitor_cache:
            try:
                _monitor_cache.extend(xinerama_monitors())
            except Exception:
                pass
        if not _monitor_cache and shutil.which("xrandr"):
            out = subprocess.run(["xrandr", "--listmonitors"], capture_output=True,
                                 text=True, timeout=1, env=external_env()).stdout
            for m in re.finditer(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)", out):
                w, h, x, y = map(int, m.groups())
                _monitor_cache.append((x, y, w, h))
        for x, y, w, h in _monitor_cache:
            if x <= px < x + w and y <= py < y + h:
                return (x, y, w, h)
    except Exception:
        pass
    return None


_wheel_canvases = []      # canvases of CTkScrollableFrames that scroll with the mouse wheel
WHEEL_STEP = 5            # canvas units (8 px each in CustomTkinter on Linux) per wheel notch


def enable_wheel_scrolling(scroll_frame):
    """Make a CTkScrollableFrame scroll with the mouse wheel on Linux.

    CustomTkinter 5.2 only listens for <MouseWheel>, but Tk 8.6 on Linux (X11) reports the
    wheel as mouse buttons 4 (up) and 5 (down), so the wheel did nothing. One global handler
    scrolls whichever registered list is under the mouse pointer."""
    if not sys.platform.startswith("linux") or tk.TkVersion >= 8.7:
        return  # Tk 8.7+ sends <MouseWheel> on Linux too, which CustomTkinter already handles
    canvas = scroll_frame._parent_canvas
    if not _wheel_canvases:
        root = scroll_frame.winfo_toplevel()
        root.bind_all("<Button-4>", lambda e: _on_wheel(e, -1), add="+")
        root.bind_all("<Button-5>", lambda e: _on_wheel(e, 1), add="+")
    _wheel_canvases.append(canvas)


def _on_wheel(event, direction):
    try:
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
    except Exception:
        return
    path = str(widget) if widget is not None else ""
    for canvas in list(_wheel_canvases):
        try:
            if not canvas.winfo_exists():
                _wheel_canvases.remove(canvas)
                continue
        except Exception:
            continue
        cpath = str(canvas)
        if path == cpath or path.startswith(cpath + "."):
            if canvas.yview() != (0.0, 1.0):        # only when the list is longer than the view
                canvas.yview_scroll(direction * WHEEL_STEP, "units")
            return



# ---- yt-dlp option helpers (Settings window) ----
YTDLP_OPTIONS_URL = "https://github.com/yt-dlp/yt-dlp#usage-and-options"
YTDLP_FORMAT_URL = "https://github.com/yt-dlp/yt-dlp#format-selection"
DEFAULT_VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav"]
AUDIO_QUALITIES = [("Best (VBR 0)", "0"), ("High (~192 kbps)", "2"),
                   ("Medium (~128 kbps)", "5"), ("Low (~64 kbps)", "9")]
COOKIE_BROWSERS = ["firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi"]


def video_format_for(height):
    """yt-dlp -f string for "best quality up to <height>p" (None = no limit), MP4 preferred."""
    if not height:
        return DEFAULT_VIDEO_FORMAT
    h = f"[height<={height}]"
    return f"bestvideo{h}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{h}+bestaudio/best{h}/best"


VIDEO_PRESETS = [("Best available", video_format_for(None))] + [
    (label, video_format_for(h)) for label, h in
    (("Up to 4K (2160p)", 2160), ("Up to 1440p", 1440), ("Up to 1080p", 1080),
     ("Up to 720p", 720), ("Up to 480p", 480))]
VIDEO_CUSTOM_LABEL = "Custom (see Advanced tab)"


# Options that change a Basic-tab setting. Custom arguments come after the Basic options and
# yt-dlp uses the last value it reads, so when one of these is in Custom arguments, it wins.
# Value: whether the option takes a value.
BASIC_OVERRIDES = {
    "audio_format": {"--audio-format": True},
    "audio_quality": {"--audio-quality": True},
    "video_quality": {"-f": True, "--format": True},
    "embed_thumbnail": {"--embed-thumbnail": False, "--no-embed-thumbnail": False},
    "embed_metadata": {"--embed-metadata": False, "--add-metadata": False,
                       "--no-embed-metadata": False, "--no-add-metadata": False},
    "cookies_browser": {"--cookies-from-browser": True, "--no-cookies-from-browser": False},
}


def overridden_settings(args):
    """{basic setting: "the custom option that replaces it"} for an argument list."""
    found = {}
    for i, a in enumerate(args):
        name = a.split("=", 1)[0] if a.startswith("--") else a
        for key, names in BASIC_OVERRIDES.items():
            if name in names:
                takes_value = names[name] and "=" not in a and i + 1 < len(args)
                found[key] = f"{a} {args[i + 1]}" if takes_value else a
    return found


def effective_audio_format(cfg):
    """The audio format downloads really use: a custom --audio-format wins over the Basic one."""
    fmt = cfg.get("audio_format", "mp3")
    args = normalize_args(cfg.get("custom_args", []))
    for i, a in enumerate(args):
        if a.startswith("--audio-format="):
            fmt = a.split("=", 1)[1]
        elif a == "--audio-format" and i + 1 < len(args):
            fmt = args[i + 1]
    return fmt


def download_summary(cfg, is_audio):
    """Short text for under the Download Type switch, e.g. "MP3 · best quality".

    Uses the values downloads really use: custom arguments win over the Basic tab."""
    args = normalize_args(cfg.get("custom_args", []))

    def last(names):
        value = None
        for i, a in enumerate(args):
            name, eq, val = a.partition("=")
            if name in names:
                value = val if eq else (args[i + 1] if i + 1 < len(args) else None)
        return value

    over = overridden_settings(args)
    if is_audio:
        fmt = effective_audio_format(cfg)
        if fmt in ("flac", "wav", "alac"):
            detail = "lossless"
        elif "audio_quality" in over:
            detail = "quality " + (last({"--audio-quality"}) or "?")
        else:
            labels = {"0": "best quality", "2": "~192 kbps", "5": "~128 kbps", "9": "~64 kbps"}
            detail = labels.get(str(cfg.get("audio_quality", "0")), "quality " + str(cfg.get("audio_quality")))
    else:
        fmt = last({"--recode-video", "--remux-video", "--merge-output-format"}) or "mp4"
        if any(c in fmt for c in "/>"):
            fmt = "custom"                  # rules like "webm>mkv/mp4"
        code = cfg.get("video_quality", "") or DEFAULT_VIDEO_FORMAT
        if "video_quality" in over:
            detail = "custom format"
        else:
            detail = {c: lbl for lbl, c in VIDEO_PRESETS}.get(code.strip(), "custom format")
            detail = detail[0].lower() + detail[1:]     # "Up to 1080p" -> "up to 1080p"
    return f"{fmt.upper()} · {detail}"


def normalize_args(items):
    """Turn saved argument lists into proper argv items.

    Older versions saved each line as one item, so "--cookies-from-browser firefox" reached
    yt-dlp as a single argument (error: no such option). Split those like a shell would."""
    out = []
    for item in items or []:
        item = str(item)
        if item.startswith("-") and "=" not in item and any(c.isspace() for c in item.strip()):
            try:
                out.extend(shlex.split(item))
                continue
            except ValueError:
                pass
        out.append(item)
    return out


def parse_args_text(text):
    """Textbox text -> (args, error). One option per line, shell-style quoting.

    A word starting with # begins a comment ("--limit-rate 2M  # slower"); a # inside
    a word, as in a URL, is kept."""
    args = []
    for n, line in enumerate(text.splitlines(), 1):
        try:
            words = shlex.split(line)
        except ValueError:
            return None, f"Line {n}: a quote (\" or \') is not closed"
        for w in words:
            if w.startswith("#"):
                break
            args.append(w)
    return args, None


def args_to_text(args):
    """Argument list -> textbox text: each option on its own line with its values after it."""
    lines = []
    for a in normalize_args(args):
        if a.startswith("-") or not lines:
            lines.append([a])
        else:
            lines[-1].append(a)
    return "\n".join(shlex.join(parts) for parts in lines)


def centered_position(widget, width, height):
    """Top-left position that centres a width x height window on the mouse's monitor."""
    mon = monitor_at_pointer(widget)
    if mon:
        x, y, w, h = mon
        return x + (w - width) // 2, y + (h - height) // 2
    return ((widget.winfo_screenwidth() - width) // 2,
            (widget.winfo_screenheight() - height) // 2)


def open_with_system(target):
    """Open a folder or URL with the desktop's default app. Returns True if a launcher was started."""
    for cmd in (["xdg-open", target], ["gio", "open", target]):
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, env=external_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                return True
            except OSError:
                continue
    return False


def system_ytdlp_path():
    """yt-dlp shipped with the app (/opt/mdj-music-downloader/yt-dlp, or /app/bin/yt-dlp in the
    Flatpak), or None when running from source."""
    if IS_FLATPAK:
        return "/app/bin/yt-dlp"
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    return None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Brand colours, taken from the MDJ icon (teal headphones on navy)
ACCENT = "#2bb5a3"          # softer teal for primary buttons, switches, progress
                            # (the icon teal #35d6c1 is too bright for big areas)
ACCENT_HOVER = "#249484"    # darker teal on hover
ACCENT_TEXT = "#17243a"     # navy text on teal (white on teal is hard to read)
ACCENT_FG = "#35d6c1"       # brighter icon teal for small text on dark backgrounds
ACCENT_DIM = "#1f4d49"      # dark teal tint: hover for outline buttons
LIGHT_TEXT = "#DCE4EE"      # normal light text on dark/coloured buttons
SWITCH_TRACK = "#1b2023"    # Download Type switch: dark track / unselected half
SWITCH_HOVER = "#262d31"
LEFT_PANEL_WIDTH = 308            # left panel content width (see setup_ui)
TIP_BG = "#ffffe1"          # classic light-yellow tooltip
TIP_TEXT = "#1a1a1a"


def _apply_brand_theme():
    """Swap CustomTkinter's blue accent for the MDJ teal in the loaded theme."""
    blue = {"#3B8ED0", "#1F6AA5"}
    blue_hover = {"#36719F", "#144870"}
    theme = ctk.ThemeManager.theme
    for widget, opts in theme.items():
        if not isinstance(opts, dict):
            continue
        for key, val in opts.items():
            if isinstance(val, list) and len(val) == 2 and all(isinstance(v, str) for v in val):
                up = {v.upper() for v in val}
                if up <= blue:
                    opts[key] = [ACCENT, ACCENT]
                elif up <= blue_hover:
                    opts[key] = [ACCENT_HOVER, ACCENT_HOVER]
    theme["CTkButton"]["text_color"] = [ACCENT_TEXT, ACCENT_TEXT]
    theme["CTkSegmentedButton"]["text_color"] = [LIGHT_TEXT, LIGHT_TEXT]
    theme["CTkOptionMenu"]["text_color"] = [ACCENT_TEXT, ACCENT_TEXT]
    theme["CTkCheckBox"]["checkmark_color"] = [ACCENT_TEXT, ACCENT_TEXT]
    theme["CTkCheckBox"]["hover_color"] = [ACCENT_HOVER, ACCENT_HOVER]
    # Thin outlines everywhere (CustomTkinter's defaults are 2-3 px, which looked heavy)
    theme["CTkEntry"]["border_width"] = 1
    theme["CTkCheckBox"]["border_width"] = 2
    theme["CTkSegmentedButton"]["border_width"] = 1


_apply_brand_theme()


def _speed_up_ctk_scrollbars():
    """CustomTkinter's scrollbar forces a full redraw of the whole app (update_idletasks)
    every time it is drawn. Windows with scrollbars then took 1-2 s to open. Tk redraws
    by itself a moment later anyway, so skip that forced redraw."""
    original = ctk.CTkScrollbar._draw
    if getattr(original, "_mdj_fast", False):
        return

    def _draw(self, *args, **kwargs):
        canvas = getattr(self, "_canvas", None)
        if canvas is None:
            return original(self, *args, **kwargs)
        canvas.update_idletasks = lambda: None      # instance attribute hides the method
        try:
            return original(self, *args, **kwargs)
        finally:
            del canvas.update_idletasks
    _draw._mdj_fast = True
    ctk.CTkScrollbar._draw = _draw


_speed_up_ctk_scrollbars()


class RoundIconButton(ctk.CTkButton):
    """CTkButton that can be a true circle: CTk reserves corner_radius-wide side columns
    around the text, so a 20px "?" would otherwise become 28px wide (an oval)."""
    def _create_grid(self):
        super()._create_grid()
        for col in (0, 4):
            self.grid_columnconfigure(col, minsize=0)


class HoverTip:
    """Small tooltip shown while the mouse rests on a widget."""
    def __init__(self, widget, text, delay=400):
        self.widget, self.text, self.delay = widget, text, delay
        self._after = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        # Same sequence the button itself uses: Tk runs only the most specific binding, so a
        # generic "<ButtonPress>" would be skipped in favour of the button's "<Button-1>".
        widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        self._after = None
        if self._tip or not self.widget.winfo_exists():
            return
        import tkinter as _tk
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() - 2
        self._tip = tip = _tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        _tk.Label(tip, text=self.text, bg=TIP_BG, fg=TIP_TEXT, padx=6, pady=2,
                  font=("TkDefaultFont", 9), relief="solid", borderwidth=1).pack()

    def _hide(self, event=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None


class TooltipNotification:
    """Small pop-up message that fades out by itself.

    once: a key for routine confirmations (e.g. "paste"); a message with a key is shown only
    the first time per app session, so repeated clicks don't keep flashing pop-ups."""
    _current = None          # only one notification on screen at a time
    _shown_once = set()

    def __init__(self, parent, message, duration=2000, once=None):
        self.tooltip = None
        if once is not None:
            if once in TooltipNotification._shown_once:
                return
            TooltipNotification._shown_once.add(once)
        previous = TooltipNotification._current
        if previous is not None:
            previous._destroy()
        TooltipNotification._current = self

        self.tooltip = ctk.CTkToplevel(parent)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes('-topmost', True)

        self.label = ctk.CTkLabel(
            self.tooltip,
            text=message,
            fg_color=TIP_BG,
            text_color=TIP_TEXT,
            font=ctk.CTkFont(size=12),
            corner_radius=6,
            padx=10,
            pady=3
        )
        self.label.pack()

        # Position tooltip - center on parent window
        parent.update_idletasks()
        self.tooltip.update_idletasks()
        tooltip_width = self.tooltip.winfo_reqwidth()
        tooltip_height = self.tooltip.winfo_reqheight()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - tooltip_width) // 2
        y = parent_y + parent_height // 4
        self.tooltip.geometry(f"+{x}+{y}")

        # Fade in
        self.tooltip.attributes('-alpha', 0.0)
        self.tooltip.deiconify()
        self.fade_in()

        # Schedule fade out
        self.tooltip.after(duration, self.fade_out)

    def _destroy(self):
        try:
            if self.tooltip is not None and self.tooltip.winfo_exists():
                self.tooltip.destroy()
        except Exception:
            pass
        self.tooltip = None
        if TooltipNotification._current is self:
            TooltipNotification._current = None

    def fade_in(self, alpha=0.0):
        if self.tooltip is None:
            return
        if alpha < 0.95:
            alpha += 0.1
            self.tooltip.attributes('-alpha', alpha)
            self.tooltip.after(30, lambda: self.fade_in(alpha))

    def fade_out(self, alpha=0.95):
        if self.tooltip is None:
            return
        if alpha > 0:
            alpha -= 0.1
            self.tooltip.attributes('-alpha', alpha)
            self.tooltip.after(30, lambda: self.fade_out(alpha))
        else:
            self._destroy()


class MusicDownloader:
    def __init__(self, root):
        debug("__init__ started")
        self.root = root
        self.root.title("MDJ Music Downloader")
        debug("Title set")

        # Config file - save in user's home directory for multi-user support
        # Flatpak: the sandbox has its own config folder (~/.var/app/<app id>/config) in XDG_CONFIG_HOME
        config_home = (os.environ.get("XDG_CONFIG_HOME") if IS_FLATPAK else None) or \
            os.path.join(os.path.expanduser("~"), ".config")
        config_dir = os.path.join(config_home, "mdj-music-downloader")
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, "config.json")
        debug("Config directory created")

        # Load configuration (output dir + yt-dlp settings)
        self.output_dir, self.ytdlp_config = self.load_config()
        debug("Config loaded (output_dir + ytdlp_config)")

        # Download type
        self.download_type = ctk.StringVar(value="audio")
        debug("Variables initialized")

        # Download control
        self.downloading = False
        self.download_process = None

        # Thread-safe queue for communication
        self.message_queue = queue.Queue()

        # Download queue system
        self._ui_calls = queue.Queue()   # work for the Tk thread, see run_in_ui()
        self._run_id = 0                 # changes on every start/cancel; stale threads see it
        self.download_queue = []  # List of {url, status, widget} dicts
        self.current_download_index = -1
        debug("Data structures initialized")

        # Window size - wider for two columns
        # Give the position right away: the window is first shown by the update in
        # center_window_on_current_monitor(), and without a position it appeared in the
        # top-left corner and then jumped to the centre.
        x, y = centered_position(self.root, 900, 700)
        self.root.geometry(f"900x700+{x}+{y}")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        debug("Window size set")

        # Center window on current monitor (proper multi-monitor support)
        debug("Centering window...")
        self.center_window_on_current_monitor(900, 700)
        debug("Window centered")

        # Setup UI
        debug("Starting UI setup...")
        self.setup_ui()
        debug("UI setup complete")


        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        debug("Close handler set")

    def parse_error_message(self, stderr):
        """Convert technical error messages to user-friendly guidance"""
        if not stderr:
            return "Download failed. Please check your internet connection and try again."

        stderr_lower = stderr.lower()

        # Check for common error patterns
        if "importerror" in stderr_lower or "modulenotfounderror" in stderr_lower or "from yt_dlp import" in stderr_lower:
            return ("yt-dlp installation error detected.\n\n"
                    "Solution:\n"
                    "1. Close this application\n"
                    "2. Reinstall the application from the latest version\n"
                    "3. Contact support if the issue persists")

        elif "permission denied" in stderr_lower or "errno 13" in stderr_lower:
            return ("Permission error.\n\n"
                    "Solution:\n"
                    "1. Check that you have write access to the output folder\n"
                    "2. Try selecting a different output folder\n"
                    "3. Close any programs that might be using the file")

        elif ("network" in stderr_lower or "connection" in stderr_lower or "unreachable" in stderr_lower or
              "urlopen error" in stderr_lower or "name or service not known" in stderr_lower or
              "unable to download" in stderr_lower and "http" not in stderr_lower):
            return ("Network connection error.\n\n"
                    "Solution:\n"
                    "1. Check your internet connection\n"
                    "2. Try again in a few moments\n"
                    "3. Check if the website is accessible in your browser")

        elif "video unavailable" in stderr_lower or "private video" in stderr_lower or "removed" in stderr_lower:
            return ("Video not available.\n\n"
                    "Possible reasons:\n"
                    "• Video is private or deleted\n"
                    "• Video is region-restricted\n"
                    "• Invalid URL\n\n"
                    "Please check the URL and try another video.")

        elif "unsupported url" in stderr_lower or "no suitable extractor" in stderr_lower:
            return ("Unsupported URL.\n\n"
                    "This website is not supported.\n"
                    "Click the ? next to 'Video/Audio URL' to see the list of supported websites.")

        elif "http error 403" in stderr_lower or "forbidden" in stderr_lower:
            return ("Access denied (403 error).\n\n"
                    "The server is blocking the download request.\n"
                    "Try:\n"
                    "1. Using a different video from the same site\n"
                    "2. Waiting a few minutes and trying again\n"
                    "3. Updating yt-dlp to the latest version")

        elif "http error 404" in stderr_lower:
            return ("Video not found (404 error).\n\n"
                    "The video may have been removed or the URL is incorrect.\n"
                    "Please check the URL and try again.")

        elif "http error 429" in stderr_lower or "too many requests" in stderr_lower:
            return ("Rate limit exceeded.\n\n"
                    "You've made too many requests.\n"
                    "Please wait a few minutes before trying again.")

        elif "no space left" in stderr_lower or "disk full" in stderr_lower:
            return ("Storage full.\n\n"
                    "Your disk doesn't have enough space.\n"
                    "Free up some space and try again.")

        elif "ffmpeg" in stderr_lower or "avconv" in stderr_lower:
            return ("Media conversion error.\n\n"
                    "There was an issue converting the media file.\n"
                    "The download may have completed but conversion failed.\n"
                    "Check your output folder.")

        # If no specific error pattern matched, show a generic message
        # Extract just the last line or first meaningful line, not the full traceback
        lines = stderr.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('File "') and not line.startswith('  ') and "Traceback" not in line:
                # Found a meaningful error line
                if len(line) > 200:
                    line = line[:200] + "..."
                return f"Download error:\n{line}\n\nPlease check:\n• Internet connection\n• URL is valid\n• Output folder is accessible"

        return "Download failed. Please check your internet connection and URL, then try again."

    def setup_ui(self):
        """Setup the main UI - called from __init__"""
        debug("Creating main frame...")
        # Main frame
        self.frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.frame.pack(expand=True, fill="both", padx=15, pady=(25, 15))  # Extra top padding for header
        debug("Main frame created")

        debug("Creating header...")
        # Professional header with sleek black background
        header_frame = ctk.CTkFrame(
            self.frame,
            fg_color=("#1a1a1a", "#0a0a0a"),  # Black with subtle gradient
            corner_radius=12,
            height=70
        )
        header_frame.pack(fill="x", padx=10, pady=(10, 20))
        header_frame.pack_propagate(False)
        debug("Header frame created")

        debug("Creating title label...")
        # Title with icon
        # Title and subtitle sit together as one group, centred vertically
        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.place(relx=0.5, rely=0.5, anchor="center")
        title_label = ctk.CTkLabel(
            header_inner,
            text="♫  MUSIC DOWNLOADER",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="white",
            height=32
        )
        title_label.pack()
        debug("Title label created")

        debug("Creating subtitle...")
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_inner,
            text="Download audio & video from YouTube and more",
            font=ctk.CTkFont(size=11),
            text_color=("#999999", "#777777"),  # Subtle gray for subtitle
            height=16
        )
        subtitle_label.pack()
        debug("Subtitle created")

        debug("Creating content frame...")
        # Two-column layout container
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        debug("Content frame created")

        debug("Creating left column...")
        # LEFT COLUMN - Main controls (with border for separation)
        # Fixed width (308 + 2x10 ipadx = 328 px, the width it always had at launch): its
        # contents must never resize the panels. Before, e.g. "Download Queue (12)" made
        # it 3 px wider and "Download" narrower again, leaving buttons drawn clipped.
        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent", border_width=1,
                                  border_color=("#cccccc", "#444444"), corner_radius=10,
                                  width=LEFT_PANEL_WIDTH)
        left_frame.pack(side="left", fill="y", padx=(0, 8), ipadx=10, ipady=10)
        left_frame.pack_propagate(False)
        debug("Left column created")

        debug("Creating right column...")
        # RIGHT COLUMN - Queue management (distinct background)
        right_frame = ctk.CTkFrame(content_frame, fg_color=("#f5f5f5", "#252525"),
                                   corner_radius=10, border_width=1,
                                   border_color=("#cccccc", "#444444"))
        right_frame.pack(side="right", fill="both", expand=True)
        debug("Right column created")

        # === LEFT COLUMN CONTENT ===
        debug("Creating LEFT COLUMN widgets...")

        # URL entry frame with paste button
        debug("Creating URL entry frame...")
        self.url_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        debug("URL frame object created")
        self.url_frame.pack(fill="x", padx=10, pady=(12, 10))  # 12px top: keep clear of the rounded border
        debug("URL frame packed")

        debug("Creating URL label...")
        url_header = ctk.CTkFrame(self.url_frame, fg_color="transparent")
        url_header.pack(fill="x", pady=(0, 5))
        url_label = ctk.CTkLabel(
            url_header,
            text="Video/Audio URL:",
            font=ctk.CTkFont(size=13)
        )
        debug("URL label created")
        url_label.pack(side="left")
        # Small round "?" = Supported Sites (replaces the full-width button to save space)
        # Quiet grey outline (teal on hover), so it doesn't compete with the main buttons
        help_grey = "#7d8790"
        self.sites_help_btn = RoundIconButton(
            url_header,
            text="?",
            width=16, height=16, corner_radius=8, border_spacing=0, border_width=1,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="transparent",
            hover_color=ACCENT_DIM,
            border_color=help_grey,
            text_color=help_grey,
            command=self.show_supported_sites
        )
        self.sites_help_btn.pack(side="left", padx=(6, 0))
        self.sites_help_btn.bind("<Enter>", lambda e: self.sites_help_btn.configure(
            border_color=ACCENT_FG, text_color=ACCENT_FG), add="+")
        self.sites_help_btn.bind("<Leave>", lambda e: self.sites_help_btn.configure(
            border_color=help_grey, text_color=help_grey), add="+")
        HoverTip(self.sites_help_btn, "Supported sites")
        debug("URL label packed - CRITICAL POINT")

        debug("About to create entry_container...")
        # Entry with paste button container
        entry_container = ctk.CTkFrame(self.url_frame, fg_color="transparent")
        debug("entry_container created")
        entry_container.pack(fill="x")
        debug("entry_container packed")

        debug("About to create URL entry widget...")
        self.url_entry = ctk.CTkEntry(
            entry_container,
            placeholder_text="Enter URL here...",
            height=40,
            font=ctk.CTkFont(size=13)
        )
        debug("URL entry widget created")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        debug("URL entry widget packed")

        debug("About to create Paste button (first CTkButton)...")
        # Paste button
        self.paste_button = ctk.CTkButton(
            entry_container,
            text="Paste",
            width=60,
            height=40,
            font=ctk.CTkFont(size=12),
            command=self.paste_from_clipboard,
            corner_radius=8
        )
        debug("Paste button created")
        self.paste_button.pack(side="left")
        debug("Paste button packed")

        # CRITICAL FIX: Process pending Tkinter events to prevent segfault
        # CustomTkinter/Tkinter requires update_idletasks() here to avoid crash
        # when creating subsequent widgets. DO NOT REMOVE!
        debug("Forcing UI update before progress_frame...")
        try:
            self.root.update_idletasks()
            debug("UI update completed")
        except Exception as e:
            debug(f"UI update failed: {e}", level="WARN")

        debug("About to create progress_frame...")
        # Progress bar (hidden initially)
        self.progress_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        debug("progress_frame created")
        self.progress_frame.pack(fill="x", padx=10, pady=(10, 0))
        debug("progress_frame packed")

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            mode="indeterminate",
            height=8
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        self.progress_frame.pack_forget()  # Hide initially

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("#1a8f80", ACCENT_FG)
        )
        self.progress_label.pack(pady=(5, 0))

        # Download type selection using buttons
        self.radio_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.radio_frame.pack(fill="x", padx=10, pady=(15, 10))

        radio_label = ctk.CTkLabel(
            self.radio_frame,
            text="Download Type:",
            font=ctk.CTkFont(size=13)
        )
        radio_label.pack(anchor="w", pady=(0, 8))

        # Segmented switch: a dark track; the selected half is filled teal
        type_buttons = ctk.CTkFrame(self.radio_frame, fg_color=SWITCH_TRACK, corner_radius=10)
        type_buttons.pack(fill="x")

        self.audio_button = ctk.CTkButton(
            type_buttons,
            text="Audio",
            command=lambda: self._select_type("audio"),
            height=33,
            corner_radius=8,
            border_width=0,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.audio_button.pack(side="left", fill="x", expand=True, padx=(3, 1), pady=3)

        self.video_button = ctk.CTkButton(
            type_buttons,
            text="Video",
            command=lambda: self._select_type("video"),
            height=33,
            corner_radius=8,
            border_width=0,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.video_button.pack(side="left", fill="x", expand=True, padx=(1, 3), pady=3)

        # What the selected type saves as, in small grey text (set in yt-dlp Settings)
        self.type_summary = ctk.CTkLabel(self.radio_frame, text="", height=16,
                                         font=ctk.CTkFont(size=11), text_color="#7d8790")
        self.type_summary.pack(anchor="w", padx=(4, 0), pady=(4, 0))
        self._select_type(self.download_type.get())

        # Button frame - Download/Cancel and Queue buttons
        self.button_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=10, pady=(15, 10))

        # Left side - Download/Cancel button
        self.action_button_frame = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        self.action_button_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Download button
        self.download_button = ctk.CTkButton(
            self.action_button_frame,
            text="Download",
            command=self.start_download,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10
        )
        self.download_button.pack(fill="x", expand=True)

        # Cancel button (hidden initially)
        self.cancel_button = ctk.CTkButton(
            self.action_button_frame,
            text="Cancel",
            command=self.cancel_download,
            height=45,
            font=ctk.CTkFont(size=15),
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            corner_radius=10,
            text_color=LIGHT_TEXT
        )

        # Right side - Queue button (fixed position)
        self.queue_button = ctk.CTkButton(
            self.button_frame,
            text="+ Queue",
            command=self.add_to_queue,
            height=45,
            width=100,
            font=ctk.CTkFont(size=15),
            corner_radius=10,
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        self.queue_button.pack(side="right")

        # Settings buttons (compact, right after main buttons)
        settings_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        settings_frame.pack(fill="x", padx=10, pady=(15, 0))

        settings_btn = ctk.CTkButton(
            settings_frame,
            text="Output Folder",
            command=self.change_output_dir,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        settings_btn.pack(fill="x", pady=(0, 5))

        # yt-dlp Settings button
        ytdlp_settings_btn = ctk.CTkButton(
            settings_frame,
            text="⚙ yt-dlp Settings",
            command=self.show_ytdlp_settings,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        ytdlp_settings_btn.pack(fill="x", pady=(0, 5))

        # Update yt-dlp button
        update_ytdlp_btn = ctk.CTkButton(
            settings_frame,
            text="Update yt-dlp",
            command=self.update_ytdlp,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        if not IS_FLATPAK:      # Flatpak: yt-dlp is updated together with the app
            update_ytdlp_btn.pack(fill="x", pady=(0, 5))

        # Support Development button
        support_btn = ctk.CTkButton(
            settings_frame,
            text="☕ Support Development",
            command=self.open_support_page,
            height=32,
            font=ctk.CTkFont(size=10),
            fg_color="#8B4545",  # Muted red - less prominent
            hover_color="#A05555",
            text_color=("#DDDDDD", "#CCCCCC")  # Slightly dimmed text
        )
        support_btn.pack(fill="x")

        # Status line (left column, after settings). Normal messages use status_label;
        # "Saved to" results swap in status_text, where only the folder path is clickable.
        self._status_pack = dict(fill="x", padx=10, pady=(10, 0))
        self.status_label = ctk.CTkLabel(
            left_frame,
            text="",
            font=ctk.CTkFont(size=9),
            wraplength=350,
            text_color=("#666666", "#888888"),
            height=30
        )
        self.status_label.pack(**self._status_pack)
        self._setup_status_link()

        # === RIGHT COLUMN CONTENT ===

        # Queue panel title
        queue_title = ctk.CTkLabel(
            right_frame,
            text="Download Queue",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        queue_title.pack(pady=(12, 8), padx=15, anchor="w")

        # Album name entry (in right column)
        album_label = ctk.CTkLabel(
            right_frame,
            text="Album/Folder:",
            font=ctk.CTkFont(size=11)
        )
        album_label.pack(anchor="w", padx=15, pady=(0, 4))

        self.album_entry = ctk.CTkEntry(
            right_frame,
            placeholder_text="Optional - organize into subfolder",
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.album_entry.pack(fill="x", padx=15, pady=(0, 8))

        # Track numbering option
        self.number_tracks_var = ctk.BooleanVar(value=False)
        self.number_tracks_checkbox = ctk.CTkCheckBox(
            right_frame,
            text="Number tracks (01.song, 02.song...)",
            variable=self.number_tracks_var,
            font=ctk.CTkFont(size=10),
            checkbox_width=18,
            checkbox_height=18
        )
        self.number_tracks_checkbox.pack(anchor="w", padx=15, pady=(0, 12))

        # Separator line
        separator = ctk.CTkFrame(right_frame, height=2, fg_color=("#d0d0d0", "#404040"))
        separator.pack(fill="x", padx=15, pady=(0, 10))

        # Scrollable frame for queue items (minimum height)
        self.queue_scroll = ctk.CTkScrollableFrame(
            right_frame,
            fg_color="transparent",
            height=200
        )
        self.queue_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        enable_wheel_scrolling(self.queue_scroll)

        # Empty state label
        self.empty_queue_label = ctk.CTkLabel(
            self.queue_scroll,
            text="Queue is empty\n\nAdd URLs using the\n'+ Queue' button",
            font=ctk.CTkFont(size=11),
            text_color=("#999999", "#666666")
        )
        self.empty_queue_label.pack(pady=30)

        # Separator before buttons
        separator2 = ctk.CTkFrame(right_frame, height=1, fg_color=("#d0d0d0", "#404040"))
        separator2.pack(fill="x", padx=15, pady=(0, 10))

        # Queue management buttons
        queue_buttons_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        queue_buttons_frame.pack(fill="x", pady=(0, 12), padx=15)

        self.clear_queue_btn = ctk.CTkButton(
            queue_buttons_frame,
            text="Clear Queue",
            command=self.clear_queue,
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=("#d32f2f", "#f44336"),
            text_color=("#d32f2f", "#f44336"),
            hover_color=("#ffebee", "#4a1f1f")
        )
        self.clear_queue_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.save_queue_btn = ctk.CTkButton(
            queue_buttons_frame,
            text="Export",
            command=self.save_queue_to_file,
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        self.save_queue_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.load_queue_btn = ctk.CTkButton(
            queue_buttons_frame,
            text="Import",
            command=self.load_queue_from_file,
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        self.load_queue_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start queue checking
        self.root.after(100, self.check_queue)
        self.root.after(50, self._pump_ui_calls)

        # Check yt-dlp version
        self.root.after(500, self.check_ytdlp_version)

    def center_window_on_current_monitor(self, width, height):
        """Center window on the monitor where the mouse cursor is"""
        self.root.update_idletasks()
        x, y = centered_position(self.root, width, height)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def center_dialog(self, dialog, width, height):
        """Center a dialog window on the main window"""
        self.root.update_idletasks()
        dialog.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - width) // 2
        y = parent_y + (parent_height - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _select_type(self, type_value):
        """Update download type and the segmented switch"""
        self.download_type.set(type_value)
        on = dict(fg_color=ACCENT, hover_color=ACCENT_HOVER,
                  text_color=ACCENT_TEXT, text_color_disabled=ACCENT_DIM)
        off = dict(fg_color=SWITCH_TRACK, hover_color=SWITCH_HOVER,
                   text_color="#8a949c", text_color_disabled="#4a5257")
        audio = type_value == "audio"
        self.audio_button.configure(**(on if audio else off))
        self.video_button.configure(**(off if audio else on))
        self.update_type_summary()

    def update_type_summary(self):
        if getattr(self, "type_summary", None) is not None:
            audio = self.download_type.get() == "audio"
            self.type_summary.configure(text=download_summary(self.ytdlp_config, audio))

    def _queue_index_of(self, item_id):
        for i, item in enumerate(self.download_queue):
            if item.get('id') == item_id:
                return i
        return None

    def run_in_ui(self, fn, *args, **kwargs):
        """Run fn on the Tk thread. Safe to call from any thread.

        Background threads must never call Tk themselves (not even root.after() or
        widget.get()): if the Tk thread is busy in update_idletasks() at that moment,
        both threads wait for each other and the app freezes for good."""
        self._ui_calls.put((fn, args, kwargs))

    def _pump_ui_calls(self):
        try:
            while True:
                fn, args, kwargs = self._ui_calls.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    debug(f"UI call failed: {e}", level="WARN")
        except queue.Empty:
            pass
        try:
            self.root.after(50, self._pump_ui_calls)
        except tk.TclError:             # window closed
            pass

    def check_queue(self):
        """Check message queue from background thread"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()

                if msg_type == "success":
                    self.progress_bar.stop()
                    self.root.after(50, lambda: self.progress_bar.set(1.0))
                    self.root.after(100, lambda: self.progress_label.configure(
                        text="✓ Download complete!",
                        text_color="#4caf50"
                    ))
                    self.show_saved_status("Saved to: ", msg_data, "#4caf50")
                    self._keep_status = True  # don't let the following "reset" clear it
                elif msg_type == "already":
                    self.progress_bar.stop()
                    self.root.after(50, lambda: self.progress_bar.set(1.0))
                    self.root.after(100, lambda: self.progress_label.configure(
                        text="✓ Already downloaded", text_color="#4caf50"))
                    self.show_saved_status("Already in: ", msg_data, "#4caf50")
                    self._keep_status = True
                elif msg_type == "error":
                    self.progress_bar.stop()
                    self.root.after(50, lambda: self.progress_label.configure(
                        text="✖ Download failed",
                        text_color="#f44336"
                    ))
                    error_lower = str(msg_data).lower()
                    update_hint = ""
                    if any(word in error_lower for word in ["403", "forbidden", "old", "update", "version"]):
                        update_hint = (" → Check for app updates in your Software Manager" if IS_FLATPAK
                                       else " → Try updating: pip3 install -U yt-dlp")
                    self.status_label.configure(text=f"Error: {msg_data}{update_hint}", text_color="#f44336")
                    self._keep_status = True
                elif msg_type == "reset":
                    self.reset_ui(keep_status=getattr(self, "_keep_status", False))
                    self._keep_status = False
                elif msg_type in ("queue_success", "queue_failed"):
                    run_id, item_id = msg_data
                    if run_id != self._run_id:      # from a cancelled run: ignore
                        continue
                    ok = msg_type == "queue_success"
                    if ok:
                        self._run_done = getattr(self, "_run_done", 0) + 1
                    else:
                        self._run_failed = getattr(self, "_run_failed", 0) + 1
                    index = self._queue_index_of(item_id)
                    if index is not None:
                        self.update_queue_item_status(index, 'done' if ok else 'failed')
                    self.root.after(200, self.process_next_queue_item)

        except queue.Empty:
            pass

        # Check queue again after 100ms
        self.root.after(100, self.check_queue)

    # ---- "Saved to:" status line with a clickable folder path ----
    def _setup_status_link(self):
        self._status_link_dir = None
        self._status_link_text = None
        bg = self.status_label._apply_appearance_mode(self.status_label.cget("bg_color"))
        self._status_font = ctk.CTkFont(size=9)
        self.status_text = tk.Text(
            # width=1: don't ask for space (Text defaults to 80 characters, which widened the left
            # panel); it fills the panel's existing width and wraps instead.
            self.status_label.master, width=1, height=1, wrap="word", font=self._status_font,
            bg=bg, relief="flat", borderwidth=0, highlightthickness=0, padx=0, pady=6,
            cursor="arrow", takefocus=0, insertwidth=0,
            selectbackground=bg, inactiveselectbackground=bg, exportselection=False)
        self.status_text.tag_configure("all", justify="center")
        self.status_text.tag_configure("link", underline=False)
        self.status_text.tag_bind("link", "<Enter>", self._on_link_enter)
        self.status_text.tag_bind("link", "<Leave>", self._on_link_leave)
        self.status_text.tag_bind("link", "<Button-1>", self._on_link_click)
        self._fit_pending = False
        self.status_text.bind("<Configure>", lambda e: self._schedule_fit_status_text())
        self.status_text.configure(state="disabled")

        original_configure = self.status_label.configure

        def configure(*args, **kwargs):
            # Any other text written to the status line turns the "Saved to" view off
            if "text" in kwargs and self._status_link_dir and kwargs["text"] != self._status_link_text:
                self._hide_saved_status()
            return original_configure(*args, **kwargs)

        self._status_label_configure = original_configure
        self.status_label.configure = configure

    def show_saved_status(self, before, folder, color, after=""):
        """Show `before + folder + after`; only `folder` is clickable (underlined on hover) and opens it."""
        text = before + folder + after
        self._status_label_configure(text=text, text_color=color)  # keep label text in sync (cget / tests)
        self._status_link_dir, self._status_link_text = folder, text
        st = self.status_text
        st.configure(state="normal")
        st.delete("1.0", "end")
        st.insert("end", before, ("all",))
        st.insert("end", folder, ("all", "link"))
        st.insert("end", after, ("all",))
        st.configure(state="disabled", fg=color)
        st.tag_configure("link", underline=False)
        if not st.winfo_manager():
            st.pack(after=self.status_label, **self._status_pack)  # same spot as the label
        self.status_label.pack_forget()
        self._schedule_fit_status_text()

    def _hide_saved_status(self):
        self._status_link_dir = self._status_link_text = None
        if not self.status_label.winfo_manager():
            if self.status_text.winfo_manager():
                self.status_label.pack(before=self.status_text, **self._status_pack)
            else:
                self.status_label.pack(**self._status_pack)
        self.status_text.pack_forget()
        self.status_text.configure(cursor="arrow")

    def _schedule_fit_status_text(self):
        # Run once, after Tk has finished laying out (never from inside a <Configure> callback,
        # since changing the height fires <Configure> again).
        if not self._fit_pending:
            self._fit_pending = True
            self.root.after_idle(self._fit_status_text)

    def _fit_status_text(self):
        """Grow/shrink the text box to the number of wrapped lines."""
        self._fit_pending = False
        try:
            if self.status_text.winfo_width() <= 1:
                return  # not laid out yet; <Configure> will call us again with the real width
            # Counting to "end" (not "end-1c") gives the number of lines, not the number of line breaks
            n = self.status_text.count("1.0", "end", "displaylines")
            n = n[0] if isinstance(n, tuple) else n
            n = max(1, int(n or 1))
            if int(self.status_text.cget("height")) != n:  # only when it changes, so no resize loop
                self.status_text.configure(height=n)
        except tk.TclError:
            pass

    def _on_link_enter(self, event=None):
        self.status_text.tag_configure("link", underline=True)
        self.status_text.configure(cursor="hand2")

    def _on_link_leave(self, event=None):
        self.status_text.tag_configure("link", underline=False)
        self.status_text.configure(cursor="arrow")

    def _on_link_click(self, event=None):
        folder = self._status_link_dir
        if not folder:
            return
        if not os.path.isdir(folder):
            TooltipNotification(self.root, "⚠ Folder no longer exists")
            return
        if open_with_system(folder):
            TooltipNotification(self.root, "Opening folder...")
        else:
            TooltipNotification(self.root, "⚠ Could not open the file manager")

    def check_ytdlp_version(self):
        """Check in the background that yt-dlp is installed and working, then update the status line."""
        def worker():
            path, version = self._resolve_ytdlp()
            self._ytdlp_cache = (path, version)
            exists = os.path.exists(path) or shutil.which(path)
            self.run_in_ui(self._show_ytdlp_status, path, version, exists)
            if version:                 # preload the Supported Sites list, so "?" opens instantly
                self.run_in_ui(lambda: self.root.after(500, self.fetch_supported_sites))
        threading.Thread(target=worker, daemon=True).start()

    def _show_ytdlp_status(self, path, version, exists):
        frozen = getattr(sys, 'frozen', False)
        if version:
            debug(f"yt-dlp version check OK: {version} ({path})")
            # All good: don't overwrite a download in progress or a result the user is reading
            if not self.downloading and not self._status_link_dir:
                self.status_label.configure(text=f"v{APP_VERSION}", text_color=("#666666", "#888888"))
        elif not exists:
            self.status_label.configure(
                text=("⚠ yt-dlp missing! Please reinstall the application" if IS_FLATPAK
                      else "⚠ yt-dlp missing! Click 'Update yt-dlp' or reinstall the application" if frozen
                      else "⚠ yt-dlp not found! Install with: pip3 install -U yt-dlp"),
                text_color="#ff9800")
        else:
            debug(f"yt-dlp at {path} does not run", level="ERROR")
            self.status_label.configure(
                text=("⚠ yt-dlp error! Please reinstall the application" if IS_FLATPAK
                      else "⚠ yt-dlp error! Click 'Update yt-dlp' to repair it" if frozen
                      else "⚠ yt-dlp error! Try: pip3 install -U --force-reinstall yt-dlp"),
                text_color="#ff9800")

    def paste_from_clipboard(self):
        try:
            clipboard_content = self.root.clipboard_get().strip()
            if clipboard_content:
                self.url_entry.delete(0, 'end')
                self.url_entry.insert(0, clipboard_content)
                TooltipNotification(self.root, "✓ URL pasted from clipboard", once="paste")
            else:
                TooltipNotification(self.root, "⚠ Clipboard is empty")
        except:
            TooltipNotification(self.root, "⚠ Clipboard is empty")

    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_entry.get().strip()
        if not url:
            TooltipNotification(self.root, "⚠ Please enter a URL")
            return

        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            TooltipNotification(self.root, "⚠ Invalid URL - must start with http:// or https://")
            return

        # Check for duplicates (same video, whatever the link style)
        key = url_key(url)
        if any(url_key(item['url']) == key for item in self.download_queue):
            TooltipNotification(self.root, "⚠ URL already in queue")
            return

        self.download_queue.append(new_queue_item(url))

        # Show queue panel when first item is added
        if len(self.download_queue) == 1:
            self.empty_queue_label.pack_forget()

        self.create_queue_item(len(self.download_queue) - 1)
        self.url_entry.delete(0, 'end')

        # Update button text
        self.update_download_button_text()

        queue_size = len(self.download_queue)
        TooltipNotification(self.root, "✓ Added to queue", once="queued")

    def create_queue_item(self, index):
        """Create widget for queue item"""
        item = self.download_queue[index]

        item_frame = ctk.CTkFrame(self.queue_scroll, fg_color=("#e0e0e0", "#3b3b3b"))
        item_frame.pack(fill="x", pady=2, padx=2)

        top_row = ctk.CTkFrame(item_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=5, pady=(5, 2))

        status_label = ctk.CTkLabel(
            top_row,
            text="…",
            font=ctk.CTkFont(size=16),
            width=30
        )
        status_label.pack(side="left", padx=(0, 5))

        # Pack the X button BEFORE the URL: when space is short, Tk shrinks the widgets
        # packed last, so the URL (not the button) gives way.
        remove_btn = ctk.CTkButton(
            top_row,
            text="X",
            width=30,
            height=25,
            command=lambda item_id=item['id']: self.remove_queue_item(item_id),
            fg_color="transparent",
            hover_color=("#d32f2f", "#b71c1c"),
            font=ctk.CTkFont(size=14),
            text_color=LIGHT_TEXT
        )
        remove_btn.pack(side="right", padx=5)
        if self.downloading:
            remove_btn.configure(state="disabled")   # removing songs needs Cancel first

        url_label = ctk.CTkLabel(
            top_row,
            text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
            width=1  # don't let the text's natural width push the row wider
        )
        url_label.pack(side="left", fill="x", expand=True)
        url_label._full_text = item['url']
        url_label._shown_text = None
        top_row.bind("<Configure>", lambda e, lbl=url_label, row=top_row, st=status_label, btn=remove_btn:
                     self._fit_url_label(lbl, row, st, btn))
        self.root.after_idle(lambda: self._fit_url_label(url_label, top_row, status_label, remove_btn))

        progress_bar = ctk.CTkProgressBar(
            item_frame,
            height=6,
            progress_color=("#666666", "#888888")
        )
        progress_bar.pack(fill="x", padx=5, pady=(0, 5))
        progress_bar.set(0)

        item['widget'] = {
            'frame': item_frame,
            'status_label': status_label,
            'url_label': url_label,
            'remove_btn': remove_btn,
            'progress_bar': progress_bar
        }
        # Show the item's real state (a row could otherwise show "waiting" for a done song)
        if item['status'] != 'waiting':
            self.update_queue_item_status(index, item['status'])

    @staticmethod
    def _truncate_to_width(text, font, max_px, ellipsis="..."):
        """Longest prefix of `text` that fits in `max_px` pixels, ending with `ellipsis` if cut."""
        if font.measure(text) <= max_px:
            return text
        lo, hi = 0, len(text)
        while lo < hi:  # binary search on the number of characters kept
            mid = (lo + hi + 1) // 2
            if font.measure(text[:mid] + ellipsis) <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo] + ellipsis if lo > 0 else ellipsis

    def _fit_url_label(self, label, row, status_label, remove_btn):
        """Show as much of the URL as fits between the status icon and the X button."""
        try:
            if not label.winfo_exists():
                return
            row_w = row.winfo_width()
            if row_w <= 1:
                return  # not laid out yet; <Configure> will call again
            # Space left for the URL = row - status icon - X button - their padding
            avail = row_w - status_label.winfo_reqwidth() - remove_btn.winfo_reqwidth() - 5 - 10 - 8
            font = tkfont.Font(font=label._label.cget("font"))
            shown = self._truncate_to_width(label._full_text, font, max(avail, 20))
            if shown != label._shown_text:  # only touch the label when the text really changes
                label._shown_text = shown
                label.configure(text=shown)
        except tk.TclError:
            pass

    def remove_queue_item(self, item_id):
        """X button of a queue row"""
        index = self._queue_index_of(item_id)
        if index is not None:
            self.remove_from_queue(index)

    def remove_from_queue(self, index):
        """Remove item from queue (not while downloading: press Cancel first)"""
        if self.downloading:
            TooltipNotification(self.root, "⚠ Press Cancel first to remove songs")
            return
        if 0 <= index < len(self.download_queue):
            item = self.download_queue.pop(index)
            # Remove just this row: the other rows keep their widgets (and their status)
            if item['widget']:
                item['widget']['frame'].destroy()
                item['widget'] = None

            if len(self.download_queue) == 0:
                self.empty_queue_label.pack(expand=True, pady=50)

            # Update button text
            self.update_download_button_text()

    def _set_remove_buttons(self, enabled):
        """Enable/disable the X buttons of all queue rows"""
        for item in self.download_queue:
            if item['widget']:
                try:
                    item['widget']['remove_btn'].configure(state="normal" if enabled else "disabled")
                except tk.TclError:
                    pass

    def pending_count(self):
        """Queue items still to download (failed ones are retried on the next run)."""
        return sum(1 for item in self.download_queue if item['status'] in ('waiting', 'failed'))

    def update_download_button_text(self):
        """Update download button text: number of queue items still to download"""
        pending = self.pending_count()
        new_text = f"Download Queue ({pending})" if pending > 0 else "Download"
        self.download_button.configure(text=new_text)

    def update_queue_item_status(self, index, status):
        """Update queue item status"""
        if 0 <= index < len(self.download_queue):
            item = self.download_queue[index]
            item['status'] = status

            if item['widget']:
                status_icons = {'waiting': '…', 'downloading': '↓', 'done': '✓', 'failed': '✗'}
                status_colors = {
                    'waiting': ("#666666", "#888888"),
                    'downloading': ("#1a8f80", ACCENT_FG),
                    'done': "#4caf50",
                    'failed': "#f44336"
                }
                progress_values = {'waiting': 0, 'downloading': 0.5, 'done': 1.0, 'failed': 1.0}

                item['widget']['status_label'].configure(
                    text=status_icons.get(status, '…'),
                    text_color=status_colors.get(status, ("#666666", "#888888"))
                )
                item['widget']['progress_bar'].configure(
                    progress_color=status_colors.get(status, ("#666666", "#888888"))
                )
                item['widget']['progress_bar'].set(progress_values.get(status, 0))

    def clear_queue(self):
        """Clear all queue items with confirmation"""
        if len(self.download_queue) == 0:
            TooltipNotification(self.root, "Queue is already empty")
            return

        if self.downloading:
            TooltipNotification(self.root, "⚠ Cannot clear queue while downloading")
            return

        confirm_window = ctk.CTkToplevel(self.root)
        confirm_window.title("Confirm Clear Queue")
        confirm_window.attributes('-topmost', True)
        self.center_dialog(confirm_window, 400, 200)

        frame = ctk.CTkFrame(confirm_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        warning = ctk.CTkLabel(
            frame,
            text="Clear Queue",
            font=ctk.CTkFont(size=18),
            text_color="#ff9800"
        )
        warning.pack(pady=(15, 10))

        msg = ctk.CTkLabel(
            frame,
            text=f"Delete all {len(self.download_queue)} items from queue?\nThis cannot be undone.",
            font=ctk.CTkFont(size=13),
            wraplength=350
        )
        msg.pack(pady=10)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(pady=(10, 15), fill="x", padx=20)

        def do_clear():
            # Close dialog first
            confirm_window.destroy()

            # Perform clearing after dialog is destroyed
            def clear_queue_now():
                # Destroy all queue item widgets (but not empty_queue_label)
                for widget in self.queue_scroll.winfo_children():
                    if widget != self.empty_queue_label:
                        widget.destroy()

                # Clear the queue list
                self.download_queue.clear()

                # Show empty state
                self.empty_queue_label.pack(expand=True, pady=50)

                # Update button text
                self.update_download_button_text()

                # Show notification
                self.root.after(50, lambda: TooltipNotification(self.root, "✓ Queue cleared"))

            self.root.after(50, clear_queue_now)

        yes_btn = ctk.CTkButton(
            button_frame,
            text="Yes, Clear All",
            height=35,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=do_clear,
            text_color=LIGHT_TEXT
        )
        yes_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        no_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            height=35,
            command=confirm_window.destroy
        )
        no_btn.pack(side="left", expand=True, fill="x")

    def save_queue_to_file(self):
        """Save queue URLs to text file"""
        if len(self.download_queue) == 0:
            TooltipNotification(self.root, "Queue is empty - nothing to save")
            return

        self.ask_path("save", "Save Queue to File", self._save_queue_to,
                      filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                      defaultextension=".txt", initialfile="queue.txt")

    def _save_queue_to(self, filename):
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    for item in self.download_queue:
                        f.write(item['url'] + '\n')
                TooltipNotification(self.root, f"✓ Saved {len(self.download_queue)} URLs to file")
            except Exception as e:
                self.show_error_dialog("Save Failed", f"Could not save queue:\n{str(e)}")

    def load_queue_from_file(self):
        """Load queue URLs from text file"""
        if not portal_can_open_in_folder():
            self.show_import_picker()       # the system dialog would open in the home folder
            return
        self.browse_queue_file()

    def browse_queue_file(self):
        self.ask_path("open", "Load Queue from File", self._load_queue_from,
                      filetypes=[("Text files", "*.txt"), ("All files", "*.*")])

    def show_import_picker(self):
        """Import window listing the queue files (.txt) in the Output Folder, newest first,
        with "Other folder..." for the system dialog."""
        win = ctk.CTkToplevel(self.root)
        win.title("Import Queue")
        self.center_dialog(win, 480, 430)
        win.minsize(380, 320)
        muted = ("#666666", "#8a949c")

        frame = ctk.CTkFrame(win, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=12, pady=12)
        ctk.CTkLabel(frame, text="Import Queue",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 0))
        folder = self.output_dir
        shown = folder.replace(os.path.expanduser("~"), "~", 1)
        ctk.CTkLabel(frame, text=f"Queue files in your Output Folder:\n{shown}",
                     font=ctk.CTkFont(size=11), text_color=muted, justify="center",
                     wraplength=420).pack(pady=(2, 8))

        files = []
        try:
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if name.lower().endswith(".txt") and os.path.isfile(path):
                    files.append((os.path.getmtime(path), name, path))
        except OSError:
            pass
        files.sort(reverse=True)

        listing = ctk.CTkScrollableFrame(frame, fg_color=("#e8e8e8", "#1f2326"), corner_radius=8)
        enable_wheel_scrolling(listing)
        chosen = {"path": None, "button": None}

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        import_btn = ctk.CTkButton(buttons, text="Import", height=34, state="disabled",
                                   fg_color=ACCENT_DIM, hover_color=ACCENT_HOVER,
                                   text_color=ACCENT_TEXT, text_color_disabled="#6f8582")

        def do_import(path=None):
            path = path or chosen["path"]
            if path:
                win.destroy()
                self._load_queue_from(path)

        def select(path, btn):
            if chosen["button"] is not None and chosen["button"].winfo_exists():
                chosen["button"].configure(fg_color="transparent")
            chosen.update(path=path, button=btn)
            btn.configure(fg_color=ACCENT_DIM)
            import_btn.configure(state="normal", fg_color=ACCENT)

        today = datetime.now().date()
        for mtime, name, path in files[:300]:
            when = datetime.fromtimestamp(mtime)
            date = when.strftime("Today %H:%M") if when.date() == today else when.strftime("%d %b %Y")
            row = ctk.CTkFrame(listing, fg_color="transparent", corner_radius=6, height=30)
            row.pack(fill="x", padx=4, pady=1)
            name_lbl = ctk.CTkLabel(row, text=name, anchor="w", font=ctk.CTkFont(size=12))
            name_lbl.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=3)
            date_lbl = ctk.CTkLabel(row, text=date, font=ctk.CTkFont(size=11), text_color=muted)
            date_lbl.pack(side="right", padx=10)
            for w in (row, name_lbl, date_lbl):
                w.bind("<Button-1>", lambda e, p=path, r=row: select(p, r))
                w.bind("<Double-Button-1>", lambda e, p=path: do_import(p))
                w.configure(cursor="hand2")
        if not files:
            ctk.CTkLabel(listing, text="No queue files here yet.\n\nUse Export to save a queue,\n"
                                       "or click \"Other folder...\" to find one.",
                         font=ctk.CTkFont(size=12), text_color=muted).pack(pady=40)

        def other_folder():
            win.destroy()
            self.browse_queue_file()

        ctk.CTkButton(buttons, text="Other folder...", command=other_folder, height=34,
                      fg_color="transparent", border_width=1, text_color=LIGHT_TEXT,
                      hover_color=ACCENT_DIM).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(buttons, text="Cancel", command=win.destroy, height=34,
                      fg_color="transparent", border_width=1, text_color=LIGHT_TEXT,
                      hover_color=ACCENT_DIM).pack(side="left", expand=True, fill="x", padx=4)
        import_btn.configure(command=do_import)
        import_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))
        buttons.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        listing.pack(expand=True, fill="both", padx=12, pady=(0, 10))
        win.bind("<Return>", lambda e: do_import())
        win.bind("<Escape>", lambda e: win.destroy())

    def _load_queue_from(self, filename):
        if filename:
            try:
                # utf-8-sig: files saved by some editors start with a byte-order mark
                with open(filename, 'r', encoding='utf-8-sig', errors='replace') as f:
                    lines = [line.strip() for line in f if line.strip()]

                if not lines:
                    TooltipNotification(self.root, "⚠ File is empty")
                    return

                added_count = skipped_count = invalid_count = 0
                keys = {url_key(item['url']) for item in self.download_queue}
                for url in lines:
                    if not (url.startswith('http://') or url.startswith('https://')):
                        invalid_count += 1
                        continue
                    key = url_key(url)
                    if key in keys:              # already queued (or twice in the file)
                        skipped_count += 1
                        continue
                    keys.add(key)
                    self.download_queue.append(new_queue_item(url))
                    if len(self.download_queue) == 1:
                        self.empty_queue_label.pack_forget()
                    self.create_queue_item(len(self.download_queue) - 1)
                    added_count += 1

                self.update_download_button_text()
                if added_count == 0:
                    message = "⚠ No new URLs in this file"
                else:
                    message = f"✓ Loaded {added_count} URLs"
                    if self.downloading:
                        message += " (added to the running queue)"
                extras = []
                if skipped_count:
                    extras.append(f"{skipped_count} already in queue")
                if invalid_count:
                    extras.append(f"{invalid_count} lines skipped")
                if extras:
                    message += " (" + ", ".join(extras) + ")"
                TooltipNotification(self.root, message)

            except Exception as e:
                self.show_error_dialog("Load Failed", f"Could not load queue:\n{str(e)}")

    def get_default_ytdlp_config(self):
        """Return default yt-dlp configuration"""
        return {
            "common_args": [
                "--ignore-config"  # Ignore system yt-dlp config for consistency
            ],
            "audio_format": "mp3",
            "audio_quality": "0",  # 0 = best quality
            "audio_extra_args": [],
            "video_format": "mp4",
            "video_quality": DEFAULT_VIDEO_FORMAT,
            "video_extra_args": [
                "--merge-output-format", "mp4",
                "--recode-video", "mp4"
            ],
            "embed_thumbnail": False,   # cover art inside the file (--embed-thumbnail)
            "embed_metadata": False,    # title/artist/date tags (--embed-metadata)
            "cookies_browser": "",      # --cookies-from-browser <name>; "" = off
            "custom_args": []  # User's custom arguments (applied to all downloads)
        }

    def load_config(self):
        """Load full config including output_dir and yt-dlp settings"""
        default_dir = os.path.expanduser("~/Music/MDJ Downloads")
        # Default folder up to v1.0.3. If a saved config still points at it, move to the new default.
        old_default_dir = os.path.expanduser("~/Music/YouTube MP3")
        default_ytdlp = self.get_default_ytdlp_config()

        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)

                # Load output directory
                saved_dir = config.get("output_dir", default_dir)
                if os.path.normpath(os.path.expanduser(saved_dir)) == old_default_dir:
                    saved_dir = default_dir
                if not (os.path.exists(os.path.dirname(saved_dir)) or saved_dir == default_dir):
                    saved_dir = default_dir

                # Load yt-dlp config (with defaults for missing keys)
                ytdlp_config = config.get("ytdlp_config", default_ytdlp)
                # Merge with defaults to ensure all keys exist
                for key, value in default_ytdlp.items():
                    if key not in ytdlp_config:
                        ytdlp_config[key] = value

                return saved_dir, ytdlp_config

        except (FileNotFoundError, json.JSONDecodeError):
            return default_dir, default_ytdlp

    def load_output_dir(self):
        """Legacy method - loads output dir from config"""
        output_dir, _ = self.load_config()
        return output_dir

    def save_config(self):
        """Save full config including output_dir and yt-dlp settings"""
        config = {
            "output_dir": self.output_dir,
            "ytdlp_config": self.ytdlp_config
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    def save_output_dir(self):
        """Legacy method - saves output dir to config"""
        self.save_config()

    def build_ytdlp_command(self, url, download_dir, is_audio=True, cfg=None, ytdlp_path=None):
        """Build yt-dlp command from config settings (cfg: another config, for previews)"""
        ytdlp_path = ytdlp_path or self.get_yt_dlp_path()
        cfg = cfg if cfg is not None else self.ytdlp_config

        # Start with common args
        command = [ytdlp_path] + normalize_args(cfg.get("common_args", []))
        if IS_FLATPAK:
            # YouTube needs a JavaScript engine; the Flatpak bundles Node.js (yt-dlp only looks for Deno by default)
            command += ["--js-runtimes", "node"]

        if is_audio:
            # Audio download
            command.extend(["-x", "--audio-format", cfg.get("audio_format", "mp3")])
            command.extend(["--audio-quality", cfg.get("audio_quality", "0")])
            command.extend(cfg.get("audio_extra_args", []))
        else:
            # Video download
            video_quality = cfg.get("video_quality", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best")
            command.extend(["-f", video_quality])
            command.extend(cfg.get("video_extra_args", []))

        # Options from the Basic tab of yt-dlp Settings
        if cfg.get("embed_thumbnail"):
            command.append("--embed-thumbnail")
        if cfg.get("embed_metadata"):
            command.append("--embed-metadata")
        if cfg.get("cookies_browser") and not IS_FLATPAK:   # the sandbox can't read browser profiles
            command.extend(["--cookies-from-browser", cfg["cookies_browser"]])

        # A link to a song inside a playlist (watch?v=...&list=...) downloads only that song;
        # playlist links still download the whole list. (--yes-playlist in Custom arguments
        # comes later and wins.)
        command.append("--no-playlist")

        # Add custom user arguments
        command.extend(normalize_args(cfg.get("custom_args", [])))

        # Output template and URL
        command.extend(["-o", os.path.join(download_dir, "%(title)s.%(ext)s")])
        command.append(url)

        return command

    def start_download(self):
        # Check ffmpeg
        if shutil.which("ffmpeg") is None:
            self.show_error_dialog("Error", "ffmpeg is missing.\nPlease reinstall the application." if IS_FLATPAK
                                   else "ffmpeg is not installed.\nInstall it using: sudo apt install ffmpeg")
            return

        # Process queue or single download
        if self.pending_count() > 0:
            self.process_queue()
        else:
            url = self.url_entry.get().strip()
            if not url:
                if self.download_queue:
                    TooltipNotification(self.root, "✓ Everything in the queue is already downloaded")
                else:
                    self.show_error_dialog("Error", "Please enter a URL")
                return
            self._run_id += 1
            run_id = self._run_id
            self._set_remove_buttons(False)

            self.download_button.pack_forget()
            self.cancel_button.pack(fill="x", expand=True)
            self.url_entry.configure(state="disabled")
            self.paste_button.configure(state="disabled")
            self.audio_button.configure(state="disabled")
            self.video_button.configure(state="disabled")
            self.queue_button.configure(state="disabled")
            self.album_entry.configure(state="disabled")
            self.number_tracks_checkbox.configure(state="disabled")
            self.clear_queue_btn.configure(state="disabled")
            self.save_queue_btn.configure(state="disabled")
            self.load_queue_btn.configure(state="disabled")

            self.downloading = True
            self.status_label.configure(text="")  # Clear old status
            self.progress_frame.pack(fill="x", padx=20, pady=(10, 0))
            self.progress_bar.set(0)
            self.progress_bar.start()
            self.progress_label.configure(
                text="Starting download...",
                text_color=("#1a8f80", ACCENT_FG)
            )
            self.status_label.configure(
                text="Downloading...",
                text_color=("#666666", "#888888")
            )

            threading.Thread(target=self.download_music, args=(url, None, self._download_options()),
                             kwargs={"run_id": run_id}, daemon=True).start()

    def process_queue(self):
        """Download every queue item that is waiting (or failed last time)"""
        if self.pending_count() == 0:
            return
        for i, item in enumerate(self.download_queue):
            if item['status'] == 'failed':          # retry failed items
                self.update_queue_item_status(i, 'waiting')

        self.download_button.pack_forget()
        self.cancel_button.pack(fill="x", expand=True)
        # Settings that apply to the whole run are locked. Adding URLs (+ Queue / Import)
        # stays possible: new items are downloaded in this run.
        self.audio_button.configure(state="disabled")
        self.video_button.configure(state="disabled")
        self.album_entry.configure(state="disabled")
        self.number_tracks_checkbox.configure(state="disabled")
        self.clear_queue_btn.configure(state="disabled")

        self._run_id += 1
        self.downloading = True
        self._set_remove_buttons(False)
        self.status_label.configure(text="")  # Clear old status
        self.progress_frame.pack(fill="x", padx=20, pady=(10, 0))

        self.current_download_index = 0
        self._queue_saved_dirs = []
        self._run_done = self._run_failed = 0  # counts for this run only
        self.process_next_queue_item()

    def process_next_queue_item(self):
        """Start the first waiting item; finish the run when none is left"""
        if not self.downloading:
            return
        for index, item in enumerate(self.download_queue):
            if item['status'] == 'waiting':
                self.current_download_index = index
                self.update_queue_item_status(index, 'downloading')

                self.progress_bar.set(0)
                self.progress_bar.start()
                self.progress_label.configure(
                    text=f"Downloading {index + 1}/{len(self.download_queue)}...",
                    text_color=("#1a8f80", ACCENT_FG)
                )
                threading.Thread(target=self.download_music,
                                 args=(item['url'], item['id'], self._download_options()),
                                 kwargs={"run_id": self._run_id},
                                 daemon=True).start()
                return

        self.queue_processing_complete()

    def queue_processing_complete(self):
        """Called when all queue items processed"""
        self.downloading = False
        self.current_download_index = -1

        # Count only what happened in this run (items finished in an earlier run stay "done" in the list)
        done_count = getattr(self, "_run_done", 0)
        failed_count = getattr(self, "_run_failed", 0)

        # (The album playlist is updated after each download, see download_music)

        # Where the files went (same folder for the whole queue, incl. the Album/Folder subfolder)
        saved_dirs = list(getattr(self, "_queue_saved_dirs", []))  # folders used in this run

        summary = f"Queue complete: {done_count} downloaded, {failed_count} failed"
        color = "#4caf50" if failed_count == 0 else "#ff9800"
        if saved_dirs:
            more = f" (+{len(saved_dirs) - 1} more)" if len(saved_dirs) > 1 else ""
            self.show_saved_status(summary + "\nSaved to: ", saved_dirs[0], color, more)
        else:
            self.status_label.configure(text=summary, text_color=color)
        self._keep_status = True  # don't let the following "reset" clear it

        self.message_queue.put(("reset", None))

    def cancel_download(self):
        confirm_window = ctk.CTkToplevel(self.root)
        confirm_window.title("Confirm Cancel")
        confirm_window.attributes('-topmost', True)
        self.center_dialog(confirm_window, 380, 200)

        frame = ctk.CTkFrame(confirm_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        warning = ctk.CTkLabel(
            frame,
            text="Confirm Cancel",
            font=ctk.CTkFont(size=18),
            text_color="#ff9800"
        )
        warning.pack(pady=(15, 10))

        msg = ctk.CTkLabel(
            frame,
            text="Are you sure you want to cancel\nthe current download?",
            font=ctk.CTkFont(size=13),
            wraplength=320
        )
        msg.pack(pady=10)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(pady=(10, 15), fill="x", padx=20)

        def do_cancel():
            # Close dialog first
            confirm_window.destroy()

            if not self.downloading:            # finished while the dialog was open
                return
            # Invalidate the running download thread first, then stop yt-dlp (if it is
            # running: it may be between two songs, or still checking the URL)
            self._run_id += 1
            self.downloading = False
            self._stop_process(self.download_process)

            # Reset queue items that were downloading back to waiting
            for i, item in enumerate(self.download_queue):
                if item['status'] == 'downloading':
                    self.update_queue_item_status(i, 'waiting')

            self.current_download_index = -1
            self.reset_ui()
            self.progress_label.configure(text="Download cancelled")
            self.root.after(2000, lambda: self.downloading or self.progress_frame.pack_forget())

        yes_btn = ctk.CTkButton(
            button_frame,
            text="Yes, Cancel",
            height=35,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=do_cancel,
            text_color=LIGHT_TEXT
        )
        yes_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        no_btn = ctk.CTkButton(
            button_frame,
            text="No, Continue",
            height=35,
            command=confirm_window.destroy
        )
        no_btn.pack(side="left", expand=True, fill="x")

    def get_yt_dlp_path(self):
        """Path of the yt-dlp to use (cached; call invalidate_ytdlp_cache() after an update)."""
        cache = getattr(self, "_ytdlp_cache", None)
        if cache is None:
            lock = self.__dict__.setdefault("_ytdlp_lock", threading.Lock())
            with lock:
                cache = getattr(self, "_ytdlp_cache", None)
                if cache is None:
                    cache = self._resolve_ytdlp()
                    self._ytdlp_cache = cache
        return cache[0]

    def invalidate_ytdlp_cache(self):
        self._ytdlp_cache = None

    def _resolve_ytdlp(self):
        """Pick the newest *working* yt-dlp among the user's own copy and the system copy.

        Returns (path, version_string_or_None)."""
        sys_path = system_ytdlp_path()
        # Flatpak: only the bundled copy (no self-downloaded yt-dlp, see IS_FLATPAK)
        candidates = [] if IS_FLATPAK else [USER_YTDLP_PATH]
        if sys_path:
            candidates.append(sys_path)
        else:
            # Running from source: also consider yt-dlp on PATH / common locations
            found = shutil.which("yt-dlp")
            for path in ([found] if found else []) + [
                    os.path.expanduser("~/.local/bin/yt-dlp"), "/usr/local/bin/yt-dlp", "/usr/bin/yt-dlp"]:
                if path and os.path.exists(path):
                    candidates.append(path)
                    break

        best = None  # (version_tuple, path, version_string)
        for path in candidates:
            vt, vs = get_ytdlp_version(path)
            debug(f"yt-dlp candidate {path}: {vs}")
            if vt is not None and (best is None or vt > best[0]):
                best = (vt, path, vs)
        if best:
            debug(f"Using yt-dlp {best[2]} at {best[1]}")
            return best[1], best[2]

        # Nothing runs: return the first candidate that exists so callers can report the error
        for path in candidates:
            if os.path.exists(path):
                return path, None
        return (sys_path or "yt-dlp"), None

    def get_album_folder(self, base_dir, album_name):
        """Get album folder path (case-insensitive)"""
        if not album_name or not album_name.strip():
            return base_dir

        album_name = safe_folder_name(album_name)
        if not album_name:
            return base_dir

        try:
            existing_items = os.listdir(base_dir)
            for item in existing_items:
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path) and item.lower() == album_name.lower():
                    return item_path
        except OSError:
            pass

        album_path = os.path.join(base_dir, album_name)
        os.makedirs(album_path, exist_ok=True)
        return album_path

    def check_has_video(self, url):
        """Check if URL has video streams available"""
        ytdlp_path = self.get_yt_dlp_path()
        try:
            # Run yt-dlp with --dump-json to get format info
            result = subprocess.run(
                [ytdlp_path, "--ignore-config", "--dump-json", "--no-playlist", url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # If we can't get info, assume video exists (let yt-dlp handle the error)
                return True

            # Parse JSON output
            import json
            video_info = json.loads(result.stdout)

            # Check if any formats have video streams
            formats = video_info.get('formats', [])
            has_video = any(
                fmt.get('vcodec') != 'none' and fmt.get('vcodec') is not None
                for fmt in formats
            )

            return has_video

        except Exception as e:
            debug(f"Warning: Could not check video availability: {e}", level="WARN")
            # On error, assume video exists (let yt-dlp handle it)
            return True

    def _download_options(self):
        """Settings for a download, read on the Tk thread (the download thread must not touch Tk)."""
        return {"video": self.download_type.get() == "video",
                "album": self.album_entry.get().strip(),
                "number": bool(self.number_tracks_var.get())}

    def download_music(self, url, item_id=None, opts=None, run_id=None):
        """Download music from URL (runs in a background thread).

        item_id: the queue item (None = single download). run_id: the run this belongs to;
        once it is cancelled (or a new run started) this thread reports nothing more."""
        if opts is None:
            opts = self._download_options()
        if run_id is None:
            run_id = self._run_id
        queue_index = 0 if item_id is not None else -1   # >= 0 means "queue item" below
        current = lambda: self._run_id == run_id and self.downloading

        def report(kind, data):
            if not current():
                return
            if kind in ("queue_success", "queue_failed"):
                data = (run_id, item_id)
            self.message_queue.put((kind, data))
        os.makedirs(self.output_dir, exist_ok=True)
        ytdlp_path = self.get_yt_dlp_path()

        if not shutil.which(ytdlp_path) and not os.path.exists(ytdlp_path):
            if queue_index >= 0:
                report("queue_failed", None)
            else:
                # Show appropriate message based on whether app is bundled
                if getattr(sys, 'frozen', False) or IS_FLATPAK:
                    error_msg = ("yt-dlp not found!\n\n"
                                "The application may be corrupted.\n"
                                "Please reinstall the application to fix this issue.")
                else:
                    error_msg = ("yt-dlp not found!\n\n"
                                "Please install it with:\n"
                                "pip3 install -U yt-dlp")
                report("error", error_msg)
                report("reset", None)
            return

        # Check if video mode is selected but URL has no video
        if opts["video"]:
            self.run_in_ui(self.progress_label.configure, text="Checking video availability...")
            has_video = self.check_has_video(url)

            if not has_video:
                # Audio-only content - prevent download
                error_msg = "This URL has no video.\nPlease select 'Audio' mode."
                if queue_index >= 0:
                    report("queue_failed", None)
                    report("error", error_msg)
                else:
                    report("error", error_msg)
                    report("reset", None)
                return

        album_name = opts["album"]
        download_dir = self.get_album_folder(self.output_dir, album_name)

        # Build yt-dlp command from config
        is_audio = not opts["video"]
        command = self.build_ytdlp_command(url, download_dir, is_audio=is_audio)
        numbering = opts["number"]
        try:
            existed_before = set(os.listdir(download_dir))
        except OSError:
            existed_before = set()
        # Videos already saved in this folder (also after numbering renamed them) are skipped:
        # yt-dlp gets them as a download archive, built fresh from the folder's record.
        tracks = load_track_map(download_dir)
        archive_fd, archive_path = tempfile.mkstemp(prefix="mdj-archive-", suffix=".txt")
        with os.fdopen(archive_fd, "w", encoding="utf-8") as f:
            f.writelines(key + "\n" for key in tracks)
        # yt-dlp prints every file it saves (also one it skipped because the file was already
        # there), so we know exactly which files a link made, in order (playlists too).
        # Put first, so Custom arguments can still override --download-archive.
        command[1:1] = ["--download-archive", archive_path, "--print", SAVED_PRINT]
        debug(f"yt-dlp command: {' '.join(command)}")

        try:
            if not current():                   # cancelled while checking the URL
                return
            self.run_in_ui(self.progress_label.configure, text="Downloading...")
            # Own process group, so Cancel can stop yt-dlp *and* the ffmpeg it starts
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                start_new_session=True
            )
            self.download_process = proc
            if not current():                   # cancelled just now
                self._stop_process(proc)
            stdout, stderr = proc.communicate()

            if not current():
                return

            # Files this link saved. Handled even when yt-dlp reports an error: in a playlist
            # it skips an unavailable video, saves the others and only then exits with an error.
            folder = os.path.realpath(download_dir)
            saved = [(key, path) for key, path in parse_saved_lines(stdout)
                     if os.path.isabs(path) and os.path.isfile(path)
                     and os.path.dirname(os.path.realpath(path)) == folder]
            new_files = 0
            for key, path in saved:
                name = os.path.basename(path)
                if name not in existed_before:
                    new_files += 1
                if numbering:
                    try:
                        path, what = number_downloaded_file(path, name in existed_before)
                        debug(f"Track numbering: {what}: {path}")
                        if what == "duplicate":
                            new_files -= 1
                    except OSError as e:
                        debug(f"Warning: Could not number {path}: {e}", level="WARN")
                tracks[key] = os.path.basename(path)
            if saved:
                try:
                    save_track_map(download_dir, tracks)
                except OSError as e:
                    debug(f"Warning: Could not save the track record: {e}", level="WARN")
            if saved and safe_folder_name(album_name or ""):
                try:
                    write_album_playlist(download_dir)
                except OSError as e:
                    debug(f"Warning: Could not write the playlist: {e}", level="WARN")

            if proc.returncode != 0:
                # Parse error and show user-friendly message instead of raw stderr
                error_message = self.parse_error_message(stderr)
                if saved:
                    error_message += (f"\n\nThe other {len(saved)} file(s) from this link were "
                                      "saved. Retry to try the missing ones again.")
                    if queue_index >= 0 and download_dir not in self._queue_saved_dirs:
                        self._queue_saved_dirs.append(download_dir)
                if queue_index >= 0:
                    report("queue_failed", None)
                else:
                    report("error", error_message)
            else:
                if queue_index >= 0:
                    if download_dir not in self._queue_saved_dirs:
                        self._queue_saved_dirs.append(download_dir)
                    report("queue_success", None)
                elif new_files <= 0:
                    report("already", download_dir)     # everything was already in the folder
                else:
                    report("success", download_dir)
        except Exception as error:
            if self.downloading:
                if queue_index >= 0:
                    report("queue_failed", None)
                else:
                    report("error", str(error))
        finally:
            try:
                os.remove(archive_path)
            except OSError:
                pass
            if self.download_process is not None and self.download_process is locals().get("proc"):
                self.download_process = None
            if queue_index < 0 and current():
                self.downloading = False
                self.message_queue.put(("reset", None))

    def reset_ui(self, keep_status=False):
        """Reset UI after download completes/cancels (keep_status: leave the final result message visible)"""
        self.downloading = False
        self._set_remove_buttons(True)
        self.current_download_index = -1  # Reset queue index
        self.cancel_button.pack_forget()

        # Update button text based on current queue state BEFORE packing
        self.update_download_button_text()

        self.download_button.pack(fill="x", expand=True)

        self.url_entry.configure(state="normal")
        self.paste_button.configure(state="normal")
        self.audio_button.configure(state="normal")
        self.video_button.configure(state="normal")
        self.queue_button.configure(state="normal")
        self.album_entry.configure(state="normal")
        self.number_tracks_checkbox.configure(state="normal")
        self.clear_queue_btn.configure(state="normal")
        self.save_queue_btn.configure(state="normal")
        self.load_queue_btn.configure(state="normal")
        self.progress_frame.pack_forget()
        if not keep_status:
            self.status_label.configure(text="")  # Clear old status messages

    def open_support_page(self):
        """Open Ko-fi support page in browser"""
        ko_fi_url = "https://ko-fi.com/mdj_musicdl"
        try:
            if not open_with_system(ko_fi_url):
                webbrowser.open(ko_fi_url)
            TooltipNotification(self.root, "Opening support page in browser...")
        except Exception as e:
            TooltipNotification(self.root, f"Could not open browser: {e}")

    def after_shown(self, win, fn):
        """Run fn once win is on screen and painted, so the user sees the window
        (with its "Loading..." text) before slow work starts."""
        done = []

        def run():
            if not win.winfo_exists():
                return
            # Tk runs timers before idle redraws, so draw the window now; otherwise the
            # slow work starts first and the user sees an empty grey window.
            win.update_idletasks()
            win.after(40, lambda: win.winfo_exists() and fn())

        def go(*_):
            if not done:
                done.append(True)
                win.after(20, run)
        if win.winfo_ismapped():        # center_dialog() usually maps it already
            go()
        else:
            win.bind("<Map>", go, add="+")
            win.bind("<Expose>", go, add="+")   # Map is not always reported for toplevels
            win.after(400, go)          # in case neither event arrives

    def _ytdlp_cache_key(self):
        path = self.get_yt_dlp_path()
        try:
            return (path, os.path.getmtime(path))
        except OSError:
            return (path, None)

    def fetch_supported_sites(self, callback=None):
        """Get yt-dlp's site list in a background thread (takes 1-5 s); cached afterwards.

        callback(sites, error) runs on the Tk thread. The list is re-read after yt-dlp is updated."""
        key = self._ytdlp_cache_key()
        cache = getattr(self, "_sites_cache", None)
        if cache and cache[0] == key:
            if callback:
                callback(cache[1], None)
            return
        waiting = getattr(self, "_sites_waiting", None)
        if waiting is not None:             # a fetch is already running: just wait for it
            if callback:
                waiting.append(callback)
            return
        self._sites_waiting = [callback] if callback else []

        def worker():
            sites, error = None, None
            try:
                r = subprocess.run([key[0], "--extractor-descriptions"],
                                   capture_output=True, text=True, timeout=60)
                sites = [line for line in r.stdout.splitlines() if line.strip()]
                if not sites:
                    error = (r.stderr.strip().splitlines() or ["yt-dlp returned no sites"])[-1]
            except Exception as ex:          # not found, timed out, ...
                error = str(ex)

            def deliver():
                if sites:
                    self._sites_cache = (key, sites)
                callbacks, self._sites_waiting = self._sites_waiting, None
                for cb in callbacks:
                    cb(sites, error)
            self.run_in_ui(deliver)
        threading.Thread(target=worker, daemon=True).start()

    def show_supported_sites(self):
        win = getattr(self, "_sites_window", None)
        if win is not None and win.winfo_exists():      # already open: bring it to the front
            win.deiconify(); win.lift(); win.focus_force()
            return

        sites_window = ctk.CTkToplevel(self.root)
        self._sites_window = sites_window
        sites_window.title("Supported Sites")
        self.center_dialog(sites_window, 500, 500)

        frame = ctk.CTkFrame(sites_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        title = ctk.CTkLabel(frame, text="Supported Sites", font=ctk.CTkFont(size=20))
        title.pack(pady=(10, 15))

        search_label = ctk.CTkLabel(frame, text="Search:", font=ctk.CTkFont(size=13))
        search_label.pack(anchor="w", padx=20, pady=(0, 5))

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(frame, textvariable=search_var,
                                    placeholder_text="Type to filter...", height=35)
        search_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Shown while yt-dlp is listing the sites
        loading = ctk.CTkFrame(frame, fg_color="transparent")
        loading.pack(expand=True, fill="both", padx=20, pady=(0, 10))
        loading_label = ctk.CTkLabel(loading, text="Loading supported sites...",
                                     font=ctk.CTkFont(size=13))
        loading_label.pack(pady=(110, 10))
        loading_bar = ctk.CTkProgressBar(loading, mode="indeterminate", width=220)
        loading_bar.pack()
        loading_bar.start()

        close_btn = ctk.CTkButton(frame, text="Close", command=sites_window.destroy, height=35)
        close_btn.pack(side="bottom", pady=(0, 10), padx=20, fill="x")

        def show_list(sites, error):
            if not sites_window.winfo_exists():
                return
            loading_bar.stop()
            if error:
                loading_bar.pack_forget()
                loading_label.configure(text=f"Could not load the list of sites.\n\n{error}",
                                        text_color="#f44336", wraplength=380)
                return
            loading.destroy()
            text_area = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=12))
            count_label = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11),
                                       text_color=("#666666", "#888888"))

            def update_text_area(*_):
                term = search_var.get().lower()
                shown = [x for x in sites if term in x.lower()]
                text_area.configure(state="normal")
                text_area.delete("1.0", "end")
                text_area.insert("1.0", "\n".join(shown))     # one insert: fast
                text_area.configure(state="disabled")
                count_label.configure(text=f"{len(shown)} of {len(sites)} sites" if term
                                      else f"{len(sites)} sites")
            search_var.trace_add("write", update_text_area)
            update_text_area()                  # fill before showing (faster)
            count_label.pack(before=close_btn, side="bottom", pady=(0, 6))
            text_area.pack(expand=True, fill="both", padx=20, pady=(0, 10))

        # Let the window appear first, then fill it (instantly if the list is cached)
        self.after_shown(sites_window, lambda: self.fetch_supported_sites(show_list))

    CUSTOM_ARGS_HELP = (
        "How to add an option (this help disappears when you click here):\n"
        "  1. Find the option in \"All yt-dlp options\" (link below).\n"
        "  2. Type it on its own line, with its value after a space.\n"
        "  3. Click Check to make sure yt-dlp accepts it, then Save.\n"
        "\n"
        "Examples (text after # is a note and is ignored):\n"
        "  --embed-chapters                # chapter marks in videos\n"
        "  --limit-rate 2M                 # max 2 MB/s download speed\n"
        "  --sponsorblock-remove sponsor   # cut sponsor segments\n"
        "  --sub-langs en --embed-subs     # English subtitles in videos"
    )

    def show_ytdlp_settings(self):
        """yt-dlp settings: common choices on the Basic tab, any yt-dlp option on the Advanced tab."""
        win = getattr(self, "_settings_window", None)
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_force()
            return
        settings_window = ctk.CTkToplevel(self.root)
        self._settings_window = settings_window
        settings_window.title("yt-dlp Settings")

        # As tall as fits on the monitor (the old fixed 600 px cut the bottom off on small screens)
        try:
            scale = ctk.ScalingTracker.get_window_scaling(self.root)
        except Exception:
            scale = 1.0
        mon = monitor_at_pointer(self.root)
        screen_h = mon[3] if mon else self.root.winfo_screenheight()
        height = max(420, min(760, int(screen_h / scale) - 100))
        self.center_dialog(settings_window, 720, height)
        settings_window.minsize(560, 400)

        frame = ctk.CTkFrame(settings_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=12, pady=12)

        muted = ("#666666", "#8a949c")
        ctk.CTkLabel(frame, text="⚙ yt-dlp Settings",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(10, 0))
        ctk.CTkLabel(frame, text="Basic: everyday choices.   Advanced: any other yt-dlp option.",
                     font=ctk.CTkFont(size=11), text_color=muted).pack(pady=(0, 2))

        # Show the window straight away with "Loading...", then build the (slow) rest
        loading = ctk.CTkLabel(frame, text="Loading settings...", font=ctk.CTkFont(size=13),
                               text_color=muted)
        loading.pack(expand=True)

        def build_rest():
            if not settings_window.winfo_exists():
                return
            loading.destroy()
            cfg = self.ytdlp_config

            tabs = ctk.CTkTabview(frame, corner_radius=10)
            basic_tab = tabs.add("Basic")
            adv_tab = tabs.add("Advanced")
            # Built first and put on screen once at the end: a scrollbar forces a full
            # redraw every time the content grows, which made this window slow to open.
            basic = ctk.CTkScrollableFrame(basic_tab, fg_color="transparent")
            adv = ctk.CTkScrollableFrame(adv_tab, fg_color="transparent")
            enable_wheel_scrolling(basic)
            enable_wheel_scrolling(adv)

            def section(parent, text, top=10):
                ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=13, weight="bold"),
                             anchor="w").pack(fill="x", pady=(top, 4))

            def hint(parent, text, pady=(2, 6)):
                lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=11), text_color=muted,
                                   anchor="w", justify="left", wraplength=600)
                lbl.pack(fill="x", pady=pady)
                return lbl

            controls = {}       # basic setting -> (widget, note label)

            def add_note(r, key, w):
                note = ctk.CTkLabel(r, text="", font=ctk.CTkFont(size=11), text_color="#f0a04b",
                                    anchor="w", justify="left", wraplength=280)
                note.pack(side="left", padx=(10, 0))
                controls[key] = (w, note)

            def row(parent, label, make, key=None):
                r = ctk.CTkFrame(parent, fg_color="transparent")
                r.pack(fill="x", pady=3)
                ctk.CTkLabel(r, text=label, width=120, anchor="w",
                             font=ctk.CTkFont(size=12)).pack(side="left", padx=(10, 0))
                w = make(r)
                w.pack(side="left")
                if key:
                    add_note(r, key, w)
                return w

            def check(parent, text, var, key):
                r = ctk.CTkFrame(parent, fg_color="transparent")
                r.pack(fill="x", pady=4)
                w = ctk.CTkCheckBox(r, text=text, variable=var, font=ctk.CTkFont(size=12))
                w.pack(side="left", padx=(10, 0))
                add_note(r, key, w)

            def link(parent, text, url):
                def go():
                    if not open_with_system(url):
                        webbrowser.open(url)
                    TooltipNotification(self.root, "Opening in your browser...")
                return ctk.CTkButton(parent, text=text, command=go, height=28, width=10,
                                     font=ctk.CTkFont(size=12), fg_color="transparent",
                                     border_width=1, text_color=ACCENT_FG, hover_color=ACCENT_DIM)

            # ---------------- Basic tab ----------------
            section(basic, "Audio downloads", top=4)
            fmt = cfg.get("audio_format", "mp3")
            audio_fmt_var = ctk.StringVar(value=fmt if fmt in AUDIO_FORMATS else "mp3")
            row(basic, "Format", lambda p: ctk.CTkOptionMenu(
                p, values=AUDIO_FORMATS, variable=audio_fmt_var, width=220), "audio_format")
            q_by_value = {v: lbl for lbl, v in AUDIO_QUALITIES}
            audio_q_var = ctk.StringVar(value=q_by_value.get(str(cfg.get("audio_quality", "0")),
                                                             AUDIO_QUALITIES[0][0]))
            row(basic, "Quality", lambda p: ctk.CTkOptionMenu(
                p, values=[lbl for lbl, _ in AUDIO_QUALITIES], variable=audio_q_var, width=220),
                "audio_quality")
            hint(basic, "mp3 plays everywhere; m4a and opus are smaller at the same quality. "
                        "flac and wav are lossless (bigger files; Quality does not apply).")

            section(basic, "Video downloads")
            preset_labels = [lbl for lbl, _ in VIDEO_PRESETS]

            def preset_label_for(fmt_code):
                for lbl, code in VIDEO_PRESETS:
                    if code == fmt_code.strip():
                        return lbl
                return VIDEO_CUSTOM_LABEL

            video_var = ctk.StringVar(value=preset_label_for(cfg.get("video_quality", "")
                                                             or DEFAULT_VIDEO_FORMAT))

            def on_video_preset(label):
                for lbl, code in VIDEO_PRESETS:
                    if lbl == label:
                        video_entry.delete(0, "end")
                        video_entry.insert(0, code)
                        schedule_refresh()
                        return
                tabs.set("Advanced")        # "Custom": the format code is edited there
                video_entry.focus_set()

            row(basic, "Quality", lambda p: ctk.CTkOptionMenu(
                p, values=preset_labels + [VIDEO_CUSTOM_LABEL], variable=video_var,
                width=220, command=on_video_preset), "video_quality")
            hint(basic, "Downloads the best MP4 up to this size. Lower sizes download faster "
                        "and use less space.")

            section(basic, "Extras")
            thumb_var = ctk.BooleanVar(value=bool(cfg.get("embed_thumbnail")))
            meta_var = ctk.BooleanVar(value=bool(cfg.get("embed_metadata")))
            check(basic, "Add cover art (the video thumbnail) to the file", thumb_var, "embed_thumbnail")
            check(basic, "Add title, artist and date tags", meta_var, "embed_metadata")

            cookies_var = ctk.StringVar(value=cfg.get("cookies_browser") or "Off")
            if not IS_FLATPAK:              # the Flatpak sandbox can't read browser profiles
                section(basic, "Sign-in (cookies)")
                row(basic, "Browser", lambda p: ctk.CTkOptionMenu(
                    p, values=["Off"] + COOKIE_BROWSERS, variable=cookies_var, width=220),
                    "cookies_browser")
                hint(basic, "Only needed when a download fails with \"Sign in to confirm\" or for "
                            "age-restricted / members-only videos: yt-dlp then uses your browser's "
                            "YouTube login. Close that browser before downloading.")

            # ---------------- Advanced tab ----------------
            section(adv, "Custom arguments", top=4)
            hint(adv, "Added to every download. Write each option the same way as on the yt-dlp "
                      "command line, one option per line.", pady=(0, 4))

            custom_text = ctk.CTkTextbox(adv, height=180, wrap="none", activate_scrollbars=False,
                                         font=ctk.CTkFont(family="Monospace", size=12))
            custom_text.pack(fill="x", pady=(0, 4))
            custom_text.tag_config("help", foreground="#7d8790")
            placeholder = {"on": False}

            def show_help():
                if not custom_text.get("1.0", "end").strip():
                    custom_text.delete("1.0", "end")
                    custom_text.insert("1.0", self.CUSTOM_ARGS_HELP, "help")
                    placeholder["on"] = True

            def hide_help(*_):
                if placeholder["on"]:
                    custom_text.delete("1.0", "end")
                    placeholder["on"] = False

            def custom_value():
                return "" if placeholder["on"] else custom_text.get("1.0", "end")

            custom_text.insert("1.0", args_to_text(cfg.get("custom_args", [])))
            show_help()
            custom_text.bind("<FocusIn>", hide_help)
            custom_text.bind("<FocusOut>", lambda e: show_help())

            check_row = ctk.CTkFrame(adv, fg_color="transparent")
            check_row.pack(fill="x", pady=(2, 0))
            check_btn = ctk.CTkButton(check_row, text="Check", width=80, height=28,
                                      font=ctk.CTkFont(size=12), fg_color=ACCENT,
                                      hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT)
            check_btn.pack(side="left")
            link(check_row, "All yt-dlp options ↗", YTDLP_OPTIONS_URL).pack(side="right")
            link(check_row, "Format codes guide ↗", YTDLP_FORMAT_URL).pack(side="right", padx=6)
            status = ctk.CTkLabel(adv, text="", font=ctk.CTkFont(size=12), anchor="w",
                                  justify="left", wraplength=600)
            status.pack(fill="x", pady=(2, 0))
            hint(adv, "Both tabs are used together: Basic first, then these options. If an option "
                      "here changes a Basic setting (like --audio-format flac), this one is used and "
                      "that Basic setting is locked until you remove the line. The folder and file "
                      "name (-o) are always set by the app.")

            section(adv, "What the app will run")
            mode_var = ctk.StringVar(value="Audio")
            ctk.CTkSegmentedButton(adv, values=["Audio", "Video"], variable=mode_var,
                                   command=lambda v: refresh()).pack(anchor="w", pady=(0, 4))
            preview = ctk.CTkTextbox(adv, height=96, wrap="word", activate_scrollbars=False,
                                     font=ctk.CTkFont(family="Monospace", size=11))
            preview.pack(fill="x")
            preview.tag_config("custom", foreground=ACCENT_FG)
            hint(adv, "Updates as you change either tab. Your custom arguments are highlighted.")

            section(adv, "Video format code (-f)")
            video_entry = ctk.CTkEntry(adv, font=ctk.CTkFont(family="Monospace", size=11))
            video_entry.pack(fill="x")
            video_entry.insert(0, cfg.get("video_quality", "") or DEFAULT_VIDEO_FORMAT)
            hint(adv, "Set by Video → Quality on the Basic tab. Change it here only if you know "
                      "yt-dlp format codes (see \"Format codes guide\").")

            section(adv, "Common arguments")
            common_text = ctk.CTkTextbox(adv, height=56, wrap="none", activate_scrollbars=False,
                                         font=ctk.CTkFont(family="Monospace", size=12))
            common_text.pack(fill="x")
            common_text.insert("1.0", args_to_text(cfg.get("common_args", [])))
            hint(adv, "Added before all other options. Keep --ignore-config, so a yt-dlp config "
                      "file elsewhere on this computer can't change how the app downloads.")

            def dialog_cfg(common, custom):
                """The config as currently shown in the window (used by preview and Save)."""
                c = dict(self.ytdlp_config)
                c["audio_format"] = audio_fmt_var.get()
                c["audio_quality"] = dict(AUDIO_QUALITIES).get(audio_q_var.get(), "0")
                c["video_quality"] = video_entry.get().strip() or DEFAULT_VIDEO_FORMAT
                c["embed_thumbnail"] = bool(thumb_var.get())
                c["embed_metadata"] = bool(meta_var.get())
                if not IS_FLATPAK:
                    browser = cookies_var.get()
                    c["cookies_browser"] = "" if browser == "Off" else browser
                c["custom_args"] = custom
                c["common_args"] = common or ["--ignore-config"]
                return c

            pending = {"id": None}

            def refresh():
                pending["id"] = None
                if not settings_window.winfo_exists():
                    return
                common, custom, err = read_args()
                if err:
                    common = common or []
                    custom = []
                # Basic: lock what Custom arguments replace, and say so
                over = overridden_settings(custom)
                for key, (w, note) in controls.items():
                    if key in over:
                        w.configure(state="disabled")
                        note.configure(text="← set by Custom arguments: " + over[key])
                    else:
                        w.configure(state="normal")
                        note.configure(text="")
                # Advanced: the full command, with the custom part highlighted
                c = dialog_cfg(common or [], [])
                base = self.build_ytdlp_command("<link>", "<Output Folder>", mode_var.get() == "Audio",
                                                cfg=c, ytdlp_path="yt-dlp")
                k = base.index("-o")
                preview.configure(state="normal")
                preview.delete("1.0", "end")
                preview.insert("end", shlex.join(base[:k]) + " ")
                if err:
                    preview.insert("end", "(custom arguments have an error) ", "custom")
                elif custom:
                    preview.insert("end", shlex.join(custom) + " ", "custom")
                preview.insert("end", shlex.join(base[k:]))
                preview.configure(state="disabled")

            def schedule_refresh(*_):
                if pending["id"] is None and settings_window.winfo_exists():
                    pending["id"] = settings_window.after(250, refresh)

            for var in (audio_fmt_var, audio_q_var, thumb_var, meta_var, cookies_var):
                var.trace_add("write", schedule_refresh)
            for box in (custom_text, common_text, video_entry):
                box.bind("<KeyRelease>", schedule_refresh, add="+")

            def on_tab_change():
                if tabs.get() == "Basic":    # the format code may have been edited by hand
                    video_var.set(preset_label_for(video_entry.get() or DEFAULT_VIDEO_FORMAT))
                refresh()
            tabs.configure(command=on_tab_change)

            # ---------------- Checking and saving ----------------
            def show_status(ok, text):
                if settings_window.winfo_exists():
                    status.configure(text=text, text_color=(ACCENT_FG if ok else "#ff6b6b"))

            def read_args():
                """(common, custom, error) from the two text boxes."""
                custom, err = parse_args_text(custom_value())
                if err:
                    return None, None, "Custom arguments: " + err
                common, err = parse_args_text(common_text.get("1.0", "end"))
                if err:
                    return None, None, "Common arguments: " + err
                return common, custom, None

            def check_args(args, done):
                """Ask yt-dlp whether it accepts args (without downloading); done(ok, message)."""
                def work():
                    path = self.get_yt_dlp_path()
                    if not path:
                        self.run_in_ui(done, None, "yt-dlp not found, options not checked")
                        return
                    if any(a in ("-U", "--update", "--update-to") or a.startswith("--update-to=")
                           for a in args):
                        self.run_in_ui(done, False, "✗ Remove -U / --update: it would try to "
                                       "update yt-dlp on every download")
                        return
                    try:
                        # Run without a URL: yt-dlp checks every option, then stops with
                        # "You must provide at least one URL" when they are all fine
                        r = subprocess.run([path] + args, capture_output=True, text=True,
                                           timeout=30, stdin=subprocess.DEVNULL)
                    except Exception as e:
                        self.run_in_ui(done, None, f"Could not run yt-dlp: {e}")
                        return
                    if "provide at least one url" in r.stderr.lower():
                        self.run_in_ui(done, True, "✓ yt-dlp accepts these options")
                        return
                    if r.returncode == 0:   # e.g. --version / --help: prints and exits
                        self.run_in_ui(done, False, "✗ One of these options makes yt-dlp stop "
                                       "without downloading anything (like --version or --help)")
                        return
                    lines = [l for l in r.stderr.splitlines() if l.strip()]
                    msg = next((l for l in lines if "error:" in l.lower()), lines[-1] if lines else "")
                    msg = re.sub(r"^.*?error:\s*", "", msg, flags=re.I) or "unknown error"
                    self.run_in_ui(done, False, "✗ yt-dlp: " + msg[:300])
                threading.Thread(target=work, daemon=True).start()

            def on_check():
                common, custom, err = read_args()
                if err:
                    show_status(False, "✗ " + err)
                    return
                check_btn.configure(state="disabled", text="...")
                show_status(True, "Checking...")

                def done(ok, msg):
                    if settings_window.winfo_exists():
                        check_btn.configure(state="normal", text="Check")
                        show_status(ok is not False, msg)
                check_args(common + custom, done)
            check_btn.configure(command=on_check)

            def apply(common, custom):
                self.ytdlp_config = dialog_cfg(common, custom)
                self.save_config()
                self.update_type_summary()
                settings_window.destroy()
                TooltipNotification(self.root, "✓ Settings saved", 2000)

            def save_settings():
                common, custom, err = read_args()
                if err:
                    tabs.set("Advanced")
                    show_status(False, "✗ " + err)
                    return
                if not custom and common == normalize_args(cfg.get("common_args", [])):
                    apply(common, custom)       # nothing typed that needs checking
                    return
                save_btn.configure(state="disabled", text="Checking...")

                def done(ok, msg):
                    if not settings_window.winfo_exists():
                        return
                    if ok is False:             # don't save options that would break every download
                        save_btn.configure(state="normal", text="Save Settings")
                        tabs.set("Advanced")
                        show_status(False, msg + "\nFix it (or remove it), then Save again.")
                    else:
                        apply(common, custom)
                check_args(common + custom, done)

            def reset_defaults():
                if messagebox.askyesno("Reset Settings", "Reset all yt-dlp settings to defaults?",
                                       parent=settings_window):
                    self.ytdlp_config = self.get_default_ytdlp_config()
                    self.save_config()
                    self.update_type_summary()
                    settings_window.destroy()
                    TooltipNotification(self.root, "✓ Settings reset to defaults", 2000)

            # Buttons: one row, always visible below the tabs
            button_frame = ctk.CTkFrame(frame, fg_color="transparent")
            button_frame.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
            ctk.CTkButton(button_frame, text="Reset to Defaults", command=reset_defaults, height=35,
                          fg_color="#8B4545", hover_color="#6B3535",
                          text_color=LIGHT_TEXT).pack(side="left", expand=True, fill="x", padx=(0, 5))
            ctk.CTkButton(button_frame, text="Cancel", command=settings_window.destroy, height=35,
                          fg_color="transparent", border_width=1, text_color=LIGHT_TEXT,
                          hover_color=ACCENT_DIM).pack(side="left", expand=True, fill="x", padx=5)
            save_btn = ctk.CTkButton(button_frame, text="Save Settings", command=save_settings,
                                     height=35, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                     text_color=ACCENT_TEXT)
            save_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

            basic.pack(expand=True, fill="both")
            adv.pack(expand=True, fill="both")
            tabs.pack(expand=True, fill="both", padx=12, pady=(0, 8))
            refresh()                       # lock overridden Basic settings, fill the preview

        self.after_shown(settings_window, build_rest)

    def update_ytdlp(self):
        """Update yt-dlp to the latest version"""
        if IS_FLATPAK:          # never download code in the Flatpak (button is hidden there too)
            return
        # Create update dialog
        update_window = ctk.CTkToplevel(self.root)
        update_window.title("Update yt-dlp")
        self.center_dialog(update_window, 500, 360)
        update_window.attributes('-topmost', True)

        frame = ctk.CTkFrame(update_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        title = ctk.CTkLabel(
            frame,
            text="Update yt-dlp",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(15, 10))

        info_label = ctk.CTkLabel(
            frame,
            text=("Downloads the latest yt-dlp.\n"
                  "With an administrator password it is updated for all users;\n"
                  "otherwise it is updated just for your account."),
            font=ctk.CTkFont(size=12),
            wraplength=400
        )
        info_label.pack(pady=(0, 15))

        status_label = ctk.CTkLabel(
            frame,
            text="Ready to update...",
            font=ctk.CTkFont(size=11),
            wraplength=400
        )
        status_label.pack(pady=(0, 10))

        progress = ctk.CTkProgressBar(frame)
        progress.pack(fill="x", padx=20, pady=(0, 15))
        progress.set(0)

        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 15))

        def do_update():
            update_btn.configure(state="disabled")
            cancel_btn.configure(text="Close", state="disabled")

            def update_thread():
                ui = self.run_in_ui
                status = lambda text, color=None: ui(lambda: status_label.configure(
                    text=text, **({"text_color": color} if color else {})))
                finish = lambda: ui(lambda: cancel_btn.configure(text="Close", state="normal"))
                tmp_dir = None
                try:
                    status("Downloading latest yt-dlp...")
                    ui(lambda: progress.set(0.3))

                    # Download into a private temp folder owned by this user. (A fixed name like
                    # /tmp/yt-dlp-latest breaks on shared computers: another user's file can't be overwritten.)
                    cache_root = os.path.join(
                        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "mdj-music-downloader")
                    os.makedirs(cache_root, exist_ok=True)
                    tmp_dir = tempfile.mkdtemp(prefix="update-", dir=cache_root)
                    temp_path = os.path.join(tmp_dir, "yt-dlp")
                    result = subprocess.run(
                        # yt-dlp_linux = standalone build with its own Python (the plain "yt-dlp"
                        # zipapp needs the system Python to be 3.11+, which Ubuntu 22.04/Mint 21 lack)
                        ["curl", "-fsSL", "--retry", "2", YTDLP_DOWNLOAD_URL, "-o", temp_path],
                        capture_output=True, text=True, timeout=600)
                    if result.returncode != 0:
                        debug(f"yt-dlp download failed: {result.stderr}", level="ERROR")
                        status("✖ Download failed! Check your internet connection.", "red")
                        return finish()

                    ui(lambda: progress.set(0.6))
                    status("Checking downloaded yt-dlp...")
                    os.chmod(temp_path, 0o755)
                    new_vt, new_vs = get_ytdlp_version(temp_path, timeout=60)
                    if new_vt is None:
                        status("✖ Downloaded yt-dlp does not run. Please try again later.", "red")
                        return finish()

                    # Nothing to do if the copy in use is already this version or newer
                    cur_path, cur_vs = self._resolve_ytdlp()
                    cur_vt = parse_ytdlp_version(cur_vs)
                    if cur_vt is not None and cur_vt >= new_vt:
                        ui(lambda: progress.set(1.0))
                        status(f"✓ yt-dlp is already up to date ({cur_vs}).", "green")
                        return finish()

                    status("Installing yt-dlp...")
                    scope = None

                    # 1) System-wide copy next to the app (all users): needs admin rights
                    sys_path = system_ytdlp_path()
                    if sys_path and os.path.isdir(os.path.dirname(sys_path)):
                        if os.access(os.path.dirname(sys_path), os.W_OK):
                            shutil.copyfile(temp_path, sys_path + ".new")
                            os.chmod(sys_path + ".new", 0o755)
                            os.replace(sys_path + ".new", sys_path)
                            scope = "all"
                        elif shutil.which("pkexec"):
                            status("Installing yt-dlp...\nEnter an administrator password to update it for all users,\nor cancel to update it just for your account.")
                            # One command = one password prompt
                            r = subprocess.run(["pkexec", "install", "-m", "755", temp_path, sys_path],
                                               capture_output=True, text=True)
                            debug(f"pkexec install returned {r.returncode}: {r.stderr.strip()}")
                            if r.returncode == 0:
                                scope = "all"

                    # 2) Fallback: this user's own copy (no password needed)
                    if scope is None:
                        os.makedirs(USER_DATA_DIR, exist_ok=True)
                        shutil.copyfile(temp_path, USER_YTDLP_PATH + ".new")
                        os.chmod(USER_YTDLP_PATH + ".new", 0o755)
                        os.replace(USER_YTDLP_PATH + ".new", USER_YTDLP_PATH)
                        scope = "user"
                    elif os.path.exists(USER_YTDLP_PATH):
                        # System copy is now newest; drop this user's older private copy
                        try:
                            os.remove(USER_YTDLP_PATH)
                        except OSError:
                            pass

                    self.invalidate_ytdlp_cache()
                    ui(lambda: progress.set(1.0))
                    if scope == "all":
                        status(f"✓ yt-dlp updated to {new_vs} for all users!", "green")
                    else:
                        status(f"✓ yt-dlp updated to {new_vs} for your account.", "green")
                    ui(lambda: self.root.after(500, self.check_ytdlp_version))
                    finish()

                except subprocess.TimeoutExpired:
                    status("✖ Download timeout! Check your internet connection.", "red")
                    finish()
                except Exception as e:
                    debug(f"yt-dlp update error: {e}", level="ERROR")
                    status(f"✖ Error: {e}", "red")
                    finish()
                finally:
                    if tmp_dir:
                        shutil.rmtree(tmp_dir, ignore_errors=True)

            threading.Thread(target=update_thread, daemon=True).start()

        update_btn = ctk.CTkButton(
            button_frame,
            text="Update Now",
            command=do_update,
            height=35,
            fg_color="#2b7a2b",
            hover_color="#3a9a3a",
            text_color=LIGHT_TEXT
        )
        update_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=update_window.destroy,
            height=35,
            fg_color="transparent",
            border_width=1,
            text_color=LIGHT_TEXT,
            hover_color=ACCENT_DIM
        )
        cancel_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def ask_path(self, kind, title, callback, initialdir=None, filetypes=None,
                 defaultextension="", initialfile=""):
        """Show the system file chooser without freezing the window; call callback(path).

        callback gets "" when the user cancels. Falls back to the Tk dialog if no
        system chooser is available or it fails to start."""
        if getattr(self, "_picker_open", False):
            return                      # a chooser is already open; ignore extra clicks
        initialdir = initialdir or self.output_dir
        # The folder may not exist yet (nothing downloaded): start in its nearest existing parent
        while initialdir and not os.path.isdir(initialdir) and os.path.dirname(initialdir) != initialdir:
            initialdir = os.path.dirname(initialdir)

        def tk_dialog():
            opts = dict(title=title, initialdir=initialdir, parent=self.root)
            if kind == "dir":
                return filedialog.askdirectory(**opts)
            if filetypes:
                opts["filetypes"] = filetypes
            if kind == "open":
                return filedialog.askopenfilename(**opts)
            return filedialog.asksaveasfilename(defaultextension=defaultextension,
                                                initialfile=initialfile, **opts)

        def finish(path):
            path = path or ""
            if path and kind == "save" and defaultextension and not os.path.splitext(path)[1]:
                path += defaultextension
            callback(path)

        try:
            xid = int(self.root.wm_frame(), 16)
        except (tk.TclError, ValueError):
            xid = None
        cmd = native_dialog_command(kind, title, initialdir, filetypes, xid, initialfile)
        proc = None
        if cmd:
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        stdin=subprocess.DEVNULL, env=external_env(), text=True)
            except OSError:
                proc = None
        if proc is None:
            finish(tk_dialog())
            return

        self._picker_open = True
        self._picker_proc = proc
        started = time.monotonic()

        def poll():
            if proc.poll() is None:
                self.root.after(100, poll)
                return
            self._picker_open = False
            out = (proc.stdout.read() or "").strip().splitlines()
            if proc.returncode == 0 and out:
                finish(out[0])
            elif proc.returncode == 1 or time.monotonic() - started > 2:
                finish("")              # user cancelled (or closed the chooser)
            else:
                finish(tk_dialog())     # chooser crashed at startup: use the Tk one
        self.root.after(100, poll)

    def change_output_dir(self):
        def chosen(new_dir):
            if new_dir:
                self.output_dir = new_dir
                self.save_output_dir()
                TooltipNotification(self.root, "✓ Output folder updated")
        self.ask_path("dir", "Select Output Folder", chosen)

    def on_closing(self):
        if self.downloading:
            confirm_window = ctk.CTkToplevel(self.root)
            confirm_window.title("Confirm Close")
            self.center_dialog(confirm_window, 380, 200)

            frame = ctk.CTkFrame(confirm_window, corner_radius=15)
            frame.pack(expand=True, fill="both", padx=15, pady=15)

            warning = ctk.CTkLabel(
                frame,
                text="Warning",
                font=ctk.CTkFont(size=18),
                text_color="#ff9800"
            )
            warning.pack(pady=(15, 10))

            msg = ctk.CTkLabel(
                frame,
                text="A download is in progress.\nAre you sure you want to close?",
                font=ctk.CTkFont(size=13),
                wraplength=320
            )
            msg.pack(pady=10)

            button_frame = ctk.CTkFrame(frame, fg_color="transparent")
            button_frame.pack(pady=(10, 15), fill="x", padx=20)

            yes_btn = ctk.CTkButton(
                button_frame,
                text="Yes, Close",
                height=35,
                fg_color="#d32f2f",
                hover_color="#b71c1c",
                command=self.close_app,
                text_color=LIGHT_TEXT
            )
            yes_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

            no_btn = ctk.CTkButton(
                button_frame,
                text="No, Continue",
                height=35,
                command=confirm_window.destroy
            )
            no_btn.pack(side="left", expand=True, fill="x")
        else:
            self.close_app()

    @staticmethod
    def _stop_process(proc, wait=1.0):
        """Stop a yt-dlp process and its children (ffmpeg): it runs in its own group.

        Waits (up to `wait` s, usually a few ms) until it has ended, and kills it if it
        has not, so a new download never runs next to one that is still stopping."""
        if proc is None or proc.poll() is not None:
            return

        def send(sig):
            try:
                os.killpg(proc.pid, sig)
            except Exception:
                try:
                    proc.send_signal(sig)
                except Exception:
                    pass
        send(signal.SIGTERM)
        try:
            proc.wait(timeout=wait)
        except Exception:
            send(signal.SIGKILL)

    def close_app(self):
        """Close the app. Always works: if destroying the window fails, exit anyway."""
        self._run_id += 1                   # nothing may report back any more
        self._stop_process(getattr(self, "download_process", None))   # don't leave yt-dlp running
        try:
            self.root.destroy()
        except Exception as e:
            log_error(f"Closing the window failed: {e!r}")
            os._exit(0)

    def show_error_dialog(self, title, message):
        error_window = ctk.CTkToplevel(self.root)
        error_window.title(title)
        self.center_dialog(error_window, 450, 300)

        frame = ctk.CTkFrame(error_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        error_title = ctk.CTkLabel(
            frame,
            text="Error",
            font=ctk.CTkFont(size=20),
            text_color="#f44336"
        )
        error_title.pack(pady=(15, 10))

        text_frame = ctk.CTkFrame(frame, fg_color="transparent")
        text_frame.pack(expand=True, fill="both", padx=20, pady=(0, 10))

        text_area = ctk.CTkTextbox(
            text_frame,
            wrap="word",
            font=ctk.CTkFont(size=12),
            height=150
        )
        text_area.pack(expand=True, fill="both")
        text_area.insert("1.0", message)
        text_area.configure(state="disabled")

        ok_btn = ctk.CTkButton(
            frame,
            text="OK",
            height=40,
            command=error_window.destroy,
            font=ctk.CTkFont(size=14)
        )
        ok_btn.pack(pady=(10, 15), padx=20, fill="x")


def resource_path(*parts):
    """Path to a bundled resource (works from source and from a PyInstaller build)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def set_window_icon(root):
    """Set the window/taskbar icon from icons/ (several sizes so the WM can pick)."""
    try:
        import tkinter as tk
        images = []
        # Keep sizes <= 128px: larger images exceed the X11 property limit and the icon is dropped
        for size in (128, 64, 48, 32):
            path = resource_path("icons", f"mdj-music-downloader-{size}.png")
            if os.path.exists(path):
                images.append(tk.PhotoImage(file=path))
        if images:
            root.iconphoto(True, *images)
            root._icon_images = images  # keep references alive
    except Exception as e:
        debug(f"Could not set window icon: {e}", level="WARNING")


ERROR_LOG = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
                         "mdj-music-downloader", "errors.log")


def log_error(text):
    """Append an error to ERROR_LOG (kept small). The installed app has no console, so
    without this, errors in button handlers etc. would be lost."""
    try:
        os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
        if os.path.exists(ERROR_LOG) and os.path.getsize(ERROR_LOG) > 200_000:
            os.replace(ERROR_LOG, ERROR_LOG + ".old")
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] v{APP_VERSION}\n{text.rstrip()}\n\n")
    except Exception:
        pass
    debug(text, level="ERROR")


def report_tk_error(exc, value, tb):
    """Tk callback errors: log them instead of printing to a console nobody sees."""
    import traceback
    log_error("".join(traceback.format_exception(exc, value, tb)))


def notify_startup_complete():
    """Tell the desktop the app has finished starting, so the busy cursor stops.

    The menu entry has StartupNotify=true: the desktop shows a busy cursor and passes
    DESKTOP_STARTUP_ID; the app must answer with a freedesktop startup-notification
    "remove" message. GTK/Qt do this automatically, Tk does not, so send it via Xlib."""
    startup_id = os.environ.pop("DESKTOP_STARTUP_ID", None)   # not for child programs
    if not startup_id:
        return
    try:
        import ctypes
        import ctypes.util

        class ClientData(ctypes.Union):   # union { char b[20]; short s[10]; long l[5]; }
            _fields_ = [("b", ctypes.c_char * 20), ("l", ctypes.c_long * 5)]

        class XClientMessageEvent(ctypes.Structure):
            _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                        ("send_event", ctypes.c_int), ("display", ctypes.c_void_p),
                        ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                        ("format", ctypes.c_int), ("data", ClientData)]

        class XEvent(ctypes.Union):
            _fields_ = [("xclient", XClientMessageEvent), ("pad", ctypes.c_long * 24)]

        x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XCreateSimpleWindow.restype = ctypes.c_ulong
        x11.XCreateSimpleWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong] + [ctypes.c_int] * 4 + [ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
        x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.POINTER(XEvent)]
        x11.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

        dpy = x11.XOpenDisplay(None)
        if not dpy:
            return
        try:
            root_win = x11.XDefaultRootWindow(dpy)
            sender = x11.XCreateSimpleWindow(dpy, root_win, -100, -100, 1, 1, 0, 0, 0)
            begin = x11.XInternAtom(dpy, b"_NET_STARTUP_INFO_BEGIN", False)
            more = x11.XInternAtom(dpy, b"_NET_STARTUP_INFO", False)
            quoted = startup_id.replace("\\", "\\\\").replace('"', '\\"')
            message = f'remove: ID="{quoted}"'.encode("utf-8") + b"\0"
            for i in range(0, len(message), 20):           # sent in 20-byte pieces
                ev = XEvent()
                ev.xclient.type = 33                          # ClientMessage
                ev.xclient.send_event = 1
                ev.xclient.display = dpy
                ev.xclient.window = sender
                ev.xclient.message_type = begin if i == 0 else more
                ev.xclient.format = 8
                ev.xclient.data.b = message[i:i + 20].ljust(20, b"\0")
                x11.XSendEvent(dpy, root_win, False, 1 << 22, ctypes.byref(ev))  # PropertyChangeMask
            x11.XDestroyWindow(dpy, sender)
            x11.XFlush(dpy)
        finally:
            x11.XCloseDisplay(dpy)
        debug("Startup notification sent")
    except Exception as e:
        debug(f"Could not send startup notification: {e}", level="WARNING")


if __name__ == "__main__":
    try:
        debug("="*70)
        debug("Starting MDJ Music Downloader...")
        debug("="*70)
        root = ctk.CTk(className="mdj-music-downloader")
        root.report_callback_exception = report_tk_error
        debug("✅ Root window created")
        set_window_icon(root)
        app = MusicDownloader(root)
        debug("✅ App initialized")
        root.after_idle(notify_startup_complete)   # window is up: stop the busy cursor
        root.mainloop()
        debug("App closed normally")
    except Exception as e:
        debug(f"❌ FATAL ERROR: {e}", level="ERROR")
        import traceback
        debug(traceback.format_exc(), level="ERROR")
        input("Press Enter to exit...")
