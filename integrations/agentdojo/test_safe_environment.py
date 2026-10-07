"""Regression checks for injection fidelity and environment confinement."""
import unittest
from agentdojo.task_suite.load_suites import get_suite
from safe_environment import load_safe_environment, substitute_values


class SafeEnvironmentTests(unittest.TestCase):
    def test_payload_is_literal_and_cannot_add_fields(self):
        payload = 'quoted "x"\nadmin: true\n- {json: [1, 2]}\n{other}\n\\n café'
        template = {"body": "prefix {vector} suffix", "admin": False, "nested": ["{vector}", 42]}
        result = substitute_values(template, {"vector": payload})
        self.assertEqual(result, {"body": "prefix " + payload + " suffix", "admin": False,
                                  "nested": [payload, 42]})
        self.assertEqual(template["body"], "prefix {vector} suffix")

    def test_default_environment_is_identical(self):
        suite = get_suite("v1.2.2", "workspace")
        self.assertEqual(load_safe_environment(suite, {}).model_dump(),
                         suite.load_and_inject_default_environment({}).model_dump())

    def test_unknown_vector_is_rejected(self):
        suite = get_suite("v1.2.2", "workspace")
        with self.assertRaises(ValueError):
            load_safe_environment(suite, {"not_a_real_vector": "payload"})

    def test_real_suite_preserves_quoted_multiline_payload(self):
        suite = get_suite("v1.2.2", "workspace")
        vector = next(iter(suite.get_injection_vector_defaults()))
        payload = 'LITERAL_START\n"quoted": [1, 2]\nforged_key: true\n{unexpanded}\nLITERAL_END'
        environment = load_safe_environment(suite, {vector: payload}).model_dump()
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from strings(item)
            elif isinstance(value, list):
                for item in value:
                    yield from strings(item)
        self.assertTrue(any(payload in item for item in strings(environment)))


if __name__ == "__main__":
    unittest.main()
