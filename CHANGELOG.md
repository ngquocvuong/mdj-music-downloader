# Changelog

All notable changes to MDJ Music Downloader will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - Unreleased

### Added
- **Flatpak package**, ready for Flathub (app ID `io.github.ngquocvuong.mdj-music-downloader`). It includes yt-dlp, ffmpeg and Node.js (which yt-dlp needs for YouTube), so nothing else has to be installed. In the Flatpak, yt-dlp is updated with the app, so "Update yt-dlp" is hidden.
- **New yt-dlp Settings window** with two tabs:
  - **Basic:** choose the audio format (mp3, m4a, opus, flac, wav) and quality, the video quality (best, 4K, 1440p, 1080p, 720p, 480p), add cover art and title/artist tags to files, and use your browser's login (cookies) for age-restricted videos (not in the Flatpak).
  - **Advanced:** custom yt-dlp options with step-by-step help when the box is empty, a **Check** button that asks yt-dlp whether it accepts them, links to the yt-dlp option list and format guide, and a live preview of the full command the app will run.
  - Both tabs are used together. When a custom option changes a Basic setting (e.g. `--audio-format flac`), the custom option is used, and that Basic setting is locked with a note saying why.
  - Save checks the options first, so a typo can't break every download.
- Under **Download Type**, a small line shows what the selected type saves as, e.g. "MP3 · best quality" or "MP4 · up to 1080p".
- **Songs already in a folder are not downloaded again**, even after track numbering renamed them. Retrying a playlist only tries the songs that are missing. A song you deleted can be downloaded again. Downloading a song you already have says "Already downloaded". (Each download folder keeps a small hidden record, `.mdj-tracks.json`.)
- In the Flatpak on older desktops (e.g. Linux Mint 21), **Import** shows the queue files in your Output Folder to pick from, with "Other folder..." for the system file chooser. Their file chooser can't open a chosen folder directly.
- Lists (the queue, Supported Sites, settings) scroll with the mouse wheel.

### Changed
- Default download folder is now `~/Music/MDJ Downloads`. If your settings still used the old default (`~/Music/YouTube MP3`), they switch to the new one; folders you chose yourself are kept.
- A link to a song inside a playlist (`watch?v=...&list=...`, including YouTube Mixes) now downloads **only that song**. Playlist links still download the whole list. Add `--yes-playlist` in Custom arguments to get the old behaviour.
- The Download Type buttons now just say **Audio** and **Video**.
- "URL pasted" and "Added to queue" messages show only the first time per session. Notifications are smaller, and only one shows at a time.
- Quieter **?** (Supported Sites) button: a small grey circle that turns teal under the mouse.
- Thinner borders on buttons, panels, text fields and checkboxes.
- The window opens on the monitor under the mouse, also where the `xrandr` program is missing.
- "Saved to:" shows your home folder as `~` (e.g. `~/Music/MDJ Downloads`), which is shorter and easier to read.

### Fixed
- **Track numbering in an existing album folder.** New songs now continue after the highest number (`01`, `02` → `03`). Before, numbering restarted at `01` on every run, giving two songs the same number, or replacing a song when the file names matched.
- Track numbering could rename the wrong file (another song, or the playlist file) when a song was already in the folder.
- Every song from a playlist link is now numbered, not only the last one.
- When one video in a playlist is unavailable, the other songs are still numbered and added to the album's playlist file.
- Downloading a song that is already numbered in the album no longer adds a second copy.
- The single **Download** button now numbers songs too.
- The album's `.m3u` playlist file is updated after every download (also single downloads and cancelled queues). It is named after the real folder, so typing "rock" for an existing "Rock" folder no longer makes a second playlist file. Numbered songs come first, in order (99 before 100).
- Song titles that start with a number, like "99.9 FM", keep their number.
- An album name with "/" (e.g. "AC/DC") no longer creates sub-folders.
- Custom arguments: an option and its value on one line (e.g. `--cookies-from-browser firefox`, the example the app itself showed) was rejected by yt-dlp with "no such option". Lines are now split like on the command line, and quotes work. Settings saved by older versions are fixed automatically.
- The bottom of the yt-dlp Settings window ("Advanced Settings") was cut off on smaller screens.
- File choosers opened your home folder when the Output Folder didn't exist yet (nothing downloaded). They now start in the nearest folder that exists, e.g. `~/Music`.

## [1.0.3] - 2026-11-09

### Added
- "Supported Sites" is now a small round **?** button next to "Video/Audio URL" (with a "Supported sites" tooltip), freeing room in the left panel.
- Click the folder path after "Saved to:" to open it in your file manager (underlined when the mouse is over it) — for single downloads and queues, including the Album/Folder subfolder.
- "Update yt-dlp" works for every user on a shared computer: with an administrator password it updates yt-dlp for all users; without one (or if the password prompt is cancelled) it updates it just for that user, in `~/.local/share/mdj-music-downloader/`. The app always uses the newest working copy.
- "Already up to date" check, so no password is asked for when there is nothing to update.

