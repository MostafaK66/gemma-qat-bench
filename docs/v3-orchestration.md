# V3 deterministic coding orchestration

V3 accepts a natural-language coding request, derives a complete internal task
specification from repository evidence, and then runs the existing deterministic coding
workflow. Ordinary Python—not a model—owns routing, state, budgets, artifact validity,
command execution, evidence freshness, persistence, and escalation.

## Quick start: describe the task

Install the optional Codex SDK adapter and run the command from anywhere inside the Git
repository:

```bash
python -m pip install -e ".[dev,v3-codex]"
gemma-qat-orchestrate run --description "Improve the CLI error message for an invalid task file."
```

The description is the only normal semantic input. V3 automatically:

- discovers the actual Git repository root;
- generates a human-readable task ID;
- derives acceptance criteria from the request and repository;
- validates semantic risk signals and selects conservative FAST/FULL routing;
- compiles a narrow repository-relative fingerprint scope;
- derives focused shell-free verification commands;
- assigns deterministic command IDs such as `CMD-001`; and
- stores the complete validated task specification for later resume.

Before command execution, V3 displays the generated task summary and exact argv arrays.
In an interactive terminal it asks once whether to authorize the complete displayed
command set. Pressing Enter or answering anything other than `y`/`yes` denies it.
The analyzer does not authorize commands, and the command broker remains the execution
authority.

Use `--authorize-commands` only when the caller has already reviewed and intends to
authorize the exact generated set:

```bash
gemma-qat-orchestrate run \
  --description "Improve the CLI error message for an invalid task file." \
  --authorize-commands
```

`--non-interactive` disables prompts. Without `--authorize-commands`, the workflow
pauses in `WAITING_AUTHORIZATION` and executes no generated command.

## stdin and terminal/agent callers

stdin uses the same intake and compiler; callers never need to construct internal JSON.
Piped stdin is normally non-interactive: omit authorization to pause for review and
resume later, or add `--authorize-commands` only when the caller intentionally
pre-authorizes the generated command set.

Linux/macOS:

```bash
printf '%s\n' 'Improve the CLI error message for an invalid task file.' \
  | gemma-qat-orchestrate run --stdin
```

Windows PowerShell:

```powershell
'Improve the CLI error message for an invalid task file.' |
    gemma-qat-orchestrate run --stdin
```

The concise human summary and authorization prompt are written to stderr. The final
result is JSON on stdout, which keeps pipelines machine-readable. Exit code `0` means
`CHANGE_COMPLETE`, `1` means invalid local input/configuration, and `2` means the
workflow paused, escalated, or needs intake clarification.

## Repository selection and ambiguity

By default, V3 runs `git rev-parse --show-toplevel` from the current working directory
and fails if it cannot establish an actual Git root. An advanced caller can select the
repository explicitly:

```bash
gemma-qat-orchestrate run \
  --description "Update the focused CLI behavior." \
  --repository-root /absolute/path/to/repository
```

The override is still resolved and checked as a Git repository; it is not permission to
operate on an arbitrary or silently different directory.

Ordinary engineering investigation remains automatic. If repository evidence cannot
resolve a consequential product decision, intake returns
`CLARIFICATION_REQUIRED` with only the missing semantic question. Supply the answer
and rerun the same description:

```bash
gemma-qat-orchestrate run \
  --description "Improve invalid-input behavior." \
  --clarification "Preserve exit code 2 for compatibility."
```

`--clarification` may be repeated. The read-only analyzer incorporates the answer and
the deterministic compiler continues normally; the user is never sent to the explicit
task JSON format merely to answer one question.

## Intake architecture

The convenience layer remains outside the engine:

```text
NaturalLanguageTaskRequest
        -> read-only TaskIntentAnalyzer
        -> strict TaskIntakeAnalysis parser
        -> deterministic TaskCompiler
        -> complete TaskSpec
        -> existing Orchestrator
```

| Component | Responsibility |
| --- | --- |
| `intake_domain` | Typed request, semantic facts, analyzer protocol, and compiled result |
| `intake_artifacts` | Closed provider schema and exact-one-object local parser |
| `intake` | Git-root discovery, task IDs, risk/scope/command policy, and compiler |
| `codex_adapter` | Shared schema-bound SDK transport; intake always uses read-only sandbox |
| `cli` | Natural-language/stdin selection, transparent summary, and advanced JSON path |
| `domain` | Strict complete `TaskSpec`, IDs, commands, fingerprints, failures, and results |
| `routing` | Conservative V2.2 FAST/FULL decision |
| `state_machine` | Explicit transition graph and FAST-to-FULL escalation |
| `artifacts` | Closed specialist schemas, typed artifacts, and strict parsing |
| `specialists` | Provider-neutral specialist requests/results and scripted fake |
| `authorization` | Human decisions for commands, Git, and degraded mode |
| `commands` | Shell-free exact-argv execution through an injected runner |
| `evidence` | One canonical fingerprint-bound ledger and safe Verifier projection |
| `scope` | Git task-start identities and actual changed-path delta |
| `fingerprint` | `implementation-fingerprint-v1` capture and freshness checks |
| `persistence` / `runtime` | Protected checkpoint encoding, restoration, and completion |
| `engine` | Application coordinator that chooses every workflow transition |

