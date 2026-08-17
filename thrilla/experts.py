"""Permanent Thrilla expert architecture."""

EXPERTS_PER_GROUP = 10

EXPERT_GROUPS = (
    "Agent Brain",
    "Coding",
    "AI Runtime",
    "Build / Language",
    "Memory / State",
    "Web Research",
    "Tools / Flows",
    "Execution / OS",
    "Interface / API",
    "Evaluation / Security",
)

EXPERT_COUNT = (
    len(EXPERT_GROUPS)
    * EXPERTS_PER_GROUP
)

assert len(EXPERT_GROUPS) == 10
assert EXPERTS_PER_GROUP == 10
assert EXPERT_COUNT == 100
