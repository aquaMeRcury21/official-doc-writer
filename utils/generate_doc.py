"""
通用公文生成脚本 —— 读取 _data/ 中的数据文件和模板，生成 .docx + .txt。

使用方式：
    python -m utils.generate_doc --dir 20260401——宣讲比赛活动 --doc 方案
    python -m utils.generate_doc --dir 20260401——宣讲比赛活动 --doc all
    python -m utils.generate_doc --dir 20260401——宣讲比赛活动 --doc 方案 --no-budget
"""

import argparse
import json
import os
import re
from pathlib import Path

from utils.settings import ROOT

# {{变量名}} 占位符正则
_PH_RE = re.compile(r'\{\{(.+?)\}\}')

# {{#列表名}}...{{/列表名}} 循环块正则
_BLOCK_RE = re.compile(r'\{\{#(.+?)\}\}(.*?)\{\{/\1\}\}', re.DOTALL)


def _resolve(value, context: dict):
    """从 context 中解析 'a.b.c' 路径的值。"""
    parts = value.split('.')
    cur = context
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p, '')
        elif isinstance(cur, list):
            try:
                cur = cur[int(p)]
            except (ValueError, IndexError):
                return ''
        else:
            return ''
    if isinstance(cur, (dict, list)):
        return json.dumps(cur, ensure_ascii=False)
    return str(cur) if cur is not None else ''


def _fill_template(template_text: str, data: dict) -> str:
    """将模板中的 {{变量}} 和 {{#列表}} 替换为实际数据。"""
    context = {**data.get('fields', {}), **data.get('meta', {}),
               'title': data.get('title', ''), 'docType': data.get('docType', ''),
               'date': data.get('date', '')}
    # 加入 lists 中的每个条目可作为 context 子键
    for k, v in data.get('lists', {}).items():
        context[k] = v

    text = template_text

    # 处理循环块 {{#list}}...{{/list}}
    def _replace_block(m):
        list_name = m.group(1).strip()
        block_body = m.group(2)
        # 直接从 context 取列表（不走 _resolve，避免 JSON 序列化）
        items = context.get(list_name, [])
        if not isinstance(items, list):
            return ''
        parts = []
        for item in items:
            item_ctx = context.copy()
            if isinstance(item, dict):
                item_ctx.update(item)
            else:
                item_ctx['.'] = item
            # 递归填充块内占位符
            filled = _fill_template(block_body, {'fields': item_ctx,
                                                   'lists': data.get('lists', {}),
                                                   'meta': data.get('meta', {}),
                                                   'title': data.get('title', ''),
                                                   'docType': data.get('docType', ''),
                                                   'date': data.get('date', '')})
            parts.append(filled)
        return ''.join(parts)

    text = _BLOCK_RE.sub(_replace_block, text)

    # 处理简单占位符 {{变量}}
    def _replace_ph(m):
        key = m.group(1).strip()
        return _resolve(key, context)

    text = _PH_RE.sub(_replace_ph, text)
    return text


def _find_data_dir(event_dir: str) -> Path:
    """在事件文件夹下找 _data/ 子目录。"""
    base = ROOT / event_dir
    data_dir = base / '_data'
    if not data_dir.exists():
        # 尝试在全路径中查找
        alt = Path(event_dir) / '_data' if os.path.isabs(event_dir) else None
        if alt and alt.exists():
            return alt
        raise FileNotFoundError(f'未找到 _data/ 目录: {data_dir}')
    return data_dir


def _find_template(data_dir: Path, doc_type: str, templates_map: dict) -> tuple[str, Path]:
    """根据文种和模板映射找到对应模板文件。"""
    # 优先从 templates 映射查找
    if doc_type in templates_map:
        tname = templates_map[doc_type]
        tpath = data_dir / tname
        if tpath.exists():
            return tname, tpath

    # 文件名前缀匹配兜底（约定格式：{文种}模板.txt）
    for fname in sorted(data_dir.iterdir()):
        if fname.suffix == '.txt' and fname.stem == f'{doc_type}模板':
            return fname.name, fname

    raise FileNotFoundError(f'未找到文种 "{doc_type}" 对应的模板文件')


def generate_doc(event_dir: str, doc_type: str = 'all',
                 no_budget: bool = False) -> list[Path]:
    """生成公文。

    Args:
        event_dir: 事件文件夹路径（相对于项目根或绝对路径）
        doc_type: 文种，如 "方案" / "主持词" / "all"
        no_budget: 是否跳过预算字段

    Returns:
        生成的 .docx 文件路径列表
    """
    # 定位数据目录
    data_dir = _find_data_dir(event_dir)
    data_file = data_dir / '公文数据.json'

    if not data_file.exists():
        raise FileNotFoundError(f'未找到数据文件: {data_file}')

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 解析 doc_type 列表
    if doc_type == 'all':
        doc_types = list(data.get('templates', {}).keys())
        # 再按文件名前缀补全
        if not doc_types:
            for f in sorted(data_dir.iterdir()):
                if f.suffix == '.txt' and f.stem.endswith('模板'):
                    dt = f.stem.replace('模板', '')
                    if dt and dt not in doc_types:
                        doc_types.append(dt)
    else:
        doc_types = [doc_type]

    if not doc_types:
        raise ValueError('未指定任何文种')

    results = []
    from utils.document_generator import write_docx

    for dt in doc_types:
        # 找模板文件
        tname, tpath = _find_template(data_dir, dt, data.get('templates', {}))
        template_text = tpath.read_text(encoding='utf-8')

        # 填充占位符
        filled_text = _fill_template(template_text, data)

        # 解析填充后的文本为段落
        lines = filled_text.split('\n')
        body = [ln for ln in lines if ln.strip()]

        # 提取标题（第一行）和其他信息
        title = data.get('title', '')
        category = data.get('meta', {}).get('category', '0004——模板')
        year = data.get('meta', {}).get('year')

        # 确定事件文件夹名（从 event_dir 取最后一段）
        event_folder = (Path(event_dir).name if not os.path.isabs(event_dir)
                        else Path(event_dir).name)

        # 调用 write_docx 生成
        docx_path = write_docx(
            title=title,
            doc_number=data.get('meta', {}).get('docNumber', ''),
            body=body,
            category=category,
            year=year,
            event_folder=event_folder,
            filename_stem=f'{dt}模板生成',
        )
        results.append(docx_path)
        print(f'[OK] 文种 "{dt}" → {docx_path}')

    return results


def main():
    parser = argparse.ArgumentParser(description='公文生成脚本')
    parser.add_argument('--dir', required=True, help='事件文件夹路径')
    parser.add_argument('--doc', default='all', help='文种（方案/主持词/致辞/all）')
    parser.add_argument('--no-budget', action='store_true', help='跳过预算字段')
    args = parser.parse_args()

    generate_doc(args.dir, args.doc, args.no_budget)


if __name__ == '__main__':
    main()
