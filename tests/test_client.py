"""Tests for :mod:`gemma_qat_bench.client`."""

from __future__ import annotations

import pytest
import requests

from conftest import FakeResponse, FakeSession, chat_response
from gemma_qat_bench.client import LlamaClient
from gemma_qat_bench.config import SamplingConfig
from gemma_qat_bench.exceptions import InferenceError


def _client(session: FakeSession, base_url: str = "http://localhost:8001/") -> LlamaClient:
    return LlamaClient(base_url, session=session, timeout_s=42.0)


# -- chat payload ----------------------------------------------------------- #


def test_chat_builds_expected_payload():
    session = FakeSession(post_response=FakeResponse(json_data=chat_response()))
    client = _client(session)
    sampling = SamplingConfig(
        temperature=0.5,
        top_p=0.9,
        top_k=40,
        max_tokens=64,
        extra_body={"chat_template_kwargs": {"thinking": False}},
    )

    client.chat(
        model="qat",
        system_prompt="sys",
        user_prompt="hi",
        sampling=sampling,
    )

    body = session.last_post_json
    assert session.last_post_url == "http://localhost:8001/v1/chat/completions"
    assert body["model"] == "qat"
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert body["temperature"] == 0.5
    assert body["top_p"] == 0.9
    assert body["top_k"] == 40
    assert body["max_tokens"] == 64
    assert body["stream"] is False
    assert body["chat_template_kwargs"] == {"thinking": False}


def test_chat_returns_payload_and_elapsed():
    payload = chat_response()
    session = FakeSession(post_response=FakeResponse(json_data=payload))
    data, elapsed = _client(session).chat(
        model="m", system_prompt="s", user_prompt="u", sampling=SamplingConfig()
    )
    assert data == payload
    assert elapsed >= 0.0


# -- chat errors ------------------------------------------------------------ #


def test_chat_raises_on_transport_error():
    session = FakeSession(post_exc=requests.ConnectionError("down"))
    with pytest.raises(InferenceError):
        _client(session).chat(
            model="m", system_prompt="s", user_prompt="u", sampling=SamplingConfig()
        )


def test_chat_raises_on_http_error_with_body():
    session = FakeSession(
        post_response=FakeResponse(status_code=500, text="boom details")
    )
    with pytest.raises(InferenceError) as exc:
        _client(session).chat(
            model="m", system_prompt="s", user_prompt="u", sampling=SamplingConfig()
        )
    assert "500" in str(exc.value)
    assert "boom details" in str(exc.value)


def test_chat_raises_on_non_json_body():
    session = FakeSession(post_response=FakeResponse(raise_on_json=True))
    with pytest.raises(InferenceError):
        _client(session).chat(
            model="m", system_prompt="s", user_prompt="u", sampling=SamplingConfig()
        )


# -- health ----------------------------------------------------------------- #


def test_health_true_on_200():
    session = FakeSession(get_response=FakeResponse(status_code=200))
    assert _client(session).health() is True


def test_health_false_on_503():
    session = FakeSession(get_response=FakeResponse(status_code=503))
    assert _client(session).health() is False


def test_health_false_on_transport_error():
    session = FakeSession(get_exc=requests.ConnectionError("refused"))
    assert _client(session).health() is False


def test_base_url_trailing_slash_stripped():
    client = LlamaClient("http://host:1234/", session=FakeSession())
    assert client.base_url == "http://host:1234"
