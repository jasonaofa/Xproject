# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['art_resource_manager.py'],
    pathex=[], binaries=[],
    datas=[('config.json', '.'), ('version.json', '.'), ('server_config.json', '.'),
           ('app_icon.ico', '.'), ('app_icon_lv.ico', '.'), ('app_icon_bai.ico', '.')],
    hiddenimports=['PIL.Image', 'requests'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='美术资源上传工具_v1.0.32',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    upx_exclude=[], runtime_tmpdir=None, console=False,
    disable_windowed_traceback=False, argv_emulation=False, target_arch=None,
    codesign_identity=None, entitlements_file=None, icon=['app_icon_bai.ico'],
    version='version_info_v1.0.32.txt',
)
