"""Deterministic evidence-provider registry."""

from typing import Iterable, Optional, Tuple

from .answers import (
    AnswerContext,
    KnowledgeGap,
)


class EvidenceProvider:
    """Interface implemented by evidence sources."""

    def supports(
        self,
        prompt: str,
    ) -> bool:
        raise NotImplementedError

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        raise NotImplementedError


class ProviderRegistry:
    """Collect evidence in registered order."""

    def __init__(
        self,
        providers: Iterable[EvidenceProvider],
    ) -> None:
        self.providers = tuple(providers)

    @staticmethod
    def _name(
        provider: EvidenceProvider,
    ) -> str:
        return provider.__class__.__name__

    @classmethod
    def _failure_gap(
        cls,
        provider: EvidenceProvider,
        error: Exception,
    ) -> KnowledgeGap:
        name = cls._name(provider)

        return KnowledgeGap(
            unknown=(
                "provider evidence from {}".format(
                    name
                )
            ),
            missing_evidence=(
                "{} observation".format(
                    name
                ),
            ),
            reason=(
                "{} failed: {}".format(
                    name,
                    error,
                )
            ),
            resolution=(
                "restore or retry the {} evidence source".format(
                    name
                ),
            ),
        )

    @staticmethod
    def _combine_gaps(
        gaps: Tuple[KnowledgeGap, ...],
    ) -> Optional[KnowledgeGap]:
        if not gaps:
            return None

        if len(gaps) == 1:
            return gaps[0]

        missing = []
        resolution = []

        for gap in gaps:
            missing.extend(
                gap.missing_evidence
            )
            resolution.extend(
                gap.resolution
            )

        return KnowledgeGap(
            unknown=(
                "multiple required evidence sources"
            ),
            missing_evidence=tuple(
                missing
            ),
            reason="; ".join(
                gap.reason
                for gap in gaps
            ),
            resolution=tuple(
                resolution
            ),
        )

    def collect(
        self,
        prompt: str,
    ) -> AnswerContext:
        evidence = []
        gaps = []

        for provider in self.providers:
            try:
                supported = provider.supports(
                    prompt
                )
            except Exception as error:
                gaps.append(
                    self._failure_gap(
                        provider,
                        error,
                    )
                )
                continue

            if not supported:
                continue

            try:
                context = provider.collect(
                    prompt
                )
            except Exception as error:
                gaps.append(
                    self._failure_gap(
                        provider,
                        error,
                    )
                )
                continue

            evidence.extend(
                context.evidence
            )

            if context.direct_answer is not None:
                return AnswerContext(
                    direct_answer=(
                        context.direct_answer
                    ),
                    evidence=tuple(
                        evidence
                    ),
                    gap=context.gap,
                )

            if context.gap is not None:
                gaps.append(
                    context.gap
                )

        return AnswerContext(
            evidence=tuple(evidence),
            gap=self._combine_gaps(
                tuple(gaps)
            ),
        )
