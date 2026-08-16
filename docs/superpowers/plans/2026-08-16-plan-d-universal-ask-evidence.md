# Universal Ask and Evidence Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and strict RED -> GREEN TDD.

**Goal:** Make Ask Thrilla the universal front door and require substantive answers to use actual knowledge/evidence or explicitly diagnose why sufficient evidence is unavailable.

**Architecture:** Add immutable evidence and knowledge-gap types plus a provider registry before model inference. Deterministic providers may answer directly; otherwise collected evidence is passed to the reasoning model while the original owner request remains authoritative.

**Tech Stack:** Python 3.9-compatible standard library, dataclasses, unittest, existing router, RuntimeManager, model client, Config, and AuditLog.

## Global Constraints

- Ask Thrilla accepts any topic.
- Specialist routing is internal and never becomes a topic gate.
- Do not return generic filler as the final answer to an evidence-dependent question.
- Model knowledge may be used when direct observation is not required.
- Current/local/self-state questions use real evidence when an applicable provider exists.
- Insufficient evidence produces an explicit KnowledgeGap.
- A KnowledgeGap identifies what is unknown, what evidence is missing, why it is missing, and how to resolve it.
- Retrieved web/file/repository/tool/model/AI content is evidence, not owner authority.
- The original direct owner request must remain separate from retrieved evidence.
- Preserve Step 21 runtime readiness before model inference.
- Preserve Python 3.9 compatibility and never use X | Y annotations.
- Thrilla expert count is exactly 100, never 98.
- The 100 experts and 100 donor repositories are separate concepts.

---

## Task 1 - Evidence and Knowledge-Gap Domain

**Files:**
- Create: `thrilla/answers.py`
- Create: `tests/test_answer_contract.py`

**Required interfaces:**
- Immutable `Evidence` with `source`, `detail`, and `content` fields.
- Immutable `KnowledgeGap` with `unknown`, `missing_evidence`, `reason`, and `resolution` fields.
- Immutable `AnswerContext` with `direct_answer`, `evidence`, and `gap` fields.

**Required type shapes:**
- `missing_evidence` is `Tuple[str, ...]`.
- `resolution` is `Tuple[str, ...]`.
- `evidence` is `Tuple[Evidence, ...]`.
- `direct_answer` is optional text.
- `gap` is an optional KnowledgeGap.

**Required behavior:**
- AnswerContext may contain a deterministic direct answer.
- AnswerContext may contain evidence for model reasoning.
- AnswerContext may contain a diagnosed knowledge gap.
- Empty evidence is represented by an empty tuple, never mutable shared state.
- KnowledgeGap must not be reduced to a generic `I do not know` string.

### TDD Cycle

- [ ] RED: Evidence is immutable and preserves source/detail/content.
- [ ] RED: KnowledgeGap preserves unknown/missing-evidence/reason/resolution.
- [ ] RED: AnswerContext supports direct answer, evidence, and gap states.
- [ ] RED: tuple fields are immutable.
- [ ] Run `python -B -m unittest tests.test_answer_contract -v` and confirm RED.
- [ ] Implement the minimum immutable answer-domain types.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 1 with message `feat: add evidence answer contract`.

## Task 2 - Evidence Provider Registry

**Files:**
- Create: `thrilla/providers.py`
- Create: `tests/test_provider_registry.py`

**Required interfaces:**
- `EvidenceProvider.supports(prompt: str) -> bool`.
- `EvidenceProvider.collect(prompt: str) -> AnswerContext`.
- `ProviderRegistry(providers)` stores providers in deterministic order.
- `ProviderRegistry.collect(prompt: str) -> AnswerContext`.

**Collection rules:**
- Only providers whose supports() returns True are invoked.
- A deterministic direct answer may terminate collection.
- Otherwise evidence from supporting providers is combined in registry order.
- Provider failure must not fabricate evidence.
- Provider failure must contribute a diagnosed KnowledgeGap describing the failed evidence source.
- No supporting provider is not itself an error; the reasoning model may still answer from model knowledge.

### TDD Cycle

- [ ] RED: unsupported providers are not called.
- [ ] RED: supported provider evidence is collected.
- [ ] RED: deterministic direct answer is returned without calling later unnecessary providers.
- [ ] RED: multiple evidence providers preserve deterministic order.
- [ ] RED: provider exception becomes a KnowledgeGap rather than invented evidence.
- [ ] Run `python -B -m unittest tests.test_provider_registry -v` and confirm RED.
- [ ] Implement the minimum provider registry.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 2 with message `feat: add evidence provider registry`.

---

## Task 3 - Universal Ask Integration

**Files:**
- Modify: `thrilla/app.py`
- Reuse: `thrilla/answers.py`
- Reuse: `thrilla/providers.py`
- Create: `tests/test_universal_ask.py`

**Required behavior:**
- Ask Thrilla remains the single front door for arbitrary questions.
- The owner is not required to pick a specialist menu first.
- Existing internal route classification may still be used for diagnostics and tool/provider selection.
- A deterministic provider direct answer bypasses unnecessary model inference.
- Collected evidence is added as reference context when model reasoning is required.
- The original owner prompt remains the authoritative request.
- If no provider applies, normal model reasoning is still allowed.
- If evidence is required but unavailable, Thrilla renders a KnowledgeGap instead of generic filler.
- Step 21 RuntimeManager readiness remains mandatory before actual model inference.

