# catchup plan

## Product boundary

`catchup` is a local-first CLI that builds a developer-specific knowledge map from git history, ranks later changes by how much they threaten that knowledge, and emits a short grounded Markdown brief. Git is the source of truth. Flat files under `.catchup/` hold generated state and feedback. The only network boundary is the explicitly configured LLM API call in the brief-generation stage.

The v1 core will stay at or below 1,500 non-test LOC. No web UI, database, GitHub App, webhook, team feature, Slack integration, editor plugin, daemon, or non-git VCS support is planned.

## Language and runtime

Use Python 3.9+ and package the CLI for `uvx`/`pip` installation. The implementation stays compatible with the older Python available in the development environment while using only standard-library features.

Python is the best fit for this first version because the core is mostly subprocess-based git inspection, deterministic text/diff processing, and small pure functions. The standard library covers process execution, JSONL, dataclasses, timestamps, and path handling; keeping dependencies minimal makes local-first behavior and licensing easier to audit. Python also lets the evaluator run identically in CI and from a checkout. The import graph will use deliberately small language-specific parsers for Python and JS/TS rather than bringing in a heavyweight compiler stack.

## Architecture

The public CLI is a thin orchestration layer over four typed, deterministic stages:

1. **Exposure model** — run local git commands filtered by one or more email identities; apply configurable time decay and authored/reviewed basis weights; write `.catchup/knowledge-map.json`.
2. **Change ingestion** — read commits in the requested window, group at merge boundaries where available, extract paths/stats, dependency deltas, and cheap public-signature changes.
3. **Relevance ranking** — combine exposure overlap, module-neighbor credit, import-graph fan-in, path fallback distance, deterministic novelty multipliers, and feedback nudges into a ranked list.
4. **Brief generation** — send only selected diff context, exposure context, and grounding metadata to the configured LLM; require 2–4 cited sentences per item; run the verifier before output.

The verifier is a separate deterministic module and is built first. It validates every citation against a real commit and every mentioned path/symbol against that commit’s diff. Generation fails closed if a sentence is uncited, cites an unknown hash/PR, or mentions unsupported change detail.

Planned core modules:

```text
src/catchup/
  cli.py          # argument parsing and command orchestration only
  git.py          # narrow, checked subprocess wrappers
  models.py       # dataclasses / typed stage inputs and outputs
  exposure.py     # stage (a)
  changes.py      # stage (b)
  graph.py        # Python + JS/TS import graph and fallbacks
  ranking.py      # stage (c), including feedback nudges
  brief.py        # stage (d) provider boundary and prompt assembly
  verify.py       # citation and diff-grounding checker
  storage.py      # .catchup JSON/JSONL files
```

Pure stages will accept explicit values and a git adapter rather than reading process globals. Git output formats will be machine-oriented (`--format`, NUL delimiters where useful), with errors converted into typed failures. The LLM provider will be the only replaceable impure edge; tests will use a deterministic stub.

## Milestones and exit criteria

### M1 — verifier, synthetic fixture, and eval harness

Build the scripted synthetic repository, fixture manifest/ground truth, citation checker, and `make eval`. Include cases for valid citations, missing citations, unknown commits, and mentioned paths/symbols absent from a cited diff. Add a deterministic stub brief so the harness runs without credentials.

Exit criteria:

- `make test` is green from a clean checkout.
- `make eval` prints one scoreboard line for the synthetic fixture and fails on grounding below 100%.
- Fixture history contains known authors, a contract-breaking change, a later fix/revert, and expected personalized targets.
- The verifier is tested independently and no product feature is required for it to run.

### M2 — exposure model

Implement identity-filtered history, authored commits, merge-commit/review evidence, trailers, timestamp decay, configurable half-life, basis weights, and `.catchup/knowledge-map.json`. Add unit tests against the synthetic history, including empty history and multiple identities.

Exit criteria:

- Exposure output is deterministic and contains score, last-seen date, and basis per path.
- Default authored/reviewed weights are 1.0/0.6 and default half-life is 90 days.
- Tests demonstrate that newer exposure outranks equally weighted older exposure.
- Core LOC remains within the 1,500-LOC budget.

### M3 — ingestion and ranking

Implement windowed commit/change ingestion, merge-boundary grouping, diff stats, dependency/import deltas, cheap signature detection, Python and JS/TS import graphs, path-distance fallback, novelty multipliers, and top-N selection. Run the end-to-end harness with the stub generator.

Exit criteria:

- The synthetic backtest produces a stable ranked list with the known contract-breaking change surfaced for the relevant user.
- Changes outside the user’s exposed areas collapse into one accurate remainder line.
- Ranking tests cover zero exposure, neighbor credit, fan-in, novelty, ties, and deterministic ordering.
- The eval scoreboard includes proxy precision, proxy recall, grounding, and noise.

### M4 — LLM brief generation and citation enforcement

Add the provider interface, environment/configuration for one LLM API, intelligent diff truncation with exposed files prioritized, prompt construction, response parsing, citation enforcement, and a real-repo backtest. Keep the stub path for offline CI.

Exit criteria:

- Every emitted sentence carries a citation and passes the script verifier.
- Unknown or ungrounded model output is rejected rather than repaired speculatively.
- A real fixture generates a brief without transmitting unrelated repository content.
- README records the first real scoreboard and the model/API setup.

### M5 — feedback and weight nudges

Implement `catchup mark <item> knew|new|irrelevant`, append-only `.catchup/feedback.jsonl`, stable item identifiers, and simple per-basis/per-path-prefix ranking nudges. Keep feedback bounded and inspectable.

Exit criteria:

- Feedback survives repeated runs and malformed lines do not corrupt prior entries.
- A synthetic before/after eval demonstrates the intended score delta for marked feedback.
- No ML or hidden persistent service is introduced.

### M6 — stranger-ready polish

Finish the README with the install one-liner, privacy boundary, limitation notes, real example brief, CLI help, fixture/eval instructions, and demo GIF script. Add packaging metadata and a clean-checkout smoke test.

Exit criteria:

- A stranger with Python and an API key can install and run the documented command in under five minutes on a contributed repository.
- `catchup --help` and subcommand help are concise and accurate.
- `make test` and `make eval` reproduce the README scoreboard.
- Running catchup on its own repository produces a coherent grounded brief.

## Evaluation and fixture policy

The synthetic repository is generated from a script so its history is reproducible. Real fixtures will be cloned only when explicitly preparing eval data, recorded in a manifest with repository URL, license, and pinned commit. Initial candidates are permissively licensed public repositories with substantial contributor history; verify current license and suitability at acquisition time before pinning.

For each real-repo backtest, build the selected contributor’s map only before cutoff `T`, generate for `T` through `T+30d`, and score against later activity. Report proxy precision, proxy recall, grounding, and noise. These are directional proxies, not proof of comprehension; the README must say so.

Every ranking or generation change gets a before/after `make eval` scoreboard in its conventional commit message. After M6, the self-improvement loop is limited to three iterations per session, stops after two consecutive metric regressions, and never changes the evaluator to improve a score.

## Public interface decisions

The initial interface follows the spec:

```text
catchup --repo PATH --me EMAIL[,EMAIL...] --since WINDOW [--top N]
catchup mark ITEM_ID knew|new|irrelevant
```

Add only flags required for determinism, configuration, and inspectability. Any change to this interface, a new credential requirement, or a dependency with a non-permissive license is an escalation point requiring human review.
