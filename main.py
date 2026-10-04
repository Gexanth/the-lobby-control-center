import sys
import os
import json
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,
    QCheckBox,QPushButton,QLabel,QStackedWidget,QFrame,QLineEdit,QTextEdit,QListWidget,QMessageBox,QComboBox,QListWidgetItem,QTabWidget)
from storage import TaskStore, STATUSES
from lobby import Lobby, DiscordError
from channel_actions import ChannelActions
from ai_assistant import request_plan, AIError
from update_ui import UpdatePage
from updates import UpdateError
from credentials import load_login,save_login,forget_login,CredentialError
from version import VERSION
from app_icon import icon,APP_ID

APP_DIR = Path(os.environ.get('LOBBY_DATA_DIR',str(Path.home() / '.the_lobby_control_center')))
APP_DIR.mkdir(exist_ok=True)
TASK_FILE = APP_DIR / 'tasks.json'

class DiscordWorker(QThread):
    def __init__(self, action):
        super().__init__()
        self.action=action
        self.result=None
        self.error=None

    def run(self):
        try: self.result=self.action()
        except (DiscordError,AIError,UpdateError,ValueError) as exc: self.error=str(exc)
        except Exception: self.error='Vorgang konnte nicht abgeschlossen werden. Bitte die Serverübersicht prüfen.'
        finally: self.action=None