The analyzer may inspect instructions, source, tests, configuration, and documentation,
but cannot edit the repository. It returns exactly one schema-bound object containing
normalized description, acceptance criteria, candidate scope, command proposals, risk
facts, genuine ambiguities, assumptions, and repository evidence. It does not generate
task IDs, command IDs, risk enums, FAST/FULL decisions, or authorization.

Provider structured output is only an outer guard. Local parsing rejects prose wrappers,
multiple roots, duplicate fields, missing fields, unknown fields, and incorrect types
before compilation. Excessive JSON nesting is reported as an artifact defect rather
than escaping the boundary as a runtime recursion failure.

## Deterministic compilation and routing

The compiler validates repository-relative scope, rejects traversal, absolute paths,
wildcards, Git metadata, directories, and duplicates, and never grants a whole-repository
wildcard. Nonexistent narrow file paths are allowed because a task may legitimately
create a new file. Actual changed paths are still detected later by the existing Git
scope protection.

`IntakeRiskPolicy` maps validated facts to the existing risk enum:

- FAST is possible only when the outcome is exact, repository evidence is unique, scope
  is cohesive and no more than three files, focused verification exists, and there is
  no semantic, security, data, dependency, operational, compatibility, or uncertainty
  signal;
- security/privacy, data, or operational impact is `HIGH_RISK` and therefore FULL;
- public-contract, configuration, architecture/ownership, dependency, compatibility,
  or uncertainty signals are at least `STANDARD` and therefore FULL;
- an exact and uniquely evidenced task that misses another FAST condition is
  `LOW_RISK` and therefore FULL; and
- all remaining uncertainty is `STANDARD`/FULL.

The existing `RoutingPolicy` remains the final routing authority:
`TRIVIAL_MECHANICAL` plus internally generated `fast_eligible=true` selects FAST;
every other result selects FULL.

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
budget exhaustion remain explicit code paths. A FAST Gate 2 rejection records
`FAST_ESCALATED_TO_FULL` and enters planning; prior FAST work is evidence, not an
approved plan.

## Generated commands, evidence, and authorization

The analyzer proposes task-specific commands from repository tooling and expected scope.
The compiler:

- rejects empty/control-character argv and shell control operators;
- rejects known shell, destructive, privilege, shutdown, and direct network executables;
- rejects inline Python `-c` execution and non-read-only Git operations;
- normalizes and validates cwd inside the repository;
- assigns unique sequential IDs;
- marks every generated command required; and
- uses `STATUS_ONLY` output handling.

Every compiled or explicit `TaskSpec` must contain at least one command with
`required=true`; the CLI rejects commandless and all-optional task files with exit 1.
These checks do not replace human authorization. Exact argv arrays are never passed
through `shell=True`, and only the broker records canonical results. Command output is
decoded as UTF-8 with replacement for undecodable bytes so binary output becomes
bounded evidence instead of crashing a resumable workflow.

The ledger binds task ID, plan/intake reference, implementation and verification
iterations, command-set source, and implementation fingerprint. Verifier views contain
only command identity, qualitative status, permitted material, and truncation state.
Specialist output cannot overwrite the ledger or fabricate command success.

## Fingerprint and scope behavior

`implementation-fingerprint-v1` is SHA-256 over UTF-8 records joined by one LF with no
trailing LF:

```text
<state>\t<normalized_repository_relative_path>\t<content_identity>
```

Paths are stored in canonical `/` form, are repository-relative, unique, and sorted.
Present identities come
from `git hash-object --no-filters -- <path>`; deleted paths use `DELETED`. The
captured scope is the union of compiled/explicit scope and every final path whose
identity differs from the task-start workspace.

An actual delta outside authorized scope is included in the fingerprint and then raises
`SCOPE_VIOLATION`; it is never silently omitted or authorized. If legitimate work
requires another file, stop and re-run intake with the expanded semantic requirement or
use a reviewed explicit task specification. Fingerprint currency is checked immediately
before command execution, including an authorized resume from
`WAITING_AUTHORIZATION`; changed content is never executed under stale evidence.
Scope/content drift before Verifier, schema repair, or Reviewer also invalidates
evidence and fails closed. Missing Git tooling, launch failures, and undecodable Git
path output are normalized into deterministic environment/tooling failures.

## Persistence, inspect, and task-ID resume

