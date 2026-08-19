# Thrilla Stage 5 Live Work, Research, and Self-Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Thrilla conversational while bounded autonomous jobs run in the background, add evidence-backed read-only web research with persistent scoped authorization, and render conversation separately from live work telemetry.

**Architecture:** Add a persistent `JobManager` with cooperative hold/resume/directive control and bounded worker threads; add isolated network authorization and research/cache modules; add an ANSI/compact live-work renderer that owns all terminal presentation; wire long-running model/research/repair operations through jobs while keeping Stage-4 direct-answer fast paths synchronous. Job state is memory-backed during runtime and atomically persisted under Thrilla state.

**Tech Stack:** Python 3.9+ standard library only (`threading`, `concurrent.futures`, `urllib`, `html.parser`, `json`, `hashlib`, `pathlib`, `time`), existing Thrilla unittest/provider/runtime/tool architecture.

**Spec:** `docs/superpowers/specs/2026-08-18-stage5-live-work-research-design.md`

## Global Constraints

- Baseline implementation commit is `0f5fd5d70d93abbd626825109c43041bf07a1163`; Stage-5 spec commit is `d0da3d4`.
- Preserve Stage 1 supervised local runtime and autonomous brain.
- Preserve Stage 2 exactly 100 experts and structured bounded tools.
- Preserve Stage 3 checkpointed autonomous coding with automatic rollback on failure.
- Preserve Stage 4 durable hybrid memory, direct owner/self fast paths, and conversation-history caching.
- Owner controls are exactly `1.Hold`, `2.Communicate`, `3.Continue full`, `0.Back`.
- Conversation telemetry and work telemetry must not mix.
- Public read-only research may run automatically when enabled.
- Authenticated read access requires one persistent site/account authorization; read permission never grants network write permission.
- Safe research artifacts may auto-download; executable-intent content may not be executed without separate authorization.
- Stage 5 must use bounded workers, URL/content deduplication, cache reuse, evidence sufficiency early-stop, and restart recovery.
- Stage-4 direct owner/self answers must not be routed through the background job engine.
- Cached job snapshot p95 must be `< 5 ms`; control mutation p95 must be `< 10 ms` on the target phone.
- Do not bump, tag, publish, or claim `v1.0.0`.

## File Structure

### New production files

- `thrilla/jobs.py` — job datamodel, persistent store, worker manager, hold/resume/directive/recovery semantics.
- `thrilla/network_auth.py` — public-read policy and persistent authenticated-read scope metadata; explicit separation from write permission.
- `thrilla/research.py` — URL normalization, HTTP fetch, search adapter, parsing, cache, safe-download classification, evidence collection and sufficiency.
- `thrilla/live_ui.py` — split-pane/compact rendering, work snapshots, owner control parsing; workers never print directly.
- `thrilla/workflows.py` — adapters that run model answer, research, and self-repair operations as job tasks without weakening existing verification/rollback.

### Modified production files

- `thrilla/app.py` — instantiate Stage-5 services, preserve direct provider fast path, submit long-running work as jobs, expose live control/communication.
- `thrilla/config.py` — bounded Stage-5 worker/network/cache defaults and persistent auth configuration metadata.
- `thrilla/limits.py` — register Stage-5 worker/network/cache limit names.
- `thrilla/capabilities.py` — update code-owned capability truth to Stage 5 without changing release policy.
- `thrilla/terminal.py` — add narrow terminal size helpers only where required; existing menu behavior remains compatible.
- `thrilla/audit.py` — no API break; only use existing `write()` for job metadata events unless a tiny thread-safety guard becomes necessary after a failing test proves concurrent writes can interleave.

### New tests

- `tests/test_jobs.py`
- `tests/test_job_recovery.py`
- `tests/test_network_auth.py`
- `tests/test_research.py`
- `tests/test_research_cache.py`
- `tests/test_safe_downloads.py`
- `tests/test_live_work_ui.py`
- `tests/test_stage5_app_integration.py`
- `tests/test_stage5_performance.py`

---

### Task 1: Persistent Job Model and Cooperative Control

