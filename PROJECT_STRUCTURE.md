# Project Structure

```
mdj-music-downloader/
├── music_downloader_customtkinter.py   # Main application
├── music_downloader.spec               # PyInstaller build specification
├── icons/                              # App icon (SVG + 32–512px PNGs), mdj-cover.jpg (fallback cover art)
├── screenshot.png                      # Main window screenshot (README, Flatpak metainfo)
├── screenshot-settings.png             # yt-dlp Settings screenshot (README, Flatpak metainfo)
├── flatpak/                            # Flatpak manifest, metainfo, desktop file, launcher (see flatpak/README.md)
├── mdj-music-downloader.desktop        # Linux menu entry
├── config.sample.json                  # Example user config
├── build.sh                            # Build executable (dist/music_downloader)
├── build-deb.sh                        # Build .deb package
├── INSTALL.sh                          # Install system-wide without a package
├── README.md, INSTALL.md, CHANGELOG.md, RELEASE_NOTES.md
├── CONFIG_GUIDE.md, YT-DLP_OPTIONS_REFERENCE.md
├── CONTRIBUTING.md, PROJECT_STRUCTURE.md
├── THIRD_PARTY_NOTICES.md              # Licenses of the software inside the .deb, and where its source is
└── LICENSE                             # MIT License
```

## Build Artifacts (Not Tracked)

- `build/`, `dist/` – PyInstaller output
- `debian/`, `*.deb` – package build output
- `yt-dlp`, `deno` – downloaded at package build time
- `__pycache__/`
- `.flatpak-builder/` – Flatpak build cache

See [INSTALL.md](INSTALL.md) for build instructions.
