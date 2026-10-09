"""Dashboard presentation; consumes existing data without network requests."""
from datetime import datetime,timezone
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSizePolicy,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView
from community import parse_time
from streams import stream_overview
from attention import attention_items
from evidence import activity_evidence,QUALITY
from polls import schedule_state

def label(text,name=None):
    widget=QLabel(text);widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True)
    widget.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Minimum)
    if name:widget.setObjectName(name)
    return widget

def panel(title):
    frame=QFrame();frame.setObjectName('card');layout=QVBoxLayout(frame)
    layout.setContentsMargins(20,18,20,18);layout.setSpacing(10)
    layout.addWidget(label(title,'cardTitle'))
    return frame,layout

class DashboardPage(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host
        layout=QVBoxLayout(self);layout.setContentsMargins(32,28,32,28);layout.setSpacing(20)
        header=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(6)
        titles.addWidget(label('Übersicht','title'))
        titles.addWidget(label('Serverstatus, Community und nächste Schritte.','subtitle'));header.addLayout(titles,1)
        self.badge=label('●  Offline','statusPill');self.badge.setProperty('connected',False)
        self.badge.setAlignment(Qt.AlignCenter);header.addWidget(self.badge,0,Qt.AlignTop);layout.addLayout(header)

        row=QHBoxLayout();row.setSpacing(14);self.values={}
        for title,key,note in [('Mitglieder','members','Inklusive Bots · ungefähr'),('Gerade online','online','Momentaufnahme · ungefähr'),('Kanäle','channels','Aus der Serverübersicht'),('Offene Aufgaben','tasks','Lokal gespeichert')]:
            frame,body=panel(title);value=label('—','metric');self.values[key]=value
            body.addWidget(value);body.addWidget(label(note,'muted'));row.addWidget(frame,1)
        layout.addLayout(row)

        frame,body=panel('Dein Server');connection_row=QHBoxLayout()
        self.connection=label('Noch keine Verbindung. Lade unter Discord die Übersicht deines Servers.','subtitle')
        connection_row.addWidget(self.connection,1);button=QPushButton('Discord verbinden');button.setObjectName('primary')
        button.clicked.connect(lambda:host.open_page(2));connection_row.addWidget(button);body.addLayout(connection_row);layout.addWidget(frame)
        self.connection_button=button

        frame,body=panel('Das braucht deine Aufmerksamkeit')
        self.attention_body=body;self.attention_signature=None
        self.attention_empty=label('Wähle unter Community einen Server für deine lokalen Hinweise.','muted')
        body.addWidget(self.attention_empty);layout.addWidget(frame)

        layout.addWidget(label('Community verwalten','sectionTitle'));row=QHBoxLayout();row.setSpacing(14)
        for title,description,action,tab in [('Activity System','Echte Kanalaktivität erfassen und passende Mitmachimpulse finden.','Aktivität öffnen',0),('Lobby Night','Spiele vorschlagen, Abstimmungen planen und Versand prüfen.','Lobby Night öffnen',1),('Creator Hub','Creator-Bewerbungen und ihren Bearbeitungsstand verwalten.','Creator Hub öffnen',2)]:
            frame,body=panel(title);body.addWidget(label(description,'muted'),1)
            button=QPushButton(action);button.clicked.connect(lambda _,t=tab:host.open_page(7,t));body.addWidget(button);row.addWidget(frame,1)
        layout.addLayout(row)

        frame,body=panel('Aktivitätsverlauf')
        self.history_channel=QComboBox();self.history_channel.setPlaceholderText('Noch keine Kanalstichproben');body.addWidget(self.history_channel)
        self.history_note=label('Wähle unter Community einen Server.','muted');body.addWidget(self.history_note)
        self.history_table=QTableWidget(0,4);self.history_table.setHorizontalHeaderLabels(['Erfasst','Nachrichten / 24h','Personen / 24h','Datenqualität'])
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.history_table.verticalHeader().hide()
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.history_table.setMinimumHeight(180)
        body.addWidget(self.history_table);self.history_channel.currentIndexChanged.connect(self.show_history)
        self.history_data={};self.history_signature=None;layout.addWidget(frame)

        row=QHBoxLayout();row.setSpacing(14)
        frame,body=panel('Anstehende Lobby Nights');self.nights=label('Wähle unter Community einen Server, um lokale Termine zu sehen.','muted')
        body.addWidget(self.nights,1);row.addWidget(frame,1)
        frame,body=panel('Deine Aufgaben');self.summary=label('','muted');self.task_preview=label('Noch keine Aufgaben gespeichert.','muted')
        body.addWidget(self.summary);body.addWidget(self.task_preview,1)
        button=QPushButton('Aufgaben verwalten');button.clicked.connect(lambda:host.open_page(3));body.addWidget(button);row.addWidget(frame,1);layout.addLayout(row)

        row=QHBoxLayout();row.setSpacing(14)
        frame,body=panel('Community-Status');self.community_summary=label('Noch kein Server für lokale Community-Daten ausgewählt.','muted');body.addWidget(self.community_summary);row.addWidget(frame,1)
        frame,body=panel('Stream-Überwachung');self.stream_health=label('Wähle unter Community einen Server, um lokale Stream-Zustände zu sehen.','muted');body.addWidget(self.stream_health,1)
        button=QPushButton('Creator Hub öffnen');button.clicked.connect(lambda:host.open_page(7,2));body.addWidget(button);row.addWidget(frame,1);layout.addLayout(row)
        layout.addWidget(label('Serverwerte werden beim Laden der Discord-Übersicht aktualisiert. Lokale Planung ist auch offline verfügbar.','footnote'));layout.addStretch()

    def set_connected(self,data):
        connected=bool(data);self.badge.setText('●  Verbunden' if connected else '●  Offline')
        self.badge.setProperty('connected',connected);self.badge.style().unpolish(self.badge);self.badge.style().polish(self.badge)
        self.connection_button.setText('Serverübersicht öffnen' if connected else 'Discord verbinden')

    def refresh_tasks(self,items):
        pending=[x for x in items if x['status']!='Erledigt'];self.values['tasks'].setText(str(len(pending)))
        self.task_preview.setText('\n\n'.join('• '+x['text'][:120] for x in pending[:3]) if pending else 'Alles erledigt. Neue Aufträge kannst du im Assistenten als Aufgabe speichern.')

    def refresh_nights(self,guild,store):
        if not guild:self.nights.setText('Wähle unter Community einen Server, um lokale Termine zu sehen.');return
        now=datetime.now(timezone.utc)
        upcoming=sorted((n for n in store.guild(guild)['nights'] if n['status']=='geplant' and parse_time(n['when'])>now),key=lambda n:parse_time(n['when']))
        states={'scheduled':'Versand geplant','due':'Versand fällig','sent':'Abstimmung veröffentlicht','sending':'Versand unklar','uncertain':'Versand unklar','ready':'Entwurf'}
        self.nights.setText('\n\n'.join(parse_time(n['when']).astimezone().strftime('%d.%m. · %H:%M')+'  '+n['title'][:90]+'\n'+states.get(schedule_state(n,now) or n.get('poll_delivery',{}).get('state'),'Lokaler Entwurf') for n in upcoming[:3]) if upcoming else 'Keine anstehende Lobby Night. Plane einen Termin im Community-Bereich.')

    def refresh_streams(self,guild,store,monitoring=False):
        self.refresh_history(guild,store)
        if not guild:
            self.stream_health.setText('Wähle unter Community einen Server, um lokale Stream-Zustände zu sehen.')
            self.refresh_attention(None)
            return
        try:
            state=stream_overview(store.path.parent,guild,store.guild(guild)['creators'])
            session='läuft in dieser App-Sitzung' if monitoring else 'ist in dieser App-Sitzung gestoppt'
            checks=f"Abrufe aktiver Quellen: {state['current']} aktuell · {state['due']} fällig · {state['never']} noch nie"
            if state['errors']:checks+=f" · {state['errors']} mit Fehler/unklarem Abbruch"
            deliveries=f"Lokales Versandprotokoll: {state['sent']} bestätigt gesendet · {state['unclear']} unklar"
            if not state['journal']:deliveries='Lokales Versandprotokoll: noch keine Abrufe oder Sendungen gespeichert'
            self.stream_health.setText(f"{state['configured']} eingerichtet · {state['active']} aktiv · {state['paused']} pausiert/erneut zu prüfen\nÜberwachung {session}.\n{checks}\n{deliveries}")
            self.refresh_attention(attention_items(store.guild(guild),state,monitoring))
        except (OSError,sqlite3.Error,ValueError):
            self.stream_health.setText('Lokales Stream-Protokoll ist nicht lesbar. Creator Hub öffnen und Überwachung gestoppt lassen.')
            self.refresh_attention(attention_items(store.guild(guild),None,monitoring))

    def refresh_history(self,guild,store):
        data=activity_evidence(store.guild(guild)) if guild else {'channels':[]}
        names={c['id']:c.get('name',c['id']) for c in (self.host.server_context or {}).get('channels',[]) if (self.host.server_context or {}).get('id')==guild}
        # Age classification can change on the existing minute refresh.
        signature=(guild,repr(data['channels']),repr(names))
        if signature==self.history_signature:return
        selected=self.history_channel.currentData() if self.history_signature and self.history_signature[0]==guild else None
        self.history_signature=signature;self.history_data={x['channel_id']:x for x in data['channels']}
        self.history_channel.blockSignals(True);self.history_channel.clear()
        for cid,row in self.history_data.items():self.history_channel.addItem(names.get(cid,cid)+' · '+QUALITY[row['quality']],cid)
        self.history_channel.setCurrentIndex(max(0,self.history_channel.findData(selected)));self.history_channel.blockSignals(False);self.show_history()

    def show_history(self):
        row=self.history_data.get(self.history_channel.currentData());points=row['recent_points'] if row else []
        self.history_note.setText((f"{row['history_points']} gespeicherte Punkte · letzte {len(points)} sichtbar. " if row else 'Noch keine gespeicherten Verlaufspunkte. ')+'Überlappende 24h-Stichproben; nicht summieren. Begrenzte Werte sind keine vollständige Aktivitätsmessung.')
        self.history_table.setRowCount(len(points))
        for index,point in enumerate(reversed(points)):
            try:when=parse_time(point['checked_at']).astimezone().strftime('%d.%m. %H:%M')
            except (ValueError,TypeError):when='Ungültiger Zeitpunkt'
            coverage={'window_reached':'24h erreicht','history_end':'Verlaufende','capped':'Abrufgrenze','empty_or_no_history_access':'Zugriff unbestätigt'}.get(point['coverage'],'Abdeckung unbekannt')
            values=[when,str(point['messages_24h']) if point['messages_24h'] is not None else '—',str(point['participants_24h']) if point['participants_24h'] is not None else '—',QUALITY[point['quality']]+' · '+coverage]
            for col,value in enumerate(values):self.history_table.setItem(index,col,QTableWidgetItem(value))

    def refresh_attention(self,items):
        signature=repr(items)
        if signature==self.attention_signature:return
        self.attention_signature=signature
        while self.attention_body.count()>2:
            item=self.attention_body.takeAt(2)
            if item.widget():item.widget().deleteLater()
        self.attention_empty.setText('Wähle unter Community einen Server für deine lokalen Hinweise.' if items is None else 'Keine offenen Hinweise in den gespeicherten Daten. Das bestätigt keine vollständige Serverprüfung.')
        self.attention_empty.setVisible(not items)
        for hint in items or []:
            row=QWidget();body=QHBoxLayout(row);body.setContentsMargins(0,4,0,4)
            row.setStyleSheet('background: transparent;');row.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Minimum)
            text=label(hint['title']+'\n'+hint['detail'],'muted');body.addWidget(text,1)
            button=QPushButton('Prüfen');button.setAccessibleName(hint['title']+' prüfen')
            button.setMinimumHeight(38)
            button.clicked.connect(lambda _,tab=hint['tab']:self.host.open_page(7,tab));body.addWidget(button)
            self.attention_body.addWidget(row)
