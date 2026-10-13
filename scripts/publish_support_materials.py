import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
import shutil

import yaml

from build_support_v3 import check_references, read_jsonl, write_jsonl


SENSITIVE_PATTERNS = (
    r'(?:/Users/|/private/tmp/|/tmp/|[A-Z]:\\Users\\)',
    r'(?<!\d)1\d{10}(?!\d)',
    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',
    r'(?<!\d)\d{7,}(?!\d)',
    r'\b(?:SF|YT|ZTO|STO|JD|JDX)\d+\b',
    r'\b(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}|\bsk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9_.-]{16,}',
    r'[\u4e00-\u9fff]{2,8}(?:省|市|自治区)[\u4e00-\u9fff\d A-Za-z_\-]*(?:区|县|镇|街|路|村|巷|栋|号)[\u4e00-\u9fff\d A-Za-z_\-]*',
)


def check_text(content, label):
    if any(re.search(pattern, content) for pattern in SENSITIVE_PATTERNS):
        raise ValueError(f'Sensitive content requires review: {label}')


def render(items, contracts):
    by_id = {item['id']: item for item in items}
    split_names = {'dev': '开发题', 'calibration': '校准题'}
    scope_names = {'customer': '客户草稿', 'internal': '客服内部', 'either': '任一部分'}
    lines = ['# 60道测试题与逐题标准', '',
             '按题号展开查看完整输入和本轮评分标准。', '',
             '[作答输入 JSONL](answering/items.jsonl) · [逐题标准 JSONL](grading/contracts.jsonl) · '
             '[题集说明](README.md)', '']
    for contract in contracts:
        item = by_id[contract['id']]
        label = f'{item["id"]} · {contract["title"]} · {split_names[contract["split"]]}'
        lines += ['<details>', '<summary>' + html.escape(label) + '</summary>', '',
                  '### 完整作答输入', '', '````text', item['prompt'], '````', '',
                  '### 本轮标准', '', '目标：' + contract['current_goal'], '',
                  '关键未知：', '']
        lines += ['- ' + value for value in contract['critical_unknowns']] or ['无。']
        lines += ['', '允许动作：', '']
        lines += ['- ' + value for value in contract['accepted_actions']]
        lines += ['', '客户草稿：' + contract['customer_now'], '',
                  '客服内部：' + contract['internal_now'], '', '本轮业务点：', '',
                  '| 编号 | 适用部分 | 权重 | 要求 |', '|---|---|---:|---|']
        for point in contract['business_points']:
            requirement = point['requirement'].replace('|', '｜')
            lines.append(f'| {point["id"]} | {scope_names[point["scope"]]} | '
                         f'{point["weight"]:g} | {requirement} |')
        lines += ['', '反馈后的分支：', '']
        lines += ['- 若' + step['condition'] + '：' + step['action']
                  for step in contract['deferred_steps']] or ['无。']
        lines += ['', '禁止动作或判断：', '']
        lines += ['- ' + value for value in contract['forbidden_actions']]
        lines += ['', '知识定位：', '']
        for reference in contract['knowledge_references']:
            path, _, section = reference.partition(' > ')
            label = reference.replace('[', '［').replace(']', '］')
            lines.append(f'- [{label}](../knowledge_base/{path})')
        lines += ['', '</details>', '']
    return '\n'.join(lines)


def publish(knowledge_root, benchmark_source, repo):
    manifest = yaml.safe_load((knowledge_root / 'kb_manifest.yaml').read_text())
    paths = [document['path'] for document in manifest['active_documents']]
    if len(paths) != len(set(paths)) or len(paths) != 29:
        raise ValueError('Expected 29 unique active knowledge documents')
    items = read_jsonl(benchmark_source / 'answering/items.jsonl')
    contracts = read_jsonl(benchmark_source / 'grading/contracts.jsonl')
    provenance = read_jsonl(benchmark_source / 'provenance.jsonl')
    if len(items) != len(contracts) or len(items) != len(provenance) or len(items) != 60:
        raise ValueError('Expected sixty inputs, contracts and source records')
    ids = {item['id'] for item in items}
    if len(ids) != 60 or ids != {c['id'] for c in contracts} or ids != {p['id'] for p in provenance}:
        raise ValueError('Question IDs are inconsistent')
    if Counter(c['split'] for c in contracts) != {'dev': 40, 'calibration': 20}:
        raise ValueError('Question splits changed')
    if Counter(p['source_kind'] for p in provenance) != {'legacy': 30, 'csv': 30}:
        raise ValueError('Question sources changed')
    for relative in paths:
        source = (knowledge_root / relative).resolve()
        if not source.is_relative_to(knowledge_root.resolve()) or '_archive' in Path(relative).parts:
            raise ValueError('Invalid active knowledge path: ' + relative)
        check_text(source.read_text(), relative)
    for item in items:
        check_text(json.dumps(item, ensure_ascii=False), item['id'])
    for contract in contracts:
        check_text(json.dumps(contract, ensure_ascii=False), contract['id'])
        check_references(contract['knowledge_references'], knowledge_root)

    destination = repo / 'knowledge_base'
    for relative in paths:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(knowledge_root / relative, target)
        target.chmod(0o644)
    benchmark = repo / 'benchmark'
    # 题干和评分标准已经脱敏，保留实验所用的原始文本与权重。
    for relative in ('answering/items.jsonl', 'grading/contracts.jsonl'):
        target = benchmark / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(benchmark_source / relative, target)
    sources = [{'id': source['id'], 'split': source['split'], 'group_id': source['group_id'],
                'source_kind': source['source_kind'], 'source_format': source['source_format'],
                'visible_message_count': len(source['messages']),
                'cutoff_index': len(source['messages']) - 1}
               for source in provenance]
    write_jsonl(benchmark / 'provenance.jsonl', sources)
    (benchmark / '题目与标准.md').write_text(render(items, contracts), encoding='utf-8')
    print(json.dumps({'knowledge_documents': len(paths), 'questions': len(items),
                      'contracts': len(contracts), 'source_records': len(sources)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--knowledge-root', required=True, type=Path)
    parser.add_argument('--benchmark-source', required=True, type=Path)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    publish(args.knowledge_root, args.benchmark_source, args.repo_root)
