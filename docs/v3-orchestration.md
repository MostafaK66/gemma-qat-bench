# V3 deterministic coding orchestration

V3 is an SDK-backed coding workflow in which ordinary Python code owns routing, state,
budgets, artifact validity, command execution, evidence freshness, persistence, and
escalation. Specialists inspect or edit the repository within role boundaries, but they
never choose the next step or own authoritative command state.

## Architecture

| Component | Responsibility |
| --- | --- |
| `domain` | Immutable IDs, enums, commands, fingerprints, budgets, failures, and results |
| `routing` | Conservative V2.2 FAST/FULL decision |
| `state_machine` | Explicit allowed transition graph and FAST-to-FULL escalation |
| `artifacts` | Closed JSON schemas, typed artifacts, and strict parsing |
| `specialists` | Provider-neutral requests/results and scripted fake |
| `codex_adapter` | Optional schema-bound Codex SDK invocation and sandbox selection |
| `authorization` | Human decision port for commands, Git, and degraded mode |
| `commands` | Shell-free exact-argv execution through an injected runner |
| `evidence` | One canonical, fingerprint-bound ledger and safe Verifier projection |
| `scope` | Git task-start identities and actual changed-path delta |
| `fingerprint` | `implementation-fingerprint-v1` manifest and freshness check |
| `persistence` | Atomic mode-0600 JSON checkpoints with parsed artifacts, budgets, and evidence |
| `runtime` | Runtime state plus checkpoint encoding, restoration, and completion projection |
| `events` | Structured, sequence-numbered, secret-minimizing events |
| `engine` | Application coordinator that consumes policies and chooses every transition |

Dependencies point inward: the engine uses typed ports, while provider, process, Git,
clock, event, and storage effects are replaceable. The benchmark runner remains
unchanged.

## Workflows

FULL follows:

```text
INTAKE -> PLANNING -> PLAN_CRITIQUE -> GATE_1
       -> IMPLEMENTATION -> COMMAND_VERIFICATION -> GATE_2
       -> REVIEW -> GATE_3 -> COMPLETE
```

FAST follows:

```text
INTAKE -> IMPLEMENTATION -> COMMAND_VERIFICATION -> GATE_2 -> COMPLETE
```

Gate rejection, failed required commands, review findings, bounded schema repair,
authorization denial, environment failure, scope violation, fingerprint drift, and
budget exhaustion are explicit code paths. FAST Gate 2 rejection is recorded as
`FAST_ESCALATED_TO_FULL`, then enters PLANNING; prior FAST work is evidence, not an
approved plan.

`CHANGE_COMPLETE` means only that the coding workflow completed. It does not authorize
Git stage, commit, push, merge, deployment, or any other side effect.

## Routing

`v3-routing-policy-1` preserves the conservative V2.2 rule:

- `TRIVIAL_MECHANICAL` may be FAST only when `fast_eligible` is explicitly true;
- `LOW_RISK`, `STANDARD`, and `HIGH_RISK` always start FULL;
- a `TRIVIAL_MECHANICAL` task with any failed eligibility check starts FULL.

The task author is responsible for making `fast_eligible` true only when the outcome is
exact, evidence is unique, scope is no more than three cohesive files including paired
tests/docs, no public/API/config/architecture/security/data/dependency decision exists,
and focused deterministic verification is available.

## Specialist artifacts

Specialists return exactly one JSON object. Whitespace is allowed around it; prose,
Markdown fences, epilogues, and a second root value are not. Schemas reject unknown
fields. Local validation distinguishes:

1. provider transport success;
2. structurally valid specialist artifact;
3. semantic Gate verdict.

The Verifier assessment list must contain each current required `command_id` exactly
once, use exactly the four allowed assessment fields, and never reconstruct canonical
ledger fields. A `PASSED` artifact with an insufficient assessment or blocking finding
is inconsistent and rejected.

## Commands, evidence, and authorization

Task files authorize the possible command set, but execution still requires the
`--authorize-commands` boundary. Commands are argv arrays, never shell strings. Working
directories must remain inside the repository. Every task must declare at least one
`required` command; a task whose command set is empty or entirely optional is rejected
at validation time so Gate 2 can never pass on an empty evidence ledger.

`output_handling` is `STATUS_ONLY` by default. Use `EXCERPT` only when stdout/stderr is
permitted evidence; excerpts are bounded. Environment/spawn failures are distinct from
nonzero product/quality results. A nonzero required result directly consumes an
implementation revision instead of trusting model self-report.

The canonical ledger binds task ID, plan/intake reference, implementation and
verification iterations, command-set source, and implementation fingerprint. Verifier
views contain only command identity, qualitative status, permitted material, and the
truncation flag. Specialist outputs cannot overwrite the ledger.

## Fingerprint and scope algorithm

