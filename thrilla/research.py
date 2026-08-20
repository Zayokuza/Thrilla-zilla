"""Stage-5 read-only research, cache, evidence, and safe-download policy."""
import hashlib, html, json, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote_plus, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from .network_auth import NetworkOperation

def normalize_url(url):
    p=urlsplit(str(url).strip())
    if not p.scheme or not p.hostname: raise ValueError('url must be absolute')
    scheme=p.scheme.lower(); host=p.hostname.lower().rstrip('.'); port=p.port
    if port and not ((scheme=='https' and port==443) or (scheme=='http' and port==80)): host=f'{host}:{port}'
    return urlunsplit((scheme,host,p.path or '/',p.query,''))

@dataclass(frozen=True)
class SearchHit: url:str; title:str=''; snippet:str=''
@dataclass(frozen=True)
class FetchedDocument: url:str; status:int; content_type:str; text:str
@dataclass(frozen=True)
class ResearchEvidence: url:str; title:str; text:str; digest:str; retrieved_at:str=''
@dataclass(frozen=True)
class ResearchResult: query:str; evidence:Tuple[ResearchEvidence,...]; errors:Tuple[str,...]; cache_hits:int=0

class DownloadDisposition(str,Enum):
    SAFE_RESEARCH='safe_research'; REQUIRES_EXECUTION_AUTHORIZATION='requires_execution_authorization'
@dataclass(frozen=True)
class DownloadClassification: filename:str; content_type:str; disposition:DownloadDisposition; reason:str
_RUN={'.apk','.appimage','.bat','.cmd','.com','.deb','.exe','.jar','.msi','.ps1','.py','.rpm','.sh','.bash','.zsh'}
_RUN_MIME={'application/java-archive','application/vnd.android.package-archive','application/x-debian-package','application/x-executable','application/x-msdownload','application/x-sh','text/x-python','text/x-shellscript'}
def classify_download(filename,content_type=''):
    name=str(filename); mime=str(content_type).split(';',1)[0].strip().lower()
    if Path(name.lower()).suffix in _RUN or mime in _RUN_MIME:
        return DownloadClassification(name,mime,DownloadDisposition.REQUIRES_EXECUTION_AUTHORIZATION,'Runnable content requires separate authorization.')
    return DownloadClassification(name,mime,DownloadDisposition.SAFE_RESEARCH,'Non-runnable research content is read-only eligible.')

class _Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.ignore=0
    def handle_starttag(self,tag,attrs):
        if tag.lower() in {'script','style','noscript'}: self.ignore+=1
    def handle_endtag(self,tag):
        if tag.lower() in {'script','style','noscript'} and self.ignore: self.ignore-=1
    def handle_data(self,data):
        if not self.ignore:
            x=' '.join(data.split())
            if x: self.parts.append(x)
def html_to_text(value):
    p=_Text(); p.feed(value); return html.unescape(' '.join(p.parts))

class _Redirects(HTTPRedirectHandler):
    def __init__(self,maximum): super().__init__(); self.maximum=max(0,int(maximum)); self.count=0
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        self.count+=1
        if self.count>self.maximum: raise RuntimeError('redirect limit exceeded')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class HTTPFetcher:
    def __init__(self,policy=None,timeout=15.0,max_bytes=2_000_000,redirects=5,user_agent='Thrilla-zilla/Stage5'):
        self.policy=policy; self.timeout=float(timeout); self.max_bytes=int(max_bytes); self.redirects=int(redirects); self.user_agent=user_agent
    def fetch(self,url):
        target=normalize_url(url)
        if self.policy is not None: self.policy.require(NetworkOperation.PUBLIC_READ,target)
        req=Request(target,headers={'User-Agent':self.user_agent},method='GET')
        with build_opener(_Redirects(self.redirects)).open(req,timeout=self.timeout) as r:
            body=r.read(self.max_bytes+1)
            if len(body)>self.max_bytes: raise RuntimeError('response exceeds configured byte limit')
            mime=r.headers.get_content_type(); charset=r.headers.get_content_charset() or 'utf-8'; status=int(getattr(r,'status',200))
        return FetchedDocument(target,status,mime,body.decode(charset,errors='replace'))

class _DDG(HTMLParser):
    def __init__(self): super().__init__(); self.hits=[]; self.href=None; self.text=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag.lower()=='a' and 'result__a' in a.get('class','') and a.get('href'):
            href=a['href']
            if href.startswith('//duckduckgo.com/l/?'):
                href=parse_qs(urlsplit('https:'+href).query).get('uddg',[href])[0]
            self.href=href; self.text=[]
    def handle_data(self,data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self,tag):
        if tag.lower()=='a' and self.href is not None:
            self.hits.append(SearchHit(self.href,' '.join(''.join(self.text).split()),'')); self.href=None; self.text=[]
