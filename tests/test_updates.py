import hashlib,json,tempfile,unittest,zipfile,io
from pathlib import Path
from unittest.mock import patch
from build_update import build
from updates import check_and_stage,inspect_zip,UpdateError
from launcher import rollback
from version import VERSION

class UpdatesTest(unittest.TestCase):
    def test_release_roundtrip_and_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);url='https://example.com/update.zip'
            build(url,root/'dist')
            raw=(root/'dist'/f'the-lobby-control-center-v{VERSION}.zip').read_bytes()
            manifest=(root/'dist'/'release.json').read_bytes()
            self.assertEqual(inspect_zip(raw)[0],VERSION)
            fetch=lambda url,limit: manifest if url.endswith('json') else raw
            check_and_stage('https://example.com/release.json','0.1.5',root,fetch)
            self.assertEqual(json.loads((root/'pending_update.json').read_text())['version'],VERSION)
            broken=json.loads(manifest);broken['sha256']='0'*64
            with self.assertRaises(UpdateError):
                check_and_stage('https://example.com/release.json','0.1.5',root/'bad',lambda url,limit:json.dumps(broken).encode() if url.endswith('json') else raw)
            self.assertFalse((root/'bad'/'pending_update.json').exists())
    def test_reject_path_traversal(self):
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as z:z.writestr('the-lobby-control-center/../evil.py','bad')
        with self.assertRaises(UpdateError):inspect_zip(raw.getvalue())
    def test_rollback_remembers_failed_version(self):
        self.assertEqual(rollback({'current':'0.1.6','previous':'0.1.5'}),{'current':'0.1.5','previous':None,'failed_version':'0.1.6'})
