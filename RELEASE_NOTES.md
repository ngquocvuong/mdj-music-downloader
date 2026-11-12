# MDJ Music Downloader v1.1.2 - Release Notes

## 🖼️ What's fixed in v1.1.2
- **Covers show in the file manager.** If the folder was open while songs downloaded, some songs could show a plain icon instead of their cover. The cover was always in the song; now the file manager shows it too.

## 🛠️ What's fixed in v1.1.1
- **YouTube downloads work on every computer.** The app now includes Deno, the JavaScript runtime yt-dlp needs for YouTube, so nothing else has to be installed. (1.1.0 depended on the computer already having one.)
- **Failed songs say why.** The queue summary names the reason, and pointing at a song's ✗ shows the full message.
- Failed downloads are written to `~/.cache/mdj-music-downloader/errors.log`.
- A broken yt-dlp is reported clearly instead of failing every download silently.
- Audio conversion uses the system's own libraries (more reliable on other Linux versions).

## 🆕 What's new in v1.1.0
- **Flatpak you can build yourself** (see [flatpak/README.md](flatpak/README.md)): yt-dlp, ffmpeg and Node.js are included, so nothing else has to be installed.
- **New yt-dlp Settings window.** Basic tab: audio format (mp3, m4a, opus, flac, wav) and quality, video quality (up to 4K), cover art and tags. Advanced tab: any yt-dlp option, with step-by-step help, a **Check** button and a live preview of the exact command. It opens much faster, and instantly after the first time.
- **Cover art and tags for music players, phones and car stereos.** Songs get a square cover and title, artist and year tags; album songs also get the album name and track number. Album folders get a `cover.jpg`, and albums with different artists are marked "Various Artists".
- **Track numbering continues** in an existing album folder (`01`, `02` → `03`) instead of starting again at `01`.
- **Songs you already have are skipped**, so retrying a playlist only downloads what's missing.
- A link to one song inside a playlist downloads **only that song**.
- **Numbered queue** (1., 2., 3. ...).
- **Export and Import remember names and folders:** Export suggests `<album>.txt`, Import fills in the album name.
- File names work on USB sticks and SD cards (car stereos, MP3 players).
- The default download folder is now `~/Music/MDJ Downloads`.
- Many fixes: see [CHANGELOG.md](CHANGELOG.md) for the full list.

### v1.0.3
- **"Update yt-dlp" now works for every user on a shared computer.** Enter an administrator password to update it for all users, or cancel to update it just for your own account — no more "Permission denied".
- The password is asked only once (was twice), and not at all when yt-dlp is already up to date.
- Fixed: updating failed for a second user on the same computer.
- Faster startup: the window no longer freezes for a few seconds while yt-dlp is checked.
- **Queue downloads now show where the files were saved** ("Saved to: …/Album name"), like single downloads.
- **Click the folder path after "Saved to:" to open it** in your file manager.
- The queue summary counts only the songs from the current run.
- Long URLs in the queue are shortened with "..." instead of squeezing the X button.
- "Supported Sites" moved to a small **?** next to "Video/Audio URL", so the progress bar and messages are no longer cut off at the bottom.
- **New look:** teal colours matching the MDJ icon, a switch for Audio / Video, and light-yellow tooltips.
- **No more "frozen" moments:** Supported Sites and yt-dlp Settings open straight away with a "Loading..." message instead of freezing the app for a couple of seconds.
- **Modern folder and file chooser:** Output Folder, Export and Import now open your desktop's own file chooser.
- **Add songs while a queue is downloading:** + Queue, Paste and Import keep working; the new songs are downloaded in the same run.
- **Cancel always works**, also between two songs, and fully stops yt-dlp and ffmpeg.
- Finished songs are never downloaded again, and failed songs are retried next time. "Download Queue (N)" counts only the songs still to download.
- **Import skips songs already in the queue**, even when the YouTube link looks different (youtu.be, watch?v=, "?si=" share codes).
- While downloading, songs can't be removed (press Cancel first). Removing a song keeps the other songs' ✓ / ✗ status.
- Fixed: the app could freeze and then not close. Clicking X now always closes it and stops a running download.
- Fixed: after Clear Queue, the buttons in the left panel could be cut off.
- The window opens centred straight away, and the cursor shows the app is starting.