class DuckDuckGoHTMLSearch:
    def __init__(self,fetcher): self.fetcher=fetcher
    def search(self,query,limit=8):
        d=self.fetcher.fetch('https://html.duckduckgo.com/html/?q='+quote_plus(str(query))); p=_DDG(); p.feed(d.text); return tuple(p.hits[:max(0,int(limit))])

class ResearchCache:
    def __init__(self,state_root,max_entries=256,max_age_seconds=3600):
        self.root=Path(state_root)/'research-cache'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'documents.json'; self.max_entries=max(1,int(max_entries)); self.max_age_seconds=max(0.0,float(max_age_seconds)); self.lock=threading.RLock(); self.items={}; self._load()
    def _load(self):
        try: p=json.loads(self.path.read_text(encoding='utf-8'))
        except (FileNotFoundError,OSError,json.JSONDecodeError): return
        if isinstance(p,dict): self.items=p
    def _save(self):
        t=self.path.with_suffix('.tmp'); t.write_text(json.dumps(self.items,indent=2,sort_keys=True)+'\n',encoding='utf-8'); t.replace(self.path)
    def get(self,url):
        key=normalize_url(url)
        with self.lock:
            item=self.items.get(key)
            if not isinstance(item,dict): return None
            if self.max_age_seconds and time.time()-float(item.get('stored_at',0))>self.max_age_seconds:
                self.items.pop(key,None); self._save(); return None
            try: return FetchedDocument(**item['document'])
            except (KeyError,TypeError): return None
    def put(self,doc):
        key=normalize_url(doc.url)
        with self.lock:
            self.items[key]={'stored_at':time.time(),'document':asdict(FetchedDocument(key,doc.status,doc.content_type,doc.text))}
            while len(self.items)>self.max_entries:
                oldest=min(self.items,key=lambda k:float(self.items[k].get('stored_at',0))); self.items.pop(oldest,None)
            self._save()
    def entry_count(self):
        with self.lock: return len(self.items)

class ResearchEngine:
    def __init__(self,search,fetcher,cache,max_workers=3): self.search=search; self.fetcher=fetcher; self.cache=cache; self.max_workers=max(1,int(max_workers))
    def _one(self,hit):
        url=normalize_url(hit.url); cached=self.cache.get(url)
        if cached is not None: return hit,cached,True
        doc=self.fetcher.fetch(url); self.cache.put(doc); return hit,doc,False
    def research(self,query,evidence_target=5,search_limit=8,job_context=None):
        if job_context is not None: job_context.checkpoint('research.search',next_action='research.fetch')
        hits=[]; seen=set()
        for h in self.search.search(query,limit=search_limit):
            try: url=normalize_url(h.url)
            except ValueError: continue
            if url not in seen: seen.add(url); hits.append(SearchHit(url,h.title,h.snippet))
        evidence=[]; errors=[]; cache_hits=0; digests=set(); target=max(1,int(evidence_target))
        if job_context is not None: job_context.checkpoint('research.fetch',next_action='research.evidence',total_steps=len(hits))
        with ThreadPoolExecutor(max_workers=self.max_workers,thread_name_prefix='thrilla-research') as pool:
            futures={pool.submit(self._one,h):h for h in hits}
            for future in as_completed(futures):
                h=futures[future]
                try: resolved,doc,cached=future.result()
                except Exception as e: errors.append(f'{h.url}: {type(e).__name__}: {e}'); continue
                if cached: cache_hits+=1
                text=html_to_text(doc.text) if doc.content_type=='text/html' else ' '.join(doc.text.split())
                if not text: continue
                digest=hashlib.sha256(text.encode()).hexdigest()
                if digest in digests: continue
                digests.add(digest)
                evidence.append(
                    ResearchEvidence(
                        normalize_url(doc.url),
                        resolved.title,
                        text[:4000],
                        digest,
                        datetime.now(timezone.utc).isoformat(),
                    )
                )
                if len(evidence)>=target:
                    for p in futures:
                        if not p.done(): p.cancel()
                    break
        if job_context is not None: job_context.checkpoint('research.evidence',next_action='finish',evidence_count=len(evidence))
        return ResearchResult(str(query),tuple(evidence),tuple(errors),cache_hits)
