# CATCHUP — Agent Build Spec (paste this whole file as your kickoff prompt)

Working name: **catchup** (rename freely). License: MIT. This file is the contract. Read fully before writing any code.

---

## 1\. Mission

Build a local-first CLI that fights **comprehension debt**: it tells one developer what merged into a git repo that *invalidates what they personally knew*, and nothing else.

One-liner: `catchup --repo . --me snehith@example.com --since 30d` → a ranked, cited markdown brief: "here's what changed in the parts of this codebase you knew, in order of how much it should worry you."

The product is **not** a changelog, not a PR summarizer, not a review bot. Those exist. The unit of value is the delta between the repo and one person's mental model. Personalization is the product. A brief that could have been generated for anyone is a failed brief.

## 2\. Non-negotiable principles

1. **Determinism first.** The knowledge model, relevance ranking, and blast-radius computation are plain, tested, deterministic code. The LLM is used ONLY at the edges: summarizing already-selected changes and tagging novelty. If a step can be done without a model call, it must be.  
2. **Grounding is absolute.** Every sentence in a brief must carry a citation to a commit hash or PR number. A script (not a model) verifies every cited hash exists and every mentioned file/symbol appears in that commit's diff. Zero uncited claims. Zero hallucinated changes. This check runs in CI and blocks merges.  
3. **Comprehensibility budget.** This tool exists because AI code outruns human understanding. It must not become an example of the disease. Hard budget: **v1 core ≤ 1,500 LOC** (excluding tests/fixtures). If a milestone would exceed it, cut scope, not corners. The human must be able to read the whole core in one sitting.  
4. **Local-first, privacy-clean.** Reads local git only. Network calls: LLM API and cloning the public fixture repos. Never transmits repo contents anywhere except the configured LLM API. No telemetry.  
5. **Anti-scope (hard NOs for v1):** no GitHub App, no webhooks, no web UI, no database (flat files in `.catchup/`), no team features, no Slack integration, no editor plugin, no support for non-git VCS, no daemon. Each of these is a future milestone at most. If you find yourself building any of them, stop and re-read this file.

## 3\. Architecture (v1)

Language: your choice between **TypeScript (Node, npx-runnable)** or **Python (uvx-runnable)** — pick for one-command install and best git tooling; justify choice in PLAN.md. Shell out to `git` rather than heavy libraries where practical.

Pipeline, four stages, each a pure function with typed I/O, each independently testable:

**(a) Exposure model → knowledge map.** From `git log` filtered by the user's email(s): files authored, files reviewed (merge commits, `Co-authored-by`, optional `Reviewed-by` trailers), commit timestamps. Compute per-file **exposure score** with time decay (half-life configurable, default 90 days). Output: `knowledge-map.json` — per path: score, last-seen date, basis (authored/reviewed). Design note: in the AI era authorship no longer implies understanding; keep basis-weights configurable (`authored: 1.0, reviewed: 0.6` defaults) so this assumption is tunable, and record it as a known limitation in README.

**(b) Change ingestion.** All merged commits in the window (`--since`), grouped into logical changes (merge-commit boundaries where available, else per-commit). Extract: touched paths, diff stats, new/removed dependencies (lockfile \+ import deltas), changed public signatures where cheaply parseable.

**(c) Relevance ranking.** For each change: `score = exposure_overlap × blast_radius × novelty`

- exposure\_overlap: sum of the user's exposure scores over touched paths (plus decayed neighbor credit within same module).  
- blast\_radius: cheap proxy in v1 — files touched × fan-in of touched modules from the import graph (build import graph for JS/TS and Python only in v1; other languages fall back to path distance).  
- novelty: deterministic flags (new dependency, new top-level module, deleted module, signature change in a file the user has exposure to), each a multiplier. Output: ranked list, top N (default 10\) pass to stage (d). Everything else is one summary line: "42 other changes in areas you never touched."

**(d) Brief generation (LLM).** For each selected change: model receives the diff (truncated intelligently — headers, hunks in files with user exposure prioritized), the user's exposure basis for the touched area, and writes 2–4 sentences: what changed, why it invalidates what this user knew, what they'd break if they acted on stale knowledge. Every sentence cited `(abc1234)`. Tone: a sharp colleague, not a press release. Feedback: `catchup mark <item> knew|new|irrelevant` appends to `.catchup/feedback.jsonl`; ranking weights consume it (simple per-basis/per-path-prefix weight nudges — no ML in v1).

