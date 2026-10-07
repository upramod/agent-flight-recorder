"""Inject untrusted content into parsed scalar values, never YAML source."""
from __future__ import annotations

import yaml
from agentdojo.task_suite.task_suite import read_suite_file, validate_injections


def substitute_values(value, substitutions):
    if isinstance(value, str):
        return value.format(**substitutions)
    if isinstance(value, list):
        return [substitute_values(item, substitutions) for item in value]
    if isinstance(value, dict):
        return {key: substitute_values(item, substitutions) for key, item in value.items()}
    return value


def load_safe_environment(suite, injections):
    defaults = suite.get_injection_vector_defaults()
    validate_injections(injections, defaults)
    template = yaml.safe_load(read_suite_file(suite.name, "environment.yaml", suite.data_path))
    return suite.environment_type.model_validate(
        substitute_values(template, {**defaults, **injections})
    )