**Files:**
- Create: `thrilla/jobs.py`
- Create: `tests/test_jobs.py`
- Create: `tests/test_job_recovery.py`

**Interfaces:**
- Produce: `JobState(str, Enum)`
- Produce: `JobSnapshot`
- Produce: `JobControl`
- Produce: `JobContext`
- Produce: `JobManager(state_root: Path, max_workers: int = 3, audit_sink: Optional[Callable[..., None]] = None)`
- Produce: `JobManager.submit(kind: str, goal: str, task: Callable[[JobContext], object], priority: int = 0) -> str`
- Produce: `JobManager.snapshot(job_id: str) -> JobSnapshot`
- Produce: `JobManager.hold(job_id: str) -> JobSnapshot`
- Produce: `JobManager.resume(job_id: str) -> JobSnapshot`
- Produce: `JobManager.directive(job_id: str, text: str) -> JobSnapshot`
- Produce: `JobManager.cancel(job_id: str) -> JobSnapshot`
- Produce: `JobManager.wait(job_id: str, timeout: Optional[float] = None) -> JobSnapshot`
- Produce: `JobManager.recoverable() -> tuple[JobSnapshot, ...]`
- Produce: `JobManager.shutdown(wait: bool = False) -> None`
- `JobContext.checkpoint(...)` is the only place a cooperative job may start its next logical action; it blocks while held and raises cancellation when cancelled.

- [ ] **Step 1: Write failing state-transition tests**

```python
def test_hold_blocks_next_checkpoint_until_explicit_resume():
    entered_second = threading.Event()

    def task(ctx):
        ctx.checkpoint("first")
        entered_second.set()
        ctx.checkpoint("second")
        return "done"

    manager = JobManager(tmp_path, max_workers=1)
    job_id = manager.submit("test", "goal", task)
    assert entered_second.wait(1.0)
    manager.hold(job_id)
    # Test helper coordinates a third checkpoint so no new action starts.
    ...
```

Also test:
- queued -> running -> verifying -> completed;
- task exception -> failed, never completed;
- cancel -> cancelled;
- `directive()` queues owner text without changing run/hold state;
- `snapshot()` returns immutable copies and does not read persistence on every call;
- worker never calls a terminal/print callback.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python -m unittest tests.test_jobs
```

Expected: import failure because `thrilla.jobs` does not exist.

- [ ] **Step 3: Implement datamodel and atomic persistence**

Use JSON files under:

```text
~/.thrilla-zilla/jobs/<job_id>.json
```

Persist with write-to-`.tmp` then `Path.replace()`. Keep active snapshots in a locked in-memory dictionary. Do not query disk in `snapshot()`.

Core dataclass fields must match the Stage-5 spec. Use monotonic time for elapsed runtime and UTC ISO timestamps for persistence/audit.

- [ ] **Step 4: Implement cooperative worker manager**

Use `ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="thrilla-job")`.

`JobControl` owns a `threading.Condition`, `hold_requested`, `cancel_requested`, and directive deque. `JobContext.checkpoint()`:
1. updates current/next action metadata;
2. persists state;
3. if hold requested, transitions to `held` and waits;
4. if cancelled, raises `JobCancelled`;
5. on resume, transitions back to `running`;
6. returns queued directives and clears those consumed by the caller.

No arbitrary `Thread` killing.

- [ ] **Step 5: Write restart recovery tests**

Persist synthetic jobs in `running`, `verifying`, `held`, `completed`, `failed`, `cancelled`, reconstruct `JobManager`, and assert:

```python
self.assertEqual(restored_running.state, JobState.WAITING)
self.assertEqual(restored_verifying.state, JobState.WAITING)
self.assertEqual(restored_held.state, JobState.HELD)
self.assertEqual(restored_completed.state, JobState.COMPLETED)
```

Recovered jobs do not automatically re-execute task callables because callables are not serialized.

- [ ] **Step 6: Run GREEN**

```bash
python -m unittest tests.test_jobs tests.test_job_recovery
```

- [ ] **Step 7: Commit**

```bash
git add thrilla/jobs.py tests/test_jobs.py tests/test_job_recovery.py
git commit -m "feat: add persistent cooperative background jobs"
```

---

### Task 2: Network Authorization and Explicit Read/Write Separation

**Files:**
- Create: `thrilla/network_auth.py`
- Create: `tests/test_network_auth.py`
- Modify: `thrilla/config.py`
- Modify: `thrilla/limits.py`

**Interfaces:**
- Produce: `NetworkOperation(str, Enum)` with `PUBLIC_READ`, `AUTH_READ`, `WRITE`
- Produce: `SiteAuthorization`
- Produce: `AuthorizationStore(state_root: Path)`
- Produce: `AuthorizationStore.authorize_read(site: str, account: str = "") -> SiteAuthorization`
- Produce: `AuthorizationStore.revoke_read(site: str, account: str = "") -> bool`
- Produce: `AuthorizationStore.can_read(site: str, account: str = "") -> bool`
- Produce: `NetworkPolicy(public_read_enabled: bool, write_enabled: bool, authorization_store: AuthorizationStore)`
- Produce: `NetworkPolicy.require(operation: NetworkOperation, url: str, account: str = "") -> None`

- [ ] **Step 1: Write RED permission tests**

Required assertions:

```python
policy.require(NetworkOperation.PUBLIC_READ, "https://example.com/")
with self.assertRaises(NetworkPermissionError):
    policy.require(NetworkOperation.AUTH_READ, "https://private.example.com/", "me")
