---
name: benchmarking
description: Design, implement, review, or interpret performance and ML inference benchmarks. Use when changing benchmark methodology, timing, warmups, repeated runs, VRAM capture, result aggregation, reproducibility metadata, or performance conclusions.
---

# Benchmarking

## Principle

A benchmark should isolate the variable being compared. Do not optimize methodology to
produce a preferred conclusion.

## Experimental control

Hold constant unless intentionally studied:

- hardware,
- driver/runtime/backend version,
- model family/size,
- quantization format,
- prompt/workload,
- context size,
- sampling parameters,
- output token budget,
- batch/concurrency settings,
- server flags,
- warmup policy,
- number of measured runs.

If any differ, state the difference explicitly.

## Warmup

Use warmup runs when first-use initialization, kernel setup, caches, model paging, JIT,
or allocator behavior could bias the first measurement. Exclude warmups from aggregate
statistics unless the experiment explicitly studies cold-start behavior.

## Repeated measurements

Use multiple measured runs for noisy metrics. Report an appropriate central tendency and
spread. In this project:

- mean generation throughput,
- median generation throughput,
- sample standard deviation,
- mean wall time,
- mean prompt throughput.

Do not report extra decimal precision that exceeds measurement stability.

## Timing semantics

Keep these concepts distinct:

- **startup/load time** — server/model initialization,
- **prompt/prefill time** — processing input tokens,
- **generation/decode time** — producing completion tokens,
- **server-reported throughput** — backend timing metric,
- **wall time** — client-observed end-to-end request duration.

When a backend-specific timing field is preferred, document the fallback behavior.

## Resource measurement

For GPU/CPU/RAM/VRAM measurements:

- define when the sample is taken,
- distinguish steady-state from peak usage,
- avoid attributing unrelated processes to the benchmark when possible,
- state units clearly (MiB vs MB, GiB vs GB).

## Reproducibility metadata

Capture or document enough context to interpret a result:

- timestamp,
- OS/platform,
- Python version,
- GPU/CPU model,
- driver/CUDA/runtime version,
- backend (`llama.cpp`) revision/version,
- model repo/file/quantization,
- benchmark config,
- number of runs/warmups.

The codebase may not yet record every item. When improving reports, prefer adding
reproducibility metadata without breaking existing result consumers.

## Statistical interpretation

- A low stdev means repeated measurements were stable; it does not prove external
  validity.
- A faster QAT run does not prove QAT is always faster on all hardware/backends.
- Smaller model files may contribute to memory/throughput differences; explain what was
  actually compared.
- Distinguish correlation in one artifact pair from a general causal claim.

## Benchmark code quality

- Keep measurement extraction in metric modules, not CLI rendering.
- Keep orchestration separate from backend/client implementation.
- Make timing/resource samplers injectable where practical so unit tests remain offline.
- Use deterministic fixtures for metrics parsing/aggregation.
- Test missing/malformed backend timing fields and fallback behavior.

## Changes to methodology

When changing warmups, run count, token budget, metric definition, resource sampling, or
comparison formulas:

1. explain why,
2. update tests,
3. update README/config examples,
4. consider backward compatibility of JSON/Markdown output,
5. do not compare old and new result sets as if methodology were unchanged.

## Interpretation template

Prefer wording like:

> On `<hardware>`, using `<backend/model/quantization/config>`, variant B achieved
> `<measured difference>` versus variant A in this benchmark.

Avoid wording like:

> Technique B is always X% faster.
