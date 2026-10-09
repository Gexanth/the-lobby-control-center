"""Opt-in stream detection, fixed provider endpoints and durable at-most-once attempts."""
import copy
import hashlib
import json
import re
import sqlite3
import time
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from community import CommunityError
from lobby import snowflake


class StreamError(CommunityError):
    pass


def source_input(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.username or p.password or p.port or p.query or p.fragment:
        raise StreamError('Einen HTTPS-Kanallink ohne Parameter eingeben.')
    path = unquote(p.path).strip('/')
    if p.hostname in ('twitch.tv', 'www.twitch.tv') and re.fullmatch(r'[A-Za-z0-9_]{1,25}', path):
        return 'twitch', path.lower()
    if p.hostname in ('youtube.com', 'www.youtube.com'):
        if re.fullmatch(r'channel/UC[A-Za-z0-9_-]{22}', path):
            return 'youtube', path.split('/')[1]
        if path.startswith('@') and 2 <= len(path) <= 100 and '/' not in path:
            return 'youtube', path
    raise StreamError('Twitch-Kanallink oder YouTube /@handle bzw. /channel/UC… verwenden; keine Video-Links.')


def api_get(url, headers):
    # All URLs originate below, never from API responses or user-supplied hosts.
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            value = json.load(response)
        if not isinstance(value, dict):
            raise StreamError('Ungültige Antwort des Streaming-Anbieters.')
        return value
    except HTTPError as exc:
        hints = {401: 'Zugangsdaten ungültig oder abgelaufen.',
                 403: 'Zugriff gesperrt oder API-Kontingent ausgeschöpft.',
                 429: 'Anfragelimit erreicht. Überwachung pausieren und später erneut prüfen.'}
        raise StreamError(hints.get(exc.code, f'Streaming-Anbieter meldet HTTP {exc.code}.')) from None
    except (URLError, TimeoutError, ValueError):
        raise StreamError('Streaming-Anbieter nicht erreichbar oder Antwort ungültig.') from None


def rows(response, key):
    value = response.get(key)
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise StreamError('Unvollständige Streaming-Antwort; Status bleibt unbekannt.')
    return value


class StreamAPI:
    def __init__(self, client_id='', token='', youtube_key='', get=api_get):
        self.client_id, self.token, self.youtube_key = client_id.strip(), token.strip(), youtube_key.strip()
        self.get = get

    def twitch_auth(self):
        if not self.client_id or not self.token:
            raise StreamError('Twitch Client-ID und Access-Token für diese Sitzung eintragen.')
        result = self.get('https://id.twitch.tv/oauth2/validate', {'Authorization': 'OAuth ' + self.token})
        if result.get('client_id') != self.client_id or not isinstance(result.get('expires_in'), int) or result['expires_in'] <= 0:
            raise StreamError('Twitch-Token abgelaufen oder gehört zu einer anderen Client-ID.')

    def twitch(self, endpoint, **params):
        return self.get('https://api.twitch.tv/helix/' + endpoint + '?' + urlencode(params),
                        {'Client-Id': self.client_id, 'Authorization': 'Bearer ' + self.token})

    def youtube(self, endpoint, **params):
        if not self.youtube_key:
            raise StreamError('YouTube Data API-Schlüssel für diese Sitzung eintragen.')
        # Header keeps keys out of request URLs and error messages.
        return self.get('https://www.googleapis.com/youtube/v3/' + endpoint + '?' + urlencode(params),
                        {'X-Goog-Api-Key': self.youtube_key})

    def resolve(self, url):
        provider, identifier = source_input(url)
        if provider == 'twitch':
            self.twitch_auth()
            found = rows(self.twitch('users', login=identifier), 'data')
            if len(found) != 1 or found[0].get('login', '').lower() != identifier or not re.fullmatch(r'[0-9]+', str(found[0].get('id', ''))):
                raise StreamError('Twitch-Kanal konnte nicht eindeutig bestätigt werden.')
            user = found[0]
            return dict(provider=provider, source_id=user['id'], name=user.get('display_name', identifier), url='https://twitch.tv/' + identifier)
        query = {'id': identifier} if identifier.startswith('UC') else {'forHandle': identifier}
        found = rows(self.youtube('channels', part='snippet', **query), 'items')
        if len(found) != 1 or not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', found[0].get('id', '')):
            raise StreamError('YouTube-Kanal konnte nicht eindeutig bestätigt werden.')
        channel = found[0]
        if 'id' in query and channel['id'] != identifier:
            raise StreamError('YouTube-Kanalantwort passt nicht zur Auswahl.')
        return dict(provider=provider, source_id=channel['id'], name=channel.get('snippet', {}).get('title', identifier), url='https://youtube.com/channel/' + channel['id'])

    def live(self, source):
        if source['provider'] == 'twitch':
            self.twitch_auth()  # Validate at each poll, including first and after token changes.
            found = rows(self.twitch('streams', user_id=source['source_id'], first=1), 'data')
            if not found:
                return []
            s = found[0]
            if len(found) != 1 or s.get('user_id') != source['source_id'] or s.get('type') != 'live' or not re.fullmatch(r'[0-9]+', s.get('id', '')):
                raise StreamError('Twitch-Liveantwort passt nicht zur geprüften Quelle.')
            return [dict(id=s['id'], title=str(s.get('title', 'Livestream'))[:300], url=source['url'])]
        found = rows(self.youtube('search', part='snippet', channelId=source['source_id'], eventType='live', type='video', maxResults=50), 'items')
        ids = []
        for s in found:
            vid = s.get('id', {}).get('videoId', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid) or s.get('snippet', {}).get('channelId') != source['source_id']:
                raise StreamError('YouTube-Suchergebnis passt nicht zur geprüften Quelle.')
            ids.append(vid)
        if not ids:
            return []
        # Search may lag a stream ending: verify actual live state before announcing.
        videos = rows(self.youtube('videos', part='snippet,liveStreamingDetails', id=','.join(ids)), 'items')
        result = []
        for v in videos:
            snippet, detail = v.get('snippet', {}), v.get('liveStreamingDetails', {})
            if v.get('id') not in ids or snippet.get('channelId') != source['source_id']:
                raise StreamError('YouTube-Video gehört nicht zur geprüften Quelle.')
            if snippet.get('liveBroadcastContent') == 'live' and detail.get('actualStartTime') and not detail.get('actualEndTime'):
                result.append(dict(id=v['id'], title=str(snippet.get('title', 'Livestream'))[:300], url='https://youtube.com/watch?v=' + v['id']))
        return result


def creator(store, guild, item):
    row = next((r for r in store.guild(guild)['creators'] if r['id'] == item), None)
    if not row:
        raise StreamError('Creator nicht mehr vorhanden.')
    return row


def save_config(store, guild, item, source, channel, expected_url):
    snowflake(guild); snowflake(channel)
    row = creator(store, guild, item)
    if row['status'] != 'Angenommen' or row['url'] != expected_url:
        raise StreamError('Creator geändert oder nicht angenommen. Erneut prüfen.')
    for other in store.guild(guild)['creators']:
        config = other.get('stream_config', {})
        if other['id'] != item and config.get('source_id') == source['source_id'] and config.get('provider') == source['provider']:
            raise StreamError('Diese geprüfte Quelle ist bereits einem anderen Creator zugeordnet.')
    old = copy.deepcopy(row)
    row['stream_config'] = dict(source, channel=channel, creator_url=expected_url, enabled=False)
    try:
        store.save()
    except OSError:
        row.clear(); row.update(old); raise


def set_enabled(store, guild, item, enabled):
    row = creator(store, guild, item)
    cfg = row.get('stream_config')
    if not cfg or (enabled and (row['status'] != 'Angenommen' or cfg['creator_url'] != row['url'])):
        raise StreamError('Angenommenen Creator und gespeicherte Quelle zuerst prüfen.')
    old = copy.deepcopy(cfg)
    cfg['enabled'] = bool(enabled)
    try:
        store.save()
    except OSError:
        cfg.clear(); cfg.update(old); raise


class StreamJournal:
    """Separate SQLite file: atomic reservation across app instances and retained after creator removal."""
    def __init__(self, root):
        self.path = root / 'streams.sqlite3'
        root.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS deliveries (key TEXT PRIMARY KEY, guild TEXT, source TEXT, stream TEXT, channel TEXT, state TEXT, message TEXT, checked REAL)')
            db.execute('CREATE TABLE IF NOT EXISTS checks (source TEXT PRIMARY KEY, checked REAL, status TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS youtube_budget (checked REAL)')

    def db(self):
        # Explicit closing, since sqlite's connection context only commits/rolls back.
        from contextlib import contextmanager
        @contextmanager
        def connection():
            conn = sqlite3.connect(self.path, timeout=5)
            try:
                with conn:
                    yield conn
            finally:
                conn.close()
        return connection()

    @staticmethod
    def source_key(guild, cfg):
        return guild + ':' + cfg['provider'] + ':' + cfg['source_id']

    def status(self, guild, cfg):
        with self.db() as db:
            return db.execute('SELECT checked,status FROM checks WHERE source=?', (self.source_key(guild, cfg),)).fetchone()

    def due(self, guild, cfg, now=None):
        state = self.status(guild, cfg)
        interval = 1800 if cfg['provider'] == 'youtube' else 120
        return not state or (now if now is not None else time.time()) - state[0] >= interval

    def start_check(self, guild, cfg, now=None):
        now = time.time() if now is None else now
        key = self.source_key(guild, cfg)
        interval = 1800 if cfg['provider'] == 'youtube' else 120
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            last = db.execute('SELECT checked FROM checks WHERE source=?', (key,)).fetchone()
            if last and now - last[0] < interval:
                raise StreamError('Abfrageabstand noch nicht erreicht (Twitch 2 Minuten, YouTube 30 Minuten).')
            if cfg['provider'] == 'youtube':
                db.execute('DELETE FROM youtube_budget WHERE checked<?', (now - 86400,))
                if db.execute('SELECT count(*) FROM youtube_budget').fetchone()[0] >= 80:
                    raise StreamError('Lokales YouTube-Budget erreicht: maximal 80 Live-Suchen in 24 Stunden für alle Creator.')
                db.execute('INSERT INTO youtube_budget VALUES (?)', (now,))
            db.execute('INSERT OR REPLACE INTO checks VALUES (?,?,?)', (key, now, 'Prüfung läuft / nach Abbruch unbekannt'))

    def record(self, guild, cfg, status):
        with self.db() as db:
            db.execute('UPDATE checks SET status=? WHERE source=?', (status[:1000], self.source_key(guild, cfg)))

    def reserve(self, guild, cfg, stream):
        source = self.source_key(guild, cfg)
        key = hashlib.sha256((source + ':' + stream['id']).encode()).hexdigest()
        with self.db() as db:
            result = db.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?,?,?,?,?,?)',
                                (key, guild, source, stream['id'], cfg['channel'], 'sending', '', time.time()))
        return key if result.rowcount else None

    def finish(self, key, state, message=''):
        with self.db() as db:
            db.execute('UPDATE deliveries SET state=?,message=? WHERE key=?', (state, message, key))

    def history(self, guild, cfg):
        with self.db() as db:
            return db.execute('SELECT stream,state,message,channel FROM deliveries WHERE source=? ORDER BY checked DESC LIMIT 5', (self.source_key(guild, cfg),)).fetchall()


