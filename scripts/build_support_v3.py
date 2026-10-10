"""Build a cutoff-specific pilot. Requires private authoring and legacy sources."""
import argparse
from collections import Counter
import json
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows), encoding='utf-8')


def check_references(references, kb_root):
    for reference in references:
        relative, _, section = reference.partition(' > ')
        path = (kb_root / relative).resolve()
        if not path.is_relative_to(kb_root.resolve()) or not path.is_file():
            raise ValueError(f'Invalid knowledge reference: {reference}')
        if section and section not in path.read_text(encoding='utf-8'):
            raise ValueError(f'Missing knowledge section: {reference}')


def select_prefix(spec, legacy, corpus):
    if spec['source_kind'] == 'legacy':
        original = legacy[spec['source_id']]
        messages = [dict(m, message_id=m['source_locator'], original_role=m['role']) for m in original['messages']]
        if not messages or messages[-1]['source_locator'] != original['cutoff']:
            raise ValueError('Legacy cutoff does not match selected messages')
        # Original real120 is already a selected prefix. Preserve its omitted-message status.
        return messages, 'legacy:' + original['source_case'], original['knowledge_references'], {
            'source_kind': 'legacy', 'source_id': spec['source_id'],
            'source_case': original['source_case'], 'source_file': original['source_file'],
            'cutoff': original['cutoff'], 'partial_excerpt': True,
            'source_format': Path(original['source_file']).suffix.lstrip('.'),
        }
    if spec['source_kind'] != 'csv':
        raise ValueError('Unsupported source kind')
    original = corpus[spec['source_id']]
    cutoff = spec['cutoff_index']
    if type(cutoff) is not int or not 0 <= cutoff < len(original['messages']):
        raise ValueError('Invalid cutoff index')
    prefix = original['messages'][:cutoff + 1]
    roles = spec['presentation_roles']
    if len(roles) != len(prefix) or roles[-1] != '客户':
        raise ValueError('Manually reviewed roles must cover the prefix and end at a customer question')
    messages = []
    for message, presentation in zip(prefix, roles):
        if presentation not in ('客户', '客服', '记录信息（角色未确认）'):
            raise ValueError('Invalid presentation role')
        messages.append({**message, 'original_role': message['role'],
                         'role': presentation, 'role_review': 'semantic_provisional_not_sender_verified'})
    return messages, 'csv:' + original['record_id'], spec['knowledge_references'], {
        'source_kind': 'csv', 'source_id': spec['source_id'], 'source_format': 'csv',
        'cutoff_index': cutoff, 'cutoff': prefix[-1]['message_id'],
        'candidate_timestamp': prefix[-1].get('timestamp'),
        'timestamp_status': 'source_parser_candidate_not_verified_session',
        'role_status': 'original_unknown_with_manual_semantic_presentation',
        'record_group_is_not_verified_customer_identity': True,
    }


def build(specs, legacy, corpus, kb_root):
    answering, contracts, provenance = [], [], []
    seen_ids, groups = set(), {}
    for spec in specs:
        key = spec['id']
        if key in seen_ids:
            raise ValueError('Duplicate item ID')
        seen_ids.add(key)
        split = spec['split']
        if split not in ('dev', 'calibration'):
            raise ValueError('Pilot has no frozen test split')
        messages, group, references, origin = select_prefix(spec, legacy, corpus)
        if group in groups and groups[group] != split:
            raise ValueError('Source group crosses splits')
        groups[group] = split
        check_references(references, kb_root)
        contract = spec['contract']
        required = ('title', 'business_type', 'current_goal', 'critical_unknowns', 'accepted_actions',
                    'customer_now', 'internal_now', 'business_points', 'deferred_steps', 'forbidden_actions')
        if any(field not in contract for field in required):
            raise ValueError('Incomplete per-turn contract')
        points = contract['business_points']
        if not points or len({p['id'] for p in points}) != len(points):
            raise ValueError('Missing or duplicate business point')
        if any(p['timing'] != 'required_now' or p['scope'] not in ('customer', 'internal', 'either')
               or type(p['weight']) not in (int, float) or p['weight'] <= 0 for p in points):
            raise ValueError('Invalid current-turn business point')
        # Never forward full-record labels, reference answers, or future messages.
        body = '\n'.join((f"[{m['timestamp']}] " if m.get('timestamp') else '')
                         + f"{m['role']}：{m['text']}" for m in messages)
        timestamp = origin.get('candidate_timestamp')
        time_note = f'\n【记录中的候选时间】{timestamp}；只作历史语境，不证明政策或状态。' if timestamp else ''
        role_note = ('CSV角色按文字语义暂定，角色未确认的卡片不能当作当前状态证明。'
                     if spec['source_kind'] == 'csv' else '')
        prompt = ('【客服求助】请协助当前一线客服处理以下会话，给客户草稿、依据及客服下一步。'
                  '\n【可见会话】仅到当前客户问题；可能省略历史内容，未附原始图片或视频。'
                  + role_note
                  + time_note + '\n' + body)
        answering.append({'id': key, 'prompt': prompt, 'input_files': ['knowledge_base']})
        contracts.append({**contract, 'id': key, 'schema_version': 'support-v3-turn-contract-1',
                          'split': split, 'group_id': group, 'knowledge_references': references,
                          'review_status': 'author_reviewed_business_pending',
                          'reference_basis': 'provided_kb_snapshot_not_historical_policy_reconstruction',
                          'runtime_profile': {'business_query': False, 'business_execution': False}})
        provenance.append({'id': key, 'split': split, 'group_id': group, **origin, 'messages': messages,
                           'knowledge_references': references, 'review_status': 'author_reviewed_business_pending'})
    return answering, contracts, provenance


