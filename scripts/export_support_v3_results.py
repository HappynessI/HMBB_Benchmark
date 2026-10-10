"""Publish answer text and score summaries without private inputs or call traces.

Requires the completed local run and its private title catalog. Uses only the
standard library; no API calls. Numeric results are preserved exactly.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re


GROUPS = 'ABCD'
METRIC_FIELDS = (
    'group', 'item_id', 'split', 'backend', 'knowledge_version',
    'program_completed', 'format_valid', 'effective_answer', 'degraded',
    'actual_backend', 'wall_seconds', 'exit_code', 'timed_out',
    'turn_exit_reason', 'native_failed', 'budget_exhausted', 'answer_chars',
    'native_usage', 'score', 'score_status',
)
MANIFEST_FIELDS = (
    'groups', 'source_counts', 'split', 'status', 'items', 'rubric', 'model',
    'top_k', 'evidence_char_budget', 'outer_max_iterations',
    'wiki_inner_max_iterations', 'max_output_tokens', 'thinking',
    'answer_workers', 'temperature_judge', 'utopia_worker_concurrency',
    'utopia_model_permits', 'archive_loaded', 'business_interfaces', 'heldout_test',
)
TEXT_PATTERNS = (
    ('local_path', r'(?:/Users/|/private/tmp/|/tmp/)[^\s）)\]"<>]+', '[本地路径]'),
    ('link', r'https?://[^\s）)\]"<>]+|(?:s\.tb\.cn|m\.tb\.cn|tb\.cn)/[^\s]+', '[链接]'),
    ('email', r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱]'),
    ('phone', r'(?<!\d)1\d{10}(?!\d)', '[手机号]'),
    ('number', r'(?<!\d)(?:0\d{2,3}[- ]?)?\d{7,}(?!\d)', '[编号]'),
    ('waybill', r'\b(?:SF|YT|ZTO|STO|JD|JDX)\d+\b', '[快递单号]'),
    ('account', r'\b(?:tb|wxj|ljn)[A-Za-z0-9_]{4,}\b', '[账号]'),
    ('speaker_id', r'客户\d+|客服\d+', '[说话人编号]'),
    ('device_id', r'(?:[A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}', '[设备编号]'),
    ('internal_id', r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b', '[内部编号]'),
    ('name', r'[\u4e00-\u9fff]{2,5}\s*[,，]?\s*(?=\[(?:手机号|电话|联系方式)\])', '[姓名] '),
    ('address', r'[\u4e00-\u9fff]{2,8}(?:省|市|自治区)\s*[\u4e00-\u9fff\d A-Za-z_\-]*(?:区|县|镇|街|路|村|巷|栋|号)[\u4e00-\u9fff\d A-Za-z_\-]*', '[地址]'),
)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def make_cleaner(alias_source):
    aliases = set()
    if alias_source:
        for record in rows(alias_source):
            for variant in [record] + record.get('source_variants', []):
                for message in variant.get('messages', []):
                    alias = (message.get('speaker_raw') or '').strip()
                    if len(alias) >= 2 and not any(word in alias for word in ('客户', '客服', '用户', '买家', '卖家', '系统', '海马爸比')):
                        aliases.add(alias)
    counts = Counter()

    def clean(text):
        for alias in sorted(aliases, key=len, reverse=True):
            n = text.count(alias)
            if n:
                text = text.replace(alias, '[昵称]')
                counts['known_alias'] += n
        for name, pattern, replacement in TEXT_PATTERNS:
            text, n = re.subn(pattern, replacement, text)
            counts[name] += n
        return text

    return clean, counts


def decision_summary(verdict, clean):
    result = {
        'needs_review': verdict['needs_review'],
        'review_reasons': [clean(s) for s in verdict.get('review_reasons', [])],
        'customer_sendability': verdict['customer_sendability'],
        'summary': clean(verdict['summary']),
    }
    for section in ('business_points', 'criteria', 'controls'):
        result[section] = {}
        for key, value in verdict[section].items():
            kept = {k: value[k] for k in ('rating', 'triggered') if k in value}
            kept.update({k: clean(value[k]) for k in ('reason', 'missing') if k in value})
            result[section][key] = kept
    # Original conversation/context, source evidence and evidence binding IDs are
    # intentionally omitted. The private verdict remains the auditable original.
    return result


def export(root, report_path, contracts_path, output, alias_source=None):
    completion = read(root / 'completion.json')
    if completion['status'] != 'completed':
        raise ValueError('Only a completed run can be exported')
    original_metrics = read(root / 'summary/metrics.json')
    if len(original_metrics) != 240 or len({(m['group'], m['item_id']) for m in original_metrics}) != 240:
        raise ValueError('Expected exactly four groups of sixty unique results')
    titles = {c['id']: c['title'] for c in rows(contracts_path)}
    clean, redactions = make_cleaner(alias_source)
    output.mkdir(parents=True, exist_ok=True)
    metrics = [{k: m[k] for k in METRIC_FIELDS if k in m} for m in original_metrics]
    write(output / 'metrics.json', metrics)
    csv_fields = [k for k in METRIC_FIELDS if k != 'native_usage']
    with (output / 'metrics.csv').open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(metrics)
    manifest = read(root / 'experiment_manifest.json')
    manifest = {k: manifest[k] for k in MANIFEST_FIELDS if k in manifest}
    manifest.update(system='../../prompts/support_v3_system.txt',
                    skill='../../candidates/haimababi-support/SKILL.md',
                    grader='../../prompts/support_v3_grader.txt',
                    rubric_file='../../rubric/support_v3/rubric.json',
                    run_id=root.name, business_confirmed=False)
    write(output / 'experiment_manifest.json', manifest)
    write(output / 'completion.json', completion)
    for name in ('paired_comparisons', 'wire_usage', 'calibration_pairs'):
        write(output / (name + '.json'), read(root / 'summary' / (name + '.json')))
    totals = {}
    for group in GROUPS:
        totals[group] = read(root / 'summary' / (group + '.json'))
        selected = sorted((m for m in metrics if m['group'] == group), key=lambda m: m['item_id'])
        if len(selected) != 60:
            raise ValueError('Incomplete experiment group')
        entries = []
        index = [f'# {group}组完整回答与评分', '',
                 '开发比较，业务标准待确认；可发送性由同模型判定。', '',
                 f'[完整回答](answers_{group}.md) · [精简评分JSONL](answers_{group}.jsonl)', '',
                 '| 题号 | 题目 | 预览分 | 检索降级 | 预算耗尽 |', '|---|---|---:|---|---|']
        full = [f'# {group}组完整模型回答', '',
                '保留三部分完整回答，仅替换敏感内容；输入会话、私有知识片段和完整调用轨迹未公开。', '']
        for metric in selected:
            ident = metric['item_id']
            score = read(root / 'grading' / group / ident / 'score.json')
            if score['score'] != metric['score']:
                raise ValueError('Score and aggregate disagree')
            answer = clean((root / 'answers' / group / ident / 'answer.md').read_text(encoding='utf-8'))
            title = clean(titles[ident])
            verdict = decision_summary(read(root / 'grading' / group / ident / 'verdict.json'), clean)
            entries.append({'schema_version': 'public-support-v3-result-1',
                            'item_id': ident, 'title': title, 'metrics': metric,
                            'answer': answer, 'score': score, 'judgment_summary': verdict})
            index.append(f'| [{ident}](answers_{group}.md#{ident}) | {title.replace(chr(124), chr(65292))} | {score["score"]} | {metric["degraded"]} | {metric["budget_exhausted"]} |')
            full.extend([f'## {ident}', '', title, '',
                         f'预览分：{score["score"]}；程序完成：{metric["program_completed"]}；检索降级：{metric["degraded"]}；预算耗尽：{metric["budget_exhausted"]}。', '',
                         '\n'.join('#' + line if line.startswith('#') else line for line in answer.splitlines()), '',
                         '### 模型评分摘要', '', verdict['summary'], '',
                         f'客户草稿可发送性：`{verdict["customer_sendability"]}`；数值评分和各维度理由见同组JSONL。', ''])
        (output / f'answers_{group}.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in entries), encoding='utf-8')
        (output / f'answers_{group}.md').write_text('\n'.join(full).rstrip() + '\n', encoding='utf-8')
        (output / f'index_{group}.md').write_text('\n'.join(index) + '\n', encoding='utf-8')
    write(output / 'group_summary.json', totals)
    report = report_path.read_text(encoding='utf-8')
    for group in GROUPS:
        report = report.replace(str(root / 'summary' / f'{group}_完整回答索引.md'), f'index_{group}.md')
    for name in ('metrics.csv', 'wire_usage.json'):
        report = report.replace(str(root / 'summary' / name), name)
    report = report.replace(str(root / 'experiment_manifest.json'), 'experiment_manifest.json')
    report = report.replace('完整回答与原始评分：', '完整回答与精简评分（原始证据与调用轨迹保持私有）：')
    report += '\n公开版说明：逐题文本经二次脱敏；数值指标、分数、维度等级及封顶保持原值。JSONL提供完整模型回答与精简判分理由，不提供客户原始输入、私有知识片段、来源证据表或完整请求。脱敏后的文本不能直接代替原文重建证据行绑定。\n'
    report += '\n指标中的“有效回答”是程序对回答正文与约定结构的检查结果，不能解释为业务正确；“可直接发送”是评分模型判定，尚未经人工业务确认。\n'
    (output / 'report.md').write_text(report, encoding='utf-8')
    write(output / 'publication.json', {
        'schema_version': 'public-support-v3-publication-1', 'run_id': root.name,
        'answer_records': 240, 'judgment_records': 240,
        'numeric_metrics_preserved': True, 'business_confirmed': False,
        'text_redaction_counts': dict(sorted((k, v) for k, v in redactions.items() if v)),
        'excluded': ['customer_inputs', 'private_turn_contracts', 'knowledge_snapshots',
                     'source_evidence_tables', 'call_traces', 'credentials', 'local_paths'],
    })
    print(json.dumps({'groups': len(totals), 'answers': len(metrics),
                      'judgments': len(metrics), 'text_redactions': sum(redactions.values())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--contracts', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--alias-source', type=Path)
    args = parser.parse_args()
    export(args.run_root.resolve(), args.report, args.contracts, args.output_dir, args.alias_source)