with self.assertRaises(NetworkPermissionError):
    policy.require(NetworkOperation.WRITE, "https://example.com/post")
```

After `authorize_read("private.example.com", "me")`, `AUTH_READ` succeeds but `WRITE` still fails.

Restart `AuthorizationStore` and prove authorization persists.

- [ ] **Step 2: Verify RED**

```bash
python -m unittest tests.test_network_auth
```

- [ ] **Step 3: Implement authorization metadata persistence**

Store only normalized site/account/scope/timestamps in:

```text
~/.thrilla-zilla/network-authorizations.json
```

Do not persist passwords, tokens, cookies, API keys, private keys, or bearer values.

- [ ] **Step 4: Register Stage-5 limits**

Add exact limit names to `DEFAULT_LIMITS`:

```text
network.public_read
network.write_actions
network.fetch_timeout
network.fetch_bytes
network.redirects
network.research_workers
network.cache_entries
network.cache_age_seconds
```

Default `network.public_read=True`, `network.write_actions=False`, fetch timeout `15.0`, fetch bytes `2_000_000`, redirects `5`, workers `3`, cache entries `256`, cache age `3600`.

Keep legacy `network.remote_model` unchanged.

- [ ] **Step 5: Add Config fields only where a limit cannot represent persistent data**

Prefer `limit_values`/`limit_modes` for numerical/policy values. Do not duplicate each Stage-5 limit as a dataclass field.

- [ ] **Step 6: GREEN + regression**

```bash
python -m unittest tests.test_network_auth tests.test_limits tests.test_config
```

- [ ] **Step 7: Commit**

```bash
git add thrilla/network_auth.py thrilla/config.py thrilla/limits.py tests/test_network_auth.py
git commit -m "feat: add scoped network read authorization"
```

---

### Task 3: Research Fetch, Search, Cache, Deduplication, and Safe Downloads

**Files:**
- Create: `thrilla/research.py`
- Create: `tests/test_research.py`
- Create: `tests/test_research_cache.py`
- Create: `tests/test_safe_downloads.py`

**Interfaces:**
- Produce: `SearchHit`
- Produce: `FetchedDocument`
- Produce: `ResearchEvidence`
- Produce: `ResearchResult`
- Produce: `HTTPFetcher(policy: NetworkPolicy, timeout: float, max_bytes: int, redirect_limit: int)`
- Produce: `ResearchCache(state_root: Path, max_entries: int, max_age_seconds: int)`
- Produce: `SearchAdapter.search(query: str, limit: int) -> tuple[SearchHit, ...]`
- Produce: `DuckDuckGoHTMLSearch(fetcher: HTTPFetcher)` as the first isolated default adapter
- Produce: `ResearchEngine(search: SearchAdapter, fetcher: HTTPFetcher, cache: ResearchCache, max_workers: int = 3)`
- Produce: `ResearchEngine.run(query: str, job: Optional[JobContext] = None, evidence_target: int = 3) -> ResearchResult`
- Produce: `classify_download(filename: str, content_type: str, disposition: str = "") -> DownloadClass`

- [ ] **Step 1: Write RED URL/cache tests**

Test canonicalization removes fragments, normalizes scheme/host casing and default ports, and leaves query data intact.

Test same canonical URL is fetched once inside one job even when search returns duplicates.

Test same content digest from different URLs is represented once in supporting evidence while preserving alternate-source metadata.

- [ ] **Step 2: Write RED fake-network research tests**

Use injected fake search/fetch classes; no test reaches live internet.

Cover:
- bounded parallel fetch;
- one source failure with enough alternatives still succeeds;
- cache hit bypasses fetch;
- insufficient evidence returns a non-success/knowledge-gap style result;
- evidence target causes early stop;
- fetched-but-unparsed pages do not count as support.

- [ ] **Step 3: Implement `HTTPFetcher`**

Use `urllib.request` behind one object with:
- explicit `User-Agent: Thrilla-zilla/Stage5`;
- policy check before opening URL;
- timeout;
- redirect handler that counts/blocks over the configured ceiling;
- reads at most `max_bytes + 1`, rejecting oversized bodies;
- content-type parsing;
- no automatic execution;
- errors normalized to `ResearchFetchError`.

- [ ] **Step 4: Implement HTML text extraction/search adapter**

Use `html.parser.HTMLParser`; strip script/style/noscript content, preserve title and readable text.

Implement DuckDuckGo HTML parsing behind `SearchAdapter`. A provider-format failure yields a search error; it must not corrupt cache or job state.

- [ ] **Step 5: Implement atomic research cache**

Store metadata/body under:

```text
~/.thrilla-zilla/research-cache/
```

Cache keys are SHA-256 of canonical URL. Metadata includes canonical URL, retrieved timestamp, content type, digest, title. Use atomic replace. Maintain an in-memory metadata index after first load.

- [ ] **Step 6: Implement safe download classification**

`SAFE_RESEARCH`: PDF, text, JSON, CSV, XML, common non-executable dataset/archive types when treated only as evidence.

`EXECUTABLE_INTENT`: `.sh`, `.bash`, `.zsh`, `.ps1`, `.cmd`, `.bat`, `.exe`, `.msi`, `.apk`, `.jar`, `.py`, native libraries/binaries, package/install artifacts intended for execution.

Unknown binary content defaults to `REQUIRES_CONFIRMATION`, not safe execution.

Downloading never calls subprocess/import/exec.

- [ ] **Step 7: Integrate cooperative job checkpoints**

Before each new network fetch, cache miss, download, retry, and verification phase call `job.checkpoint(...)` when a job context is present. This makes Hold deterministic.

- [ ] **Step 8: GREEN**

```bash
python -m unittest \
  tests.test_research \
  tests.test_research_cache \
  tests.test_safe_downloads \
  tests.test_network_auth
