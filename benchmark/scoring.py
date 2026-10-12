"""Aggregate reviewed v3 levels; this module does not judge language or sources."""
import json
import math
from pathlib import Path

SPEC = json.loads(Path(__file__).with_name('rubric.json').read_text(encoding='utf-8'))
VALUES = SPEC['ratings']
POINTS = {key: value['points'] for key, value in SPEC['criteria'].items()}
CAPS = {key: value['cap'] for key, value in SPEC['controls'].items()}


def _exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'{label}: missing or unknown IDs')


def score(contract, verdict):
    """Return a preview for candidate references; never silently fill missing levels."""
    if type(verdict.get('needs_review')) is not bool:
        raise ValueError('needs_review must be a boolean')
    if verdict['needs_review']:
        return {'status': 'needs_review', 'score': None, 'formal_eligible': False}
    points = contract.get('business_points')
    if not isinstance(points, list) or not points:
        raise ValueError('business_points must be a non-empty list')
    ids = [point.get('id') for point in points]
    if any(not isinstance(key, str) or not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError('business point IDs must be unique non-empty strings')
    weights = [point.get('weight') for point in points]
    if not all(type(w) in (int, float) and math.isfinite(w) and w > 0 for w in weights):
        raise ValueError('business weights must be finite and positive')
    if any(point.get('timing') != 'required_now' for point in points):
        raise ValueError('Deferred points must not enter the current-turn denominator')
    _exact_keys(verdict.get('business_points'), ids, 'business_points')
    _exact_keys(verdict.get('criteria'), POINTS, 'criteria')
    _exact_keys(verdict.get('controls'), CAPS, 'controls')
    ratings = [*verdict['business_points'].values(), *verdict['criteria'].values()]
    if not all(isinstance(level, str) and level in VALUES for level in ratings):
        raise ValueError('Unknown rating; missing is not poor and NA is not accepted')
    if not all(type(flag) is bool for flag in verdict['controls'].values()):
        raise ValueError('Controls must be booleans')
    sendability = verdict.get('customer_sendability')
    if sendability not in SPEC['customer_sendability']:
        raise ValueError('Invalid customer_sendability')
    review = contract.get('review_status')
    if review not in ('author_reviewed_business_pending', 'business_confirmed'):
        raise ValueError('Unknown reference review_status')
    if verdict['controls']['no_answer'] and sendability != 'unusable':
        raise ValueError('A missing answer cannot be sendable')
    dimensions = {
        'business_points': SPEC['business_points']['points'] * sum(
            point['weight'] * VALUES[verdict['business_points'][point['id']]]
            for point in points
        ) / sum(weights)
    }
    dimensions.update({key: weight * VALUES[verdict['criteria'][key]] for key, weight in POINTS.items()})
    active = {key: CAPS[key] for key, flag in verdict['controls'].items() if flag}
    for key, cap in SPEC['poor_caps'].items():
        if verdict['criteria'][key] == 'poor':
            active['severe_' + key] = cap
    raw = sum(dimensions.values())
    total = min([max(0, min(100, raw)), *active.values()])
    confirmed = review == 'business_confirmed'
    return {
        'status': 'scored' if confirmed else 'preview_scored',
        'formal_eligible': confirmed,
        'rubric_version': SPEC['version'],
        'dimensions': dimensions,
        'raw_score': raw,
        'caps': active,
        'score': round(total, 2),
        'customer_sendability': sendability,
    }
