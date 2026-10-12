"""Local matchmaking editor; no automatic Discord posting."""
from datetime import datetime, timedelta
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QSpinBox,QPushButton,QListWidget,QMessageBox
from PySide6.QtCore import Qt
from matchmaking import create_listing, join_listing, leave_listing, close_listing, active_listings
from community import CommunityError

class MatchmakingPanel(QWidget):
    def __init__(self, community_page):
        super().__init__()
        self.page = community_page
        layout = QVBoxLayout(self)
        label = QLabel("Lokale Mitspielersuche. Keine Veröffentlichung auf Discord. Discord-IDs statt Benutzernamen eingeben.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.owner = QLineEdit()
        self.owner.setPlaceholderText("Eigene Discord-Mitglieds-ID")
        layout.addWidget(self.owner)
        self.game = QLineEdit()
        self.game.setPlaceholderText("Spiel (z. B. Valorant)")
        layout.addWidget(self.game)
        self.mode = QLineEdit()
        self.mode.setPlaceholderText("Modus (z. B. Ranked)")
        layout.addWidget(self.mode)
        self.rank = QLineEdit()
        self.rank.setPlaceholderText("Rang (optional)")
        layout.addWidget(self.rank)
        self.slots = QSpinBox()
        self.slots.setRange(1,20)
        self.slots.setValue(4)
        layout.addWidget(QLabel("Gesuchte Mitspieler"))
        layout.addWidget(self.slots)
        self.start = QLineEdit((datetime.now()+timedelta(hours=1)).astimezone().isoformat(timespec="minutes"))
        self.start.setPlaceholderText("Startzeit ISO 8601 mit Zeitzone")
        layout.addWidget(self.start)
        add = QPushButton("Gesuch lokal speichern")
        add.clicked.connect(self.add_listing)
        layout.addWidget(add)
        self.listings = QListWidget()
        layout.addWidget(self.listings)
        buttons = QHBoxLayout()
        for name, handler in (("Aktualisieren",self.refresh),("Beitreten",self.join),("Verlassen",self.leave),("Schließen",self.close)):
            button=QPushButton(name)
            button.clicked.connect(handler)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.status=QLabel("Server auswählen und aktualisieren.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def guild(self):
        guild=self.page.guild_id or self.page.offline_server.currentText().strip()
        if not guild or not guild.isdecimal():
            raise CommunityError("Zuerst eine gültige Server-ID auswählen.")
        return guild

    def action(self, fn):
        try:
            result=fn()
            self.refresh()
            self.status.setText("Lokal gespeichert. Discord wurde nicht verändert.")
            return result
        except (CommunityError,OSError,ValueError) as error:
            self.status.setText(str(error))

    def selected(self):
        item=self.listings.currentItem()
        if item is None:
            raise CommunityError("Zuerst ein Gesuch auswählen.")
        return item.data(Qt.UserRole)

    def refresh(self):
        try:
            self.listings.clear()
            for row in active_listings(self.page.store,self.guild()):
                self.listings.addItem(f"{row['game']} · {row['mode']} · {len(row['members'])}/{row['slots']} · {row['starts_at']} · {row['status']}")
                self.listings.item(self.listings.count()-1).setData(Qt.UserRole,row['id'])
            self.status.setText(f"{self.listings.count()} aktive Gesuche (lokale Daten).")
        except (CommunityError,ValueError) as error:
            self.status.setText(str(error))

    def add_listing(self):
        self.action(lambda:create_listing(self.page.store,self.guild(),self.owner.text().strip(),self.game.text(),self.mode.text(),self.rank.text(),self.slots.value(),self.start.text().strip()))
    def join(self):
        self.action(lambda:join_listing(self.page.store,self.guild(),self.selected(),self.owner.text().strip()))
    def leave(self):
        self.action(lambda:leave_listing(self.page.store,self.guild(),self.selected(),self.owner.text().strip()))
    def close(self):
        self.action(lambda:close_listing(self.page.store,self.guild(),self.selected(),self.owner.text().strip()))
