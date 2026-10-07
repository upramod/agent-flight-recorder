"""Post-hoc paired resampling sensitivity for the archived v2 outcomes."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from extract_attacked_audits import load_attacked_cases
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations' / 'agentdojo'))
from analyze_validation_v3 import cluster_summary


def analyze(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != '3a4e8c97a8237b8f2fa5eae08f9fc2e4188c72173ff594a58680b7b907faac81':
        raise ValueError('Wrong frozen v2 archive')
    cases = load_attacked_cases(archive)
    if len(cases) != 120:
        raise ValueError('Expected all120 frozen pairs')
    endpoints = {}
    for endpoint in ('security', 'utility'):
        rows=[]
        for case in cases:
            b,f=case['baseline'],case['flight-recorder']
            if type(b[endpoint]) is not bool or type(f[endpoint]) is not bool:
                raise ValueError('Outcome is not Boolean')
            rows.append({'pair':case['case'],'userTask':b['user_task_id'],'injectionTask':b['injection_task_id'],
                         'baseline':int(b[endpoint]),'recorder':int(f[endpoint]),
                         'difference':int(f[endpoint])-int(b[endpoint])})
        sums=(sum(r['baseline'] for r in rows),sum(r['recorder'] for r in rows))
        if sums != ((20,0) if endpoint=='security' else (61,35)):
            raise ValueError('Frozen endpoint counts differ')
        endpoints[endpoint]={'baselineSuccesses':sums[0],'recorderSuccesses':sums[1],
            'pairedRiskDifference':sum(r['difference'] for r in rows)/120,
            'pairedTable':{key:sum(str(r['recorder'])+str(r['baseline'])==key for r in rows) for key in ('00','01','10','11')},
            'resampling':{key:cluster_summary(rows,key,'v2-posthoc-'+endpoint,20000,20261007) for key in ('pair','injectionTask','userTask')}}
    return {'sourceRun':35180860582,'sourceArchiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
        'analysisDateUtc':'2026-10-07','methodSelection':'Post-hoc. V2 requested an appropriate paired-effect interval but did not specify a construction. This does not retroactively preregister the method.',
        'method':'20000 percentile paired resamples, seed20261007, type7 quantiles; preserve paired arms. Pair resampling is nominal under independent-pair sampling. Goal and user cluster resampling are separate sensitivity analyses, not joint dependence correction. Unequal cluster sizes retain pair-weighted ratios.',
        'inferenceLimit':'Finite deterministic task selection; reused components; small14-goal cluster set. No population coverage or cross-model generalization claim.',
        'endpoints':endpoints}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=analyze(args.archive);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
