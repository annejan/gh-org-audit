# SPDX-FileCopyrightText: 2026 Anne Jan Brouwer
# SPDX-License-Identifier: MIT

"""Shared fakes: a requests-like session backed by a route table."""

import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests

import gh_org_audit


class FakeResponse:
    def __init__(self, status_code=200, body=None, headers=None, next_url=None, text=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.links = {"next": {"url": next_url}} if next_url else {}
        self.text = text if text is not None else (json.dumps(body) if body is not None else "")
        self.url = ""

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} for {self.url}", response=self)


class FakeSession:
    """Route table: {(path, frozenset(params)): FakeResponse | [FakeResponse, ...]}.

    A list is consumed one response per call (for retry tests). Unknown routes
    return 404. Every call is logged in `calls`.
    """

    def __init__(self, routes=None):
        self.routes = dict(routes or {})
        self.calls = []
        self.headers = {}

    def add(self, path, response, params=None):
        self.routes[(path, _key(params))] = response

    def get(self, url, params=None, timeout=None):
        u = urlparse(url)
        path = u.path.replace("/api.github.com", "")
        merged = {k: v[0] for k, v in parse_qs(u.query).items()}
        merged.update(params or {})
        merged.pop("per_page", None)
        self.calls.append((path, merged))
        resp = self.routes.get((path, _key(merged)))
        if resp is None:
            resp = self.routes.get((path, _key(None)))
        if resp is None:
            resp = FakeResponse(404, {"message": "Not Found"})
        if isinstance(resp, list):
            resp = resp.pop(0) if len(resp) > 1 else resp[0]
        resp.url = url
        return resp


def _key(params):
    return frozenset((params or {}).items())


@pytest.fixture
def gh(monkeypatch):
    """A GitHub client whose session is a FakeSession; sleep is a no-op."""
    monkeypatch.setattr(gh_org_audit.time, "sleep", lambda *_: None)
    client = gh_org_audit.GitHub("dummy")
    client.s = FakeSession()
    return client
