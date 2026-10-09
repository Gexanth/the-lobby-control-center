"""Dashboard presentation; consumes existing data without network requests."""
from datetime import datetime,timezone
import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton
from community import parse_time
from streams import stream_overview

def label(text,name=None):
    widget=QLabel(text);widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True)
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

        layout.addWidget(label('Community verwalten','sectionTitle'));row=QHBoxLayout();row.setSpacing(14)
        for title,description,action,tab in [('Activity System','Echte Kanalaktivität erfassen und passende Mitmachimpulse finden.','Aktivität öffnen',0),('Lobby Night','Spiele vorschlagen, Abstimmungen planen und Versand prüfen.','Lobby Night öffnen',1),('Creator Hub','Creator-Bewerbungen und ihren Bearbeitungsstand verwalten.','Creator Hub öffnen',2)]:
            frame,body=panel(title);body.addWidget(label(description,'muted'),1)
            button=QPushButton(action);button.clicked.connect(lambda _,t=tab:host.open_page(7,t));body.addWidget(button);row.addWidget(frame,1)
        layout.addLayout(row)

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
        self.nights.setText('\n\n'.join(parse_time(n['when']).astimezone().strftime('%d.%m. · %H:%M')+'  '+n['title'][:90] for n in upcoming[:3]) if upcoming else 'Keine anstehende Lobby Night. Plane einen Termin im Community-Bereich.')

    def refresh_streams(self,guild,store,monitoring=False):
        if not guild:
            self.stream_health.setText('Wähle unter Community einen Server, um lokale Stream-Zustände zu sehen.')
            return
        try:
            state=stream_overview(store.path.parent,guild,store.guild(guild)['creators'])
            session='läuft in dieser App-Sitzung' if monitoring else 'ist in dieser App-Sitzung gestoppt'
            checks=f"Abrufe aktiver Quellen: {state['current']} aktuell · {state['due']} fällig · {state['never']} noch nie"
            if state['errors']:checks+=f" · {state['errors']} mit Fehler/unklarem Abbruch"
            deliveries=f"Lokales Versandprotokoll: {state['sent']} bestätigt gesendet · {state['unclear']} unklar"
            if not state['journal']:deliveries='Lokales Versandprotokoll: noch keine Abrufe oder Sendungen gespeichert'
            self.stream_health.setText(f"{state['configured']} eingerichtet · {state['active']} aktiv · {state['paused']} pausiert/erneut zu prüfen\nÜberwachung {session}.\n{checks}\n{deliveries}")
        except (OSError,sqlite3.Error,ValueError):
            self.stream_health.setText('Lokales Stream-Protokoll ist nicht lesbar. Creator Hub öffnen und Überwachung gestoppt lassen.')
