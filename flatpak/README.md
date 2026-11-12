# Flatpak packaging

MDJ Music Downloader is **not on Flathub**. The main download is the `.deb` on the [Releases page](https://github.com/ngquocvuong/mdj-music-downloader/releases). This folder lets you build and install a Flatpak yourself if you prefer one.

App ID: `io.github.ngquocvuong.mdj-music-downloader` (it follows the GitHub repo name).

| File | What it is |
|---|---|
| `io.github.ngquocvuong.mdj-music-downloader.yml` | Build recipe (manifest) |
| `io.github.ngquocvuong.mdj-music-downloader.metainfo.xml` | Store page: description, screenshots, releases |
| `io.github.ngquocvuong.mdj-music-downloader.desktop` | Menu entry |
| `mdj-music-downloader.sh` | Launcher (`/app/bin/mdj-music-downloader`) |

What goes into the Flatpak:
- Tcl/Tk 8.6 and Python's `tkinter`. The runtime's Python doesn't include them.
- customtkinter 5.2.2
- mutagen, which writes cover art and tags
- yt-dlp, with yt-dlp-ejs
- Node.js, the JavaScript engine yt-dlp needs for YouTube
- ffmpeg, which comes from the runtime

The app detects the Flatpak (`/.flatpak-info`). Inside it, the app hides "Update yt-dlp" and uses only the bundled yt-dlp, because the app's files in the Flatpak are read-only. It also saves its settings in `~/.var/app/<id>/config`. To get a newer yt-dlp, update its wheel in the manifest (see below) and rebuild.

## Build and install

You need `flatpak` and `org.flatpak.Builder` (`flatpak install flathub org.flatpak.Builder`). Run these from the repo folder:

```bash
B=~/.cache/mdj-flatpak-build
flatpak run org.flatpak.Builder --user --force-clean --state-dir=$B/state \
    --repo=$B/repo $B/build flatpak/io.github.ngquocvuong.mdj-music-downloader.yml
flatpak --user remote-add --if-not-exists --no-gpg-verify mdj-local $B/repo
flatpak --user install mdj-local io.github.ngquocvuong.mdj-music-downloader   # first time
flatpak --user update io.github.ngquocvuong.mdj-music-downloader              # after rebuilds
flatpak run io.github.ngquocvuong.mdj-music-downloader
```

This installs it for your account only. To install it for every account on the computer, use the system installation instead:

```bash
sudo flatpak remote-add --if-not-exists --no-gpg-verify mdj-local $B/repo
sudo flatpak install mdj-local io.github.ngquocvuong.mdj-music-downloader
```

(The system installation also needs the freedesktop 26.08 runtime: `sudo flatpak install flathub org.freedesktop.Platform//26.08`.)

Optional lint, which checks the manifest, metainfo and build:

```bash
L="flatpak run --command=flatpak-builder-lint org.flatpak.Builder"
$L manifest flatpak/io.github.ngquocvuong.mdj-music-downloader.yml
$L appstream flatpak/io.github.ngquocvuong.mdj-music-downloader.metainfo.xml
$L repo ~/.cache/mdj-flatpak-build/repo
```

## Updating for a new release

1. Set the new `APP_VERSION` in the app and the version in `build-deb.sh` and `INSTALL.sh`, update the `.deb` file names in README.md, INSTALL.md and RELEASE_NOTES.md, set the date in CHANGELOG.md, and add a `<release>` with its date and notes to the metainfo.
2. Check whether newer versions of the Python wheels (yt-dlp especially) are available, and update their URLs and sha256 checksums in the manifest.
3. Check whether the runtime's Python is still 3.14.9. If not, change the `Python-3.14.9.tar.xz` source to match.
4. Rebuild, test a download, and run the lint commands.
5. Commit, tag the version (for example `v1.2.0`) and push. The screenshot URLs in the metainfo point to the tag.