### Changed
- While a queue is downloading you can keep adding songs (+ Queue, Paste, Import); they are downloaded in the same run.
- "Download Queue (N)" now counts only the songs still to download. Songs that failed are tried again on the next run; finished songs are not downloaded again.
- Duplicate detection recognises the same YouTube video whatever the link looks like (youtu.be, watch?v=, shorts, "?si=" share codes), also when importing.
- Import reports what it skipped (already in the queue, or lines that are not links) and reads files saved with a byte-order mark or Windows line endings.
- New colour scheme matching the MDJ icon: teal accents (buttons, progress bars, checkbox) with dark navy text on teal buttons, instead of the default blue.
- "Download Type" is now a two-part switch: the selected type (Audio or Video) is filled teal, the other stays dark.
- Tooltips and pop-up messages are now classic light yellow with dark text.
- The header title and subtitle are centred together, with more space above the title.
- Output Folder, Export and Import now use your desktop's own modern file chooser (with sidebar, bookmarks and breadcrumbs) instead of the old-style Tk dialog. The old dialog is still used if no system chooser is available.

### Fixed
- Cancel did nothing if pressed between two songs (or while a video link was being checked); the queue carried on. It now always stops, including yt-dlp's ffmpeg process.
- Cancel and then Download straight away could let the cancelled song report back into the new run (wrong song marked failed, two downloads at once).
- Removing a song from the queue during a download made the app pause, mark the wrong song and skip the next one. While downloading, the X buttons are now disabled (press Cancel first).
- Removing a song from the queue redrew every row as "waiting", so finished (✓) and failed songs lost their status. Now only that row is removed.
- Closing the app during a queue download started the next song in the background.
- The app could freeze for good (and then not close) when a background task (the yt-dlp check at startup, loading Supported Sites, updating yt-dlp, or a download) talked to the window at the same moment as the window was redrawing. Background tasks now hand their updates to the window safely.
- Clicking X now always closes the app, and stops a running download; problems while closing or in buttons are written to ~/.cache/mdj-music-downloader/errors.log.
- After Clear Queue the left panel could change width, leaving the Paste and + Queue buttons cut off at the right. The left panel now has a fixed width.
- Clicking **?** (Supported Sites) froze the app for about 2 seconds with nothing on screen. The window now opens immediately with "Loading supported sites..." and a progress bar; the list is loaded in the background, preloaded shortly after startup, and kept for next time. Search is faster and shows how many sites match.
- At startup the window briefly appeared in the top-left corner of the screen and then jumped to the centre; it now opens centred straight away.
- The menu entry now asks the desktop for launch feedback (busy cursor while the app starts), and the app tells the desktop when it has finished loading, so the cursor turns back into an arrow straight away.
- yt-dlp Settings opened about twice as fast, and shows "Loading settings..." straight away instead of a frozen app.
- After a queue finished, the result message was cleared straight away. It now stays and shows where the files were saved, e.g. "Queue complete: 3 downloaded, 0 failed / Saved to: ~/Music/My Album" (including the Album/Folder subfolder).
- Queue summary counted songs finished in an earlier run; it now counts only the current run.
- Long URLs in the queue squeezed the X (remove) button. The URL is now shortened with "..." to fit the space, and re-fits when the window is resized; the X button keeps its size.
- The left and right panels no longer change width when a download finishes; they keep the size the app opens with.
- The top border of the left panel was hidden behind the "Video/Audio URL" row; it is now fully visible.
- The download progress bar and messages were cut off at the bottom of the left panel during and after downloads.
- Updating yt-dlp asked for the administrator password twice; now once.
- Opening the browser (Support Development) or file manager from the installed app now uses the system's own libraries instead of the app's bundled ones, which could make them fail to start.
- Updating failed for a second user on the same computer (shared temporary file in /tmp).
- The window froze for a few seconds at startup while yt-dlp was checked; the check now runs in the background.

## [1.0.2] - 2026-11-09

### Fixed
- Downloads failed with "yt-dlp error" on Ubuntu 22.04 / Linux Mint 21 and other systems with Python older than 3.11. The package and the in-app updater now use yt-dlp's standalone Linux build, which includes its own Python.
- The in-app yt-dlp updater checks that the downloaded file runs before installing it, and allows more time on slow connections.

## [1.0.1] - 2026-11-09

### Changed
- "Support Development" button and docs now link to the new Ko-fi page: https://ko-fi.com/mdj_musicdl

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

[1.0.3]: https://github.com/ngquocvuong/mdj-music-downloader/releases/tag/v1.0.3
[1.0.2]: https://github.com/ngquocvuong/mdj-music-downloader/releases/tag/v1.0.2
[1.0.1]: https://github.com/ngquocvuong/mdj-music-downloader/releases/tag/v1.0.1
[1.0.0]: https://github.com/ngquocvuong/mdj-music-downloader/releases/tag/v1.0.0
