# Stage 2 — Atomic Release Scaffold

Status: **ROUGH / intentionally below 50% complete**

Stage 2 establishes only the inactive foundation needed for safe future
installation, update and rollback work.

It MUST NOT interfere with normal Thrilla startup.

## Implemented

- deterministic dated release IDs;
- isolated release directories;
- inactive payload staging;
- source-tree copying;
- exclusion of `.git`, caches, bytecode and virtual environments;
- atomic candidate manifest writing;
- refusal to overwrite an existing candidate;
- cleanup of a partially-created candidate;
- manual-only invocation;
- tests proving staging does not touch a live launcher.

## Deliberately not implemented

The following are deferred:

- launcher activation;
- automatic update checking;
- automatic startup integration;
- active-release pointer;
- previous-release pointer;
- rollback execution;
- failed-activation recovery;
- pre-activation testing;
- live model/runtime validation;
- release locks;
- concurrent updater handling;
- remote downloads;
- package/signature verification;
- release channels;
- pruning/retention;
- Windows activation;
- Termux launcher replacement.

## Non-blocking invariant

Normal Thrilla does not import or execute `thrilla.release_stage`.

Failure inside the release-staging module therefore cannot prevent the
existing Thrilla application from starting.

A candidate remains:

    staged-inactive

until later Stage-2 work explicitly implements and tests activation.

## Future Stage-2 sequence

1. candidate validation;
2. candidate test runner;
3. release metadata validation;
4. activation pointer abstraction;
5. atomic pointer swap;
6. launcher indirection;
7. previous-release preservation;
8. health proof after activation;
9. automatic recovery;
10. explicit rollback;
11. Termux installation integration;
12. Windows installation integration;
13. concurrency locking;
14. release retention;
15. update transport.

Nothing in this scaffold performs those operations yet.
