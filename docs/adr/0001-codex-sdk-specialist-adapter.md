# ADR 0001: Codex Python SDK specialist adapter

- Status: accepted
- Date: 2026-08-18
- Scope: V3 specialist transport only

## Context

V3 needs coding-focused specialists with repository access, a real response boundary,
provider-level structured output where available, role-specific write isolation, and an
offline fake. The deterministic application must not depend on the provider.

At implementation time:

- the official [Codex SDK guide](https://developers.openai.com/codex/codex-sdk) described
  the Python SDK as stable, installed through `openai-codex`, backed by a pinned Codex
  runtime, and supporting read-only and workspace-write sandboxes;
- runtime inspection of `openai-codex` 0.147.0 confirmed `Thread.run(...,
  output_schema=...)`, `TurnResult.final_response`, usage metadata, and the sandbox
  presets;
- the official [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
  confirmed JSON Schema enforcement as a provider feature, while also requiring callers
  to handle refusals and incomplete responses;
- no live provider credential was available in the development environment.

## Decision

Use the optional Python Codex SDK for the production specialist adapter and keep it
behind `SpecialistClient`.

- Planner, Plan Critic, Verifier, and Reviewer use `read_only`.
- Implementer uses `workspace_write`.
- SDK approval mode is `deny_all`; V3's command broker owns verification commands.
- Each turn receives the closed artifact JSON schema through `output_schema`.
- The adapter returns `final_response` without wrapper heuristics.
- The deterministic parser validates the response again and owns artifact validity.
- Provider exceptions become typed transport failures rather than Gate verdicts.
- The base benchmark install does not gain the SDK; it is the `v3-codex` optional extra.

## Alternatives considered

### GitHub Copilot SDK

The [GitHub Copilot SDK repository](https://github.com/github/copilot-sdk) provides a
coding-agent runtime, but the inspected public surface did not provide equally clear,
confirmed schema-bound output semantics for this use. Selecting it would leave more of
the V2 malformed-artifact risk at the transport boundary.

### Direct non-interactive CLI calls

Direct process invocation can expose an output schema, but it adds process lifecycle and
event parsing to every specialist call and is less natural to fake. The Python SDK
already owns that protocol and bundles a pinned runtime.

### Provider-specific orchestration

Allowing a model framework to choose specialists, retries, or transitions would violate
the central V3 requirement. The SDK is therefore only an invocation adapter, not the
orchestrator.

## Consequences

- Offline development and tests use `ScriptedSpecialistClient` and need no credential.
- Live use requires `pip install -e ".[v3-codex]"` (or `.[dev,v3-codex]`) and a working
  Codex authentication setup.
- A live provider smoke test is optional and separately marked; deterministic gates do
  not depend on it.
- The Implementer sandbox can provide coding tools, but no model-reported command result
  is canonical. Only brokered, authorized command evidence can satisfy Gate 2.
- A future provider needs only the capability report and `SpecialistClient` contract;
  no domain or state-machine change is required.