```

- [ ] **Step 9: Commit**

```bash
git add thrilla/research.py tests/test_research.py tests/test_research_cache.py tests/test_safe_downloads.py
git commit -m "feat: add cached evidence research pipeline"
```

---

### Task 4: Split-Pane Live Work Renderer

**Files:**
- Create: `thrilla/live_ui.py`
- Create: `tests/test_live_work_ui.py`
- Modify: `thrilla/terminal.py`

**Interfaces:**
- Produce: `ControlAction(str, Enum)` values `HOLD="1"`, `COMMUNICATE="2"`, `CONTINUE="3"`, `BACK="0"`
- Produce: `ChatLine(role: str, text: str)`
- Produce: `LiveWorkRenderer(palette: Palette)`
- Produce: `LiveWorkRenderer.render(chat: Sequence[ChatLine], job: Optional[JobSnapshot], columns: int, lines: int) -> str`
- Produce: `LiveWorkRenderer.mode(columns: int) -> str` returning `"split"` or `"compact"`
- Produce: `parse_control(value: str) -> Optional[ControlAction]`

- [ ] **Step 1: Write RED rendering tests**

At wide width assert the rendered text has distinct headings:
- `YOU + THRILLA`
- `ACTIVE WORK`

Assert work metadata strings appear only in the work region before the footer and synthetic tool-log strings are never injected into chat lines.

At narrow width assert:
- `[CHAT]`
- `[ACTIVE WORK]`
- exact footer `1.Hold   2.Communicate   3.Continue full   0.Back`

- [ ] **Step 2: Test exact control mapping**

```python
self.assertIs(parse_control("1"), ControlAction.HOLD)
self.assertIs(parse_control("hold"), ControlAction.HOLD)
self.assertIs(parse_control("2"), ControlAction.COMMUNICATE)
self.assertIs(parse_control("3"), ControlAction.CONTINUE)
self.assertIs(parse_control("0"), ControlAction.BACK)
```

`Back` is a UI action only; this module does not mutate a job.

- [ ] **Step 3: Implement pure renderer first**

Renderer returns a string and performs no I/O. This enforces the rule that workers cannot print. App/foreground code is the only caller that writes it to a terminal stream.

Use visible-width-aware wrapping from existing terminal helpers. Add a public wrapper in `terminal.py` only if required rather than copying wrapping logic.

- [ ] **Step 4: Add in-place ANSI presentation helper**

Add a foreground-only `present_live_frame(stream, frame)` helper that uses home/clear-to-end semantics for TTYs and a single bounded snapshot for non-TTY tests. It must not be callable from worker modules.

Throttle refresh in the controller, not inside worker code.

- [ ] **Step 5: GREEN**

```bash
python -m unittest tests.test_live_work_ui tests.test_terminal
```

- [ ] **Step 6: Commit**

```bash
git add thrilla/live_ui.py thrilla/terminal.py tests/test_live_work_ui.py
git commit -m "feat: add separated live chat and work panes"
```

---

### Task 5: Workflow Adapters for Model, Research, and Existing Self-Repair

**Files:**
- Create: `thrilla/workflows.py`
- Create: `tests/test_stage5_app_integration.py`
- Modify: `thrilla/app.py`

**Interfaces:**
- Produce: `WorkflowServices`
- Produce: `run_answer_job(ctx: JobContext, prompt: str, previous, route: str) -> str`
- Produce: `run_research_job(ctx: JobContext, prompt: str) -> ResearchResult`
- Produce: `run_repair_job(ctx: JobContext, goal: str) -> CodingOutcome`
- App produces: `self.jobs`, `self.network_authorizations`, `self.network_policy`, `self.research`, `self.live_renderer`, `self.workflows`

- [ ] **Step 1: Write RED Stage-4 direct-path preservation test**

For `"what is my name"` and `"what can you do"`:
- `_resolve_ask_answer()` still answers directly;
- no job is submitted;
- no model is called.

This protects the Stage-4 performance architecture.

- [ ] **Step 2: Write RED background-model responsiveness test**

Use a blocking fake runtime/model action. Submit a normal model answer job, prove the test thread can:
- call `jobs.snapshot()` immediately;
- append a directive;
- hold/resume control;
- invoke a direct provider query without waiting for the blocked model worker.

Do not claim two simultaneous local-model generations are supported. Stage 5 separates foreground control from work; model-intensive jobs may still serialize through the runtime.

- [ ] **Step 3: Wrap self-repair without weakening Stage 3**

`run_repair_job()` calls the existing `AutonomousCodingAgent.run(goal)` unchanged for mutation/checkpoint/verification/critic/rollback semantics. Add job checkpoints only outside indivisible Stage-3 mutation/verification operations.

Never duplicate self-repair logic in Stage 5.

- [ ] **Step 4: Add research routing**

For search/research/fresh/current/external-evidence requests, submit `run_research_job()` rather than sending an unsupported generic prompt directly to the local model.

Research result passed to the answer synthesis path contains only fetched evidence records. If the local model is unavailable, the research job still preserves evidence and reports that synthesis is unavailable rather than claiming the task completed.

- [ ] **Step 5: Add Stage-5 service construction and refresh**

In `ThrillaApp.__init__` instantiate in dependency order:
1. config/audit/history/memory;
2. runtime/expert/tools/coding;
3. network authorization/policy;
4. research/cache;
5. jobs;
6. live renderer/workflow services;
7. providers/model.

`_refresh()` must preserve or safely replace live services without orphaning running jobs. Do not blindly instantiate a second `JobManager` while jobs are active; either retain it or shut it down first under a tested rule.

- [ ] **Step 6: GREEN integration**

```bash
python -m unittest tests.test_stage5_app_integration
```

- [ ] **Step 7: Commit**

```bash
git add thrilla/workflows.py thrilla/app.py tests/test_stage5_app_integration.py
git commit -m "feat: run long Thrilla work as background jobs"
```

---

### Task 6: Owner Live Control Loop and Nonblocking Communication

**Files:**
- Modify: `thrilla/app.py`
- Modify: `thrilla/live_ui.py`
- Extend: `tests/test_stage5_app_integration.py`

**Interfaces:**
- App method: `_active_work_screen(job_id: str) -> None`
- App method: `_communicate_during_job(job_id: str) -> None`
- App method: `_handle_control(job_id: str, action: ControlAction) -> bool`
- `bool` return means remain in work screen (`True`) or navigate back (`False`).

- [ ] **Step 1: RED exact control behavior**

Assert:
- HOLD calls `jobs.hold(job_id)` and stays in view.
- COMMUNICATE enters conversation mode without mutating job state.
- CONTINUE calls `jobs.resume(job_id)` and stays in view.
- BACK returns from view and does not call hold/resume/cancel.

- [ ] **Step 2: Implement live controller**

Only foreground code performs:
- terminal frame render;
- input read;
- control dispatch;
- chat line mutation.

Use a bounded refresh interval (target 200–500 ms while idle in active-work view). On POSIX, use `select`/existing key primitives; on Windows use existing `msvcrt` path. Do not spawn a renderer thread that races with owner typing.

- [ ] **Step 3: Implement Communicate mode**

Communication retains a job snapshot/work pane while accepting `you>` prompts. If prompt is an explicit job directive, queue it with `jobs.directive()`. If it is a direct provider question, answer immediately. If it requires model generation while the model worker is occupied, submit/queue a separate answer job and keep the owner loop responsive rather than blocking the terminal.

- [ ] **Step 4: Preserve conversation history semantics**

Owner/assistant conversational lines remain in `ConversationHistory`. Work events remain in job/audit records and never get appended as assistant conversation text.

- [ ] **Step 5: GREEN**

```bash
python -m unittest tests.test_stage5_app_integration tests.test_live_work_ui
```

- [ ] **Step 6: Commit**

```bash
git add thrilla/app.py thrilla/live_ui.py tests/test_stage5_app_integration.py
git commit -m "feat: keep owner chat live during background work"
```

---

### Task 7: Performance, Concurrency, Recovery, and Capability Truth

**Files:**
- Create: `tests/test_stage5_performance.py`
- Modify: `thrilla/capabilities.py`
- Modify: `thrilla/app.py` About text if required by existing source-invariant tests.

**Interfaces:**
- No new public API.

- [ ] **Step 1: Add local orchestration benchmarks as tests**

Warm the manager, then collect at least 500 samples each:
- `JobManager.snapshot()` p95 `< 5 ms`
- hold/resume or directive control mutation p95 `< 10 ms`

The test records actual measured milliseconds in failure output.

- [ ] **Step 2: Add synthetic foreground responsiveness acceptance**

Run a worker blocked on an event for at least 250 ms. During the block:
- get a snapshot;
- submit a directive;
- execute a direct owner-memory answer;
- assert these complete before worker release.

This proves orchestration responsiveness without pretending to benchmark internet/LLM latency.

- [ ] **Step 3: Add bounded concurrency test**

Use a fake fetcher that tracks simultaneous calls. With `max_workers=3`, assert peak concurrency `<= 3` and `>= 2` for independent read-only sources.

- [ ] **Step 4: Update code-owned capabilities**

Set `STAGE = 5`. Active capabilities must include:
- persistent cooperative background jobs;
- live owner communication/control;
- split chat/work UI;
- evidence-backed cached read-only web research;
- persistent scoped authenticated-read authorization;
- bounded recovery.

Move those items out of `FUTURE_CAPABILITIES`. Keep release policy text exactly preserving owner-only v1.0.0 authorization.

- [ ] **Step 5: Run focused Stages 1–5 suite**

```bash
python -m unittest \
  tests.test_agent_brain \
  tests.test_runtime_supervisor \
  tests.test_expert_orchestration \
  tests.test_structured_tools \
  tests.test_checkpoints \
  tests.test_coding_workflow \
  tests.test_long_term_memory \
  tests.test_memory_knowledge \
  tests.test_history_cache \
  tests.test_jobs \
  tests.test_job_recovery \
  tests.test_network_auth \
  tests.test_research \
  tests.test_research_cache \
  tests.test_safe_downloads \
  tests.test_live_work_ui \
  tests.test_stage5_app_integration \
  tests.test_stage5_performance
