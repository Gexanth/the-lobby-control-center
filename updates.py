"""Source-release updater. Trust is in the configured HTTPS release publisher."""
import hashlib,json,os,re,shutil,stat,tempfile,zipfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request,urlopen

DATA=Path(os.environ.get('LOBBY_DATA_DIR',str(Path.home()/'.the_lobby_control_center')))
DEFAULT_UPDATE_URL="https://github.com/Gexanth/the-lobby-control-center/releases/latest/download/release.json"
MAX_ZIP=25*1024*1024
REQUIRED={'main.py','storage.py','lobby.py','channel_actions.py','ai_assistant.py','updates.py','update_ui.py','version.py','requirements.txt'}
class UpdateError(RuntimeError):pass

def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,4}\.\d{1,4}\.\d{1,4}',value):raise UpdateError('Ungültige Versionsnummer.')
    return tuple(map(int,value.split('.')))

def read_json(path,default):
    if not path.exists():return default
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):raise UpdateError('Update-Konfiguration ist nicht lesbar.') from None

def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)

def https(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:raise UpdateError('Eine vollständige HTTPS-Adresse ohne Zugangsdaten eingeben.')
    return url

def fetch(url,limit):
    https(url)
    try:
        with urlopen(Request(url,headers={'User-Agent':'TheLobby-Updater/1'}),timeout=30) as r:
            https(r.url)
            content=r.read(limit+1)
        if len(content)>limit:raise UpdateError('Update-Datei ist zu groß.')
        return content
    except UpdateError:raise
    except Exception:raise UpdateError('Update-Quelle nicht erreichbar. Die installierte Version bleibt erhalten.') from None

def inspect_zip(raw):
    import io
    try:
        archive=zipfile.ZipFile(io.BytesIO(raw))
        files={};size=0
        for info in archive.infolist():
            if info.is_dir():continue
            path=PurePosixPath(info.filename)
            if '\\' in info.filename or path.is_absolute() or '..' in path.parts or len(path.parts)!=2 or path.parts[0]!='the-lobby-control-center':raise UpdateError('Unzulässiger Dateipfad im Update.')
            if stat.S_ISLNK(info.external_attr>>16):raise UpdateError('Verknüpfungen sind im Update nicht erlaubt.')
            filename=path.name
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',filename) or filename.lower() in {x.lower() for x in files}:raise UpdateError('Ungültiger oder doppelter Dateiname im Update.')
            if Path(filename).suffix not in ('.py','.txt','.md','.bat','.json'):raise UpdateError('Nicht unterstützte Datei im Update.')
            size+=info.file_size
            if size>MAX_ZIP or info.file_size>5*1024*1024:raise UpdateError('Entpacktes Update ist zu groß.')
            files[filename]=archive.read(info)
        if not REQUIRED.issubset(files):raise UpdateError('Das Update-Paket ist unvollständig.')
        match=re.fullmatch(r"\s*VERSION\s*=\s*['\"](\d+\.\d+\.\d+)['\"]\s*",files['version.py'].decode('utf-8'))
        if not match:raise UpdateError('Versionsdatei ist ungültig.')
        v=match.group(1);version(v)
        return v,files
    except UpdateError:raise
    except Exception:raise UpdateError('Die ZIP-Datei ist beschädigt oder ungültig.') from None

def stage(raw,current,expected=None,root=DATA):
    if len(raw)>MAX_ZIP:raise UpdateError('Update-Datei ist zu groß.')
    v,files=inspect_zip(raw)
    if version(v)<=version(current):raise UpdateError('Dieses Paket ist nicht neuer als die laufende Version.')
    if expected and v!=expected:raise UpdateError('Paketversion stimmt nicht mit der Ankündigung überein.')
    if files['requirements.txt'].strip()!=Path(__file__).with_name('requirements.txt').read_bytes().strip():raise UpdateError('Dieses Update benötigt neue Abhängigkeiten. Bitte vollständig manuell installieren.')
    releases=root/'releases';releases.mkdir(parents=True,exist_ok=True)
    target=releases/v
    state=read_json(root/'update_state.json',{})
    if v in (state.get('current'),state.get('previous')):raise UpdateError('Diese Version wird bereits verwendet.')
    temporary=Path(tempfile.mkdtemp(prefix='stage-',dir=releases))
    try:
        for filename,data in files.items():(temporary/filename).write_bytes(data)
        if target.exists():shutil.rmtree(target)
        os.replace(temporary,target)
        atomic_json(root/'pending_update.json',{'version':v})
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return f'Version {v} ist bereit. App schließen und mit start.bat erneut öffnen.'

def check_and_stage(url,current,root=DATA,fetcher=fetch):
    try:manifest=json.loads(fetcher(https(url),65536))
    except UpdateError:raise
    except Exception:raise UpdateError('Die Update-Ankündigung ist kein gültiges JSON.') from None
    if not isinstance(manifest,dict):raise UpdateError('Ungültige Update-Ankündigung.')
    v=manifest.get('version');version(v)
    if manifest.get('format')!='lobby-source-v1' or manifest.get('launcher_version')!=1:raise UpdateError('Dieses Update benötigt einen neueren Starter oder ein anderes Paketformat.')
    if version(v)<=version(current):return 'Du verwendest bereits die aktuelle Version.'
    state=read_json(root/'update_state.json',{})
    if state.get('failed_version')==v:raise UpdateError('Diese Version wurde nach einem Startfehler zurückgesetzt. Warte auf eine korrigierte Version.')
    if read_json(root/'pending_update.json',{}).get('version')==v:return f'Version {v} wartet auf den nächsten Start.'
    sha=manifest.get('sha256','')
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):raise UpdateError('Prüfsumme fehlt oder ist ungültig.')
    raw=fetcher(https(manifest.get('url','')),MAX_ZIP)
    if hashlib.sha256(raw).hexdigest()!=sha:raise UpdateError('Die Prüfsumme stimmt nicht. Das Update wurde verworfen.')
    return stage(raw,current,v,root)
