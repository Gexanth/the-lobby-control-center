"""Discord REST adapter. No gateway, user-token or arbitrary-URL access."""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def snowflake(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{17,20}", value):
        raise ValueError("Discord-ID muss eine 17â€“20-stellige Zahl als Text sein.")
    return value


def name(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 100:
        raise ValueError("Name muss 1â€“100 Zeichen enthalten.")
    return value.strip()


class DiscordError(RuntimeError):
    pass


def discord_http_error_message(code,method,path):
    """Return sanitized, endpoint-specific help without response bodies or secrets."""
    if code==401:return 'Bot-Token ungültig. Zugangsdaten prüfen.'
    if code==403:
        if method=='GET' and re.fullmatch(r'/channels/[0-9]{17,20}/messages(?:\?.*)?',path):
            return ('Aktivität blockiert: Der Bot braucht im gewählten Kanal „Kanal ansehen“ und '
                    '„Nachrichtenverlauf anzeigen“. Discord → Kanal bearbeiten → Berechtigungen → '
                    'Bot-Rolle; beide Rechte erlauben. „Nachrichten senden“ ist für die Erfassung nicht erforderlich.')
        if method=='GET' and re.fullmatch(r'/channels/[0-9]{17,20}',path):
            return ('Kanalzugriff blockiert: Der Bot braucht im gewählten Kanal „Kanal ansehen“. '
                    'Discord → Kanal bearbeiten → Berechtigungen → Bot-Rolle prüfen.')
        return 'Bot hat keinen Zugriff. Rechte der Bot-Rolle und Kanalüberschreibungen prüfen.'
    if code==404:
        if method=='GET' and path.startswith('/channels/'):
            return 'Kanal nicht gefunden oder für den Bot nicht sichtbar. Kanalwahl und „Kanal ansehen“ prüfen.'
        return 'Kanal oder Server nicht gefunden beziehungsweise nicht zugänglich.'
    return f'Discord HTTP {code}: Rechte, IDs und Bot-Verbindung prüfen.'


class Lobby:
    def __init__(self, token, guild_id, writes=False, db="data/lobby.sqlite3", transport=None):
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN fehlt.")
        self.guild = snowflake(guild_id)
        self.token, self.writes, self.db = token, writes, Path(db)
        self.transport = transport or self._http

    @classmethod
    def from_env(cls):
        return cls(os.getenv("DISCORD_BOT_TOKEN"), os.getenv("DISCORD_GUILD_ID"),
                   os.getenv("LOBBY_ALLOW_WRITES", "false").lower() == "true",
                   os.getenv("LOBBY_DATABASE", "data/lobby.sqlite3"))

    def _http(self, method, path, payload=None, reason=None):
        headers = {"Authorization": "Bot " + self.token,
                   "Content-Type": "application/json", "User-Agent": "TheLobby/0.1"}
        if reason:
            headers["X-Audit-Log-Reason"] = quote(reason, safe="")
        data = None if payload is None else json.dumps(payload).encode()
        try:
            with urlopen(Request("https://discord.com/api/v10" + path, data=data,
                                 headers=headers, method=method), timeout=20) as response:
                body = response.read()
                return json.loads(body) if body else {"ok": True}
        except HTTPError as error:
            # Never expose response bodies, tokens, or request headers.
            if error.code == 429:
                raise DiscordError("Discord-Anfragelimit erreicht. Später erneut versuchen; keine automatische Wiederholung.") from None
            raise DiscordError(discord_http_error_message(error.code,method,path)) from None
        except (URLError, TimeoutError):
            raise DiscordError("Discord nicht erreichbar. Bei Schreibaktionen vor Wiederholung den Server prÃ¼fen.") from None

    def request(self, method, path, payload=None, reason=None):
        return self.transport(method, path, payload, reason)

    def channels(self):
        return self.request("GET", f"/guilds/{self.guild}/channels")

    def roles(self):
        return self.request("GET", f"/guilds/{self.guild}/roles")

    def channel(self, channel_id):
        snowflake(channel_id)
        channel = self.request("GET", f"/channels/{channel_id}")
        if channel.get("guild_id") != self.guild:
            raise ValueError("Channel gehÃ¶rt nicht zu The Lobby.")
        return channel

    def overview(self):
        guild = self.request("GET", f"/guilds/{self.guild}?with_counts=true")
        return {"id": guild["id"], "name": guild["name"],
                "approximate_members_including_bots": guild.get("approximate_member_count"),
                "online_now_not_weekly_activity": guild.get("approximate_presence_count"),
                "nsfw_level": guild.get("nsfw_level"),
                "channels": [{k: c.get(k) for k in ("id", "name", "type", "parent_id", "topic")}
                             for c in self.channels()],
                "roles": [{k: r.get(k) for k in ("id", "name", "position", "permissions", "managed")}
                          for r in self.roles()]}

    def recent_messages(self, channel_id, limit=25):
        self.channel(channel_id)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit muss zwischen 1 und 100 liegen.")
        messages = self.request("GET", f"/channels/{channel_id}/messages?limit={limit}")
        return [{"id": m["id"], "author_id": m.get("author", {}).get("id"),
                 "content": m.get("content", ""), "bot": m.get("author", {}).get("bot", False), "timestamp": m.get("timestamp")}
                for m in messages]

    def activity_window(self,channel_id,max_pages=5,now=None):
        """Read a bounded 24h window, retaining only aggregate metadata."""
        from datetime import timedelta
        from community import activity_sample,parse_time
        if type(max_pages) is not int or not 1<=max_pages<=5:raise ValueError('Maximal fünf Abrufe pro Erfassung.')
        channel=self.channel(channel_id)
        if channel.get('type') not in (0,5):raise ValueError('Aktivität benötigt einen Text- oder Ankündigungskanal.')
        now=now or datetime.now(timezone.utc);cutoff=now-timedelta(hours=24)
        before=None;seen=set();messages=[];pages=0;coverage='capped';scanned=0
        for _ in range(max_pages):
            path=f'/channels/{channel_id}/messages?limit=100'
            if before:path+='&before='+before
            batch=self.request('GET',path);pages+=1
            if not isinstance(batch,list) or len(batch)>100:raise DiscordError('Discord lieferte keine gültige Nachrichtenliste.')
            if not batch:
                coverage='empty_or_no_history_access';break
            older=False;ids=[]
            for m in batch:
                mid=snowflake(m.get('id'));ids.append(mid)
                if mid in seen:continue
                seen.add(mid);scanned+=1
                try:when=parse_time(m['timestamp'])
                except (ValueError,KeyError):raise DiscordError('Ungültiger Nachrichtenzeitpunkt; Erfassung wurde verworfen.') from None
                if when<cutoff:older=True;continue
                if when>now:continue
                author=m.get('author',{})
                messages.append({'author_id':author.get('id'),'bot':author.get('bot',False),'timestamp':m['timestamp']})
            cursor=min(ids,key=int)
            if before is not None and int(cursor)>=int(before):raise DiscordError('Nachrichtenabruf ohne Fortschritt; Erfassung wurde verworfen.')
            before=cursor
            if older:coverage='window_reached';break
            if len(batch)<100:coverage='history_end';break
        sample=activity_sample(messages,channel_id,now)
        sample.update(sample_size=scanned,pages=pages,coverage=coverage,limit_reached=coverage=='capped',window_start=cutoff.isoformat(),window_end=now.isoformat(),scope='24-Stunden-Fenster, maximal 500 Nachrichten in fünf Abrufen. Nur zugängliche, noch vorhandene Nachrichten; keine gelöschten Nachrichten oder Voice-Aktivität.')
        return sample

    def _change(self, method, path, payload, reason, preview):
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 200:
            raise ValueError("Konkreten Nutzerauftrag als reason (1â€“200 Zeichen) angeben.")
        if type(preview) is not bool:
            raise ValueError("preview muss bool sein.")
        if preview:
            return {"preview": True, "method": method, "path": path, "payload": payload, "reason": reason}
        if not self.writes:
            raise ValueError("Schreibzugriff deaktiviert: LOBBY_ALLOW_WRITES=true konfigurieren.")
        # Validate local audit storage before sending a write.
        with self._db():
            pass
        result = self.request(method, path, payload, reason)
        try:
            with self._db() as db:
                db.execute("INSERT INTO audit(ts, method, path) VALUES (?, ?, ?)",
                           (datetime.now(timezone.utc).isoformat(), method, path))
        except (OSError, sqlite3.Error):
            result = dict(result, audit_warning="Änderung ausgeführt; lokales Protokoll konnte nicht gespeichert werden.")
        return result

    def create_channel(self, channel_name, kind="text", category_id=None, reason="", preview=True):
        types = {"text": 0, "voice": 2, "category": 4}
        if kind not in types:
            raise ValueError("kind: text, voice oder category.")
        payload = {"name": name(channel_name), "type": types[kind]}
        if category_id:
            if kind == "category" or self.channel(category_id).get("type") != 4:
                raise ValueError("UngÃ¼ltige Ã¼bergeordnete Kategorie.")
            payload["parent_id"] = category_id
        return self._change("POST", f"/guilds/{self.guild}/channels", payload, reason, preview)

    def edit_channel(self, channel_id, channel_name=None, topic=None, reason="", preview=True):
        channel = self.channel(channel_id)
        payload = {}
        if channel_name is not None:
            payload["name"] = name(channel_name)
        if topic is not None:
            if channel.get("type") != 0 or not isinstance(topic, str) or len(topic) > 1024:
                raise ValueError("Beschreibung nur fÃ¼r Textchannel, maximal 1024 Zeichen.")
            payload["topic"] = topic
        if not payload:
            raise ValueError("Keine Ã„nderung angegeben.")
        return self._change("PATCH", f"/channels/{channel_id}", payload, reason, preview)

    def delete_channel(self, channel_id, reason="", preview=True):
        channel = self.channel(channel_id)

        if channel.get("guild_id") != self.guild:
            raise ValueError("Channel gehört nicht zu The Lobby.")

        return self._change(
            "DELETE",
            f"/channels/{channel_id}",
            None,
            reason,
            preview
        )
    def create_role(self, role_name, color=0, reason="", preview=True):
        if type(color) is not int or not 0 <= color <= 0xFFFFFF:
            raise ValueError("Farbe muss eine Zahl zwischen 0 und 16777215 sein.")
        return self._change("POST", f"/guilds/{self.guild}/roles",
                            {"name": name(role_name), "color": color, "permissions": "0",
                             "mentionable": False}, reason, preview)

    def member_role(self, member_id, role_id, action="add", reason="", preview=True):
        snowflake(member_id)
        snowflake(role_id)
        if action not in ("add", "remove"):
            raise ValueError("action: add oder remove.")
        role = next((r for r in self.roles() if r["id"] == role_id), None)
        if not role or role_id == self.guild or role.get("managed") or int(role.get("permissions", "0")) != 0:
            raise ValueError("Nur normale Rollen ohne Zusatzberechtigungen sind zuweisbar.")
        self.request("GET", f"/guilds/{self.guild}/members/{member_id}")
        return self._change("PUT" if action == "add" else "DELETE",
                            f"/guilds/{self.guild}/members/{member_id}/roles/{role_id}", None, reason, preview)

    def post_message(self, channel_id, content, reason="", preview=True):
        if self.channel(channel_id).get("type") not in (0, 5):
            raise ValueError("Nachrichten nur in Text-/AnkÃ¼ndigungschannels.")
        if not isinstance(content, str) or not 1 <= len(content.strip()) <= 2000:
            raise ValueError("Nachricht muss 1â€“2000 Zeichen enthalten.")
        return self._change("POST", f"/channels/{channel_id}/messages",
                            {"content": content, "allowed_mentions": {"parse": []}}, reason, preview)

    @contextmanager
    def _db(self):
        self.db.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db)
        db.execute("CREATE TABLE IF NOT EXISTS snapshots(ts TEXT, data TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, method TEXT, path TEXT)")
        try:
            with db:
                yield db
        finally:
            db.close()

    def snapshot(self):
        current = self.overview()
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            previous = db.execute("SELECT ts, data FROM snapshots ORDER BY rowid DESC LIMIT 1").fetchone()
            db.execute("INSERT INTO snapshots(ts, data) VALUES (?, ?)", (now, json.dumps(current)))
        report = {"timestamp": now, "current": current, "previous_timestamp": None,
                  "changes": None, "limitation": "Vergleich seit letzter Aufnahme; keine Voice-, Stream- oder Einladungsstatistik."}
        if previous:
            old = json.loads(previous[1])
            changes = {}
            for key in ("channels", "roles"):
                before = {x["id"]: x for x in old[key]}
                after = {x["id"]: x for x in current[key]}
                changes[key] = {"added": [after[i] for i in after.keys() - before.keys()],
                                "removed": [before[i] for i in before.keys() - after.keys()],
                                "changed": [{"before": before[i], "after": after[i]} for i in before.keys() & after.keys()
                                            if before[i] != after[i]]}
            a, b = current["approximate_members_including_bots"], old["approximate_members_including_bots"]
            changes["member_delta_approximate"] = a - b if a is not None and b is not None else None
            report.update(previous_timestamp=previous[0], changes=changes)
        return report
