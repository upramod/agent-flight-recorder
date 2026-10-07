"""Sequential per-shard inference ledger shared by target and attacker calls."""
import hashlib
import json
import os
import time
from pathlib import Path

TOKEN_CAP = 3_000_000
PROMPT_CHARACTER_CAP = 500_000


def attach_budget(client):
    ledger_name = os.getenv('STUDY_TOKEN_LEDGER')
    if not ledger_name:
        return client
    ledger = Path(ledger_name)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    transport = client.chat.completions.create
    recovery = os.getenv('STUDY_RATE_LIMIT_RECOVERY') == '1'

    def original(**kwargs):
        if not recovery:
            return transport(**kwargs)
        transport_log = ledger.with_name(ledger.name + '.transport.jsonl')
        for attempt in range(1, 7):
            time.sleep(1)
            event = {'logicalLedgerRequest': len(ledger.read_text().splitlines()),
                     'physicalAttempt': attempt, 'status': 'requested'}
            with transport_log.open('a') as stream:
                stream.write(json.dumps(event) + '\n')
            try:
                response = transport(**kwargs)
                event.update(status='completed', responseModel=response.model)
                return response
            except Exception as error:
                limited = getattr(error, 'status_code', None) == 429
                event.update(status='rate_limited' if limited else 'error', errorType=type(error).__name__)
                if not limited or attempt == 6:
                    raise
            finally:
                with transport_log.open('a') as stream:
                    stream.write(json.dumps(event) + '\n')
            time.sleep(60)


    def create(**kwargs):
        records = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
        if any(row.get('status') == 'requested' for row in records):
            raise RuntimeError('pending_request_usage_unknown')
        if any(type(row.get('totalTokens')) is not int or row['totalTokens'] < 0 for row in records):
            raise RuntimeError('invalid_budget_ledger')
        used = sum(row['totalTokens'] for row in records)
        if used >= TOKEN_CAP:
            raise RuntimeError('shard_token_budget_exhausted')
        prompt = json.dumps({'messages': kwargs.get('messages'), 'tools': kwargs.get('tools')}, ensure_ascii=False, default=str)
        if len(prompt) > PROMPT_CHARACTER_CAP:
            raise RuntimeError('request_prompt_character_cap_exceeded')
        row = {'request': len(records) + 1, 'model': kwargs.get('model'),
               'priorReportedTokens': used, 'promptCharacters': len(prompt),
               'promptSha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'temperature': kwargs.get('temperature'),
               'maxCompletionTokens': kwargs.get('max_completion_tokens'),
               'status': 'requested', 'transportRetries': 0}
        with ledger.open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        try:
            response = original(**kwargs)
            usage = getattr(response, 'usage', None)
            if usage is None or type(usage.total_tokens) is not int or usage.total_tokens < 0:
                raise RuntimeError('missing_usage_budget_cannot_continue')
            row.update(status='completed', totalTokens=usage.total_tokens, responseModel=response.model)
            return response
        except Exception as error:
            # Unknown usage conservatively consumes the remaining shard budget.
            row.update(status='error', errorType=type(error).__name__,
                       totalTokens=0 if recovery and getattr(error, 'status_code', None) == 429 else max(0, TOKEN_CAP-used))
            raise
        finally:
            records.append(row)
            replacement = ledger.with_name(ledger.name + '.pending')
            replacement.write_text(''.join(json.dumps(item) + '\n' for item in records))
            os.replace(replacement, ledger)
    client.chat.completions.create = create
    return client
