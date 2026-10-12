import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics


GROUPS = [
    ('original_old_wiki', 'A', '旧', 'LLM-Wiki', 'supplementary', 'O_W'),
    ('original_old_utopia', 'A', '旧', 'Utopia', 'supplementary', 'O_U'),
    ('user_v3_old_wiki', 'B', '旧', 'LLM-Wiki', 'previous', 'A'),
    ('user_v3_old_utopia', 'B', '旧', 'Utopia', 'previous', 'C'),
    ('user_v3_new_wiki', 'B', '新', 'LLM-Wiki', 'previous', 'B'),
    ('user_v3_new_utopia', 'B', '新', 'Utopia', 'previous', 'D'),
    ('senior_old_wiki', 'C', '旧', 'LLM-Wiki', 'supplementary', 'S_O_W'),
    ('senior_old_utopia', 'C', '旧', 'Utopia', 'supplementary', 'S_O_U'),
    ('senior_new_wiki', 'C', '新', 'LLM-Wiki', 'supplementary', 'S_N_W'),
    ('senior_new_utopia', 'C', '新', 'Utopia', 'supplementary', 'S_N_U'),
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def summarize(entries):
    scores = [entry['score'] for entry in entries if entry['score'].get('score') is not None]
    return {
        'answers': len(entries), 'scored': len(scores),
        'mean_score': round(statistics.mean(s['score'] for s in scores), 2),
        'program_completed': sum(e['metrics']['program_completed'] for e in entries),
        'format_valid': sum(e['metrics']['format_valid'] for e in entries),
        'effective_answer': sum(e['metrics']['effective_answer'] for e in entries),
        'degraded': sum(e['metrics']['degraded'] for e in entries),
        'budget_exhausted': sum(e['metrics']['budget_exhausted'] for e in entries),
        'severe_cap_count': sum(any(v <= 20 for v in s.get('caps', {}).values()) for s in scores),
        'send_as_is': sum(s.get('customer_sendability') == 'send_as_is' for s in scores),
        'score_statuses': dict(Counter(e['score']['status'] for e in entries)),
    }


def consolidate(previous, supplementary, output, readme):
    sources = {'previous': previous, 'supplementary': supplementary}
    manifests = {key: read(folder / 'experiment_manifest.json') for key, folder in sources.items()}
    assert {m['model'] for m in manifests.values()} == {'doubao-seed-2-1-lite'}
    primary = set(manifests['supplementary']['product_primary_ids'])
    assert len(primary) == 12
    answers = output / 'answers'
    answers.mkdir(parents=True, exist_ok=True)
    metrics, summaries, configurations, usage = [], {}, {}, {}
    expected_ids = None
    for ident, profile, knowledge, backend, batch, original_group in GROUPS:
        source = sources[batch]
        entries = [json.loads(line) for line in
                   (source / ('answers_' + original_group + '.jsonl')).read_text().splitlines()]
        ids = {entry['item_id'] for entry in entries}
        assert len(entries) == len(ids) == 60
        if expected_ids is None:
            expected_ids = ids
        assert ids == expected_ids and primary <= ids
        for entry in entries:
            assert entry['metrics']['score'] == entry['score']['score']
            metric = dict(entry['metrics'])
            metric.update(group=ident, profile=profile, source_group=original_group,
                          source_run=manifests[batch]['run_id'])
            metrics.append(metric)
        summaries[ident] = {'all60': summarize(entries),
                            'product12': summarize([e for e in entries if e['item_id'] in primary])}
        summaries[ident]['all60']['mean_wall_seconds'] = round(
            statistics.mean(entry['metrics']['wall_seconds'] for entry in entries), 2)
        parameters = manifests[batch]
        configurations[ident] = {
            'profile': profile, 'knowledge': knowledge, 'backend': backend,
            'source_group': original_group, 'source_run': parameters['run_id'],
            'model': parameters['model'], 'top_k': parameters['top_k'],
            'evidence_char_budget': parameters['evidence_char_budget'],
            'outer_max_iterations': parameters['outer_max_iterations'],
            'wiki_inner_max_iterations': parameters['wiki_inner_max_iterations'],
            'max_output_tokens': parameters['max_output_tokens'], 'thinking': parameters['thinking'],
        }
        usage[ident] = read(source / 'wire_usage.json')[original_group]
        full = [f'# {profile}＋{knowledge}知识库＋{backend}', '', '共60题。', '']
        exported = []
        for entry in sorted(entries, key=lambda e: e['item_id']):
            record = {key: entry[key] for key in ('item_id', 'title', 'answer', 'score', 'judgment_summary')}
            exported.append({'schema_version': 'hmbb-result-1', 'group': ident, **record})
            score = entry['score']['score']
            score_text = f'{score:g}' if score is not None else '未生成分数'
            full += ['## ' + entry['item_id'], '', entry['title'], '', '评分：' + score_text, '',
                     '\n'.join('#' + line if line.startswith('#') else line
                               for line in entry['answer'].splitlines()), '',
                     '### 评分摘要', '', entry['judgment_summary']['summary'], '']
        (answers / (ident + '.jsonl')).write_text(
            ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in exported), encoding='utf-8')
        (answers / (ident + '.md')).write_text('\n'.join(full).rstrip() + '\n', encoding='utf-8')
    assert len(metrics) == 600
    assert sum(m['score'] is not None for m in metrics) == 599
    fields = list(dict.fromkeys(key for metric in metrics for key in metric))
    with (output / 'metrics.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list))
                         else value for key, value in metric.items()} for metric in metrics)
    write(output / 'summary.json', {'groups': summaries, 'product_item_ids': sorted(primary),
                                   'answer_records': 600, 'scored_records': 599})
    write(output / 'configurations.json', configurations)
    write(output / 'usage.json', usage)

    report = ['# 海马爸比客服助手评测', '',
              '当前 benchmark 为60题：既有会话30题、CSV会话30题，包含40道开发题和20道校准题。'
              '模型为 `doubao-seed-2-1-lite`，十组实验均采用同一套 Rubric v3。', '',
              '## 十组实验结果', '',
              '之前的四组实验与补充的六组实验合并如下。每组60题，共600份作答、599份数值评分。'
              '产品12题是60题中的固定子集；之前四组的产品子集分数由已有评分重新汇总，未重新作答。', '',
              '| system prompt＋总 Skill | 知识库 | Wiki：全部60题 | Utopia：全部60题 | Wiki：平均用时（秒） | Utopia：平均用时（秒） | Wiki：产品12题 | Utopia：产品12题 |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for left, right in zip(GROUPS[::2], GROUPS[1::2]):
        cells = []
        for scope, ident in [('all60', left[0]), ('all60', right[0]),
                             ('product12', left[0]), ('product12', right[0])]:
            cells.append(f'[{summaries[ident][scope]["mean_score"]:.2f}](results/answers/{ident}.md)')
        cells[2:2] = [f'{summaries[ident]["all60"]["mean_wall_seconds"]:.2f}'
                      for ident in (left[0], right[0])]
        report.append('| ' + left[1] + ' | ' + left[2] + ' | ' + ' | '.join(cells) + ' |')
    report += ['', '分数范围为0—100，点击分数可查看该组完整回答。配置 A 的 Wiki 全题均分采用59份数值评分；'
               '其他九组采用60份。产品子集每组都有12份数值评分。', '',
               '平均用时按每组全部60题的作答运行耗时计算，包含检索和生成，不包含评分；未形成答复的题也计入平均值。', '',
               '配置含义：', '',
               '- **A**：旧system prompt和旧总Skill。',
               '- **B**：结合有价值的业务数据更新后的客服支持system prompt和总Skill。',
               '- **C**：针对产品咨询场景更新后的system prompt和总Skill。', '',
               '旧、新知识库分别包含25、29份文件。', '',
               '## 文件入口', '',
               '| 内容 | 位置 |', '|---|---|',
               '| 当前60题 benchmark | [说明](benchmark/README.md) · [题目构成](benchmark/manifest.json) |',
               '| 当前评分规则 | [评分说明](benchmark/评分说明.md) · [Rubric](benchmark/rubric.json) |',
               '| 配置 B | [system prompt](config/system_prompt.txt) · [总 Skill](config/SKILL.md) · [评分 prompt](config/grader_prompt.txt) |',
               '| 十组详细指标 | [逐题指标](results/metrics.csv) · [分组汇总](results/summary.json) |',
               '| 实验参数与用量 | [配置](results/configurations.json) · [调用用量](results/usage.json) |',
               '| 4,361条业务对话数据 | [数据说明](data/processed_dialogues/README.md) |', '']
    # 只更新结果表和配置说明，保留创建背景与人工补充的展开解读。
    existing = readme.read_text(encoding='utf-8')
    heading = '## 十组实验结果\n'
    start = existing.index(heading)
    end = existing.index('\n## ', start + len(heading))
    section = existing[start:end]
    details_start = section.find('\n<details>\n')
    explanation = section[details_start:] if details_start >= 0 else ''
    generated = '\n'.join(report)
    generated_start = generated.index(heading)
    generated_end = generated.index('\n## 文件入口', generated_start)
    readme.write_text(existing[:start] + generated[generated_start:generated_end] + explanation + existing[end:],
                      encoding='utf-8')
    print(json.dumps({'groups': len(summaries), 'answers': len(metrics),
                      'scored': 599, 'product_scores': len(primary) * len(summaries)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', required=True, type=Path)
    parser.add_argument('--supplementary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--readme', required=True, type=Path)
    args = parser.parse_args()
    consolidate(args.previous, args.supplementary, args.output, args.readme)
