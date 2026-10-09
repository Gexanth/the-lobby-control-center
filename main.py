import sys
import os
import json
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QShortcut,QKeySequence,QTextCursor
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,
    QScrollArea,QProgressBar,QCheckBox,QPushButton,QLabel,QStackedWidget,QFrame,QLineEdit,QTextEdit,QListWidget,QMessageBox,QComboBox,QListWidgetItem,QTabWidget)
from storage import TaskStore, STATUSES
from task_review import TaskReview
from citations import source_index,reference_report
from lobby import Lobby, DiscordError
from channel_actions import ChannelActions
from ai_assistant import request_plan, AIError
from update_ui import UpdatePage
from updates import UpdateError
from credentials import load_login,save_login,forget_login,CredentialError
from community_ui import CommunityPage
from dashboard_ui import DashboardPage
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
        self.ai_keys={"openai":os.getenv("OPENAI_API_KEY",""),"anthropic":os.getenv("ANTHROPIC_API_KEY","")}
        self.ai_models={"openai":"gpt-4.1-mini","anthropic":"claude-sonnet-5-5"}
        self.active_ai_provider="anthropic"
        self.setWindowTitle('The Lobby Control Center — '+VERSION)
        self.resize(1180,760)
        root=QWidget(); self.setCentralWidget(root)
        shell=QHBoxLayout(root); shell.setContentsMargins(0,0,0,0); shell.setSpacing(0)

        sidebar=QFrame(); sidebar.setObjectName('sidebar'); sidebar.setFixedWidth(235)
        side=QVBoxLayout(sidebar); side.setContentsMargins(18,24,18,24)
        brand_row=QHBoxLayout();brand_icon=QLabel();brand_icon.setPixmap(icon().pixmap(34,34));brand_row.addWidget(brand_icon)
        brand=QLabel('THE LOBBY\nControl Center');brand.setObjectName('brand');brand_row.addWidget(brand,1);side.addLayout(brand_row);side.addSpacing(24)
        self.stack=QStackedWidget()
        self.nav_buttons=[]
        nav=[('Übersicht',self.dashboard()),('Assistent',self.assistant()),('Discord',self.discord()),('Aufgaben',self.tasks()),('Automationen',self.automations()),('Einstellungen',self.settings()),('Updates',self.update_page()),('Community',self.community_page())]
        for i,(name,page) in enumerate(nav):
            b=QPushButton(name); b.setObjectName('nav');b.setCheckable(True);b.setToolTip(f'{name.strip()} · Strg+{i+1}')
            b.clicked.connect(lambda _,x=i:self.stack.setCurrentIndex(x));self.nav_buttons.append(b)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setWidget(page);self.stack.addWidget(scroll)
            shortcut=QShortcut(QKeySequence(f'Ctrl+{i+1}'),self);shortcut.activated.connect(lambda x=i:self.stack.setCurrentIndex(x))
        for section,indices in [('ARBEITSBEREICH',(0,1,2,7)),('ORGANISATION',(3,4)),('SYSTEM',(5,6))]:
            heading=QLabel(section);heading.setObjectName('navSection');side.addWidget(heading)
            for index in indices:side.addWidget(self.nav_buttons[index])
            side.addSpacing(12)
        self.stack.currentChanged.connect(self.mark_navigation);self.mark_navigation(0)
        side.addStretch(); version=QLabel('Version '+VERSION); version.setObjectName('muted'); side.addWidget(version)
        shell.addWidget(sidebar); shell.addWidget(self.stack,1)
        self.connection_badge=QLabel('Discord nicht verbunden');self.statusBar().addWidget(self.connection_badge,1)
        self.busy_indicator=QProgressBar();self.busy_indicator.setRange(0,0);self.busy_indicator.setMaximumWidth(130);self.busy_indicator.hide();self.statusBar().addPermanentWidget(self.busy_indicator)
        self.apply_style()
        self.refresh_tasks()

    def card(self,title,text):
        f=QFrame(); f.setObjectName('card'); l=QVBoxLayout(f); t=QLabel(title); t.setObjectName('cardTitle'); d=QLabel(text); d.setWordWrap(True); d.setObjectName('muted'); l.addWidget(t); l.addWidget(d); return f

    def mark_navigation(self,index):
        for i,b in enumerate(self.nav_buttons):b.setChecked(i==index)

    def metric_card(self,title):
        f=QFrame();f.setObjectName('card');layout=QVBoxLayout(f)
        label=QLabel(title);label.setObjectName('muted');value=QLabel('—');value.setObjectName('metric');layout.addWidget(label);layout.addWidget(value)
        return f,value

    def dashboard(self):
        self.dashboard_page=DashboardPage(self)
        self.dashboard_values=self.dashboard_page.values
        self.dashboard_connection=self.dashboard_page.connection
        self.community_summary=self.dashboard_page.community_summary
        self.summary=self.dashboard_page.summary
        return self.dashboard_page

    def open_page(self,index,tab=None):
        self.stack.setCurrentIndex(index)
        if tab is not None:self.community.tabs.setCurrentIndex(tab)

    def refresh_dashboard(self,data=None):
        self.dashboard_page.set_connected(data)
        if not data:
            for key in ('members','online','channels'):self.dashboard_values[key].setText('—')
            self.dashboard_connection.setText('Discord nicht verbunden.');self.connection_badge.setText('Discord nicht verbunden.');return
        values={'members':data.get('approximate_members_including_bots'),'online':data.get('online_now_not_weekly_activity'),'channels':len(data.get('channels',[]))}
        for key,value in values.items():self.dashboard_values[key].setText(str(value) if value is not None else '—')
        name=data.get('name','Discord');now=datetime.now().strftime('%H:%M')
        self.dashboard_connection.setText(f'{name} · Stand {now} · Übersicht unter Discord aktualisieren')
        self.connection_badge.setText('Verbunden: '+name)

    def assistant(self):
        self.ai_source_records=[]
        self.last_ai_task_id=None
        p=Page('Assistent','KI-Aufträge besprechen und Kanalaktionen vorbereiten. Die Ausführung erfolgt nach einer konkreten Vorschau.')
        self.chat=QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setPlaceholderText('Beispiel: Erstelle einen Textkanal namens test in der Kategorie EVENTS.')
        self.ai_input=QLineEdit(); self.ai_input.setMaxLength(4000); self.ai_input.setPlaceholderText('Dein Auftrag oder deine Frage …')
        self.ai_send=QPushButton('An KI senden'); self.ai_send.setObjectName('primary'); self.ai_send.clicked.connect(self.ask_ai);self.ai_input.returnPressed.connect(self.ask_ai)
        self.ai_save=QPushButton('Nur als Aufgabe speichern');self.ai_save.clicked.connect(self.save_ai_task)
        self.ai_apply=QPushButton('Vorgeschlagene Aktion prüfen');self.ai_apply.setEnabled(False);self.ai_apply.clicked.connect(self.apply_ai_plan)
        self.ai_clear=QPushButton('Gespräch leeren');self.ai_clear.clicked.connect(self.clear_ai_chat)
        self.ai_save_selection=QPushButton('Markierten Vorschlag als Aufgabe vorbereiten');self.ai_save_selection.setEnabled(False);self.ai_save_selection.clicked.connect(self.save_ai_selection)
        self.chat.selectionChanged.connect(lambda:self.ai_save_selection.setEnabled(bool(self.chat.textCursor().selectedText().strip()) and self.discord_worker is None))
        p.layout.addWidget(self.chat,1)
        row=QHBoxLayout();row.addWidget(self.ai_input,1);row.addWidget(self.ai_send);p.layout.addLayout(row)
        row=QHBoxLayout();row.addWidget(self.ai_apply);row.addWidget(self.ai_save);row.addWidget(self.ai_clear);p.layout.addLayout(row)
        p.layout.addWidget(self.ai_save_selection)
        self.ai_open_task=QPushButton('Zuletzt übernommene Aufgabe öffnen');self.ai_open_task.setEnabled(False);self.ai_open_task.clicked.connect(self.open_last_ai_task);p.layout.addWidget(self.ai_open_task)
        self.ai_status=QLabel('API-Schlüssel unter Einstellungen einrichten. Eine Kanalaktion pro Auftrag.');self.ai_status.setWordWrap(True);p.layout.addWidget(self.ai_status)
        return p

    def save_ai_task(self):
        text=self.ai_input.text().strip()
        if text and self.save_task(text):
            self.append_chat('System: Aufgabe lokal gespeichert: '+text+'\n\n');self.ai_input.clear()

    def append_chat(self,text):
        cursor=QTextCursor(self.chat.document());cursor.movePosition(QTextCursor.End)
        start=cursor.position();cursor.insertText(text)
        self.chat.setTextCursor(cursor)
        return start,cursor.position()

    def save_ai_selection(self):
        if self.discord_worker is not None:return
        text=self.chat.textCursor().selectedText().replace('\u2029','\n').strip()
        if not text:return
        if len(text)>4000:self.ai_status.setText('Bitte einen Vorschlag mit höchstens 4000 Zeichen markieren.');return
        dialog=TaskReview(self,text)
        cursor=self.chat.textCursor()
        for record in self.ai_source_records:
            if record['start']<=cursor.selectionStart() and cursor.selectionEnd()<=record['end']:
                provenance='\n\nHerkunft: KI-Vorschlag · Server '+str(record['guild'])+' · Anfrage '+record['time']+'\n'+reference_report(text,record['sources'])
                dialog.set_evidence(provenance.strip())
                dialog.notes.setPlainText(text+provenance)
                break
        while dialog.exec():
            if self.discord_worker is not None:
                self.ai_status.setText('Ein Vorgang wurde inzwischen gestartet. Aufgabe anschließend erneut vorbereiten.');return
            title=dialog.title.text().strip();notes=dialog.notes.toPlainText().strip();status=dialog.status.currentText()
            if any(t['text']==title and t.get('notes','')==notes and t['status']!='Erledigt' for t in self.store.items):
                self.ai_status.setText('Diese offene Aufgabe ist bereits gespeichert. Unter Aufgaben findest du sie wieder.');return
            created=[]
            if self.mutate(lambda:created.append(self.store.add(title,notes,status))):
                self.last_ai_task_id=created[0]['id'];self.ai_open_task.setEnabled(True)
                self.ai_status.setText('Vorbereitete Aufgabe lokal gespeichert. Noch nicht ausgeführt.');return
            dialog.feedback.setText('Speichern fehlgeschlagen. Dein Entwurf ist erhalten; erneut speichern oder abbrechen.')

    def open_last_ai_task(self):
        if self.discord_worker is not None:return
        if not any(t['id']==self.last_ai_task_id for t in self.store.items):
            self.ai_open_task.setEnabled(False);self.ai_status.setText('Diese Aufgabe ist nicht mehr vorhanden.');return
        self.filter.setCurrentText('Alle');self.refresh_tasks()
        for i in range(self.task_list.count()):
            if self.task_list.item(i).data(Qt.UserRole)==self.last_ai_task_id:
                self.task_list.setCurrentRow(i);break
        self.stack.setCurrentIndex(3)

    def clear_ai_chat(self):
        if self.discord_worker is not None:return
        self.chat.clear();self.ai_source_records=[];self.ai_history=[];self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.ai_status.setText('Gespräch geleert. Keine Discord-Aktion ausgeführt.')

    def ask_ai(self,analysis_only=False):
        if self.discord_worker is not None:return
        prompt=self.ai_input.text().strip()
        if not prompt:return
        provider=self.active_ai_provider
        key=self.api_key_input.text().strip() or self.ai_keys[provider]
        if not key:
            self.ai_status.setText('Bitte zuerst unter Einstellungen den API-Schlüssel des gewählten Anbieters eingeben.');return
        if self.discord_client and key==self.discord_client.token:
            self.ai_status.setText('Das ist dein Discord-Token. Bitte stattdessen den API-Schlüssel des gewählten Anbieters eingeben.');return
        self.ai_keys[provider]=key;self.api_key_input.clear()
        model=self.ai_model.text().strip()
        context=json.loads(json.dumps(self.server_context)) if self.server_context else None
        if context and hasattr(self,'community'):
            context['community']=self.community.store.analysis_context(context['id'])
        history=list(self.ai_history)
        self.pending_ai=None;self.ai_apply.setEnabled(False)
        self.append_chat('Du: '+prompt+'\n');self.ai_input.clear()
        sources=source_index(context);requested_at=datetime.now().astimezone().isoformat(timespec='seconds')
        self.ai_status.setText('KI erstellt eine Antwort …')
        def answered(result):
            self.append_chat('Assistent: ')
            start,end=self.append_chat(result['message'])
            self.ai_source_records.append({'start':start,'end':end,'guild':context['id'] if context else 'nicht verbunden','time':requested_at,'sources':sources})
            self.append_chat('\n\n')
            if analysis_only or '[ACT-' in result['message']:
                self.append_chat('Quellenprüfung: '+reference_report(result['message'],sources)+'\n\n')
            self.ai_history.extend([{'role':'user','content':prompt},{'role':'assistant','content':result['message']}]);self.ai_history=self.ai_history[-8:]
            self.pending_ai=result if result['spec'] else None
            self.ai_apply.setEnabled(self.pending_ai is not None)
            self.ai_status.setText('Kanalaktion vorbereitet. Noch nicht ausgeführt.' if result['spec'] else 'Antwort erhalten. Keine Kanalaktion vorbereitet.')
        def failed(message):
            self.append_chat('System: '+message+'\n\n');self.ai_status.setText('KI-Anfrage fehlgeschlagen. Keine Discord-Aktion ausgeführt.')
        self.run_discord_job(lambda:request_plan(key,model,prompt,context,history,provider=provider,analysis_only=analysis_only),answered,failed)

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
        self.busy_indicator.setVisible(busy)
        self.statusBar().showMessage('Vorgang läuft …' if busy else 'Bereit')
        if hasattr(self,'community'):
            self.community.refresh_connection_controls()
            if busy:self.community.scan.setEnabled(False);self.community.poll_publish.setEnabled(False);self.community.poll_results.setEnabled(False);self.community.poll_schedule.setEnabled(False);self.community.poll_unschedule.setEnabled(False);self.community.creator_role_apply.setEnabled(False);self.community.creator_link_save.setEnabled(False)
            if busy:
                for widget in (self.community.creator_save,self.community.creator_remove,self.community.creators,self.community.creator_new,self.community.creator_search,self.community.creator_filter,self.community.creator_member_id,self.community.creator_role_id):widget.setEnabled(False)
        for widget in (self.remember_login,self.forget_login_button,self.connect_button,self.disconnect_button,self.bot_token,self.guild_id,self.channel_actions,self.ai_send,self.ai_input,self.ai_save,self.ai_save_selection,self.ai_clear,self.ai_apply,self.api_key_input,self.ai_model,self.ai_provider,self.forget_key_button):
            widget.setEnabled(not busy)
        if hasattr(self,'updates'):
            self.updates.setEnabled(not busy)
        if not busy:self.ai_apply.setEnabled(self.pending_ai is not None)
        if not busy:self.ai_save_selection.setEnabled(bool(self.chat.textCursor().selectedText().strip()))

    def run_discord_job(self, action, success, failure):
        if self.discord_worker is not None: return
        worker=DiscordWorker(action); self.discord_worker=worker
        self.set_discord_busy(True)
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
        if hasattr(self,'community'):self.community.bind(None)
        self.refresh_dashboard()
        self.channel_actions.result.setText('Bitte zuerst die Serverübersicht laden.')

    def show_discord(self, data):
        self.server_context=data
        if hasattr(self,'community'):self.community.bind(data)
        self.refresh_dashboard(data)
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
            self.summary.setText('  ·  '.join(f'{n} {status}' for status,n in counts.items()))
            self.dashboard_page.refresh_tasks(self.store.items)

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
        p.layout.addWidget(QLabel('KI-Anbieter'))
        self.ai_provider=QComboBox();self.ai_provider.addItem('Claude / Anthropic','anthropic');self.ai_provider.addItem('OpenAI','openai');p.layout.addWidget(self.ai_provider)
        self.ai_key_label=QLabel();p.layout.addWidget(self.ai_key_label)
        self.ai_key_link=QLabel();self.ai_key_link.setOpenExternalLinks(True);p.layout.addWidget(self.ai_key_link)
        self.api_key_input=QLineEdit(os.getenv('ANTHROPIC_API_KEY',''));self.api_key_input.setEchoMode(QLineEdit.Password);self.api_key_input.setPlaceholderText('API-Schlüssel hier eingeben');p.layout.addWidget(self.api_key_input)
        p.layout.addWidget(QLabel('Modell-ID (bei Bedarf an deinen API-Zugang anpassen)'))
        self.ai_model=QLineEdit(self.ai_models['anthropic']);p.layout.addWidget(self.ai_model)
        self.forget_key_button=QPushButton('API-Schlüssel dieses Anbieters aus der Sitzung entfernen');self.forget_key_button.clicked.connect(self.forget_ai_key);p.layout.addWidget(self.forget_key_button)
        p.layout.addWidget(self.card('API-Nutzung','Die API wird separat berechnet; ein Chat-Abonnement ersetzt keinen API-Zugang. Beim Senden gehen Auftrag, Gesprächsverlauf, Kanalnamen und IDs sowie zusammengefasste Community-Daten an den gewählten Anbieter. Discord-Token und einzelne Discord-Nachrichten werden nicht übertragen.'))
        self.refresh_ai_provider_labels()
        self.ai_provider.currentIndexChanged.connect(self.change_ai_provider)
        p.layout.addWidget(self.card('Gespräch & Aufgaben','Das KI-Gespräch bleibt in dieser App-Sitzung. Nur ausdrücklich gespeicherte Aufgaben liegen dauerhaft in deiner Aufgabendatei.'))
        p.layout.addWidget(self.card('Aufgabendatei',str(TASK_FILE)));p.layout.addStretch();return p

    def community_page(self):
        self.community=CommunityPage(self)
        return self.community

    def update_page(self):
        self.updates=UpdatePage(self)
        return self.updates

    def forget_ai_key(self):
        self.ai_keys[self.active_ai_provider]='';self.api_key_input.clear()
        self.ai_status.setText('API-Schlüssel dieses Anbieters aus der Sitzung entfernt.')

    def refresh_ai_provider_labels(self):
        claude=self.active_ai_provider=='anthropic'
        name='Claude / Anthropic' if claude else 'OpenAI'
        url='https://platform.claude.com/settings/keys' if claude else 'https://platform.openai.com/api-keys'
        self.ai_key_label.setText(name+'-API-Schlüssel (nur für die aktuelle Sitzung)')
        self.ai_key_link.setText(f'<a href="{url}">API-Schlüssel bei {name} erstellen</a>')
        self.ai_send.setText('An Claude senden' if claude else 'An OpenAI senden')

    def change_ai_provider(self):
        old=self.active_ai_provider
        self.ai_keys[old]=self.api_key_input.text().strip() or self.ai_keys[old]
        self.ai_models[old]=self.ai_model.text().strip()
        self.active_ai_provider=self.ai_provider.currentData()
        self.api_key_input.clear()
        self.ai_model.setText(self.ai_models[self.active_ai_provider])
        self.clear_ai_chat()
        self.refresh_ai_provider_labels()
        self.ai_status.setText('Anbieter gewechselt. Neues Gespräch; vorhandene Pläne wurden verworfen.')

    def save_task(self,text):
        return self.mutate(lambda:self.store.add(text))

    def apply_style(self):
        self.setStyleSheet(' '.join([
            '* { font-family:"Segoe UI"; font-size:13px; color:#e6eaf3; }',
            'QMainWindow,QWidget { background:#0d111b; }',
            'QLabel { background:transparent; }',
            '#sidebar { background:#121725; border-right:1px solid #252d40; }',
            '#brand { font-size:16px; font-weight:700; color:#e8eafa; }',
            '#navSection { color:#79839b; font-size:10px; font-weight:700; padding:5px 12px; }',
            '#title { font-size:30px; font-weight:700; color:#f3f5fb; }',
            '#subtitle,#muted { color:#a3adc2; }',
            '#footnote { color:#8691a9; font-size:12px; }',
            '#sectionTitle { font-size:16px; font-weight:600; color:#cbd3e6; }',
            '#nav { text-align:left; padding:11px 14px; border:1px solid transparent; border-radius:7px; background:transparent; color:#aeb8ce; }',
            '#nav:hover { background:#1b2335; color:#f3f5fb; }',
            '#nav:checked { background:#282443; color:#d6ccff; border:1px solid #494064; }',
            '#metric { font-size:32px; font-weight:700; color:#f2f4fc; }',
            '#card { background:#151c2b; border:1px solid #2b354b; border-radius:10px; }',
            '#card QLabel { background:transparent; }',
            '#cardTitle { font-size:14px; font-weight:600; color:#ccd5e8; }',
            '#statusPill { border:1px solid #38435b; border-radius:13px; padding:6px 12px; color:#aeb8ce; background:#192133; font-size:12px; }',
            '#statusPill[connected="true"] { border-color:#275f54; color:#8fe0c3; background:#173b34; }',
            'QPushButton { background:#202a3d; border:1px solid #3b4963; border-radius:7px; padding:9px 12px; color:#e1e7f5; }',
            'QPushButton:hover { background:#2b3850; border-color:#63738f; }',
            'QPushButton:pressed { background:#354363; }',
            'QPushButton:focus { border:1px solid #b39aff; }',
            'QPushButton:disabled { background:#182031; border-color:#29344a; color:#8390a8; }',
            '#primary { background:#8b70eb; color:#ffffff; border:1px solid #a18aef; font-weight:600; }',
            '#danger { background:#572832; border-color:#a14a5c; color:#ffe8ed; }',
            '#danger:hover { background:#763443; }',
            '#danger:disabled { background:#32232a; color:#a78a94; border-color:#4d343e; }',
            '#primary:hover { background:#9b82f1; }',
            '#primary:disabled { background:#3b3553; color:#a49bbd; border-color:#4b4465; }',
            'QLineEdit,QTextEdit,QListWidget,QComboBox { background:#111827; border:1px solid #35415b; border-radius:7px; padding:9px; selection-background-color:#514475; }',
            'QLineEdit:focus,QTextEdit:focus,QComboBox:focus,QListWidget:focus { border-color:#a18aef; }',
            'QLineEdit:disabled,QComboBox:disabled { color:#8390a8; border-color:#29344a; }',
            'QListWidget::item { padding:6px 8px; border-radius:4px; }',
            'QListWidget::item:selected { background:#3b335b; color:#eee8ff; }',
            'QTabWidget::pane { border:1px solid #35415b; border-radius:7px; }',
            'QTabBar::tab { background:#192235; padding:10px 13px; color:#adb9d0; border-bottom:2px solid transparent; }',
            'QTabBar::tab:selected { background:#282443; color:#e0d7ff; border-bottom:2px solid #a78bfa; }',
            'QTabBar::tab:hover { background:#25314a; }',
            'QCheckBox { spacing:8px; }',
            'QCheckBox::indicator { width:16px; height:16px; border:1px solid #7483a2; border-radius:4px; background:#111827; }',
            'QCheckBox::indicator:checked { background:#9b82f1; border:3px solid #c4b5fd; }',
            'QCheckBox:disabled { color:#8390a8; }',
            'QTableWidget { background:#111827; alternate-background-color:#192235; gridline-color:#29344a; border:1px solid #35415b; }',
            'QTableWidget::item:selected { background:#3b335b; color:#eee8ff; }',
            'QHeaderView::section { background:#1c273b; color:#bdc9df; padding:8px; border:0; border-right:1px solid #35415b; }',
            'QScrollArea { border:0; }',
            'QScrollBar:vertical { background:#121725; width:10px; margin:0; }',
            'QScrollBar::handle:vertical { background:#414e69; border-radius:4px; min-height:24px; margin:2px; }',
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }',
            'QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }',
            'QStatusBar { background:#121725; color:#a3adc2; border-top:1px solid #252d40; }',
            'QStatusBar::item { border:0; }',
            'QProgressBar { border:0; background:#202a3d; max-height:6px; }',
            'QProgressBar::chunk { background:#a78bfa; }'
        ]))

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

