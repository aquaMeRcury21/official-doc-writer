"""
文件工具 —— 临时文件归档、路径处理等。
"""

import logging
import os
import shutil

from utils.settings import WORKING_DIR

logger = logging.getLogger(__name__)


def archive_working_files(target_dir: str) -> list[str]:
    """将 `当前工作/` 下的所有文件移动到目标目录。

    用于：起草公文时从 `当前工作/` 读取临时参考文件，
    生成正式 .docx 后自动归档到同一目录，方便追溯。

    Args:
        target_dir: 目标目录（生成的 .docx 所在目录）

    Returns:
        移动的文件名列表
    """
    if not os.path.isdir(WORKING_DIR):
        logger.info('当前工作目录不存在，跳过: %s', WORKING_DIR)
        return []

    os.makedirs(target_dir, exist_ok=True)
    moved = []

    for fname in os.listdir(WORKING_DIR):
        src = os.path.join(WORKING_DIR, fname)
        if not os.path.isfile(src):
            continue
        if fname.startswith('.'):
            continue
        dst = os.path.join(target_dir, fname)
        # 目标已存在则加时间戳后缀
        if os.path.exists(dst):
            stem, ext = os.path.splitext(fname)
            dst = os.path.join(target_dir, f'{stem}_{int(os.path.getmtime(src))}{ext}')
        shutil.move(src, dst)
        moved.append(fname)
        logger.info('归档临时文件: %s → %s', src, dst)

    if moved:
        logger.info('共归档 %d 个临时文件到 %s', len(moved), target_dir)
    else:
        logger.info('当前工作目录无临时文件')

    return moved
