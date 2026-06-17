"""
公文查重工具 —— 对新起草文稿逐段比对历史归档（archive 层），
使用 TF-IDF + 余弦相似度直接计算，绕过 ChromaDB HNSW 索引问题。

特别针对讲话稿、季度分析研判会通报等周期性材料，
标注与前次同主题稿件的相似度。

用法：
  python scripts/check_duplicate.py 新文稿.txt
  python scripts/check_duplicate.py --text "一是持续深化理论武装..."
  python scripts/check_duplicate.py 新文稿.txt --top-k 5 --min-score 0.3
  python scripts/check_duplicate.py 新文稿.txt --corpus-size 500
"""

import argparse
import io
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.document_parser import read_document

# ── 配置 ──
PARA_MIN_CHARS = 20
SCORE_HIGH = 0.70
SCORE_MEDIUM = 0.50
ARCHIVE_DIR = os.path.join(Path(__file__).resolve().parents[4], 'knowledge-base', 'archive')

# 排比句式特征词（避免因排比格式导致误判）
PARALLELISM_PATTERNS = re.compile(
    r'^(一是|二是|三是|四是|五是|六是|七是|八是|九是|十是|'
    r'一要|二要|三要|四要|五要|'
    r'坚持|深化|强化|聚焦|突出|着力|统筹|健全|完善|推动|推进|落实|'
    r'持续|深入|扎实|切实|全面|不断)'
)


def read_input(text_path=None, text_str=None):
    if text_path:
        for enc in ['utf-8', 'gbk', 'gb2312']:
            try:
                with open(text_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None
    return text_str


def split_paragraphs(text):
    lines = text.replace('\r\n', '\n').split('\n')
    paragraphs = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) < PARA_MIN_CHARS:
            continue
        if re.match(r'^[一二三四五六七八九十]+[、．\u3001]', stripped) and len(stripped) < 30:
            continue
        if re.match(r'^（[一二三四五六七八九十\d]+）', stripped) and len(stripped) < 30:
            continue
        paragraphs.append({
            'idx': i + 1,
            'text': stripped,
            'preview': stripped[:80],
            'len': len(stripped),
        })
    return paragraphs


def load_corpus(max_files=300, quiet=False):
    """
    从 archive 目录加载对照库文本，分段返回。
    返回 list[{'text': str, 'source': str, 'year': str}]
    """
    if not os.path.isdir(ARCHIVE_DIR):
        if not quiet:
            print(f'[WARN] 对照库不存在: {ARCHIVE_DIR}', file=sys.stderr)
        return []

    segments = []
    file_count = 0

    for root, _, files in os.walk(ARCHIVE_DIR):
        for fname in sorted(files):
            if not fname.endswith('.txt'):
                continue
            if file_count >= max_files:
                break
            fpath = os.path.join(root, fname)
            text = read_document(fpath)
            if not text:
                continue
            file_count += 1
            # 提取年份
            year_match = re.search(r'[/\\\\](20\d{2})[/\\\\]', fpath)
            year = year_match.group(1) if year_match else ''

            # 分段（每段约 500 字符）
            chunk_size = 500
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size].strip()
                if len(chunk) >= PARA_MIN_CHARS:
                    segments.append({
                        'text': chunk,
                        'source': fpath,
                        'year': year,
                    })
        if file_count >= max_files:
            break

    if not quiet:
        print(f'  对照库: {file_count} 个文件, {len(segments)} 个片段', file=sys.stderr)
    return segments


