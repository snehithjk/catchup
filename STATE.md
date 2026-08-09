# State

- Phase 0 reviewed by implementation authority; Python 3.9+ and the four-stage local pipeline are documented in `PLAN.md`.
- M1-M3 implementation is in place: synthetic fixture, citation verifier, offline eval, exposure model, ingestion, import graph, ranking, feedback storage, and CLI.
- M4 edge is usable through an optional OpenAI-compatible provider; default generation remains deterministic and offline with exposed-file diff prioritization.
- Iteration 1 made “why you” explicit with prior/current citations, path-prefix feedback, HEAD-bounded history, historical-tree graphing, and symlink-safe state writes.
- Iteration 2 tightened explicit diff evidence, relative JS/TS graph resolution, model prompt privacy/HTTPS policy, and made the synthetic contract break plus eval denominators honest.
- Latest verification before the public-repository pass: 16 unit tests pass, synthetic precision is 0.50, recall 1.00, grounding 1.00, noise 0.20, and core LOC is 1062.
- Public-repository pass: pinned HTTPX, Flask, and Vite checkouts are recorded in `fixtures/real/manifest.json`; all three top-N reports matched 2/2 documented anchors and passed grounding. The pass found and fixed `git log --all` remote-branch pollution, historical-tree drift, import-move novelty, context-file over-weighting, and merge/integration ranking ambiguity. See `docs/real-evaluation.md`.
- Packaging smoke test builds and installs `catchup-0.1.0` successfully; no external runtime dependencies are required.