### v1.0.2
- **Fixed:** downloads failed with "yt-dlp error! Please reinstall the application" on Ubuntu 22.04, Linux Mint 21 and other systems with Python older than 3.11. The app now ships yt-dlp's standalone build, which includes its own Python. **Please update if you installed v1.0.0 or v1.0.1.**
- The "Update yt-dlp" button now downloads the standalone build and checks it works before installing.

### v1.0.1
- "Support Development" button now opens the new Ko-fi page: https://ko-fi.com/mdj_musicdl

**Install:** download `mdj-music-downloader_1.1.2_amd64.deb` below, then run `sudo apt install ./mdj-music-downloader_1.1.2_amd64.deb`

---

## 🎉 Public Release - Stable Version

A user-friendly application for downloading music and videos from YouTube and 1000+ other sites.

---

## ✨ Key Features

### Download Capabilities
- **Audio Download**: MP3 (or M4A, Opus, FLAC, WAV) with best quality, cover art and tags
- **Video Download**: MP4 up to 4K
- **Queue System**: Add multiple URLs and download them sequentially
- **Album Organization**: Organize downloads into folders
- **Track Numbering**: Automatically number tracks in order

### User Experience
- **User-Friendly Error Messages**: No more technical jargon! Clear, actionable guidance when errors occur
- **Progress Tracking**: Real-time progress display
- **Modern UI**: Clean, dark-themed interface
- **Clipboard Integration**: Paste URLs directly from clipboard

### Technical Improvements
- **Multi-User Support**: Works on ALL user accounts
- **Independent yt-dlp Updates**: Update yt-dlp without reinstalling the app
- **Built-in Update Function**: One-click yt-dlp updates
- **Thread-Safe**: Stable operation with proper threading
- **Version-Independent**: Compatible with any yt-dlp version

---

## 🆕 What's New in v1.0.0

### 🎯 User-Friendly Error Handling
- No more scary Python tracebacks!
- Detects and explains:
  - Installation errors → "Please reinstall the application"
  - Permission errors → "Check folder permissions"
  - Network errors → "Check internet connection"
  - Video unavailable → "Video is private or deleted"
  - 403/404/429 errors → Specific guidance for each
  - Disk full → "Free up space"
  - And many more...

### 🔄 Independent yt-dlp Management
- **Separated from app binary**: yt-dlp is no longer bundled
- **Easy updates**: Click "Update yt-dlp" button in the app
- **Future-proof**: Works with any yt-dlp version
- **Multiple update methods**:
  - GUI button (easiest)
  - Manual download
  - pip install

### 🛡️ Stability Improvements
- Fixed thread safety issues
- Improved error detection
- Better fallback mechanisms
- GUI-friendly privilege escalation (pkexec/sudo)

### 🎨 UI Enhancements
- "Update yt-dlp" button added
- Better error message display
- Clearer status indicators

---

## 📦 Installation

### Quick Install (Recommended)
Download `mdj-music-downloader_1.1.2_amd64.deb` from the Releases page, then:
```bash
sudo apt install ./mdj-music-downloader_1.1.2_amd64.deb
```

### From Source
```bash
./build.sh          # build dist/music_downloader
sudo ./INSTALL.sh   # install binary, yt-dlp, icon and menu entry
```

---

## 🚀 Usage

### Launch
- **From Menu**: Search for "MDJ Music Downloader" in your application menu
- **From Terminal**: `/opt/mdj-music-downloader/music_downloader`

### Download Audio
1. Paste or enter YouTube URL
2. Select **Audio** (MP3 by default; change the format in yt-dlp Settings)
3. (Optional) Enter album/folder name
4. Click "Download" or "+ Queue" for batch downloads

### Download Video
1. Paste or enter video URL
2. Select **Video**
3. Click "Download"

### Update yt-dlp (.deb only; in the Flatpak, yt-dlp is updated with the app)
1. Click "Update yt-dlp" button
2. Click "Update Now"
3. Enter an administrator password to update it for **all users** — or cancel to update it **just for your account**
4. Done!

---

## 🔧 System Requirements

