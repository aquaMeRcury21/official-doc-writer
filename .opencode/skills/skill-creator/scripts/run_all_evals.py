"""
批量运行所有技能的 evals 测试。

用法：
  # 测试所有技能（带技能 vs 不带技能）
  python scripts/run_all_evals.py --output-dir evals-results/full-eval

  # 只测试指定技能
  python scripts/run_all_evals.py --skills doc-templates,doc-format --output-dir evals-results/quick-test
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = PROJECT_ROOT / '.opencode' / 'skills'
RUNNER = SCRIPT_DIR / 'skill_runner.py'
VIEWER = SCRIPT_DIR / 'eval_viewer.py'


def find_all_skills_with_evals():
    """找到所有有 evals/evals.json 的技能"""
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir():
            evals_path = d / 'evals' / 'evals.json'
            if evals_path.exists():
                with open(evals_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                skills.append({
                    'name': data.get('skill_name', d.name),
                    'path': str(d),
                    'evals_path': str(evals_path),
                })
    return skills


def main():
    parser = argparse.ArgumentParser(description='批量运行所有技能 evals')
    parser.add_argument('--skills', help='只测试指定技能（逗号分隔）')
    parser.add_argument('--output-dir', default='evals-results/full-eval',
                        help='输出根目录')
    parser.add_argument('--model', default='deepseek-chat', help='模型名称')
    parser.add_argument('--compare', action='store_true',
                        help='同时运行带技能和 Baseline 并对比')

    args = parser.parse_args()

    skills = find_all_skills_with_evals()

    if args.skills:
        names = set(s.strip() for s in args.skills.split(','))
        skills = [s for s in skills if s['name'] in names]

    if not skills:
        print("未找到任何有 evals.json 的技能")
        print("请先在 .opencode/skills/技能名/evals/evals.json 中配置测试用例")
        sys.exit(1)

    print(f"找到 {len(skills)} 个技能有 evals:")
    for s in skills:
        print(f"  - {s['name']} ({s['evals_path']})")
    print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_root = f"{args.output_dir}_{timestamp}" if args.output_dir == 'evals-results/full-eval' else args.output_dir

    for skill in skills:
        name = skill['name']
        skill_path = skill['path']
        evals_path = skill['evals_path']

        print(f"\n{'='*60}")
        print(f"  技能: {name}")
        print(f"{'='*60}")

        # 运行带技能的版本
        ws_dir = os.path.join(output_root, name, 'with-skill')
        print(f"\n--- 带技能运行 ---")
        os.system(f'"{sys.executable}" "{RUNNER}" '
                  f'--skill-path "{skill_path}" '
                  f'--evals "{evals_path}" '
                  f'--output-dir "{ws_dir}" '
                  f'--model "{args.model}"')

        if args.compare:
            # 运行 Baseline
            bl_dir = os.path.join(output_root, name, 'baseline')
            print(f"\n--- Baseline 运行 ---")
            os.system(f'"{sys.executable}" "{RUNNER}" '
                      f'--evals "{evals_path}" '
                      f'--output-dir "{bl_dir}" '
                      f'--model "{args.model}"')

            # 生成对照报告
            report_dir = os.path.join(output_root, name)
            report_path = os.path.join(report_dir, f'{name}_report.html')
            print(f"\n--- 生成对照报告 ---")
            os.system(f'"{sys.executable}" "{VIEWER}" '
                      f'--with-skill "{ws_dir}" '
                      f'--baseline "{bl_dir}" '
                      f'--output "{report_path}"')
            print(f"报告: {report_path}")

    print(f"\n{'='*60}")
    print(f"  全部完成")
    print(f"  结果目录: {output_root}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
