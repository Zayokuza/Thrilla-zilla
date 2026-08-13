# Thrilla-zilla canonical project record

Last consolidated: 2026-08-12

This document is the clean public record compiled from the Thrilla design conversation, the source implemented in this repository, the donor manifest, and the Android/Termux readouts supplied during testing. It intentionally excludes unrelated project conversations and private chat material.

## Plain-language project statement

Thrilla-zilla is a local-first AI system being built to run primarily on Android through Termux and on Windows. The intended system should be able to talk, research, understand unfamiliar repositories, write and repair software, use tools, work with files and data, operate within device permissions, remember useful project context, and evaluate whether its own changes are actually improvements.

The project has a library of open-source repositories to study. Those repositories are donors and references. They are not one application, they are not automatically trusted, and they will not be merged into one enormous dependency tree.

The governing development loop is:

```text
inspect source
→ understand mechanism
→ check license
→ design Thrilla-native interface
→ implement or adapt narrowly
→ test independently
→ integrate
→ benchmark
→ critic evaluation
→ better: keep
→ worse: rollback
```

## Target architecture

```text
                         THRILLA-ZILLA
                               │
                          Agent Brain
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
           Model             Memory            Coder
             │                 │                 │
             └─────────┬───────┴────────┬────────┘
                       ▼                ▼
                     Tools             Web
                       │                │
                       └───────┬────────┘
                               ▼
                           Executor
                               │
                               ▼
                         Android/Windows
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                 Interface         Trace / Security
                                      │
                                      ▼
                                  Evaluation
                                      │
                              better → keep
                              worse  → rollback
```

## Core routes

The interface stays simple while internal routing remains visible:

1. General chat
2. Coding
3. Deep search and OSINT
4. Files and data
5. Device and system

The current deterministic router represents files, data, device, and system as separate internal routes so behavior can be tested and explained.

## Behavioral priorities

The ten selected traits are accuracy, transparency, fairness, user privacy, adaptability, reliability, user safety, accountability, user-centered empathy, and efficiency.

When these compete, the order is:

```text
accuracy + user safety
→ reliability
→ privacy
→ transparency + accountability
→ fairness
→ adaptability
→ efficiency
→ user-centered empathy
```

Thrilla must never turn an unavailable, cancelled, or failed action into a plausible-sounding success report.

## Donor-library structure

Phase 1 contains ten core categories with ten repositories each:

1. Agent brain, reasoning, and orchestration
2. Coding, self-repair, and repository modification
3. AI models, inference, and runtime
4. Language intelligence, compilers, and build systems
5. Memory, retrieval, knowledge, and state
6. Browser, research, crawling, and historical web
7. Tools, workflows, and automation
8. Android/Windows execution, operating systems, and sandboxes
9. Interface, API, and control plane
10. Evaluation, testing, security, and observability

The first three in every category form a priority layer of 30. The exact catalog is in [DONOR-LIBRARY.md](DONOR-LIBRARY.md) and in the executable `thrilla/catalog.py` source.

Phase 2 is a specialist/reference library intended to teach Thrilla broader engineering disciplines after the core system works. XTLS/Xray-core is currently its first verified networking/proxy/transport entry. The rest of Phase 2 has not been finalized and must avoid every Phase-1 duplicate.

## Device-reported donor status

The supplied phone transcript reported:

```text
Phase-1 Git repositories: 100 / 100
Clone failures:            0
Phase-1 footprint:         about 23 GB
Free space at completion:  about 61 GB
```

The supplied Xray-core verification reported:

```text
Repository: XTLS/Xray-core
Path:       ~/Thrilla-codebases/11-networking-proxy/01-xray-core
Branch:     main
Commit:     7d214f8
Status:     clean
Size:       8.7 MB
```

These are preserved as device-reported evidence. This build workspace cannot mount or independently rescan the phone filesystem.

## Current native implementation

The repository currently contains an early Thrilla-native control plane:

- compact interactive terminal menu;
- arrow-key selection and numeric fallback;
- cyan user input and green Thrilla output;
- distinct success, warning, error, accent, and muted colors;
- responsive compact layout for a phone terminal;
- `NO_COLOR` and plain non-terminal output;
- deterministic request routing with confidence and explanation;
- OpenAI-compatible local-model client suitable for llama.cpp;
- default rejection of remote model URLs to prevent accidental prompt disclosure;
- canonical catalog and read-only scan of the core 100 and priority 30;
- read-only per-repository Git inspection;
- local conversation history;
- separate metadata-only activity log;
- settings and diagnostics;
- Termux and Windows launchers/installers;
- Python 3.9-compatible, dependency-free runtime and tests.

This is a foundation. It is not yet the complete autonomous system described above.

## Missing core implementation

The following are still required:

- automatic model discovery, startup, shutdown, streaming, cancellation, and RAM/context control;
- bounded plan/action/observation/critic agent loop;
- structured tool schemas and capability registry;
- safety policies, permission boundaries, secrets handling, and destructive-action gates;
- safe file, shell, Git, process, compile, lint, and test tools;
- automatic checkpoints and rollback;
- repository/language/framework/build-system indexing;
- coding and repair agent;
- SQLite working memory, durable state, source metadata, and retrieval;
- live, cached, and archived research with citations and timestamps;
- execution isolation and resource limits;
- full trace, security, testing, benchmark, and regression evaluation;
- controlled keep-or-rollback improvement system;
- Android/Termux and Windows device adapters;
- atomic upgrades, configuration migration, crash recovery, and release rollback;
- complete Phase-2 specialist catalog and later donor studies.

## Definition of working

Thrilla should not be called fully working or version 1.0 merely because its menu launches. A 1.0 candidate must pass, on target hardware:

1. cold installation and upgrade from the prior release;
2. complete donor inventory;
3. automatic local-model startup and live conversation;
4. context/history continuity without unbounded growth;
5. file task with evidence;
6. unfamiliar-repository analysis;
7. checkpointed code repair followed by compile/test;
8. demonstrated rollback after a forced regression;
9. live research with citations plus cached/archive behavior;
10. command cancellation, Ctrl+C, timeout, and crash recovery;
11. security and path-boundary tests;
12. measured RAM, CPU, heat, latency, storage, and battery impact;
13. Android/Termux proof;
14. Windows proof;
15. no known menu item that silently fails.

## Public-project boundaries

- No license has been selected for Thrilla-zilla yet.
- Donor licenses must be reviewed individually before direct reuse.
- The raw recovered chat transcript is not part of the public repository.
- User prompts, credentials, device identifiers, and unrelated project records must not be committed.
- Reported device results are labeled separately from independently reproduced verification.

