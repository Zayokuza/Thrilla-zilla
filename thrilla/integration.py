"""Controlled cross-system capabilities for Thrilla Stage 7E."""

from typing import Any, Mapping

from .tools import (
    ToolPermission,
    ToolRegistry,
    ToolSpec,
)


class IntegratedToolFactory:
    def __init__(
        self,
        *,
        research_engine,
        memory,
        coding_agent,
    ):
        self.research_engine = research_engine
        self.memory = memory
        self.coding_agent = coding_agent

    def research_query(
        self,
        args: Mapping[str, Any],
    ):
        query = str(
            args.get("query", "")
        ).strip()

        if not query:
            raise ValueError(
                "research query must not be empty"
            )

        target = max(
            1,
            min(
                int(
                    args.get(
                        "evidence_target",
                        5,
                    )
                ),
                8,
            ),
        )

        result = self.research_engine.research(
            query,
            evidence_target=target,
        )

        if not result.evidence:
            detail = (
                "; ".join(result.errors)
                or "no research evidence"
            )
            raise RuntimeError(detail)

        evidence = []

        for item in result.evidence:
            evidence.append(
                {
                    "url": item.url,
                    "title": item.title,
                    "text": item.text,
                    "digest": item.digest,
                    "retrieved_at": getattr(
                        item,
                        "retrieved_at",
                        "",
                    ),
                }
            )

        return {
            "source": "research:" + query,
            "detail": "collected {0} research evidence items".format(
                len(evidence)
            ),
            "query": query,
            "evidence": evidence,
            "errors": list(result.errors),
            "cache_hits": int(
                getattr(
                    result,
                    "cache_hits",
                    0,
                )
            ),
        }

    def memory_search(
        self,
        args: Mapping[str, Any],
    ):
        query = str(
            args.get("query", "")
        ).strip()

        limit = max(
            1,
            min(
                int(
                    args.get(
                        "limit",
                        8,
                    )
                ),
                20,
            ),
        )

        facts = self.memory.store.search(
            query,
            limit=limit,
        )

        items = []

        for fact in facts:
            items.append(
                {
                    "id": fact.fact_id,
                    "category": fact.category,
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "value": fact.value,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "updated_at": fact.updated_at,
                }
            )

        return {
            "source": "durable-memory",
            "detail": "found {0} matching memories".format(
                len(items)
            ),
            "query": query,
            "facts": items,
        }

    def memory_remember(
        self,
        args: Mapping[str, Any],
    ):
        text = str(
            args.get("text", "")
        ).strip()

        if not text:
            raise ValueError(
                "memory text must not be empty"
            )

        fact = self.memory.remember_explicit(
            text
        )

        return {
            "source": "durable-memory",
            "detail": "stored explicit durable memory",
            "fact": {
                "id": fact.fact_id,
                "category": fact.category,
                "subject": fact.subject,
                "predicate": fact.predicate,
                "value": fact.value,
                "confidence": fact.confidence,
            },
        }

    def coding_repair(
        self,
        args: Mapping[str, Any],
    ):
        goal = str(
            args.get("goal", "")
        ).strip()

        if not goal:
            raise ValueError(
                "coding goal must not be empty"
            )

        outcome = self.coding_agent.run(
            goal
        )

        if not getattr(
            outcome,
            "ok",
            False,
        ):
            raise RuntimeError(
                getattr(
                    outcome,
                    "summary",
                    "checkpointed coding repair failed",
                )
            )

        critic = getattr(
            outcome,
            "critic",
            None,
        )

        return {
            "source": "checkpointed-coding",
            "detail": getattr(
                outcome,
                "summary",
                "coding repair verified",
            ),
            "checkpoint_id": getattr(
                outcome,
                "checkpoint_id",
                "",
            ),
            "edited_paths": list(
                getattr(
                    outcome,
                    "edited_paths",
                    (),
                )
            ),
            "rolled_back": bool(
                getattr(
                    outcome,
                    "rolled_back",
                    False,
                )
            ),
            "critic_passed": bool(
                getattr(
                    critic,
                    "passed",
                    True,
                )
            ),
        }


def register_stage7e_tools(
    registry: ToolRegistry,
    *,
    research_engine,
    memory,
    coding_agent,
):
    factory = IntegratedToolFactory(
        research_engine=research_engine,
        memory=memory,
        coding_agent=coding_agent,
    )

    registry.register(
        ToolSpec(
            "research.query",
            ToolPermission.NETWORK,
            "Perform policy-controlled read-only web research and return evidence.",
            factory.research_query,
        )
    )

    registry.register(
        ToolSpec(
            "memory.search",
            ToolPermission.READ,
            "Search Thrilla's durable local memory.",
            factory.memory_search,
        )
    )

    registry.register(
        ToolSpec(
            "memory.remember",
            ToolPermission.WRITE,
            "Store explicit durable memory with Thrilla's secret filter.",
            factory.memory_remember,
        )
    )

    registry.register(
        ToolSpec(
            "coding.repair",
            ToolPermission.WRITE,
            "Run checkpointed repository coding with verification and rollback.",
            factory.coding_repair,
        )
    )
