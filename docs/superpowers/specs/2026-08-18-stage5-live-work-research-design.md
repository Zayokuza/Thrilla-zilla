# Thrilla Stage 5 Live Work, Research, and Self-Recovery Design

## Status

Approved owner direction for Stage 5.

Stage 5 builds on verified Stage-4 commit `0f5fd5d70d93abbd626825109c43041bf07a1163`.

Stage 5 does **not** make Thrilla `v1.0.0`. Thrilla may not claim, tag, merge, publish, or release `v1.0.0` unless the owner explicitly authorizes that version.

## Goal

Keep Thrilla fully conversational while autonomous work continues in the background, add evidence-backed web research with hybrid network autonomy, persist unfinished work safely across restarts, and provide explicit hold/communicate/continue controls without mixing execution telemetry into the conversation.

## Current architecture constraints

The Stage-4 application is a synchronous terminal application. `ThrillaApp.ask()` currently reads one prompt, runs routing and provider resolution, then blocks while model or repair work executes. The current terminal layer already supports Termux and Windows and owns terminal width, raw key reading, menu rendering, and compact fallback behavior.

Stage 5 must preserve:
- Stage 1 supervised local runtime and autonomous brain.
- Stage 2 exactly 100 experts and structured bounded tools.
- Stage 3 checkpointed autonomous coding with deterministic verification and automatic rollback on failure.
- Stage 4 durable hybrid memory, direct owner/self knowledge, conversation-history caching, and performance fast paths.
- Existing provider evidence-first behavior.
- Existing explicit software policy/limit controls.

## Architecture

Stage 5 uses an event-driven background job engine. The foreground owner-chat/control loop is independent from job execution. Long-running work runs in bounded workers and publishes structured state/events. The UI renders conversation and job telemetry separately.

```text
OWNER CHAT / CONTROL LOOP
        |
        +-- normal conversation remains available
        +-- 1.Hold
        +-- 2.Communicate
        +-- 3.Continue full
        +-- 0.Back
        |
        v
JOB MANAGER / PERSISTED JOB STATE
        |
        +-- research jobs
        +-- coding/repair jobs
        +-- verification jobs
        +-- workflow/recovery jobs
        |
        v
BOUNDED WORKERS -> STRUCTURED EVENTS -> RIGHT-SIDE WORK PANE
```

The model/runtime must never be the synchronization primitive for job control. Hold, resume, cancellation, state inspection, and persistence are deterministic local operations.

## Job model

Every long-running unit of work is represented by a persistent job record with at least:
- `job_id`
- `kind`
- `goal`
- `state`
- `priority`
- `current_step`
- `completed_steps`
- `total_steps` when known
- `progress`
- `started_at`
- `updated_at`
- `elapsed`
- `active_workers`
- `evidence_count`
- `last_action`
- `next_action`
- `error`
- `checkpoint`
- `owner_directives`
- `result`

Valid states are `queued`, `running`, `held`, `waiting`, `verifying`, `completed`, `failed`, and `cancelled`.

A job may transition to `completed` only after its completion condition is verified. Exceptions, process death, network failure, cancellation, or restart must never produce false success.

## Owner control semantics

During any active job the owner control surface is exactly:

```text
1.Hold
2.Communicate
3.Continue full
0.Back
```

### 1. Hold

`Hold` requests a cooperative pause. The active job finishes only the current indivisible/safety-critical operation, reaches the next safe checkpoint, persists its state, and enters `held`. It remains held until the owner explicitly resumes it. Hold must prevent new research fetches, model actions, file mutations, downloads, or workflow steps from starting after the safe checkpoint.

### 2. Communicate

`Communicate` keeps eligible background work running while the owner talks to Thrilla. The conversation path remains responsive and may inspect the current job state, answer unrelated questions, or accept additional directives. A directive relevant to the active job is appended to that job's owner-directive queue and is consumed at the next safe planning/checkpoint boundary.

The owner is never placed on hold merely because Thrilla is thinking, researching, coding, downloading, verifying, or recovering.

### 3. Continue full

`Continue full` sets the selected job to normal autonomous execution under the currently enabled permissions and policies. It resumes a held job and permits planning, read-only research, eligible downloads, tools, verification, bounded retry/replan, and recovery.

### 0. Back

`Back` exits the active-work control view. It does not silently pause, cancel, resume, reprioritize, or otherwise alter the active job.

## Split-pane terminal UI

Conversation and execution telemetry must never be interleaved.

On a sufficiently wide terminal:

```text
+---------------- LEFT: YOU + THRILLA ----------------+--------------- RIGHT: ACTIVE WORK ---------------+
| you> ...                                             | Job: research-0042                               |
| thrilla> ...                                         | State: RUNNING                                   |
|                                                      | Step: 4/9                                        |
| conversation only                                    | Sources: 6 verified                              |
|                                                      | Last action / next action / elapsed / errors      |
+------------------------------------------------------+---------------------------------------------------+
| 1.Hold   2.Communicate   3.Continue full   0.Back                                                        |
+----------------------------------------------------------------------------------------------------------+
```

The left pane contains only owner and Thrilla conversation. It must not contain scan logs, tool traces, download progress, verification spam, research fetch logs, or background stack traces.

The right pane contains only structured active-work telemetry: selected job, state, progress, current/next step, elapsed time, evidence count, last action, error/retry state, and related job metadata.

The right pane updates in place with a bounded refresh rate rather than appending repeated status lines.

When the terminal is too narrow for useful two-column rendering, Stage 5 automatically switches to compact stacked rendering:

```text
[CHAT]
you> ...
thrilla> ...

[ACTIVE WORK]
RUNNING | step 4/9 | verifying sources | 02:14

1.Hold  2.Communicate  3.Continue full  0.Back
```

The logical separation between conversation and work telemetry remains mandatory in compact mode.

## Foreground responsiveness

Chat/control must not block on a running job. Background job work therefore uses bounded threads for Stage 5 rather than running inside `ask()`.

Requirements:
- The owner input loop stays available while jobs run.
- Job state changes are synchronized with deterministic local locks/conditions.
- No worker may directly own or redraw the terminal.
- Workers publish events/state only; the foreground renderer owns presentation.
- A stuck network request must not freeze the chat loop.
- Worker count is bounded and configurable.
- Shutdown requests stop accepting new work, persist job state, and terminate or abandon workers safely without declaring unfinished jobs complete.

## Web research policy

Stage 5 uses hybrid network autonomy.

### Public read-only access

Thrilla may automatically use public internet access for read-only research when fresh or external evidence is required, including search queries, fetching public pages, reading public documentation, following source links, comparing sources, and downloading eligible research artifacts.

No per-request confirmation is required for these read-only operations when the network policy is enabled.

### Network writes

Read permission never implies write permission. Uploads, posting, form submission, sending messages, account/profile changes, purchases, destructive remote changes, remote API mutation, and any other externally visible side effect remain separately authorized.

Stage 5 must make it impossible for a read-only research grant to authorize a network write by accident.

## Authenticated sites/accounts

Public research is automatic when enabled. Authenticated read access is site/account scoped and requires one explicit owner authorization before first use. That authorization persists across Thrilla restarts until the owner revokes it.

Authenticated read authorization does not grant write authorization.

The authorization store records scope metadata only. Stage 5 must not add plaintext password, token, cookie, API-key, or private-key persistence to Thrilla's durable hybrid memory.

## Download policy

Safe research artifacts may download automatically when needed for the active task. Examples include PDFs, documentation, text, JSON, CSV, datasets, model metadata, and source archives used only as evidence/reference.

Executable or executable-intent content requires execution/write authorization before Thrilla may use it as code. This includes installers, executables, scripts, packages, binaries, and downloaded content intended to be executed.

Downloading a file never authorizes executing it. Downloaded research is evidence, not trusted code.

## Research pipeline

```text
QUERY
  -> PLAN SOURCES
  -> SEARCH / FETCH IN PARALLEL
  -> PARSE / NORMALIZE
  -> DEDUPLICATE
  -> CACHE
  -> EVIDENCE QUALITY CHECK
      -> insufficient: targeted additional search
      -> sufficient: stop searching
  -> CROSS-CHECK
  -> VERIFIED RESEARCH RESULT + SOURCE RECORD
```

Research must stop when the evidence threshold is satisfied rather than browsing indefinitely.

## Search and fetch implementation

Stage 5 keeps Thrilla's zero-runtime-dependency project policy. The research core uses Python standard-library networking/parsing primitives behind injectable interfaces so tests never require the live internet.

The first search adapter is isolated from the evidence engine. Search-provider failures therefore do not corrupt caching, job control, or evidence evaluation and can be replaced later without restructuring the job system.

HTTP requirements:
- reusable opener/session-equivalent object where practical with stdlib
- explicit user agent
- bounded network operation timeout
- response-size ceiling for in-memory page parsing
- redirect ceiling
- content-type inspection
- URL normalization
- URL/domain deduplication
- no implicit execution of downloaded content
- cache metadata includes fetch time and source URL

