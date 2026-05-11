# Contributing

Thanks for considering a contribution. This project is small enough that you can read the whole codebase in an afternoon — please do, before opening a PR.

## Development setup

```bash
git clone https://github.com/mbkautomacoes/zyon.git
cd Allos
python -m venv .venv
. .venv/Scripts/activate    # Windows
. .venv/bin/activate        # Linux/macOS
pip install -e ".[dev]"
cp config.example.py config.py    # then edit
```

## Tests

```bash
pytest -q                     # full suite
pytest tests/test_xxx.py -v   # single file
pytest -k bootstrap           # by name
```

The CI workflow in `.github/workflows/ci.yml` runs the same suite on every push and PR. A red CI blocks merge.

## Style

- **Python**: standard library only where possible. We avoid runtime deps that are not strictly needed.
- **Tests**: pytest. Use `monkeypatch` for env / `subprocess` / `urllib`. Never hit the real megaAPI in tests.
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`. Scope optional (`feat(bootstrap): …`).
- **No emojis** in code, comments, or commit messages.
- **No comments** explaining what code does — only why, when non-obvious.

## Branch and PR flow

1. Open an issue first for non-trivial changes (use the templates in `.github/ISSUE_TEMPLATE/`).
2. Branch off `main`: `git checkout -b feat/your-thing`.
3. TDD where possible. Each commit should leave the suite green.
4. Open a PR. Fill in the template. Link the issue.
5. CI must pass. At least one maintainer review.

## Adding a new feature that touches Claude Code's prompt

`CLAUDE_PROMPT.md` is the source of truth for the agent's runtime contract. If you change it, also:

- Update `docs/API_CONTRACT.md` if the change touches the gateway HTTP contract.
- Add a test to `tests/test_webhook_parser.py` if you change the JSONL schema.
- Bump `CHANGELOG.md` under `[Unreleased]`.

## Releasing

Maintainers only:

```bash
git checkout main && git pull
# bump CHANGELOG: move [Unreleased] entries under a new version header
git commit -am "chore: release vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main vX.Y.Z
```

Create a GitHub release pointing to the tag with a copy of the CHANGELOG section.
