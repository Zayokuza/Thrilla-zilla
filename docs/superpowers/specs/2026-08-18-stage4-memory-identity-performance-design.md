# Thrilla Stage 4 Memory, Identity, Self-Knowledge, and Performance Design

## Status

Approved owner direction: hybrid memory model (Option C).

## Goal

Make Thrilla remember durable owner/project facts, correct and forget them safely, know its own identity/capabilities accurately, and answer those knowledge paths with minimal latency.

## Memory authority

1. Explicit owner memory is authoritative and confidence 1.0.
2. High-confidence deterministic extraction from normal owner messages may auto-promote durable facts.
3. System-observed self/runtime/repository facts come from code-owned providers, not from assistant prose.
4. Conversation history remains temporary context and does not become durable owner fact merely because the assistant said it.

## Persistence

SQLite at `~/.thrilla-zilla/memory.sqlite3`.

Each fact records:
- fact id
- category
- subject
- predicate
- value
- confidence
- source
- source timestamp
- created/updated timestamps
- active/superseded/deleted status
- superseded fact id
- raw owner source text

Active facts are cached in-process for fast reads.

## Hybrid capture

Automatic capture is deterministic and bounded to high-confidence patterns such as owner name, favorites, preferred settings/models, owned device facts, location, and explicit Thrilla project goals.

Explicit `/remember` accepts broader facts.

Credential/secret-like content is rejected from durable memory.

## Corrections

A new fact with the same subject/predicate supersedes the prior active fact. `/correct` also supports targeted corrections. `/forget` marks matching facts deleted while retaining audit history.

## Self-knowledge

Code-owned direct providers answer:
- Thrilla identity/name
- creator
- configured/remembered owner
- roadmap stage
- current active capabilities
- later-stage boundaries
- explicit release policy

Repository/version/branch/commit and runtime/model questions remain delegated to their existing observed providers.

## Performance

Performance is a hard Stage-4 acceptance property:
- durable memory/self-knowledge direct answers bypass model inference
- one reusable SQLite connection per store
- WAL + NORMAL synchronous mode
- active fact cache in RAM
- deterministic regex extraction instead of an LLM extraction pass
- conversation JSONL parsed once per running process and cached
- no repository scan or subprocess on the owner-memory hot path
- benchmark p95 for a typical cached memory lookup must remain below 25 ms on the target phone during installer acceptance

## Release policy

Stage 4 does not change Thrilla to v1.0.0. Thrilla may not claim v1.0.0 unless the owner explicitly authorizes that version.