class Page(QWidget):
    def __init__(self, title, subtitle=''):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32,28,32,28)
        h = QLabel(title); h.setObjectName('title')
        self.layout.addWidget(h)
        if subtitle:
            s=QLabel(subtitle); s.setObjectName('subtitle'); s.setWordWrap(True); self.layout.addWidget(s)
        self.layout.addSpacing(18)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = TaskStore(TASK_FILE)
        self.discord_client=None
        self.discord_worker=None
        self.server_context=None
        self.ai_history=[]
        self.pending_ai=None
        self.openai_api_key=""
        self.setWindowTitle('The Lobby Control Center — '+VERSION)
        self.resize(1180,760)
        root=QWidget(); self.setCentralWidget(root)
        shell=QHBoxLayout(root); shell.setContentsMargins(0,0,0,0); shell.setSpacing(0)

        sidebar=QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(235)
        side=QVBoxLayout(sidebar); side.setContentsMargins(18,24,18,24)
        brand=QLabel('THE LOBBY\nCONTROL CENTER'); brand.setObjectName('brand'); side.addWidget(brand); side.addSpacing(25)
        self.stack=QStackedWidget()
        nav=[('⌂  Dashboard',self.dashboard()),('✦  Assistent',self.assistant()),('◈  Discord',self.discord()),('✓  Aufgaben',self.tasks()),('⚡  Automationen',self.automations()),('⚙  Einstellungen',self.settings()),('↻  Updates',self.update_page())]
        for i,(name,page) in enumerate(nav):
            b=QPushButton(name); b.setObjectName('nav'); b.clicked.connect(lambda _,x=i:self.stack.setCurrentIndex(x)); side.addWidget(b); self.stack.addWidget(page)
        side.addStretch(); version=QLabel('Version '+VERSION); version.setObjectName('muted'); side.addWidget(version)
        shell.addWidget(sidebar); shell.addWidget(self.stack,1)
        self.apply_style()
        self.refresh_tasks()

    def card(self,title,text):
        f=QFrame(); f.setObjectName('card'); l=QVBoxLayout(f); t=QLabel(title); t.setObjectName('cardTitle'); d=QLabel(text); d.setWordWrap(True); d.setObjectName('muted'); l.addWidget(t); l.addWidget(d); return f

    def dashboard(self):
        p=Page('Dashboard','Zentrale für The Lobby, Aufgaben und den integrierten Assistenten.')
        row=QHBoxLayout(); row.addWidget(self.card('Discord','Verbindung unter Discord prüfen; Kanäle und Rollen anzeigen.')); row.addWidget(self.card('Aufgaben','Aufträge lokal speichern und verwalten.')); row.addWidget(self.card('Assistent','Befehle natürlich formulieren.'))
        p.layout.addLayout(row); self.summary=QLabel(); p.layout.addWidget(self.summary); p.layout.addWidget(self.card('Aktueller Stand','Aufträge speichern, bearbeiten und für die Übergabe in ChatGPT kopieren. Discord-Übersicht verfügbar. Kanäle erstellen, umbenennen und verschieben unter Discord. KI-Aufträge jetzt unter Assistent; API-Schlüssel in Einstellungen eingeben.')); p.layout.addStretch(); return p

    def assistant(self):
        p=Page('Assistent','KI-Aufträge besprechen und Kanalaktionen vorbereiten. Die Ausführung erfolgt nach einer konkreten Vorschau.')
        self.chat=QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setPlaceholderText('Beispiel: Erstelle einen Textkanal namens test in der Kategorie EVENTS.')
        self.ai_input=QLineEdit(); self.ai_input.setMaxLength(4000); self.ai_input.setPlaceholderText('Dein Auftrag oder deine Frage …')
        self.ai_send=QPushButton('An KI senden'); self.ai_send.setObjectName('primary'); self.ai_send.clicked.connect(self.ask_ai);self.ai_input.returnPressed.connect(self.ask_ai)
        self.ai_save=QPushButton('Nur als Aufgabe speichern');self.ai_save.clicked.connect(self.save_ai_task)
        self.ai_apply=QPushButton('Vorgeschlagene Aktion prüfen');self.ai_apply.setEnabled(False);self.ai_apply.clicked.connect(self.apply_ai_plan)
        self.ai_clear=QPushButton('Gespräch leeren');self.ai_clear.clicked.connect(self.clear_ai_chat)
        p.layout.addWidget(self.chat,1)
        row=QHBoxLayout();row.addWidget(self.ai_input,1);row.addWidget(self.ai_send);p.layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(self.ai_apply);row.addWidget(self.ai_save);row.addWidget(self.ai_clear);p.layout.addLayout(row)
        self.ai_status=QLabel('API-Schlüssel unter Einstellungen einrichten. Eine Kanalaktion pro Auftrag.');self.ai_status.setWordWrap(True);p.layout.addWidget(self.ai_status)
        return p

    def save_ai_task(self):
        text=self.ai_input.text().strip()
        if text and self.save_task(text):
            self.chat.insertPlainText('System: Aufgabe lokal gespeichert: '+text+'\n\n');self.ai_input.clear()

    def clear_ai_chat(self):
        if self.discord_worker is not None:return
        self.chat.clear();self.ai_history=[];self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.ai_status.setText('Gespräch geleert. Keine Discord-Aktion ausgeführt.')

    def ask_ai(self):
        if self.discord_worker is not None:return
        prompt=self.ai_input.text().strip()
        if not prompt:return
        key=self.api_key_input.text().strip() or self.openai_api_key
        if not key:
            self.ai_status.setText('Bitte zuerst unter Einstellungen den OpenAI-API-Schlüssel eingeben.');return
        if self.discord_client and key==self.discord_client.token:
            self.ai_status.setText('Das ist dein Discord-Token. Bitte stattdessen den OpenAI-API-Schlüssel eingeben.');return
        self.openai_api_key=key;self.api_key_input.clear()
        model=self.ai_model.text().strip()
        context=json.loads(json.dumps(self.server_context)) if self.server_context else None
        history=list(self.ai_history)
        self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.chat.insertPlainText('Du: '+prompt+'\n');self.ai_input.clear()
        self.ai_status.setText('KI erstellt eine Antwort …')
        def answered(result):
            self.chat.insertPlainText('Assistent: '+result['message']+'\n\n')
            self.ai_history.extend([{'role':'user','content':prompt},{'role':'assistant','content':result['message']}]);self.ai_history=self.ai_history[-8:]
            self.pending_ai=result if result['spec'] else None
            self.ai_apply.setEnabled(self.pending_ai is not None)
            self.ai_status.setText('Kanalaktion vorbereitet. Noch nicht ausgeführt.' if result['spec'] else 'Antwort erhalten. Keine Kanalaktion vorbereitet.')
        def failed(message):
            self.chat.insertPlainText('System: '+message+'\n\n');self.ai_status.setText('KI-Anfrage fehlgeschlagen. Keine Discord-Aktion ausgeführt.')
        self.run_discord_job(lambda:request_plan(key,model,prompt,context,history),answered,failed)

    def apply_ai_plan(self):
        if self.discord_worker is not None or not self.pending_ai:return
        result=self.pending_ai
        if not self.discord_client or result['guild']!=self.discord_client.guild:
            self.ai_status.setText('Bitte zuerst mit dem Server aus dem KI-Auftrag verbinden und die Anfrage erneut senden.');return
        spec=result['spec'];controls=self.channel_actions
        if spec['action']!='create' and controls.channel.findData(spec['channel'])<0:
            self.ai_status.setText('Kanal nicht mehr verfügbar. Bitte Serverübersicht aktualisieren.');return
        if spec['parent'] and controls.parent.findData(spec['parent'])<0:
            self.ai_status.setText('Zielkategorie nicht mehr verfügbar. Bitte Serverübersicht aktualisieren.');return
        controls.action.setCurrentIndex(controls.action.findData(spec['action']))
        controls.kind.setCurrentIndex(controls.kind.findData(spec['kind']))
        if spec['channel']:controls.channel.setCurrentIndex(controls.channel.findData(spec['channel']))
        controls.parent.setCurrentIndex(controls.parent.findData(spec['parent']))
        controls.channel_name.setText(spec['name']);controls.reason.setText(spec['reason'])
        self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.stack.setCurrentIndex(2);self.discord_tabs.setCurrentIndex(1)
        controls.review()

    def discord(self):
        p=Page('Discord','Verbinde deinen Bot mit The Lobby und lade die aktuelle Serverübersicht.')
        self.discord_status=QLabel('Noch nicht geprüft.'); self.discord_status.setWordWrap(True); self.discord_status.setTextFormat(Qt.PlainText)
        p.layout.addWidget(self.discord_status)
        p.layout.addWidget(QLabel('Bot-Token (optional geschützt unter Windows speichern)'))
        self.bot_token=QLineEdit(os.getenv('DISCORD_BOT_TOKEN',''))
        self.bot_token.setEchoMode(QLineEdit.Password); p.layout.addWidget(self.bot_token)
        p.layout.addWidget(QLabel('Server-ID'))
        self.guild_id=QLineEdit(os.getenv('DISCORD_GUILD_ID',''))
        self.guild_id.setPlaceholderText('17–20-stellige Discord-Server-ID'); p.layout.addWidget(self.guild_id)
        self.remember_login=QCheckBox('Zugangsdaten auf diesem Windows-PC merken')
        self.remember_login.setChecked(os.name=='nt');self.remember_login.setEnabled(os.name=='nt')
        p.layout.addWidget(self.remember_login)
        self.forget_login_button=QPushButton('Gespeicherte Zugangsdaten löschen')
        self.forget_login_button.clicked.connect(self.forget_discord_login);p.layout.addWidget(self.forget_login_button)
        try:
            saved_token,saved_guild,remembered=load_login()
            if saved_token:self.bot_token.setText(saved_token)
            if saved_guild:self.guild_id.setText(saved_guild)
            if remembered:self.remember_login.setChecked(True)
        except (CredentialError,UpdateError,OSError) as exc:self.discord_status.setText(str(exc))
        self.connect_button=QPushButton('Verbindung prüfen und Übersicht laden'); self.connect_button.setObjectName('primary')
        self.connect_button.clicked.connect(self.load_discord)
        self.disconnect_button=QPushButton('Verbindung trennen'); self.disconnect_button.clicked.connect(self.disconnect_discord)
        row=QHBoxLayout(); row.addWidget(self.connect_button);row.addWidget(self.disconnect_button);p.layout.addLayout(row)
        self.discord_output=QTextEdit(); self.discord_output.setReadOnly(True)
        self.discord_output.setPlaceholderText('Hier erscheinen Serverstatus, Kanäle und Rollen.'); self.discord_tabs=QTabWidget(); self.discord_tabs.addTab(self.discord_output,'Serverübersicht')
        self.channel_actions=ChannelActions(self); self.discord_tabs.addTab(self.channel_actions,'Kanäle verwalten')
        p.layout.addWidget(self.discord_tabs,1)
        p.layout.addWidget(self.card('Stand der Anbindung','Kanalaktionen werden über das Formular ausgeführt. KI-Aufträge können unter Assistent vorbereitet werden; die Ausführung erfolgt über eine Vorschau.'))
        return p

    def set_discord_busy(self, busy):
        for widget in (self.remember_login,self.forget_login_button,self.connect_button,self.disconnect_button,self.bot_token,self.guild_id,self.channel_actions,self.ai_send,self.ai_input,self.ai_save,self.ai_clear,self.ai_apply,self.api_key_input,self.ai_model,self.forget_key_button):
            widget.setEnabled(not busy)
        if hasattr(self,'updates'):
            self.updates.setEnabled(not busy)
        if not busy:self.ai_apply.setEnabled(self.pending_ai is not None)

    def run_discord_job(self, action, success, failure):
        if self.discord_worker is not None: return
        self.set_discord_busy(True)
        worker=DiscordWorker(action); self.discord_worker=worker
        def done():
            result,error=worker.result,worker.error
            self.discord_worker=None
            self.set_discord_busy(False)
            worker.deleteLater()
            if error is not None: failure(error)
            else: success(result)
        worker.finished.connect(done)
        worker.start()

    def load_discord(self):
        if self.discord_worker is not None: return
        token=self.bot_token.text().strip()
        if not token and self.remember_login.isChecked():
            try:token=load_login()[0]
            except (CredentialError,UpdateError,OSError) as exc:
                QMessageBox.warning(self,'Zugangsdaten',str(exc));return
        if not token:
            if self.discord_client and self.discord_client.guild==self.guild_id.text().strip():
                self.refresh_discord();return
            QMessageBox.warning(self,'Konfiguration prüfen','Bot-Token und Server-ID eingeben.');return
        try: client=Lobby(token,self.guild_id.text().strip(),writes=True,db=APP_DIR/'discord.sqlite3')
        except ValueError:
            QMessageBox.warning(self,'Konfiguration prüfen','Bot-Token und gültige Server-ID eingeben.');return
        remember=self.remember_login.isChecked()
        if not remember:
            try:forget_login()
            except (CredentialError,OSError) as exc:
                QMessageBox.warning(self,'Zugangsdaten',str(exc));return
        self.disconnect_discord()
        self.bot_token.clear()
        self.discord_status.setText('Verbindung wird geprüft …')
        def connected(data):
            self.discord_client=client
            self.show_discord(data)
            if remember:
                try:save_login(client.token,client.guild)
                except (CredentialError,OSError) as exc:QMessageBox.warning(self,'Speichern fehlgeschlagen',str(exc))
        def failed(message):
            client.token=''
            self.discord_failed(message)
        self.run_discord_job(client.overview,connected,failed)

    def forget_discord_login(self):
        try:forget_login()
        except (CredentialError,OSError) as exc:
            QMessageBox.warning(self,'Löschen fehlgeschlagen',str(exc));return
        self.bot_token.clear();self.guild_id.clear();self.remember_login.setChecked(False)
        QMessageBox.information(self,'Zugangsdaten','Gespeicherte Zugangsdaten gelöscht. Eine laufende Verbindung bleibt bis zum Trennen aktiv.')

    def refresh_discord(self):
        if not self.discord_client:return
        self.discord_status.setText('Serverübersicht wird aktualisiert …')
        self.run_discord_job(self.discord_client.overview,self.show_discord,self.discord_failed)

    def disconnect_discord(self):
        if self.discord_worker is not None:return
        if self.discord_client:self.discord_client.token=''
        self.discord_client=None;self.bot_token.clear();self.server_context=None
        self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.discord_output.clear();self.channel_actions.populate([])
        self.discord_status.setText('Verbindung getrennt.')
        self.channel_actions.result.setText('Bitte zuerst die Serverübersicht laden.')

    def show_discord(self, data):
        self.server_context=data
        self.discord_status.setText(f"Verbunden: {data['name']} • Server-ID: {data['id']}")
        channels=data.get('channels',[])
        self.channel_actions.populate(channels)
        categories={x['id']:x['name'] for x in channels if x.get('type')==4}
        members=data.get('approximate_members_including_bots')
        online=data.get('online_now_not_weekly_activity')
        lines=[f"Mitglieder inkl. Bots (ungefähr): {members if members is not None else 'Nicht verfügbar'}",
               f"Gerade online (ungefähr): {online if online is not None else 'Nicht verfügbar'}",'', 'KANÄLE']
        for channel in channels:
            kind={0:'Text',2:'Voice',4:'Kategorie',5:'Ankündigung',15:'Forum'}.get(channel.get('type'),'Kanal')
            parent=categories.get(channel.get('parent_id'))
            lines.append(f"{kind}: {channel['name']}" + (f" • {parent}" if parent else '') + f" • ID {channel['id']}")
        lines.extend(['','ROLLEN'])
        for role in sorted(data.get('roles',[]),key=lambda x:x.get('position',0),reverse=True):
            lines.append(f"{role['name']} • ID {role['id']}")
        self.discord_output.setPlainText('\n'.join(lines))

    def discord_failed(self, message):
        self.discord_status.setText('Abruf fehlgeschlagen. Die Übersicht wurde nicht aktualisiert.')
        self.discord_output.setPlainText(message)

    def closeEvent(self, event):
        worker=getattr(self,'discord_worker',None)
        if worker is not None:
            self.discord_status.setText('Bitte den laufenden Abruf abwarten, bevor du die App schließt.')
            event.ignore(); return
        self.disconnect_discord()
        self.forget_ai_key()
        super().closeEvent(event)

    def tasks(self):
        p=Page('Aufgaben','Aufträge bleiben lokal gespeichert. Ein Statuswechsel führt keine Discord-Aktion aus.')
        self.filter=QComboBox(); self.filter.addItems(['Alle'] + list(STATUSES))
        self.filter.currentTextChanged.connect(self.refresh_tasks)
        p.layout.addWidget(self.filter)
        self.task_list=QListWidget(); self.task_list.currentItemChanged.connect(self.select_task)
        p.layout.addWidget(self.task_list,1)
        self.task_title=QLabel('Wähle einen Auftrag.'); self.task_title.setWordWrap(True)
        p.layout.addWidget(self.task_title)
        self.task_status=QComboBox(); self.task_status.addItems(STATUSES); p.layout.addWidget(self.task_status)
        self.notes=QTextEdit(); self.notes.setPlaceholderText('Details, Kanalnamen, Ergebnis oder offene Fragen'); self.notes.setMaximumHeight(140); p.layout.addWidget(self.notes)
        row=QHBoxLayout()
        for label, handler in [('Änderungen speichern',self.update_task),('Für ChatGPT kopieren',self.copy_task),('Auftrag löschen',self.delete_task)]:
            btn=QPushButton(label); btn.clicked.connect(handler); row.addWidget(btn)
        p.layout.addLayout(row)
        return p

    def selected_id(self):
        item=self.task_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def refresh_tasks(self, *_):
        selected=self.selected_id()
        self.task_list.clear()
        for task in self.store.items:
            if self.filter.currentText() not in ('Alle',task['status']): continue
            item=QListWidgetItem(f"{task['status']}  •  {task['text']}")
            item.setData(Qt.UserRole,task['id']); self.task_list.addItem(item)
            if task['id']==selected: self.task_list.setCurrentItem(item)
        if hasattr(self,'summary'):
            counts={status:sum(x['status']==status for x in self.store.items) for status in STATUSES}
            self.summary.setText('  •  '.join(f'{n} {status}' for status,n in counts.items()))

    def select_task(self, item, *_):
        task=next((x for x in self.store.items if item and x['id']==item.data(Qt.UserRole)),None)
        self.task_title.setText(f"{task['text']}\nErstellt: {task['created']}" if task else 'Wähle einen Auftrag.')
        self.task_status.setCurrentText(task['status'] if task else STATUSES[0])
        self.notes.setPlainText(task['notes'] if task else '')

    def mutate(self, action):
        try: action()
        except (OSError,ValueError) as exc:
            QMessageBox.critical(self,'Speichern fehlgeschlagen',str(exc)); return False
        self.refresh_tasks(); return True

    def update_task(self):
        task_id=self.selected_id()
        if task_id: self.mutate(lambda:self.store.update(task_id,self.task_status.currentText(),self.notes.toPlainText()))

    def copy_task(self):
        task_id=self.selected_id()
        if task_id and self.mutate(lambda:self.store.update(task_id,self.task_status.currentText(),self.notes.toPlainText())):
            QApplication.clipboard().setText(self.store.handoff(task_id))
            QMessageBox.information(self,'Auftrag kopiert','Füge den Auftrag in diesen Chat ein. Es wurde noch nichts an Discord gesendet.')

    def delete_task(self):
        task_id=self.selected_id()
        if task_id and QMessageBox.question(self,'Auftrag löschen','Diesen lokal gespeicherten Auftrag löschen?')==QMessageBox.Yes:
            self.mutate(lambda:self.store.delete(task_id))

    def automations(self):
        p=Page('Automationen','Wiederkehrende Abläufe werden hier später zentral verwaltet.')
        p.layout.addWidget(self.card('Beispiele','Tägliche Content-Aufgaben • wöchentlicher Serverbericht • Streamer-Onboarding • Event-Vorbereitung'))
        p.layout.addStretch(); return p

    def settings(self):
        p=Page('Einstellungen','KI-Verbindung für deinen lokalen Assistenten.')
        p.layout.addWidget(QLabel('OpenAI-API-Schlüssel (nur für die aktuelle Sitzung)'))
        link=QLabel('<a href="https://platform.openai.com/api-keys">API-Schlüssel bei OpenAI erstellen</a>');link.setOpenExternalLinks(True);p.layout.addWidget(link)
        self.api_key_input=QLineEdit(os.getenv('OPENAI_API_KEY',''));self.api_key_input.setEchoMode(QLineEdit.Password);self.api_key_input.setPlaceholderText('API-Schlüssel hier eingeben');p.layout.addWidget(self.api_key_input)
        p.layout.addWidget(QLabel('Modell (mit Responses API und strukturierten Ausgaben)'))
        self.ai_model=QLineEdit('gpt-4.1-mini');p.layout.addWidget(self.ai_model)
        self.forget_key_button=QPushButton('API-Schlüssel aus der Sitzung entfernen');self.forget_key_button.clicked.connect(self.forget_ai_key);p.layout.addWidget(self.forget_key_button)
        p.layout.addWidget(self.card('API-Nutzung','Die API kann separat berechnete Kosten verursachen. Beim Senden werden dein Auftrag, die letzten Gesprächsbeiträge und Kanalnamen sowie IDs an OpenAI übermittelt. Discord-Token, Mitglieder und Nachrichten werden nicht übertragen.'))
        p.layout.addWidget(self.card('Gespräch & Aufgaben','Das KI-Gespräch bleibt in dieser App-Sitzung. Nur ausdrücklich gespeicherte Aufgaben liegen dauerhaft in deiner Aufgabendatei.'))
        p.layout.addWidget(self.card('Aufgabendatei',str(TASK_FILE)));p.layout.addStretch();return p

    def update_page(self):
        self.updates=UpdatePage(self)
        return self.updates

    def forget_ai_key(self):
        self.openai_api_key='';self.api_key_input.clear()

    def save_task(self,text):
        return self.mutate(lambda:self.store.add(text))

    def apply_style(self):
        self.setStyleSheet('''
        * { font-family: "Segoe UI"; font-size: 14px; }
        QMainWindow,QWidget { background:#0b0e14; color:#eef2ff; }
        #sidebar { background:#10141d; border-right:1px solid #242a38; }
        #brand { font-size:18px; font-weight:800; letter-spacing:1px; color:#8ea7ff; }
        #title { font-size:30px; font-weight:800; }
        #subtitle,#muted { color:#9099aa; }
        #nav { text-align:left; padding:12px 14px; border:0; border-radius:8px; background:transparent; color:#cdd5e5; }
        #nav:hover { background:#1a2030; }
        #card { background:#121722; border:1px solid #252c3b; border-radius:12px; padding:12px; }
        #card QLabel { background:transparent; }
        QPushButton:disabled { color:#737b8c; }
        #cardTitle { font-size:17px; font-weight:700; }
        QLineEdit,QTextEdit,QListWidget,QComboBox { background:#10151f; border:1px solid #293144; border-radius:9px; padding:10px; }
        #primary { background:#536dfe; color:white; border:0; border-radius:9px; padding:11px 16px; font-weight:700; }
        #primary:hover { background:#6980ff; }
        ''')

if __name__=='__main__':
    if os.name=='nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    app=QApplication(sys.argv)
    app.setWindowIcon(icon())
    try: w=MainWindow()
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, 'Start fehlgeschlagen', f'Die Aufgabendatei konnte nicht geladen werden. Sie wird nicht überschrieben.\n{TASK_FILE}\n{exc}')
        sys.exit(1)
    w.show()
    marker=os.getenv('LOBBY_READY_FILE')
    if marker:
        QTimer.singleShot(500,lambda:Path(marker).write_text(VERSION,encoding='utf-8'))
    sys.exit(app.exec())
