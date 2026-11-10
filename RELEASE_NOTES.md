# MDJ Music Downloader v1.0.3 - Release Notes

## 🆕 What's new in v1.0.3
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
- **Modern folder and file chooser:** Output Folder, Export and Import now open your desktop's own file chooser.

### v1.0.2
- **Fixed:** downloads failed with "yt-dlp error! Please reinstall the application" on Ubuntu 22.04, Linux Mint 21 and other systems with Python older than 3.11. The app now ships yt-dlp's standalone build, which includes its own Python. **Please update if you installed v1.0.0 or v1.0.1.**
- The "Update yt-dlp" button now downloads the standalone build and checks it works before installing.

### v1.0.1
- "Support Development" button now opens the new Ko-fi page: https://ko-fi.com/mdj_musicdl

**Install:** download `mdj-music-downloader_1.0.3_amd64.deb` below, then run `sudo apt install ./mdj-music-downloader_1.0.3_amd64.deb`

---

## 🎉 Public Release - Stable Version

A user-friendly application for downloading music and videos from YouTube and 1000+ other sites.

---

## ✨ Key Features

### Download Capabilities
- **Audio Download**: MP3 format with best quality
- **Video Download**: MP4 format with best quality
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
Download `mdj-music-downloader_1.0.3_amd64.deb` from the Releases page, then:
```bash
sudo apt install ./mdj-music-downloader_1.0.3_amd64.deb
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
2. Select "Audio (MP3)" mode
3. (Optional) Enter album/folder name
4. Click "Download" or "+ Queue" for batch downloads

### Download Video
1. Paste or enter video URL
2. Select "Video (MP4)" mode
3. Click "Download"

### Update yt-dlp
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
- **Default Downloads**: `~/Music/`
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
- Check the supported sites list in the app (blue **?** next to "Video/Audio URL")

---

## ⚖️ License

This application is licensed under the MIT License.

**Note**: This application uses yt-dlp which is released under the Unlicense. Please ensure you comply with the terms of service of the websites you download from.

---

## 🙏 Credits

- Built with: Python, CustomTkinter
- Download engine: yt-dlp
- Conversion: ffmpeg

---

## 📝 Changelog

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