## 4\. The verifier (build this FIRST, before features)

The tool's claim — "the brief surfaces what you needed to know" — is backtestable. This eval harness is milestone 1, not an afterthought, because it is what lets you self-improve without the human.

**Backtest protocol:**

1. Fixtures: (i) `fixtures/synthetic/` — a scripted small repo whose history you generate (known authors, known contract-breaking changes, known ground truth of what each fake user "should" be told); (ii) two cloned public repos with long history and many contributors (pick medium-sized, active, permissively licensed ones; pin to a commit).  
2. For a real repo: choose a past contributor identity C and cutoff date T. Build C's knowledge map from history **before** T only. Generate the brief for window T → T+30d.  
3. Score against what actually happened **after** T+30d:  
   - **Proxy precision**: fraction of brief items whose touched areas intersect files C subsequently modified, or that were later reverted/hotfixed (`git log --grep` for revert/fix references).  
   - **Proxy recall**: fraction of C's post-window activity areas that had in-window changes which the brief surfaced.  
   - **Grounding score**: % of sentences passing the citation checker (target: 100%, hard fail below).  
   - **Noise score**: brief length vs. N cap (briefs that sprawl fail).  
4. `make eval` prints one scoreboard line per fixture. Every PR/commit that touches ranking or generation must include before/after scoreboard in its message.

These proxies are imperfect — say so in README — but they are directional, automatic, and cheap. That's what a verifier needs to be.

## 5\. Process contract (how you work)

**Phase 0 (before any code):** produce `PLAN.md` (architecture decisions \+ milestone breakdown with exit criteria) and `AGENTS.md` (conventions: how to run tests, how to run evals, commit format, the anti-scope list, the LOC budget, the escalation rules below). Then STOP and wait for one human review of PLAN.md. This is the human's single mandatory intervention.

**Milestones (each ends with: tests green, evals run, conventional commit, one-paragraph entry in STATE.md):**

- M1: Eval harness \+ synthetic fixture \+ grounding checker (yes, before the product).  
- M2: Exposure model (a) with unit tests against synthetic fixture.  
- M3: Ingestion \+ ranking (b, c); backtest runs end-to-end with a stub generator.  
- M4: LLM brief generation (d) \+ citation enforcement; first real scoreboard.  
- M5: Feedback command \+ weight nudges; scoreboard delta demonstrated.  
- M6: Polish for strangers: README with a real example brief generated from a public fixture repo, install one-liner, `--help` that doesn't embarrass anyone, demo GIF script.

**Self-improvement loop (after M6, runs with minimal human input):** `run full evals → identify worst metric → propose the smallest change that could improve it (one paragraph in STATE.md) → implement → re-run → commit with metric delta`. Hard rules: max 3 loop iterations per session; if a metric regresses twice consecutively, stop and write up the dead end instead of thrashing; never "improve" a metric by weakening the eval.

**Context management:** keep AGENTS.md under 150 lines and stable. STATE.md is the running memory — after each milestone, compress what happened into ≤10 lines there so a fresh session can resume from AGENTS.md \+ PLAN.md \+ STATE.md alone, without replaying history. Never rely on conversation memory across sessions.

**Model usage:** use your strongest reasoning configuration for Phase 0, ranking-algorithm design, and the self-improvement "propose" step; use faster/cheaper configuration for bulk implementation, test writing, and fixture generation. Run a separate critic pass over each milestone's diff checking only: PLAN.md conformance, anti-scope violations, LOC budget, grounding-checker coverage.

**Escalate to the human (stop and ask) only when:** a decision changes the public CLI interface; a dependency with a non-permissive license would enter; evals regress twice; anything requires credentials beyond the one LLM API key; or you believe the anti-scope list is wrong (argue in writing, don't just violate it).

## 6\. Definition of done (v1)

A stranger with Node/Python and an API key can run one install command and, within 5 minutes, get a grounded, personalized, honest brief on any repo they've contributed to. `make eval` reproduces the scoreboard in the README. Core ≤ 1,500 LOC. Every brief sentence cited. The repo's own history is clean enough that catchup, run on itself, produces a coherent brief — which is also the standing demo: **the tool's first job is briefing its human on what its builder agent did overnight.**  
