# Flatpak / Flathub packaging

App ID: `io.github.ngquocvuong.mdj-music-downloader`. It must match the GitHub repo name, as Flathub requires.

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

The app detects the Flatpak (`/.flatpak-info`). Inside it, the app hides "Update yt-dlp" and uses only the bundled yt-dlp, because Flathub doesn't allow apps to download and run code. It also saves its settings in `~/.var/app/<id>/config`. yt-dlp updates arrive as new Flatpak versions instead.

## Test build on this computer

```bash
B=~/.cache/mdj-flatpak-build
flatpak run org.flatpak.Builder --user --force-clean --state-dir=$B/state \
    --repo=$B/repo $B/build flatpak/io.github.ngquocvuong.mdj-music-downloader.yml
flatpak --user remote-add --if-not-exists --no-gpg-verify mdj-local $B/repo
flatpak --user install mdj-local io.github.ngquocvuong.mdj-music-downloader   # first time
flatpak --user update io.github.ngquocvuong.mdj-music-downloader              # after rebuilds
flatpak run io.github.ngquocvuong.mdj-music-downloader
```

Lint, which uses the same checks as Flathub:

```bash
L="flatpak run --command=flatpak-builder-lint org.flatpak.Builder"
$L manifest flatpak/io.github.ngquocvuong.mdj-music-downloader.yml
$L appstream flatpak/io.github.ngquocvuong.mdj-music-downloader.metainfo.xml
$L repo ~/.cache/mdj-flatpak-build/repo
```

## Before submitting (release v1.1.0)

1. Set `APP_VERSION = "1.1.0"` in the app and the version in `build-deb.sh` and `INSTALL.sh`, update the `.deb` file names in README.md, INSTALL.md and RELEASE_NOTES.md, set the date in CHANGELOG.md, and update the `<release>` date and notes in the metainfo.
2. Commit, tag `v1.1.0` and push. The screenshot URL in the metainfo points to the tag, so the linter's screenshot warning goes away once the tag exists.
3. In the manifest, replace the `type: dir` source with the `type: git` block that's commented out there, using the tag and its commit hash.
4. Check whether newer versions of the Python wheels (yt-dlp especially) are available, and update their URLs and sha256 checksums.
5. Check whether the runtime's Python is still 3.14.9. If not, change the `Python-3.14.9.tar.xz` source to match.
6. Rebuild, test a download, and run all three lint commands.

## Submitting to Flathub

1. Fork https://github.com/flathub/flathub. Uncheck "Copy the master branch only".
2. Create a branch from `new-pr`, and add only the manifest (`.yml`) to it.
3. Open a pull request against the `new-pr` branch, titled `Add io.github.ngquocvuong.mdj-music-downloader`.
4. Reply to the reviewers. You can start a test build by commenting `bot, build`.
5. After the pull request is merged, you get your own repo at `flathub/io.github.ngquocvuong.mdj-music-downloader`. You release future updates by changing the manifest there.
