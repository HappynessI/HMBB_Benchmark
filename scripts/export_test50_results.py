import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import statistics

from export_support_v3_results import make_cleaner


GROUPS = {
    ('claude-code', 'no_business_skill_or_kb'): ('claude_code_baseline', 'Claude Code：无业务 Skill / 知识库', 'formal1'),
    ('claude-code', 'original_skill_and_kb'): ('claude_code_original', 'Claude Code：原 Skill＋原知识库', 'formal1'),
    ('dsh', 'no_business_skill_or_kb'): ('dsh_baseline', 'DSH：无业务 Skill / 知识库', 'formal1'),
    ('dsh', 'original_skill_and_kb'): ('dsh_original', 'DSH：原 Skill＋原知识库', 'formal1'),
    ('hermes', 'no_business_skill_or_kb'): ('hermes_baseline', 'Hermes：无业务 Skill / 知识库', 'formal2'),
    ('hermes', 'original_skill_and_kb'): ('hermes_original', 'Hermes：原 Skill＋原知识库', 'formal2'),
    ('hermes', 'llm_wiki'): ('hermes_wiki', 'Hermes：原 Skill＋LLM-Wiki', 'formal1'),
    ('hermes', 'utopia'): ('hermes_utopia', 'Hermes：原 Skill＋Utopia', 'formal2'),
}
METRIC_FIELDS = (
    'harness', 'condition', 'question_id', 'status', 'exit_code', 'timed_out',
    'wall_seconds', 'answer_chars', 'api_error_count', 'input_tokens',
    'output_tokens', 'token_usage_complete', 'successful_call_usage_complete',
    'model_api_calls', 'api_seconds', 'stream_error_count', 'tool_error_count',
    'wire_high_confirmed', 'response_models', 'http_error_count',
    'transport_error_count', 'total_tokens', 'three_required_headings',
    'unparsed_tool_markup', 'actual_backend', 'retrieval_degraded',
    'evidence_count', 'embedding_calls', 'embedding_seconds',
    'embedding_input_tokens_known', 'embedding_error_count',
    'embedding_usage_complete', 'mcp_calls', 'mcp_error_count', 'mcp_seconds',
)
EXTRA_REDACTIONS = (
    ('credential', r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b', '[凭据]'),
    ('authorization', r'(?i)\bBearer\s+[A-Za-z0-9._~-]{12,}', 'Bearer [凭据]'),
    ('local_path_extra', r'(?:/home/|/root/|/workspace/)[^\s）)\]"<>]+', '[本地路径]'),
    ('private_address', r'\b(?:127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)(?::\d+)?\b', '[内部地址]'),
)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def display_answer(answer, unparsed_markup):
    if not answer.strip():
        return '*该次运行未产生最终作答文本。*'
    if unparsed_markup:
        fence = '`' * max(3, max((len(m.group()) + 1 for m in re.finditer(r'`+', answer)), default=3))
        return f'{fence}text\n{answer.rstrip()}\n{fence}'
    return re.sub(r'^#{1,2} ', '### ', answer.rstrip(), flags=re.MULTILINE)


def export(source, output):
    manifest = read(source / 'manifest.json')
    expected_ids = manifest['ids']
    if len(expected_ids) != 50 or len(set(expected_ids)) != 50:
        raise ValueError('Expected fifty distinct test50 question IDs')
    with (source / 'execution_metrics.csv').open(encoding='utf-8', newline='') as handle:
        selected = list(csv.DictReader(handle))
    if len(selected) != 400:
        raise ValueError('Expected 400 selected formal runs')
    reference_summary = {
        (row['harness'], row['condition']): row
        for row in read(source / 'execution_summary.json')
    }
    clean, redactions = make_cleaner(None)
    extra_counts = Counter()
    groups = defaultdict(list)
    metrics = []
    seen = set()
    for selected_row in selected:
        # 迁移后的目录沿用原运行目录名，历史绝对路径不写入公开结果。
        folder = source / 'results' / Path(selected_row['artifact_dir']).name
        if not folder.is_dir() or (folder / 'INVALID_FOR_COMPARISON.md').exists():
            raise ValueError('Selected run is missing or marked invalid')
        raw = read(folder / 'execution_metrics.json')['metrics']
        result = read(folder / 'result.json')
        key = (raw['harness'], raw['condition'], raw['question_id'])
        if key in seen or key[:2] not in GROUPS or key[2] not in expected_ids:
            raise ValueError('Unexpected or repeated run identity')
        seen.add(key)
        for field in ('harness', 'condition', 'question_id', 'status'):
            if selected_row[field] != str(raw[field]) or result[field] != raw[field]:
                raise ValueError(f'Run identity or status mismatch: {field}')
        group, label, attempt = GROUPS[key[:2]]
        if not folder.name.endswith('__' + attempt):
            raise ValueError(f'Unexpected formal attempt for {group}')
        original = (folder / 'answer.md').read_text(encoding='utf-8')
        answer = original
        for name, pattern, replacement in EXTRA_REDACTIONS:
            answer, count = re.subn(pattern, replacement, answer)
            extra_counts[name] += count
        answer = clean(answer)
        metric = {name: raw[name] for name in METRIC_FIELDS}
        metric.update(group=group, selected_attempt=attempt,
                      actual_backend=raw['actual_backend'] or None,
                      retrieval_error_present=bool(raw['retrieval_error']))
        entry = {
            'schema_version': 'public-test50-result-v1',
            'group': group, 'question_id': key[2], 'selected_attempt': attempt,
            'answer': answer, 'answer_present': bool(original.strip()),
            'answer_redacted': answer != original,
            'grading_status': 'not_graded', 'score': None, 'metrics': metric,
        }
        groups[group].append(entry)
        metrics.append(metric)
    summaries = []
    for key, (group, label, attempt) in GROUPS.items():
        entries = groups[group]
        if len(entries) != 50 or {entry['question_id'] for entry in entries} != set(expected_ids):
            raise ValueError(f'Incomplete question coverage for {group}')
        entries.sort(key=lambda entry: expected_ids.index(entry['question_id']))
        reference = reference_summary[key]
        checks = {
            'runs': len(entries),
            'completed': sum(entry['metrics']['status'] == 'completed' for entry in entries),
            'required_headings_runs': sum(entry['metrics']['three_required_headings'] for entry in entries),
            'input_tokens_known': sum(entry['metrics']['input_tokens'] or 0 for entry in entries),
            'output_tokens_known': sum(entry['metrics']['output_tokens'] or 0 for entry in entries),
            'http_errors': sum(entry['metrics']['http_error_count'] for entry in entries),
            'transport_errors': sum(entry['metrics']['transport_error_count'] for entry in entries),
            'stream_errors': sum(entry['metrics']['stream_error_count'] for entry in entries),
            'tool_errors': sum(entry['metrics']['tool_error_count'] for entry in entries),
        }
        if any(reference[name] != value for name, value in checks.items()):
            raise ValueError(f'Published totals would differ from the source summary: {group}')
        mean = round(statistics.mean(entry['metrics']['wall_seconds'] for entry in entries), 3)
        if mean != reference['mean_wall_seconds']:
            raise ValueError(f'Runtime summary differs: {group}')
        summaries.append(dict(reference, group=group, label=label, selected_attempt=attempt,
                              nonempty_answers=sum(entry['answer_present'] for entry in entries),
                              redacted_answers=sum(entry['answer_redacted'] for entry in entries)))
    summary = {
        'run_id': source.name, 'records': len(metrics),
        'completed_runs': sum(row['completed'] for row in summaries),
        'not_completed_runs': sum(row['runs'] - row['completed'] for row in summaries),
        'nonempty_answers': sum(row['nonempty_answers'] for row in summaries),
        'required_headings_runs': sum(row['required_headings_runs'] for row in summaries),
        'unparsed_tool_markup_runs': sum(row['unparsed_tool_markup_runs'] for row in summaries),
        'grading_status': 'not_graded', 'business_confirmed': False, 'groups': summaries,
    }
    if (summary['completed_runs'], summary['required_headings_runs']) != (369, 366):
        raise ValueError('Source totals differ from the established test50 batch')
    public_manifest = {
        'run_id': source.name, 'dataset': '旧 test50', 'question_ids': expected_ids,
        'model': manifest['answer_model_api'], 'reasoning_effort': manifest['reasoning_effort'],
        'versions': {name: manifest['versions'][name] for name in
                     ('claude_code', 'dsh_executed', 'hermes', 'hermes_anthropic_sdk')},
        'limits': manifest['limits'],
        'groups': [{'group': group, 'harness': key[0], 'condition': key[1], 'selected_attempt': attempt}
                   for key, (group, label, attempt) in GROUPS.items()],
        'grading_status': 'not_graded', 'business_confirmed': False,
        'answer_policy': '按正式批次导出最终输出；只替换敏感文本，不润色、不补答；空输出保留为空字符串。',
        'selection_policy': '以 execution_metrics.csv 中的400条正式记录为准；排除标记无效的批次、冒烟测试和预检。',
        'redacted_answers': sum(row['redacted_answers'] for row in summaries),
        'redaction_counts': dict(redactions + extra_counts),
    }
    # 在写出前检查所有公开字段，避免将路径或凭据带入结果。
    payload = json.dumps([groups, metrics, summary, public_manifest], ensure_ascii=False)
    checks = (
        r'/Users/|/private/tmp/|/home/|/root/|/workspace/',
        r'(?<!\d)1\d{10}(?!\d)', r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
        EXTRA_REDACTIONS[0][1], EXTRA_REDACTIONS[1][1],
    )
    for index, pattern in enumerate(checks):
        if re.search(pattern, payload):
            raise ValueError(f'Public export failed sensitive-text check {index}')
    output.mkdir(parents=True, exist_ok=True)
    answers = output / 'answers'
    answers.mkdir(exist_ok=True)
    write_json(output / 'metrics.json', metrics)
    write_json(output / 'summary.json', summary)
    write_json(output / 'manifest.json', public_manifest)
    with (output / 'metrics.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(metrics)
    for key, (group, label, attempt) in GROUPS.items():
        entries = groups[group]
        (answers / f'{group}.jsonl').write_text(
            ''.join(json.dumps(entry, ensure_ascii=False) + '\n' for entry in entries), encoding='utf-8')
        document = [f'# {label}', '', '共50条正式运行记录，尚未统一业务评分。空输出和异常输出保留。', '']
        for entry in entries:
            metric = entry['metrics']
            document.extend([
                f'## {entry["question_id"]}', '',
                f'运行状态：`{metric["status"]}`；正式批次：`{attempt}`；耗时：{metric["wall_seconds"]:.2f} 秒。', '',
                display_answer(entry['answer'], metric['unparsed_tool_markup']), '',
            ])
        (answers / f'{group}.md').write_text('\n'.join(document), encoding='utf-8')
    document = [
        '# 旧 test50：逐题作答与运行结果', '',
        '本批次使用 `deepseek-v4-flash`、high，8组各50题，共400条正式运行记录。'
        '369条原生运行完成，31条未完成；366条具有约定的三个标题，3条含未解析工具标记。'
        '程序完成和格式通过不代表业务正确。本批次尚未统一业务评分。', '',
        f'有非空最终输出的记录为{summary["nonempty_answers"]}条。每组JSONL保留全部50条记录，'
        '包括空输出、运行失败和格式异常。最终输出只作敏感文本替换，不补写失败答案。', '',
        '| 实验组 | 记录数 | 运行完成 | 非空输出 | 三段标题齐全 | 平均耗时（秒） | 作答文件 |',
        '|---|---:|---:|---:|---:|---:|---|',
    ]
    for row in summaries:
        group = row['group']
        document.append(
            f'| {row["label"]} | {row["runs"]} | {row["completed"]} | {row["nonempty_answers"]} | '
            f'{row["required_headings_runs"]} | {row["mean_wall_seconds"]:.2f} | '
            f'[逐题阅读](answers/{group}.md) · [JSONL](answers/{group}.jsonl) |')
    document.extend([
        '', '## 指标与复现口径', '',
        '- [逐题指标 CSV](metrics.csv) · [逐题指标 JSON](metrics.json) · [分组汇总](summary.json)。',
        '- [实验配置与脱敏统计](manifest.json)记录模型、版本、正式批次、运行上限和替换次数。',
        '- 脱敏后的最终输出在JSONL的 `answer` 字段中，脱敏修改由 `answer_redacted` 标记；空字符串表示没有最终作答文本。',
        '- `score` 为 `null`，`grading_status` 为 `not_graded`。用量未知值保持 `null`，汇总仅累计已报告的 token。',
        '- 耗时包含启动、检索、模型调用和重试；组间可能并发，Utopia通过本地中转且为单worker，不将耗时差异直接解释为后端性能差异。',
        '- Wiki仅编译现行知识，Utopia包含归档来源；检索top_k分别为8和6。Utopia在答题前关闭自动治理并冻结图谱。',
        '- 400条记录沿用原实验选定的正式批次；无效沙箱批次、Utopia中止的TLS故障批次与冒烟测试未混入。',
        '- 发布文件包含最终输出和白名单运行指标；原始API流量、内部工具轨迹及本地运行环境另存于实验目录。', '',
        '## 重新导出', '',
        '在仓库根目录运行，并将参数替换为本机原始实验目录：', '',
        '```sh',
        'python3 scripts/export_test50_results.py --source-root /path/to/20260929_test50',
        '```', '',
        '导出程序检查400条唯一记录、每组50题、正式批次、运行状态、耗时、token合计及敏感字段。', '',
    ])
    (output / 'README.md').write_text('\n'.join(document), encoding='utf-8')
    print(json.dumps({name: summary[name] for name in
                      ('records', 'completed_runs', 'not_completed_runs', 'nonempty_answers',
                       'required_headings_runs', 'unparsed_tool_markup_runs')}, ensure_ascii=False))
    print(json.dumps({'redacted_answers': public_manifest['redacted_answers'],
                      'redaction_counts': public_manifest['redaction_counts']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('results/test50'))
    arguments = parser.parse_args()
    export(arguments.source_root, arguments.output)
