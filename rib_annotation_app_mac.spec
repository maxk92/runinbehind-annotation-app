# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for rib-annotation-app — macOS
# Build on macOS:  pyinstaller rib_annotation_app_mac.spec

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_qt5agg',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        'lxml._elementpath',
        'lxml.etree',
        'floodlight',
        'floodlight.io.dfl',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RibAnnotationApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX can cause crashes on macOS — leave disabled
    console=False,
    argv_emulation=False,   # do not emulate sys.argv from Apple Events
    target_arch=None,       # None = native arch; use 'universal2' for fat binary
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RibAnnotationApp',
)

app = BUNDLE(
    coll,
    name='RibAnnotationApp.app',
    icon=None,              # replace with path to a .icns file if available
    bundle_identifier='com.yourorg.ribannotation',
    info_plist={
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
