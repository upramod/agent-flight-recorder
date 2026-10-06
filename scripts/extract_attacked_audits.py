"""Separate attacked user-task audits from AgentDojo's auxiliary task runs.

The archived runner writes both runs to one JSONL file. A file is therefore not
a trajectory. This extractor validates the two session boundaries against both
raw transcripts before exposing only the attacked user-task session.
"""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile


def _tool_results(transcript):
    return [message for message in transcript['messages'] if message['role'] == 'tool']


def split_sessions(events, auxiliary, attacked):
    """Validate the archived auxiliary-then-attacked layout, then split it.

    This intentionally fails on a changed layout instead of silently selecting
    the last session. The runner's two raw transcripts establish the expected
    order, tool sequence, result status, and session start times.
    """
    if not str(auxiliary['user_task_id']).startswith('injection_task_'):
        raise ValueError('Auxiliary transcript is not an injection-task run')
    if auxiliary['injection_task_id'] is not None or auxiliary['attack_type'] is not None:
        raise ValueError('Auxiliary transcript unexpectedly contains an attack')
    if not str(attacked['user_task_id']).startswith('user_task_'):
        raise ValueError('Attacked transcript is not a user-task run')
    if attacked['injection_task_id'] != auxiliary['user_task_id'] or not attacked['attack_type']:
        raise ValueError('Transcript injection identities do not match')
    starts = [datetime.fromisoformat(t['evaluation_timestamp']) for t in (auxiliary, attacked)]
    if starts[0] > starts[1]:
        raise ValueError('Auxiliary transcript follows attacked transcript')
    groups = []
    seen = set()
    for event in events:
        if 'action' not in event or 'assessment' not in event:
            raise ValueError('Incomplete policy event')
        session = event['action']['sessionId']
        if not groups or groups[-1][0]['action']['sessionId'] != session:
            if session in seen:
                raise ValueError('Interleaved policy sessions')
            seen.add(session)
            groups.append([])
        groups[-1].append(event)
    if len(groups) != 2:
        raise ValueError(f'Expected two distinct policy sessions, found {len(groups)}')
    for index, (group, transcript) in enumerate(zip(groups, (auxiliary, attacked))):
        results = _tool_results(transcript)
        expected = [message['tool_call']['function'] for message in results]
        if [event['tool'] for event in group] != expected:
            raise ValueError('Policy session does not match raw transcript tool sequence')
        executed = 0
        previous_time = None
        for event, result in zip(group, results):
            timestamp = datetime.fromisoformat(event['action']['timestamp']).replace(tzinfo=None)
            if timestamp < starts[index] or (previous_time is not None and timestamp < previous_time):
                raise ValueError('Policy timestamps disagree with transcript ordering')
            # Transcript start times have only whole-second precision.
            if index == 0 and timestamp.replace(microsecond=0) > starts[1]:
                raise ValueError('Auxiliary policy event follows attacked run start')
            previous_time = timestamp
            if event['assessment']['historyLength'] != executed:
                raise ValueError('Policy session history is not isolated successful execution history')
            if event['executed'] is not (result.get('error') is None):
                raise ValueError('Policy execution status disagrees with raw transcript')
            executed += event['executed']
    return groups[0], groups[1]


def load_attacked_cases(archive_path):
    """Return validated main-session events and paired raw endpoint results."""
    cases = []
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        audit_names = sorted(name for name in names if name.endswith('/flight-recorder/flight-recorder-policy.jsonl'))
        if not audit_names:
            raise ValueError('No policy audits found')
        for audit_name in audit_names:
            case = audit_name.split('/')[-3]
            prefix = audit_name.rsplit('/', 1)[0] + '/'
            transcripts = [json.loads(archive.read(name)) for name in names
                           if name.startswith(prefix) and name.endswith('.json')]
            main = [t for t in transcripts if str(t.get('user_task_id')).startswith('user_task_')]
            aux = [t for t in transcripts if str(t.get('user_task_id')).startswith('injection_task_')]
            if len(main) != 1 or len(aux) != 1 or len(transcripts) != 2:
                raise ValueError(f'{case}: expected exactly one attacked and one auxiliary transcript')
            baseline_names = [name for name in names if name.startswith(f'run/{case}/baseline/')
                              and '/user_task_' in name and name.endswith('.json')]
            if len(baseline_names) != 1:
                raise ValueError(f'{case}: expected one paired baseline transcript')
            baseline = json.loads(archive.read(baseline_names[0]))
            for field in ('user_task_id', 'injection_task_id', 'attack_type', 'benchmark_version', 'suite_name', 'injections'):
                if baseline[field] != main[0][field]:
                    raise ValueError(f'{case}: paired raw transcripts differ in {field}')
            for transcript in (baseline, main[0]):
                if transcript['error'] is not None:
                    raise ValueError(f'{case}: raw endpoint has a trajectory error')
                if any(type(transcript[field]) is not bool for field in ('utility', 'security')):
                    raise ValueError(f'{case}: raw endpoint is not boolean')
            events = [json.loads(line) for line in archive.read(audit_name).decode().splitlines() if line]
            auxiliary_events, attacked_events = split_sessions(events, aux[0], main[0])
            cases.append({'case': case, 'events': attacked_events, 'auxiliaryEvents': auxiliary_events,
                          'baseline': baseline, 'flight-recorder': main[0]})
    return cases


def extract(archive_path, output_root):
    cases = load_attacked_cases(archive_path)
    counts = Counter()
    for case in cases:
        destination = output_root / case['case'] / 'flight-recorder-policy.jsonl'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(''.join(json.dumps(event, separators=(',', ':')) + '\n'
                                       for event in case['events']))
        counts['attackedProposals'] += len(case['events'])
        counts['excludedAuxiliaryProposals'] += len(case['auxiliaryEvents'])
    return {'attackedTrajectories': len(cases), **dict(counts)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.archive, args.output_root), indent=2))