def compute_similarity(paragraphs, corpus_segments, top_k=3, min_score=0.3):
    """
    用 TF-IDF + 余弦相似度计算每段与对照库的相似度。
    """
    if not corpus_segments:
        for p in paragraphs:
            p['matches'] = []
            p['max_score'] = 0.0
            p['match_count'] = 0
        return

    # 合并语料
    all_docs = [p['text'] for p in paragraphs] + [s['text'] for s in corpus_segments]
    n_query = len(paragraphs)

    # TF-IDF 向量化
    vec = TfidfVectorizer(max_features=2048, ngram_range=(1, 2), analyzer='char_wb')
    matrix = vec.fit_transform(all_docs)

    # 余弦相似度
    query_vecs = matrix[:n_query]
    corpus_vecs = matrix[n_query:]
    sim_matrix = cosine_similarity(query_vecs, corpus_vecs)

    for i, p in enumerate(paragraphs):
        scores = sim_matrix[i]
        # 找到 top_k 匹配
        top_indices = scores.argsort()[::-1][:top_k]
        matches = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                continue
            seg = corpus_segments[idx]
            matches.append({
                'score': score,
                'text': seg['text'][:120],
                'source': seg['source'],
                'year': seg['year'],
            })
        p['matches'] = matches
        p['max_score'] = matches[0]['score'] if matches else 0.0
        p['match_count'] = len(matches)


def classify_matches(paragraphs):
    high, medium, matched_any = [], [], []
    for p in paragraphs:
        if p['max_score'] >= SCORE_HIGH:
            high.append(p)
            matched_any.append(p)
        elif p['max_score'] >= SCORE_MEDIUM:
            medium.append(p)
            matched_any.append(p)
        elif p['max_score'] > 0:
            matched_any.append(p)
    return high, medium, matched_any


def compute_overall_similarity(paragraphs):
    if not paragraphs:
        return 0.0
    total_len = sum(p['len'] for p in paragraphs)
    if total_len == 0:
        return 0.0
    weighted = sum(p['max_score'] * p['len'] for p in paragraphs)
    return weighted / total_len


def count_matched_sources(paragraphs):
    sources = []
    for p in paragraphs:
        for m in p.get('matches', []):
            src = m.get('source', '')
            if src:
                sources.append(os.path.basename(src))
    return Counter(sources)


def detect_temporal_repetition(paragraphs):
    year_counts = Counter()
    for p in paragraphs:
        for m in p.get('matches', []):
            year = m.get('year', '')
            if year:
                year_counts[year] += 1
    return year_counts


