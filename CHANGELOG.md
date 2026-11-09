# Changelog

All notable changes to MDJ Music Downloader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] - 2026-11-01

### Added
- Queue management system for batch downloads
- Automatic .m3u playlist generation for albums
- Smart track numbering with intelligent prefix removal
- Album/folder organization for downloads
- Export and import queue functionality
- URL validation to prevent invalid entries
- Multi-user support with per-user configuration
- Ko-fi donation integration in app UI
- Multi-monitor window positioning support
- Professional dark-themed UI with CustomTkinter

### Fixed
- Download button text not updating when queue changes
- Taskbar icon not highlighting correctly on launch
- Config file permission issues in multi-user environments
- Track numbering incorrectly removing numbers from song titles (e.g., "1 Hour Mix")
- Empty queue label destruction causing crashes

### Changed
- Config files now stored in `~/.config/mdj-music-downloader/` for multi-user compatibility
- Header background changed to sleek black design
- "Settings" button renamed to "Output Folder" for clarity
- Export/Import dialogs now default to download directory

### Technical
- Python 3.8+ required
- Built with CustomTkinter for modern UI
- Uses yt-dlp for download engine
- Packaged as .deb for Debian/Ubuntu systems
- New MDJ app icon (installed into the system icon theme)
- Licensed under MIT License

[1.0.0]: https://github.com/ngquocvuong/mdj-music-downloader/releases/tag/v1.0.0
