"""Probe configured study models without disclosing credentials or endpoints."""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from openai import AzureOpenAI, OpenAI


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
        return AzureOpenAI(azure_endpoint=endpoint, api_key=key,
            api_version=os.getenv('AZURE_OPENAI_API_VERSION') or '2025-01-01-preview',
            timeout=60, max_retries=2)
    return OpenAI(api_key=key, timeout=60, max_retries=2)


def deployment_for(config):
    return os.getenv(config['deploymentEnv']) or ('gpt-4o-2024-08-06' if config['provider'] == 'openai' else '')


def safe_error(error):
    return {'type': type(error).__name__, 'statusCode': getattr(error, 'status_code', None),
            'code': getattr(error, 'code', None)}


def probe():
    rows = []
    for config in configured_models():
        deployment = deployment_for(config)
        row = {**config, 'deployment': deployment, 'status': 'unavailable'}
        try:
            if not deployment:
                raise ValueError('missing_deployment')
            with client_for(config) as client:
                response = client.chat.completions.create(model=deployment,
                    messages=[{'role': 'user', 'content': 'Reply READY.'}],
                    temperature=0, max_completion_tokens=16)
            row.update(status='ready', responseModel=response.model,
                       systemFingerprint=getattr(response, 'system_fingerprint', None),
                       usage=response.usage.model_dump() if response.usage else None,
                       temperature=0, targetMaxCompletionTokens=2048)
        except Exception as error:
            row['error'] = safe_error(error)
        rows.append(row)
    ready = [r for r in rows if r['status'] == 'ready']
    distinct = len({r.get('responseModel') for r in ready}) >= 2
    return {'createdAt': datetime.now(timezone.utc).isoformat(), 'models': rows,
            'twoDistinctResponseModels': distinct,
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
