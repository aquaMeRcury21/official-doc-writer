"""Project-wide configuration constants.

Usage:
    from utils.settings import ORG_NAME, KNOWLEDGE_BASE
"""

from pathlib import Path

# Project root (two levels up from utils/)
ROOT = Path(__file__).resolve().parent.parent

# === File system paths ===
KNOWLEDGE_BASE = ROOT / 'knowledge-base'
WORKING_DIR = ROOT / 'workspace'
ARCHIVE_DIR = KNOWLEDGE_BASE / 'archive'

# === Organization placeholders ===
# Replace these with your actual information before use.
ORG_NAME = '[单位名称]'
ORG_SHORT = '[发文机关简称]'
ORG_CODE = '[发文机关代字]'
PLACE_NAME = '[地名]'
WECHAT_ACCOUNT = '[公众号名称]'
