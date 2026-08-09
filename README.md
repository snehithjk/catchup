# catchup

`catchup` is a local-first CLI for comprehension debt: it tells one engineer which recent git changes invalidate what they personally knew about a codebase.

```sh
python3 -m pip install .
catchup --repo . --me you@example.com --since 30d
```

For a checkout without installing:

```sh
PYTHONPATH=src python3 -m catchup --repo . --me you@example.com --since 30d
```

The offline renderer is deterministic and needs no credentials. To use the optional LLM edge, set `CATCHUP_API_KEY` (and optionally `CATCHUP_API_URL` and `CATCHUP_MODEL`) and add `--llm`. Only selected diff context is sent to that configured endpoint; git inspection, exposure modeling, ranking, and grounding stay local.

Useful commands:

```sh
make test
make eval
make demo
PYTHONPATH=src python3 -m catchup mark <item-id> knew|new|irrelevant --repo .
```

The pinned public-repository backtest is documented in
[`docs/real-evaluation.md`](docs/real-evaluation.md). After downloading its
ignored fixtures, run `PYTHONPATH=src python3 scripts/real_eval.py`.

The brief is intentionally small. It ranks changes with exposure overlap, module fan-in, novelty signals, and feedback nudges. Each generated sentence must cite a commit, and the verifier checks that cited commits exist and that explicit paths/symbols appear in their diffs.

## Current milestone

The first implementation covers the verifier/eval harness, synthetic backtest, exposure map, change ingestion, deterministic ranking, offline brief, optional model edge, and feedback storage. The brief now shows the historical exposure evidence that made each item personal, and feedback carries forward by path prefix. `make eval` is the reproducible smoke test:

```text
synthetic precision=0.50 recall=1.00 grounding=1.00 noise=0.20 items=2
```

These precision and recall values are directional proxies, not proof that a human comprehended the change. Real-repository fixtures should be pinned before being used for comparison.

## Known limitation

Authorship is treated as evidence of exposure even though AI-assisted authorship no longer guarantees understanding. The authored/reviewed basis weights are configurable (`1.0` and `0.6` by default) so this assumption can be tuned and measured.

## Scope

The v1 boundary is intentionally strict: local git only, flat `.catchup/` files, one optional LLM API boundary, and no web UI, GitHub App, webhook, database, team features, Slack, editor plugin, daemon, or non-git VCS.

MIT licensed.
