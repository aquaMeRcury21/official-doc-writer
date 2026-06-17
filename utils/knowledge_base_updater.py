"""
知识库更新器 —— 扫描 `kb-inbox/` 目录下的文件，自动分类入库。
支持格式：.txt, .md, .docx, .pdf, .xlsx

用法：
    python utils/knowledge_base_updater.py
    或从代码调用：
        from utils.knowledge_base_updater import process_all
        result = process_all()
"""

import logging
import re
from datetime import datetime
from pathlib import Path

from .document_parser import read_document
from .rag_engine import LAYER_DIRS, RAGEngine
from .settings import ROOT as PROJECT_ROOT

logger = logging.getLogger(__name__)

SOURCE_DIR = PROJECT_ROOT / 'kb-inbox'

SUPPORTED_EXTS = {'.txt', '.md', '.docx', '.pdf', '.xlsx'}

GLOBAL_THRESHOLD = 2

GLOBAL_KEYWORDS = [
    '习近平', '总书记', '中共中央', '国务院', '省委', '省政府',
    '省人民政府', '市人民政府', '管理办法', '实施意见',
    '条例', '法规', '纲要', '规划', '总体方案',
    '关于深化', '关于加强', '关于进一步', '关于促进',
    '决定',
]

CATEGORY_RULES = [
    ('通知', ['通知如下', '特此通知', '请遵照执行', '现将有关事项通知如下',
              '现就有关事项通知如下', '请认真贯彻执行', '将有关事项通知如下']),
    ('请示', ['请示如下', '妥否，请批示', '特此请示', '当否，请批示',
              '请予批准', '请审批', '现就有关问题请示如下']),
    ('报告', ['现报告如下', '现将有关情况报告如下', '特此报告',
              '现就有关情况报告如下', '现就有关工作情况报告如下']),
    ('讲话稿', ['同志们：', '同志们，', '在此，我代表', '我讲几点意见',
                '强调以下几点', '表示热烈欢迎', '讲几点意见']),
    ('总结', ['工作总结', '回顾过去一年', '一年来，', '半年来，',
              '主要做法及成效', '存在的问题', '下一步工作打算']),
    ('方案', ['工作方案', '实施方案', '行动方案', '总体要求',
              '重点任务', '保障措施']),
    ('纪要', ['会议纪要', '会议议定', '会议决定', '会议指出',
              '会议强调', '会议要求', '会议审议']),
    ('简报', ['工作简报', '工作动态', '情况简报', '信息专报']),
    ('函', ['函', '商请函', '复函', '致函']),
]


def classify(text: str) -> tuple[str, str]:
    if not text:
        return ('archive', str(datetime.now().year))

    best_cat = ''
    best_score = 0
    best_ratio = 0.0
    for cat, keywords in CATEGORY_RULES:
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat
            best_ratio = score / len(keywords)
        elif 0 < score == best_score:
            ratio = score / len(keywords)
            if ratio > best_ratio:
                best_ratio = ratio
                best_cat = cat

    if best_score >= 1:
        return ('category', best_cat)

    global_score = sum(1 for kw in GLOBAL_KEYWORDS if kw in text)
    if global_score >= GLOBAL_THRESHOLD:
        return ('global', '')

    year_match = re.search(r'20\d{2}', text)
    year = year_match.group(0) if year_match else str(datetime.now().year)
    return ('archive', year)


def collect_files(source_dir: Path) -> list[Path]:
    files = []
    for f in sorted(source_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            files.append(f)
    return files


def process_all(source_dir: str | Path | None = None) -> dict:
    if source_dir is None:
        source_dir = SOURCE_DIR
    source_dir = Path(source_dir)

    if not source_dir.is_dir():
        logger.warning('目录不存在，自动创建: %s', source_dir)
        source_dir.mkdir(parents=True, exist_ok=True)
        return {'warning': f'已创建空目录: {source_dir}', 'processed': 0}

    stats = {
        'processed': 0,
        'deleted': 0,
        'skipped': 0,
        'by_layer': {'global': 0, 'category': 0, 'archive': 0},
        'details': [],
    }

    files = collect_files(source_dir)
    if not files:
        logger.warning('没有找到可处理的文件')
        return {'warning': '没有找到可处理的文件', 'processed': 0}

    affected_layers = set()
    processed = []

    for fpath in files:
        content = read_document(str(fpath))
        if not content:
            stats['skipped'] += 1
            stats['details'].append(f'[跳过] {fpath.name}（无法解析或内容为空）')
            continue

        layer, sub_path = classify(content)
        affected_layers.add(layer)

        if layer == 'global':
            target_dir = Path(LAYER_DIRS['global'])
        elif layer == 'category':
            target_dir = Path(LAYER_DIRS['category']) / sub_path
        else:
            target_dir = Path(LAYER_DIRS['archive']) / sub_path

        target_dir.mkdir(parents=True, exist_ok=True)

        stem = fpath.stem
        txt_name = f'{stem}.txt'
        txt_path = target_dir / txt_name

        counter = 1
        while txt_path.exists():
            txt_path = target_dir / f'{stem}_{counter}.txt'
            counter += 1

        txt_path.write_text(content, encoding='utf-8')
        processed.append(fpath)

        stats['processed'] += 1
        stats['by_layer'][layer] += 1

        layer_labels = {
            'global': 'global-knowledge',
            'category': f'category-knowledge/{sub_path}',
            'archive': f'archive/{sub_path}',
        }
        stats['details'].append(
            f'[OK] {fpath.name} → 知识库/{layer_labels[layer]}/{txt_name}'
        )

    for layer in affected_layers:
        try:
            rag = RAGEngine()
            rag._build_layer_index(layer, force=True)
            stats['details'].append(f'[索引] {layer} 层已重建')
        except Exception as e:
            stats['details'].append(f'[索引] {layer} 层重建失败: {e}')
            continue

    for fpath in processed:
        try:
            fpath.unlink()
            stats['deleted'] += 1
        except Exception as e:
            stats['details'].append(f'[删除失败] {fpath.name}: {e}')

    return stats


def print_report(stats: dict):
    print('\n处理报告：')
    print(f'  已处理：{stats.get("processed", 0)} 个文件')
    print(f'  已删除：{stats.get("deleted", 0)} 个原文件')
    print(f'  跳过：{stats.get("skipped", 0)} 个')

    by_layer = stats.get('by_layer', {})
    if any(by_layer.values()):
        labels = {
            'global': '  → global-knowledge（政策文件/领导讲话）',
            'category': '  → category-knowledge（按文种分类）',
            'archive': '  → archive（归档）',
        }
        for layer, label in labels.items():
            if by_layer.get(layer, 0) > 0:
                print(f'{label}: {by_layer[layer]} 个')

    print()
    for d in stats.get('details', []):
        print(f'  {d}')

    if 'warning' in stats:
        print(f'\n[警告] {stats["warning"]}')
    if 'error' in stats:
        print(f'\n[错误] {stats["error"]}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    result = process_all()
    print_report(result)