def render_review(items, contracts, provenance):
    rows = ['# 客服支持助手 v3：60题试点审阅稿', '',
            '作者已逐题整理；全部待业务确认。dev用于开发，calibration用于校准判分，均不是冻结测试集。',
            'CSV角色仅按文本语义暂定；时间来自解析候选值。知识依据为所提供知识库快照，不代表历史活动复原。', '',
            '草稿标准允许等价表达，不是唯一参考答案。后续步骤在条件未触发时不进入本轮必答分母。', '']
    for item, contract, source in zip(items, contracts, provenance):
        rows.extend([f"## {item['id']} · {contract['title']} · {contract['split']}", '',
                     f"来源组：{source['group_id']}；截止：{source['cutoff']}；类型：{contract['business_type']}", '',
                     '### 完整作答输入', '', item['prompt'], '', '### 本轮标准', '',
                     f"目标：{contract['current_goal']}",
                     '关键未知：' + '；'.join(contract['critical_unknowns']),
                     '允许动作：' + '；'.join(contract['accepted_actions']),
                     '客户草稿：' + contract['customer_now'],
                     '客服内部：' + contract['internal_now'], '', '本轮业务点：', ''])
        rows.extend(f"- {p['id']}（{p['scope']}，权重{p['weight']}）：{p['requirement']}" for p in contract['business_points'])
        rows.extend(['', '有条件后续：', ''])
        rows.extend(f"- 若{p['condition']}：{p['action']}" for p in contract['deferred_steps'])
        rows.extend(['', '禁用判断或动作：' + '；'.join(contract['forbidden_actions']), '', '知识定位：', ''])
        rows.extend('- ' + reference for reference in contract['knowledge_references'])
        rows.append('')
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authoring', required=True, type=Path)
    parser.add_argument('--legacy-provenance', required=True, type=Path)
    parser.add_argument('--corpus', required=True, type=Path)
    parser.add_argument('--knowledge-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='Private directory, not an Agent working directory')
    parser.add_argument('--manifest', type=Path, help='Optional public aggregate manifest')
    args = parser.parse_args()
    specs = json.loads(args.authoring.read_text(encoding='utf-8'))
    legacy = {p['id']: p for p in json.loads(args.legacy_provenance.read_text(encoding='utf-8'))}
    corpus = {p['record_id']: p for p in read_jsonl(args.corpus)}
    items, contracts, provenance = build(specs, legacy, corpus, args.knowledge_root)
    if len(items) != 60 or Counter(p['source_kind'] for p in provenance) != {'legacy': 30, 'csv': 30}:
        raise ValueError('Expected the reviewed 30+30 pilot')
    if Counter(c['split'] for c in contracts) != {'dev': 40, 'calibration': 20}:
        raise ValueError('Expected dev40/calibration20')
    write_jsonl(args.output / 'answering/items.jsonl', items)
    write_jsonl(args.output / 'grading/contracts.jsonl', contracts)
    write_jsonl(args.output / 'provenance.jsonl', provenance)
    (args.output / '审阅版.md').write_text(render_review(items, contracts, provenance), encoding='utf-8')
    manifest = {'version': 'support-v3-pilot60-candidate', 'total': len(items),
                'source_kinds': dict(Counter(p['source_kind'] for p in provenance)),
                'splits': dict(Counter(c['split'] for c in contracts)), 'source_groups': len({p['group_id'] for p in provenance}),
                'current_turn_types': dict(Counter(c['business_type'] for c in contracts)),
                'csv_current_turn_types': dict(Counter(c['business_type'] for c,p in zip(contracts,provenance) if p['source_kind']=='csv')),
                'reference_status': '60 author-reviewed; 0 business-confirmed',
                'checks': {'source_cutoff': 'passed', 'source_group_split_isolation': 'passed',
                           'knowledge_file_and_section_locations': 'passed', 'answerer_has_no_grading_fields': 'passed'},
                'limitations': ['No verified sender metadata for CSV', 'No verified independent customer identities',
                                'KB snapshot is not a reconstruction of historical policy',
                                'No held-out test; model scores are development previews, not business confirmation', 'KB location checks do not establish business truth']}
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
