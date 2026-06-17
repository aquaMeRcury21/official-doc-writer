# -*- mode: python ; coding: utf-8 -*-
# 公文撰写工作站 PyInstaller 构建配置
# 使用: pyinstaller 公文撰写工作站.spec

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

PROJECT_ROOT = os.getcwd()
utils_submodules = collect_submodules('utils')

a = Analysis(
    ['gui/main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        ('gui/resources/styles.qss', 'gui/resources'),
        (os.path.join(PROJECT_ROOT, 'knowledge-base'), 'knowledge-base'),
    ],
    hiddenimports=[
        'cffi',
        'gui', 'gui.web_search',
        'utils', 'utils.settings', 'utils.api_client',
        'utils.cost_tracker', 'utils.document_parser',
        'utils.document_generator', 'utils.file_utils',
        'utils.rag_engine', 'utils.knowledge_base_updater',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'PIL', 'cv2', 'pandas',
        'notebook', 'jupyter', 'IPython', 'tests',
        'setuptools', 'wheel', 'pip', 'pygments',
        'pytest', 'prompt_toolkit', 'parso', 'jedi',
    ],
    noarchive=False,
)

# 将 utils/ 目录作为数据树打包
utils_tree = Tree(os.path.join(PROJECT_ROOT, 'utils'),
                  prefix='utils', excludes=['__pycache__'])
a.datas += utils_tree

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='公文撰写工作站',
    debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    runtime_tmpdir=None, console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, codesign_identity=None,
    entitlements_file=None, icon=None,
)
