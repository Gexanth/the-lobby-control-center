"""Creator Hub stream controls; API credentials live only in widgets for this session."""
from copy import deepcopy
from datetime import datetime
import sqlite3
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QMessageBox
from streams import StreamAPI, StreamJournal, StreamError, creator, save_config, set_enabled, send_stream, notification


class StreamPanel(QWidget):
    def __init__(self, community):
        super().__init__(); self.community = community; self.host = community.host
        self.selected = None; self.channel_signature = None
        layout = QVBoxLayout(self)
        title = QLabel('Stream-Benachrichtigungen'); title.setObjectName('cardTitle'); layout.addWidget(title)
        hint = QLabel('Quelle für den oben ausgewählten Creator prüfen. Zugangsdaten gelten nur für diese App-Sitzung. '
                      'Automatik läuft nur bei geöffneter, verbundener App. Keine Rollen-Pings. '
                      'MEE6 oder andere Bots müssen für diese Quelle separat deaktiviert sein, sonst sind doppelte Meldungen möglich.')
        hint.setWordWrap(True); layout.addWidget(hint)
        self.client_id = QLineEdit(); self.client_id.setPlaceholderText('Twitch Client-ID')
        self.token = QLineEdit(); self.token.setPlaceholderText('Twitch Access-Token (kein Stream-Key)'); self.token.setEchoMode(QLineEdit.Password)
        self.youtube_key = QLineEdit(); self.youtube_key.setPlaceholderText('YouTube Data API v3: API-Schlüssel'); self.youtube_key.setEchoMode(QLineEdit.Password)
        for w in (self.client_id, self.token, self.youtube_key): layout.addWidget(w)
        self.forget = QPushButton('Streaming-Zugangsdaten aus dieser Sitzung entfernen'); self.forget.clicked.connect(self.forget_keys); layout.addWidget(self.forget)
        self.channels = QComboBox(); layout.addWidget(QLabel('Discord-Zielkanal')); layout.addWidget(self.channels)
        self.resolve = QPushButton('Gespeicherten Creator-Kanal prüfen und Quelle übernehmen'); self.resolve.clicked.connect(self.resolve_source); layout.addWidget(self.resolve)
        self.source_label = QLabel('Angenommenen Creator auswählen.'); self.source_label.setWordWrap(True); self.source_label.setTextFormat(Qt.PlainText); layout.addWidget(self.source_label)
        self.conflict = QCheckBox('Ich habe andere Stream-Meldungen (z. B. MEE6) für diese Quelle deaktiviert.'); layout.addWidget(self.conflict)
        row = QHBoxLayout()
        self.enable = QPushButton('Meldungen für diesen Creator aktivieren'); self.enable.clicked.connect(self.enable_source); row.addWidget(self.enable)
        self.pause = QPushButton('Creator-Meldungen pausieren'); self.pause.clicked.connect(self.pause_source); row.addWidget(self.pause); layout.addLayout(row)
        self.check = QPushButton('Live-Status prüfen (ohne Nachricht)'); self.check.clicked.connect(self.check_only); layout.addWidget(self.check)
        self.running = QCheckBox('Überwachung für aktivierte Creator in dieser Sitzung starten'); layout.addWidget(self.running)
        self.running.toggled.connect(self.running_changed)
        hint = QLabel('Twitch: frühestens alle 2 Minuten je Quelle. YouTube: frühestens alle 30 Minuten; '
                      'maximal 80 Live-Suchen je 24 Stunden insgesamt in dieser Installation. '
                      'Bei mehreren YouTube-Creatorn kann das Budget früher aufgebraucht sein. Kurze Streams können verpasst werden. '
                      'Pause stoppt neue Abrufe; ein bereits laufender Versand kann nicht zurückgerufen werden.')
        hint.setWordWrap(True); layout.addWidget(hint)
        self.status = QLabel('Überwachung gestoppt.'); self.status.setWordWrap(True); self.status.setTextFormat(Qt.PlainText); layout.addWidget(self.status)
        self.history = QLabel(); self.history.setWordWrap(True); self.history.setTextFormat(Qt.PlainText); layout.addWidget(self.history)
        self.timer = QTimer(self); self.timer.setInterval(60000); self.timer.timeout.connect(self.tick); self.timer.start()

    def journal(self):
        return StreamJournal(self.community.store.path.parent)

    def api(self):
        return StreamAPI(self.client_id.text(), self.token.text(), self.youtube_key.text())

    def failure(self, message):
        self.running.setChecked(False)
        self.status.setText(str(message) + '\nÜberwachung gestoppt. Nach Behebung erneut starten.')
        self.refresh()

    def forget_keys(self):
        self.running.setChecked(False)
        self.client_id.clear(); self.token.clear(); self.youtube_key.clear()
        self.status.setText('Streaming-Zugangsdaten entfernt. Überwachung gestoppt.')

    def running_changed(self, checked):
        self.status.setText('Überwachung gestartet; nächste Prüfung innerhalb einer Minute.' if checked else 'Überwachung gestoppt. Bereits laufender Versand kann noch abschließen.')

    def refresh(self):
        c = self.community; row = c.chosen_creator(); client = self.host.discord_client
        idle = self.host.discord_worker is None
        connected = bool(client and client.guild == c.guild_id)
        signature = (c.guild_id, tuple(c.channels) if connected else ())
        if signature != self.channel_signature:
            chosen = self.channels.currentData(); self.channels.clear()
            if connected:
                for name, cid in c.channels: self.channels.addItem(name, cid)
            self.channels.setCurrentIndex(max(0, self.channels.findData(chosen)))
            if self.channel_signature and signature[0] != self.channel_signature[0]: self.running.setChecked(False)
            self.channel_signature = signature
        cfg = row.get('stream_config') if row else None
        identity = (c.guild_id, row['id'] if row else None, repr(cfg))
        if self.selected != identity:
            self.conflict.setChecked(False); self.selected = identity
            if cfg:
                index = self.channels.findData(cfg['channel'])
                if index >= 0: self.channels.setCurrentIndex(index)
        eligible = bool(row and row['status'] == 'Angenommen')
        valid = bool(eligible and cfg and cfg.get('creator_url') == row['url'])
        self.resolve.setEnabled(eligible and connected and idle)
        self.enable.setEnabled(valid and connected and idle and not cfg.get('enabled'))
        self.pause.setEnabled(bool(cfg and cfg.get('enabled')) and idle)
        self.check.setEnabled(valid and idle)
        for w in (self.client_id, self.token, self.youtube_key, self.forget, self.channels, self.conflict): w.setEnabled(idle)
        self.running.setEnabled(connected and (idle or self.running.isChecked()))
        if not connected: self.running.setChecked(False)
        self.source_label.setText((cfg['provider'].title() + ' · ' + cfg['name'] + '\n' + cfg['url'] + '\nZielkanal: ' + cfg['channel'] + '\n' +
                                  ('Aktiviert' if cfg.get('enabled') and valid else 'Pausiert / erneute Prüfung erforderlich')) if cfg else 'Noch keine geprüfte Quelle gespeichert.')
        self.history.clear()
        if cfg:
            try:
                journal = self.journal(); last = journal.status(c.guild_id, cfg)
                lines = []
                if last: lines.append('Letzter Abruf: ' + datetime.fromtimestamp(last[0]).strftime('%d.%m. %H:%M') + ' · ' + last[1])
                states = {'sending': 'Versand unklar (nicht wiederholen)', 'uncertain': 'Versand unklar (nicht wiederholen)', 'sent': 'Gesendet'}
                for stream, state, message, channel in journal.history(c.guild_id, cfg):
                    lines.append('Stream ' + stream + ': ' + states.get(state, state) + (' · https://discord.com/channels/' + c.guild_id + '/' + channel + '/' + message if message else ''))
                self.history.setText('\n'.join(lines) or 'Noch kein Live-Abruf oder Versand protokolliert.')
            except (OSError, sqlite3.Error) as exc:
                self.history.setText('Lokales Stream-Protokoll nicht lesbar. Überwachung gestoppt.'); self.running.setChecked(False)

    def resolve_source(self):
        c = self.community; row = c.chosen_creator(); client = self.host.discord_client
        if self.host.discord_worker is not None or not row or row['status'] != 'Angenommen' or not client or client.guild != c.guild_id: return
        channel = self.channels.currentData()
        if not channel: self.status.setText('Discord-Zielkanal auswählen.'); return
        guild, item, url = c.guild_id, row['id'], row['url']; api = self.api()
        self.running.setChecked(False)
        def work():
            target = client.channel(channel)
            if target.get('type') not in (0, 5): raise StreamError('Text- oder Ankündigungskanal auswählen.')
            return api.resolve(url)
        def done(source):
            if c.guild_id != guild or self.host.discord_client is not client: self.failure('Verbindung geändert. Erneut prüfen.'); return
            try:
                save_config(c.store, guild, item, source, channel, url)
                self.status.setText('Quelle bestätigt und pausiert gespeichert. Probelauf liest nur den Live-Status.'); self.refresh()
            except (ValueError, OSError) as exc: self.failure(exc)
        self.host.run_discord_job(work, done, self.failure)

    def enable_source(self):
        c = self.community; row = c.chosen_creator(); client = self.host.discord_client
        if self.host.discord_worker is not None or not row or not row.get('stream_config') or not client or client.guild != c.guild_id: return
        cfg = deepcopy(row['stream_config']); guild, item = c.guild_id, row['id']
        if self.channels.currentData()!=cfg['channel']: self.status.setText('Geänderten Zielkanal zuerst über die Quellenprüfung übernehmen.'); return
        if not self.conflict.isChecked(): self.status.setText('Zuerst bestätigen, dass andere Bots diese Quelle nicht mehr ankündigen.'); return
        if not client.writes: self.status.setText('Discord-Schreibzugriff zuerst aktivieren.'); return
        text = ('Quelle: ' + cfg['name'] + '\n' + cfg['url'] + '\nDiscord-Kanal: ' + cfg['channel'] +
                '\n\nBei laufender Überwachung für jeden erstmals erkannten Live-Stream eine Nachricht ohne Pings senden? '
                'Auch ein bereits laufender Stream kann beim ersten Abruf angekündigt werden.\n\nBeispiel:\n' +
                notification(cfg, {'url': cfg['url']}))
        if QMessageBox.question(self, 'Stream-Meldungen aktivieren', text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        if self.host.discord_worker is not None or self.host.discord_client is not client or c.guild_id != guild: self.status.setText('Vorgang oder Verbindung geändert. Erneut prüfen.'); return
        try:
            if creator(c.store, guild, item).get('stream_config') != cfg: raise StreamError('Quelle geändert. Erneut prüfen.')
            set_enabled(c.store, guild, item, True); self.status.setText('Creator aktiviert. Überwachung bei Bedarf separat starten.'); self.refresh()
        except (ValueError, OSError) as exc: self.failure(exc)

    def pause_source(self):
        row = self.community.chosen_creator()
        if not row or self.host.discord_worker is not None: return
        try:
            set_enabled(self.community.store, self.community.guild_id, row['id'], False)
            self.status.setText('Meldungen für diesen Creator pausiert.'); self.refresh()
        except (ValueError, OSError) as exc: self.failure(exc)

    def check_only(self):
        row = self.community.chosen_creator()
        if row: self.check_source(row, False)

    def tick(self):
        c = self.community; client = self.host.discord_client
        if not self.running.isChecked() or self.host.discord_worker is not None or not c.guild_id or not client or client.guild != c.guild_id: return
        try:
            journal = self.journal()
            for row in c.store.guild(c.guild_id)['creators']:
                cfg = row.get('stream_config', {})
                if row['status'] == 'Angenommen' and cfg.get('enabled') and cfg.get('creator_url') == row['url'] and journal.due(c.guild_id, cfg):
                    self.check_source(row, True); return
        except (ValueError, OSError, sqlite3.Error) as exc: self.failure(exc)

    def check_source(self, row, announce):
        if self.host.discord_worker is not None: return
        c = self.community; cfg = deepcopy(row.get('stream_config')); guild, item = c.guild_id, row['id']; client = self.host.discord_client
        if not cfg or row['status'] != 'Angenommen' or cfg.get('creator_url') != row['url']: return
        api = self.api()
        try:
            # Validate missing credentials before spending/persisting a query slot.
            if cfg['provider'] == 'twitch' and (not api.client_id or not api.token): raise StreamError('Twitch Client-ID und Access-Token eintragen.')
            if cfg['provider'] == 'youtube' and not api.youtube_key: raise StreamError('YouTube API-Schlüssel eintragen.')
            journal = self.journal(); journal.start_check(guild, cfg)
        except (ValueError, OSError, sqlite3.Error) as exc: self.failure(exc); return
        def failed(message):
            try: journal.record(guild, cfg, 'Fehler: ' + str(message))
            except (OSError, sqlite3.Error): pass
            self.failure(message)
        def checked(streams):
            try:
                journal.record(guild, cfg, 'Live: ' + str(len(streams)) if streams else 'Kein öffentlicher Live-Stream erkannt')
                self.status.setText(('Live erkannt.' if streams else 'Kein öffentlicher Live-Stream erkannt.') + (' Probelauf: keine Nachricht gesendet.' if not announce else ''))
                self.refresh()
                current = creator(c.store, guild, item)
                if not announce or not streams or not self.running.isChecked() or c.guild_id != guild or self.host.discord_client is not client or current.get('stream_config') != cfg or current['status'] != 'Angenommen' or current['url'] != cfg['creator_url'] or not cfg.get('enabled'): return
                if self.host.discord_worker is not None: return
                def send():
                    return '\n'.join(send_stream(client, journal, guild, cfg, stream) for stream in streams)
                def sent(result): self.status.setText(result); self.refresh()
                self.host.run_discord_job(send, sent, failed)
            except (ValueError, OSError, sqlite3.Error) as exc: failed(str(exc))
        self.host.run_discord_job(lambda: api.live(cfg), checked, failed)
