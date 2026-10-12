import copy
import unittest

from scoring import CAPS, POINTS, SPEC, score


class SupportScoringTests(unittest.TestCase):
    def setUp(self):
        self.contract = {
            'review_status': 'author_reviewed_business_pending',
            'business_points': [
                {'id': 'known', 'weight': 2, 'timing': 'required_now'},
                {'id': 'unknown', 'weight': 1, 'timing': 'required_now'},
            ],
            'deferred_steps': [{'condition': '核验出库状态之后', 'action': '反馈对应物流节点'}],
        }
        self.verdict = {
            'needs_review': False,
            'business_points': {'known': 'excellent', 'unknown': 'excellent'},
            'criteria': dict.fromkeys(POINTS, 'excellent'),
            'controls': dict.fromkeys(CAPS, False),
            'customer_sendability': 'send_as_is',
        }

    def test_weights_sum_to_100(self):
        self.assertEqual(SPEC['business_points']['points'] + sum(POINTS.values()), 100)

    def test_unknown_state_and_deferred_steps_do_not_prevent_full_preview(self):
        result = score(self.contract, self.verdict)
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['status'], 'preview_scored')
        self.assertFalse(result['formal_eligible'])

    def test_only_confirmed_reference_is_formal(self):
        self.contract['review_status'] = 'business_confirmed'
        self.assertEqual(score(self.contract, self.verdict)['status'], 'scored')

    def test_fabricated_completed_action_is_capped(self):
        self.verdict['controls']['fabricated_business_state_or_action'] = True
        self.assertEqual(score(self.contract, self.verdict)['score'], 20)

    def test_empty_answer(self):
        self.verdict['controls']['no_answer'] = True
        self.verdict['customer_sendability'] = 'unusable'
        self.assertEqual(score(self.contract, self.verdict)['score'], 0)

    def test_only_generic_internal_support_cannot_get_high_score(self):
        self.verdict['criteria']['internal_support'] = 'poor'
        result = score(self.contract, self.verdict)
        self.assertEqual(result['raw_score'], 80)
        self.assertEqual(result['score'], 59)

    def test_lowest_cap_without_additive_penalties(self):
        self.verdict['criteria']['customer_load'] = 'poor'
        self.verdict['controls']['urgent_safety_failure'] = True
        self.verdict['controls']['decisive_business_error'] = True
        self.assertEqual(score(self.contract, self.verdict)['score'], 20)

    def test_unequal_business_weights(self):
        self.verdict['business_points']['unknown'] = 'poor'
        self.assertEqual(score(self.contract, self.verdict)['dimensions']['business_points'], 20)

    def test_conflict_is_unscored(self):
        self.verdict = {'needs_review': True}
        self.assertIsNone(score(self.contract, self.verdict)['score'])

    def test_missing_level_is_not_zero(self):
        del self.verdict['criteria']['grounding']
        with self.assertRaises(ValueError):
            score(self.contract, self.verdict)

    def test_duplicate_binding_id_rejected(self):
        self.contract['business_points'].append(copy.deepcopy(self.contract['business_points'][0]))
        with self.assertRaises(ValueError):
            score(self.contract, self.verdict)

    def test_deferred_point_in_denominator_rejected(self):
        self.contract['business_points'][0]['timing'] = 'deferred'
        with self.assertRaises(ValueError):
            score(self.contract, self.verdict)

    def test_invalid_values_rejected(self):
        for weight in (0, -1, True, float('nan'), float('inf')):
            with self.subTest(weight=weight):
                self.contract['business_points'][0]['weight'] = weight
                with self.assertRaises(ValueError):
                    score(self.contract, self.verdict)

    def test_string_flag_rejected(self):
        self.verdict['controls']['wrong_task'] = 'false'
        with self.assertRaises(ValueError):
            score(self.contract, self.verdict)

    def test_missing_answer_cannot_be_marked_sendable(self):
        self.verdict['controls']['no_answer'] = True
        with self.assertRaises(ValueError):
            score(self.contract, self.verdict)


if __name__ == '__main__':
    unittest.main()
