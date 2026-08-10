"""Shared test fixtures and lightweight fakes.

No test touches the network, the filesystem outside ``tmp_path``, or a real
subprocess. Collaborators are replaced with the fakes defined here.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pytest

# Make ``src/`` importable without installing the package (belt-and-suspenders;
# pyproject also sets tool.pytest.ini_options.pythonpath).
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# --------------------------------------------------------------------------- #
# Canned llama.cpp response                                                    #
# --------------------------------------------------------------------------- #


def chat_response(
    *,
    prompt_tokens: int = 40,
    completion_tokens: int = 512,
    gen_per_s: float | None = 94.65,
    prompt_per_s: float | None = 510.22,
    content: str = "Because it keeps quality while shrinking memory.",
    reasoning_content: str | None = None,
    include_usage: bool = True,
    include_timings: bool = True,
) -> dict[str, Any]:
    """Build a chat-completion payload shaped like ``llama-server``'s."""
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    payload: dict[str, Any] = {"choices": [{"message": message}]}
    if include_usage:
        payload["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
    if include_timings:
        payload["timings"] = {
            "prompt_n": prompt_tokens,
            "predicted_n": completion_tokens,
            "prompt_per_second": prompt_per_s,
            "predicted_per_second": gen_per_s,
        }
    return payload


# --------------------------------------------------------------------------- #
# HTTP fakes (for LlamaClient)                                                 #
# --------------------------------------------------------------------------- #


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        raise_on_json: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self._raise_on_json = raise_on_json

    def json(self) -> Any:
        if self._raise_on_json:
            raise ValueError("no JSON")
        return self._json_data


class FakeSession:
    """Records the last POST payload and returns/raises pre-programmed results."""

    def __init__(
        self,
        *,
        post_response: FakeResponse | None = None,
        post_exc: Exception | None = None,
        get_response: FakeResponse | None = None,
        get_exc: Exception | None = None,
    ) -> None:
        self.post_response = post_response
        self.post_exc = post_exc
        self.get_response = get_response
        self.get_exc = get_exc
        self.last_post_url: str | None = None
        self.last_post_json: dict[str, Any] | None = None
        self.last_get_url: str | None = None

    def post(self, url: str, json: dict[str, Any], timeout: float) -> FakeResponse:
        self.last_post_url = url
        self.last_post_json = json
        if self.post_exc is not None:
            raise self.post_exc
        assert self.post_response is not None
        return self.post_response

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.last_get_url = url
        if self.get_exc is not None:
            raise self.get_exc
        assert self.get_response is not None
        return self.get_response


# --------------------------------------------------------------------------- #
# Subprocess fake (for ServerManager)                                          #
# --------------------------------------------------------------------------- #


class FakeProcess:
    """Programmable stand-in for :class:`subprocess.Popen`."""

    def __init__(
        self,
        *,
        poll_results: Iterable[int | None] = (None,),
        wait_raises_once: bool = False,
    ) -> None:
        self._poll_results = list(poll_results)
        self._poll_index = 0
        self.terminated = False
        self.killed = False
        self.wait_calls = 0
        self._wait_raises_once = wait_raises_once

    def poll(self) -> int | None:
        if self._poll_index < len(self._poll_results):
            result = self._poll_results[self._poll_index]
            self._poll_index += 1
            return result
        return self._poll_results[-1]

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        import subprocess

        self.wait_calls += 1
        if self._wait_raises_once and self.wait_calls == 1:
            raise subprocess.TimeoutExpired(cmd="llama-server", timeout=timeout or 0)
        return 0


# --------------------------------------------------------------------------- #
# Health-check client fake (for ServerManager)                                 #
# --------------------------------------------------------------------------- #


class FakeHealthClient:
    def __init__(self, health_sequence: Iterable[bool]) -> None:
        self._sequence = list(health_sequence)
        self._index = 0

    def health(self) -> bool:
        if self._index < len(self._sequence):
            value = self._sequence[self._index]
            self._index += 1
            return value
        return self._sequence[-1]


class SequenceClock:
    """Deterministic monotonic clock returning successive values."""

    def __init__(self, values: Iterable[float]) -> None:
        self._values = list(values)
        self._index = 0

    def __call__(self) -> float:
        if self._index < len(self._values):
            value = self._values[self._index]
            self._index += 1
            return value
        return self._values[-1]


# --------------------------------------------------------------------------- #
# Chat client + server fakes (for BenchmarkRunner)                             #
# --------------------------------------------------------------------------- #


class FakeChatClient:
    def __init__(self, response: dict[str, Any], wall_time_s: float = 5.0) -> None:
        self._response = response
        self._wall = wall_time_s
        self.calls = 0

    def chat(self, **_kwargs: Any) -> tuple[dict[str, Any], float]:
        self.calls += 1
        return self._response, self._wall


class FakeServer:
    def __init__(self, base_url: str = "http://127.0.0.1:8001") -> None:
        self._base_url = base_url
        self.entered = False
        self.exited = False

    @property
    def base_url(self) -> str:
        return self._base_url

    def __enter__(self) -> FakeServer:
        self.entered = True
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.exited = True


# --------------------------------------------------------------------------- #
# Fixtures                                                                      #
# --------------------------------------------------------------------------- #


@pytest.fixture
def make_gguf() -> Callable[[Path, str], Path]:
    """Return a helper that creates a placeholder .gguf file and returns its path."""

    def _make(directory: Path, name: str = "model-UD-Q4_K_XL.gguf") -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(b"GGUF\x00")
        return path

    return _make
