from datetime import datetime,timedelta
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTabWidget,QComboBox,QPushButton,QLineEdit,QTextEdit,QListWidget,QMessageBox,QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QHBoxLayout
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
        self.channel.currentIndexChanged.connect(self.channel_changed)
        self.scan=QPushButton('Aktivität dieses Kanals erfassen');self.scan.clicked.connect(self.sample);a.addWidget(self.scan)
        self.auto_sample=QCheckBox('Diesen Kanal alle 15 Minuten erfassen, solange verbunden')
        a.addWidget(self.auto_sample)
        self.activity_timer=QTimer(self);self.activity_timer.setInterval(15*60*1000);self.activity_timer.timeout.connect(lambda:self.sample() if self.auto_sample.isChecked() else None);self.activity_timer.start()
        self.activity_metrics=QLabel('Noch keine Daten für diesen Kanal.');self.activity_metrics.setWordWrap(True);a.addWidget(self.activity_metrics)
        self.activity=QTextEdit();self.activity.setReadOnly(True);self.activity.setMaximumHeight(130);a.addWidget(self.activity)
        title=QLabel('Verlauf · maximal 96 Messpunkte pro Kanal');a.addWidget(title)
        self.history_table=QTableWidget(0,5);self.history_table.setHorizontalHeaderLabels(['Erfasst','Nachrichten¹','Personen¹','Stichprobe','Grenze'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.history_table.setEditTriggers(QTableWidget.NoEditTriggers);self.history_table.setAlternatingRowColors(True);a.addWidget(self.history_table)
        note=QLabel('¹ Letzte 24 Stunden innerhalb der letzten maximal 100 Nachrichten. Messpunkte können sich überschneiden und dürfen nicht addiert werden. Bei 100 gelesenen Nachrichten ist die Erfassung möglicherweise unvollständig.');note.setWordWrap(True);a.addWidget(note)
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
        old_guild=self.guild_id;selected=self.channel.currentData();auto=self.auto_sample.isChecked()
        self.guild_id=data['id'] if data else None;self.tabs.setEnabled(bool(data))
        channels=[(c['name'],c['id']) for c in data.get('channels',[]) if c['type'] in (0,5)] if data else []
        if channels!=self.channels or old_guild!=self.guild_id:
            self.channel.blockSignals(True);self.channel.clear()
            for name,item in channels:self.channel.addItem(name,item)
            index=self.channel.findData(selected)
            if old_guild==self.guild_id and index>=0:self.channel.setCurrentIndex(index)
            self.channel.blockSignals(False);self.channels=channels
            self.auto_sample.setChecked(auto and old_guild==self.guild_id and index>=0)
        if data:
            self.status.setText('Community für '+data['name']);self.refresh();QTimer.singleShot(0,self.reminders)
        else:
            self.auto_sample.setChecked(False)
            self.status.setText('Discord verbinden, um Community-Daten zu öffnen.');self.activity.clear();self.nights.clear();self.creators.clear();self.history_table.setRowCount(0);self._history_signature=None;self.activity_metrics.setText('Discord nicht verbunden.')
            self._night_signature=None;self._creator_signature=None
        self.dashboard()
    def sync_list(self,widget,rows,signature_name,display):
        signature=repr(rows)
        if getattr(self,signature_name,None)==signature:return
        selected=widget.currentItem().data(Qt.UserRole) if widget.currentItem() else None
        widget.clear()
        for row in rows:
            widget.addItem(display(row));item=widget.item(widget.count()-1);item.setData(Qt.UserRole,row['id'])
            if row['id']==selected:widget.setCurrentItem(item)
        setattr(self,signature_name,signature)

    def guard(self,action):
        if not self.guild_id:return
        try:action();self.refresh();return True
        except (CommunityError,OSError,ValueError) as exc:
            self.status.setText('Speichern fehlgeschlagen: '+str(exc));QMessageBox.warning(self,'Community',str(exc));return False
    def refresh(self):
        if not self.guild_id:return
        g=self.store.guild(self.guild_id)
        self.refresh_activity()
        self.sync_list(self.nights,g['nights'],'_night_signature',lambda n:f"{n['title']} · {parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')} · {n['status']}")
        self.sync_list(self.creators,g['creators'],'_creator_signature',lambda c:f"{c['name']} · {c['status']}")
        self.dashboard()
    def channel_changed(self):
        if hasattr(self,'auto_sample'):self.auto_sample.setChecked(False)
        if hasattr(self,'history_table'):self.refresh_activity()
    def refresh_activity(self):
        channel=self.channel.currentData()
        g=self.store.guild(self.guild_id) if self.guild_id else {}
        sample=g.get('activity',{}).get(channel)
        def local(value):return parse_time(value).astimezone().strftime('%d.%m. %H:%M') if value else 'unbekannt'
        if sample:
            self.activity_metrics.setText(f"Letzte 24h in der Stichprobe: {sample.get('messages_24h','—')} Nachrichten · {sample.get('participants_24h','—')} Personen")
            text=f"#{self.channel.currentText()} · zuletzt geprüft {local(sample['checked_at'])}\n{sample['messages']} menschliche Nachrichten in {sample['sample_size']} gelesenen Nachrichten\nErfasster Zeitraum: {local(sample['oldest'])} – {local(sample['latest'])}"
            if sample.get('limit_reached'):text+='\n100-Nachrichten-Grenze erreicht: weitere Nachrichten können fehlen.'
        else:
            self.activity_metrics.setText('Noch keine Daten für diesen Kanal.');text='Wähle einen Kanal und klicke auf Erfassen. Bestehende Stichproben aus älteren Versionen bleiben erhalten; 24h-Werte kommen mit der nächsten Erfassung.'
        if self.activity.toPlainText()!=text:self.activity.setPlainText(text)
        rows=list(reversed(self.store.history(self.guild_id,channel))) if self.guild_id and channel else []
        signature=(self.guild_id,channel,repr(rows))
        if getattr(self,'_history_signature',None)==signature:return
        self.history_table.setUpdatesEnabled(False)
        try:
            self.history_table.setRowCount(len(rows))
            for i,row in enumerate(rows):
                for j,value in enumerate([local(row['checked_at']),row.get('messages_24h','—'),row.get('participants_24h','—'),row['sample_size'],'100 erreicht' if row.get('limit_reached') else 'unter 100']):self.history_table.setItem(i,j,QTableWidgetItem(str(value)))
            self._history_signature=signature
        finally:self.history_table.setUpdatesEnabled(True)

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
            if self.guard(lambda:self.store.record_activity(guild,result)):self.status.setText('Aktivitätsstichprobe und Verlauf gespeichert.')
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
