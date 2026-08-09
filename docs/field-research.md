# Field research: the personal re-entry layer

Research run: 2026-08-08. Reddit is treated as anecdotal practitioner
evidence, not as a representative survey. The engineering sources are used
to extract design patterns, not to claim that any company has built Catchup.

## What engineers are asking for

The recurring pain is not “write code faster.” It is restoring a working model
after interruption, navigating a codebase that has changed faster than a human
can read it, and deciding whether an AI-produced change is actually understood.

- A recent [ExperiencedDevs discussion about context switching](https://www.reddit.com/r/ExperiencedDevs/comments/1suto7c/managing_super_frequent_context_switching/)
  describes the cost of tracking several blocked and unblocked work threads and
  the burden of maintaining notes.
- A tech-lead thread, [I can't keep up with the codebase I own](https://www.reddit.com/r/ExperiencedDevs/comments/1m3h35t/i_cant_keep_up_with_the_codebase_i_own/),
  describes AI-driven code volume outrunning architectural understanding and
  review capacity.
- Discussions about AI-generated code repeatedly converge on a practical
  standard: the author must be able to explain the change, the PR must stay
  reviewable, and the human must retain ownership of the result.

This supports the original wedge: Catchup should be a small re-entry ritual,
not another chat window or a giant repository encyclopedia.

## What large engineering organizations reveal

### Google: search and targeting before generation

Google reports that engineers use code search heavily to answer what an API
does, how to use it, why something fails, and where code is located. Their
large-scale migration workflow separates targeting, edit generation and
validation, and review/rollout. Code Search and Kythe identify a tight set of
locations and dependencies before the model is asked to edit.

Lessons for Catchup:

1. Start from a change or question and retrieve the narrowest useful evidence.
2. Make targeting explainable: show the paths, symbols, and dependency edges.
3. Keep generation separate from validation and human review.

Sources: [Google code-search study](https://research.google/pubs/how-developers-search-for-code-a-case-study/),
[AI code migrations](https://research.google/blog/accelerating-code-migrations-with-ai/).

### Meta: a durable semantic index plus diff sketches

Meta's open-source [Glean](https://engineering.fb.com/2024/12/19/developer-tools/glean-open-source-code-indexing/)
supports repository-wide symbol search, cross-language navigation, call
hierarchies, documentation, and code-review integrations. It also indexes
diffs into machine-readable “diff sketches” that can drive notifications,
static analysis, and semantic search over commits.

Lessons for Catchup:

1. Move from path overlap toward stable symbol IDs and source spans.
2. Treat a change as a structured event, not only as a patch and subject.
3. Make the graph available in the review surface and editor, not only in a CLI.

Meta also described a 2026 internal system that generated concise, opt-in
context files for tribal knowledge. Its design used five questions per module,
critic passes, stale-reference checks, and short “compass, not encyclopedia”
guides.

Source: [Meta tribal-knowledge mapping](https://engineering.fb.com/2026/04/06/developer-tools/how-meta-used-ai-to-map-tribal-knowledge-in-large-scale-data-pipelines/).

### GitHub: repository-scoped, cited, expiring memory

GitHub's public Copilot memory is the closest adjacent product. Its memories
are repository-scoped, cited, verified against the current codebase, shared
across coding agent, CLI, and code review, and automatically expired after 28
days. Their example stores a cross-file invariant such as “these API versions
must stay synchronized,” with file-and-line citations.

Lessons for Catchup:

1. Store facts, not vague summaries.
2. Attach every fact to citations and revalidate it before use.
3. Give memories a freshness policy and let users inspect/delete them.
4. Share one memory layer across re-entry, review, and coding workflows.

Sources: [GitHub agentic memory](https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/),
[Copilot memory changelog](https://github.blog/changelog/2026-03-04-copilot-memory-now-on-by-default-for-pro-and-pro-users-in-public-preview/).

## What to build next

### Now: make the personal loop habitual

- zero-config identity detection;
- `--since last` for resuming interrupted work;
- a five-item default brief with a concrete “read this first” path;
- `catchup remember` for a human-authored fact tied to commit/path citations;
- visible `knew`, `new`, and `irrelevant` feedback with an inspectable history.

### Next: make the evidence more semantic

- tree-sitter or language-server adapters for Python and TypeScript;
- stable symbol IDs and source spans;
- changed-symbol and call-graph deltas;
- detected invariants such as “update these files together”;
- freshness checks that invalidate memories when cited symbols move or change.

### Distribution: meet engineers where they already work

1. CLI first: `catchup` must be useful in under 10 seconds.
2. Editor action: “Catch me up on this file/function.”
3. PR comment: “What changed here that this reviewer is likely to miss?”
4. Optional daily digest, never a noisy notification stream.
5. Hosted SaaS only after the local workflow earns repeat usage.

## Product judgment

There is evidence of real demand, but no public evidence that a large company
has shipped this exact personal re-entry product. Instead, the category is
being assembled from adjacent systems: code search, semantic indexing, AI code
review, repository memory, and tribal-knowledge maps.

That is good news for Catchup. The open-source opportunity is a neutral,
local-first layer that works across AI vendors and code hosts. The SaaS
opportunity is a privacy-preserving sync and integration layer around that
core, not a hosted copy of every repository.

The moat should be the user's validated, longitudinal knowledge graph:
what they touched, what they confirmed, what they forgot, what changed around
their work, and which repository facts stayed true over time.
