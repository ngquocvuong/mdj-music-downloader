# Configuration File Guide

## 📍 Where is the Config File?

The config file is stored **per-user** in:
```
~/.config/mdj-music-downloader/config.json
```
In the Flatpak it is:
```
~/.var/app/io.github.ngquocvuong.mdj-music-downloader/config/mdj-music-downloader/config.json
```

**Why not in the source directory?**
- ✅ **Multi-user support**: Each user has their own settings
- ✅ **Persistent**: Survives app updates and rebuilds
- ✅ **Standard**: Follows Linux config file conventions
- ✅ **User-writable**: No sudo needed to change settings

## 📂 File Locations

```
Source Directory (cloned repository):
mdj-music-downloader/
├── music_downloader_customtkinter.py  (source code)
├── config.sample.json                  (template/example)
└── CONFIG_GUIDE.md                     (this file)

User Config Directory (per-user):
~/.config/mdj-music-downloader/
└── config.json                         (actual config file)

Installation (.deb):
/opt/mdj-music-downloader/
├── music_downloader                    (binary)
└── yt-dlp                              (downloader)

Flatpak:
~/.var/app/io.github.ngquocvuong.mdj-music-downloader/config/mdj-music-downloader/
└── config.json                         (actual config file)
```

## 🔧 How It Works

1. **First Launch**: Config doesn't exist
   - App creates `~/.config/mdj-music-downloader/` directory
   - Uses default settings (hardcoded in code)

2. **User Changes Settings**: Via "⚙ yt-dlp Settings" button
   - Settings saved to `~/.config/mdj-music-downloader/config.json`
   - Immediately effective (no rebuild needed)

3. **Next Launch**: Config exists
   - App loads settings from `config.json`
   - Merges with defaults (in case new settings added)

## 📝 Config File Format

See `config.sample.json` for a template.

```json
{
  "output_dir": "/path/to/music/folder",
  "ytdlp_config": {
    "common_args": ["--ignore-config"],
    "audio_format": "mp3",
    "audio_quality": "0",
    "audio_extra_args": [],
    "video_format": "mp4",
    "video_quality": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
    "video_extra_args": ["--merge-output-format", "mp4", "--recode-video", "mp4"],
    "embed_thumbnail": true,
    "embed_metadata": true,
    "cookies_browser": "",
    "custom_args": []
  }
}
```

## 🎛️ Settings Reference

### `output_dir`
Default download location.

Example: `"/home/user/Music/MDJ Downloads"`

### `ytdlp_config.common_args`
Arguments applied to ALL downloads (audio + video).

Example:
```json
"common_args": [
  "--ignore-config",
  "--cookies-from-browser",
  "firefox"
]
```

### `queue_dir`
The folder Export and Import last used. It is only saved after you export to or import from a folder other than the Output Folder. If it is missing or the folder is gone, the Output Folder is used.

### `ytdlp_config.audio_format`
Audio file type: `"mp3"` (default), `"m4a"`, `"opus"`, `"flac"` or `"wav"`.

### `ytdlp_config.audio_quality`
Audio quality for MP3 (0-9, where 0 is best).

- `"0"` = Best (~320kbps VBR)
- `"2"` = High (~192kbps)
- `"5"` = Medium (~128kbps)
- `"9"` = Low (~64kbps)

### `ytdlp_config.video_quality`
Format selection string for video downloads.

Default: `"bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"`

Examples:
- 1080p max: `"bestvideo[height<=1080]+bestaudio/best[height<=1080]"`
- 720p max: `"bestvideo[height<=720]+bestaudio/best[height<=720]"`
- Best WebM: `"bestvideo[ext=webm]+bestaudio[ext=webm]/best"`

### `ytdlp_config.embed_thumbnail`
`true` (default): songs get a square cover picture, and album folders get a `cover.jpg`. Videos never get an extra cover (add `--embed-thumbnail` in `custom_args` if you want one).

### `ytdlp_config.embed_metadata`
`true` (default): title, artist and date tags. Songs in an Album/Folder always get the album name and track number, even when this is `false`.

### `ytdlp_config.cookies_browser`
Use a browser's login for age-restricted videos, e.g. `"firefox"`. `""` (default) = off. Not available in the Flatpak.

### `ytdlp_config.custom_args`
Your custom yt-dlp arguments (applied to all downloads).

Example:
```json
"custom_args": [
  "--limit-rate", "1M",
  "--geo-bypass",
  "--proxy", "socks5://127.0.0.1:1080"
]
```

## 🚀 How to Edit

### Method 1: Via UI (Recommended)
1. Launch app
2. Click "⚙ yt-dlp Settings"
3. Edit settings
4. Click "Save Settings"

### Method 2: Edit File Directly
1. Open: `~/.config/mdj-music-downloader/config.json` (Flatpak: the path at the top of this guide)
2. Edit JSON (use sample as reference)
3. Save file
4. Restart app

### Method 3: Copy Sample
```bash
# Use sample as starting point
cp config.sample.json \
   ~/.config/mdj-music-downloader/config.json

# Edit with your preferred editor
nano ~/.config/mdj-music-downloader/config.json
```

## 🔄 Reset to Defaults

If config gets corrupted:

**Option 1: Via UI**
1. Open "⚙ yt-dlp Settings"
2. Click "Reset to Defaults"

**Option 2: Delete Config**
```bash
rm ~/.config/mdj-music-downloader/config.json
```
App will recreate with defaults on next launch.

## 🧪 Testing Your Config

The easiest way: open "⚙ yt-dlp Settings", Advanced tab. **Check** asks yt-dlp whether it accepts your options, and "What the app will run" shows the exact command for audio and video.

For a full log, enable debug mode:

1. Edit source: `music_downloader_customtkinter.py`
2. Line 25: Set `DEBUG = True`
3. Rebuild: `./build.sh`
4. Run app and try download
5. Check: `cat /tmp/mdj-music-downloader-debug.log`

You'll see:
```
yt-dlp command: /opt/mdj-music-downloader/yt-dlp --ignore-config -x --audio-format mp3 ...
```

## 📋 Multi-User Example

User 1 (alice):
- Config: `/home/alice/.config/mdj-music-downloader/config.json`
- Output: `/home/alice/Music/MDJ Downloads`
- Quality: Best (0)

User 2 (bob):
- Config: `/home/bob/.config/mdj-music-downloader/config.json`
- Output: `/home/bob/Downloads`
- Quality: Medium (5)

Each user has independent settings!

## 🔍 Troubleshooting

**Config not loading?**
```bash
ls -la ~/.config/mdj-music-downloader/config.json
# Should be owned by you and readable
```

**Settings not saving?**
```bash
# Check directory permissions
ls -ld ~/.config/mdj-music-downloader/
# Should be: drwxrwxr-x (775 or 755)
```

**Want to share config with another user?**
```bash
# Copy your config to another user
sudo cp ~/.config/mdj-music-downloader/config.json \
        /home/otheruser/.config/mdj-music-downloader/
sudo chown otheruser:otheruser \
        /home/otheruser/.config/mdj-music-downloader/config.json
```

## 📚 More Info

- yt-dlp options reference: [YT-DLP_OPTIONS_REFERENCE.md](YT-DLP_OPTIONS_REFERENCE.md)
- yt-dlp options: `yt-dlp --help`
- Sample config: `config.sample.json` (in source directory)
