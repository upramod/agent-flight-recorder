"""Describe interventions in frozen utility-loss pairs without causal claims."""
import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

try:
    from .extract_attacked_audits import load_attacked_cases
except ImportError:
    from extract_attacked_audits import load_attacked_cases


def analyze(archive_path):
    cases = load_attacked_cases(archive_path)
    attacked = {case['case']: case for case in cases}
    with ZipFile(archive_path) as archive:
        rows = list(csv.DictReader(io.StringIO(archive.read('summary.csv').decode())))
        by_case = {}
        for row in rows:
            modes = by_case.setdefault(row['case'], {})
            if row['mode'] in modes:
                raise ValueError('Duplicate case/mode outcome')
            modes[row['mode']] = row
        if any(set(modes) != {'baseline', 'flight-recorder'} for modes in by_case.values()):
            raise ValueError('Missing paired outcome')
        if set(by_case) != set(attacked):
            raise ValueError('Raw transcripts and summary have different case identities')
        for case, modes in by_case.items():
            for mode, row in modes.items():
                for column, endpoint in [('utility_passed', 'utility'), ('attack_success', 'security')]:
                    if int(row[column]) != int(attacked[case][mode][endpoint]):
                        raise ValueError('Summary endpoint differs from raw attacked transcript')
        lost = [case for case, modes in by_case.items()
                if modes['baseline']['utility_passed'] == '1'
                and modes['flight-recorder']['utility_passed'] == '0']
        first = Counter()
        no_intervention = reviews = blocks = failures = 0
        for case in lost:
            events = attacked[case]['events']
            denied = [e for e in events if e['assessment']['decision'] != 'Allow']
            if denied:
                first[denied[0]['tool'] + ':' + denied[0]['assessment']['decision']] += 1
            else:
                no_intervention += 1
            reviews += sum(e['assessment']['decision'] == 'Review' for e in events)
            blocks += sum(e['assessment']['decision'] == 'Block' for e in events)
            failures += sum(e['assessment']['decision'] == 'Allow' and not e['executed'] for e in events)
    return {'auditScope': 'Attacked user-task sessions only; auxiliary injection-task runs excluded.',
            'validatedPairedEndpoints': len(cases),
            'attackedProposals': sum(len(case['events']) for case in cases),
            'excludedAuxiliaryProposals': sum(len(case['auxiliaryEvents']) for case in cases),
            'utilityLostPairs': len(lost), 'firstPolicyInterventionInLostPairs': dict(first),
            'lostPairsWithoutPolicyIntervention': no_intervention,
            'reviewProposalsInLostPairs': reviews, 'blockProposalsInLostPairs': blocks,
            'allowedButNotExecutedInLostPairs': failures,
            'interpretation': 'Associations on observed trajectories, not proof of cause or estimated recovered utility.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
