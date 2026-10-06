"""Offline checks for the declared sequential reported-token soft stop."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import study_budget


class StudyBudgetTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Path(self.directory.name) / "tokens.jsonl"
        environment = patch.dict(os.environ, {"STUDY_TOKEN_LEDGER": str(self.ledger)})
        environment.start()
        self.addCleanup(environment.stop)
        token_cap = patch.object(study_budget, "TOKEN_CAP", 100)
        token_cap.start()
        self.addCleanup(token_cap.stop)

    @staticmethod
    def arguments(content="A synthetic prompt."):
        return {"model": "verified-model-snapshot", "messages": [{"role": "user", "content": content}],
                "temperature": 0, "max_completion_tokens": 16}

    def client(self, tokens=7, error=None):
        response = SimpleNamespace(usage=SimpleNamespace(total_tokens=tokens), model="verified-model-snapshot")
        original = Mock(return_value=response, side_effect=error)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=original)))
        study_budget.attach_budget(client)
        return client, original, response

    def write_records(self, records):
        self.ledger.write_text("".join(json.dumps(row) + "\n" for row in records))

    def records(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def test_successful_sequential_calls_share_reported_usage(self):
        first, _, response = self.client(tokens=7)
        second, _, _ = self.client(tokens=11)
        self.assertIs(first.chat.completions.create(**self.arguments()), response)
        second.chat.completions.create(**self.arguments())
        rows = self.records()
        self.assertEqual([row["priorReportedTokens"] for row in rows], [0, 7])
        self.assertEqual(sum(row["totalTokens"] for row in rows), 18)
        self.assertEqual([row["request"] for row in rows], [1, 2])
        self.assertTrue(all(row["status"] == "completed" for row in rows))

    def test_crossing_call_is_retained_then_next_call_is_stopped(self):
        self.write_records([{"request": 1, "status": "completed", "totalTokens": 95}])
        client, original, response = self.client(tokens=12)
        self.assertIs(client.chat.completions.create(**self.arguments()), response)
        self.assertEqual(sum(row["totalTokens"] for row in self.records()), 107)
        with self.assertRaisesRegex(RuntimeError, "budget_exhausted"):
            client.chat.completions.create(**self.arguments())
        original.assert_called_once()

    def test_exact_cap_stops_before_transport(self):
        self.write_records([{"request": 1, "status": "completed", "totalTokens": 100}])
        client, original, _ = self.client()
        with self.assertRaisesRegex(RuntimeError, "budget_exhausted"):
            client.chat.completions.create(**self.arguments())
        original.assert_not_called()

    def test_interrupted_request_prevents_new_spending(self):
        self.write_records([{"request": 1, "status": "completed", "totalTokens": 7},
                            {"request": 2, "status": "requested", "priorReportedTokens": 7}])
        client, original, _ = self.client()
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(**self.arguments())
        original.assert_not_called()

    def test_invalid_prior_usage_cannot_reduce_or_reset_the_budget(self):
        for tokens in (True, -1, 1.5, "7", None):
            with self.subTest(tokens=tokens):
                self.write_records([{"request": 1, "status": "completed", "totalTokens": tokens}])
                client, original, _ = self.client()
                with self.assertRaises(RuntimeError):
                    client.chat.completions.create(**self.arguments())
                original.assert_not_called()

    def test_invalid_usage_consumes_remaining_budget(self):
        for tokens in (True, False, -1, 1.5, "7", None):
            with self.subTest(tokens=tokens):
                self.write_records([{"request": 1, "status": "completed", "totalTokens": 7}])
                client, original, _ = self.client(tokens=tokens)
                with self.assertRaises(RuntimeError):
                    client.chat.completions.create(**self.arguments())
                rows = self.records()
                self.assertEqual(rows[-1]["status"], "error")
                self.assertGreaterEqual(sum(row["totalTokens"] for row in rows), 100)
                with self.assertRaises(RuntimeError):
                    client.chat.completions.create(**self.arguments())
                original.assert_called_once()

    def test_zero_reported_tokens_are_a_valid_nonnegative_integer(self):
        client, original, response = self.client(tokens=0)
        self.assertIs(client.chat.completions.create(**self.arguments()), response)
        self.assertEqual(self.records()[0]["totalTokens"], 0)
        self.assertEqual(self.records()[0]["status"], "completed")
        original.assert_called_once()

    def test_unicode_character_cap_is_separate_from_token_accounting(self):
        arguments = self.arguments("\U0001f600" * 10)
        prompt = json.dumps({"messages": arguments["messages"], "tools": None}, ensure_ascii=False, default=str)
        self.assertGreater(len(prompt.encode()), len(prompt))
        client, original, _ = self.client()
        with patch.object(study_budget, "PROMPT_CHARACTER_CAP", len(prompt)):
            client.chat.completions.create(**arguments)
            with self.assertRaisesRegex(RuntimeError, "prompt_character_cap"):
                client.chat.completions.create(**self.arguments("\U0001f600" * 11))
        original.assert_called_once()
        row = self.records()[0]
        self.assertEqual(row["promptCharacters"], len(prompt))
        self.assertEqual(row["promptSha256"], hashlib.sha256(prompt.encode()).hexdigest())

    def test_unknown_failure_consumes_remaining_without_logging_secret_text(self):
        secret = "synthetic-secret-do-not-store"
        self.write_records([{"request": 1, "status": "completed", "totalTokens": 7}])
        client, original, _ = self.client(error=RuntimeError("https://private.invalid/ " + secret))
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(**self.arguments(secret))
        rows = self.records()
        self.assertEqual(sum(row["totalTokens"] for row in rows), 100)
        self.assertEqual(rows[-1]["errorType"], "RuntimeError")
        self.assertNotIn(secret, self.ledger.read_text())
        self.assertNotIn("private.invalid", self.ledger.read_text())
        original.assert_called_once()

    def test_malformed_ledger_fails_before_transport(self):
        self.ledger.write_text("{incomplete-json\n")
        client, original, _ = self.client()
        with self.assertRaises((RuntimeError, ValueError)):
            client.chat.completions.create(**self.arguments())
        original.assert_not_called()

    def test_without_ledger_configuration_client_is_unchanged(self):
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=Mock())))
        original = client.chat.completions.create
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(study_budget.attach_budget(client), client)
        self.assertIs(client.chat.completions.create, original)


if __name__ == "__main__":
    unittest.main()
