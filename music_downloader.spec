# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['music_downloader_customtkinter.py'],
    pathex=[],
    binaries=[],
    datas=[('icons', 'icons')],
    hiddenimports=['mutagen', 'mutagen.id3', 'mutagen.mp4', 'mutagen.flac', 'mutagen.oggopus',
                   'mutagen.oggvorbis', 'mutagen.wave'],   # tags + covers (imported inside functions)
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='music_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
