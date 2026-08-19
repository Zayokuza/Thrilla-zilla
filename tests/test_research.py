import tempfile, threading, time, unittest
from pathlib import Path
from thrilla.research import FetchedDocument, ResearchCache, ResearchEngine, SearchHit, normalize_url

class FakeSearch:
    def __init__(self, hits): self.hits = tuple(hits)
    def search(self, query, limit=8): return self.hits[:limit]

class FakeFetcher:
    def __init__(self, docs, delay=0):
        self.docs=dict(docs); self.delay=delay; self.lock=threading.Lock(); self.active=0; self.peak=0; self.calls=[]
    def fetch(self, url):
        with self.lock:
            self.active += 1; self.peak=max(self.peak,self.active); self.calls.append(url)
        try:
            if self.delay: time.sleep(self.delay)
            value=self.docs[url]
            if isinstance(value, Exception): raise value
            return value
        finally:
            with self.lock: self.active -= 1

class ResearchTests(unittest.TestCase):
    def test_url_normalization(self):
        self.assertEqual(normalize_url('HTTPS://Example.COM:443/a?b=1#x'),'https://example.com/a?b=1')
    def test_dedup_url_and_content(self):
        hits=[SearchHit('https://EXAMPLE.com/a#x','A',''),SearchHit('https://example.com/a','A2',''),SearchHit('https://example.com/b','B','')]
        docs={u:FetchedDocument(u,200,'text/plain','same evidence') for u in ('https://example.com/a','https://example.com/b')}
        f=FakeFetcher(docs)
        with tempfile.TemporaryDirectory() as root:
            r=ResearchEngine(search=FakeSearch(hits),fetcher=f,cache=ResearchCache(Path(root),max_entries=8,max_age_seconds=60),max_workers=2).research('q',evidence_target=5)
        self.assertEqual(len(r.evidence),1); self.assertEqual(len(f.calls),2)
    def test_parallel_fetch_is_bounded(self):
        hits=[SearchHit(f'https://example.com/{i}',str(i),'') for i in range(5)]
        docs={h.url:FetchedDocument(h.url,200,'text/plain',f'evidence {i}') for i,h in enumerate(hits)}
        f=FakeFetcher(docs,0.04)
        with tempfile.TemporaryDirectory() as root:
            r=ResearchEngine(search=FakeSearch(hits),fetcher=f,cache=ResearchCache(Path(root),max_entries=8,max_age_seconds=60),max_workers=3).research('q',evidence_target=5)
        self.assertEqual(len(r.evidence),5); self.assertGreaterEqual(f.peak,2); self.assertLessEqual(f.peak,3)
    def test_fetch_errors_are_reported(self):
        hits=[SearchHit('https://example.com/good','G',''),SearchHit('https://example.com/bad','B','')]
        docs={'https://example.com/good':FetchedDocument('https://example.com/good',200,'text/plain','verified'),'https://example.com/bad':RuntimeError('network failed')}
        with tempfile.TemporaryDirectory() as root:
            r=ResearchEngine(search=FakeSearch(hits),fetcher=FakeFetcher(docs),cache=ResearchCache(Path(root),max_entries=8,max_age_seconds=60),max_workers=2).research('q')
        self.assertEqual(len(r.evidence),1); self.assertEqual(len(r.errors),1); self.assertIn('network failed',r.errors[0])