```

- [ ] **Step 6: Compile**

```bash
python -m compileall -q thrilla tests
```

- [ ] **Step 7: Full regression**

```bash
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_*.py'
```

- [ ] **Step 8: Diff integrity**

```bash
git diff --check
git status --short
```

- [ ] **Step 9: Commit**

```bash
git add thrilla tests
git commit -m "feat: complete stage 5 live research workflows"
```

---

### Task 8: Real Phone Acceptance Gate

**Files:**
- No production changes unless a test-proven defect is found.
- If a defect is found, add a failing regression test before changing production code.

- [ ] **Step 1: Verify exact branch and clean worktree**

```bash
git branch --show-current
git status --short
git log -8 --oneline --decorate
```

- [ ] **Step 2: Run target-phone performance acceptance**

Run the benchmark from `tests/test_stage5_performance.py` and print p50/p95/worst for snapshots and controls.

Required:
- snapshot p95 `< 5 ms`
- control p95 `< 10 ms`

- [ ] **Step 3: Run synthetic live-control acceptance**

Start a blocked synthetic job and demonstrate:
- job state RUNNING;
- owner direct query answers while job remains blocked;
- Hold reaches HELD at a checkpoint;
- Communicate does not resume/hold automatically;
- Continue resumes;
- Back does not change job state;
- job finishes only after verification.

- [ ] **Step 4: Run fake-network research acceptance**

Without depending on public internet:
- 5 synthetic search hits;
- duplicate URL;
- duplicate body digest;
- one transient failure;
- bounded concurrency;
- evidence target 3;
- assert exactly sufficient evidence and no extra fetches after threshold.

- [ ] **Step 5: Optional live public-read smoke test**

Only after deterministic tests pass, perform one public read-only research query if network is available. This is a smoke test, not the correctness foundation. Failure due to provider/network availability is reported separately and does not rewrite deterministic acceptance evidence.

- [ ] **Step 6: Full suite one final time**

```bash
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q thrilla tests
git diff --check
```

- [ ] **Step 7: Stage-5 completion commit only if needed**

If Task 8 required no fixes, do not create an empty commit.

- [ ] **Step 8: Final status must explicitly say**

```text
THRILLA STAGE 5/6: PASS
Background jobs + restart recovery: PASS
1.Hold / 2.Communicate / 3.Continue full / 0.Back: PASS
Split conversation/work UI: PASS
Read-only research + cache + evidence: PASS
Scoped authenticated-read authorization: PASS
Safe-download policy: PASS
Foreground responsiveness: PASS
Performance gates: PASS
Full regression suite: PASS
v1.0.0 status: NOT CLAIMED
```

No Stage-5 script may print this block before all preceding gates return success.
