"""Bot credentials in Windows Credential Manager; no plaintext token files."""
import os,ctypes
from ctypes import wintypes
from updates import DATA,read_json,atomic_json
TARGET='TheLobby.ControlCenter.DiscordBot'
class CredentialError(RuntimeError):pass
class CREDENTIAL(ctypes.Structure):
    _fields_=[('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]
def api():
    if os.name!='nt':raise CredentialError('Geschütztes Token-Speichern wird nur unter Windows unterstützt.')
    a=ctypes.WinDLL('Advapi32.dll',use_last_error=True)
    a.CredWriteW.argtypes=[ctypes.POINTER(CREDENTIAL),wintypes.DWORD];a.CredWriteW.restype=wintypes.BOOL
    a.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(CREDENTIAL))];a.CredReadW.restype=wintypes.BOOL
    a.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD];a.CredDeleteW.restype=wintypes.BOOL
    a.CredFree.argtypes=[ctypes.c_void_p];a.CredFree.restype=None
    return a

def save_token(token):
    a=api();raw=token.encode('utf-16-le')
    if len(raw)>2560:raise CredentialError('Bot-Token ist zu lang.')
    blob=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw)
    c=CREDENTIAL();c.Type=1;c.TargetName=TARGET;c.CredentialBlobSize=len(raw);c.CredentialBlob=blob;c.Persist=2;c.UserName='DiscordBot'
    if not a.CredWriteW(ctypes.byref(c),0):raise CredentialError('Windows konnte das Bot-Token nicht geschützt speichern.')

def load_token():
    a=api();ptr=ctypes.POINTER(CREDENTIAL)()
    if not a.CredReadW(TARGET,1,0,ctypes.byref(ptr)):
        if ctypes.get_last_error()==1168:return ''
        raise CredentialError('Windows konnte das gespeicherte Bot-Token nicht lesen.')
    try:return ctypes.string_at(ptr.contents.CredentialBlob,ptr.contents.CredentialBlobSize).decode('utf-16-le')
    finally:a.CredFree(ptr)

def delete_token():
    a=api()
    if not a.CredDeleteW(TARGET,1,0) and ctypes.get_last_error()!=1168:raise CredentialError('Windows konnte das gespeicherte Bot-Token nicht löschen.')

def save_login(token,guild,root=DATA):
    save_token(token)
    atomic_json(root/'discord_login.json',{'guild_id':guild,'remember':True})
def forget_login(root=DATA):
    if os.name=='nt':delete_token()
    (root/'discord_login.json').unlink(missing_ok=True)
def load_login(root=DATA):
    config=read_json(root/'discord_login.json',{})
    if not isinstance(config,dict):raise CredentialError('Gespeicherte Discord-Einstellungen sind ungültig.')
    return (load_token() if config.get('remember') and os.name=='nt' else '',str(config.get('guild_id','')),config.get('remember') is True)