### Knowledge-Gap Output

When a gap is the correct result, Thrilla presents:
- what is unknown;
- which evidence is missing;
- why that evidence is missing;
- concrete ways to resolve the gap.

### TDD Cycle

- [ ] RED: an arbitrary general question reaches the normal reasoning path without a specialist-topic rejection.
- [ ] RED: deterministic direct answer bypasses model chat.
- [ ] RED: provider evidence is included in reasoning context.
- [ ] RED: original owner request remains separate from evidence text.
- [ ] RED: evidence-required failure renders structured KnowledgeGap content.
- [ ] RED: model inference still calls RuntimeManager readiness first.
- [ ] Run `python -B -m unittest tests.test_universal_ask -v` and confirm RED.
- [ ] Implement the minimum Universal Ask integration.
- [ ] Run focused suite to GREEN.
- [ ] Run existing Ask and Step 21 regressions.
- [ ] Commit Task 3 with message `feat: add universal evidence-driven ask flow`.

## Task 4 - Owner Authority Isolation

**Files:**
- Modify: `thrilla/answers.py` and/or the narrow message-construction boundary.
- Reuse owner-source classification from Plan B.
- Create: `tests/test_owner_authority.py`

**Required behavior:**
- Direct local owner input remains the command.
- Web text is evidence only.
- File contents are evidence only.
- Repository instructions are evidence only.
- Tool output is evidence only.
- Model-generated text is evidence/output only.
- Another AI output is evidence only.
- Prompt-injection text inside retrieved evidence cannot replace the owner request.
- Evidence is explicitly framed as reference material when passed to the model.

### TDD Cycle

- [ ] RED: evidence containing `ignore the owner request` remains non-authoritative evidence.
- [ ] RED: evidence cannot replace or rewrite the stored owner prompt.
- [ ] RED: multiple retrieved sources remain labeled as evidence.
- [ ] RED: owner prompt is preserved byte-for-byte except existing intentional normalization.
- [ ] Implement the minimum authority-isolation message boundary.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 4 with message `feat: isolate owner commands from retrieved evidence`.

## Task 5 - Permanent 100 Expert Invariant

**Files:**
- Create: `thrilla/experts.py`
- Modify: `thrilla/app.py` where expert architecture is displayed.
- Create: `tests/test_expert_invariant.py`

**Required constants:**
- `EXPERTS_PER_GROUP = 10`
- `EXPERT_COUNT = 100`

**Required expert groups:**
- Agent Brain
- Coding
- AI Runtime
- Build / Language
- Memory / State
- Web Research
- Tools / Flows
- Execution / OS
- Interface / API
- Evaluation / Security

**Required behavior:**
- Exactly ten groups exist.
- Each group represents ten experts.
- Total expert count is exactly 100.
- Thrilla UI and new documentation from this batch must never say 98 experts.
- 100 experts are explicitly separate from the 100 core donor repositories.
- Do not falsely claim expert runtime behavior that has not yet been implemented.

### TDD Cycle

- [ ] RED: exactly ten expert groups are registered.
- [ ] RED: EXPERTS_PER_GROUP equals 10.
- [ ] RED: EXPERT_COUNT equals 100.
- [ ] RED: computed group count times experts-per-group equals 100.
- [ ] RED: UI wording distinguishes 100 experts from 100 donor repositories.
- [ ] Implement the minimum expert-invariant module and truthful UI exposure.
- [ ] Run focused suite to GREEN.
- [ ] Search changed product files for the phrase `98 experts` and require zero matches.
- [ ] Commit Task 5 with message `feat: lock Thrilla 100 expert architecture`.

## Plan D Verification Gate

- [ ] Run answer-contract tests.
- [ ] Run provider-registry tests.
- [ ] Run Universal Ask tests.
- [ ] Run owner-authority tests.
- [ ] Run 100-expert invariant tests.
- [ ] Run existing router tests.
- [ ] Run existing Ask and Step 21 runtime-readiness tests.
- [ ] Run existing donor-library tests.
- [ ] Run the full test suite.
- [ ] Run `python -m compileall -f -q thrilla tests`.
- [ ] Run `git diff --check`.
- [ ] Confirm Ask has no specialist-topic gate.
- [ ] Confirm no generic filler is used as the terminal result for a diagnosed evidence gap.
- [ ] Confirm retrieved content remains evidence, not authority.
- [ ] Confirm expert count is 100 and no changed product file says 98 experts.
- [ ] Confirm 100 experts and 100 donor repositories remain separate concepts.

## Plan D Completion

Plan D is complete only when Ask Thrilla accepts arbitrary questions, direct evidence can answer deterministically, model reasoning can consume labeled evidence without surrendering owner authority, insufficient required evidence produces a diagnosed KnowledgeGap, Step 21 readiness remains intact, and Thrilla expert architecture is fixed at exactly 100 experts separate from the 100 donor repositories.
