# SPDX-FileCopyrightText: 2026 Anne Jan Brouwer
# SPDX-License-Identifier: MIT

import pytest
import requests

from tests.conftest import FakeResponse


def test_paginate_follows_link_header(gh):
    gh.s.add("/orgs/o/repos", FakeResponse(200, [{"name": "a"}], next_url="https://api.github.com/orgs/o/repos?page=2"))
    gh.s.add("/orgs/o/repos", FakeResponse(200, [{"name": "b"}]), params={"page": "2"})
    assert [r["name"] for r in gh.paginate("/orgs/o/repos")] == ["a", "b"]
    assert gh.s.calls[0][1].get("per_page") is None  # stripped by fake, but was sent
    assert gh.s.calls[1][1] == {"page": "2"}


def test_ok404_returns_none(gh):
    assert gh.get("/nope", ok404=True) is None


def test_404_raises_without_ok404(gh):
    with pytest.raises(requests.HTTPError):
        gh.get("/nope")


def test_rate_limit_sleeps_and_retries(gh, monkeypatch):
    slept = []
    monkeypatch.setattr("gh_org_audit.time.sleep", slept.append)
    monkeypatch.setattr("gh_org_audit.time.time", lambda: 1000)
    gh.s.add(
        "/x",
        [
            FakeResponse(403, {}, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1010"}),
            FakeResponse(200, {"ok": True}),
        ],
    )
    assert gh.get("/x").json() == {"ok": True}
    assert slept == [12]


def test_retry_after_header(gh, monkeypatch):
    slept = []
    monkeypatch.setattr("gh_org_audit.time.sleep", slept.append)
    gh.s.add("/x", [FakeResponse(429, {}, headers={"Retry-After": "3"}), FakeResponse(200, {"ok": True})])
    assert gh.get("/x").json() == {"ok": True}
    assert slept == [3]


def test_5xx_retries_with_backoff_then_raises(gh, monkeypatch):
    slept = []
    monkeypatch.setattr("gh_org_audit.time.sleep", slept.append)
    gh.s.add("/x", [FakeResponse(502, {})])
    with pytest.raises(requests.HTTPError):
        gh.get("/x")
    assert slept == [1, 2, 4, 8, 16, 32]


def test_auth_header_set():
    from gh_org_audit import GitHub

    c = GitHub("tok")
    assert c.s.headers["Authorization"] == "Bearer tok"
