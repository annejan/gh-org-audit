# SPDX-FileCopyrightText: 2026 Anne Jan Brouwer
# SPDX-License-Identifier: MIT

import base64

from gh_org_audit import fetch_codeowners, parse_codeowners
from tests.conftest import FakeResponse

SAMPLE = """\
# comment line
*             @minvws/team-a @minvws/team-b   # trailing comment
/docs/        @minvws/team-a @someone
/infra/**     @OtherOrg/ops  ops@example.org

/empty-owners
"""


def test_parse_teams_users_dedup_and_foreign_org():
    teams, users = parse_codeowners(SAMPLE, "minvws")
    assert teams == ["team-a", "team-b", "@OtherOrg/ops"]
    assert users == ["someone", "ops@example.org"]


def test_parse_org_match_is_case_insensitive():
    teams, _ = parse_codeowners("* @MinVWS/Team-X", "minvws")
    assert teams == ["Team-X"]


def test_parse_empty():
    assert parse_codeowners("", "minvws") == ([], [])
    assert parse_codeowners("# only comments\n\n", "minvws") == ([], [])


def test_fetch_tries_paths_in_order(gh):
    content = base64.b64encode(b"* @minvws/x\n").decode()
    gh.s.add(
        "/repos/minvws/r/contents/.github/CODEOWNERS",
        FakeResponse(200, {"encoding": "base64", "content": content}),
        params={"ref": "main"},
    )
    path, text = fetch_codeowners(gh, "minvws", "r", "main")
    assert path == ".github/CODEOWNERS"
    assert text == "* @minvws/x\n"
    # root CODEOWNERS was tried first and 404'd
    assert gh.s.calls[0][0] == "/repos/minvws/r/contents/CODEOWNERS"


def test_fetch_none_when_absent(gh):
    assert fetch_codeowners(gh, "minvws", "r", "main") == (None, None)
    assert len(gh.s.calls) == 3


def test_fetch_falls_back_to_download_url_for_large_files(gh):
    gh.s.add(
        "/repos/minvws/r/contents/CODEOWNERS",
        FakeResponse(200, {"encoding": "none", "content": "", "download_url": "https://raw.example/CODEOWNERS"}),
        params={"ref": "main"},
    )
    gh.s.add("/CODEOWNERS", FakeResponse(200, text="* @minvws/big\n"))
    assert fetch_codeowners(gh, "minvws", "r", "main") == ("CODEOWNERS", "* @minvws/big\n")
