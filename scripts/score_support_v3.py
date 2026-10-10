"""Score one reviewed answer or export its exact original-line evidence catalog."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rubric/support_v3'))
from verdict import checked_score, evidence_catalog


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--answer', required=True, type=Path)
    parser.add_argument('--catalog-only', action='store_true')
    parser.add_argument('--contract', type=Path, help='One JSON object or private contracts.jsonl with --id')
    parser.add_argument('--id', help='Select one contract from JSONL')
    parser.add_argument('--verdict', type=Path, help='Rich verdict in prompts/support_v3_grader.txt format')
    parser.add_argument('--sources', type=Path, help='Grader-side source-ID catalog, e.g. {"K1":"path > section"}')
    args = parser.parse_args()
    answer = args.answer.read_text(encoding='utf-8')
    if args.catalog_only:
        print(json.dumps(evidence_catalog(answer), ensure_ascii=False, indent=2))
        return
    if not all((args.contract, args.verdict, args.sources)):
        parser.error('Scoring requires --contract, --verdict and --sources')
    if args.id:
        contracts = [json.loads(line, object_pairs_hook=unique_object)
                     for line in args.contract.read_text(encoding='utf-8').splitlines() if line.strip()]
        matches = [c for c in contracts if c['id'] == args.id]
        if len(matches) != 1:
            raise ValueError('Contract ID must have exactly one match')
        contract = matches[0]
    else:
        contract = read_json(args.contract)
    result = checked_score(contract, read_json(args.verdict), answer, read_json(args.sources))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
