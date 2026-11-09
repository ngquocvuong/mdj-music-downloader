#!/bin/bash
# Build the standalone executable with PyInstaller.
set -e
cd "$(dirname "$0")"

echo "Building MDJ Music Downloader..."
if [ ! -d icons ]; then
    echo "Error: icons/ folder is missing." >&2
    exit 1
fi

pyinstaller --noconfirm music_downloader.spec

echo "Build successful: dist/music_downloader"
echo "Install locally: sudo ./INSTALL.sh   (or build a package: ./build-deb.sh)"
