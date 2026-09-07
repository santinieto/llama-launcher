# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/llama.cpp/app/main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:/llama.cpp/config', 'config')],
    hiddenimports=['app', 'app.core', 'app.gui', 'app.models'],
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
    [],
    exclude_binaries=True,
    name='LocalLLMManager',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LocalLLMManager',
)
