"""Stable launcher, retained in the extracted install folder (launcher protocol 1)."""
import os,sys,subprocess,time,uuid,shutil
from contextlib import contextmanager
from pathlib import Path
from updates import DATA,UpdateError,atomic_json,read_json,version
from version import VERSION

@contextmanager
def single_instance(root):
    root.mkdir(parents=True,exist_ok=True)
    handle=open(root/'launcher.lock','a+b');handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close();raise UpdateError('Das Control Center läuft bereits. Bitte das vorhandene Fenster öffnen.')
    try:yield
    finally:handle.close()

def release(root,v):
    version(v)
    path=root/'releases'/v
    if not (path/'main.py').is_file():raise UpdateError('Die installierte Version ist unvollständig.')
    return path

def rollback(state):
    old=state.get('previous')
    if not old:raise UpdateError('Es ist noch keine vorherige Version verfügbar.')
    return dict(current=old,previous=None,failed_version=state['current'])

def launch(root=DATA):
    with single_instance(root):
        state_path=root/'update_state.json'
        state=read_json(state_path,{})
        if not state:
            dest=root/'releases'/VERSION;dest.mkdir(parents=True,exist_ok=True)
            for p in Path(__file__).parent.iterdir():
                if p.is_file() and p.suffix in ('.py','.txt','.bat','.md','.json'):shutil.copyfile(p,dest/p.name)
            state={'current':VERSION,'previous':None};atomic_json(state_path,state)
        if '--rollback' in sys.argv:
            state=rollback(state);atomic_json(state_path,state)
            (root/'pending_update.json').unlink(missing_ok=True)
        pending=read_json(root/'pending_update.json',{})
        if pending:
            target=pending.get('version');release(root,target)
            if version(target)>version(state['current']):
                state=dict(current=target,previous=state['current'],failed_version=state.get('failed_version'))
                atomic_json(state_path,state)
            (root/'pending_update.json').unlink(missing_ok=True)
        for attempt in range(2):
            path=release(root,state['current'])
            marker=root/('ready-'+uuid.uuid4().hex)
            env=os.environ.copy();env['LOBBY_READY_FILE']=str(marker);env['LOBBY_LAUNCHER']='1'
            child=subprocess.Popen([sys.executable,str(path/'main.py')],cwd=path,env=env)
            deadline=time.monotonic()+45
            while child.poll() is None and not marker.exists() and time.monotonic()<deadline:time.sleep(.1)
            ready=marker.exists();marker.unlink(missing_ok=True)
            if ready:return child.wait()
            if child.poll() is None:child.terminate();child.wait(timeout=10)
            if attempt==0 and state.get('previous'):
                state=rollback(state);atomic_json(state_path,state)
                print('Neue Version konnte nicht starten. Vorherige Version wird wiederhergestellt.')
            else:raise UpdateError('Die App konnte nicht starten. Bitte die Fehlermeldung im Fenster prüfen.')

if __name__=='__main__':
    try:sys.exit(launch())
    except (UpdateError,OSError,ValueError) as exc:
        print('Startfehler:',str(exc));sys.exit(1)
