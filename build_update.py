"""Build a ZIP and release.json for an HTTPS publisher; does not publish files."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from updates import https
from version import VERSION

def build(url,out):
    https(url);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    package=out/f'the-lobby-control-center-v{VERSION}.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(__file__).parent.iterdir()):
            if p.is_file() and p.suffix in ('.py','.txt','.md','.bat','.json'):
                z.write(p,'the-lobby-control-center/'+p.name)
    manifest={'format':'lobby-source-v1','launcher_version':1,'version':VERSION,'url':url,'sha256':hashlib.sha256(package.read_bytes()).hexdigest()}
    (out/'release.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(package)
    print(out/'release.json')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',required=True,help='Final HTTPS download URL of the ZIP');parser.add_argument('--out',default='dist/updates')
    args=parser.parse_args();build(args.url,args.out)