`implementation-fingerprint-v1` is SHA-256 over UTF-8 records joined by one LF with no
trailing LF:

```text
<state>\t<normalized_repository_relative_path>\t<content_identity>
```

Paths use `/`, are repository-relative, unique, and lexically sorted. Present content
identity comes from `git hash-object --no-filters -- <path>`; deleted paths use
`DELETED`. The scope is the union of the authorized task scope and every final file whose
identity differs from the task-start Git workspace identity, including authorized
untracked files and a pre-existing modified file changed again.

An actual delta outside authorized scope is included in the captured fingerprint and
then raises `SCOPE_VIOLATION`; it is never silently omitted. Scope or content drift
before Verifier, schema repair, or Reviewer invalidates evidence and fails closed.

## Budgets and failure behavior

| Budget | Default |
| --- | ---: |
| Plan revisions | 2 |
| Shared implementation revisions | 2 |
| Verifier schema-only repair | 1 |
| Reviewer-driven repairs | 2 (also consumes shared implementation budget) |
| Provider invocation retry | 1 |

Every consumption emits an event and is persisted. There is no recursive or hidden
retry. Typed failures include profile unavailable, invocation failure, malformed
artifact, loop limit, tool capability failure, environment/tooling failure, quality
failure, scope violation, fingerprint drift, budget exhaustion, and authorization
denial.

## Persistence and resume

The default CLI saves `$XDG_STATE_HOME/gemma-qat-bench/v3/<task-id>.json` (or
`~/.local/state/gemma-qat-bench/v3/...` when XDG state is unset) atomically with mode
0600. Keeping checkpoints outside the specialist workspace prevents a workspace-write
Implementer from modifying orchestration authority. `--state-dir` can override this;
choose a similarly protected location. V3 persists parsed artifacts rather than blind
raw provider output, bounded permitted command material, validation defects, Gate
results, budgets, scope baseline, fingerprint, escalation, and structured event history.

`resume` loads and revalidates stored artifacts. Read-only planning/review boundaries can
be repeated. Verification commands can be re-authorized and rerun after interruption.
Before any interrupted Implementer is replayed, V3 compares the persisted pre-invocation
fingerprint; changed content escalates as ambiguous human intent instead of risking a
second write.

## Installation and CLI

Deterministic scripted use needs the normal development environment:

```bash
python -m pip install -e ".[dev]"
```

Codex-backed use adds the optional SDK:

```bash
python -m pip install -e ".[dev,v3-codex]"
```

Copy `configs/v3-task.example.json`, replace the absolute repository path, and make the
authorized scope and exact commands task-specific. Start a live Codex workflow:

```bash
gemma-qat-orchestrate run task.json --provider codex --authorize-commands
```

Without `--authorize-commands`, the workflow records `AUTHORIZATION_REQUIRED`, pauses in
`WAITING_AUTHORIZATION`, and executes nothing. Resume with the flag after reviewing the
exact task command set, or inspect without side effects:

```bash
gemma-qat-orchestrate resume task.json --provider codex --authorize-commands
gemma-qat-orchestrate inspect EXAMPLE-001
```

The equivalent module entry point is:

```bash
python -m gemma_qat_bench.orchestration --help
```

For deterministic/offline development, pass `--provider scripted --responses
responses.json`. The response file is an ordered array:

```json
[
  {"role": "IMPLEMENTER", "response": {"task_id": "..."}},
  {"role": "VERIFIER", "response": {"task_id": "..."}}
]
```

Each `response` must contain the complete artifact schema for that role. The scripted
client deliberately fails when invocation order differs, making workflow tests sensitive
to accidental transition changes.

## End-to-end examples

### FAST

Use `risk: "TRIVIAL_MECHANICAL"` and `fast_eligible: true` for an exact, uniquely
determined one-file edit. Provide the paired focused test as `CMD-001` and include every
authorized product/test/doc path in `fingerprint_scope`. Expected Gates are Gate 2
`PASSED`, Gate 1 and Gate 3 not applicable, then `CHANGE_COMPLETE`.

### FULL

Use `risk: "STANDARD"` and `fast_eligible: false` for a normal feature. The application
invokes Planner and Plan Critic, requires Gate 1 approval, then Implementer, brokered
commands, Verifier, and Reviewer. A Reviewer change request returns to Implementer and
must pass fresh commands and Gate 2 before review repeats.

## Development and tests

All deterministic V3 tests are offline:

```bash
python -m pytest -q tests/v3
python -m pytest -q
ruff check .
ruff format --check .
python -m mypy
```

The focused suite covers domain invariants, routing, every valid and invalid transition,
artifact defect codes, golden fingerprint vectors, evidence integrity, authorization,
environment/product failure classification, retry exhaustion, FAST/FULL workflows,
Gate repairs, scope drift, fingerprint drift, persistence, resume, CLI, and the SDK
capability seam.