def stream_overview(path, guild, creators, now=None):
    """Summarize saved configuration and an existing journal without creating or changing it."""
    now = time.time() if now is None else now
    configured = [row for row in creators if row.get('stream_config')]
    active = []
    for row in configured:
        cfg = row['stream_config']
        if row.get('status') == 'Angenommen' and cfg.get('enabled') and cfg.get('creator_url') == row.get('url'):
            active.append(cfg)
    result = {'configured': len(configured), 'active': len(active), 'paused': len(configured) - len(active),
              'current': 0, 'due': 0, 'never': len(active), 'errors': 0, 'sent': 0, 'unclear': 0,
              'latest': None, 'journal': False}
    path = path / 'streams.sqlite3'
    if not path.is_file():
        return result
    # Read-only URI prevents this dashboard path from creating or migrating state.
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5) as db:
        result['journal'] = True
        checks = {}
        if active:
            keys = [StreamJournal.source_key(guild, cfg) for cfg in active]
            marks = ','.join('?' for _ in keys)
            checks = {source: (checked, status) for source, checked, status in
                      db.execute(f'SELECT source,checked,status FROM checks WHERE source IN ({marks})', keys)}
        result['never'] = 0
        for cfg in active:
            state = checks.get(StreamJournal.source_key(guild, cfg))
            if not state:
                result['never'] += 1
                continue
            checked, status = state
            result['latest'] = max(result['latest'] or checked, checked)
            interval = 1800 if cfg.get('provider') == 'youtube' else 120
            result['due' if now - checked >= interval else 'current'] += 1
            if str(status).startswith('Fehler:') or 'unbekannt' in str(status).casefold():
                result['errors'] += 1
        rows = db.execute('SELECT state,count(*) FROM deliveries WHERE guild=? GROUP BY state', (guild,)).fetchall()
        counts = dict(rows)
        result['sent'] = counts.get('sent', 0)
        result['unclear'] = counts.get('uncertain', 0) + counts.get('sending', 0)
    return result


