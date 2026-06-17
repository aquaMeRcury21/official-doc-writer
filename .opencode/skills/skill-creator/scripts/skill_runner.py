"""
公文技能评估运行器。

功能：
1. 读取 evals.json 测试用例
2. 分别调用 DeepSeek API（带技能 prompt vs 不带/Baseline）
3. 保存输出结果
4. 聚合生成 benchmark 比较报告

用法：
  # 带技能运行（加载 SKILL.md 作为 system prompt 前缀）
  python scripts/skill_runner.py \\
    --skill-path ".opencode/skills/doc-templates" \\
    --evals ".opencode/skills/doc-templates/evals/evals.json" \\
    --output-dir "evals-results/iteration-1/with-skill"

  # Baseline 运行（不带技能）
  python scripts/skill_runner.py \\
    --evals ".opencode/skills/doc-templates/evals/evals.json" \\
    --output-dir "evals-results/iteration-1/baseline"

  # 对比两次迭代
  python scripts/skill_runner.py --compare \\
    --old "evals-results/iteration-1" \\
    --new "evals-results/iteration-2"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 将项目根目录加入 path
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))


def load_evals(evals_path: str) -> dict:
    """加载 evals.json 测试用例"""
    path = Path(evals_path)
    if not path.exists():
        print(f"[ERROR] evals 文件不存在: {evals_path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_skill_instructions(skill_path: str) -> str:
    """加载技能的 SKILL.md 内容作为 prompt 上下文"""
    skill_dir = Path(skill_path)
    skill_md = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        print(f"[WARN] SKILL.md 不存在: {skill_md}")
        return ''

    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()

    # 去掉 YAML frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    return content


def build_prompt(eval_case: dict, skill_instructions: str = '') -> tuple:
    """
    构造发送给 API 的 messages。

    返回 (system_prompt, user_prompt)
    """
    skill_text = skill_instructions

    # 基础系统提示
    base_system = (
        '你是一位在体制内深耕20年以上的公文写作专家。\n'
        '严格遵循 GB/T 9704-2012 标准撰写公文，语言严谨、规范、无AI腔。\n'
        '返回纯公文正文，不加任何解释说明。'
    )

    if skill_text:
        system_prompt = (
            f'请严格遵循以下公文写作规范：\n\n'
            f'{skill_text}\n\n'
            f'-----\n\n'
            f'{base_system}'
        )
    else:
        system_prompt = base_system

    user_prompt = eval_case.get('prompt', '')
    return system_prompt, user_prompt


def run_single_eval(client, eval_case: dict, skill_instructions: str,
                    eval_id: int, eval_name: str, output_dir: str,
                    model: str = 'deepseek-chat') -> dict:
    """运行单个测试用例"""
    system_prompt, user_prompt = build_prompt(eval_case, skill_instructions)

    print(f"  [Eval {eval_id}] {eval_name} ... ", end='', flush=True)

    try:
        # 直接调用 API（复用 utils.api_client 或手动调用）
        from utils.api_client import DeepSeekClient, TASK_TYPE

        # 如果没传 client，临时创建一个
        local_client = client or DeepSeekClient.from_env()

        result = local_client.chat(
            user_message=user_prompt,
            task_type=TASK_TYPE.DRAFT,
            extra_messages=[{'role': 'system', 'content': system_prompt}],
        )

        if result.success:
            print(f"OK ({result.duration_ms:.0f}ms, {result.output_tokens}tok, ¥{result.cost_yuan:.4f})")
        else:
            print(f"FAIL: {result.error}")

    except Exception as e:
        print(f"ERROR: {e}")
        result = type('obj', (object,), {
            'success': False, 'content': None, 'model': model,
            'input_tokens': 0, 'output_tokens': 0, 'cost_yuan': 0.0,
            'duration_ms': 0.0, 'error': str(e),
            'retries_used': 0
        })()

    # 保存输出
    os.makedirs(output_dir, exist_ok=True)
    eval_dir = os.path.join(output_dir, f'eval-{eval_id}')
    os.makedirs(eval_dir, exist_ok=True)

    output = {
        'eval_id': eval_id,
        'eval_name': eval_name,
        'prompt': user_prompt,
        'system_prompt': system_prompt,
        'has_skill': bool(skill_instructions),
        'output': result.content if result.success else None,
        'error': result.error if not result.success else None,
        'metrics': {
            'success': result.success,
            'model': result.model,
            'input_tokens': getattr(result, 'input_tokens', 0),
            'output_tokens': getattr(result, 'output_tokens', 0),
            'cost_yuan': getattr(result, 'cost_yuan', 0.0),
            'duration_ms': getattr(result, 'duration_ms', 0.0),
            'retries_used': getattr(result, 'retries_used', 0),
        },
        'timestamp': datetime.now().isoformat(),
    }

    # 保存 JSON
    with open(os.path.join(eval_dir, 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 保存输出内容单独文件
    if result.content:
        with open(os.path.join(eval_dir, 'output.txt'), 'w', encoding='utf-8') as f:
            f.write(result.content)

    return output


def run_evals(evals_path: str, skill_path: str = None,
              output_dir: str = 'evals-results', model: str = 'deepseek-chat'):
    """运行全部测试用例"""
    from utils.api_client import DeepSeekClient

    data = load_evals(evals_path)
    evals = data.get('evals', [])
    skill_name = data.get('skill_name', 'unknown')

    print(f"技能名称: {skill_name}")
    print(f"测试用例: {len(evals)} 个")
    print(f"输出目录: {output_dir}")

    # 加载技能指令
    skill_instructions = ''
    if skill_path:
        skill_instructions = load_skill_instructions(skill_path)
        has_skill = len(skill_instructions.strip()) > 0
        print(f"技能路径: {skill_path} ({'已加载' if has_skill else '未找到'})")
    else:
        print("运行模式: BASELINE（无技能）")

    print(f"模型: {model}")
    print("-" * 60)

    # 创建客户端
    client = DeepSeekClient.from_env()

    results = []
    for i, eval_case in enumerate(evals):
        name = eval_case.get('name', f'测试{i}')
        result = run_single_eval(
            client=client,
            eval_case=eval_case,
            skill_instructions=skill_instructions,
            eval_id=eval_case.get('id', i),
            eval_name=name,
            output_dir=output_dir,
            model=model,
        )
        results.append(result)

    # 生成汇总报告
    summary_path = os.path.join(output_dir, 'summary.json')
    summary = {
        'skill_name': skill_name,
        'skill_path': skill_path,
        'model': model,
        'has_skill': bool(skill_instructions),
        'total_evals': len(results),
        'success_count': sum(1 for r in results if r.get('metrics', {}).get('success')),
        'total_cost': sum(r['metrics']['cost_yuan'] for r in results if r['metrics'].get('success')),
        'total_duration_ms': sum(r['metrics']['duration_ms'] for r in results),
        'total_output_tokens': sum(r['metrics']['output_tokens'] for r in results),
        'results': results,
        'timestamp': datetime.now().isoformat(),
    }

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print(f"完成: {summary['success_count']}/{summary['total_evals']} 成功")
    print(f"总耗时: {summary['total_duration_ms'] / 1000:.1f}s")
    print(f"总费用: ¥{summary['total_cost']:.4f}")
    print(f"汇总: {summary_path}")

    return summary


def compare_results(old_dir: str, new_dir: str):
    """对比两次迭代的结果"""
    old_summary = os.path.join(old_dir, 'summary.json')
    new_summary = os.path.join(new_dir, 'summary.json')

    if not os.path.exists(old_summary):
        print(f"[ERROR] 旧结果不存在: {old_summary}")
        return
    if not os.path.exists(new_summary):
        print(f"[ERROR] 新结果不存在: {new_summary}")
        return

    with open(old_summary, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    with open(new_summary, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    print(f"\n{'='*60}")
    print(f"  对比结果: {os.path.basename(old_dir)} vs {os.path.basename(new_dir)}")
    print(f"{'='*60}")

    old_has = old_data.get('has_skill', False)
    new_has = new_data.get('has_skill', False)
    print(f"  旧: {'带技能' if old_has else '无技能'} | 新: {'带技能' if new_has else '无技能'}")

    def fmt_metric(key, label):
        o = old_data.get(key, 0)
        n = new_data.get(key, 0)
        delta = n - o
        pct = f"({delta / o * 100:+.1f}%)" if o else ""
        if delta == 0:
            return f"  {label}: {n} (无变化)"
        elif delta > 0:
            return f"  {label}: {o} → {n} [+{delta} {pct}]"
        else:
            return f"  {label}: {o} → {n} [{delta} {pct}]"

    print(f"  成功率: {old_data.get('success_count', 0)}/{old_data.get('total_evals', 0)} → "
          f"{new_data.get('success_count', 0)}/{new_data.get('total_evals', 0)}")
    print(fmt_metric('total_cost', '总费用(¥)'))
    print(fmt_metric('total_duration_ms', '总耗时(ms)'))
    print(fmt_metric('total_output_tokens', '输出token数'))

    # 逐项对比
    print(f"\n  逐项对比:")
    old_results = {r['eval_id']: r for r in old_data.get('results', [])}
    new_results = {r['eval_id']: r for r in new_data.get('results', [])}

    for eid in sorted(set(list(old_results.keys()) + list(new_results.keys()))):
        o = old_results.get(eid, {})
        n = new_results.get(eid, {})
        oname = o.get('eval_name') or n.get('eval_name') or f'Eval-{eid}'
        o_tok = o.get('metrics', {}).get('output_tokens', 0) if o.get('metrics', {}).get('success') else -1
        n_tok = n.get('metrics', {}).get('output_tokens', 0) if n.get('metrics', {}).get('success') else -1
        o_cost = o.get('metrics', {}).get('cost_yuan', 0)
        n_cost = n.get('metrics', {}).get('cost_yuan', 0)
        print(f"    [{eid}] {oname}: tok={o_tok}→{n_tok} cost=¥{o_cost:.4f}→{n_cost:.4f}")


def main():
    parser = argparse.ArgumentParser(description='公文技能评估运行器')
    parser.add_argument('--skill-path', help='技能路径（省略则运行 Baseline）')
    parser.add_argument('--evals', required=True, help='evals.json 路径')
    parser.add_argument('--output-dir', default='evals-results', help='输出目录')
    parser.add_argument('--model', default='deepseek-chat', help='模型名称')
    parser.add_argument('--compare', action='store_true', help='对比模式')
    parser.add_argument('--old', help='旧结果目录（对比用）')
    parser.add_argument('--new', help='新结果目录（对比用）')

    args = parser.parse_args()

    if args.compare:
        if not args.old or not args.new:
            parser.error('--compare 需要 --old 和 --new')
        compare_results(args.old, args.new)
    else:
        run_evals(
            evals_path=args.evals,
            skill_path=args.skill_path,
            output_dir=args.output_dir,
            model=args.model,
        )


if __name__ == '__main__':
    main()
