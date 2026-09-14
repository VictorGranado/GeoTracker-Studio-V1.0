from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH)
hidden = collect_submodules('pyqtgraph.opengl') + collect_submodules('OpenGL')

a = Analysis(
    ['geotracker_studio_launcher.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root/'assets'), 'assets')],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='GeoTracker Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root/'assets'/'geotracker_studio.ico'),
    version=str(root/'windows_version_info.txt'),
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GeoTracker Studio v1.0.1',
)
