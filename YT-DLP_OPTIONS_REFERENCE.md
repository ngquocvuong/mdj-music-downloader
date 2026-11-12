# yt-dlp Options Quick Reference

> Only download content you have the right to download, and follow each site's terms of service. These options are for content you are allowed to access; they are not a way around copyright, DRM, paywalls or region locks. See [Legal and responsible use](README.md#legal).

Add these in **⚙ yt-dlp Settings → Advanced → Custom arguments**, one option per line (an option and its value can share a line, e.g. `--limit-rate 1M`). Click **Check** to make sure yt-dlp accepts them.

**Already handled by MDJ** — you usually don't need these:
- Audio format and quality, video quality: the **Basic** tab. A custom option such as `--audio-format flac` wins, and the Basic control is locked with a note.
- Cover art and title/artist/album/track tags: the Basic tab's Extras (MDJ writes them itself after the download).
- `--download-archive` (skipping songs you have), `--no-playlist` and `--windows-filenames` are set by MDJ. Custom arguments override them, but changing `--download-archive` breaks skipping songs you already have. `--yes-playlist` brings back downloading the whole playlist from a song-in-playlist link.
- File names (`-o`) are always set by MDJ, because album folders and track numbering depend on them, so a custom `-o` for the file name has no effect. Use the Album/Folder field and Output Folder instead.

## 🎵 Audio Options

```bash
# Quality (0-9, 0=best)
--audio-quality 0
--audio-quality 5

# Format
--audio-format mp3
--audio-format opus
--audio-format m4a
--audio-format wav

# Extract audio from video
-x, --extract-audio
```

## 🎬 Video Options

```bash
# Best quality
-f bestvideo+bestaudio

# Specific resolution
-f "bestvideo[height<=1080]+bestaudio"
-f "bestvideo[height<=720]+bestaudio"

# Worst quality (fastest)
-f worst

# Merge to MP4
--merge-output-format mp4
--recode-video mp4
```

## 🌐 Network Options

```bash
# Speed limit
--limit-rate 500K
--limit-rate 2M

# Proxy
--proxy socks5://127.0.0.1:1080

# Retries
--retries 10

# Timeout
--socket-timeout 30
```

## 🔐 Signing In With Your Own Account

For videos your own account can watch (for example after confirming your age, or as a channel member). yt-dlp uses your login only with the access your account already has.

```bash
# Browser cookies (your own login)
--cookies-from-browser firefox
--cookies-from-browser chrome
--cookies-from-browser edge

# Cookie file
--cookies cookies.txt

# Username/password (site-specific)
--username YOUR_USERNAME
--password YOUR_PASSWORD
```

## 📝 Metadata Options

In MDJ, songs already get covers and tags from the Basic tab's Extras; these are for videos or plain yt-dlp.

```bash
# Embed thumbnail
--embed-thumbnail

# Embed metadata
--embed-metadata
```

## 📋 Playlist Options

```bash
# Specific items
--playlist-items 1,3,5-10

# Reverse order
--playlist-reverse

# Start/end
--playlist-start 5
--playlist-end 10

# Archive (skip downloaded) - MDJ already keeps one per folder (.mdj-tracks.json)
--download-archive archive.txt
```

## 📺 Subtitle Options

```bash
# Download subtitles
--write-subs
--write-auto-subs

# Specific languages
--sub-langs en,es

# Embed in video
--embed-subs
```

## 🎨 Thumbnail Options

```bash
# Download thumbnail
--write-thumbnail

# Embed in audio/video
--embed-thumbnail

# Convert format
--convert-thumbnails jpg
```

## ⚙️ Performance Options

```bash
# Concurrent downloads
--concurrent-fragments 5

# Buffer size
--buffer-size 16K

# No overwrites
--no-overwrites

# Continue partial downloads
--continue
```

## 🔍 Filtering Options

```bash
# Date range
--dateafter YYYYMMDD
--datebefore YYYYMMDD

# Match title
--match-title "REGEX"
--reject-title "REGEX"

# Duration
--min-duration 60
--max-duration 600
```

## 📁 Output Options

For plain yt-dlp. In MDJ, file names and folders come from the Output Folder, Album/Folder and "Number tracks", and a custom `-o` is ignored.

```bash
# Output template
-o "%(title)s.%(ext)s"
-o "%(playlist_index)s-%(title)s.%(ext)s"

# Output directory
-o "/path/to/folder/%(title)s.%(ext)s"

# Restrict filenames
--restrict-filenames
```

## 🐢 Being Gentle With Servers

```bash
# "Too many requests" errors: slow down
--limit-rate 1M
--sleep-interval 5
```

## 💡 Useful Combinations

### Best Audio Quality with Metadata
In MDJ: choose opus and Best on the Basic tab, and keep both Extras on. With plain yt-dlp:
```bash
-x --audio-format opus --audio-quality 0 --embed-thumbnail --embed-metadata
```

### 1080p Video with Subtitles
```bash
-f "bestvideo[height<=1080]+bestaudio" --merge-output-format mp4 --write-subs --embed-subs
```

### Slow/Unreliable Connection
```bash
--limit-rate 500K --retries 10 --fragment-retries 10 --continue
```

### Playlist Download, Oldest First, Slowly
MDJ already skips songs you have, so no archive file is needed:
```bash
--playlist-reverse --sleep-interval 3
```

### Videos That Need Your Sign-In
For videos your own account can watch:
```bash
--cookies-from-browser firefox
```

## 🔗 Full Documentation

- **Official Docs**: https://github.com/yt-dlp/yt-dlp#usage-and-options
- **Format Selection**: https://github.com/yt-dlp/yt-dlp#format-selection
- **Output Template**: https://github.com/yt-dlp/yt-dlp#output-template

## 📞 Get Help

```bash
# View all options
yt-dlp --help

# Search for specific option
yt-dlp --help | grep -i "quality"

# Get version
yt-dlp --version

# List supported sites
yt-dlp --list-extractors
```
