# Installation Guide

## Easy Install (.deb package)

1. Download `mdj-music-downloader_1.0.3_amd64.deb` from [Releases](https://github.com/ngquocvuong/mdj-music-downloader/releases)
2. Install: `sudo apt install ./mdj-music-downloader_1.0.3_amd64.deb`
3. Launch from the application menu, or run: `/opt/mdj-music-downloader/music_downloader`

## Run from Source

```bash
git clone https://github.com/ngquocvuong/mdj-music-downloader.git
cd mdj-music-downloader
sudo apt install ffmpeg python3-tk
pip3 install customtkinter Pillow darkdetect packaging yt-dlp mutagen
python3 music_downloader_customtkinter.py
```

`mutagen` writes the cover art and tags into songs. For full YouTube support, yt-dlp needs a JavaScript runtime (Deno by default; see the [yt-dlp EJS guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS)). The Flatpak includes one.

## Build from Source

```bash
pip3 install pyinstaller
./build.sh              # Build executable -> dist/music_downloader
./build-deb.sh          # Build .deb package (downloads yt-dlp if needed)
sudo ./INSTALL.sh       # Or install directly without a package
```

## Flatpak

A Flatpak (with yt-dlp, ffmpeg and Node.js included) is being prepared for Flathub. To build and test it yourself, see [flatpak/README.md](flatpak/README.md).

## Uninstall

- .deb: `sudo apt remove mdj-music-downloader`
- Flatpak: `flatpak uninstall io.github.ngquocvuong.mdj-music-downloader`

## Support

- Issues: https://github.com/ngquocvuong/mdj-music-downloader/issues
- Email: blackhawk_7585@icloud.com
- Donate: https://ko-fi.com/mdj_musicdl