- **OS**: 64-bit Linux – Ubuntu 22.04+, Linux Mint 21+, Debian 12+ (tested on Linux Mint 21.3)
- **Python**: Not required (bundled in binary)
- **ffmpeg**: Required for MP3 conversion (installed automatically with the .deb)
- **Internet**: Required for downloads
- **Disk Space**: ~20MB for app + downloads

### Optional Dependencies
- `pkexec`: For GUI privilege escalation (usually pre-installed)

---

## 📂 File Locations

- **Application**: `/opt/mdj-music-downloader/music_downloader`
- **yt-dlp**: `/opt/mdj-music-downloader/yt-dlp` (all users)
- **yt-dlp updated without admin password**: `~/.local/share/mdj-music-downloader/yt-dlp` (that user only; the newer copy is used)
- **User Config**: `~/.config/mdj-music-downloader/config.json`
- **Default Downloads**: `~/Music/MDJ Downloads`
- **Flatpak Config**: `~/.var/app/io.github.ngquocvuong.mdj-music-downloader/config/mdj-music-downloader/config.json`
- **Desktop Entry**: `/usr/share/applications/mdj-music-downloader.desktop`

---

## 🐛 Troubleshooting

### yt-dlp not found error
- Click "Update yt-dlp" in the app, OR
- Run: `sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux -o /opt/mdj-music-downloader/yt-dlp && sudo chmod 755 /opt/mdj-music-downloader/yt-dlp`

### Permission denied error
- Check output folder permissions
- Try selecting a different output folder
- Make sure you have write access to the location

### Download fails with "Video unavailable"
- Video may be private, deleted, or region-restricted
- Try a different video
- Check if you can view the video in your browser

### App doesn't appear in menu
- Run: `sudo update-desktop-database /usr/share/applications/`
- Log out and log back in

---

## 🆘 Support

### Reporting Issues
When reporting issues, please include:
1. Error message shown in the app
2. URL you're trying to download (if applicable)
3. Output folder location
4. yt-dlp version (shown in app status bar)

### Getting Help
- Check error message guidance first
- Verify internet connection
- Try updating yt-dlp
- Check the supported sites list in the app (the small **?** next to "Video/Audio URL")

---

## ⚖️ License and responsible use

MDJ Music Downloader's source code is licensed under the MIT License. The `.deb` also contains third-party software under its own licenses (some GPL); see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**Only download content you have the right to download**, and follow copyright law and each site's terms of service. MDJ does not break DRM or copy protection. See [Legal and responsible use](README.md#legal).

---

## 🙏 Credits

- Built with: Python, CustomTkinter
- Download engine: yt-dlp
- Conversion: ffmpeg

---

## 📝 Changelog

### v1.1.2 (2026-11-12)
- 🖼️ Covers show in the file manager even when the folder was open during the download

### v1.1.1 (2026-11-12)
- 🌐 Deno included: YouTube works without installing anything
- ❗ Failed queue songs show the reason; errors.log for every failed download
- 🧩 Broken yt-dlp reported clearly; conversion uses the system libraries

### v1.1.0 (2026-11-11)
- 📦 Flatpak build recipe (build it yourself)
- ⚙️ New yt-dlp Settings window (Basic and Advanced tabs, Check, command preview)
- 🖼️ Cover art and tags; album `cover.jpg`; "Various Artists" albums
- 🔢 Numbering continues in existing albums; numbered queue
- ⏭️ Songs you already have are skipped
- 💾 Export/Import remember album names and folders

### v1.0.3 (2026-11-09)
- 👥 "Update yt-dlp" works for standard users (per-user copy), one password prompt, faster startup
- 📁 Queue shows "Saved to" folder when finished; click the path to open the folder

### v1.0.2 (2026-11-09)
- 🐛 Fixed "yt-dlp error" on systems with Python older than 3.11 (standalone yt-dlp build)

### v1.0.1 (2026-11-09)
- ☕ "Support Development" now opens the new Ko-fi page: https://ko-fi.com/mdj_musicdl

### v1.0.0 (2026-11-09)
- 🎉 Initial public release
- ✅ User-friendly error messages
- ✅ Independent yt-dlp updates
- ✅ Multi-user support
- ✅ Queue download system
- ✅ Album organization
- ✅ Track numbering
- ✅ Modern UI
- ✅ Thread-safe operations

---

**Enjoy downloading! 🎵**
