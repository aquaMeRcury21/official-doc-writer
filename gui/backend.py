"""GUI 工具函数 —— 封装与后端模块的交互"""

import shutil
import sys
from pathlib import Path


def _init_workspace():
    """frozen 模式下首次启动时自解压知识库等资源到 exe 目录"""
    if not getattr(sys, 'frozen', False):
        return
    exe_dir = Path(sys.executable).resolve().parent
    sentinel = exe_dir / '.workspace_initialized'
    if sentinel.exists():
        return
    try:
        meipass = Path(sys._MEIPASS)
    except AttributeError:
        return
    # 自解压 knowledge-base
    src_kb = meipass / 'knowledge-base'
    if src_kb.exists():
        dst_kb = exe_dir / 'knowledge-base'
        if not dst_kb.exists():
            shutil.copytree(src_kb, dst_kb)
    # 创建 output 目录
    (exe_dir / 'output').mkdir(parents=True, exist_ok=True)
    # 创建 archive 子目录
    (exe_dir / 'knowledge-base' / 'archive').mkdir(parents=True, exist_ok=True)
    # 生成默认 .env 模板
    env_dst = exe_dir / '.env'
    if not env_dst.exists():
        env_dst.write_text(
            '# 公文撰写工作站环境配置\n'
            '# 请在 GUI 设置页填入 API Key\n'
            'DEEPSEEK_API_KEY=\n'
            'DEEPSEEK_BASE_URL=https://api.deepseek.com\n',
            encoding='utf-8',
        )
    sentinel.write_text('', encoding='utf-8')


def _project_root() -> Path:
    """获取项目根目录（兼容 PyInstaller 打包模式）。"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# 在解析 PROJECT_ROOT 之前先初始化工作区
_init_workspace()

PROJECT_ROOT = _project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 修正 utils.settings 中的 ROOT 指向真实项目目录
try:
    import utils.settings as _settings

    _settings.ROOT = PROJECT_ROOT
    _settings.KNOWLEDGE_BASE = PROJECT_ROOT / 'knowledge-base'
    _settings.WORKING_DIR = PROJECT_ROOT / 'workspace'
    _settings.ARCHIVE_DIR = _settings.KNOWLEDGE_BASE / 'archive'
except ImportError:
    pass

from utils.api_client import (
    DeepSeekClient,
)


def deepseek_client() -> DeepSeekClient:
    """获取已配置的 DeepSeek 客户端实例"""
    return DeepSeekClient.from_env()
