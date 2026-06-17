"""
评估结果查看器 —— 生成对照 HTML 报告。

将带技能 / 不带技能的两份 summary.json 并排展示，
方便人工评审输出质量差异。

用法：
  # 单次结果查看
  python scripts/eval_viewer.py \\
    --with-skill "evals-results/iteration-1/with-skill" \\
    --baseline "evals-results/iteration-1/baseline" \\
    --output "evals-results/report.html"

  # 也可以只查看一次结果
  python scripts/eval_viewer.py \\
    --single "evals-results/iteration-1/with-skill" \\
    --output "evals-results/report.html"
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def load_summary(dir_path: str) -> dict:
    path = os.path.join(dir_path, 'summary.json')
    if not os.path.exists(path):
        print(f"[WARN] summary.json 不存在: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_output(dir_path: str, eval_id: int) -> str:
    path = os.path.join(dir_path, f'eval-{eval_id}', 'output.txt')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return '[无输出]'


def generate_html(single_data: dict = None,
                  with_skill_data: dict = None,
                  baseline_data: dict = None) -> str:
    """生成对照 HTML"""
    if single_data:
        results = single_data.get('results', [])
        has_skill = single_data.get('has_skill', False)
    else:
        # 合并带技能和 baseline
        ws_results = {r['eval_id']: r for r in (with_skill_data or {}).get('results', [])}
        bl_results = {r['eval_id']: r for r in (baseline_data or {}).get('results', [])}
        all_ids = sorted(set(list(ws_results.keys()) + list(bl_results.keys())))
        results = []
        for eid in all_ids:
            ws = ws_results.get(eid, {})
            bl = bl_results.get(eid, {})
            results.append({
                'eval_id': eid,
                'eval_name': ws.get('eval_name') or bl.get('eval_name') or f'Eval-{eid}',
                'prompt': ws.get('prompt') or bl.get('prompt'),
                'with_skill': ws,
                'baseline': bl,
            })
        has_skill = True  # 双栏模式

    # 构建 HTML
    cards = []
    for r in results:
        name = r.get('eval_name', '')
        prompt = r.get('prompt', '')

        if single_data:
            output = r.get('output', '')
            metrics = r.get('metrics', {})
            duration = metrics.get('duration_ms', 0)
            tokens = metrics.get('output_tokens', 0)
            cost = metrics.get('cost_yuan', 0)
            card = f'''
            <div class="card">
              <div class="card-header">
                <span class="eval-id">#{r.get('eval_id')}</span>
                <span class="eval-name">{name}</span>
                <span class="meta">tok={tokens} cost=¥{cost:.4f} {duration:.0f}ms</span>
              </div>
              <div class="prompt"><strong>Prompt:</strong><pre>{prompt}</pre></div>
              <div class="output"><strong>Output:</strong><pre>{output}</pre></div>
            </div>'''
        else:
            ws = r.get('with_skill', {})
            bl = r.get('baseline', {})
            ws_metrics = ws.get('metrics', {})
            bl_metrics = bl.get('metrics', {})
            ws_output = ws.get('output', '') or (read_output(
                (with_skill_data or {}).get('_dir', ''), r['eval_id'])
                if ws else '[无输出]')
            bl_output = bl.get('output', '') or (read_output(
                (baseline_data or {}).get('_dir', ''), r['eval_id'])
                if bl else '[无输出]')
            ws_dur = ws_metrics.get('duration_ms', 0)
            bl_dur = bl_metrics.get('duration_ms', 0)
            ws_tok = ws_metrics.get('output_tokens', 0)
            bl_tok = bl_metrics.get('output_tokens', 0)
            ws_cost = ws_metrics.get('cost_yuan', 0)
            bl_cost = bl_metrics.get('cost_yuan', 0)

            card = f'''
            <div class="card">
              <div class="card-header">
                <span class="eval-id">#{r.get('eval_id')}</span>
                <span class="eval-name">{name}</span>
              </div>
              <div class="prompt"><strong>Prompt:</strong><pre>{prompt}</pre></div>
              <div class="columns">
                <div class="column with-skill">
                  <div class="column-title">
                    <span>带技能</span>
                    <span class="meta">tok={ws_tok} ¥{ws_cost:.4f} {ws_dur:.0f}ms</span>
                  </div>
                  <pre>{ws_output}</pre>
                </div>
                <div class="column baseline">
                  <div class="column-title">
                    <span>Baseline</span>
                    <span class="meta">tok={bl_tok} ¥{bl_cost:.4f} {bl_dur:.0f}ms</span>
                  </div>
                  <pre>{bl_output}</pre>
                </div>
              </div>
            </div>'''
        cards.append(card)

    total_cost_w = (with_skill_data or {}).get('total_cost', 0) if with_skill_data else 0
    total_cost_b = (baseline_data or {}).get('total_cost', 0) if baseline_data else 0
    total_dur_w = (with_skill_data or {}).get('total_duration_ms', 0) if with_skill_data else 0
    total_dur_b = (baseline_data or {}).get('total_duration_ms', 0) if baseline_data else 0

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>公文技能评估报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f5f5; padding: 20px; }}
  h1 {{ font-size: 20px; margin-bottom: 8px; }}
  .summary {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; }}
  .stat-box {{ background: #fff; border-radius: 8px; padding: 12px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .stat-box .label {{ font-size: 12px; color: #999; }}
  .stat-box .value {{ font-size: 20px; font-weight: bold; }}
  .card {{ background: #fff; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }}
  .card-header {{ display: flex; align-items: center; gap: 12px; padding: 10px 16px; background: #fafafa; border-bottom: 1px solid #eee; }}
  .eval-id {{ background: #4A90D9; color: #fff; border-radius: 4px; padding: 2px 8px; font-size: 12px; }}
  .eval-name {{ font-weight: bold; }}
  .meta {{ color: #999; font-size: 12px; margin-left: auto; }}
  .prompt {{ padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #eee; }}
  .prompt pre {{ font-size: 13px; white-space: pre-wrap; margin-top: 4px; color: #333; }}
  .columns {{ display: flex; }}
  .column {{ flex: 1; padding: 12px 16px; min-width: 0; }}
  .column:first-child {{ border-right: 1px solid #eee; }}
  .column-title {{ font-size: 12px; color: #666; margin-bottom: 8px; display: flex; justify-content: space-between; }}
  .column pre {{ font-size: 13px; white-space: pre-wrap; line-height: 1.6; }}
  .with-skill {{ background: #f0f7ff; }}
  .baseline {{ background: #fafafa; }}
  .output {{ padding: 12px 16px; }}
  .output pre {{ font-size: 13px; white-space: pre-wrap; line-height: 1.6; }}
</style>
</head>
<body>
  <h1>公文技能评估报告</h1>
  <p class="summary">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
'''

    if with_skill_data and baseline_data:
        html += f'''
  <div class="stats">
    <div class="stat-box">
      <div class="label">测试用例</div>
      <div class="value">{len(results)}</div>
    </div>
    <div class="stat-box">
      <div class="label">带技能总费用</div>
      <div class="value">¥{total_cost_w:.4f}</div>
    </div>
    <div class="stat-box">
      <div class="label">Baseline 总费用</div>
      <div class="value">¥{total_cost_b:.4f}</div>
    </div>
    <div class="stat-box">
      <div class="label">带技能耗时</div>
      <div class="value">{total_dur_w / 1000:.1f}s</div>
    </div>
    <div class="stat-box">
      <div class="label">Baseline 耗时</div>
      <div class="value">{total_dur_b / 1000:.1f}s</div>
    </div>
  </div>
'''
    else:
        single = single_data or {}
        total = single.get('total_cost', 0)
        dur = single.get('total_duration_ms', 0)
        n = len(results)
        html += f'''
  <div class="stats">
    <div class="stat-box"><div class="label">测试用例</div><div class="value">{n}</div></div>
    <div class="stat-box"><div class="label">总费用</div><div class="value">¥{total:.4f}</div></div>
    <div class="stat-box"><div class="label">总耗时</div><div class="value">{dur/1000:.1f}s</div></div>
  </div>
'''

    html += ''.join(cards)
    html += '\n</body>\n</html>'
    return html


def main():
    parser = argparse.ArgumentParser(description='评估结果查看器')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--with-skill', help='带技能的结果目录')
    group.add_argument('--single', help='单次结果目录')
    parser.add_argument('--baseline', help='Baseline 结果目录')
    parser.add_argument('--output', default='evals-results/report.html', help='输出 HTML 路径')

    args = parser.parse_args()

    if args.single:
        data = load_summary(args.single)
        if not data:
            sys.exit(1)
        html = generate_html(single_data=data)
    elif args.with_skill:
        ws_data = load_summary(args.with_skill)
        if not ws_data:
            print("[ERROR] 带技能结果不存在")
            sys.exit(1)
        bl_data = None
        if args.baseline:
            bl_data = load_summary(args.baseline)
            bl_data['_dir'] = args.baseline if bl_data else None
        ws_data['_dir'] = args.with_skill
        html = generate_html(with_skill_data=ws_data, baseline_data=bl_data)
    else:
        parser.print_help()
        sys.exit(1)

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"报告已生成: {output_path}")


if __name__ == '__main__':
    main()
