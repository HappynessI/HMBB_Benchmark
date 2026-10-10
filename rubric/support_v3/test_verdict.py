import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from verdict import checked_score, evidence_catalog
from scoring import CAPS, POINTS


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.answer = '## 建议回复（可直接发给客户）\n我先核对这笔订单的退款进度。\n\n## 下一步\n客服核对退款阶段，未确认前不要保证到账。'
        self.contract = {'review_status':'author_reviewed_business_pending',
                         'business_points':[{'id':'p1', 'timing':'required_now', 'weight':1}]}
        judgment = {'rating':'excellent', 'reason':'示例中有待核验动作。',
                    'evidence_ids':['L0002'], 'missing':'', 'sources':['conversation']}
        self.verdict = {'needs_review':False, 'review_reasons':[],
                        'context':{'known':['客户问退款'], 'unknown':['进度'], 'current_goal':'核验进度', 'immediate_risks':[]},
                        'business_points':{'p1':copy.deepcopy(judgment)},
                        'criteria':{key:copy.deepcopy(judgment) for key in POINTS},
                        'controls':{key:{'triggered':False, 'reason':'结构示例，未触发。', 'evidence_ids':[], 'sources':[]}
                                    for key in CAPS},
                        'customer_sendability':'send_as_is', 'summary':'只用于验证结构，非业务评审。'}
        self.sources = {'conversation':'本题截止点前会话'}

    def test_original_line_numbers_preserve_blank_lines(self):
        catalog = evidence_catalog(self.answer)
        self.assertNotIn('L0003', catalog)
        self.assertEqual(catalog['L0005'], '客服核对退款阶段，未确认前不要保证到账。')

    def test_checked_structure_is_preview_not_semantic_verification(self):
        result = checked_score(self.contract, self.verdict, self.answer, self.sources)
        self.assertEqual(result['status'], 'preview_scored')
        self.assertEqual(result['semantic_evidence_review'], 'required_separately')

    def test_invented_evidence_id_rejected(self):
        self.verdict['business_points']['p1']['evidence_ids'] = ['L9999']
        with self.assertRaises(ValueError): checked_score(self.contract, self.verdict, self.answer, self.sources)

    def test_unlisted_source_rejected(self):
        self.verdict['criteria']['grounding']['sources'] = ['fake_order_api']
        with self.assertRaises(ValueError): checked_score(self.contract, self.verdict, self.answer, self.sources)

    def test_omission_requires_explanation(self):
        self.verdict['business_points']['p1']['evidence_ids'] = []
        with self.assertRaises(ValueError): checked_score(self.contract, self.verdict, self.answer, self.sources)

    def test_duplicate_evidence_rejected(self):
        self.verdict['business_points']['p1']['evidence_ids'] *= 2
        with self.assertRaises(ValueError): checked_score(self.contract, self.verdict, self.answer, self.sources)

    def test_review_requires_reason(self):
        self.verdict['needs_review'] = True
        with self.assertRaises(ValueError): checked_score(self.contract, self.verdict, self.answer, self.sources)

    def test_valid_unscored_review(self):
        self.verdict['needs_review'] = True
        self.verdict['review_reasons'] = ['适用政策有冲突，需要业务确认。']
        result = checked_score(self.contract, self.verdict, self.answer, self.sources)
        self.assertIsNone(result['score'])

    def run_cli(self, duplicate=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'answer.md').write_text(self.answer,encoding='utf-8')
            for name,value in [('contract',self.contract),('verdict',self.verdict),('sources',self.sources)]:
                text=json.dumps(value,ensure_ascii=False)
                if duplicate and name=='verdict': text=text.replace('"needs_review": false','"needs_review": false, "needs_review": true')
                (root/(name+'.json')).write_text(text,encoding='utf-8')
            command=[sys.executable,str(Path(__file__).resolve().parents[2]/'scripts/score_support_v3.py'),
                     '--answer',str(root/'answer.md'),'--contract',str(root/'contract.json'),
                     '--verdict',str(root/'verdict.json'),'--sources',str(root/'sources.json')]
            return subprocess.run(command,text=True,capture_output=True)

    def test_cli_round_trip(self):
        result=self.run_cli()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'preview_scored')

    def test_cli_rejects_duplicate_json_keys(self):
        result=self.run_cli(duplicate=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Duplicate JSON key',result.stderr)


if __name__ == '__main__':
    unittest.main()
