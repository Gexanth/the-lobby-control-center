"""Windowless entry point for the permanent Windows launcher folder."""
import sys,traceback
from updates import DATA
from launcher import launch

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    # pythonw has no stdout/stderr; keep diagnostics available on disk.
    with (DATA/'startup.log').open('a',encoding='utf-8',buffering=1) as log:
        sys.stdout=sys.stderr=log
        try:return launch()
        except Exception as exc:
            traceback.print_exc()
            from PySide6.QtWidgets import QApplication,QMessageBox
            app=QApplication.instance() or QApplication([])
            QMessageBox.critical(None,'The Lobby – Startfehler',f'{exc}\n\nDetails: {DATA / "startup.log"}')
            return 1
if __name__=='__main__':sys.exit(main())
