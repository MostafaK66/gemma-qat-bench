# gemma-qat-bench

Benchmark **Quantization-Aware Training (QAT)** vs **non-QAT** GGUF models locally
with [`llama.cpp`](https://github.com/ggml-org/llama.cpp). This is a clean,
fully-tested reimplementation of the DataCamp *"Gemma 4 QAT"* tutorial: it builds
`llama.cpp`, downloads the non-QAT and QAT variants, serves each with
`llama-server`, and compares **generation speed** and **VRAM usage**.

```
 build llama.cpp ──► download GGUFs ──► serve (llama-server) ──► measure ──► compare
```

## Why this exists

The tutorial is a sequence of shell commands. This repo turns it into a small,
importable, testable package with a CLI. Two things the tutorial gets wrong or
glosses over are handled here:

1. **Repo id casing.** The non-QAT model is `unsloth/gemma-4-12b-it-GGUF`
   (lowercase `b`). Hugging Face repo ids are case-sensitive, so the tutorial's
   `gemma-4-12B-it-GGUF` is not the same string.
2. **Gemma 4 is a *thinking* model.** With reasoning enabled, the visible answer
   can land in `reasoning_content` and `content` comes back empty. The client
   reads both, and `sampling.extra_body` lets you disable reasoning.

It also replaces the single-shot measurement with warmup + multiple runs and
reports a mean and standard deviation.

## Requirements

- **Python 3.11+**
- To actually run a benchmark (not required for the tests): `git`, `cmake`, a
  C/C++ toolchain, and — for a GPU build — the CUDA toolkit and an NVIDIA GPU.
  On Debian/Ubuntu: `sudo apt-get install -y build-essential cmake curl libcurl4-openssl-dev`.
- The 12B `UD-Q4_K_XL` weights are ~6.7 GB **each**. Point `local_dir` somewhere
  with room, or swap in a smaller model (see [Configuration](#configuration)).

If you have no NVIDIA GPU, the build falls back to CPU automatically and VRAM
capture is simply skipped.

## Install

```bash
git clone https://github.com/<your-username>/gemma-qat-bench.git
cd gemma-qat-bench
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Quick start

```bash
# 1) Build llama.cpp (CUDA auto-detected; force with --cuda / --no-cuda)
gemma-qat-bench build

# 2) Run the full benchmark against the tutorial config
gemma-qat-bench --config configs/tutorial.toml bench
```

`bench` downloads any missing models on demand, so the two steps above are
enough. To do everything (build → download → benchmark) in one command:

```bash
gemma-qat-bench --config configs/tutorial.toml all
```

Results are printed as a table and written to `results/benchmark-<timestamp>.{json,md}`.

### CLI overview

```
gemma-qat-bench [--config PATH] [-v] <command>

build      Clone + compile llama.cpp        [--cuda|--no-cuda] [--jobs N] [--source-dir DIR]
download   Fetch the configured GGUFs
bench      Run the benchmark                [--runs N] [--warmup N] [--server-binary PATH]
                                            [--no-vram] [--out DIR]
all        build, then bench
```

Every flag overrides the corresponding value from the config file (or the
built-in tutorial defaults if `--config` is omitted).

## Running in PyCharm

1. **Open** the project folder in PyCharm.
2. **Interpreter:** *Settings → Project → Python Interpreter* → add a Virtualenv
   Environment (or select `.venv`). PyCharm will offer to install from
   `pyproject.toml` — accept, or run `pip install -e ".[dev]"` in the terminal.
3. **Sources root:** the `src/` layout is picked up automatically via
   `pyproject.toml` (`tool.pytest.ini_options.pythonpath`). If imports still show
   red, right-click `src/` → *Mark Directory as → Sources Root*.
4. **Test runner:** *Settings → Tools → Python Integrated Tools → Testing* →
   set the default runner to **pytest**.
5. **Run configurations:** two shared configs ship in `.run/` — *"pytest (all
   tests)"* and *"bench (tutorial)"* — and appear in the Run dropdown
   automatically. Pick a config and hit **Run** (or the green ▶).

## Configuration

Copy `configs/tutorial.toml`, edit, and pass it with `--config`. To benchmark a
smaller model (handy for a laptop without a big GPU), change a `[[models]]` block,
for example:

```toml
[[models]]
key = "qat"
display_name = "Gemma 4 E4B (QAT)"
repo_id = "unsloth/gemma-4-E4B-it-qat-GGUF"
local_dir = "models/gemma-4-E4B-it-qat-GGUF"
is_qat = true
```

To stop Gemma 4 from spending the token budget on hidden reasoning:

```toml
[sampling.extra_body.chat_template_kwargs]
thinking = false
```

## How it fits together

| Module        | Responsibility                                                        |
| ------------- | --------------------------------------------------------------------- |
| `config.py`   | Frozen, self-validating config dataclasses; TOML loading.             |
| `build.py`    | `git clone` + `cmake` command builders and driver; CUDA detection.    |
| `models.py`   | Download/resolve GGUFs via `huggingface_hub` (injectable downloader). |
| `server.py`   | Launch, health-check, and tear down `llama-server` (context manager). |
| `client.py`   | POST to `/v1/chat/completions`; read `/health`.                       |
| `vram.py`     | Sample GPU memory via `nvidia-smi` (degrades to `None`).              |
| `metrics.py`  | Parse per-run metrics; aggregate mean/median/stdev.                   |
| `benchmark.py`| Orchestrate download → serve → warmup → measure → aggregate.          |
| `report.py`   | Baseline-vs-QAT comparison; console / Markdown / JSON rendering.      |
| `cli.py`      | Argument parsing, override resolution, command dispatch.              |

Throughput prefers `llama.cpp`'s `timings.predicted_per_second` (the number the
tutorial quotes) and falls back to wall-clock tokens/sec, so it still works
against a strictly OpenAI-compatible backend.

## Testing

The entire suite is **offline** — no network, no GPU, no real subprocess.
Collaborators are dependency-injected and replaced with fakes.

```bash
pytest                 # or: make test
ruff check src tests   # lint
mypy                   # type-check
```

## Project layout

```
gemma-qat-bench/
├── src/gemma_qat_bench/     # package
├── tests/                   # offline test suite
├── configs/tutorial.toml    # default (editable) config
├── scripts/                 # reference bash equivalents
├── .run/                    # shared PyCharm run configs
├── .github/workflows/ci.yml # lint + tests on push
├── pyproject.toml
└── Makefile
```

## Notes & attribution

Concept and default parameters from the DataCamp *"Quantization Aware Training:
A Guide to Improving Gemma 4's Local Inference"* tutorial. Models by Google
DeepMind, GGUF conversions by [Unsloth](https://huggingface.co/unsloth). Model
availability changes; verify repo ids on Hugging Face if a download 404s.

## License

MIT — see [LICENSE](LICENSE).
