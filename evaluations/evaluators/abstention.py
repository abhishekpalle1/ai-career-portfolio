"""Answer-versus-decline decisions and required-fact coverage."""

from __future__ import annotations

from evaluations.dataset import EvalCase
from evaluations.evaluators.text import affirmative_matches, contains_fact
from evaluations.observations import Observation


def decision_correct(case: EvalCase, obs: Observation) -> bool | None:
    """None for behaviours outside abstention accuracy (blocks, redirects, out of scope, safe)."""
    response = obs.response
    if case.expected_behavior == "ANSWER":
        return bool(response and response.grounded and not response.abstained and not obs.blocked)
    if case.expected_behavior == "DECLINE":
        if obs.blocked or response is None:
            return False
        if response.abstained:
            return True
        return not affirmative_matches(response.answer, case.forbidden_claims)
    return None


def required_facts(case: EvalCase, answer: str) -> tuple[list[str], list[str]]:
    """(found, missing) required facts."""
    found = [fact for fact in case.required_facts if contains_fact(answer, fact)]
    return found, [fact for fact in case.required_facts if fact not in found]
