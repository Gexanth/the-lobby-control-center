import os,sys
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QLineEdit,QCheckBox,QPushButton,QFileDialog
from updates import DEFAULT_UPDATE_URL,DATA,UpdateError,atomic_json,read_json,https,check_and_stage,stage,MAX_ZIP
from version import VERSION

class UpdatePage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.config={}
        layout=QVBoxLayout(self);layout.setContentsMargins(32,28,32,28)
        title=QLabel('Updates');title.setObjectName('title');layout.addWidget(title)
        layout.addWidget(QLabel('Installierte Version: '+VERSION))
        description=QLabel('Neue Versionen werden vorbereitet und beim nächsten Start über start.bat übernommen. Aufgaben und Einstellungen liegen außerhalb der Programmversionen.');description.setWordWrap(True);layout.addWidget(description)
        layout.addWidget(QLabel('Feste Update-Quelle (HTTPS-Adresse einer Release-JSON-Datei)'))
        self.url=QLineEdit();self.url.setPlaceholderText('Noch keine Downloadquelle eingerichtet');layout.addWidget(self.url)
        self.auto=QCheckBox('Neue Versionen automatisch prüfen und herunterladen');layout.addWidget(self.auto)
        notice=QLabel('Trage nur eine Quelle ein, deren Betreiber du vertraust. Updates enthalten ausführbaren Programmcode.');notice.setWordWrap(True);layout.addWidget(notice)
        self.save=QPushButton('Update-Einstellungen speichern');self.save.clicked.connect(self.save_config);layout.addWidget(self.save)
        self.check=QPushButton('Update prüfen und herunterladen');self.check.clicked.connect(self.check_now);layout.addWidget(self.check)
        self.local=QPushButton('Heruntergeladene Update-ZIP auswählen');self.local.clicked.connect(self.import_zip);layout.addWidget(self.local)
        self.status=QLabel('');self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);layout.addWidget(self.status)
        recovery=QLabel('Wiederherstellung: App schließen und restore_previous.bat aus dem ursprünglichen Programmordner öffnen. Die letzte Programmversion wird wieder aktiviert; Aufgabendaten werden nicht zurückgesetzt.');recovery.setWordWrap(True);layout.addWidget(recovery);layout.addStretch()
        try:
            self.config=read_json(DATA/'update_config.json',{'url':DEFAULT_UPDATE_URL,'auto':True})
            if not isinstance(self.config,dict):raise UpdateError('Update-Einstellungen ungültig.')
            self.url.setText(str(self.config.get('url','')));self.auto.setChecked(self.config.get('auto') is True)
            self.status.setText('Automatische Prüfung aktiviert.' if self.auto.isChecked() else 'Automatische Updates sind noch nicht aktiviert.')
        except UpdateError as exc:self.status.setText(str(exc));self.config={}
        self.supported=not getattr(sys,'frozen',False) and os.getenv('LOBBY_LAUNCHER')=='1'
        if not self.supported:
            self.status.setText('Bitte diese Quellcode-Version über start.bat starten. EXE-Updates werden noch nicht unterstützt.')
            for control in (self.save,self.check,self.local):control.setEnabled(False)
        self.timer=QTimer(self);self.timer.setInterval(6*60*60*1000);self.timer.timeout.connect(self.auto_check);self.timer.start()
        QTimer.singleShot(5000,self.auto_check)

    def save_config(self):
        try:
            url=self.url.text().strip()
            if url:https(url)
            if self.auto.isChecked() and not url:raise UpdateError('Für automatische Updates fehlt noch die Downloadquelle.')
            self.config={'url':url,'auto':self.auto.isChecked()}
            atomic_json(DATA/'update_config.json',self.config)
            self.status.setText('Gespeichert. Automatische Prüfung beim Start und alle sechs Stunden.' if self.config['auto'] else 'Gespeichert. Automatische Updates deaktiviert.')
        except (UpdateError,OSError) as exc:self.status.setText(str(exc))

    def auto_check(self):
        if self.supported and self.config.get('auto') and self.config.get('url') and self.host.discord_worker is None:self.run_check(self.config['url'])

    def check_now(self):
        if self.supported:self.run_check(self.url.text().strip())

    def run_check(self,url):
        if self.host.discord_worker is not None:return
        try:https(url)
        except UpdateError as exc:self.status.setText(str(exc));return
        self.status.setText('Update wird geprüft und gegebenenfalls heruntergeladen …')
        self.host.run_discord_job(lambda:check_and_stage(url,VERSION),self.status.setText,self.status.setText)

    def import_zip(self):
        if not self.supported or self.host.discord_worker is not None:return
        path,_=QFileDialog.getOpenFileName(self,'Update-Paket auswählen','','ZIP-Dateien (*.zip)')
        if not path:return
        def load():
            if Path(path).stat().st_size>MAX_ZIP:raise UpdateError('Die ZIP-Datei ist zu groß.')
            return stage(Path(path).read_bytes(),VERSION)
        self.host.run_discord_job(load,self.status.setText,self.status.setText)
