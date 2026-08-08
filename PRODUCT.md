# Product direction

## The sharp wedge

Catchup is a personal re-entry layer for AI-accelerated software work.

The painful moment is not “what happened in the repository?” It is: “I am about to change this code based on a mental model that was true last week. What changed underneath me, and which part should I reread first?” A generic changelog cannot answer that because it does not know what the engineer previously touched, reviewed, or believed.

The initial habit is a two-minute re-entry brief before an engineer resumes work after being away, after an AI coding session, or before touching a risky subsystem.

## Three viable product shapes

### 1. Re-entry brief — build this first

Input: local repository, developer identity, time window.

Output: a ranked, cited list of changes that intersect the developer’s prior knowledge, with the stale assumption each change threatens. The current CLI is this version.

Why it wins: immediate value, low trust barrier, no team coordination, and the personalization is visible in every item. The success test is whether the brief changes what the engineer rereads or checks before editing.

### 2. Memory check — the deeper individual product

Before an engineer edits a path, Catchup asks for a lightweight “what do you think is true?” checkpoint, then compares that answer with recent history. It can say “your model is current,” “this API changed,” or “you are missing a new dependency.”

Why it matters: this turns a passive digest into an active human-in-the-loop loop. It is more defensible, but it needs a good interaction design and should come after the re-entry brief proves the ranking signal.

### 3. Change radar — the future team product

A local or CI service computes personalized risk views for each contributor after merges. The team sees no surveillance dashboard; each engineer gets a private “you should know this” feed.

Why it matters: distribution and recurring usage are stronger, but it crosses the current anti-scope into hosted state, identity management, and team trust. Do not build it in v1.

## Product principles

- Personalization must be falsifiable. A brief that looks identical for two engineers is a failed product case.
- The system should earn trust by showing why an item was selected: exposed file, exposure basis, novelty signal, and exact diff citation.
- Human feedback is product data, not a thumbs-up vanity metric. `knew`, `new`, and `irrelevant` should visibly change the next ranking.
- The model is a compression layer, never the source of truth. The source is the local diff.
- Privacy is a wedge. Local git inspection and explicit API boundaries make adoption possible in security-conscious engineering teams.

## Business shape

Start with an individual developer tool. A free local mode demonstrates value; a future paid layer could add encrypted personal history, scheduled briefs, or organization-managed model routing without exposing repository contents to Catchup. Team pricing only makes sense after the personal “this saved me from stale knowledge” moment is repeatable.

The likely moat is not the summary prompt. It is the accumulated personal knowledge graph, feedback history, and calibrated evidence of which changes actually mattered to a developer. That moat must remain exportable and inspectable so it does not become a surveillance or lock-in product.

## Metrics that matter

- **Personalized precision:** fraction of surfaced changes that intersect the engineer’s next edits, hotfixes, or explicit `new` feedback.
- **Stale-model catches:** cases where the brief causes a reread or prevents an incorrect edit.
- **Time to safe re-entry:** time from opening the brief to the engineer starting work confidently.
- **Feedback usefulness:** ranking delta after feedback, not raw feedback volume.
- **Trust:** grounding score must remain 100%; rejected or hallucinated claims are hard failures.

The next product iteration should make “why you” more explicit in each item before adding more repository coverage.