## Evidence records

Research evidence stores at least:
- canonical source URL
- source title when available
- retrieval timestamp
- content type
- extracted text/snippet
- content digest
- source/domain identity
- cache provenance
- job id

Duplicate content is detected by canonical URL and content digest.

Thrilla must distinguish search result discovered, source fetched, source parsed, source verified/cross-checked, and source unavailable. Only fetched/parsed evidence may support a research answer.

## Cache

Research cache lives below `~/.thrilla-zilla` and is separate from owner semantic memory.

The cache must avoid duplicate network fetches within a job, allow reuse of recent evidence when appropriate, preserve original source URL and retrieval timestamp, use atomic metadata writes, remain bounded by configurable policies, and never treat cached evidence as current when the job explicitly requires fresher evidence.

## Self-recovery and retry

Recovery rules:
- transient fetch errors may retry with bounded backoff
- one failing source does not fail the entire research job when sufficient alternate evidence exists
- job-level failure records the actual unresolved blocker
- restart discovers persisted nonterminal jobs and marks them recoverable/waiting rather than completed
- resume continues from the last persisted safe checkpoint
- model/runtime failures reuse existing supervisor behavior where applicable
- coding mutations retain Stage-3 checkpoint/verification/rollback guarantees
- retries never bypass owner permissions

## Persistence

Job and authorization metadata persist under `~/.thrilla-zilla` using atomic local storage. Job persistence is independent of conversation history and semantic owner memory.

On startup:
- completed/cancelled jobs remain historical records
- previously running/verifying jobs become recoverable `waiting` jobs until execution resumes
- held jobs remain held
- failed jobs remain failed unless explicitly retried

No unfinished job is silently resumed into side-effecting work before its stored permission state is revalidated.

## Performance requirements

Performance is a Stage-5 acceptance gate.

Requirements:
- owner chat/control remains responsive while a synthetic long-running worker is active
- state inspection is memory-backed and must not scan persistence on every render
- right-pane redraw is throttled and in-place
- worker count is bounded
- identical URLs within one research job are fetched once
- independent read-only fetches may run concurrently
- cache hits bypass network fetch
- evidence collection stops after sufficiency is reached
- Stage-4 direct memory/self-knowledge paths remain direct and must not be routed through the background job engine

Acceptance benchmark targets on the target phone:
- cached job snapshot p95 < 5 ms
- foreground control-state mutation p95 < 10 ms
- synthetic foreground chat/control availability demonstrated while a worker remains blocked/running

These targets measure local orchestration overhead, not internet or LLM latency.

## Audit behavior

Background jobs write structured metadata events to Thrilla's audit system. Prompt/answer text remains in conversation history rather than being duplicated into the metadata audit log. The right pane may show the latest event but the left conversation pane must not be polluted with the event stream.

## Testing and acceptance

Stage 5 cannot pass without tests proving:
1. A long-running synthetic job does not block foreground owner communication.
2. `1.Hold` prevents new work after a safe checkpoint and remains held until explicit resume.
3. `2.Communicate` keeps eligible work running while owner interaction continues.
4. `3.Continue full` resumes a held job.
5. `0.Back` changes only UI navigation state and does not change job execution state.
6. Wide terminals render logically separate chat/work panes.
7. Narrow terminals use compact stacked mode without mixing telemetry into conversation.
8. Worker threads never write directly to the terminal renderer.
9. Read-only public research may proceed automatically when enabled.
10. Network write operations cannot use read-only authorization.
11. Authenticated read access requires prior site/account authorization and persists until revocation.
12. Safe research files may auto-download; executable-intent downloads cannot be executed without separate authorization.
13. Search/fetch deduplicates URLs.
14. Cache hits prevent duplicate fetches.
15. Parallel read-only work remains within the worker ceiling.
16. Research stops after evidence sufficiency.
17. Restart restores unfinished jobs as held/waiting/recoverable, never completed.
18. Failed work never claims success.
19. Existing Stage 1-4 focused tests still pass.
20. Full regression suite passes.
21. `python -m compileall -q thrilla tests` passes.
22. `git diff --check` passes.
23. Local job snapshot/control performance gates pass on the target phone.
24. Stage 5 does not bump, tag, or claim `v1.0.0`.

## Release boundary

Passing Stage 5 means web/research, persistent background workflows, split-pane live control, bounded recovery, and their acceptance gates are complete.

It does **not** mean Thrilla is `v1.0.0`. Stage 6 remains release-candidate acceptance work, and final `v1.0.0` status remains exclusively owner-authorized.
