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
import re
import tempfile
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
    """yt-dlp shipped next to the app (/opt/mdj-music-downloader/yt-dlp), or None when running from source."""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    return None

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TooltipNotification:
    def __init__(self, parent, message, duration=2000):
        self.tooltip = ctk.CTkToplevel(parent)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes('-topmost', True)

        self.label = ctk.CTkLabel(
            self.tooltip,
            text=message,
            fg_color=("#3b8ed0", "#1f6aa5"),
            corner_radius=8,
            padx=20,
            pady=10
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

    def fade_in(self, alpha=0.0):
        if alpha < 0.95:
            alpha += 0.1
            self.tooltip.attributes('-alpha', alpha)
            self.tooltip.after(30, lambda: self.fade_in(alpha))

    def fade_out(self, alpha=0.95):
        if alpha > 0:
            alpha -= 0.1
            self.tooltip.attributes('-alpha', alpha)
            self.tooltip.after(30, lambda: self.fade_out(alpha))
        else:
            self.tooltip.destroy()


class MusicDownloader:
    def __init__(self, root):
        debug("__init__ started")
        self.root = root
        self.root.title("MDJ Music Downloader")
        debug("Title set")

        # Config file - save in user's home directory for multi-user support
        config_dir = os.path.join(os.path.expanduser("~"), ".config", "mdj-music-downloader")
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
        self.download_queue = []  # List of {url, status, widget} dicts
        self.current_download_index = -1
        debug("Data structures initialized")

        # Window size - wider for two columns
        self.root.geometry("900x700")
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
                    "Click 'Supported Sites' to see the list of supported websites.")

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
        title_label = ctk.CTkLabel(
            header_frame,
            text="♫  MUSIC DOWNLOADER",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="white"
        )
        title_label.pack(expand=True)
        debug("Title label created")

        debug("Creating subtitle...")
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Download audio & video from YouTube and more",
            font=ctk.CTkFont(size=11),
            text_color=("#999999", "#777777")  # Subtle gray for subtitle
        )
        subtitle_label.pack(pady=(0, 8))
        debug("Subtitle created")

        debug("Creating content frame...")
        # Two-column layout container
        content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        debug("Content frame created")

        debug("Creating left column...")
        # LEFT COLUMN - Main controls (with border for separation)
        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent", border_width=2,
                                  border_color=("#cccccc", "#444444"), corner_radius=10)
        left_frame.pack(side="left", fill="y", padx=(0, 8), ipadx=10, ipady=10)
        debug("Left column created")

        debug("Creating right column...")
        # RIGHT COLUMN - Queue management (distinct background)
        right_frame = ctk.CTkFrame(content_frame, fg_color=("#f5f5f5", "#252525"),
                                   corner_radius=10, border_width=2,
                                   border_color=("#cccccc", "#444444"))
        right_frame.pack(side="right", fill="both", expand=True)
        debug("Right column created")

        # === LEFT COLUMN CONTENT ===
        debug("Creating LEFT COLUMN widgets...")

        # URL entry frame with paste button
        debug("Creating URL entry frame...")
        self.url_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        debug("URL frame object created")
        self.url_frame.pack(fill="x", padx=10, pady=(0, 10))
        debug("URL frame packed")

        debug("Creating URL label...")
        url_label = ctk.CTkLabel(
            self.url_frame,
            text="Video/Audio URL:",
            font=ctk.CTkFont(size=13)
        )
        debug("URL label created")
        url_label.pack(anchor="w", pady=(0, 5))
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
            text_color=("#1f6aa5", "#3b8ed0")
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

        type_buttons = ctk.CTkFrame(self.radio_frame, fg_color="transparent")
        type_buttons.pack(fill="x")

        self.audio_button = ctk.CTkButton(
            type_buttons,
            text="Audio (MP3)",
            command=lambda: self._select_type("audio"),
            height=35,
            fg_color=("#3b8ed0", "#1f6aa5"),
            corner_radius=8
        )
        self.audio_button.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.video_button = ctk.CTkButton(
            type_buttons,
            text="Video (MP4)",
            command=lambda: self._select_type("video"),
            height=35,
            fg_color="transparent",
            border_width=2,
            corner_radius=8
        )
        self.video_button.pack(side="left", fill="x", expand=True, padx=(5, 0))

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
            corner_radius=10
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
            border_width=2
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
            border_width=1
        )
        settings_btn.pack(fill="x", pady=(0, 5))

        help_btn = ctk.CTkButton(
            settings_frame,
            text="Supported Sites",
            command=self.show_supported_sites,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1
        )
        help_btn.pack(fill="x", pady=(0, 5))

        # yt-dlp Settings button
        ytdlp_settings_btn = ctk.CTkButton(
            settings_frame,
            text="⚙ yt-dlp Settings",
            command=self.show_ytdlp_settings,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1
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
            border_width=1
        )
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

        # Status label (left column, after settings)
        self.status_label = ctk.CTkLabel(
            left_frame,
            text="",
            font=ctk.CTkFont(size=9),
            wraplength=350,
            text_color=("#666666", "#888888"),
            height=30
        )
        self.status_label.pack(fill="x", padx=10, pady=(10, 0))
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
            border_width=2,
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
            border_width=2
        )
        self.save_queue_btn.pack(side="left", fill="x", expand=True, padx=2)

        self.load_queue_btn = ctk.CTkButton(
            queue_buttons_frame,
            text="Import",
            command=self.load_queue_from_file,
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=2
        )
        self.load_queue_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Bind window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start queue checking
        self.root.after(100, self.check_queue)

        # Check yt-dlp version
        self.root.after(500, self.check_ytdlp_version)

    def center_window_on_current_monitor(self, width, height):
        """Center window on the monitor where the mouse cursor is"""
        self.root.update_idletasks()

        # Get mouse cursor position to determine which monitor user is on
        cursor_x = self.root.winfo_pointerx()
        cursor_y = self.root.winfo_pointery()

        # Try to get monitor info using xrandr
        try:
            import subprocess
            result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                monitors = []

                for line in lines:
                    if ' connected' in line:
                        parts = line.split()
                        for part in parts:
                            # Look for geometry pattern like "1920x1080+0+0"
                            if 'x' in part and '+' in part:
                                try:
                                    # Split by '+' to get resolution and position
                                    res_pos = part.split('+')
                                    if len(res_pos) >= 3:
                                        # Parse width and height from resolution
                                        w_h = res_pos[0].split('x')
                                        if len(w_h) == 2:
                                            mon_w = int(w_h[0])
                                            mon_h = int(w_h[1])
                                            mon_x = int(res_pos[1])
                                            mon_y = int(res_pos[2])
                                            monitors.append({
                                                'x': mon_x, 'y': mon_y,
                                                'width': mon_w, 'height': mon_h
                                            })
                                            break
                                except (ValueError, IndexError):
                                    continue

                # Find which monitor contains the cursor
                current_monitor = None
                for mon in monitors:
                    if (mon['x'] <= cursor_x < mon['x'] + mon['width'] and
                        mon['y'] <= cursor_y < mon['y'] + mon['height']):
                        current_monitor = mon
                        break

                # If found, center on that monitor
                if current_monitor:
                    x = current_monitor['x'] + (current_monitor['width'] - width) // 2
                    y = current_monitor['y'] + (current_monitor['height'] - height) // 2
                    self.root.geometry(f"{width}x{height}+{x}+{y}")
                    return

        except Exception:
            pass

        # Fallback: simple centering
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
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
        """Update download type and button states"""
        self.download_type.set(type_value)

        if type_value == "audio":
            # Audio selected - highlight audio button
            self.audio_button.configure(
                fg_color=("#3b8ed0", "#1f6aa5"),
                border_width=0
            )
            self.video_button.configure(
                fg_color="transparent",
                border_width=2
            )
        else:
            # Video selected - highlight video button
            self.audio_button.configure(
                fg_color="transparent",
                border_width=2
            )
            self.video_button.configure(
                fg_color=("#3b8ed0", "#1f6aa5"),
                border_width=0
            )

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
                    self.show_saved_status(f"Saved to: {msg_data}", "#4caf50", msg_data)
                    self._keep_status = True  # don't let the following "reset" clear it
                elif msg_type == "error":
                    self.progress_bar.stop()
                    self.root.after(50, lambda: self.progress_label.configure(
                        text="✖ Download failed",
                        text_color="#f44336"
                    ))
                    error_lower = str(msg_data).lower()
                    update_hint = ""
                    if any(word in error_lower for word in ["403", "forbidden", "old", "update", "version"]):
                        update_hint = " → Try updating: pip3 install -U yt-dlp"
                    self.status_label.configure(text=f"Error: {msg_data}{update_hint}", text_color="#f44336")
                    self._keep_status = True
                elif msg_type == "reset":
                    self.reset_ui(keep_status=getattr(self, "_keep_status", False))
                    self._keep_status = False
                elif msg_type == "queue_success":
                    self._run_done = getattr(self, "_run_done", 0) + 1
                    self.update_queue_item_status(msg_data, 'done')
                    self.current_download_index += 1
                    self.root.after(200, self.process_next_queue_item)
                elif msg_type == "queue_failed":
                    self._run_failed = getattr(self, "_run_failed", 0) + 1
                    self.update_queue_item_status(msg_data, 'failed')
                    self.current_download_index += 1
                    self.root.after(200, self.process_next_queue_item)

        except queue.Empty:
            pass

        # Check queue again after 100ms
        self.root.after(100, self.check_queue)

    # ---- clickable "Saved to:" status line ----
    def _setup_status_link(self):
        self._status_link_dir = None
        self._status_link_text = None
        self._status_font = ctk.CTkFont(size=9)
        self._status_font_link = ctk.CTkFont(size=9, underline=True)
        original_configure = self.status_label.configure

        def configure(*args, **kwargs):
            # Any other text written to the status line turns the link off
            if "text" in kwargs and self._status_link_dir and kwargs["text"] != self._status_link_text:
                self._status_link_dir = self._status_link_text = None
                original_configure(font=self._status_font, cursor="")
            return original_configure(*args, **kwargs)

        self.status_label.configure = configure
        self.status_label.bind("<Button-1>", self._on_status_click)

    def show_saved_status(self, text, color, folder):
        """Show a result message; clicking it opens `folder` in the file manager."""
        self.status_label.configure(text=text, text_color=color)
        self._status_link_dir, self._status_link_text = folder, text
        self.status_label.configure(font=self._status_font_link, cursor="hand2")

    def _on_status_click(self, event=None):
        folder = self._status_link_dir
        if not folder or self.status_label.cget("text") != self._status_link_text:
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
            self.root.after(0, lambda: self._show_ytdlp_status(path, version, exists))
        threading.Thread(target=worker, daemon=True).start()

    def _show_ytdlp_status(self, path, version, exists):
        frozen = getattr(sys, 'frozen', False)
        if version:
            debug(f"yt-dlp version check OK: {version} ({path})")
            self.status_label.configure(text=f"v{APP_VERSION}", text_color=("#666666", "#888888"))
        elif not exists:
            self.status_label.configure(
                text=("⚠ yt-dlp missing! Click 'Update yt-dlp' or reinstall the application" if frozen
                      else "⚠ yt-dlp not found! Install with: pip3 install -U yt-dlp"),
                text_color="#ff9800")
        else:
            debug(f"yt-dlp at {path} does not run", level="ERROR")
            self.status_label.configure(
                text=("⚠ yt-dlp error! Click 'Update yt-dlp' to repair it" if frozen
                      else "⚠ yt-dlp error! Try: pip3 install -U --force-reinstall yt-dlp"),
                text_color="#ff9800")

    def paste_from_clipboard(self):
        try:
            clipboard_content = self.root.clipboard_get().strip()
            if clipboard_content:
                self.url_entry.delete(0, 'end')
                self.url_entry.insert(0, clipboard_content)
                TooltipNotification(self.root, "✓ URL pasted from clipboard")
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

        # Check for duplicates
        for item in self.download_queue:
            if item['url'] == url:
                TooltipNotification(self.root, "⚠ URL already in queue")
                return

        queue_item = {
            'url': url,
            'status': 'waiting',
            'widget': None
        }
        self.download_queue.append(queue_item)

        # Show queue panel when first item is added
        if len(self.download_queue) == 1:
            self.empty_queue_label.pack_forget()

        self.create_queue_item(len(self.download_queue) - 1)
        self.url_entry.delete(0, 'end')

        # Update button text
        self.update_download_button_text()

        queue_size = len(self.download_queue)
        TooltipNotification(self.root, f"✓ Added to queue ({queue_size} items)")

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

        url_text = item['url']
        if len(url_text) > 50:
            url_text = url_text[:47] + "..."
        url_label = ctk.CTkLabel(
            top_row,
            text=url_text,
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        url_label.pack(side="left", fill="x", expand=True)

        remove_btn = ctk.CTkButton(
            top_row,
            text="X",
            width=30,
            height=25,
            command=lambda idx=index: self.remove_from_queue(idx),
            fg_color="transparent",
            hover_color=("#d32f2f", "#b71c1c"),
            font=ctk.CTkFont(size=14)
        )
        remove_btn.pack(side="right", padx=5)

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

    def remove_from_queue(self, index):
        """Remove item from queue"""
        if 0 <= index < len(self.download_queue):
            item = self.download_queue[index]

            if item['status'] == 'downloading':
                TooltipNotification(self.root, "⚠ Cannot remove item being downloaded")
                return

            if item['widget']:
                item['widget']['frame'].destroy()

            self.download_queue.pop(index)
            self.rebuild_queue_display()

            if len(self.download_queue) == 0:
                self.empty_queue_label.pack(expand=True, pady=50)

            # Update button text
            self.update_download_button_text()

    def rebuild_queue_display(self):
        """Rebuild queue display after removal"""
        # Destroy all queue item widgets (but not empty_queue_label)
        for widget in self.queue_scroll.winfo_children():
            if widget != self.empty_queue_label:
                widget.destroy()

        for i in range(len(self.download_queue)):
            self.download_queue[i]['widget'] = None
            self.create_queue_item(i)

    def update_download_button_text(self):
        """Update download button text based on queue size"""
        queue_size = len(self.download_queue)
        new_text = f"Download Queue ({queue_size})" if queue_size > 0 else "Download"
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
                    'downloading': ("#1f6aa5", "#3b8ed0"),
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
            command=do_clear
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

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Queue to File",
            initialdir=self.output_dir
        )

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
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load Queue from File",
            initialdir=self.output_dir
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]

                if not urls:
                    TooltipNotification(self.root, "⚠ File is empty")
                    return

                added_count = 0
                skipped_count = 0
                for url in urls:
                    if url.startswith('http://') or url.startswith('https://'):
                        # Check for duplicates
                        if any(item['url'] == url for item in self.download_queue):
                            skipped_count += 1
                            continue

                        queue_item = {
                            'url': url,
                            'status': 'waiting',
                            'widget': None
                        }
                        self.download_queue.append(queue_item)

                        if len(self.download_queue) == 1:
                            self.empty_queue_label.pack_forget()

                        self.create_queue_item(len(self.download_queue) - 1)
                        added_count += 1

                self.update_download_button_text()
                message = f"✓ Loaded {added_count} URLs"
                if skipped_count > 0:
                    message += f" ({skipped_count} duplicates skipped)"
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
            "video_quality": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "video_extra_args": [
                "--merge-output-format", "mp4",
                "--recode-video", "mp4"
            ],
            "custom_args": []  # User's custom arguments (applied to all downloads)
        }

    def load_config(self):
        """Load full config including output_dir and yt-dlp settings"""
        default_dir = os.path.expanduser("~/Music/YouTube MP3")
        default_ytdlp = self.get_default_ytdlp_config()

        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)

                # Load output directory
                saved_dir = config.get("output_dir", default_dir)
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

    def build_ytdlp_command(self, url, download_dir, is_audio=True):
        """Build yt-dlp command from config settings"""
        ytdlp_path = self.get_yt_dlp_path()
        cfg = self.ytdlp_config

        # Start with common args
        command = [ytdlp_path] + cfg.get("common_args", [])

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

        # Add custom user arguments
        command.extend(cfg.get("custom_args", []))

        # Output template and URL
        command.extend(["-o", os.path.join(download_dir, "%(title)s.%(ext)s")])
        command.append(url)

        return command

    def start_download(self):
        # Check ffmpeg
        if shutil.which("ffmpeg") is None:
            self.show_error_dialog("Error", "ffmpeg is not installed.\nInstall it using: sudo apt install ffmpeg")
            return

        # Process queue or single download
        if len(self.download_queue) > 0:
            self.process_queue()
        else:
            url = self.url_entry.get().strip()
            if not url:
                self.show_error_dialog("Error", "Please enter a URL")
                return

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
                text_color=("#1f6aa5", "#3b8ed0")
            )
            self.status_label.configure(
                text="Downloading...",
                text_color=("#666666", "#888888")
            )

            threading.Thread(target=self.download_music, args=(url, -1), daemon=True).start()

    def process_queue(self):
        """Process all queue items"""
        if len(self.download_queue) == 0:
            return

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

        self.current_download_index = 0
        self._queue_saved_dirs = []
        self._run_done = self._run_failed = 0  # counts for this run only
        self.process_next_queue_item()

    def process_next_queue_item(self):
        """Process next item in queue"""
        while self.current_download_index < len(self.download_queue):
            item = self.download_queue[self.current_download_index]
            if item['status'] == 'waiting':
                url = item['url']
                self.update_queue_item_status(self.current_download_index, 'downloading')

                self.progress_bar.set(0)
                self.progress_bar.start()
                self.progress_label.configure(
                    text=f"Downloading {self.current_download_index + 1}/{len(self.download_queue)}...",
                    text_color=("#1f6aa5", "#3b8ed0")
                )

                threading.Thread(target=self.download_music, args=(url, self.current_download_index), daemon=True).start()
                return

            self.current_download_index += 1

        self.queue_processing_complete()

    def create_playlist_for_album(self, album_folder, album_name):
        """Create M3U playlist file for all songs in album folder"""
        try:
            # Get all audio/video files in the folder
            audio_extensions = ('.mp3', '.mp4', '.m4a', '.flac', '.wav', '.ogg', '.webm', '.opus')
            files = []

            for filename in os.listdir(album_folder):
                if filename.lower().endswith(audio_extensions):
                    files.append(filename)

            if not files:
                return  # No audio files to create playlist

            # Sort files naturally (so "1.Song" < "2.Song" < "10.Song")
            import re
            def natural_sort_key(s):
                return [int(text) if text.isdigit() else text.lower()
                        for text in re.split('([0-9]+)', s)]

            files.sort(key=natural_sort_key)

            # Create M3U playlist file
            playlist_name = f"{album_name}.m3u" if album_name else "playlist.m3u"
            playlist_path = os.path.join(album_folder, playlist_name)

            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")  # M3U header
                for filename in files:
                    f.write(f"{filename}\n")

            debug(f"Created playlist: {playlist_path} with {len(files)} songs")
        except Exception as e:
            debug(f"Warning: Could not create playlist: {e}", level="WARN")

    def queue_processing_complete(self):
        """Called when all queue items processed"""
        self.downloading = False
        self.current_download_index = -1

        # Count only what happened in this run (items finished in an earlier run stay "done" in the list)
        done_count = getattr(self, "_run_done", 0)
        failed_count = getattr(self, "_run_failed", 0)

        # Create playlist if downloading to an album folder
        album_name = self.album_entry.get().strip()
        if album_name and done_count > 0:
            album_folder = self.get_album_folder(self.output_dir, album_name)
            self.create_playlist_for_album(album_folder, album_name)

        # Where the files went (same folder for the whole queue, incl. the Album/Folder subfolder)
        saved_dirs = list(getattr(self, "_queue_saved_dirs", []))  # folders used in this run

        summary = f"Queue complete: {done_count} downloaded, {failed_count} failed"
        if saved_dirs:
            summary += f"\nSaved to: {saved_dirs[0]}" + (f" (+{len(saved_dirs) - 1} more)" if len(saved_dirs) > 1 else "")
        color = "#4caf50" if failed_count == 0 else "#ff9800"
        if saved_dirs:
            self.show_saved_status(summary, color, saved_dirs[0])
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

            if self.download_process:
                self.download_process.terminate()
                self.downloading = False

                # Reset queue items that were downloading back to waiting
                for item in self.download_queue:
                    if item['status'] == 'downloading':
                        item['status'] = 'waiting'
                        self.update_queue_item_status(self.download_queue.index(item), 'waiting')

                # Reset download index
                self.current_download_index = -1

                self.reset_ui()
                self.progress_label.configure(text="Download cancelled")
                self.root.after(2000, lambda: self.progress_frame.pack_forget())

        yes_btn = ctk.CTkButton(
            button_frame,
            text="Yes, Cancel",
            height=35,
            fg_color="#d32f2f",
            hover_color="#b71c1c",
            command=do_cancel
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
        candidates = [USER_YTDLP_PATH]
        sys_path = system_ytdlp_path()
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

        album_name = album_name.strip()

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

    def remove_number_prefix(self, filename):
        """Remove existing track number prefix like '1.', '01.', '02.' from filename"""
        import re
        # Only match numbers followed by a period (standard track numbering)
        # Does NOT remove numbers followed by spaces (those are part of the title)
        # Examples: "1.Song" → "Song", "01.Song" → "Song"
        # Preserves: "1 Hour Song", "3 Minutes", "24K Magic"
        match = re.match(r'^(\d+)\.\s*(.+)$', filename)
        if match:
            return match.group(2)  # Return filename without the number
        return filename

    def add_track_number(self, filepath, track_number):
        """Add track number prefix to filename"""
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)

        # Split filename and extension
        name_parts = os.path.splitext(filename)
        name_without_ext = name_parts[0]
        ext = name_parts[1]

        # Remove existing number prefix first
        clean_name = self.remove_number_prefix(name_without_ext)

        # Add new track number (zero-padded to 2 digits)
        new_filename = f"{track_number:02d}.{clean_name}{ext}"
        new_filepath = os.path.join(directory, new_filename)

        # Rename the file
        try:
            os.rename(filepath, new_filepath)
            return new_filepath
        except Exception as e:
            debug(f"Warning: Could not rename file: {e}", level="WARN")
            return filepath

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

    def download_music(self, url, queue_index=-1):
        """Download music from URL"""
        os.makedirs(self.output_dir, exist_ok=True)
        ytdlp_path = self.get_yt_dlp_path()

        if not shutil.which(ytdlp_path) and not os.path.exists(ytdlp_path):
            if queue_index >= 0:
                self.message_queue.put(("queue_failed", queue_index))
            else:
                # Show appropriate message based on whether app is bundled
                if getattr(sys, 'frozen', False):
                    error_msg = ("yt-dlp not found!\n\n"
                                "The application may be corrupted.\n"
                                "Please reinstall the application to fix this issue.")
                else:
                    error_msg = ("yt-dlp not found!\n\n"
                                "Please install it with:\n"
                                "pip3 install -U yt-dlp")
                self.message_queue.put(("error", error_msg))
                self.message_queue.put(("reset", None))
            return

        # Check if video mode is selected but URL has no video
        if self.download_type.get() == "video":
            self.root.after(0, self.progress_label.configure, {"text": "Checking video availability..."})
            has_video = self.check_has_video(url)

            if not has_video:
                # Audio-only content - prevent download
                error_msg = "This URL has no video.\nPlease select 'Audio (MP3)' mode."
                if queue_index >= 0:
                    self.message_queue.put(("queue_failed", queue_index))
                    self.message_queue.put(("error", error_msg))
                else:
                    self.message_queue.put(("error", error_msg))
                    self.message_queue.put(("reset", None))
                return

        album_name = self.album_entry.get().strip()
        download_dir = self.get_album_folder(self.output_dir, album_name)

        # Build yt-dlp command from config
        is_audio = (self.download_type.get() == "audio")
        command = self.build_ytdlp_command(url, download_dir, is_audio=is_audio)
        debug(f"yt-dlp command: {' '.join(command)}")

        try:
            self.root.after(0, self.progress_label.configure, {"text": "Downloading..."})
            self.download_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = self.download_process.communicate()

            if not self.downloading:
                return

            if self.download_process.returncode != 0:
                # Parse error and show user-friendly message instead of raw stderr
                error_message = self.parse_error_message(stderr)
                if queue_index >= 0:
                    self.message_queue.put(("queue_failed", queue_index))
                else:
                    self.message_queue.put(("error", error_message))
            else:
                # Apply track numbering if enabled and downloading from queue
                if self.number_tracks_var.get() and queue_index >= 0:
                    try:
                        # Find the most recently created file in download_dir
                        files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))]
                        if files:
                            latest_file = max(files, key=os.path.getctime)
                            # Use queue_index + 1 as track number (1-based)
                            self.add_track_number(latest_file, queue_index + 1)
                    except Exception as e:
                        debug(f"Warning: Could not apply track numbering: {e}", level="WARN")

                if queue_index >= 0:
                    if download_dir not in self._queue_saved_dirs:
                        self._queue_saved_dirs.append(download_dir)
                    self.message_queue.put(("queue_success", queue_index))
                else:
                    self.message_queue.put(("success", download_dir))
        except Exception as error:
            if self.downloading:
                if queue_index >= 0:
                    self.message_queue.put(("queue_failed", queue_index))
                else:
                    self.message_queue.put(("error", str(error)))
        finally:
            self.download_process = None
            if queue_index < 0:
                self.downloading = False
                self.message_queue.put(("reset", None))

    def reset_ui(self, keep_status=False):
        """Reset UI after download completes/cancels (keep_status: leave the final result message visible)"""
        self.downloading = False
        self.current_download_index = -1  # Reset queue index
        self.cancel_button.pack_forget()

        # Update button text based on current queue state BEFORE packing
        queue_size = len(self.download_queue)
        if queue_size > 0:
            self.download_button.configure(text=f"Download Queue ({queue_size})")
        else:
            self.download_button.configure(text="Download")

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

    def show_supported_sites(self):
        try:
            result = subprocess.run(
                [self.get_yt_dlp_path(), "--extractor-descriptions"],
                capture_output=True,
                text=True
            )
            sites = result.stdout.strip().split("\n")

            sites_window = ctk.CTkToplevel(self.root)
            sites_window.title("Supported Sites")
            self.center_dialog(sites_window, 500, 500)

            frame = ctk.CTkFrame(sites_window, corner_radius=15)
            frame.pack(expand=True, fill="both", padx=15, pady=15)

            title = ctk.CTkLabel(
                frame,
                text="Supported Sites",
                font=ctk.CTkFont(size=20)
            )
            title.pack(pady=(10, 15))

            search_label = ctk.CTkLabel(frame, text="Search:", font=ctk.CTkFont(size=13))
            search_label.pack(anchor="w", padx=20, pady=(0, 5))

            search_var = ctk.StringVar()
            search_entry = ctk.CTkEntry(
                frame,
                textvariable=search_var,
                placeholder_text="Type to filter...",
                height=35
            )
            search_entry.pack(fill="x", padx=20, pady=(0, 10))

            text_area = ctk.CTkTextbox(frame, wrap="word", font=ctk.CTkFont(size=12))
            text_area.pack(expand=True, fill="both", padx=20, pady=(0, 10))

            def update_text_area(*args):
                text_area.delete("1.0", "end")
                search_term = search_var.get().lower()
                for site in sites:
                    if search_term in site.lower():
                        text_area.insert("end", f"{site}\n")

            search_var.trace("w", update_text_area)
            update_text_area()

            close_btn = ctk.CTkButton(
                frame,
                text="Close",
                command=sites_window.destroy,
                height=35
            )
            close_btn.pack(pady=(0, 10), padx=20, fill="x")

        except Exception as e:
            self.show_error_dialog("Error", f"Failed to fetch supported sites: {str(e)}")

    def show_ytdlp_settings(self):
        """Show yt-dlp settings configuration dialog"""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("yt-dlp Settings")
        self.center_dialog(settings_window, 700, 600)

        frame = ctk.CTkFrame(settings_window, corner_radius=15)
        frame.pack(expand=True, fill="both", padx=15, pady=15)

        # Title
        title = ctk.CTkLabel(
            frame,
            text="⚙ yt-dlp Configuration",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(10, 5))

        subtitle = ctk.CTkLabel(
            frame,
            text="Customize yt-dlp download arguments (one per line)",
            font=ctk.CTkFont(size=11),
            text_color=("#666666", "#888888")
        )
        subtitle.pack(pady=(0, 15))

        # Scrollable content
        content = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=15, pady=(0, 10))

        cfg = self.ytdlp_config

        # Audio Quality dropdown
        audio_qual_label = ctk.CTkLabel(content, text="Audio Quality:", font=ctk.CTkFont(size=13, weight="bold"))
        audio_qual_label.pack(anchor="w", pady=(5, 5))

        quality_frame = ctk.CTkFrame(content, fg_color="transparent")
        quality_frame.pack(fill="x", pady=(0, 10))

        audio_quality_var = ctk.StringVar(value=cfg.get("audio_quality", "0"))
        quality_options = [
            ("0 - Best", "0"),
            ("2 - High (192kbps)", "2"),
            ("5 - Medium (128kbps)", "5"),
            ("9 - Low (64kbps)", "9")
        ]
        for label, value in quality_options:
            rb = ctk.CTkRadioButton(
                quality_frame,
                text=label,
                variable=audio_quality_var,
                value=value,
                font=ctk.CTkFont(size=12)
            )
            rb.pack(anchor="w", padx=10, pady=2)

        # Custom Arguments
        custom_label = ctk.CTkLabel(content, text="Custom Arguments (applied to all downloads):",
                                   font=ctk.CTkFont(size=13, weight="bold"))
        custom_label.pack(anchor="w", pady=(15, 5))

        custom_text = ctk.CTkTextbox(content, height=100, font=ctk.CTkFont(size=11))
        custom_text.pack(fill="x", pady=(0, 5))
        custom_text.insert("1.0", "\n".join(cfg.get("custom_args", [])))

        hint1 = ctk.CTkLabel(
            content,
            text="Tip: --cookies-from-browser firefox",
            font=ctk.CTkFont(size=10),
            text_color=("#888888", "#666666")
        )
        hint1.pack(anchor="w", pady=(0, 10))

        # Advanced Settings (collapsible)
        advanced_label = ctk.CTkLabel(content, text="Advanced Settings:",
                                     font=ctk.CTkFont(size=13, weight="bold"))
        advanced_label.pack(anchor="w", pady=(15, 5))

        # Common args
        common_label = ctk.CTkLabel(content, text="Common Arguments:", font=ctk.CTkFont(size=12))
        common_label.pack(anchor="w", pady=(5, 5))
        common_text = ctk.CTkTextbox(content, height=60, font=ctk.CTkFont(size=11))
        common_text.pack(fill="x", pady=(0, 10))
        common_text.insert("1.0", "\n".join(cfg.get("common_args", [])))

        # Video quality
        video_qual_label = ctk.CTkLabel(content, text="Video Quality Format:", font=ctk.CTkFont(size=12))
        video_qual_label.pack(anchor="w", pady=(5, 5))
        video_qual_text = ctk.CTkEntry(content, font=ctk.CTkFont(size=11))
        video_qual_text.pack(fill="x", pady=(0, 10))
        video_qual_text.insert(0, cfg.get("video_quality", ""))

        # Buttons
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 10))

        def reset_defaults():
            if messagebox.askyesno("Reset Settings",
                                  "Reset all yt-dlp settings to defaults?"):
                self.ytdlp_config = self.get_default_ytdlp_config()
                self.save_config()
                settings_window.destroy()
                TooltipNotification(self.root, "✓ Settings reset to defaults", 2000)

        def save_settings():
            # Parse custom args
            custom_args_text = custom_text.get("1.0", "end").strip()
            custom_args = [line.strip() for line in custom_args_text.split("\n") if line.strip()]

            # Parse common args
            common_args_text = common_text.get("1.0", "end").strip()
            common_args = [line.strip() for line in common_args_text.split("\n") if line.strip()]

            # Update config
            self.ytdlp_config["audio_quality"] = audio_quality_var.get()
            self.ytdlp_config["custom_args"] = custom_args
            self.ytdlp_config["common_args"] = common_args if common_args else ["--ignore-config"]
            self.ytdlp_config["video_quality"] = video_qual_text.get().strip()

            # Save to file
            self.save_config()
            settings_window.destroy()
            TooltipNotification(self.root, "✓ Settings saved successfully", 2000)

        reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            command=reset_defaults,
            height=35,
            fg_color="#8B4545",
            hover_color="#6B3535"
        )
        reset_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save Settings",
            command=save_settings,
            height=35,
            fg_color=("#3b8ed0", "#1f6aa5")
        )
        save_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

        cancel_btn = ctk.CTkButton(
            frame,
            text="Cancel",
            command=settings_window.destroy,
            height=35,
            fg_color="transparent",
            border_width=1
        )
        cancel_btn.pack(fill="x", padx=15, pady=(0, 10))

    def update_ytdlp(self):
        """Update yt-dlp to the latest version"""
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
                ui = lambda fn: self.root.after(0, fn)
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
                    self.root.after(500, self.check_ytdlp_version)
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
            hover_color="#3a9a3a"
        )
        update_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=update_window.destroy,
            height=35,
            fg_color="transparent",
            border_width=1
        )
        cancel_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def change_output_dir(self):
        new_dir = filedialog.askdirectory(initialdir=self.output_dir, title="Select Output Folder")
        if new_dir:
            self.output_dir = new_dir
            self.save_output_dir()
            TooltipNotification(self.root, f"✓ Output folder updated")

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
                command=lambda: [self.root.destroy(), confirm_window.destroy()]
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
            self.root.destroy()

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


if __name__ == "__main__":
    try:
        debug("="*70)
        debug("Starting MDJ Music Downloader...")
        debug("="*70)
        root = ctk.CTk(className="mdj-music-downloader")
        debug("✅ Root window created")
        set_window_icon(root)
        app = MusicDownloader(root)
        debug("✅ App initialized")
        root.mainloop()
        debug("App closed normally")
    except Exception as e:
        debug(f"❌ FATAL ERROR: {e}", level="ERROR")
        import traceback
        debug(traceback.format_exc(), level="ERROR")
        input("Press Enter to exit...")
