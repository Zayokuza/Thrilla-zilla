# Current status

Version: **0.1.0-alpha.2**
Date: **2026-08-19**
Roadmap: **Stage 5/6 — Stages 1 through 5 integrated and Android/Termux accepted**

## Stages 1 through 5

1. **Runtime + autonomous brain** — integrated.
2. **100 experts + structured tools** — integrated; exactly 10 groups × 10 experts.
3. **Checkpointed coding + verification + rollback** — integrated.
4. **Durable memory + owner/self knowledge** — integrated.
5. **Read-only web research + persistent background workflows + optional live controls** — integrated.

## Fresh final acceptance

- Full regression suite: **471 tests**, no ResourceWarning.
- SQLite memory lifecycle: explicit close and GC fallback verified.
- Real local Gemma casual chat through Thrilla: **24.832s**.
- Self-status query **"what is and isnt functioning"** bypasses model inference and uses code-owned capability state.
- Live Stage-5 research pipeline with real HTTPS retrieval: **0.472s**.
- Model-facing history remains bounded while durable history is preserved.
- General chat is bounded and guarded against system-boilerplate and internal Critic/expert leakage.
- Hold / Communicate / Continue / Back remain optional controls; long work continues automatically.

## Outside this acceptance

Stage 6 is **not started** by this pass.

Thrilla is **not v1.0.0** and must not be tagged or released as v1.0.0 without explicit owner authorization.
