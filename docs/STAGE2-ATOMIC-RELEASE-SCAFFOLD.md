# Stage 2 — Atomic Installation, Update and Rollback

Status: **COMPLETE — 100%**

Stage 2 provides Thrilla with a tested atomic release system for local
installation, updates, activation and rollback.

## Completed capabilities

- deterministic dated release IDs;
- isolated release directories;
- source-tree copying;
- exclusion of `.git`, caches, bytecode and virtual environments;
- atomic release manifests;
- refusal to overwrite an existing release;
- cleanup of incomplete candidates;
- pre-activation Python compilation;
- pre-activation automated test execution;
- validated-release state;
- atomic `current` release pointer;
- atomic `previous` release pointer;
- startup proof before accepting activation;
- automatic restoration after failed activation;
- restoration of both current and previous pointers after failure;
- previous-release manifest tracking;
- explicit rollback;
- exclusive update locking;
- stale-lock detection and recovery;
- protection against concurrent release mutation;
- release inventory/status;
- retention/pruning while protecting active and previous releases;
- stable POSIX launcher;
- stable Windows launcher generation;
- launcher symlink replacement without overwriting the symlink target;
- launcher isolation from the development checkout;
- shared release/application state root;
- release CLI:
  - `release status`
  - `release install`
  - `release rollback`
  - `release prune`
- Termux atomic installer;
- Windows atomic installer implementation;
- preservation of the previous launcher during migration;
- real Android/Termux atomic installation proof;
- real Android/Termux second-release update proof;
- real Android/Termux rollback proof.

## Verified Android / Termux proof

Two real releases were installed:

- `20260813-221521-e62c3521cd61`
- `20260813-221703-e62c3521cd61`

Before rollback:

    current  = 20260813-221703-e62c3521cd61
    previous = 20260813-221521-e62c3521cd61

After rollback:

    current  = 20260813-221521-e62c3521cd61
    previous = 20260813-221703-e62c3521cd61

The phone printed:

    PASS: REAL PHONE ATOMIC ROLLBACK

The rolled-back installation then passed:

    thrilla --version
    thrilla doctor --no-model

## Automated verification

The complete regression suite passed on Android/Termux:

    Ran 62 tests
    OK

The suite covers release staging, validation, activation, pointer management,
rollback, automatic failed-activation recovery, locking, stale-lock recovery,
retention, POSIX launcher isolation, Windows launcher generation, installer
integration and failure paths.

`git diff --check` also passed.

## Safety properties

A candidate cannot become active until its compilation and tests pass.

A failed candidate does not replace the working release.

A failed post-activation startup proof restores the prior release state.

Rollback proves the target release can start before switching to it.

Concurrent release mutations are rejected.

A stale update lock may be recovered only when its recorded owner is no
longer running.

The stable launcher follows the active release pointer instead of importing
the development checkout.

Existing launcher symlinks are replaced without overwriting their targets.

## Platform status

Android / Termux installation, update and rollback are verified on the real
target phone.

The Windows installer and stable launcher are implemented and covered by
automated generation/behavior tests. Full execution on the target Windows
machine remains part of later cross-platform target-device verification and
does not block completion of the Stage-2 atomic release architecture.

## Completion decision

Stage 2 is complete.

Further changes to installation/update behavior are maintenance or future
features, not unfinished Stage-2 foundation work.
