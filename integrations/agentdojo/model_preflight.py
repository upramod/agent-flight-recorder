"""Probe configured study models without disclosing credentials or endpoints."""
from __future__ import annotations
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from openai import AzureOpenAI, OpenAI
from study_budget import attach_budget


def configured_models():
    primary = {'slot': 'model-a', 'provider': 'azure', 'deploymentEnv': 'AZURE_OPENAI_DEPLOYMENT',
               'endpointEnv': 'AZURE_OPENAI_ENDPOINT', 'keyEnv': 'AZURE_OPENAI_API_KEY'}
    candidates = [primary]
    if os.getenv('AZURE_OPENAI_SECONDARY_DEPLOYMENT'):
        candidates.append({'slot': 'model-b', 'provider': 'azure',
            'deploymentEnv': 'AZURE_OPENAI_SECONDARY_DEPLOYMENT',
            'endpointEnv': 'AZURE_OPENAI_SECONDARY_ENDPOINT' if os.getenv('AZURE_OPENAI_SECONDARY_ENDPOINT') else 'AZURE_OPENAI_ENDPOINT',
            'keyEnv': 'AZURE_OPENAI_SECONDARY_API_KEY' if os.getenv('AZURE_OPENAI_SECONDARY_API_KEY') else 'AZURE_OPENAI_API_KEY'})
    elif os.getenv('OPENAI_API_KEY'):
        candidates.append({'slot': 'model-b', 'provider': 'openai', 'deploymentEnv': 'OPENAI_SECONDARY_MODEL', 'keyEnv': 'OPENAI_API_KEY'})
    return candidates


def client_for(config):
    key = os.getenv(config['keyEnv'])
    if not key:
        raise ValueError('missing_credential')
    if config['provider'] == 'azure':
        endpoint = os.getenv(config['endpointEnv'])
        if not endpoint:
            raise ValueError('missing_endpoint')
        return attach_budget(AzureOpenAI(azure_endpoint=endpoint, api_key=key,
            api_version=os.getenv('AZURE_OPENAI_API_VERSION') or '2025-01-01-preview',
            timeout=60, max_retries=0))
    return attach_budget(OpenAI(api_key=key, timeout=60, max_retries=0))


def deployment_for(config):
    return config.get('deployment') or os.getenv(config.get('deploymentEnv', '')) or ('gpt-4o-2024-08-06' if config['provider'] == 'openai' else '')


def safe_error(error):
    code = getattr(error, 'code', None)
    status = getattr(error, 'status_code', None)
    return {'type': type(error).__name__, 'statusCode': status if type(status) is int else None,
            'code': code if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', code) else None}


def probe_one(config):
    deployment = deployment_for(config)
    row = {**config, 'deployment': deployment, 'status': 'unavailable'}
    try:
        if not deployment:
            raise ValueError('missing_deployment')
        with client_for(config) as client:
            response = client.chat.completions.create(model=deployment,
                messages=[{'role': 'user', 'content': 'Reply READY.'}],
                temperature=0, max_completion_tokens=16)
        if not isinstance(response.model, str) or not response.model.strip():
            raise ValueError('missing_response_model')
        row.update(status='ready', responseModel=response.model,
                   systemFingerprint=getattr(response, 'system_fingerprint', None),
                   usage=response.usage.model_dump() if response.usage else None,
                   temperature=0, targetMaxCompletionTokens=2048)
    except Exception as error:
        row['error'] = safe_error(error)
    return row


def probe():
    rows = [probe_one(config) for config in configured_models()]
    discovery = {'status': 'not_needed'}
    if len({row.get('responseModel') for row in rows if row['status'] == 'ready'}) < 2:
        discovery = {'status': 'unavailable', 'attempts': []}
        try:
            endpoint = os.environ['AZURE_OPENAI_ENDPOINT'].rstrip('/')
            with OpenAI(base_url=endpoint + '/openai/v1/', api_key=os.environ['AZURE_OPENAI_API_KEY'], timeout=30, max_retries=0) as client:
                ids = sorted({model.id for model in client.models.list()})
            discovery.update(status='listed', modelIds=ids)
            priority = ['gpt-4o', 'gpt-4.1', 'gpt-4o-mini']
            primary_model = next((r.get('responseModel') for r in rows if r['slot'] == 'model-a'), '')
            candidates = [name for family in priority for name in ids
                          if (name == family or name.startswith(family + '-20')) and name != primary_model]
            for name in candidates[:2]:
                candidate = probe_one({'slot': 'model-b', 'provider': 'azure', 'deployment': name,
                    'endpointEnv': 'AZURE_OPENAI_ENDPOINT', 'keyEnv': 'AZURE_OPENAI_API_KEY'})
                discovery['attempts'].append(candidate)
                if candidate['status'] == 'ready' and candidate['responseModel'] != primary_model:
                    rows = [r for r in rows if r['slot'] != 'model-b'] + [candidate]
                    break
        except Exception as error:
            discovery['error'] = safe_error(error)
    ready = [r for r in rows if r['status'] == 'ready']
    distinct = len({r.get('responseModel') for r in ready}) >= 2
    return {'createdAt': datetime.now(timezone.utc).isoformat(), 'models': rows,
            'twoDistinctResponseModels': distinct, 'azureModelDiscovery': discovery,
            'missingSecondModel': not any(r['slot'] == 'model-b' and r['status'] == 'ready' for r in rows),
            'identityLimit': 'API response model identifier verified; immutable provider snapshot only if the returned identifier includes one.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    if not any(r['slot'] == 'model-a' and r['status'] == 'ready' for r in result['models']):
        raise SystemExit(1)
