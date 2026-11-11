#!/bin/bash
# Build a .deb package from dist/music_downloader (run ./build.sh first).
set -e
cd "$(dirname "$0")"

VERSION="1.0.3"
PACKAGE_NAME="mdj-music-downloader"
PKG="debian/${PACKAGE_NAME}"
OUT="${PACKAGE_NAME}_${VERSION}_amd64.deb"

if [ ! -f dist/music_downloader ]; then
    echo "Error: dist/music_downloader not found. Run ./build.sh first." >&2
    exit 1
fi

echo "Building ${OUT}..."
rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt/mdj-music-downloader" "$PKG/usr/share/applications"

# App binary
install -m 755 dist/music_downloader "$PKG/opt/mdj-music-downloader/music_downloader"

# yt-dlp (download engine, kept next to the app so the in-app updater can replace it)
# Must be the standalone build (yt-dlp_linux, an ELF binary with its own Python).
# The plain "yt-dlp" zipapp needs system Python 3.11+ and breaks on Ubuntu 22.04 / Mint 21.
if [ ! -f yt-dlp ] || [ "$(head -c 4 yt-dlp | tail -c 3)" != "ELF" ]; then
    echo "Downloading latest yt-dlp (standalone build)..."
    curl -fL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux -o yt-dlp
    chmod 755 yt-dlp
fi
./yt-dlp --version > /dev/null || { echo "Error: yt-dlp does not run" >&2; exit 1; }
install -m 755 yt-dlp "$PKG/opt/mdj-music-downloader/yt-dlp"

# Icons (installed into the system icon theme)
for size in 32 48 64 128 256 512; do
    dir="$PKG/usr/share/icons/hicolor/${size}x${size}/apps"
    mkdir -p "$dir"
    install -m 644 "icons/mdj-music-downloader-${size}.png" "$dir/mdj-music-downloader.png"
done
mkdir -p "$PKG/usr/share/icons/hicolor/scalable/apps"
install -m 644 icons/mdj-music-downloader.svg "$PKG/usr/share/icons/hicolor/scalable/apps/mdj-music-downloader.svg"

# Menu entry
install -m 644 mdj-music-downloader.desktop "$PKG/usr/share/applications/mdj-music-downloader.desktop"

find "$PKG" -type d -exec chmod 755 {} +
INSTALLED_SIZE=$(du -sk "$PKG" | cut -f1)
cat > "$PKG/DEBIAN/control" <<CTRLEOF
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: sound
Priority: optional
Architecture: amd64
Depends: ffmpeg
Recommends: zenity | kdialog
Installed-Size: ${INSTALLED_SIZE}
Maintainer: MDJ Digital LLC <blackhawk_7585@icloud.com>
Homepage: https://github.com/ngquocvuong/mdj-music-downloader
Description: Modern music and video downloader for Linux
 Download audio and video from YouTube and 1000+ sites.
 Features a numbered download queue, album folders with track numbers,
 cover art and tags for music players, and .m3u playlists.
CTRLEOF

cat > "$PKG/DEBIAN/postinst" <<'POSTEOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
POSTEOF
cp "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"
chmod 755 "$PKG/DEBIAN/postinst" "$PKG/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "$PKG" "$OUT"
echo "Package: $OUT"
echo "Install: sudo apt install ./$OUT"
