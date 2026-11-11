#!/bin/sh
# Flatpak launcher: run the app with the sandbox's Python.
exec python3 /app/share/mdj-music-downloader/music_downloader_customtkinter.py "$@"
