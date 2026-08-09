# Public-repository evaluation

This is a qualitative backtest, not a claim that a human's comprehension can be
measured from Git alone. Each scenario freezes one contributor's pre-cutoff
exposure, asks Catchup to rank the next window, and compares the top-N result
with changes that are explicitly documented in the repository's own changelog
or configuration documentation.

The clones are intentionally ignored from this repository. The tracked
[fixture manifest](../fixtures/real/manifest.json) records the source URL,
license, exact checkout, identity, time window, expected documented anchors,
and primary knowledge sources.

## Fixtures

| Fixture | Why it is useful | Source knowledge | Result |
| --- | --- | --- | --- |
| [HTTPX](https://github.com/encode/httpx) | Typed Python client with a detailed changelog and a concentrated 0.28 compatibility event | [official changelog](https://github.com/encode/httpx/blob/master/CHANGELOG.md), [HTTPX docs](https://www.python-httpx.org/) | Top 5 includes 2/2 documented anchors; grounded |
| [Flask](https://github.com/pallets/flask) | Mature framework with API deprecations, behavior changes, and frequent integration commits | [official changes](https://github.com/pallets/flask/blob/main/CHANGES.rst), [Flask docs](https://flask.palletsprojects.com/en/stable/) | Top 5 includes 2/2 documented API anchors; grounded |
| [Vite](https://github.com/vitejs/vite) | Large TypeScript monorepo with plugin, build-option, test, and package metadata surfaces | [official README](https://github.com/vitejs/vite#readme), [build options](https://vite.dev/config/build-options), [plugin API](https://vite.dev/guide/api-plugin) | Top 5 includes 2/2 documented option/plugin anchors; grounded |

Run the reproducible report after downloading the pinned checkouts:

```sh
mkdir -p fixtures/real
git clone --filter=blob:none --no-tags https://github.com/encode/httpx fixtures/real/httpx
git clone --filter=blob:none --no-tags https://github.com/pallets/flask fixtures/real/flask
git clone --filter=blob:none --no-tags https://github.com/vitejs/vite fixtures/real/vite
PYTHONPATH=src python3 scripts/real_eval.py
```

The report uses `top_n=5`. Its `documented_anchor_recall` is the fraction of
predeclared documented commits found in that list. `grounded` is a hard safety check:
every generated sentence must cite a real commit and mention only evidence
present in its diff. The unmatched top-N items are not automatically noise;
they are unlabelled changes that require human review.

## Engineering findings and fixes

### 1. History must be a closed world

The first real run used `git log --all ... HEAD`. A clone of HTTPX had 1,523
commits reachable from `HEAD` but 1,643 reachable from all fetched refs; Vite
had 9,554 versus 10,117. The extra remote branches polluted the window and
made the brief look more knowledgeable than it was. The Git adapter now walks
only the requested ref. A regression test creates an unmerged branch and
asserts that its file cannot enter the current-branch history.

This is analogous to compiling one selected source graph: inputs outside the
declared root are not silently linked into the program.

### 2. Separate integration nodes from semantic changes

Flask's history contains two-parent commits whose subjects are actual API
changes, such as `redirect defaults to 303 (#5898)`, alongside pure
`Merge branch 'stable'` nodes. Penalizing every two-parent commit hid real API
contracts; penalizing none let large integrations dominate. Catchup now
penalizes only merge-labeled integration subjects and keeps semantic PR merge
commits at full strength. The pure integration commit remains visible and
grounded, but direct contract changes rank above it.

### 3. Use a stable intermediate representation and provenance

The pipeline now has explicit stages: bounded history selection, exposure
map, change IR, boundary-tree import graph, ranking, brief rendering, and
verification. `Change`, `ExposureEntry`, and `RankedChange` carry the commit,
path, basis, and exposure citation that justify a result. The offline renderer
and tie-break order are deterministic. The optional model sees selected diffs
and evidence metadata, never the user's email identity.

The exact graph is read from `git archive` at the historical boundary commit,
not from the current worktree. This prevents a current file from becoming a
false explanation for an old change. Path metadata is collected in one Git
history walk, which made the large Vite run complete instead of timing out in
per-commit subprocess scans.

### 4. Treat context files differently from code

The public runs exposed a common failure mode: dependency locks, CI files,
release notes, and documentation can touch many paths and win by raw file
count. Exposure contributions now discount docs/readmes/changelogs and common
build or CI metadata. Import refactors are netted (`added - removed`) so a
move does not masquerade as a new dependency. This is intentionally a small,
conservative lexical pass rather than an imagined full semantic parser.

### 5. Make generation an evidence-carrying pass

An earlier truncation marker (`+N more`) could be mistaken for a path, and a
reason label containing a slash could be mistaken for a source reference. The
renderer now keeps summary markers outside code spans and uses stable reason
words. The verifier requires a citation and explicit diff evidence for every
non-aggregate sentence, and rejects fabricated claims. This is the equivalent
of a type/checking pass after code generation: unverified model prose cannot
escape as product output.

## Compiler-design lessons carried forward

The useful analogy is not “build a compiler for English.” It is the discipline
of a compiler pipeline:

1. define the input boundary and resolve it deterministically;
2. parse into a small typed IR instead of passing raw strings between phases;
3. preserve source provenance through every transformation;
4. make optimization/ranking deterministic and explainable;
5. emit only after a separate validation pass;
6. use golden fixtures and regression tests for every discovered counterexample.

The next high-value compiler-inspired step is an incremental cache keyed by
`(HEAD, cutoff, identities, options)` plus language-aware AST adapters for
Python and TypeScript. It should be added only after measuring cache hit rate
and parser false positives; the current conservative parser is easier to
trust.

## Limits of this evaluation

The expected anchors were selected by inspecting official repository history
and documentation, so this is a targeted smoke test rather than a blind
benchmark. Authorship is still only a proxy for personal understanding, and
the tool does not yet know whether a contributor actually read a change. The
real-repository results validate grounding, history selection, performance,
and several high-value ranking signals; they do not establish product-market
fit or human time saved.
