#!/bin/bash
#
# MDJ Music Downloader - Public Release Installation Script
# Version: 1.0.1
# This script installs MDJ Music Downloader for all users on the system
#

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       MDJ Music Downloader - Installation Script          ║"
echo "║                    Version 1.0.1                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script requires sudo privileges to install system-wide."
    echo "   Please run: sudo $0"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/mdj-music-downloader"

echo "📦 Installation directory: $INSTALL_DIR"
echo ""

# Step 1: Create installation directory
echo "[1/6] Creating installation directory..."
mkdir -p "$INSTALL_DIR"

# Step 2: Install main application binary
echo "[2/6] Installing application binary..."
if [ ! -f "$SCRIPT_DIR/dist/music_downloader" ]; then
    echo "❌ Error: Binary not found at $SCRIPT_DIR/dist/music_downloader"
    echo "   Please run ./build.sh first!"
    exit 1
fi

cp "$SCRIPT_DIR/dist/music_downloader" "$INSTALL_DIR/music_downloader"
chmod 755 "$INSTALL_DIR/music_downloader"
echo "   ✅ Binary installed ($(du -h "$INSTALL_DIR/music_downloader" | cut -f1))"

# Step 3: Install icon
echo "[3/6] Installing application icon..."
if [ -d "$SCRIPT_DIR/icons" ]; then
    for size in 32 48 64 128 256 512; do
        dir="/usr/share/icons/hicolor/${size}x${size}/apps"
        mkdir -p "$dir"
        cp "$SCRIPT_DIR/icons/mdj-music-downloader-${size}.png" "$dir/mdj-music-downloader.png"
    done
    mkdir -p /usr/share/icons/hicolor/scalable/apps
    cp "$SCRIPT_DIR/icons/mdj-music-downloader.svg" /usr/share/icons/hicolor/scalable/apps/mdj-music-downloader.svg
    rm -f "$INSTALL_DIR/download_music_64x64.png"
    command -v gtk-update-icon-cache &> /dev/null && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
    echo "   ✅ Icon installed"
else
    echo "   ⚠️  Icon not found (app will work without it)"
fi

# Step 4: Install yt-dlp (if not present or outdated)
echo "[4/6] Installing yt-dlp..."
if [ -f "$INSTALL_DIR/yt-dlp" ]; then
    YTDLP_SIZE=$(stat -c%s "$INSTALL_DIR/yt-dlp")
    if [ "$YTDLP_SIZE" -gt 1000000 ]; then
        echo "   ✅ yt-dlp already installed ($(du -h "$INSTALL_DIR/yt-dlp" | cut -f1))"
        echo "      Use the 'Update yt-dlp' button in the app to update it"
    else
        echo "   ⚠️  Found outdated yt-dlp wrapper, replacing with standalone binary..."
        curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o "$INSTALL_DIR/yt-dlp"
        chmod 755 "$INSTALL_DIR/yt-dlp"
        echo "   ✅ yt-dlp installed ($(du -h "$INSTALL_DIR/yt-dlp" | cut -f1))"
    fi
else
    echo "   Downloading latest yt-dlp..."
    curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o "$INSTALL_DIR/yt-dlp"
    chmod 755 "$INSTALL_DIR/yt-dlp"
    echo "   ✅ yt-dlp installed ($(du -h "$INSTALL_DIR/yt-dlp" | cut -f1))"
fi

# Step 5: Install desktop menu entry
echo "[5/6] Installing desktop menu entry..."
if [ -f "$SCRIPT_DIR/mdj-music-downloader.desktop" ]; then
    cp "$SCRIPT_DIR/mdj-music-downloader.desktop" /usr/share/applications/mdj-music-downloader.desktop
    chmod 644 /usr/share/applications/mdj-music-downloader.desktop

    # Update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database /usr/share/applications/ 2>/dev/null || true
    fi
    echo "   ✅ Desktop entry installed"
else
    echo "   ⚠️  Desktop file not found (creating default...)"
    cat > /usr/share/applications/mdj-music-downloader.desktop <<EOF
[Desktop Entry]
Name=MDJ Music Downloader
Exec=$INSTALL_DIR/music_downloader
Icon=mdj-music-downloader
Type=Application
Categories=AudioVideo;Audio;
Terminal=false
StartupWMClass=mdj-music-downloader
Comment=Download music and videos from YouTube and other sites
EOF
    chmod 644 /usr/share/applications/mdj-music-downloader.desktop
    echo "   ✅ Desktop entry created"
fi

# Step 6: Verify installation
echo "[6/6] Verifying installation..."
ERRORS=0

if [ ! -f "$INSTALL_DIR/music_downloader" ]; then
    echo "   ❌ Binary not found!"
    ERRORS=$((ERRORS+1))
elif [ ! -x "$INSTALL_DIR/music_downloader" ]; then
    echo "   ❌ Binary not executable!"
    ERRORS=$((ERRORS+1))
else
    echo "   ✅ Binary: OK"
fi

if [ ! -f "$INSTALL_DIR/yt-dlp" ]; then
    echo "   ❌ yt-dlp not found!"
    ERRORS=$((ERRORS+1))
elif [ ! -x "$INSTALL_DIR/yt-dlp" ]; then
    echo "   ❌ yt-dlp not executable!"
    ERRORS=$((ERRORS+1))
else
    echo "   ✅ yt-dlp: OK"
fi

if [ -f /usr/share/applications/mdj-music-downloader.desktop ]; then
    echo "   ✅ Desktop entry: OK"
else
    echo "   ⚠️  Desktop entry not found (app will still work)"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ✅ Installation Successful!                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🎵 MDJ Music Downloader is now installed!"
    echo ""
    echo "📖 How to use:"
    echo "   • Launch from application menu: Search for 'MDJ Music Downloader'"
    echo "   • Or run directly: $INSTALL_DIR/music_downloader"
    echo ""
    echo "🔄 To update yt-dlp:"
    echo "   • Open the app and click the 'Update yt-dlp' button"
    echo "   • Or run: sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o $INSTALL_DIR/yt-dlp && sudo chmod 755 $INSTALL_DIR/yt-dlp"
    echo ""
    echo "✨ Features:"
    echo "   ✓ User-friendly error messages"
    echo "   ✓ Download audio (MP3) or video (MP4)"
    echo "   ✓ Queue multiple downloads"
    echo "   ✓ Organize into albums/folders"
    echo "   ✓ Auto-numbering for tracks"
    echo "   ✓ Works on all user accounts"
    echo ""
    echo "📝 Config location: ~/.config/mdj-music-downloader/"
    echo "📥 Default downloads: ~/Music/"
    echo ""
else
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          ⚠️  Installation completed with errors            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Please check the error messages above and try again."
    exit 1
fi