def build_report(paragraphs, high, medium, overall_sim,
                 source_counter, year_counts, filename,
                 corpus_size, top_k, min_score):
    lines = []
    lines.append('=' * 60)
    lines.append('  公 文 查 重 报 告')
    lines.append('=' * 60)
    lines.append(f'')
    lines.append(f'  文稿: {filename or "直接粘贴文本"}')
    lines.append(f'  总段落: {len(paragraphs)} 段')
    lines.append(f'  对照库: archive 层, {corpus_size} 个片段')
    lines.append(f'  搜索: top_k={top_k}, min_score={min_score}')
    lines.append(f'')
    lines.append(f'  ── 整篇相似度: {overall_sim:.1%} '
                 f'{"⚠️ 偏高" if overall_sim >= SCORE_HIGH else ""}'
                 f'{"🔶 注意" if SCORE_MEDIUM <= overall_sim < SCORE_HIGH else ""}'
                 f'{"✅ 正常" if overall_sim < SCORE_MEDIUM else ""}')
    lines.append(f'')

    if overall_sim >= SCORE_HIGH:
        conclusion = '❌ 驳回重写（与历史文稿高度重复）'
    elif overall_sim >= SCORE_MEDIUM:
        conclusion = '🔶 需修改（标注段落须调整角度或表述）'
    else:
        conclusion = '✅ 通过（无显著重复）'
    lines.append(f'  ── 查重结论: {conclusion}')
    lines.append(f'')

    if year_counts:
        lines.append(f'  ── 时序重复检测（周期性材料风险）:')
        for year, count in sorted(year_counts.items()):
            bar = '█' * min(count // 2 + 1, 20)
            lines.append(f'    {year}: {bar} {count} 段匹配')
        lines.append(f'')

    if high:
        lines.append(f'  ── ⚠️ 高度重复段落（≥{SCORE_HIGH:.0%}）: {len(high)} 处')
        lines.append(f'  {"":-^58}')
        for p in high:
            tm = p['matches'][0]
            src = os.path.basename(tm.get('source', '?'))
            lines.append(f'  ## 第{p["idx"]}段 ({p["max_score"]:.0%}) → {src}')
            lines.append(f'  原文: {p["preview"]}')
            lines.append(f'  建议: 调整论述角度，避免照搬')
            lines.append(f'')
    else:
        lines.append(f'  ✅ 无高度重复段落')
        lines.append(f'')

    if medium:
        lines.append(f'  ── 🔶 中度雷同段落（{SCORE_MEDIUM:.0%}-{SCORE_HIGH:.0%}）: {len(medium)} 处')
        lines.append(f'  {"":-^58}')
        for p in medium:
            tm = p['matches'][0]
            src = os.path.basename(tm.get('source', '?'))
            lines.append(f'  ## 第{p["idx"]}段 ({p["max_score"]:.0%}) → {src}')
            lines.append(f'  原文: {p["preview"]}')
            lines.append(f'  建议: 调整结构或用词')
            lines.append(f'')
    else:
        lines.append(f'  ✅ 无中度雷同段落')
        lines.append(f'')

    if source_counter:
        lines.append(f'  ── 被匹配的历史文稿 Top-10:')
        for src, count in source_counter.most_common(10):
            lines.append(f'    {src}: 匹配 {count} 段')
        lines.append(f'')

    lines.append(f'  {"":-^58}')
    lines.append(f'  ✅ 查重完毕')
    lines.append(f'  {"":=^58}')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='公文查重工具')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('file', nargs='?', help='待查重文本文件路径')
    parser.add_argument('--text', help='直接传入文本内容')
    parser.add_argument('--top-k', type=int, default=3, help='每段返回匹配数 (默认3)')
    parser.add_argument('--min-score', type=float, default=0.3, help='相似度阈值 (默认0.3)')
    parser.add_argument('--corpus-size', type=int, default=300,
                        help='加载多少文件作为对照库 (默认300)')
    parser.add_argument('--output', '-o', help='输出报告到文件')
    parser.add_argument('--quiet', action='store_true')

    args = parser.parse_args()

    if args.file:
        text = read_input(text_path=args.file)
        filename = os.path.basename(args.file)
    elif args.text:
        text = args.text
        filename = '直接粘贴文本'
    else:
        parser.print_help()
        print('\n请提供待查重文本（文件路径或 --text）')
        sys.exit(1)

    if not text:
        print('[ERROR] 无法读取文本')
        sys.exit(1)

    print(f'正在查重... ({len(text)} 字符)', file=sys.stderr)

    paragraphs = split_paragraphs(text)
    print(f'  段落: {len(paragraphs)} 段', file=sys.stderr)

    corpus = load_corpus(max_files=args.corpus_size)
    print(f'  加载对照库: {len(corpus)} 片段', file=sys.stderr)

    print(f'  计算相似度...', file=sys.stderr)
    compute_similarity(paragraphs, corpus, top_k=args.top_k, min_score=args.min_score)
    matched_count = sum(1 for p in paragraphs if p['max_score'] > 0)
    print(f'  存在匹配: {matched_count} 段', file=sys.stderr)

    high, medium, matched_any = classify_matches(paragraphs)
    overall_sim = compute_overall_similarity(paragraphs)
    source_counter = count_matched_sources(paragraphs)
    year_counts = detect_temporal_repetition(paragraphs)

    if args.quiet:
        print(f'{overall_sim:.3f}')
        return

    report = build_report(
        paragraphs=paragraphs, high=high, medium=medium,
        overall_sim=overall_sim, source_counter=source_counter,
        year_counts=year_counts, filename=filename,
        corpus_size=len(corpus), top_k=args.top_k,
        min_score=args.min_score,
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f'报告已写入: {args.output}')
    else:
        print()
        print(report)


if __name__ == '__main__':
    main()
