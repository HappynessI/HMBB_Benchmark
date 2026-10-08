"""Deterministic aggregation only: no LLM, credentials or mutation of answers."""
import math
VALUES={'excellent':1.0,'adequate':0.5,'poor':0.0}
POINTS={'turn_decision':20,'customer_load':20,'natural_contextual_reply':15,'grounding':10,'internal_support':5}
CAPS={'no_answer':0,'wrong_task':20,'decisive_business_error':20,'urgent_safety_failure':20}
def score(binding,verdict):
    if verdict.get('needs_review') is not False:
        return {'status':'needs_review','score':None}
    kp=binding['business_points'];ratings=verdict['business_points'];general=verdict['criteria'];flags=verdict['controls']
    if set(ratings)!={x['id'] for x in kp} or set(general)!=set(POINTS) or set(flags)!=set(CAPS):raise ValueError('Missing, duplicate or unknown rubric IDs')
    if not all(x in VALUES for x in [*ratings.values(),*general.values()]):raise ValueError('Unknown rating')
    if not all(type(x) is bool for x in flags.values()):raise ValueError('Control flags must be booleans')
    weights=[x['original_weight'] for x in kp]
    if not kp or not all(isinstance(w,(float,int)) and not isinstance(w,bool) and math.isfinite(w) and w>0 for w in weights):raise ValueError('Invalid business weights')
    parts={'business_points':30*sum(x['original_weight']*VALUES[ratings[x['id']]] for x in kp)/sum(weights)}
    parts.update({k:w*VALUES[general[k]] for k,w in POINTS.items()})
    active={k:CAPS[k] for k,v in flags.items() if v}
    if general['turn_decision']=='poor':active['severe_turn_failure']=59
    if general['customer_load']=='poor':active['severe_customer_overload']=59
    raw=sum(parts.values());value=min([max(0,min(100,raw)),*active.values()])
    return {'status':'scored','dimensions':parts,'raw_score':raw,'caps':active,'score':round(value,2)}
