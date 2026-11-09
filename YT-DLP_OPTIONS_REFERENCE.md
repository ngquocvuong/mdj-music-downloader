# yt-dlp Options Quick Reference

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

## 🔐 Authentication Options

```bash
# Browser cookies
--cookies-from-browser firefox
--cookies-from-browser chrome
--cookies-from-browser edge

# Cookie file
--cookies cookies.txt

# Username/password (site-specific)
--username YOUR_USERNAME
--password YOUR_PASSWORD
```

## 🌍 Geographic Options

```bash
# Bypass restrictions
--geo-bypass

# Specific country
--geo-bypass-country US
--geo-bypass-country JP
```

## 📝 Metadata Options

```bash
# Embed thumbnail
--embed-thumbnail

# Embed metadata
--embed-metadata

# Add to filename
-o "%(uploader)s - %(title)s.%(ext)s"
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

# Archive (skip downloaded)
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

```bash
# Output template
-o "%(title)s.%(ext)s"
-o "%(playlist_index)s-%(title)s.%(ext)s"

# Output directory
-o "/path/to/folder/%(title)s.%(ext)s"

# Restrict filenames
--restrict-filenames
```

## 🚫 Common Restrictions Bypass

```bash
# Age-restricted videos
--cookies-from-browser firefox

# Geo-blocked content
--geo-bypass
--geo-bypass-country US

# Private/unlisted videos
--cookies-from-browser chrome

# Rate-limited downloads
--limit-rate 1M
--sleep-interval 5
```

## 💡 Useful Combinations

### Best Audio Quality with Metadata
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

### Playlist Download with Archive
```bash
--download-archive downloaded.txt --playlist-reverse --sleep-interval 3
```

### Private/Age-Restricted Content
```bash
--cookies-from-browser firefox --age-limit 0
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
