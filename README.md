# gh-org-audit

[![CI](https://github.com/annejan/gh-org-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/annejan/gh-org-audit/actions/workflows/ci.yml)
[![REUSE status](https://api.reuse.software/badge/github.com/annejan/gh-org-audit)](https://api.reuse.software/info/github.com/annejan/gh-org-audit)

Dumps the authorisations of a GitHub organisation to one Excel workbook:
which teams can read or write which repository, who is in which team, and
which teams and people are listed in `CODEOWNERS`. For colleagues who speak
Excel, not API.

## Install

```
python3 -m venv .venv
.venv/bin/pip install .
```

Or run the single file `gh_org_audit.py` directly after
`pip install requests openpyxl`.

## Use

```
gh-org-audit minvws -o minvws-authorisations.xlsx
```

Options:

| Flag | Meaning |
|---|---|
| `-o FILE` | output path (default `<org>-authorisations-<date>.xlsx`) |
| `--token TOKEN` | GitHub token; otherwise `$GITHUB_TOKEN`, otherwise `gh auth token` |
| `-j N` | parallel API workers (default 8) |
| `--skip-archived` | leave archived repositories out |

The token needs the `read:org` and `repo` scopes. Membership of the
organisation is enough; owner rights are not required.

## Sheets

| Sheet | Content |
|---|---|
| Repos | per repo: archived, visibility, default branch, last push, teams per permission level, CODEOWNERS file, CODEOWNERS teams and users, direct collaborators |
| Matrix | repos × teams; cell = `A`/`M`/`W`/`T`/`R` (admin/maintain/write/triage/read), `+CO` when the team is also in CODEOWNERS |
| Teams | one row per (team, member), with maintainer/member role |
| Team summary | team, description, member count, repo counts per level |
| Members | reverse lookup: member → teams |
| Collaborators | users granted access directly on a repo, outside a team |
| Info | legend and caveats |

## Caveats

* Team permissions come from `/orgs/{org}/teams/{team}/repos`, which any
  org member can read. Secret teams you are not a member of are invisible
  and therefore missing. Run as an org owner for a complete picture.
* Direct collaborators can only be listed on repos where you have admin
  rights; elsewhere the column stays empty.
* `CODEOWNERS` is read from the default branch, from `CODEOWNERS`,
  `.github/CODEOWNERS` or `docs/CODEOWNERS` (first hit wins, like GitHub).

## Develop

```
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pytest
.venv/bin/reuse lint
```

## License

MIT, see [LICENSES/MIT.txt](LICENSES/MIT.txt). REUSE compliant.
