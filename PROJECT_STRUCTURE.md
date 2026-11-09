# Project Structure

```
mdj-music-downloader/
├── music_downloader_customtkinter.py   # Main application
├── music_downloader.spec               # PyInstaller build specification
├── icons/                              # App icon (SVG + 32–512px PNGs)
├── screenshot.png                      # Screenshot used in README
├── mdj-music-downloader.desktop        # Linux menu entry
├── config.sample.json                  # Example user config
├── build.sh                            # Build executable (dist/music_downloader)
├── build-deb.sh                        # Build .deb package
├── INSTALL.sh                          # Install system-wide without a package
├── README.md, INSTALL.md, CHANGELOG.md, RELEASE_NOTES.md
├── CONFIG_GUIDE.md, YT-DLP_OPTIONS_REFERENCE.md
├── CONTRIBUTING.md, PROJECT_STRUCTURE.md
└── LICENSE                             # MIT License
```

## Build Artifacts (Not Tracked)

- `build/`, `dist/` – PyInstaller output
- `debian/`, `*.deb` – package build output
- `yt-dlp` – downloaded at package build time
- `__pycache__/`

See [INSTALL.md](INSTALL.md) for build instructions.
