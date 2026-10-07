#!/usr/bin/env python3
"""Audit raw v3 provenance, usage, and literal payload fidelity without inference."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations/agentdojo'))
from agentdojo.task_suite.load_suites import get_suite
from safe_environment import load_safe_environment


def digest(value, **kwargs):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), **kwargs).encode()).hexdigest()


def audit(root):
    suite = get_suite('v1.2.2', 'workspace')
    fidelity, transport, episodes, models = Counter(), Counter(), Counter(), Counter()
    checked = 0
    seen = set()
    details = []
    for path in sorted(root.rglob('before-call.json')):
        before = json.loads(path.read_text())
        payload = json.loads((path.parent / 'injections.json').read_text())
        assert digest(payload, ensure_ascii=False) == before['injectionsSha256'], path
        assert digest(before['configuration'], allow_nan=False) == before['configurationSha256'], path
        assert before['sessionId'] not in seen, path
        seen.add(before['sessionId'])
        checked += 1
        literal = load_safe_environment(suite, payload).model_dump()
        try:
            legacy = suite.load_and_inject_default_environment(payload).model_dump()
            status = 'identical' if literal == legacy else 'different'
        except Exception as error:
            status = type(error).__name__
        fidelity[status] += 1
        details.append({'trial': str(path.parent.relative_to(root)), 'legacyVersusLiteral': status,
                        'recordedLoader': before['configuration'].get('environmentLoader', 'legacy-loader-before-field-added')})
    reported_tokens = reserved_tokens = 0
    for path in sorted(root.rglob('usage.jsonl')):
        for row in map(json.loads, path.read_text().splitlines()):
            if row['status'] == 'completed':
                reported_tokens += row['totalTokens']
                models[row['responseModel']] += 1
            else:
                reserved_tokens += row['totalTokens']
    for path in sorted(root.rglob('usage.jsonl.transport.jsonl')):
        for row in map(json.loads, path.read_text().splitlines()):
            transport[row['status']] += 1
    for path in sorted(root.rglob('episode.json')):
        row = json.loads(path.read_text())
        error = row.get('error')
        label = row['status'] if not error else str(error.get('details', {}).get('type', error.get('type')))
        episodes[label] += 1
    return {'provenanceRecordsVerified': checked, 'uniqueSessions': len(seen),
            'legacyVersusLiteral': dict(fidelity), 'episodeStatusOrError': dict(episodes),
            'transportEvents': dict(transport), 'completedResponseModels': dict(models),
            'providerReportedTokens': reported_tokens, 'conservativeErrorReservationTokens': reserved_tokens,
            'interpretation': 'Error reservations are budget charges, not provider-reported token use. '
                'Legacy-versus-literal comparisons are offline environment reconstruction, not new task outcomes.',
            'trials': details}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'trials'}, indent=2))
