from datetime import datetime,timedelta
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTabWidget,QComboBox,QPushButton,QLineEdit,QTextEdit,QListWidget,QMessageBox,QCheckBox
from community import CommunityStore,CommunityError,activity_sample,parse_time

class CommunityPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.guild_id=None;self.channels=[]
        self.store=CommunityStore();layout=QVBoxLayout(self);layout.setContentsMargins(32,28,32,28)
        title=QLabel('Community');title.setObjectName('title');layout.addWidget(title)
        self.status=QLabel('Discord verbinden, um die Community dieses Servers zu öffnen.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);layout.addWidget(self.status)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        def page(name):
            w=QWidget();l=QVBoxLayout(w);self.tabs.addTab(w,name);return l
        a=page('Activity System')
        info=QLabel('Liest die letzten bis zu 100 Nachrichten eines gewählten Textkanals. Bots werden ausgeschlossen. Gespeichert werden nur Summen und Zeitpunkte, keine Nachrichtentexte oder Mitglieder-IDs. Dies ist keine vollständige Serverstatistik.');info.setWordWrap(True);a.addWidget(info)
        self.channel=QComboBox();a.addWidget(self.channel)
        self.channel.currentIndexChanged.connect(lambda:self.auto_sample.setChecked(False) if hasattr(self,'auto_sample') else None)
        self.scan=QPushButton('Aktivität dieses Kanals erfassen');self.scan.clicked.connect(self.sample);a.addWidget(self.scan)
        self.auto_sample=QCheckBox('Diesen Kanal alle 15 Minuten erfassen, solange verbunden')
        a.addWidget(self.auto_sample)
        self.activity_timer=QTimer(self);self.activity_timer.setInterval(15*60*1000);self.activity_timer.timeout.connect(lambda:self.sample() if self.auto_sample.isChecked() else None);self.activity_timer.start()
        self.activity=QTextEdit();self.activity.setReadOnly(True);a.addWidget(self.activity)
        n=page('Lobby Night')
        info=QLabel('Lokaler Planer: erstellt einen Abstimmungstext und erinnert beim Termin, solange die App läuft. Verpasste Termine werden beim nächsten Verbinden angezeigt. Noch keine automatische Discord-Nachricht oder Abstimmung.');info.setWordWrap(True);n.addWidget(info)
        self.night_title=QLineEdit('Lobby Night');n.addWidget(self.night_title)
        self.night_time=QLineEdit((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d 20:00'));self.night_time.setPlaceholderText('Lokale PC-Zeit: JJJJ-MM-TT HH:MM');n.addWidget(self.night_time)
        self.options=QTextEdit();self.options.setPlaceholderText('Ein Spielvorschlag pro Zeile (2–10)');self.options.setMaximumHeight(100);n.addWidget(self.options)
        b=QPushButton('Termin und Vorschläge speichern');b.clicked.connect(self.add_night);n.addWidget(b)
        self.nights=QListWidget();n.addWidget(self.nights)
        b=QPushButton('Abstimmungstext kopieren');b.clicked.connect(self.copy_poll);n.addWidget(b)
        b=QPushButton('Ausgewählten Termin absagen');b.clicked.connect(self.cancel_night);n.addWidget(b)
        c=page('Creator Hub')
        info=QLabel('Lokale Bewerbungsübersicht für Twitch-/YouTube-Creator. Änderungen vergeben noch keine Discord-Rollen und aktivieren keine Stream-Benachrichtigungen.');info.setWordWrap(True);c.addWidget(info)
        self.creator_name=QLineEdit();self.creator_name.setPlaceholderText('Creator-Name');c.addWidget(self.creator_name)
        self.creator_url=QLineEdit();self.creator_url.setPlaceholderText('https://www.twitch.tv/kanal');c.addWidget(self.creator_url)
        self.creator_status=QComboBox();self.creator_status.addItems(['Bewerbung','Angenommen','Pausiert']);c.addWidget(self.creator_status)
        b=QPushButton('Creator speichern / nach Kanallink aktualisieren');b.clicked.connect(self.add_creator);c.addWidget(b)
        self.creators=QListWidget();self.creators.itemClicked.connect(self.select_creator);c.addWidget(self.creators)
        b=QPushButton('Ausgewählten Creator entfernen');b.clicked.connect(self.remove_creator);c.addWidget(b)
        x=page('Serveranalyse')
        info=QLabel('Die KI erhält Serverstruktur und die aggregierten Community-Daten. Nachrichtentexte und Creator-Kanallinks werden nicht mitgegeben. OpenAI-API-Schlüssel unter Einstellungen erforderlich.');info.setWordWrap(True);x.addWidget(info)
        b=QPushButton('KI-Analyse im Assistenten starten');b.clicked.connect(self.analyze);x.addWidget(b);x.addStretch()
        self.tabs.setEnabled(False)
        self.timer=QTimer(self);self.timer.setInterval(60000);self.timer.timeout.connect(self.reminders);self.timer.start()
    def bind(self,data):
        self.guild_id=data['id'] if data else None;self.tabs.setEnabled(bool(data));self.channel.clear()
        if data:
            for c in data['channels']:
                if c['type'] in (0,5):self.channel.addItem(c['name'],c['id'])
            self.status.setText('Community für '+data['name']);self.refresh();QTimer.singleShot(0,self.reminders)
        else:
            self.status.setText('Discord verbinden, um Community-Daten zu öffnen.');self.activity.clear();self.nights.clear();self.creators.clear()
        self.dashboard()
    def guard(self,action):
        if not self.guild_id:return
        try:action();self.refresh()
        except (CommunityError,OSError,ValueError) as exc:QMessageBox.warning(self,'Community',str(exc))
    def refresh(self):
        if not self.guild_id:return
        g=self.store.guild(self.guild_id)
        self.activity.setPlainText('\n\n'.join(f"Kanal {s['channel_id']}\n{s['messages']} Nachrichten von {s['participants']} Personen in einer Stichprobe von {s['sample_size']} Nachrichten\nErfasst: {s['checked_at']}\nZeitraum: {s['oldest'] or 'unbekannt'} bis {s['latest'] or 'unbekannt'}" for s in g['activity'].values()) or 'Noch keine Aktivitätsstichprobe erfasst.')
        self.nights.clear()
        for n in g['nights']:
            self.nights.addItem(f"{n['title']} · {parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')} · {n['status']}");self.nights.item(self.nights.count()-1).setData(Qt.UserRole,n['id'])
        self.creators.clear()
        for c in g['creators']:
            self.creators.addItem(f"{c['name']} · {c['status']}");self.creators.item(self.creators.count()-1).setData(Qt.UserRole,c['id'])
        self.dashboard()
    def dashboard(self):
        if not hasattr(self.host,'community_summary'):return
        if not self.guild_id:self.host.community_summary.setText('Community: Discord noch nicht verbunden.');return
        g=self.store.guild(self.guild_id)
        self.host.community_summary.setText(f"Community: {len(g['activity'])} Kanalstichproben · {sum(n['status']=='geplant' for n in g['nights'])} geplante Lobby Nights · {len(g['creators'])} Creator\nStichproben und Planung sind lokal; keine vollständige Serveraktivitätsmessung.")
    def sample(self):
        client=self.host.discord_client;channel=self.channel.currentData();guild=self.guild_id
        if not client or not channel or self.host.discord_worker is not None:return
        self.status.setText('Aktivität wird gelesen …')
        def done(result):
            self.guard(lambda:self.store.record_activity(guild,result));self.status.setText('Aktivitätsstichprobe gespeichert.')
        self.host.run_discord_job(lambda:activity_sample(client.recent_messages(channel,100),channel),done,self.status.setText)
    def add_night(self):self.guard(lambda:self.store.add_night(self.guild_id,self.night_title.text(),self.night_time.text(),self.options.toPlainText()))
    def chosen_night(self):
        item=self.nights.currentItem()
        return next((n for n in self.store.guild(self.guild_id)['nights'] if item and n['id']==item.data(Qt.UserRole)),None) if self.guild_id else None
    def copy_poll(self):
        n=self.chosen_night()
        if n:
            from PySide6.QtWidgets import QApplication
            text=n['title']+' · '+parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')+'\nWas wollt ihr spielen?\n'+'\n'.join(f'{i+1}. {v}' for i,v in enumerate(n['options']))+'\nEigene Vorschläge sind willkommen!'
            QApplication.clipboard().setText(text);self.status.setText('Abstimmungstext kopiert. Noch nicht in Discord veröffentlicht.')
    def cancel_night(self):
        n=self.chosen_night()
        if n:self.guard(lambda:self.store.cancel_night(self.guild_id,n['id']))
    def reminders(self):
        if not self.guild_id:return
        try:
            due=self.store.due_nights(self.guild_id)
            for n in due:
                self.store.mark_reminded(self.guild_id,n['id'])
                QMessageBox.information(self,'Lobby Night Erinnerung',n['title']+' ist fällig: '+parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M'))
        except (CommunityError,OSError,ValueError) as exc:self.status.setText(str(exc))
    def add_creator(self):self.guard(lambda:self.store.save_creator(self.guild_id,self.creator_name.text(),self.creator_url.text().strip(),self.creator_status.currentText()))
    def select_creator(self,item):
        c=next(x for x in self.store.guild(self.guild_id)['creators'] if x['id']==item.data(Qt.UserRole))
        self.creator_name.setText(c['name']);self.creator_url.setText(c['url']);self.creator_status.setCurrentText(c['status'])
    def remove_creator(self):
        item=self.creators.currentItem()
        if item:self.guard(lambda:self.store.remove_creator(self.guild_id,item.data(Qt.UserRole)))
    def analyze(self):
        self.host.stack.setCurrentIndex(1)
        self.host.ai_input.setText('Analysiere die Serverstruktur und die verfügbaren Community-Daten. Benenne Datenlücken, drei belegte Erkenntnisse und drei priorisierte Mitmachideen für Activity System, Lobby Night und Creator Hub. Keine Kanalaktion planen; nur antworten. Keine vollständige Aktivitätsmessung behaupten.')
        self.host.ask_ai()
