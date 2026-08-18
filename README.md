# Gemma QAT Bench

A reproducible benchmark harness for comparing **Quantization-Aware Training (QAT)** and **non-QAT** Gemma GGUF models with [`llama.cpp`](https://github.com/ggml-org/llama.cpp).

The project automates the full workflow:

```text
build llama.cpp
      ↓
download GGUF models
      ↓
start llama-server
      ↓
warm up the model
      ↓
measure throughput + wall time + VRAM
      ↓
stop the server
      ↓
repeat for the next model
      ↓
compare QAT vs non-QAT
      ↓
write Markdown + JSON reports
```

The default configuration reproduces a Gemma 4 12B comparison using the **UD-Q4_K_XL** GGUF quantization for both variants.

> **Scope:** this project measures **runtime performance and memory usage**. It is not a model-quality or accuracy benchmark.

---

## Highlights

- QAT vs non-QAT benchmarking under the same prompt, sampling settings, context size, backend, and hardware.
- Automatic `llama.cpp` clone and CMake build.
- CUDA auto-detection, with explicit `--cuda` and `--no-cuda` overrides.
- Automatic Hugging Face model download with local caching.
- Automatic `llama-server` lifecycle management and `/health` polling.
- Warmup runs excluded from measured results.
- Multiple measured runs per model instead of a single noisy sample.
- Generation throughput, prompt throughput, wall time, VRAM, mean, median, and standard deviation.
- Gemma reasoning-aware response handling (`content` and `reasoning_content`).
- Console, Markdown, and JSON reports.
- Fully offline unit-test suite with injectable fakes for network, subprocess, server, and GPU interactions.
- CLI, Makefile targets, PyCharm run configurations, and GitHub Actions CI.

### V3 coding orchestration

The repository also includes a deterministic SDK-backed software-development
orchestrator with repository-aware natural-language task intake. From the repository
root, a normal live workflow starts with only the requested outcome:

```bash
python -m pip install -e ".[dev,v3-codex]"
gemma-qat-orchestrate run --description "Improve the CLI error for an invalid task file."
```

V3 derives and displays the task ID, repository root, acceptance criteria, conservative
risk/routing decision, narrow file scope, and focused verification commands. The user
still authorizes the exact generated command set before it runs. Natural-language input
also works through stdin:

```bash
printf '%s\n' 'Improve the CLI error for an invalid task file.' \
  | gemma-qat-orchestrate run --stdin
```

Python code continues to own FAST/FULL routing, the state machine, Gates, strict JSON
artifacts, bounded revisions, command authorization, canonical evidence, content
fingerprints, persistence/resume, and escalation. Provider-specific code is isolated
behind typed protocols, with scripted offline fakes and an optional Codex Python SDK
adapter. The original explicit JSON workflow remains available for reproducible and
advanced use.

Start with [the V3 guide](docs/v3-orchestration.md) and the
[requirements/migration map](docs/v3-requirements.md). The
[`configs/v3-task.example.json`](configs/v3-task.example.json) file documents the
advanced explicit format. The V3 workflow is independent of benchmark execution, and
`CHANGE_COMPLETE` never grants Git authority.

---

## Example result

A completed run on an **NVIDIA RTX PRO 4000 Blackwell (24 GB)** produced:

| Metric | Gemma 4 12B IT (non-QAT) | Gemma 4 12B IT (QAT) |
| --- | ---: | ---: |
| Quantization | UD-Q4_K_XL | UD-Q4_K_XL |
| Prompt tokens | 40 | 40 |
| Completion tokens | 512 | 512 |
| Generation speed | 10.49 tok/s | **14.85 tok/s** |
| Generation stdev | 0.00 tok/s | 0.00 tok/s |
| Prompt speed | 14.48 tok/s | **27.37 tok/s** |
| Wall time | 49.286 s | **34.810 s** |
| VRAM used | 8984 MiB | **8364 MiB** |

For that specific run:

- **Generation throughput:** `10.49 → 14.85 tok/s` (**+41.5%**)
- **VRAM:** `620 MiB` saved (**6.9% less**)
- **Average request wall time:** `49.286 s → 34.810 s`

These numbers are an example, not a universal QAT speedup claim. Results depend on the GPU, driver, CUDA toolkit, `llama.cpp` revision, model conversion, quantization format, context size, and sampling settings.

---

## Default models

The tutorial configuration compares these two Hugging Face repositories:

| Variant | Repository | Primary GGUF pattern |
| --- | --- | --- |
| non-QAT | `unsloth/gemma-4-12b-it-GGUF` | `*UD-Q4_K_XL*.gguf` |
| QAT | `unsloth/gemma-4-12B-it-qat-GGUF` | `*UD-Q4_K_XL*.gguf` |

The lowercase/uppercase `b` difference in the repository names is intentional. Hugging Face repository IDs are case-sensitive.

The default download patterns also include `mmproj-BF16` files when available.

---

## Requirements

### Python

- **Python 3.11+**
- The CI matrix currently covers Python **3.11** and **3.12**.

### Build tools

To build `llama.cpp` you need:

- `git`
- `cmake`
- a C/C++ compiler/toolchain
- `curl` / libcurl development files where required by the platform

On Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake curl libcurl4-openssl-dev git
```

### GPU benchmark

For CUDA inference you additionally need:

- an NVIDIA GPU
- a compatible NVIDIA driver
- the CUDA toolkit
- `nvidia-smi`
- preferably `nvcc` available on `PATH`

Verify the environment before building:

```bash
nvidia-smi
nvcc --version
```

`gemma-qat-bench` can auto-detect CUDA, but an actual CUDA build still requires a usable CUDA toolchain. If the environment has `nvidia-smi` but no CUDA compiler/toolkit, install the toolkit or explicitly build with `--no-cuda`.

### Disk and network

The default tutorial models use roughly **14 GB** of disk space in the demonstrated setup, before accounting for the `llama.cpp` source/build tree, Python environment, caches, and result files. Leave comfortable headroom; **20–30 GB of free space** is a practical minimum for this configuration.

Internet access is required for the first `llama.cpp` clone and model download. Once the model files and build are present locally, later benchmark runs reuse them.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/MostafaK66/gemma-qat-bench.git
cd gemma-qat-bench
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the installation:

```bash
which python        # Windows: where.exe python
gemma-qat-bench --help
pytest
```

The package is installed in editable mode, so changes under `src/gemma_qat_bench/` are immediately visible to the environment.

---

## Quick start: GPU benchmark

The explicit workflow is:

### 1. Run the offline tests

```bash
pytest
```

### 2. Build `llama.cpp` with CUDA

```bash
gemma-qat-bench --config configs/tutorial.toml build --cuda
```

The expected server binary is normally:

```text
third_party/llama.cpp/build/bin/llama-server
```

You can verify the build with:

```bash
grep '^GGML_CUDA' third_party/llama.cpp/build/CMakeCache.txt
third_party/llama.cpp/build/bin/llama-server --version
```

A CUDA build should show:

```text
GGML_CUDA:BOOL=ON
```

### 3. Download the configured models

```bash
gemma-qat-bench --config configs/tutorial.toml download
```

The download is skipped automatically when the configured GGUF already exists locally.

### 4. Run the benchmark

```bash
gemma-qat-bench --config configs/tutorial.toml bench
```

`bench` also downloads missing configured models on demand, so an explicit `download` step is useful for visibility but is not mandatory.

### One-command workflow

To build `llama.cpp` and then run the full benchmark:

```bash
gemma-qat-bench --config configs/tutorial.toml all --cuda
```

---

## CPU-only workflow

A GPU is not required for the Python package or offline tests. You can force a CPU-only `llama.cpp` build with:

```bash
gemma-qat-bench --config configs/tutorial.toml build --no-cuda
```

Then run without VRAM capture:

```bash
gemma-qat-bench --config configs/tutorial.toml bench --no-vram
```

The default 12B models are intended for a capable system and will be much slower on CPU. For lightweight development, consider configuring smaller GGUF models.

---

## Remote GPU / RunPod workflow

A practical workflow is to keep the repository, models, build output, and results on persistent storage such as `/workspace`.

```bash
cd /workspace
git clone https://github.com/MostafaK66/gemma-qat-bench.git
cd gemma-qat-bench

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pytest
nvidia-smi
nvcc --version

gemma-qat-bench build --cuda
gemma-qat-bench --config configs/tutorial.toml download
gemma-qat-bench --config configs/tutorial.toml bench
```

### If the default port is already occupied

The tutorial config uses port `8001`. Some cloud images already run `nginx` or another service on that port.

Check it with:

```bash
ss -ltnp | grep ':8001'
```

Create a provider-specific config instead of modifying the tutorial config:

```bash
cp configs/tutorial.toml configs/runpod.toml
sed -i 's/port = 8001/port = 8002/' configs/runpod.toml
```

Verify the new port:

```bash
grep '^port' configs/runpod.toml
```

Then benchmark with:

```bash
gemma-qat-bench --config configs/runpod.toml bench
```

Choose any free local port if `8002` is also occupied.

---

## What the benchmark actually does

For each configured model, `BenchmarkRunner` performs the following sequence:

1. Resolve the requested GGUF file locally.
2. Download it from Hugging Face if it is missing.
3. Start `llama-server` with the configured host, port, context size, and GPU layers.
4. Poll `/health` until the server reports ready.
5. Send the configured warmup request(s).
6. Sample steady-state GPU memory when VRAM capture is enabled.
7. Send the configured number of measured chat-completion requests.
8. Parse token counts and timing information returned by `llama.cpp`.
9. Stop `llama-server` and release the model.
10. Repeat the same procedure for the next model.
11. Aggregate the measurements and compare the first non-QAT baseline with the first QAT result.
12. Render console output and write JSON + Markdown reports.

The warmup result is deliberately excluded from the final statistics.

---

## Default benchmark workload

The default config uses:

```toml
[benchmark]
prompt = "Explain why quantization-aware training is useful for running LLMs on consumer GPUs."
system_prompt = "You are a helpful local AI assistant."
n_runs = 3
warmup_runs = 1
request_timeout_s = 300.0

[sampling]
temperature = 1.0
top_p = 0.95
top_k = 64
max_tokens = 512
```

Both model variants receive the same prompt and sampling configuration. This keeps the workload consistent so the runtime comparison is meaningful.

---

## Metrics

| Metric | Meaning |
| --- | --- |
| **Prompt tokens** | Number of input tokens processed for the chat request. |
| **Completion tokens** | Number of generated output tokens. |
| **Generation speed (tok/s)** | Mean output-token generation throughput across measured runs. |
| **Generation stdev (tok/s)** | Sample standard deviation of generation throughput across measured runs. |
| **Prompt speed (tok/s)** | Mean prompt/prefill processing throughput reported by `llama.cpp`. |
| **Wall time (s)** | Client-observed elapsed time from sending the request until the full response is received. |
| **VRAM used (MiB)** | GPU memory sampled after warmup, while the model is loaded in steady state. |

Generation throughput prefers `llama.cpp`'s non-standard `timings.predicted_per_second` value. If that field is unavailable, the project falls back to client wall-clock completion tokens per second.

The comparison report computes:

```text
speedup % = (QAT generation speed - baseline generation speed)
            --------------------------------------------------- × 100
                     baseline generation speed
```

and:

```text
VRAM saved = baseline VRAM - QAT VRAM
```

---

## Output

Every successful benchmark prints a summary to the terminal and writes two timestamped files:

```text
results/
├── benchmark-YYYYMMDD-HHMMSS.json
└── benchmark-YYYYMMDD-HHMMSS.md
```

If a run lands in the same second as an existing report pair, numeric suffixes are used in order (`-2`, `-3`, ...), for example `benchmark-YYYYMMDD-HHMMSS-2.json` and `.md`.

Example console summary:

```text
Model                     Gen tok/s  ±stdev  Prompt tok/s  Wall s  VRAM MiB
------------------------  ---------  -------  ------------  ------  --------
Gemma 4 12B IT (non-QAT)  10.49      0.00     14.48         49.286  8984
Gemma 4 12B IT (QAT)      14.85      0.00     27.37         34.810  8364

Comparison (QAT vs baseline):
  - Generation speed: 10.49 -> 14.85 tok/s (+41.5%)
  - VRAM: 620 MiB saved (6.9% less than baseline)
  - Wall time: 49.286s -> 34.810s
```

The Markdown report is convenient for documentation and pull requests. The JSON report includes aggregate values as well as the individual measured runs for programmatic analysis.

---

## CLI reference

General form:

```text
gemma-qat-bench [--config PATH] [-v] {build,download,bench,all} ...
```

### Global options

| Option | Description |
| --- | --- |
| `--config PATH` | TOML configuration file. If omitted, built-in tutorial defaults are used. |
| `-v`, `--verbose` | Enable debug logging. |

### `build`

Clone and compile `llama.cpp`.

```bash
gemma-qat-bench build [--cuda | --no-cuda] [--jobs N] [--source-dir DIR]
```

| Option | Description |
| --- | --- |
| `--cuda` | Force CUDA build. |
| `--no-cuda` | Force CPU-only build. |
| `--jobs N` | Number of parallel build jobs. |
| `--source-dir DIR` | Override the `llama.cpp` source/build location. |

### `download`

Download the configured model files:

```bash
gemma-qat-bench --config configs/tutorial.toml download
```

### `bench`

Run the benchmark using an already-built `llama-server`:

```bash
gemma-qat-bench --config configs/tutorial.toml bench \
  [--runs N] \
  [--warmup N] \
  [--server-binary PATH] \
  [--no-vram] \
  [--out DIR]
```

| Option | Description |
| --- | --- |
| `--runs N` | Override measured runs per model. |
| `--warmup N` | Override warmup runs per model. |
| `--server-binary PATH` | Use a specific `llama-server` binary. |
| `--no-vram` | Disable `nvidia-smi` VRAM capture. |
| `--out DIR` | Override the results directory. |

### `all`

Build `llama.cpp` and then run the full benchmark:

```bash
gemma-qat-bench --config configs/tutorial.toml all --cuda
```

The same build and benchmark overrides are available on `all`.

The package can also be invoked as a Python module:

```bash
python -m gemma_qat_bench --config configs/tutorial.toml bench
```

---

## Configuration

The main configuration lives in [`configs/tutorial.toml`](configs/tutorial.toml).

Important settings include:

| Section | Setting | Purpose |
| --- | --- | --- |
| top level | `results_dir` | Directory for Markdown and JSON output. |
| top level | `capture_vram` | Enable/disable VRAM sampling. |
| `server` | `binary_path` | Path to `llama-server`. |
| `server` | `host`, `port` | Local server bind address. |
| `server` | `ctx_size` | Context window requested from `llama.cpp`. |
| `server` | `n_gpu_layers` | Number of layers requested for GPU offload. |
| `server` | `startup_timeout_s` | Maximum model startup/health-check wait. |
| `sampling` | `temperature`, `top_p`, `top_k` | Sampling controls. |
| `sampling` | `max_tokens` | Maximum completion length. |
| `benchmark` | `prompt` | User prompt used for every benchmark request. |
| `benchmark` | `system_prompt` | System instruction sent with each request. |
| `benchmark` | `n_runs` | Number of measured runs per model. |
| `benchmark` | `warmup_runs` | Number of unmeasured warmup runs. |
| `benchmark` | `request_timeout_s` | HTTP request timeout. |
| `build` | `repo_url` | `llama.cpp` repository URL. |
| `build` | `source_dir` | Local source/build location. |
| `models` | `repo_id` | Hugging Face model repository. |
| `models` | `local_dir` | Local model storage directory. |
| `models` | `is_qat` | Marks the model as QAT or baseline. |
| `models` | `include_patterns` | Files allowed during download. |
| `models` | `gguf_pattern` | Pattern used to select the primary model GGUF. |

To make a custom configuration:

```bash
cp configs/tutorial.toml configs/my-benchmark.toml
```

Edit it, then run:

```bash
gemma-qat-bench --config configs/my-benchmark.toml bench
```

### Disable Gemma reasoning

Gemma can return generated text in `reasoning_content` while `content` is empty. The client handles both automatically.

If you want to disable thinking in the request template, add:

```toml
[sampling.extra_body.chat_template_kwargs]
thinking = false
```

---

## Project structure

```text
gemma-qat-bench/
│
├── src/
│   └── gemma_qat_bench/
│       ├── __init__.py           # version + public API exports
│       ├── __main__.py           # enables: python -m gemma_qat_bench
│       ├── exceptions.py         # custom exception hierarchy
│       ├── _logging.py           # package logging setup
│       ├── config.py             # frozen config dataclasses + TOML loading
│       ├── build.py              # clone + CMake build of llama.cpp; CUDA detection
│       ├── models.py             # Hugging Face GGUF download/resolution
│       ├── server.py             # start / health-check / stop llama-server
│       ├── client.py             # OpenAI-compatible HTTP client
│       ├── vram.py               # nvidia-smi VRAM sampling
│       ├── metrics.py            # per-run and aggregate metrics
│       ├── benchmark.py          # benchmark orchestration
│       ├── report.py             # comparison + console/Markdown/JSON rendering
│       └── cli.py                # argparse entry point
│
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_metrics.py
│   ├── test_client.py
│   ├── test_server.py
│   ├── test_build.py
│   ├── test_models.py
│   ├── test_vram.py
│   ├── test_report.py
│   ├── test_benchmark.py
│   └── test_cli.py
│
├── configs/
│   └── tutorial.toml
│
├── scripts/
│   ├── build_llama_cpp.sh
│   └── download_models.sh
│
├── .run/
│   ├── pytest.run.xml
│   └── bench.run.xml
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── pyproject.toml
├── Makefile
├── README.md
├── LICENSE
└── .gitignore
```

---

## Package architecture

| Module | Responsibility |
| --- | --- |
| `config.py` | Immutable, validated configuration objects and TOML loading. |
| `build.py` | Clone/configure/build `llama.cpp`; resolve CUDA mode and server binary. |
| `models.py` | Ensure the requested GGUF is present; download from Hugging Face when missing. |
| `server.py` | Manage one `llama-server` process and wait for readiness. |
| `client.py` | Call `/health` and `/v1/chat/completions`. |
| `vram.py` | Query GPU memory usage with `nvidia-smi`. |
| `metrics.py` | Parse one response and aggregate repeated measurements. |
| `benchmark.py` | Coordinate model → server → warmup → VRAM → measured runs. |
| `report.py` | Compare baseline and QAT metrics and render output formats. |
| `cli.py` | Parse CLI arguments, apply config overrides, dispatch commands. |

The implementation intentionally uses dependency injection around subprocesses, HTTP clients, model downloads, server factories, and VRAM sampling. That keeps the core workflow testable without requiring a network connection, a GPU, or a real `llama-server` process.

---

## Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the complete offline test suite:

```bash
pytest
```

Run linting:

```bash
ruff check src tests
```

Format and auto-fix:

```bash
ruff format src tests
ruff check --fix src tests
```

Run static type checking:

```bash
mypy
```

### Makefile shortcuts

```bash
make help
make install
make test
make lint
make format
make typecheck
make build-llama
make download
make bench
make all
make clean
```

The current test suite is fully offline and contains **103 tests**.

---

## PyCharm

The repository includes shared run configurations under `.run/`:

- `pytest (all tests)`
- `bench (tutorial)`

Recommended local setup:

1. Open the repository root in PyCharm.
2. Configure `.venv` as the project interpreter.
3. Mark `src/` as **Sources Root** if PyCharm does not detect it automatically.
4. Mark `tests/` as **Test Sources Root**.
5. Use `pytest` as the default test runner.

For a remote GPU while using a PyCharm edition without a remote SSH interpreter, a simple workflow is:

```text
edit locally in PyCharm
        ↓
git commit / push
        ↓
SSH to the GPU machine
        ↓
git pull
        ↓
run the benchmark remotely
```

---

## CI

The GitHub Actions workflow installs the package with development extras and runs:

```text
Ruff
pytest + coverage
mypy
```

across Python 3.11 and 3.12. The current workflow runs on pull requests and on pushes to the branch configured in `.github/workflows/ci.yml`.

---

## Troubleshooting

### `llama-server` cannot bind to the configured port

Example:

```text
couldn't bind HTTP server socket, hostname: 127.0.0.1, port: 8001
```

Find the process using the port:

```bash
ss -ltnp | grep ':8001'
```

Use another free port in a copied TOML config.

### `llama-server` binary not found

Run:

```bash
gemma-qat-bench build
```

or pass an existing binary:

```bash
gemma-qat-bench --config configs/tutorial.toml bench \
  --server-binary /path/to/llama-server
```

### CUDA was selected but CMake cannot build CUDA code

Check both:

```bash
nvidia-smi
nvcc --version
```

A driver-visible GPU does not by itself guarantee that the CUDA compiler/toolkit required by CMake is installed.

### Out of VRAM

Possible mitigations:

- choose a smaller model
- reduce `ctx_size`
- reduce `n_gpu_layers`
- use a more memory-efficient quantization
- run CPU-only if necessary

### Hugging Face download fails

Check:

- repository ID and casing
- internet connectivity
- available disk space
- whether the repository requires authentication or license acceptance

### `content` is empty

Gemma may place its generated answer in `reasoning_content`. This project checks `content` first and then falls back to `reasoning_content`.

### VRAM is reported as `n/a`

VRAM capture requires a working NVIDIA environment and `nvidia-smi`. Use `--no-vram` when VRAM measurement is not applicable.

---

## Reproducibility notes

The builder currently performs a shallow clone of the configured `llama.cpp` repository. Because upstream `llama.cpp` changes rapidly, results can vary between runs performed at different times even when the model and GPU are unchanged.

For benchmark records, capture at least:

```bash
python --version
nvidia-smi
third_party/llama.cpp/build/bin/llama-server --version
```

Also keep the generated JSON report, which contains the individual measured runs in addition to the aggregate summary.

---

## Interpreting QAT results correctly

QAT is a training technique that prepares a model to tolerate low-precision inference. It does **not** imply that every QAT model will always be faster by the same percentage on every device.

A defensible conclusion should look like:

> On this hardware, with these model files, this quantization, and this `llama.cpp` build, the QAT variant achieved the measured throughput and VRAM differences shown in the report.

That distinction matters when comparing results across GPUs, quantizations, backend versions, or different GGUF conversions.

---

## Attribution

The default experiment is based on the DataCamp tutorial **“Quantization Aware Training: A Guide to Improving Gemma 4's Local Inference”**.

- Gemma models: Google DeepMind
- GGUF repositories/conversions: [Unsloth](https://huggingface.co/unsloth)
- Inference backend: [`llama.cpp`](https://github.com/ggml-org/llama.cpp)

Model availability and repository contents can change over time. Verify Hugging Face repository IDs if downloads begin failing.

---

## License

This project is licensed under the **MIT License**. See [`LICENSE`](LICENSE).
