import tempfile, unittest
from pathlib import Path
from thrilla.research import FetchedDocument, ResearchCache
class ResearchCacheTests(unittest.TestCase):
    def test_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root); c=ResearchCache(p,max_entries=4,max_age_seconds=3600); c.put(FetchedDocument('https://example.com/doc',200,'text/plain','cached'))
            loaded=ResearchCache(p,max_entries=4,max_age_seconds=3600).get('https://example.com/doc')
            self.assertIsNotNone(loaded); self.assertEqual(loaded.text,'cached')
    def test_enforces_entry_bound(self):
        with tempfile.TemporaryDirectory() as root:
            c=ResearchCache(Path(root),max_entries=2,max_age_seconds=3600)
            for i in range(3): c.put(FetchedDocument(f'https://example.com/{i}',200,'text/plain',str(i)))
            self.assertLessEqual(c.entry_count(),2)
