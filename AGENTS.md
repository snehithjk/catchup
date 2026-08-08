# AGENTS.md

## Mission

Build `catchup` as a small, local-first Python CLI that reports changes likely to invalidate one developer’s knowledge of a git repository. Personalization, deterministic ranking, and citation grounding are product requirements.

## Working rules

- Read `PLAN.md` and `STATE.md` before continuing work. If `STATE.md` is absent, create it only at the end of the first completed milestone.
- Implement the milestones in order: verifier/eval first, then exposure, ingestion/ranking, LLM generation, feedback, and polish.
- Keep deterministic logic in typed, independently testable functions. Use the LLM only for summarization and novelty tagging at the edges.
- Every brief sentence must cite a commit hash or PR number. The script verifier must reject unknown citations and claims about paths/symbols absent from the cited diff.
- Core production code must remain at or below 1,500 LOC, excluding tests and fixtures. Check this before each milestone handoff.
- Preserve append-only and inspectable state in `.catchup/`; never add a database or daemon.

## Scope exclusions

Do not build a GitHub App, webhook, web UI, database, team feature, Slack integration, editor plugin, daemon, or non-git VCS support. Do not add telemetry. Do not transmit repository contents except the selected, explicitly configured LLM request.

## Commands

Once scaffolded, the canonical commands are:

```sh
make test
make eval
```

Use the project’s documented `uv`/`pytest` commands when invoking individual tests. Run the synthetic eval offline; real-repository evals must identify their pinned fixture commit. Run a CLI smoke test before a milestone handoff.

## Fixtures and evals

- Generate the synthetic git fixture from its script; do not hand-edit generated history.
- Keep real fixture URLs, licenses, and pinned commits in a manifest.
- Any change to ranking or generation must include before/after scoreboard lines in the conventional commit message.
- Never weaken an eval to make a metric improve. If a metric regresses twice consecutively, stop the self-improvement loop and document the dead end in `STATE.md`.

## Git and review

- Use conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- Each milestone ends with green tests, an eval run, one concise `STATE.md` entry, and one commit.
- Review diffs for conformance to `PLAN.md`, anti-scope violations, core LOC, and grounding-checker coverage.
- Preserve unrelated user changes. Do not reset or discard worktree changes without explicit approval.

## Escalation

Stop and ask the human before changing the public CLI, adding credentials beyond the single LLM API key, adding a dependency with a non-permissive license, accepting a metric regression twice, or deciding the anti-scope list is wrong. Record the reasoning in writing rather than silently expanding scope.

