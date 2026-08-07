"""Thin client for a ``llama-server`` OpenAI-compatible endpoint.

The client is deliberately tiny and takes its :class:`requests.Session` by
injection, which lets tests pass a fake session and exercise every branch
without a network or a running server.
"""


from __future__ import annotations

import time
from typing import Any

import requests

from .config import SamplingConfig
from .exceptions import InferenceError


class LlamaClient:
    """Minimal wrapper over the ``/health`` and ``/v1/chat/completions`` routes."""

    def __init__(
        self,
        base_url: str,
        *,
        session: requests.Session | None = None,
        timeout_s: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session if session is not None else requests.Session()
        self._timeout = timeout_s

    @property
    def base_url(self) -> str:
        return self._base_url

    def health(self) -> bool:
        """Return ``True`` when the server reports it is ready to serve.

        ``llama-server`` answers ``/health`` with 200 once the model is loaded
        and 503 while it is still loading; any transport error means "not yet".
        """
        try:
            response = self._session.get(f"{self._base_url}/health", timeout=5)
        except requests.RequestException:
            return False
        return response.status_code == 200

    def chat(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        sampling: SamplingConfig,
    ) -> tuple[dict[str, Any], float]:
        """Send one chat completion and return ``(payload, wall_time_seconds)``.

        Raises :class:`InferenceError` on transport failure, a non-2xx status,
        or a body that is not valid JSON.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": sampling.temperature,
            "top_p": sampling.top_p,
            "top_k": sampling.top_k,
            "max_tokens": sampling.max_tokens,
            "stream": False,
        }
        payload.update(sampling.extra_body)

        url = f"{self._base_url}/v1/chat/completions"
        start = time.perf_counter()
        try:
            response = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise InferenceError(f"request to {url} failed: {exc}") from exc
        elapsed = time.perf_counter() - start

        if response.status_code != 200:
            body = _safe_body(response)
            raise InferenceError(
                f"server returned HTTP {response.status_code}: {body}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise InferenceError("server returned a non-JSON body") from exc
        return data, elapsed


def _safe_body(response: requests.Response, limit: int = 500) -> str:
    try:
        text = response.text
    except Exception:  # pragma: no cover - extremely defensive
        return "<unreadable body>"
    return text[:limit]


__all__ = ["LlamaClient"]
