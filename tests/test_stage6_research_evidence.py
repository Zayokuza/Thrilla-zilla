import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from thrilla.app import ThrillaApp
from thrilla.research import (
    FetchedDocument,
    ResearchCache,
    ResearchEngine,
    SearchHit,
)


class OneHitSearch:
    def search(self, query, limit=8):
        del query, limit
        return (
            SearchHit(
                "https://example.com/evidence",
                "Evidence",
                "",
            ),
        )


class OneDocFetcher:
    def fetch(self, url):
        return FetchedDocument(
            url,
            200,
            "text/plain",
            "timestamped evidence",
        )


class Stage6ResearchEvidenceTests(unittest.TestCase):
    def test_live_evidence_records_utc_retrieval_time(self):
        with tempfile.TemporaryDirectory() as root:
            result = ResearchEngine(
                search=OneHitSearch(),
                fetcher=OneDocFetcher(),
                cache=ResearchCache(
                    Path(root),
                    max_entries=8,
                    max_age_seconds=60,
                ),
                max_workers=1,
            ).research(
                "timestamp proof",
                evidence_target=1,
                search_limit=1,
            )

        item = result.evidence[0]

        self.assertTrue(
            hasattr(item, "retrieved_at"),
            "research evidence must record retrieval time",
        )

        parsed = datetime.fromisoformat(
            item.retrieved_at.replace("Z", "+00:00")
        )

        self.assertEqual(
            parsed.utcoffset(),
            timezone.utc.utcoffset(parsed),
        )

    def test_rendered_research_shows_retrieval_time(self):
        timestamp = "2026-08-20T03:26:00+00:00"
        result = SimpleNamespace(
            evidence=(
                SimpleNamespace(
                    title="Evidence",
                    url="https://example.com/evidence",
                    text="timestamped evidence",
                    retrieved_at=timestamp,
                ),
            ),
            errors=(),
        )

        rendered = ThrillaApp._format_research_result(result)

        self.assertIn(
            "Retrieved: " + timestamp,
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
