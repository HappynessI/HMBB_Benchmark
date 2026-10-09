"""Export the final labelled local JSONL as a compact, de-identified public dataset.

No model calls or credentials. Raw fields, source paths and old annotation snapshots
are deliberately omitted; all distinct visible messages and current evidence remain.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

CATEGORIES = ['催发货','物流问题','售后问题','售前咨询','退换货','其他','产品咨询','价格优惠','投诉抱怨']
PATTERNS = [
    (r'https?://[^\s）)]+|(?:s\.tb\.cn|m\.tb\.cn|tb\.cn)/[^\s]+', '[链接]'),
    (r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱]'),
    (r'(?<!\d)1\d{10}(?!\d)', '[手机号]'),
    (r'(?<!\d)(?:0\d{2,3}[- ]?)?\d{7,}(?!\d)', '[编号]'),
    (r'\b(?:SF|YT|ZTO|STO|JD|JDX)\d+\b', '[快递单号]'),
    (r'\b(?:tb|wxj|ljn)[A-Za-z0-9_]{4,}\b', '[账号]'),
    (r'客户\d+|客服\d+', '[说话人编号]'),
    (r'(?:[A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}', '[设备编号]'),
    (r'/Users/[^\s]+', '[本地路径]'),
]


def export(input_path, output_dir):
    records=[json.loads(x) for x in input_path.open(encoding='utf-8')]
    assert len(records)==4361 and len({r['record_id'] for r in records})==4361
    # Visible sender metadata may contain customer aliases or names. Never publish
    # those metadata fields; also remove occurrences of known aliases in body text.
    aliases=set()
    for r in records:
        for v in [r]+r.get('source_variants',[]):
            for m in v['messages']:
                label=(m.get('speaker_raw') or '').strip()
                if len(label)>=2 and not any(w in label for w in ('客户','客服','用户','买家','卖家','系统','海马爸比')):
                    aliases.add(label)
    def clean(text):
        for alias in sorted(aliases,key=len,reverse=True):
            text=text.replace(alias,'[昵称]')
        for pattern,replacement in PATTERNS:
            text=re.sub(pattern,replacement,text)
        text=re.sub(r'[\u4e00-\u9fff]{2,5}\s*[,，]?\s*(?=\[(?:手机号|电话|联系方式)\])','[姓名] ',text)
        text=re.sub(r'[\u4e00-\u9fff]{2,8}(?:省|市|自治区)\s*[\u4e00-\u9fff\d A-Za-z_\-]*(?:区|县|镇|街|路|村|巷|栋|号)[\u4e00-\u9fff\d A-Za-z_\-]*','[地址]',text)
        return text
    output_dir.mkdir(parents=True,exist_ok=True)
    result=[];types=Counter();formats=Counter();stages=Counter();status=Counter()
    for r in records:
        messages=[];lookup={};seen=set()
        for vi,v in enumerate([r]+r.get('source_variants',[])):
            for mi,m in enumerate(v['messages']):
                key=(m['role'],m.get('role_hint'),m.get('timestamp_raw'),m['text'])
                if key in seen:continue
                seen.add(key);ident=f'v{vi}:m{mi}'
                entry={'message_id':ident,'role':m['role'],'role_hint':m.get('role_hint'),
                       'timestamp':m.get('timestamp_raw'),'text':clean(m['text']),
                       'media_status':m.get('media_status')}
                messages.append(entry);lookup[ident]=entry
        final=r['problem_type_final_status'];source=r[final['source_field']]
        annotation=source.get('review') or source.get('annotation')
        intents=[]
        def evidence(entries):
            out=[]
            for e in entries:
                ident=e['message_id'];assert ident in lookup
                out.append({'message_id':ident,'quote':lookup[ident]['text']})
            return out
        for i in annotation['intents']:
            entry={'type':i['type'],'summary':clean(i['summary'])}
            if 'evidence' in i:
                entry.update(basis='客户正文',customer_evidence=evidence(i['evidence']),agent_context_evidence=[])
            else:
                entry.update(basis=i['basis'],customer_evidence=evidence(i['customer_evidence']),
                             agent_context_evidence=evidence(i['agent_context_evidence']))
            intents.append(entry)
        assert set(r['problem_types'])=={i['type'] for i in intents}
        latest={k:v for k,v in final.items() if k!='source_field'}
        # First-pass records did not provide the two independent certainty axes.
        # Preserve nulls rather than inventing confidence or completeness values.
        latest['label_basis']=list(dict.fromkeys(i['basis'] for i in intents))
        entry={'schema_version':'public-dialogue-v1','record_id':r['record_id'],
               'source_format':r['source_format'],'messages':messages,'problem_types':r['problem_types'],
               'classification':latest,'intents':intents}
        if final['classification_status']=='insufficient_information':
            entry['information_gap_reason']=clean(r['problem_type_codex_review']['decision_reason'])
        result.append(entry);types.update(r['problem_types']);formats[r['source_format']]+=1
        stages[final['applied_stage']]+=1;status[final['classification_status']]+=1
    target=output_dir/'dialogues.jsonl'
    target.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in result),encoding='utf-8')
    stats={'total_records':len(result),'source_format_counts':dict(formats),'classification_status_counts':dict(status),
           'applied_stage_counts':dict(stages),'problem_type_counts':dict(types),
           'multi_label_records':sum(len(r['problem_types'])>1 for r in result),
           'distinct_visible_messages':sum(len(r['messages']) for r in result),
           'review_scope':{'selected':1105,'turbo_adopted':878,'codex_reviewed':227,'codex_classified':162,'insufficient_information':65},
           'model':'doubao-seed-2-1-turbo-260628','notes':'Includes all 4361 records; this is a labelled dialogue pool, not a finalized evaluation set.'}
    (output_dir/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output_dir/'insufficient_ids.json').write_text(json.dumps([r['record_id'] for r in result if r['classification']['needs_additional_context']],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    content=target.read_text(encoding='utf-8')
    assert not re.search(r'/Users/|(?<!\d)1\d{10}(?!\d)|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',content)
    for r in result:
        messages={m['message_id']:m for m in r['messages']}
        for i in r['intents']:
            for e in i['customer_evidence']+i['agent_context_evidence']:
                assert e['quote']==messages[e['message_id']]['text']
    print(json.dumps({'records':len(result),'classified':status['classified'],'insufficient':status['insufficient_information'],
                      'messages':stats['distinct_visible_messages'],'bytes':target.stat().st_size},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path('data/processed_dialogues'))
    args=parser.parse_args();export(args.input,args.output_dir)
