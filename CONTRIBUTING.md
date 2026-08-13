# Contributing to Thrilla-zilla

Thrilla-zilla is at an early architecture and integration stage. Discussion, testing, design review, reproducible bug reports, and narrowly scoped implementations are useful now.

No project license has been selected yet. Do not assume that public visibility grants permission to redistribute Thrilla code. A license decision is required before outside code contributions can be accepted normally.

## Current priorities

1. Stable Android/Termux and Windows terminal behavior.
2. Automatic local-model lifecycle management.
3. A bounded agent loop with cancellation and visible limits.
4. A structured tool contract and safe file/Git/shell tools.
5. Checkpoints, validation, evaluation, and rollback.

The complete sequence is in [docs/ROADMAP.md](docs/ROADMAP.md).

## Donor-code rule

The repositories in `~/Thrilla-codebases` are study sources, not dependencies to merge wholesale. Before adapting any mechanism, record:

- repository and exact commit;
- files and behavior inspected;
- upstream license and compatibility finding;
- whether the Thrilla implementation is original, adapted, or copied;
- Thrilla-native interface affected;
- isolated and integration tests;
- correctness, security, speed, RAM, CPU, and maintainability measurements;
- final critic decision: keep or rollback.

Do not submit copied donor code without an explicit license and provenance record.

## Change requirements

Every behavior-changing patch should include:

- a concise explanation of the problem;
- a bounded implementation;
- regression tests;
- Python 3.9 grammar compatibility;
- no third-party runtime dependency unless justified;
- an update to documentation when behavior or limitations change.

Run:

```bash
python -m compileall -q thrilla tests
python -m unittest discover -s tests -v
```

For phone bugs, include the Android/Termux versions, terminal width, exact command, full traceback, and whether the local model was running.

