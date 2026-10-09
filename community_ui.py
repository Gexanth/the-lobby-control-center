from datetime import datetime,timedelta,timezone
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTabWidget,QComboBox,QPushButton,QLineEdit,QTextEdit,QListWidget,QMessageBox,QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QHBoxLayout,QFrame
from polls import poll_spec,PollJournal,send_poll,read_poll_results,schedule_state
from copy import deepcopy
from stream_ui import StreamPanel
from creator_roles import binding,save_binding,delivery,checked_plan,assign_checked,creator_next_step
from engagement import engagement_ideas,activity_quality
from updates import DATA,read_json,UpdateError
from lobby import snowflake
from community import CommunityStore,CommunityError,activity_sample,parse_time,night_fields

class CommunityPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.guild_id=None;self.channels=[]
        self.store=CommunityStore();layout=QVBoxLayout(self);layout.setContentsMargins(32,28,32,28)
        title=QLabel('Community');title.setObjectName('title');layout.addWidget(title)
        self.status=QLabel('Discord verbinden, um die Community dieses Servers zu öffnen.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.PlainText);layout.addWidget(self.status)
        connect=QPushButton('Discord verbinden / Verbindung prüfen');connect.clicked.connect(self.open_connection);layout.addWidget(connect)
        row=QHBoxLayout();row.addWidget(QLabel('Server-ID für lokale Daten'))
        self.offline_server=QComboBox();self.offline_server.setEditable(True)
        remembered=''
        try:remembered=str(read_json(DATA/'discord_login.json',{}).get('guild_id',''))
        except (UpdateError,AttributeError):pass
        ids=sorted(set(self.store.data['guilds'])|({remembered} if remembered else set()))
        self.offline_server.addItems(ids)
        if remembered:self.offline_server.setCurrentText(remembered)
        row.addWidget(self.offline_server,1)
        self.open_local=QPushButton('Lokale Daten öffnen');self.open_local.clicked.connect(self.open_offline);row.addWidget(self.open_local);layout.addLayout(row)
        self.tabs=QTabWidget();layout.addWidget(self.tabs)
        def page(name):
            w=QWidget();l=QVBoxLayout(w);self.tabs.addTab(w,name);return l
        a=page('Activity System')
        info=QLabel('Erfasst die letzten 24 Stunden eines Textkanals in bis zu fünf Abrufen (maximal 500 Nachrichten). Bots werden ausgeschlossen. Gespeichert werden nur Summen und Zeitpunkte, keine Nachrichtentexte oder Mitglieder-IDs. Dies ist keine vollständige Serverstatistik.');info.setWordWrap(True);a.addWidget(info)
        self.channel=QComboBox();a.addWidget(self.channel)
        self.channel.currentIndexChanged.connect(self.channel_changed)
        self.scan=QPushButton('Aktivität dieses Kanals erfassen');self.scan.clicked.connect(self.sample);a.addWidget(self.scan)
        self.auto_sample=QCheckBox('Diesen Kanal alle 15 Minuten erfassen, solange verbunden')
        a.addWidget(self.auto_sample)
        self.activity_access=QLabel('Benötigt im gewählten Kanal: „Kanal ansehen“ und „Nachrichtenverlauf anzeigen“. Nachrichten senden ist nicht erforderlich.')
        self.activity_access.setWordWrap(True);self.activity_access.setTextFormat(Qt.PlainText);a.addWidget(self.activity_access)
        self.activity_timer=QTimer(self);self.activity_timer.setInterval(15*60*1000);self.activity_timer.timeout.connect(lambda:self.sample() if self.auto_sample.isChecked() else None);self.activity_timer.start()
        self.activity_metrics=QLabel('Noch keine Daten für diesen Kanal.');self.activity_metrics.setWordWrap(True);a.addWidget(self.activity_metrics)
        self.activity_quality=QLabel();self.activity_quality.setWordWrap(True);self.activity_quality.setTextFormat(Qt.PlainText);a.addWidget(self.activity_quality)
        b=QPushButton('Passenden Mitmachimpuls ansehen');b.clicked.connect(lambda:self.tabs.setCurrentIndex(4));a.addWidget(b)
        self.activity=QTextEdit();self.activity.setReadOnly(True);self.activity.setMaximumHeight(130);a.addWidget(self.activity)
        title=QLabel('Verlauf · maximal 96 Messpunkte pro Kanal');a.addWidget(title)
        self.history_table=QTableWidget(0,5);self.history_table.setHorizontalHeaderLabels(['Erfasst','Nachrichten¹','Personen¹','Gelesen','Abdeckung'])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.history_table.setEditTriggers(QTableWidget.NoEditTriggers);self.history_table.setAlternatingRowColors(True);a.addWidget(self.history_table)
        note=QLabel('¹ Messpunkte überlappen und dürfen nicht addiert werden. Es zählen nur zugängliche, noch vorhandene Nachrichten. Alte Messpunkte nutzen weiterhin die frühere 100-Nachrichten-Stichprobe.');note.setWordWrap(True);a.addWidget(note)
        n=page('Lobby Night')
        info=QLabel('Lokaler Planer: erstellt einen Abstimmungstext und erinnert beim Termin, solange die App läuft. Verpasste Termine werden beim nächsten Verbinden angezeigt. Eine echte Discord-Abstimmung kann unten nach Vorschau veröffentlicht werden. Kein Discord-Event. Geplante Veröffentlichungen benötigen die laufende, verbundene App.');info.setWordWrap(True);n.addWidget(info)
        self.night_title=QLineEdit('Lobby Night');n.addWidget(self.night_title)
        self.night_time=QLineEdit((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d 20:00'));self.night_time.setPlaceholderText('Lokale PC-Zeit: JJJJ-MM-TT HH:MM');n.addWidget(self.night_time)
        self.options=QTextEdit();self.options.setPlaceholderText('Ein Spielvorschlag pro Zeile (2–10)');self.options.setMaximumHeight(100);n.addWidget(self.options)
        self.night_readiness=QLabel();self.night_readiness.setWordWrap(True);self.night_readiness.setTextFormat(Qt.PlainText);n.addWidget(self.night_readiness)
        row=QHBoxLayout();self.night_save=QPushButton('Termin und Vorschläge speichern');self.night_save.clicked.connect(self.save_night);row.addWidget(self.night_save)
        self.night_new=QPushButton('Neuen Entwurf beginnen');self.night_new.clicked.connect(self.new_night);row.addWidget(self.night_new);n.addLayout(row)
        self.night_edit_id=None;self.night_edit_guild=None
        self.nights=QListWidget();self.nights.itemSelectionChanged.connect(self.select_night);self.nights.setMaximumHeight(120);n.addWidget(self.nights)
        self.night_review=QLabel('Noch keinen gespeicherten Lobby-Night-Plan ausgewählt.');self.night_review.setWordWrap(True);self.night_review.setTextFormat(Qt.PlainText);n.addWidget(self.night_review)
        self.night_title.textChanged.connect(self.refresh_night_readiness);self.night_time.textChanged.connect(self.refresh_night_readiness);self.options.textChanged.connect(self.refresh_night_readiness)
        row=QHBoxLayout();self.night_reminder=QComboBox()
        for label,value in [('Zum Termin',0),('15 Minuten vorher',15),('30 Minuten vorher',30),('1 Stunde vorher',60),('1 Tag vorher',1440),('Ausgeschaltet',None)]:self.night_reminder.addItem(label,value)
        row.addWidget(self.night_reminder);self.night_reminder_save=QPushButton('Erinnerung für Auswahl speichern');self.night_reminder_save.clicked.connect(self.save_night_reminder);row.addWidget(self.night_reminder_save);n.addLayout(row)
        self.night_reminder_status=QLabel('Erinnerungen erscheinen nur lokal bei laufender App.');self.night_reminder_status.setWordWrap(True);n.addWidget(self.night_reminder_status)
        self.poll_readiness=QLabel();self.poll_readiness.setWordWrap(True);self.poll_readiness.setTextFormat(Qt.PlainText);n.addWidget(self.poll_readiness)
        n.addWidget(QLabel('Discord-Abstimmung: Zielkanal und Laufzeit'))
        poll_row=QHBoxLayout();self.poll_channel=QComboBox();poll_row.addWidget(self.poll_channel,2)
        self.poll_hours=QComboBox()
        for hours in (1,6,12,24,48,72,168):self.poll_hours.addItem(str(hours)+' Stunden',hours)
        self.poll_hours.setCurrentIndex(3);poll_row.addWidget(self.poll_hours,1);n.addLayout(poll_row)
        self.poll_multi=QCheckBox('Mehrere Spielvorschläge auswählbar');n.addWidget(self.poll_multi)
        self.poll_channel.currentIndexChanged.connect(self.refresh_poll_readiness);self.poll_hours.currentIndexChanged.connect(self.refresh_poll_readiness);self.poll_multi.toggled.connect(self.refresh_poll_readiness)
        self.poll_publish=QPushButton('Abstimmung prüfen und veröffentlichen');self.poll_publish.clicked.connect(lambda:self.review_poll(False));n.addWidget(self.poll_publish)
        self.poll_send_time=QLineEdit();self.poll_send_time.setPlaceholderText('Veröffentlichungszeit: JJJJ-MM-TT HH:MM (lokale PC-Zeit)');n.addWidget(self.poll_send_time)
        self.poll_schedule=QPushButton('Veröffentlichung nach Vorschau planen');self.poll_schedule.clicked.connect(lambda:self.review_poll(True));n.addWidget(self.poll_schedule)
        self.poll_unschedule=QPushButton('Geplante Veröffentlichung stoppen');self.poll_unschedule.clicked.connect(self.stop_scheduled_poll);n.addWidget(self.poll_unschedule)
        self.poll_status=QLabel('Noch keine Abstimmung veröffentlicht.');self.poll_status.setWordWrap(True);self.poll_status.setTextFormat(Qt.PlainText);n.addWidget(self.poll_status)
        self.poll_results=QPushButton('Ergebnisse der veröffentlichten Abstimmung laden');self.poll_results.clicked.connect(self.load_poll_results);n.addWidget(self.poll_results)
        self.poll_link=QPushButton('Abstimmungslink kopieren');self.poll_link.clicked.connect(self.copy_poll_link);n.addWidget(self.poll_link)
        self.poll_reset=QPushButton('Unklaren Versand nach manueller Discord-Prüfung freigeben');self.poll_reset.clicked.connect(self.reset_poll);n.addWidget(self.poll_reset)
        b=QPushButton('Abstimmungstext kopieren');b.clicked.connect(self.copy_poll);n.addWidget(b)
        b=QPushButton('Ausgewählten Termin absagen');b.clicked.connect(self.cancel_night);n.addWidget(b)
        c=page('Creator Hub')
        info=QLabel('Lokale Bewerbungsübersicht für Twitch-/YouTube-Creator. Änderungen vergeben noch keine Discord-Rollen und aktivieren keine Stream-Benachrichtigungen.');info.setWordWrap(True);c.addWidget(info)
        self.creator_edit_id=None;self.creator_edit_guild=None
        self.creator_summary=QLabel();self.creator_summary.setObjectName('subtitle');c.addWidget(self.creator_summary)
        row=QHBoxLayout();self.creator_search=QLineEdit();self.creator_search.setPlaceholderText('Creator oder Kanallink suchen …');row.addWidget(self.creator_search,2)
        self.creator_filter=QComboBox();self.creator_filter.addItems(['Alle Status','Bewerbung','Angenommen','Pausiert']);row.addWidget(self.creator_filter,1);c.addLayout(row)
        columns=QHBoxLayout();left=QVBoxLayout();self.creators=QListWidget();self.creators.setMinimumHeight(240);self.creators.setMaximumHeight(460);self.creators.currentItemChanged.connect(self.select_creator);left.addWidget(self.creators)
        self.creator_matches=QLabel();self.creator_matches.setObjectName('muted');left.addWidget(self.creator_matches);columns.addLayout(left,1)
        frame=QFrame();frame.setObjectName('card');form=QVBoxLayout(frame);form.setContentsMargins(18,18,18,18);form.setSpacing(10)
        self.creator_editor_title=QLabel('Neue Bewerbung');self.creator_editor_title.setObjectName('cardTitle');form.addWidget(self.creator_editor_title)
        form.addWidget(QLabel('Creator-Name'));self.creator_name=QLineEdit();self.creator_name.setPlaceholderText('Name des Creators');form.addWidget(self.creator_name)
        form.addWidget(QLabel('Twitch- oder YouTube-Kanallink'));self.creator_url=QLineEdit();self.creator_url.setPlaceholderText('https://www.twitch.tv/kanal');form.addWidget(self.creator_url)
        form.addWidget(QLabel('Bearbeitungsstand'));self.creator_status=QComboBox();self.creator_status.addItems(['Bewerbung','Angenommen','Pausiert']);form.addWidget(self.creator_status)
        form.addWidget(QLabel('Interne Bewerbungsnotizen (nur lokal, maximal 2000 Zeichen)'))
        self.creator_notes=QTextEdit();self.creator_notes.setMaximumHeight(95);self.creator_notes.setPlaceholderText('Offene Fragen, Gesprächsstand, nächste Schritte …');form.addWidget(self.creator_notes)
        self.creator_next=QLabel('Neue Bewerbung anlegen.');self.creator_next.setWordWrap(True);self.creator_next.setTextFormat(Qt.PlainText);form.addWidget(self.creator_next)
        self.creator_save=QPushButton('Bewerbung speichern');self.creator_save.setObjectName('primary');self.creator_save.clicked.connect(self.add_creator);form.addWidget(self.creator_save)
        self.creator_new=QPushButton('Neue Bewerbung beginnen');self.creator_new.clicked.connect(self.new_creator);form.addWidget(self.creator_new)
        self.creator_copy=QPushButton('Gespeicherten Kanallink kopieren');self.creator_copy.clicked.connect(self.copy_creator_link);form.addWidget(self.creator_copy)
        self.creator_remove=QPushButton('Ausgewählten Creator entfernen');self.creator_remove.clicked.connect(self.remove_creator);form.addWidget(self.creator_remove)
        note=QLabel('Statusänderungen bleiben lokal. Rollen können unten nach Prüfung zugewiesen werden. Stream-Quellen und die optionale Überwachung lassen sich unten einrichten.');note.setWordWrap(True);note.setObjectName('muted');form.addWidget(note);form.addStretch();columns.addWidget(frame,1);c.addLayout(columns)
        role_frame=QFrame();self.creator_role_frame=role_frame;role_frame.setObjectName('card');role_form=QVBoxLayout(role_frame);role_form.setContentsMargins(18,18,18,18)
        title=QLabel('Discord-Rolle verknüpfen');title.setObjectName('cardTitle');role_form.addWidget(title)
        hint=QLabel('Nur für gespeicherte, angenommene Creator. IDs in Discord mit aktiviertem Entwicklermodus kopieren. Eine Verknüpfung allein vergibt keine Rolle.');hint.setWordWrap(True);role_form.addWidget(hint)
        row=QHBoxLayout();member_column=QVBoxLayout();member_column.addWidget(QLabel('Discord-Mitglieds-ID'))
        self.creator_member_id=QLineEdit();self.creator_member_id.setPlaceholderText('17–20-stellige Mitglieds-ID');member_column.addWidget(self.creator_member_id);row.addLayout(member_column)
        role_column=QVBoxLayout();role_column.addWidget(QLabel('Discord-Rollen-ID'))
        self.creator_role_id=QLineEdit();self.creator_role_id.setPlaceholderText('17–20-stellige Rollen-ID');role_column.addWidget(self.creator_role_id);row.addLayout(role_column);role_form.addLayout(row)
        row=QHBoxLayout();self.creator_link_save=QPushButton('Verknüpfung lokal speichern');self.creator_link_save.clicked.connect(self.save_creator_link);row.addWidget(self.creator_link_save)
        self.creator_role_apply=QPushButton('Rolle prüfen und zuweisen');self.creator_role_apply.clicked.connect(self.review_creator_role);row.addWidget(self.creator_role_apply);role_form.addLayout(row)
        self.creator_role_status=QLabel('Keine Verknüpfung ausgewählt.');self.creator_role_status.setWordWrap(True);self.creator_role_status.setTextFormat(Qt.PlainText);role_form.addWidget(self.creator_role_status);c.addWidget(role_frame);self.stream_panel=StreamPanel(self);c.addWidget(self.stream_panel);c.addStretch()
        self.creator_search.textChanged.connect(self.refresh_creators);self.creator_filter.currentTextChanged.connect(self.refresh_creators)
        x=page('Serveranalyse')
        info=QLabel('Die KI erhält Serverstruktur und die aggregierten Community-Daten. Nachrichtentexte und Creator-Kanallinks werden nicht mitgegeben. API-Schlüssel für Claude oder OpenAI unter Einstellungen erforderlich.');info.setWordWrap(True);x.addWidget(info)
        b=QPushButton('KI-Analyse im Assistenten starten');b.clicked.connect(self.analyze);x.addWidget(b);x.addStretch()
        e=page('Mitmachimpulse')
        intro=QLabel('Konkrete Gesprächsideen aus der ausgewählten Aktivitätsmessung. Die Begründung zeigt, ob Daten verwendbar sind. Kein API-Schlüssel und keine zusätzlichen Abrufe erforderlich.');intro.setWordWrap(True);e.addWidget(intro)
        self.engagement_basis=QLabel();self.engagement_basis.setWordWrap(True);self.engagement_basis.setTextFormat(Qt.PlainText);e.addWidget(self.engagement_basis)
        self.engagement_select=QComboBox();self.engagement_select.currentIndexChanged.connect(self.select_engagement);e.addWidget(self.engagement_select)
        self.engagement_why=QLabel();self.engagement_why.setWordWrap(True);self.engagement_why.setTextFormat(Qt.PlainText);e.addWidget(self.engagement_why)
        self.engagement_draft=QTextEdit();self.engagement_draft.setPlaceholderText('Vorschlag vor dem Kopieren bearbeiten …');e.addWidget(self.engagement_draft)
        b=QPushButton('Bearbeiteten Gesprächsimpuls kopieren');b.clicked.connect(self.copy_engagement);e.addWidget(b)
        b=QPushButton('Lobby-Night-Planer öffnen');b.clicked.connect(lambda:self.tabs.setCurrentIndex(1));e.addWidget(b)
        hint=QLabel('Die Vorschläge werden nicht automatisch versendet. Kopiere bei Bedarf einen passenden Impuls in Discord. Keine Mitglieder pingen und keine Erfolgsgarantie.');hint.setWordWrap(True);e.addWidget(hint)
        self.engagement_hint=QLabel();self.engagement_hint.setWordWrap(True);e.addWidget(self.engagement_hint)
        self.tabs.currentChanged.connect(lambda index:self.refresh_engagement() if index==4 else None)
        self.tabs.setEnabled(True)
        self.timer=QTimer(self);self.timer.setInterval(60000);self.timer.timeout.connect(self.refresh_activity_feedback);self.timer.timeout.connect(self.reminders);self.timer.timeout.connect(self.refresh_poll_readiness);self.timer.timeout.connect(self.dispatch_scheduled_poll);self.timer.start()
        self.refresh_night_readiness()
        self.bind(None)
    def bind(self,data):
        old_guild=self.guild_id;selected=self.channel.currentData();auto=self.auto_sample.isChecked()
        if data:
            self.guild_id=data['id']
            if self.offline_server.findText(self.guild_id)<0:self.offline_server.addItem(self.guild_id)
            self.offline_server.setCurrentText(self.guild_id)
        else:
            try:self.guild_id=snowflake(self.offline_server.currentText().strip())
            except ValueError:self.guild_id=None
        if old_guild!=self.guild_id:
            self.new_creator();self.creator_search.blockSignals(True);self.creator_filter.blockSignals(True)
            self.creator_search.clear();self.creator_filter.setCurrentIndex(0)
            self.creator_search.blockSignals(False);self.creator_filter.blockSignals(False)
        self.tabs.setEnabled(True)
        self.offline_server.setEnabled(not bool(data));self.open_local.setEnabled(not bool(data))
        channels=[(c['name'],c['id']) for c in data.get('channels',[]) if c['type'] in (0,5)] if data else [(f'Gespeicherter Kanal · {cid}',cid) for cid in self.store.guild(self.guild_id)['activity']] if self.guild_id else []
        if channels!=self.channels or old_guild!=self.guild_id:
            self.channel.blockSignals(True);self.channel.clear()
            for name,item in channels:self.channel.addItem(name,item)
            index=self.channel.findData(selected)
            if old_guild==self.guild_id and index>=0:self.channel.setCurrentIndex(index)
            self.channel.blockSignals(False);self.channels=channels
            self.auto_sample.setChecked(auto and old_guild==self.guild_id and index>=0)
        self.poll_channel.clear()
        if data:
            for c in data['channels']:
                if c.get('type')==0:self.poll_channel.addItem(c['name'],c['id'])
        if data:
            self.status.setText('Community für '+data['name']);self.refresh();QTimer.singleShot(0,self.reminders)
        else:
            self.auto_sample.setChecked(False)
            self.status.setText('Offline · lokale Daten für Server '+self.guild_id if self.guild_id else 'Tabs sind verfügbar. Für lokale Planung eine Server-ID eingeben; für Aktivität Discord verbinden.')
            if self.guild_id:self.refresh()
            else:
                self.activity.clear();self.nights.clear();self.creators.clear();self.history_table.setRowCount(0);self._history_signature=None;self.activity_metrics.setText('Keine Server-ID gewählt.');self.refresh_engagement()
                self.activity_quality.setText('Noch keine Messung. Für neue Daten diesen Server verbinden.')
                self._night_signature=None;self._creator_signature=None
        self.refresh_creators();self.refresh_connection_controls();self.dashboard()
    def refresh_connection_controls(self):
        client=self.host.discord_client
        connected=bool(client and client.guild==self.guild_id)
        self.scan.setEnabled(connected and self.host.discord_worker is None and self.channel.currentData() is not None)
        self.auto_sample.setEnabled(connected and self.channel.currentData() is not None)
        n=self.chosen_night();state=n.get('poll_delivery',{}).get('state') if n else None
        planned=bool(n and n.get('status')=='geplant' and parse_time(n['when'])>datetime.now(timezone.utc))
        self.poll_publish.setEnabled(connected and self.host.discord_worker is None and self.poll_channel.currentData() is not None and planned and state not in ('sent','sending','uncertain','scheduled'))
        self.poll_schedule.setEnabled(self.poll_publish.isEnabled());self.poll_unschedule.setVisible(state=='scheduled')
        self.poll_unschedule.setEnabled(self.host.discord_worker is None)
        self.poll_results.setEnabled(connected and self.host.discord_worker is None and state=='sent')
        self.poll_link.setEnabled(state=='sent');self.poll_reset.setVisible(state in ('sending','uncertain'))
        self.refresh_creator_role_controls()
        self.refresh_poll_readiness()
        if hasattr(self,"night_reminder_save"):self.night_reminder_save.setEnabled(bool(n and n.get("status")=="geplant" and self.host.discord_worker is None))
    def open_connection(self):
        if self.guild_id:self.host.guild_id.setText(self.guild_id)
        self.host.stack.setCurrentIndex(2)
    def open_offline(self):
        if self.host.discord_client:return
        try:snowflake(self.offline_server.currentText().strip())
        except ValueError:self.status.setText('Bitte eine gültige 17–20-stellige Server-ID eingeben.');return
        self.bind(None)

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
        if not self.guild_id:self.status.setText('Für diese lokale Aktion zuerst eine Server-ID wählen.');return False
        try:action();self.refresh();return True
        except (CommunityError,OSError,ValueError) as exc:
            self.status.setText('Speichern fehlgeschlagen: '+str(exc));QMessageBox.warning(self,'Community',str(exc));return False
    def refresh(self):
        if not self.guild_id:return
        g=self.store.guild(self.guild_id)
        self.refresh_activity()
        self.refresh_engagement()
        self.sync_list(self.nights,g['nights'],'_night_signature',lambda n:f"{n['title']} · {parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')} · {n['status']}")
        self.refresh_creators()
        self.show_poll_status();self.refresh_connection_controls();self.dashboard()
    def channel_changed(self):
        if hasattr(self,'auto_sample'):self.auto_sample.setChecked(False)
        if hasattr(self,'history_table'):self.refresh_activity()
        if hasattr(self,'engagement_select'):self.refresh_engagement()
    def refresh_activity_feedback(self):
        self.refresh_activity();self.refresh_engagement()
    def refresh_activity(self):
        channel=self.channel.currentData()
        g=self.store.guild(self.guild_id) if self.guild_id else {}
        sample=g.get('activity',{}).get(channel)
        def local(value):
            try:return parse_time(value).astimezone().strftime('%d.%m. %H:%M') if value else 'unbekannt'
            except (ValueError,TypeError):return 'ungültiger Zeitpunkt'
        quality=activity_quality(sample)
        self.activity_quality.setText({
            'missing':'Noch keine Messung. Für neue Daten diesen Server verbinden.',
            'fresh':'Aktuelle Erfassung · zugängliches 24h-Fenster oder Verlaufende erreicht. Keine vollständige Serverstatistik.',
            'stale':'Veraltet · älter als sechs Stunden. Werte bleiben als frühere Erfassung sichtbar; vor Entscheidungen aktualisieren.',
            'limited':'Begrenzte / unbestätigte Abdeckung · Werte sind nur eine Stichprobe. Keine verlässliche Aussage über Inaktivität.',
            'future':'Erfassungszeitpunkt in der Zukunft · PC-Uhr prüfen und neu erfassen.',
            'invalid':'24h-Werte / Zeitpunkt nicht verwendbar · neu erfassen. Gespeicherte Daten bleiben erhalten.'
        }[quality])
        if sample:
            self.activity_metrics.setText(f"24h vor Erfassung am {local(sample.get('checked_at'))} · {sample.get('messages_24h','—')} Nachrichten · {sample.get('participants_24h','—')} Personen")
            if quality in ('future','invalid'):self.activity_metrics.setText('Keine belastbaren aktuellen 24h-Werte · neu erfassen.')
            text=f"#{self.channel.currentText()} · zuletzt geprüft {local(sample.get('checked_at'))}\n{sample.get('messages','—')} menschliche Nachrichten in {sample.get('sample_size','—')} gelesenen Nachrichten\nErfasster Zeitraum: {local(sample.get('oldest'))} – {local(sample.get('latest'))}"
            coverage=sample.get('coverage')
            if coverage in ('window_reached','history_end'):text+='\nZeitfenster beziehungsweise zugängliches Verlaufende erreicht.'
            elif coverage=='empty_or_no_history_access':
                text+='\nKeine weiteren Nachrichten zurückgegeben. Kanal kann leer sein oder dem Bot fehlt Nachrichtenverlauf lesen. Abdeckung unbestätigt.'
                if sample['sample_size']==0:self.activity_metrics.setText('Keine belastbaren Aktivitätswerte · Verlaufzugriff prüfen.')
            elif sample.get('limit_reached'):text+='\nAbrufgrenze erreicht: weitere Nachrichten können fehlen.'
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
                for j,value in enumerate([local(row['checked_at']),row.get('messages_24h','—'),row.get('participants_24h','—'),row['sample_size'],{'window_reached':'24h erreicht','history_end':'Verlaufende','empty_or_no_history_access':'Unbestätigt','capped':'500-Grenze'}.get(row.get('coverage'),'Alte Stichprobe')]):self.history_table.setItem(i,j,QTableWidgetItem(str(value)))
            self._history_signature=signature
        finally:self.history_table.setUpdatesEnabled(True)

    def refresh_engagement(self):
        sample=self.store.guild(self.guild_id).get('activity',{}).get(self.channel.currentData()) if self.guild_id else None
        result=engagement_ideas(sample)
        self.engagement_basis.setText(result['basis']);self.engagement_hint.setText(result['limits'])
        # Preserve a draft being edited while the recommendation stays the same.
        signature=(self.guild_id,self.channel.currentData(),result['kind'])
        old_signature=getattr(self,'_engagement_signature',None)
        if old_signature==signature:return
        keep=old_signature is not None and old_signature[:2]==signature[:2] and self.engagement_draft.document().isModified()
        edited=self.engagement_draft.toPlainText() if keep else None
        self.engagement_select.blockSignals(True);self.engagement_select.clear()
        for idea in result['ideas']:self.engagement_select.addItem(idea['title'],idea)
        self.engagement_select.blockSignals(False);self._engagement_signature=signature;self.select_engagement()
        if edited is not None:self.engagement_draft.setPlainText(edited);self.engagement_draft.document().setModified(True)
    def select_engagement(self,*_):
        idea=self.engagement_select.currentData()
        if idea:self.engagement_why.setText(idea['why']);self.engagement_draft.setPlainText(idea['draft'])
    def copy_engagement(self):
        from PySide6.QtWidgets import QApplication
        text=self.engagement_draft.toPlainText().strip()
        if not text:self.status.setText('Bitte einen Gesprächsimpuls auswählen oder eingeben.');return
        QApplication.clipboard().setText(text);self.status.setText('Gesprächsimpuls kopiert. Noch nicht in Discord veröffentlicht.')

    def dashboard(self):
        if not hasattr(self.host,'community_summary'):return
        if hasattr(self.host,'dashboard_page'):self.host.dashboard_page.refresh_nights(self.guild_id,self.store)
        if not self.guild_id:self.host.community_summary.setText('Noch kein Server für lokale Community-Daten ausgewählt.');return
        g=self.store.guild(self.guild_id)
        states=[schedule_state(n) or n.get('poll_delivery',{}).get('state') for n in g['nights']]
        delivery=f"Abstimmungen: {states.count('scheduled')} geplant · {states.count('due')} fällig · {states.count('sent')} veröffentlicht"
        attention=states.count('expired')+states.count('cancelled');unclear=states.count('uncertain')+states.count('sending')
        if attention:delivery+=f' · {attention} gestoppte/abgelaufene Termine'
        if unclear:delivery+=f' · {unclear} unklare Versandversuche: in Discord prüfen'
        self.host.community_summary.setText(f"Community: {len(g['activity'])} Kanalstichproben · {sum(n['status']=='geplant' for n in g['nights'])} geplante Lobby Nights · {len(g['creators'])} Creator\n{delivery}\nStichproben und Planung sind lokal; keine vollständige Serveraktivitätsmessung.")
    def sample(self):
        client=self.host.discord_client;channel=self.channel.currentData();guild=self.guild_id
        if not client or client.guild!=guild or not channel:
            self.status.setText('Für neue Aktivitätsdaten zuerst diesen Server mit Discord verbinden.');return
        if self.host.discord_worker is not None:return
        self.status.setText('Aktivität wird gelesen …')
        def done(result):
            if self.guard(lambda:self.store.record_activity(guild,result)):
                self.status.setText('Aktivitätsstichprobe und Verlauf gespeichert.')
                self.activity_access.setText('Zugriff bei der letzten Erfassung bestätigt: Kanal ansehen und Nachrichtenverlauf anzeigen.')
        def failed(error):
            self.status.setText('Aktivität nicht erfasst. Hinweise im Activity System prüfen.')
            self.activity_access.setText(str(error))
            if str(error).startswith(('Aktivität blockiert:','Kanalzugriff blockiert:')):self.auto_sample.setChecked(False)
        self.host.run_discord_job(lambda:client.activity_window(channel),done,failed)
    def refresh_night_readiness(self,*_):
        if not hasattr(self,'night_readiness'):return
        try:
            _,due,options=night_fields(self.night_title.text(),self.night_time.text(),self.options.toPlainText())
            self.night_readiness.setText(f'Bereit zum lokalen Speichern · {len(options)} eindeutige Vorschläge · Termin {due.astimezone().strftime("%d.%m.%Y %H:%M")}. Vor Discord-Veröffentlichung folgt eine weitere Vorschau.')
        except (CommunityError,ValueError) as exc:self.night_readiness.setText('Entwurf noch nicht bereit: '+str(exc))
    def new_night(self):
        self.night_edit_id=None;self.night_edit_guild=None;self.nights.setCurrentRow(-1)
        self.night_title.setText('Lobby Night');self.night_time.setText((datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d 20:00'));self.options.clear()
        for widget in (self.night_title,self.night_time,self.options):widget.setEnabled(True)
        self.night_save.setEnabled(bool(self.guild_id));self.night_save.setText('Termin und Vorschläge speichern');self.night_review.setText('Neuer lokaler Entwurf · noch nicht gespeichert oder veröffentlicht.')
    def save_night(self):
        if self.night_edit_id:
            if self.night_edit_guild!=self.guild_id:self.status.setText('Server gewechselt. Lobby Night erneut auswählen.');return
            if self.guard(lambda:self.store.update_night(self.guild_id,self.night_edit_id,self.night_title.text(),self.night_time.text(),self.options.toPlainText())):self.status.setText('Lobby-Night-Entwurf aktualisiert. Noch nicht veröffentlicht.');self.show_poll_status()
            return
        created=[]
        if self.guard(lambda:created.append(self.store.add_night(self.guild_id,self.night_title.text(),self.night_time.text(),self.options.toPlainText()))):
            for i in range(self.nights.count()):
                if self.nights.item(i).data(Qt.UserRole)==created[0]['id']:self.nights.setCurrentRow(i);break
            self.status.setText('Lobby-Night-Entwurf gespeichert. Noch nicht veröffentlicht.')
    def add_night(self):self.save_night() # compatibility for existing callers
    def select_night(self):
        n=self.chosen_night()
        if not n:self.show_poll_status();return
        self.night_edit_id=n['id'];self.night_edit_guild=self.guild_id
        self.night_title.setText(n['title']);self.night_time.setText(parse_time(n['when']).astimezone().strftime('%Y-%m-%d %H:%M'));self.options.setPlainText('\n'.join(n['options']))
        locked=n.get('status')!='geplant' or n.get('poll_delivery',{}).get('state') not in (None,'ready')
        for widget in (self.night_title,self.night_time,self.options):widget.setEnabled(not locked)
        self.night_save.setEnabled(not locked);self.night_save.setText('Änderungen am Entwurf speichern')
        self.show_poll_status()
    def save_night_reminder(self):
        n=self.chosen_night()
        if not n or self.host.discord_worker is not None:return
        if self.guard(lambda:self.store.set_night_reminder(self.guild_id,n['id'],self.night_reminder.currentData())):
            self.show_poll_status();self.status.setText('Lokale Erinnerung gespeichert. Keine Discord-Nachricht geplant.')

    def refresh_poll_readiness(self,*_):
        if not hasattr(self,'poll_readiness') or not hasattr(self,'poll_multi'):return
        n=self.chosen_night()
        if not n:self.poll_readiness.setText('Veröffentlichung: zuerst einen gespeicherten Plan auswählen.');return
        state=n.get('poll_delivery',{}).get('state')
        if state=='scheduled' and schedule_state(n) in ('cancelled','expired'):
            self.poll_readiness.setText('Zeitplan gestoppt: Termin abgesagt oder abgelaufen. Keine Veröffentlichung.');return
        if state in ('sent','scheduled','sending','uncertain'):
            self.poll_readiness.setText({'sent':'Abstimmung veröffentlicht. Ergebnisse können geladen werden.','scheduled':'Veröffentlichung eingeplant. Die App muss laufen und verbunden sein.','sending':'Versand läuft oder wurde unterbrochen. Status in Discord prüfen.','uncertain':'Versand unklar. Vor jeder Wiederholung in Discord prüfen.'}[state]);return
        missing=[]
        client=self.host.discord_client
        if not client or client.guild!=self.guild_id:missing.append('mit diesem Discord-Server verbinden')
        if not self.poll_channel.currentData():missing.append('Zielkanal auswählen')
        try:
            night_fields(n['title'],n['when'],'\n'.join(n['options']))
            if n.get('status')!='geplant':raise CommunityError('Termin ist abgesagt.')
            if self.poll_channel.currentData():poll_spec(self.guild_id,deepcopy(n),self.poll_channel.currentData(),self.poll_hours.currentData(),self.poll_multi.isChecked())
        except (CommunityError,ValueError,TypeError) as exc:missing.append(str(exc))
        if self.host.discord_worker is not None:missing.append('laufenden Vorgang abwarten')
        self.poll_readiness.setText('Noch offen: '+ ' · '.join(missing) if missing else 'Bereit für die Vorschau. Bot-Rechte werden erst beim Discord-Aufruf geprüft; noch nicht veröffentlicht.')

    def chosen_night(self):
        item=self.nights.currentItem()
        return next((n for n in self.store.guild(self.guild_id)['nights'] if item and n['id']==item.data(Qt.UserRole)),None) if self.guild_id else None
    def copy_poll(self):
        n=self.chosen_night()
        if n:
            from PySide6.QtWidgets import QApplication
            text=n['title']+' · '+parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')+'\nWas wollt ihr spielen?\n'+'\n'.join(f'{i+1}. {v}' for i,v in enumerate(n['options']))+'\nEigene Vorschläge sind willkommen!'
            QApplication.clipboard().setText(text);self.status.setText('Abstimmungstext kopiert. Noch nicht in Discord veröffentlicht.')
    def show_poll_status(self):
        if not hasattr(self,'poll_status'):return
        n=self.chosen_night()
        d=n.get('poll_delivery',{}) if n else {}
        if hasattr(self,'night_review'):
            self.night_review.setText(('Ausgewählter Plan · '+n['title']+' · '+parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M')+'\nVorschläge: '+' · '.join(f'{i+1}. {v}' for i,v in enumerate(n['options']))+'\nDies ist kein Discord-Event.') if n else 'Noch keinen gespeicherten Lobby-Night-Plan ausgewählt.')
        if d.get('state')=='sent':
            self.poll_status.setText('Veröffentlicht: https://discord.com/channels/'+self.guild_id+'/'+d['channel']+'/'+d['message_id'])
        elif d.get('state')=='scheduled':
            state=schedule_state(n)
            detail={'cancelled':'Termin abgesagt · wird nicht versendet. Zeitplan kann gestoppt werden.', 'expired':'Termin abgelaufen · wird nicht mehr versendet. Zeitplan kann gestoppt werden.', 'due':'Veröffentlichung fällig · wartet auf passende Verbindung und freien Discord-Zugriff.', 'scheduled':'App muss laufen und mit diesem Server verbunden sein.'}[state]
            self.poll_status.setText('Veröffentlichungszeit: '+parse_time(d['send_at']).astimezone().strftime('%d.%m.%Y %H:%M')+' · '+detail)
        elif d.get('state') in ('sending','uncertain'):self.poll_status.setText('Versand unklar. Zuerst in Discord prüfen; kein automatischer Neuversand.')
        else:self.poll_status.setText('Noch nicht veröffentlicht. Bot benötigt Kanal ansehen, Nachrichten senden und Abstimmungen erstellen.')
        self.refresh_connection_controls()
        if n:
            minutes=n.get('reminder_minutes',0);self.night_reminder.setCurrentIndex(self.night_reminder.findData(minutes))
            when=parse_time(n['when'])-timedelta(minutes=minutes or 0)
            self.night_reminder_status.setText('Erinnerung ausgeschaltet.' if minutes is None else ('Bereits erinnert · ' if n.get('reminded') else 'Lokale Erinnerung · ')+when.astimezone().strftime('%d.%m.%Y %H:%M'))
        else:self.night_reminder_status.setText('Erinnerung: zuerst einen gespeicherten Plan auswählen.')
        self.night_reminder_save.setEnabled(bool(n and n.get('status')=='geplant' and self.host.discord_worker is None))
        self.refresh_poll_readiness()
    def review_poll(self,scheduled=False):
        client=self.host.discord_client;n=self.chosen_night()
        if self.host.discord_worker is not None:return
        if not client or client.guild!=self.guild_id:self.status.setText('Zuerst den gewählten Server mit Discord verbinden.');return
        if not n:self.status.setText('Zuerst einen gespeicherten Lobby-Night-Termin auswählen.');return
        if n.get('poll_delivery',{}).get('state')=='scheduled':self.status.setText('Vor einer neuen Veröffentlichung den bestehenden Zeitplan stoppen.');return
        try:spec=poll_spec(self.guild_id,deepcopy(n),self.poll_channel.currentData(),self.poll_hours.currentData(),self.poll_multi.isChecked())
        except (CommunityError,ValueError,TypeError) as exc:self.status.setText(str(exc));return
        text='Server: '+self.guild_id+'\nKanal: '+self.poll_channel.currentText()+'\n'+spec['payload']['content']+'\n\n'+spec['payload']['poll']['question']['text']+'\n'+'\n'.join(n['options'])+'\nLaufzeit: '+str(spec['payload']['poll']['duration'])+' Stunden\nMehrfachauswahl: '+('Ja' if self.poll_multi.isChecked() else 'Nein')+'\n\nJetzt diese echte Discord-Abstimmung veröffentlichen? Keine Rollen- oder Mitglieder-Pings.'
        if scheduled:
            try:
                due=parse_time(self.poll_send_time.text().strip())
                from datetime import timezone
                if not datetime.now(timezone.utc)<due<parse_time(n['when']):raise CommunityError('Veröffentlichung muss in der Zukunft und vor der Lobby Night liegen.')
            except (CommunityError,ValueError) as exc:self.status.setText(str(exc));return
            text=text.replace('Jetzt diese echte Discord-Abstimmung veröffentlichen?', 'Diese Abstimmung automatisch am '+due.astimezone().strftime('%d.%m.%Y %H:%M')+' veröffentlichen? App muss laufen und verbunden sein.')
        if QMessageBox.question(self,'Discord-Abstimmung veröffentlichen',text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        journal=PollJournal(self.store)
        if scheduled:
            if self.guard(lambda:journal.schedule(spec,self.poll_send_time.text().strip())):self.status.setText('Veröffentlichung geplant. App geöffnet und verbunden lassen.')
            return
        self.publish_approved_poll(spec,client)
    def publish_approved_poll(self,spec,client):
        if self.host.discord_worker is not None:self.status.setText('Ein anderer Vorgang läuft. Veröffentlichung danach erneut prüfen.');return
        journal=PollJournal(self.store)
        try:journal.begin(spec)
        except (CommunityError,OSError) as exc:self.status.setText('Versand nicht begonnen: '+str(exc));return
        self.show_poll_status();self.status.setText('Discord-Abstimmung wird veröffentlicht …')
        def sent(result):
            try:journal.finish(spec,result)
            except (CommunityError,OSError,ValueError) as exc:
                self.status.setText('Discord hat geantwortet, aber Versandstatus konnte nicht bestätigt werden. In Discord prüfen; nicht erneut senden.');self.show_poll_status();return
            self.status.setText('Discord-Abstimmung veröffentlicht.');self.refresh()
        def failed(error):
            try:journal.uncertain(spec)
            except OSError:pass
            self.status.setText(error+' Versand unklar: vor Wiederholung in Discord prüfen.');self.show_poll_status()
        self.host.run_discord_job(lambda:send_poll(client,spec),sent,failed)
    def reset_poll(self):
        if self.host.discord_worker is not None:return
        n=self.chosen_night()
        if not n:return
        if n.get('poll_delivery',{}).get('state') not in ('sending','uncertain'):self.status.setText('Kein unklarer Versand ausgewählt.');return
        if QMessageBox.question(self,'Neuversand freigeben','Hast du im Zielkanal geprüft, dass diese Abstimmung NICHT veröffentlicht wurde? Eine falsche Freigabe kann doppelte Abstimmungen erzeugen.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        self.guard(lambda:PollJournal(self.store).reset_uncertain(self.guild_id,n['id']))

    def stop_scheduled_poll(self):
        if self.host.discord_worker is not None:return
        n=self.chosen_night()
        if n:self.guard(lambda:PollJournal(self.store).unschedule(self.guild_id,n['id']))
    def dispatch_scheduled_poll(self):
        self.show_poll_status();self.dashboard()
        client=self.host.discord_client
        if not client or client.guild!=self.guild_id or self.host.discord_worker is not None:return
        try:
            due=PollJournal(self.store).due(self.guild_id)
            if due:self.publish_approved_poll(due[0],client)
        except (CommunityError,OSError,ValueError) as exc:self.status.setText('Geplante Veröffentlichung blockiert: '+str(exc))

    def load_poll_results(self):
        client=self.host.discord_client;n=self.chosen_night()
        if self.host.discord_worker is not None:return
        if not n or n.get('poll_delivery',{}).get('state')!='sent':self.poll_status.setText('Zuerst eine veröffentlichte Abstimmung auswählen.');return
        if not client or client.guild!=self.guild_id:self.status.setText('Für Ergebnisse zuerst Discord verbinden.');return
        delivery=deepcopy(n['poll_delivery']);guild=self.guild_id
        self.host.run_discord_job(lambda:read_poll_results(client,guild,delivery),self.poll_status.setText,self.poll_status.setText)
    def copy_poll_link(self):
        from PySide6.QtWidgets import QApplication
        n=self.chosen_night();d=n.get('poll_delivery',{}) if n else {}
        if d.get('state')!='sent':self.status.setText('Noch kein bestätigter Abstimmungslink vorhanden.');return
        QApplication.clipboard().setText('https://discord.com/channels/'+self.guild_id+'/'+d['channel']+'/'+d['message_id']);self.status.setText('Abstimmungslink kopiert.')

    def cancel_night(self):
        if self.host.discord_worker is not None:return
        n=self.chosen_night()
        if n:self.guard(lambda:self.store.cancel_night(self.guild_id,n['id']))
    def reminders(self):
        if not self.guild_id:return
        try:
            due=self.store.due_nights(self.guild_id)
            for n in due:
                self.store.mark_reminded(self.guild_id,n['id'])
                QMessageBox.information(self,'Lobby Night Erinnerung',n['title']+' · Termin: '+parse_time(n['when']).astimezone().strftime('%d.%m.%Y %H:%M'))
        except (CommunityError,OSError,ValueError) as exc:self.status.setText(str(exc))
    def refresh_creators(self,*_):
        if not hasattr(self,'creator_matches'):return
        rows=self.store.guild(self.guild_id)['creators'] if self.guild_id else []
        self.creator_summary.setText('  ·  '.join(f"{sum(x['status']==status for x in rows)} {status}" for status in ('Bewerbung','Angenommen','Pausiert')))
        query=self.creator_search.text().strip().casefold();status=self.creator_filter.currentText()
        filtered=sorted((x for x in rows if (status=='Alle Status' or x['status']==status) and (not query or query in x['name'].casefold() or query in x['url'].casefold())),key=lambda x:x['name'].casefold())
        selected=self.creators.currentItem().data(Qt.UserRole) if self.creators.currentItem() else None
        self.creators.blockSignals(True);self.creators.clear()
        for row in filtered:
            self.creators.addItem(row['name']+' · '+row['status']+'\n'+row['url']);item=self.creators.item(self.creators.count()-1);item.setData(Qt.UserRole,row['id'])
            if row['id']==selected:self.creators.setCurrentItem(item)
        self.creators.blockSignals(False)
        self.creator_matches.setText(f'{len(filtered)} von {len(rows)} Creator angezeigt' if filtered else 'Keine Treffer. Suche/Filter ändern oder eine Bewerbung hinzufügen.')
        self.creator_save.setEnabled(bool(self.guild_id));chosen=bool(self.creators.currentItem())
        self.creator_copy.setEnabled(chosen);self.creator_remove.setEnabled(chosen)
        self.refresh_creator_role_controls()
    def new_creator(self):
        self.creator_edit_id=None;self.creator_edit_guild=None
        self.creator_name.clear();self.creator_url.clear();self.creator_status.setCurrentIndex(0);self.creator_notes.clear();self.creator_next.setText('Neue Bewerbung anlegen.')
        self.creator_editor_title.setText('Neue Bewerbung');self.creator_save.setText('Bewerbung speichern')
        self.creators.setCurrentRow(-1);self.creator_copy.setEnabled(False);self.creator_remove.setEnabled(False)
        if hasattr(self,'creator_member_id'):self.creator_member_id.clear();self.creator_role_id.clear();self.creator_role_status.setText('Keine Verknüpfung ausgewählt.');self.refresh_creator_role_controls()
    def add_creator(self):
        if self.host.discord_worker is not None:return
        if not self.guild_id:self.status.setText('Zuerst eine Server-ID für lokale Bewerbungen auswählen.');return
        if self.creator_edit_id and self.creator_edit_guild!=self.guild_id:self.status.setText('Server gewechselt. Bewerbung erneut auswählen.');return
        url=self.creator_url.text().strip()
        if not self.creator_edit_id and any(x['url']==url for x in self.store.guild(self.guild_id)['creators']):
            self.status.setText('Kanallink bereits gespeichert. Den bestehenden Creator zum Bearbeiten auswählen.');return
        def save():
            row=self.store.save_creator(self.guild_id,self.creator_name.text(),url,self.creator_status.currentText(),self.creator_edit_id,notes=self.creator_notes.toPlainText())
            self.creator_edit_id=row['id'];self.creator_edit_guild=self.guild_id
        if self.guard(save):
            self.creator_editor_title.setText('Creator bearbeiten');self.creator_save.setText('Änderungen speichern')
            for i in range(self.creators.count()):
                if self.creators.item(i).data(Qt.UserRole)==self.creator_edit_id:self.creators.setCurrentRow(i);break
            self.status.setText('Creator lokal gespeichert. Keine Discord-Rolle geändert.')
    def select_creator(self,item,*_):
        self.creator_copy.setEnabled(bool(item));self.creator_remove.setEnabled(bool(item))
        if not item or not self.guild_id:return
        row=next((x for x in self.store.guild(self.guild_id)['creators'] if x['id']==item.data(Qt.UserRole)),None)
        if not row:return
        self.creator_edit_id=row['id'];self.creator_edit_guild=self.guild_id
        self.creator_notes.setPlainText(row.get('notes',''));self.creator_next.setText(creator_next_step(row))
        self.creator_name.setText(row['name']);self.creator_url.setText(row['url']);self.creator_status.setCurrentText(row['status'])
        self.creator_editor_title.setText('Creator bearbeiten');self.creator_save.setText('Änderungen speichern')
        link=row.get('discord_link',{});self.creator_member_id.setText(link.get('member_id',''));self.creator_role_id.setText(link.get('role_id',''))
        state=row.get('role_delivery',{}).get('state')
        self.creator_role_status.setText('Letzter Versand unklar. Erneut prüfen liest zuerst den Mitgliedsstatus.' if state in ('sending','uncertain') else 'Zuletzt bestätigt. Erneut prüfen liest den aktuellen Mitgliedsstatus.' if state=='confirmed' else 'Vor der Vergabe Verknüpfung speichern und Rechte prüfen.')
        self.refresh_creator_role_controls()
    def copy_creator_link(self):
        item=self.creators.currentItem()
        if not item or not self.guild_id:return
        row=next((x for x in self.store.guild(self.guild_id)['creators'] if x['id']==item.data(Qt.UserRole)),None)
        if row:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(row['url']);self.status.setText('Gespeicherter Kanallink kopiert.')
    def remove_creator(self):
        if self.host.discord_worker is not None:return
        item=self.creators.currentItem()
        if not item or not self.guild_id:return
        row=next((x for x in self.store.guild(self.guild_id)['creators'] if x['id']==item.data(Qt.UserRole)),None)
        if not row:return
        if QMessageBox.question(self,'Creator entfernen',row['name']+' aus dieser lokalen Übersicht entfernen? Discord-Rollen bleiben unverändert.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        if self.guard(lambda:self.store.remove_creator(self.guild_id,row['id'])):self.new_creator();self.status.setText('Creator aus der lokalen Übersicht entfernt.')
    def chosen_creator(self):
        item=self.creators.currentItem()
        return next((r for r in self.store.guild(self.guild_id)['creators'] if item and r['id']==item.data(Qt.UserRole)),None) if self.guild_id else None
    def refresh_creator_role_controls(self):
        if not hasattr(self,'creator_role_apply'):return
        if hasattr(self,'stream_panel'):self.stream_panel.refresh()
        row=self.chosen_creator();idle=self.host.discord_worker is None
        if hasattr(self,'creator_next'):self.creator_next.setText(creator_next_step(row) if row else 'Neue Bewerbung anlegen oder gespeicherten Creator auswählen.')
        self.creator_link_save.setEnabled(bool(row) and idle)
        self.creator_save.setEnabled(bool(self.guild_id) and idle);self.creator_remove.setEnabled(bool(row) and idle)
        for widget in (self.creators,self.creator_new,self.creator_search,self.creator_filter):widget.setEnabled(idle)
        for widget in (self.creator_member_id,self.creator_role_id):widget.setEnabled(bool(row) and idle)
        client=self.host.discord_client
        self.creator_role_apply.setEnabled(bool(row and row['status']=='Angenommen' and row.get('discord_link') and client and client.guild==self.guild_id and idle))
    def save_creator_link(self):
        row=self.chosen_creator()
        if not row or self.host.discord_worker is not None:return
        try:link=binding(self.creator_member_id.text().strip(),self.creator_role_id.text().strip())
        except ValueError as exc:self.creator_role_status.setText(str(exc));return
        if self.guard(lambda:save_binding(self.store,self.guild_id,row['id'],link)):
            self.creator_role_status.setText('Verknüpfung lokal gespeichert. Keine Discord-Rolle geändert. Alte Rollen werden beim Ändern einer Verknüpfung nicht entfernt.')
    def review_creator_role(self):
        row=self.chosen_creator();client=self.host.discord_client
        if self.host.discord_worker is not None:return
        if not row or row['status']!='Angenommen' or not row.get('discord_link') or not client or client.guild!=self.guild_id:
            self.creator_role_status.setText('Angenommenen Creator verknüpfen und mit seinem Server verbinden.');return
        guild=self.guild_id;item=row['id'];link=deepcopy(row['discord_link'])
        if link!=dict(member_id=self.creator_member_id.text().strip(),role_id=self.creator_role_id.text().strip()):
            self.creator_role_status.setText('Geänderte Verknüpfung zuerst lokal speichern.');return
        self.creator_role_status.setText('Mitglied, Rolle und Bot-Rechte werden gelesen …')
        def reviewed(plan):
            current=self.chosen_creator()
            if self.guild_id!=guild or not current or current['id']!=item or current.get('discord_link')!=link or current['status']!='Angenommen':
                self.creator_role_status.setText('Auswahl geändert. Erneut prüfen.');return
            if plan['has_role']:
                if self.guard(lambda:delivery(self.store,guild,item,link,'confirmed')):self.creator_role_status.setText('Rolle ist bereits vorhanden. Keine Änderung gesendet.')
                return
            text='Server: '+guild+'\nCreator: '+current['name']+'\nDiscord-Mitglied: '+plan['member_name']+' ('+link['member_id']+')\nRolle: '+plan['role_name']+' ('+link['role_id']+')\n\nDiese bestehende Rolle jetzt zuweisen? Andere Rollen bleiben erhalten. Keine Nachricht oder Benachrichtigung wird gesendet.'
            if QMessageBox.question(self,'Creator-Rolle zuweisen',text,QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
                self.creator_role_status.setText('Rollenvergabe abgebrochen. Keine Discord-Änderung gesendet.');return
            if self.host.discord_worker is not None or self.host.discord_client is not client:
                self.creator_role_status.setText('Verbindung oder laufender Vorgang geändert. Danach erneut prüfen.');return
            if not self.guard(lambda:delivery(self.store,guild,item,link,'sending')):return
            self.creator_role_status.setText('Bestätigte Rollenvergabe wird erneut geprüft und ausgeführt …')
            def done(result):
                if self.guard(lambda:delivery(self.store,guild,item,link,'confirmed')):self.creator_role_status.setText('Rolle beim Mitglied bestätigt.'+(' '+result['audit_warning'] if result.get('audit_warning') else ''))
                else:self.creator_role_status.setText('Status konnte nicht gespeichert werden. Vor Wiederholung Mitglied prüfen.')
            def failed(error):
                try:delivery(self.store,guild,item,link,'uncertain')
                except (OSError,CommunityError):pass
                self.creator_role_status.setText(error+' Versand unklar; kein automatischer Neuversand. Erneut prüfen liest den Mitgliedsstatus.')
            self.host.run_discord_job(lambda:assign_checked(client,plan),done,failed)
        self.host.run_discord_job(lambda:checked_plan(client,guild,link),reviewed,self.creator_role_status.setText)

    def analyze(self):
        if not self.host.server_context or self.host.server_context['id']!=self.guild_id:
            self.status.setText('Für die Serveranalyse zuerst die aktuelle Discord-Übersicht laden.');self.open_connection();return
        self.host.stack.setCurrentIndex(1)
        self.host.ai_input.setText('Analysiere die Serverstruktur und die verfügbaren Community-Daten. Benenne Datenlücken, drei belegte Erkenntnisse und drei priorisierte Mitmachideen für Activity System, Lobby Night und Creator Hub. Keine Kanalaktion planen; nur antworten. Keine vollständige Aktivitätsmessung behaupten.')
        self.host.ask_ai()
