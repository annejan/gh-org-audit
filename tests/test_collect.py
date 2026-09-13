# SPDX-FileCopyrightText: 2026 Anne Jan Brouwer
# SPDX-License-Identifier: MIT

import base64

from gh_org_audit import collect_repo, collect_team, perm_from_flags, perm_from_role
from tests.conftest import FakeResponse


def test_perm_from_flags_picks_highest():
    assert perm_from_flags({"admin": True, "push": True}) == "admin"
    assert perm_from_flags({"maintain": True, "push": True, "pull": True}) == "maintain"
    assert perm_from_flags({"push": True, "pull": True}) == "push"
    assert perm_from_flags({"triage": True, "pull": True}) == "triage"
    assert perm_from_flags({"pull": True}) == "pull"
    assert perm_from_flags(None) == "pull"


def test_perm_from_role_builtin_and_custom():
    assert perm_from_role("write", {}) == "push"
    assert perm_from_role("Admin", {}) == "admin"
    assert perm_from_role("read", {}) == "pull"
    # custom role name -> fall back to flags
    assert perm_from_role("security-manager", {"push": True, "pull": True}) == "push"
    assert perm_from_role(None, {"pull": True}) == "pull"


def test_collect_team(gh):
    gh.s.add("/orgs/o/teams/t/members", FakeResponse(200, [{"login": "alice"}, {"login": "bob"}]))
    gh.s.add("/orgs/o/teams/t/members", FakeResponse(200, [{"login": "bob"}]), params={"role": "maintainer"})
    gh.s.add(
        "/orgs/o/teams/t/repos",
        FakeResponse(
            200,
            [
                {"name": "r1", "owner": {"login": "o"}, "role_name": "write", "permissions": {}},
                {"name": "r2", "owner": {"login": "o"}, "role_name": "custom", "permissions": {"admin": True}},
                {"name": "foreign", "owner": {"login": "other"}, "role_name": "admin", "permissions": {}},
            ],
        ),
    )
    t = collect_team(gh, "o", {"slug": "t", "name": "Team T", "privacy": "closed", "parent": {"slug": "p"}})
    assert t["slug"] == "t"
    assert t["parent"] == "p"
    assert t["description"] == ""
    assert t["members"] == [{"login": "alice", "role": "member"}, {"login": "bob", "role": "maintainer"}]
    assert t["repos"] == {"r1": "push", "r2": "admin"}


def _repo(**kw):
    base = {
        "name": "r",
        "private": True,
        "default_branch": "main",
        "archived": False,
        "pushed_at": "2026-01-02T03:04:05Z",
    }
    base.update(kw)
    return base


def test_collect_repo_with_codeowners_and_collaborators(gh):
    content = base64.b64encode(b"* @o/t1 @carol\n").decode()
    gh.s.add(
        "/repos/o/r/contents/CODEOWNERS",
        FakeResponse(200, {"encoding": "base64", "content": content}),
        params={"ref": "main"},
    )
    gh.s.add(
        "/repos/o/r/collaborators",
        FakeResponse(200, [{"login": "dave", "permissions": {"admin": True}}]),
        params={"affiliation": "direct"},
    )
    r = collect_repo(gh, "o", _repo(visibility="internal"), {"t1": "push", "t2": "pull"})
    assert r["visibility"] == "internal"
    assert r["team_perms"] == {"t1": "push", "t2": "pull"}
    assert r["codeowners_path"] == "CODEOWNERS"
    assert r["codeowners_teams"] == ["t1"]
    assert r["codeowners_users"] == ["carol"]
    assert r["collaborators"] == [("dave", "admin")]
    assert r["pushed_at"] == "2026-01-02T03:04:05Z"


def test_collect_repo_visibility_fallback_and_missing_endpoints(gh):
    # no CODEOWNERS, collaborators 404 (no admin) -> empty, no exception
    r = collect_repo(gh, "o", _repo(private=False), {})
    assert r["visibility"] == "public"
    assert r["codeowners_path"] is None
    assert r["codeowners_teams"] == []
    assert r["collaborators"] == []


def test_collect_repo_codeowners_server_error_is_tolerated(gh, capsys):
    gh.s.add("/repos/o/r/contents/CODEOWNERS", FakeResponse(500, {}), params={"ref": "main"})
    r = collect_repo(gh, "o", _repo(), {})
    assert r["codeowners_path"] is None
    assert "CODEOWNERS fetch failed" in capsys.readouterr().err
