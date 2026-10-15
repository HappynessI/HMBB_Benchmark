import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import statistics

from consolidate_results import summarize
from export_support_v3_results import METRIC_FIELDS, decision_summary, make_cleaner, read, rows, write


IDENT = 'agentic_new_utopia'
GROUP = 'D_U'


def append_results(run, output, alias_source=None):
    if read(run / 'completion.json')['status'] != 'completed':
        raise ValueError('实验尚未完成')
    manifest = read(run / 'experiment_manifest.json')
    assert manifest['knowledge_prefetch'] is False
    assert manifest['model'] == 'doubao-seed-2-1-lite'
    metrics = read(run / 'summary/metrics.json')
    contracts = {c['id']: c for c in rows(run / 'evaluation/grading/contracts.jsonl')}
    assert len(metrics) == len({m['item_id'] for m in metrics}) == 60
    assert {m['item_id'] for m in metrics} == set(contracts)
    clean, redactions = make_cleaner(alias_source)
    entries, public_metrics = [], []
    verification, tool_counts = [], Counter()
    for metric in sorted(metrics, key=lambda m: m['item_id']):
        qid = metric['item_id']
        folder = run / 'answers' / GROUP / qid
        check = read(folder / 'retrieval_verification.json')
        assert check['first_input_has_no_prefetched_context']
        assert check['all_queries_model_initiated']
        verification.append(check)
        for path in (folder / 'mcp').glob('*.json'):
            request = read(path)['request']
            if request['method'] == 'tools/call':
                tool_counts[request['params']['name']] += 1
        score = read(run / 'grading' / GROUP / qid / 'score.json')
        assert score['score'] == metric['score']
        if score['status'] == 'invalid_verdict':
            judgment = {'summary': '评分裁决未通过校验，没有可汇总分数。'}
        else:
            judgment = decision_summary(read(run / 'grading' / GROUP / qid / 'verdict.json'), clean)
        entries.append({'item_id': qid, 'title': clean(contracts[qid]['title']),
                        'answer': clean((folder / 'answer.md').read_text()),
                        'score': score, 'judgment_summary': judgment, 'metrics': metric})
        exported_metric = {key: metric[key] for key in METRIC_FIELDS if key in metric}
        exported_metric.update(group=IDENT, profile='D', source_group=GROUP, source_run=run.name,
                               knowledge_prefetch=False, knowledge_tool_calls=check['tool_calls'])
        public_metrics.append(exported_metric)
    primary = set(manifest['product_primary_ids'])
    summary = read(output / 'summary.json')
    assert primary == set(summary['product_item_ids'])
    summary['groups'][IDENT] = {
        'all60': summarize(entries),
        'product12': summarize([e for e in entries if e['item_id'] in primary]),
        'retrieval': {'mode': 'model_directed', 'prefetch': False,
                      'verified_answers': len(verification), 'tool_calls': dict(tool_counts),
                      'answers_without_retrieval': sum(c['tool_calls'] == 0 for c in verification),
                      'mean_tool_calls': round(statistics.mean(c['tool_calls'] for c in verification), 2)},
    }
    summary['groups'][IDENT]['all60']['mean_wall_seconds'] = round(
        statistics.mean(m['wall_seconds'] for m in metrics), 2)
    with (output / 'metrics.csv').open(newline='') as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames)
        previous = [row for row in reader if row['group'] != IDENT]
    for field in ('knowledge_prefetch', 'knowledge_tool_calls'):
        if field not in fields:
            fields.append(field)
    previous.extend({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                     for key, value in metric.items()} for metric in public_metrics)
    assert len(previous) == 660
    assert len({(m['group'], m['item_id']) for m in previous}) == 660
    with (output / 'metrics.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(previous)
    summary['answer_records'] = sum(s['all60']['answers'] for s in summary['groups'].values())
    summary['scored_records'] = sum(s['all60']['scored'] for s in summary['groups'].values())
    write(output / 'summary.json', summary)
    configs = read(output / 'configurations.json')
    for config in configs.values():
        if config['profile'] in ('A', 'B', 'C'):
            config['knowledge_prefetch'] = True
    configs[IDENT] = {
        'profile': 'D', 'knowledge': '新', 'backend': 'Utopia', 'source_group': GROUP,
        'source_run': run.name, 'model': manifest['model'], 'thinking': manifest['thinking'],
        'knowledge_prefetch': False, 'retrieval_mode': 'model_directed',
        'outer_max_iterations': 20, 'max_output_tokens': 8192,
        'answer_workers': 4, 'grading_workers': 4,
        'system_prompt': '../config/D/system_prompt.txt', 'skill': '../config/D/SKILL.md',
        'hermes_config': '../config/D/hermes_config.yaml',
        'hermes_revision': '0f0cee72',
        'utopia_reuses_frozen_kbs': True,
    }
    write(output / 'configurations.json', configs)
    usage = read(output / 'usage.json')
    usage[IDENT] = read(run / 'summary/wire_usage.json')[GROUP]
    write(output / 'usage.json', usage)
    exported = [{key: e[key] for key in ('item_id', 'title', 'answer', 'score', 'judgment_summary')}
                for e in entries]
    (output / 'answers' / (IDENT + '.jsonl')).write_text(''.join(
        json.dumps({'schema_version': 'hmbb-result-1', 'group': IDENT, **e}, ensure_ascii=False) + '\n'
        for e in exported))
    full = ['# D＋新知识库＋Utopia', '', '共60题。模型自主决定检索。', '']
    for entry in entries:
        score = entry['score']['score']
        score_text = f'{score:g}' if score is not None else '未生成分数'
        full += ['## ' + entry['item_id'], '', entry['title'], '', '评分：' + score_text, '',
                 '\n'.join('#' + line if line.startswith('#') else line for line in entry['answer'].splitlines()),
                 '', '### 评分摘要', '', entry['judgment_summary']['summary'], '']
    (output / 'answers' / (IDENT + '.md')).write_text('\n'.join(full).rstrip() + '\n')
    print(json.dumps({'D': summary['groups'][IDENT], 'answer_records': summary['answer_records'],
                      'scored_records': summary['scored_records'], 'redactions': dict(redactions)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'results')
    parser.add_argument('--alias-source', type=Path)
    args = parser.parse_args()
    append_results(args.run_root, args.output, args.alias_source)
