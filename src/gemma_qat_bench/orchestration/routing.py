"""Deterministic FAST/FULL routing policy."""

from __future__ import annotations

from .domain import RiskLevel, RoutingDecision, TaskSpec, WorkflowDepth

POLICY_VERSION = "v3-routing-policy-1"


class RoutingPolicy:
    """Preserve the conservative V2.2 FAST eligibility rule in code."""

    def decide(self, task: TaskSpec) -> RoutingDecision:
        if task.risk is RiskLevel.TRIVIAL_MECHANICAL and task.fast_eligible:
            return RoutingDecision(
                risk=task.risk,
                native_depth=WorkflowDepth.FAST,
                reason="all explicit TRIVIAL_MECHANICAL FAST eligibility checks passed",
                policy_version=POLICY_VERSION,
            )
        reason = (
            "TRIVIAL_MECHANICAL task failed one or more FAST eligibility checks"
            if task.risk is RiskLevel.TRIVIAL_MECHANICAL
            else f"{task.risk.value} tasks use FULL under the conservative V2.2 rule"
        )
        return RoutingDecision(
            risk=task.risk,
            native_depth=WorkflowDepth.FULL,
            reason=reason,
            policy_version=POLICY_VERSION,
        )