The default checkpoint is
`$XDG_STATE_HOME/gemma-qat-bench/v3/<task-id>.json`, or
`~/.local/state/gemma-qat-bench/v3/<task-id>.json` when XDG state is unset. Files are
written atomically with mode 0600 inside a mode-0700 state directory. `--state-dir`
overrides this; use a location the workspace-writing Implementer cannot modify.

Checkpoint schema v2 stores the complete validated `TaskSpec`, parsed specialist
artifacts, budgets, permitted command evidence, Gates, scope baseline, fingerprint,
escalation, and ordered events. The protected specification is revalidated on load and
must match on resume.

The generated task ID is printed in both the summary and final JSON. Resume without
recreating task JSON:

```bash
gemma-qat-orchestrate resume V3-20260818-180501-A1B2C3 --authorize-commands
gemma-qat-orchestrate inspect V3-20260818-180501-A1B2C3
```

An interactive task-ID resume can omit `--authorize-commands` and answer the same
one-shot exact-command confirmation. The explicit flag remains useful for reviewed
automation.

Use the same `--state-dir` on run, resume, and inspect when overriding the default.
Legacy schema-v1 checkpoints remain readable; because they predate stored task
specifications, resume them with the original task JSON path.

## Advanced: explicit task specification JSON

The original strict JSON workflow remains supported for deterministic replay, CI,
debugging, tests, and externally prepared specifications. Copy
`configs/v3-task.example.json`, replace its absolute repository root, and make its
scope and command set task-specific:

```bash
gemma-qat-orchestrate run configs/v3-task.example.json \
  --provider codex \
  --authorize-commands
```

Resume an explicit task file:

```bash
gemma-qat-orchestrate resume configs/v3-task.example.json \
  --provider codex \
  --authorize-commands
```

The explicit loader remains closed and strict. Natural-language intake does not make
`TaskSpec` fields optional and does not weaken this format.

## Deterministic scripted provider

Offline development can inject one ordered response file:

```bash
gemma-qat-orchestrate run --description "Update the exact message." \
  --provider scripted \
  --responses responses.json \
  --authorize-commands
```

Natural-language mode consumes an `INTAKE_ANALYZER` entry before the existing
specialist entries:

```json
[
  {
    "role": "INTAKE_ANALYZER",
    "response": {
      "normalized_description": "Update the exact message.",
      "acceptance_criteria": ["The requested message is updated."],
      "candidate_scope": ["src/example.py", "tests/test_example.py"],
      "verification_commands": [
        {
          "argv": ["python", "-m", "pytest", "-q", "tests/test_example.py"],
          "cwd": ".",
          "rationale": "focused behavior check"
        }
      ],
      "risk_signals": {
        "exact_outcome": true,
        "unique_repository_evidence": true,
        "cohesive_scope": true,
        "focused_verification_available": true,
        "public_contract_impact": false,
        "configuration_impact": false,
        "architecture_or_ownership_impact": false,
        "security_or_privacy_impact": false,
        "data_impact": false,
        "dependency_impact": false,
        "operational_impact": false,
        "compatibility_impact": false,
        "uncertainty_present": false
      },
      "ambiguities": [],
      "assumptions": [],
      "repository_evidence": ["The focused module and test own this message."]
    }
  },
  {"role": "IMPLEMENTER", "response": {"task_id": "{{TASK_ID}}", "...": "complete role artifact"}},
  {"role": "VERIFIER", "response": {"task_id": "{{TASK_ID}}", "...": "complete role artifact"}}
]
```

Every specialist response must contain its complete role schema. The scripted clients
fail when invocation order differs, making tests sensitive to accidental transition
changes. In natural-language mode, the CLI replaces the exact `{{TASK_ID}}` marker in
specialist response text after generating the task identity. The deterministic suite
never needs a live model.

## Budgets and failure behavior

| Budget | Default |
| --- | ---: |
| Plan revisions | 2 |
| Shared implementation revisions | 2 |
| Verifier schema-only repair | 1 |
| Reviewer-driven repairs | 2 (also consumes shared implementation budget) |
| Provider invocation retry | 1 |

Every consumption emits and persists an event; there is no recursive or hidden retry.
Transport failure, malformed artifact, product failure, environment failure,
authorization denial, scope violation, fingerprint drift, and budget exhaustion remain
distinct machine-readable outcomes.

`CHANGE_COMPLETE` means only that the coding workflow completed. It never authorizes
Git stage, commit, push, merge, deployment, or another side effect.

## Development and tests

All deterministic tests are offline:

```bash
python -m pytest -q tests/v3
python -m pytest -q
ruff format --check .
ruff check .
python -m mypy
```

The suite covers natural-language and stdin intake, strict analysis parsing, repository
discovery/override, deterministic task IDs, conservative routing, Windows-style path
normalization, safe command compilation, authorization, ambiguity, schema-v2
persistence, task-ID resume, legacy JSON, FAST/FULL workflows, artifact boundaries,
scope drift, fingerprints, evidence, and bounded failure behavior.