def notification(cfg, stream):
    # No role/everyone mentions, embeds or remote title formatting needed.
    label = re.sub(r'[*_`~<>\\\[\]\r\n]', '', str(cfg['name']))[:100]
    return f'{label} ist jetzt live!\n{stream["url"]}'


def send_stream(client, journal, guild, cfg, stream):
    if client.guild != guild or not client.writes:
        raise StreamError('Passenden Discord-Server mit Schreibzugriff verbinden.')
    channel = client.channel(cfg['channel'])
    if channel.get('type') not in (0, 5):
        raise StreamError('Stream-Meldungen benötigen einen Text- oder Ankündigungskanal.')
    key = journal.reserve(guild, cfg, stream)
    if key is None:
        return 'Bereits verarbeitet; keine erneute Meldung.'
    payload = {'content': notification(cfg, stream), 'allowed_mentions': {'parse': []}, 'nonce': key[:24], 'enforce_nonce': True}
    try:
        result = client._change('POST', f'/channels/{cfg["channel"]}/messages', payload, 'Creator Hub: aktivierte Stream-Benachrichtigung', False)
        if result.get('channel_id') != cfg['channel']:
            raise StreamError('Versandantwort passt nicht zum Zielkanal.')
        message = snowflake(result.get('id'))
        journal.finish(key, 'sent', message)
    except Exception:
        # Even if this save fails, the durable 'sending' reservation blocks retries.
        journal.finish(key, 'uncertain')
        raise StreamError('Versand unklar. Nachricht in Discord prüfen; dieser Stream wird nicht erneut gesendet.') from None
    return 'Stream-Meldung gesendet.'

