"""Check verdict structure and catalog bindings, not semantic evidence validity."""
from scoring import CAPS, POINTS, VALUES, _exact_keys, score


def evidence_catalog(answer):
    return {f'L{number:04}': line for number, line in enumerate(answer.splitlines(), 1) if line.strip()}


def checked_score(contract, verdict, answer, sources):
    catalog = evidence_catalog(answer)
    if type(verdict.get('needs_review')) is not bool:
        raise ValueError('needs_review must be a boolean')
    reasons = verdict.get('review_reasons')
    if not isinstance(reasons, list) or not all(isinstance(s, str) and s.strip() for s in reasons):
        raise ValueError('review_reasons must contain nonempty strings')
    if verdict['needs_review'] and not reasons:
        raise ValueError('Review required but no reason provided')
    if not verdict['needs_review'] and reasons:
        raise ValueError('Review reasons contradict needs_review=false')
    context = verdict.get('context')
    _exact_keys(context, ['known', 'unknown', 'current_goal', 'immediate_risks'], 'context')
    for field in ('known', 'unknown', 'immediate_risks'):
        if not isinstance(context[field], list) or not all(isinstance(s, str) for s in context[field]):
            raise ValueError('Invalid context list')
    if not isinstance(context['current_goal'], str) or not context['current_goal'].strip():
        raise ValueError('Missing current goal')
    if not isinstance(verdict.get('summary'), str) or not verdict['summary'].strip():
        raise ValueError('Missing verdict summary')
    if not isinstance(sources, dict) or not all(isinstance(k, str) and k for k in sources):
        raise ValueError('Sources must be a source-ID catalog')
    flat = {'needs_review': verdict['needs_review'], 'customer_sendability': verdict.get('customer_sendability')}
    bindings = {'business_points': [p['id'] for p in contract['business_points']], 'criteria': POINTS, 'controls': CAPS}
    for group, keys in bindings.items():
        _exact_keys(verdict.get(group), keys, group)
        flat[group] = {}
        for key, judgment in verdict[group].items():
            fields = ['triggered', 'reason', 'evidence_ids', 'sources'] if group == 'controls' else [
                'rating', 'reason', 'evidence_ids', 'missing', 'sources']
            _exact_keys(judgment, fields, f'{group}.{key}')
            if not isinstance(judgment['reason'], str) or not judgment['reason'].strip():
                raise ValueError(f'Missing reason: {group}.{key}')
            for field, available in [('evidence_ids', catalog), ('sources', sources)]:
                chosen = judgment[field]
                if not isinstance(chosen, list) or not all(isinstance(s, str) for s in chosen):
                    raise ValueError(f'Invalid {field}: {group}.{key}')
                if len(chosen) != len(set(chosen)) or not set(chosen) <= set(available):
                    raise ValueError(f'Unknown or duplicate {field}: {group}.{key}')
            if group == 'controls':
                if type(judgment['triggered']) is not bool:
                    raise ValueError('triggered must be a boolean')
                flat[group][key] = judgment['triggered']
            else:
                if judgment['rating'] not in VALUES or not isinstance(judgment['missing'], str):
                    raise ValueError('Invalid rating or missing text')
                if not judgment['evidence_ids'] and not judgment['missing'].strip():
                    raise ValueError('Supply answer evidence or explain the omission')
                flat[group][key] = judgment['rating']
    result = score(contract, flat)
    result['validation'] = 'structure_and_catalog_binding_only'
    result['semantic_evidence_review'] = 'required_separately'
    return result
