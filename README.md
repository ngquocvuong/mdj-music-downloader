# 🎵 MDJ Music Downloader

A modern, easy-to-use desktop application for downloading audio and video from YouTube and 1000+ websites.

![MDJ Music Downloader](screenshot.png)

## ✨ Features

- 🎵 **Audio & Video Downloads** - MP3 or MP4 format
- ⚙️ **Configurable yt-dlp Settings** - Customize download options via UI
- 📋 **Queue Management** - Download multiple songs/videos in order
- 📁 **Album Organization** - Auto-organize downloads into folders
- 🔢 **Smart Track Numbering** - Automatically number tracks (01.Song, 02.Song...)
- 🎼 **Playlist Generation** - Auto-creates .m3u playlist files
- 💾 **Queue Export/Import** - Save and load download queues
- 🖥️ **Multi-Monitor Support** - Proper window positioning
- 👥 **Multi-User Ready** - Each user gets their own settings
- 🎨 **Modern Interface** - Clean, professional CustomTkinter UI
- 🔄 **Built-in yt-dlp Updater** - Update downloader without reinstalling

## 🎯 Why MDJ Music Downloader?

Unlike other downloaders, MDJ Music Downloader is specifically designed for music collectors:
- **Smart numbering** removes existing track numbers ("1.Song") but keeps natural numbers ("1 Hour Mix")
- **Automatic playlists** so you can copy albums directly to your MP3 player
- **Clean, focused UI** - not bloated with features you don't need
- **Queue system** for batch downloading entire albums

## 📥 Installation

### From Package (Recommended – Ubuntu/Debian/Linux Mint)
1. Download `mdj-music-downloader_1.0.0_amd64.deb` from the [Releases](https://github.com/ngquocvuong/mdj-music-downloader/releases) page
2. Install it:
   ```bash
   sudo apt install ./mdj-music-downloader_1.0.0_amd64.deb
   ```
3. Launch **MDJ Music Downloader** from your application menu

Uninstall: `sudo apt remove mdj-music-downloader`

### From Source
See [INSTALL.md](INSTALL.md).

### Requirements
- 64-bit Linux (Ubuntu 20.04+, Debian 11+, Linux Mint 20+, or equivalent)
- ffmpeg (installed automatically by the .deb package)
- Python and yt-dlp are bundled – nothing else to install

## 🎬 Usage

1. **Add URLs** - Paste YouTube or other video URLs
2. **Add to Queue** - Build your download list
3. **Set Album Folder** (optional) - Organize into albums
4. **Enable Track Numbering** (optional) - Auto-number songs
5. **Click Download** - Sit back and relax!

### Tips:
- Use "Album/Folder" field to organize downloads
- Enable "Number tracks" for proper album track ordering
- Queue exports (.txt) can be shared or backed up
- Playlists (.m3u) work on most MP3 players and media software

## ⚙️ Configuration (Optional)

**No config file needed!** The app works out-of-the-box with sensible defaults.

### Customizing yt-dlp Settings

Click "⚙ yt-dlp Settings" button to:
- Adjust audio quality (Best/High/Medium/Low)
- Add custom yt-dlp arguments
- Configure video quality formats
- Reset to defaults

**Config File Location:** `~/.config/mdj-music-downloader/config.json` (auto-created when you change settings)

**Sample Config:** See [`config.sample.json`](config.sample.json) for reference

**Detailed Guide:** See [`CONFIG_GUIDE.md`](CONFIG_GUIDE.md) for all options

### Common Customizations

```bash
# Use Firefox cookies (for age-restricted videos)
--cookies-from-browser firefox

# Limit download speed
--limit-rate 500K

# Use proxy
--proxy socks5://127.0.0.1:1080
```

## 🛠️ Built With

- **[Python](https://www.python.org/)** - Programming language
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern UI framework
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - Download engine (powers the downloads)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Third-party licenses:**
- yt-dlp: [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE) (Public Domain)
- CustomTkinter: [MIT License](https://github.com/TomSchimansky/CustomTkinter/blob/master/LICENSE)

## 💖 Support Development

If MDJ Music Downloader saves you time and you'd like to support its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/musicdl)

**Other ways to support:**
- ⭐ Star this project on GitHub
- 🐛 Report bugs and request features
- 📢 Share with friends who need it
- 💬 Leave a review

All donations help maintain and improve MDJ Music Downloader!

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs via [Issues](https://github.com/ngquocvuong/mdj-music-downloader/issues)
- Suggest features
- Submit pull requests

## 📞 Contact

- **Issues**: [GitHub Issues](https://github.com/ngquocvuong/mdj-music-downloader/issues)
- **Email**: blackhawk_7585@icloud.com (for private inquiries)

## ⚖️ Disclaimer

MDJ Music Downloader is a tool for downloading publicly accessible content. Users are responsible for complying with copyright laws and website terms of service. This tool should only be used for:
- Personal backups of your own content
- Downloading Creative Commons or public domain content
- Content you have permission to download

## 🙏 Acknowledgments

- **yt-dlp team** for the amazing download engine
- **CustomTkinter** for the beautiful UI framework
- **All contributors and supporters** who make this project possible

---

Made with ❤️ for the Linux community
