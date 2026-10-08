import copy,unittest
from scoring import score,POINTS,CAPS
class ScoringTests(unittest.TestCase):
 def setUp(self):
  self.b={'business_points':[{'id':'kp1','original_weight':2.5},{'id':'kp2','original_weight':2}]}
  self.v={'needs_review':False,'business_points':{'kp1':'excellent','kp2':'excellent'},'criteria':dict.fromkeys(POINTS,'excellent'),'controls':dict.fromkeys(CAPS,False)}
 def test_full(self):self.assertEqual(score(self.b,self.v)['score'],100)
 def test_severe_overload_not_high_score(self):
  self.v['criteria']['customer_load']='poor';self.assertEqual(score(self.b,self.v)['raw_score'],80);self.assertEqual(score(self.b,self.v)['score'],59)
 def test_safety_takes_lowest_cap(self):
  self.v['criteria']['customer_load']='poor';self.v['controls']['urgent_safety_failure']=True;self.assertEqual(score(self.b,self.v)['score'],20)
 def test_empty_answer(self):
  self.v['controls']['no_answer']=True;self.assertEqual(score(self.b,self.v)['score'],0)
 def test_unequal_kp_weights(self):
  self.v['business_points']['kp2']='poor';self.assertAlmostEqual(score(self.b,self.v)['dimensions']['business_points'],30*2.5/4.5)
 def test_no_duplicate_penalty(self):
  self.v['controls']['urgent_safety_failure']=True;self.v['controls']['decisive_business_error']=True;self.assertEqual(score(self.b,self.v)['score'],20)
 def test_review_unscored(self):
  self.v['needs_review']=True;self.assertIsNone(score(self.b,self.v)['score'])
 def test_missing_is_not_zero(self):
  del self.v['criteria']['grounding']
  with self.assertRaises(ValueError):score(self.b,self.v)
 def test_invalid_level(self):
  self.v['criteria']['grounding']='good'
  with self.assertRaises(ValueError):score(self.b,self.v)
if __name__=='__main__':unittest.main()
