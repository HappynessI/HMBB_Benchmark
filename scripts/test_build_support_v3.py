"""Regression checks for data leakage and provenance loss, using invented records."""
import copy
from pathlib import Path
import tempfile
import unittest
from build_support_v3 import build


class CutoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name)
        (self.kb/'boundary.md').write_text('# 核验\n未知状态由当前客服核验。',encoding='utf-8')
        self.contract = {'title':'示例', 'business_type':'物流', 'current_goal':'核验', 'critical_unknowns':['状态'],
                         'accepted_actions':['查记录'], 'customer_now':'核验', 'internal_now':'查记录',
                         'business_points':[{'id':'p','timing':'required_now','scope':'internal','weight':1}],
                         'deferred_steps':[], 'forbidden_actions':['编造']}
        self.spec = {'id':'demo','split':'dev','source_kind':'csv','source_id':'csv-demo','cutoff_index':0,
                     'presentation_roles':['客户'],'knowledge_references':['boundary.md > 核验'], 'contract':self.contract}
        self.corpus = {'csv-demo':{'record_id':'csv-demo', 'problem_types':['FUTURE_LABEL'],
                                  'messages':[{'message_id':'m0','role':'unknown','role_hint':'customer','text':'到哪了？'},
                                              {'message_id':'m1','role':'unknown','text':'FUTURE_ANSWER'}]}}

    def tearDown(self): self.tmp.cleanup()

    def test_no_future_answers_or_whole_record_types_in_input(self):
        answering, _, provenance = build([self.spec],{},self.corpus,self.kb)
        self.assertNotIn('FUTURE_', answering[0]['prompt'])
        self.assertEqual(set(answering[0]), {'id','prompt','input_files'})
        self.assertEqual(len(provenance[0]['messages']),1)

    def test_original_unknown_role_preserved(self):
        _,_,provenance = build([self.spec],{},self.corpus,self.kb)
        self.assertEqual(provenance[0]['messages'][0]['original_role'],'unknown')
        self.assertEqual(provenance[0]['messages'][0]['role_review'],'semantic_provisional_not_sender_verified')

    def test_same_source_cannot_cross_splits(self):
        second=copy.deepcopy(self.spec); second.update(id='demo2',split='calibration')
        with self.assertRaises(ValueError): build([self.spec,second],{},self.corpus,self.kb)

    def test_bad_knowledge_section_rejected(self):
        self.spec['knowledge_references']=['boundary.md > 不存在']
        with self.assertRaises(ValueError): build([self.spec],{},self.corpus,self.kb)

    def test_role_review_must_end_at_customer(self):
        self.spec['presentation_roles']=['客服']
        with self.assertRaises(ValueError): build([self.spec],{},self.corpus,self.kb)


if __name__=='__main__': unittest.main()
