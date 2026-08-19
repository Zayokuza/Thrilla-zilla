"""Code-owned Thrilla capability registry."""

from .identity import CREATOR_NAME


STAGE = 5

ACTIVE_CAPABILITIES = (
    "supervised local llama-server runtime with one managed recovery attempt",
    "100 routed experts with Reason / Action / Critic advisory roles",
    "structured bounded local read tools",
    "checkpointed repository self-repair with verification and rollback",
    "durable hybrid owner/project memory with provenance and correction",
    "direct local owner-memory and self-knowledge answers without model inference",
    "persistent bounded background jobs with checkpoint recovery",
    "read-only web research with persistent cache, evidence deduplication, and safe-download classification",
    "split conversation / active-work interface with owner Hold, Communicate, Continue full, and Back controls",
    "live owner communication while eligible background work continues",
)

FUTURE_CAPABILITIES = (
    "release-candidate acceptance across target platforms",
)

RELEASE_POLICY = (
    "Thrilla is not v1.0.0 unless the owner explicitly authorizes v1.0.0."
)


def self_description(owner_name: str = "") -> str:
    owner = owner_name.strip() or "not configured"

    lines = (
        "Name: Thrilla-zilla",
        "Creator: {0}".format(CREATOR_NAME),
        "Owner: {0}".format(owner),
        "Roadmap stage: {0}/6".format(STAGE),
        "Active capabilities:",
        *(
            "- " + capability
            for capability in ACTIVE_CAPABILITIES
        ),
        "Not active yet:",
        *(
            "- " + capability
            for capability in FUTURE_CAPABILITIES
        ),
        "Release policy: {0}".format(RELEASE_POLICY),
    )

    return "\n".join(lines)
