# Stage 4 Memory + Identity + Self-Knowledge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fast durable hybrid owner/project memory and accurate direct self-knowledge without adding an extra model call to normal prompts.

**Architecture:** `thrilla/memory.py` owns SQLite persistence, active-fact caching, deterministic extraction, correction and forgetting. `thrilla/knowledge.py` exposes owner-memory and self-knowledge as direct evidence providers. `thrilla/history.py` keeps JSONL persistence while caching parsed history in-process. `thrilla/app.py` wires commands, automatic promotion, owner-name synchronization and providers.

**Tech Stack:** Python 3 standard library, sqlite3, unittest, existing Thrilla provider/runtime architecture.

**Spec:** `docs/superpowers/specs/2026-08-18-stage4-memory-identity-performance-design.md`

## Global Constraints

- Baseline commit must be `834cbcf`.
- Preserve Stage 1 runtime/autonomous brain.
- Preserve Stage 2 exactly-100 expert orchestration/tools.
- Preserve Stage 3 checkpointed self-repair/rollback.
- No extra LLM call for memory extraction.
- No secret-like credential persistence.
- Direct memory/self-knowledge answers bypass model inference.
- Do not bump or claim v1.0.0.

---

### Task 1: Durable hybrid memory

**Files:**
- Create: `thrilla/memory.py`
- Test: `tests/test_long_term_memory.py`

**Interfaces:**
- `MemoryStore.remember(...) -> MemoryFact`
- `MemoryStore.search(query, limit) -> tuple[MemoryFact, ...]`
- `HybridMemory.observe(owner_text) -> tuple[MemoryFact, ...]`
- `HybridMemory.remember_explicit(owner_text) -> MemoryFact`
- `HybridMemory.correct(query, replacement) -> MemoryFact`
- `HybridMemory.forget(query) -> int`

- [ ] Write tests first and confirm RED.
- [ ] Implement SQLite schema, reusable connection and active cache.
- [ ] Implement deterministic high-confidence extraction.
- [ ] Implement supersession, correction, deletion and secret rejection.
- [ ] Run tests GREEN.

### Task 2: Direct knowledge providers

**Files:**
- Create: `thrilla/capabilities.py`
- Create: `thrilla/knowledge.py`
- Test: `tests/test_memory_knowledge.py`

- [ ] Write provider tests and confirm RED.
- [ ] Implement direct owner-memory provider.
- [ ] Implement code-owned self-knowledge provider.
- [ ] Verify release policy and active capability truth.

### Task 3: Faster conversation history

**Files:**
- Replace: `thrilla/history.py`
- Test: `tests/test_history_cache.py`

- [ ] Write cache behavior tests.
- [ ] Cache parsed JSONL in the running process.
- [ ] Keep append/clear semantics and explicit reload support.

### Task 4: App integration

**Files:**
- Modify: `thrilla/app.py`
- Test: `tests/test_stage4_app_integration.py`

- [ ] Write RED app integration tests.
- [ ] Instantiate durable memory before provider registry.
- [ ] Add self/owner direct providers.
- [ ] Add `/remember`, `/memories`, `/forget`, `/correct`.
- [ ] Auto-promote deterministic owner facts.
- [ ] Sync remembered owner name into config.
- [ ] Update About boundary.

### Task 5: Performance + regression gate

- [ ] Run focused Stage-4 tests.
- [ ] Verify memory/self direct answers do not invoke model.
- [ ] Benchmark cached owner-memory lookup p95 < 25 ms.
- [ ] Compile all Python.
- [ ] Run full unittest discovery.
- [ ] Run `git diff --check`.
- [ ] Commit only if every gate passes.
