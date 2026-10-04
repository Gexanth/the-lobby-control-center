"""Create desktop and Start menu shortcuts without changing user taskbar pins."""
import os,subprocess,sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from app_icon import write_ico

def main():
    if os.name!='nt':raise RuntimeError('Die Verknüpfung ist für Windows vorgesehen.')
    root=Path(__file__).resolve().parent
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file():raise RuntimeError('pythonw.exe fehlt. Bitte Python vollständig installieren.')
    app=QApplication([]);write_ico(root/'lobby.ico')
    env=os.environ.copy()
    env.update(LOBBY_SHORTCUT_ROOT=str(root),LOBBY_SHORTCUT_PYTHON=str(pythonw))
    script=r'''
$ErrorActionPreference = 'Stop'
$root = $env:LOBBY_SHORTCUT_ROOT
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$programs = [Environment]::GetFolderPath('Programs')
foreach ($folder in @($desktop, $programs)) {
    $link = $shell.CreateShortcut((Join-Path $folder 'The Lobby Control Center.lnk'))
    $link.TargetPath = $env:LOBBY_SHORTCUT_PYTHON
    $link.Arguments = '"' + (Join-Path $root 'desktop_start.py') + '"'
    $link.WorkingDirectory = $root
    $link.IconLocation = (Join-Path $root 'lobby.ico') + ',0'
    $link.Description = 'The Lobby Control Center mit automatischen Updates'
    $link.Save()
}
'''
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,check=True)
    print('Verknüpfungen erstellt. Im Startmenü nach The Lobby Control Center suchen,')
    print('Rechtsklick -> An Taskleiste anheften. Den Programmordner danach nicht verschieben.')
if __name__=='__main__':main()
