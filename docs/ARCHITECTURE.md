# Thrilla-zilla architecture

## System boundary

Thrilla-zilla owns its interfaces, policies, state, routing, execution gates, traces, and evaluations. The cloned repositories under `~/Thrilla-codebases` are a separate study library. Merely possessing a repository does not install it, license its code for reuse, or make its subsystem active.

## Target flow

```text
User interface
    → transparent request router
    → agent brain
        → model
        → memory
        → coder
        → tools / web
    → gated executor
        → Android / Termux
        → Windows
    → trace / security
    → evaluation
        → improvement: keep
        → regression: rollback
```

## Integration stages

| Stage | Deliverable | Gate |
|---|---|---|
| 0 | Colored UI, donor registry, router, local-model adapter, diagnostics, logs | Included in `0.1.0-alpha.2` |
| 1 | SQLite working/durable memory and source-aware retrieval | Migration, privacy, and retrieval tests |
| 2 | Read-only file/repository intelligence using language/build detection | Path-boundary and parser tests |
| 3 | Sandboxed tools and command execution | Exact action preview, policy, timeout, cancellation |
| 4 | Live/cached/archive research | Source, timestamp, citation, network, and privacy gates |
| 5 | Checkpointed coding and repair | Diff review, tests, compile/lint, rollback proof |
| 6 | Evaluation and controlled strengthening | Before/after benchmark and critic decision |
| 7 | Android and Windows control surfaces | Device-specific permission and recovery tests |

## Autonomy contract

Thrilla should minimize unnecessary interruptions, but autonomy is not permission to hide actions or bypass safety boundaries. Every state-changing operation needs a recorded scope, target, reason, timeout, result, and recovery path. High-risk actions remain gated. A failed or unavailable action must be reported as failed, never converted into a plausible-sounding success message.

## Behavioral priority

1. Accuracy and user safety
2. Reliability
3. Privacy
4. Transparency and accountability
5. Fairness
6. Adaptability
7. Efficiency
8. User-centered empathy

## Donor integration record

Each studied mechanism should eventually receive a record containing:

- donor repository and exact commit;
- files and behavior inspected;
- license and reuse determination;
- Thrilla-native interface affected;
- implementation provenance;
- tests and measurements before/after;
- security/privacy review;
- critic outcome: keep or rollback.
