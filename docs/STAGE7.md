# Stage 7 — Final capability development before v1.0.0

Stage 7 is Thrilla-zilla's final planned development stage before
release-candidate tuning and acceptance.

## Phase status

- **7A — Performance core: COMPLETE**
  - reusable repository source index
  - automatic per-file cache invalidation
  - verified runtime-client binding reuse
  - runtime binding invalidation after inference failure
  - runtime-manager replacement invalidates cached binding
  - shutdown clears cached binding

- **7B — Expanded structured tools: COMPLETE**
  - deterministic tool discovery/catalog
  - filesystem stat, glob and SHA-256 tools
  - dedicated read-only Git status and diff
  - executable PATH discovery
  - bounded repository unittest execution
  - all filesystem operations remain root-confined
  - generic structured tools still expose no unrestricted write primitive
- **7C — General autonomous task runner: COMPLETE**
  - model-planned multi-step structured-tool execution
  - explicit tool/finish JSON protocol
  - deterministic tool catalog exposed to planner
  - relative workspace path resolution
  - structured observation feedback after every action
  - failed tool observations return to the planner instead of becoming fake success
  - hard autonomous step ceiling
  - WRITE and NETWORK permissions excluded from the generic runner
  - autonomous tasks run through persistent background jobs
  - `/auto <goal>` command surface
  - active autonomous model work participates in Thrilla's model-contention guard
- **7D — Critic, replanning, budgets and recovery: COMPLETE**
  - independent critic gate before autonomous completion
  - critic can reject unsupported completion and force replanning
  - separate step and tool-call budgets
  - bounded replan budget
  - bounded tool-failure budget
  - bounded planner/critic protocol-error recovery
  - repeated-action loop detection and recovery
  - tool-failure classification for missing paths, permission failures, timeouts and path errors
  - owner directives feed directly into subsequent autonomous planning
  - autonomous audit records critic checks, replans, failures, protocol recoveries and loop blocks
  - Stage 7C behavior remains compatible when no critic is configured
- **7E — Autonomous research/coding/memory/tool integration: PENDING**
- **7F — Final tuning and release acceptance: INTENTIONALLY OPEN**

## v1.0.0 boundary

7F remains open for final optimization, target-device benchmarking,
Android/Termux and Windows acceptance, release-documentation review,
and final owner-approved tweaks.

No v1.0.0 tag or release is authorized merely by completing 7A–7E.
