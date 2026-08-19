import unittest
from thrilla.research import DownloadDisposition, classify_download
class SafeDownloadTests(unittest.TestCase):
    def test_safe_research_files(self):
        for name,mime in [('report.pdf','application/pdf'),('notes.txt','text/plain'),('data.csv','text/csv'),('photo.png','image/png')]:
            with self.subTest(name=name): self.assertIs(classify_download(name,mime).disposition,DownloadDisposition.SAFE_RESEARCH)
    def test_runnable_files_require_execution_authorization(self):
        for name,mime in [('setup.exe','application/octet-stream'),('install.sh','text/x-shellscript'),('tool.py','text/x-python'),('update.apk','application/vnd.android.package-archive'),('run.ps1','text/plain')]:
            with self.subTest(name=name): self.assertIs(classify_download(name,mime).disposition,DownloadDisposition.REQUIRES_EXECUTION_AUTHORIZATION)
