#!/usr/bin/env python3
"""Evaluate recorded JSON windows; synthetic scores are not phone validation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.gestures import load_config, recognize

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--minimum-accuracy', type=float, default=0)
    args = parser.parse_args()
    config = load_config(args.config) if args.config else load_config()
    labels = ['bolt', 'ward', 'empower', 'hex', 'unknown']
    matrix = {a:{b:0 for b in labels} for a in labels}
    total = correct = 0
    for path in sorted(args.directory.rglob('*.json')):
        try:
            item = json.loads(path.read_text());label = item['label']
            if label not in labels: raise ValueError('Unknown label')
            prediction, _ = recognize(item['samples'], item.get('platform', 'other'), config)
            prediction = prediction or 'unknown'
            matrix[label][prediction] += 1;total += 1;correct += prediction == label
        except (KeyError, ValueError) as exc:
            print(f'{path}: {exc}', file=sys.stderr);return 2
    if not total:
        print('No recorded samples found. Capture real phone gestures at /record.', file=sys.stderr);return 2
    print('Rows: actual. Columns: predicted.\n')
    print(f'{"":12}' + ''.join(f'{s:>10}' for s in labels))
    for label in labels:print(f'{label:12}' + ''.join(f'{matrix[label][p]:10}' for p in labels))
    accuracy = correct/total
    print(f'\nAccuracy: {correct}/{total} = {accuracy:.1%}')
    return 0 if accuracy >= args.minimum_accuracy else 1

if __name__ == '__main__':raise SystemExit(main())
