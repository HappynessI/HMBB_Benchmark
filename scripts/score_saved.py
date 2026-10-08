"""Aggregate an existing, reviewed verdict. No model calls or file writes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rubric'))
from scoring import score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--verdict', type=Path, required=True)
    args = parser.parse_args()
    binding = json.loads(args.binding.read_text(encoding='utf-8'))
    verdict = json.loads(args.verdict.read_text(encoding='utf-8'))
    print(json.dumps(score(binding, verdict), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
