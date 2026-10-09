"""Prioritized local operational hints; no network calls or state changes."""
from datetime import datetime, timezone
from engagement import activity_quality
from polls import schedule_state


def attention_items(data, streams=None, monitoring=False, now=None):
    now = now or datetime.now(timezone.utc)
    items = []
    def add(key, title, detail, tab):
        items.append({'key': key, 'title': title, 'detail': detail, 'tab': tab})
    states = [schedule_state(n, now) or n.get('poll_delivery', {}).get('state') for n in data.get('nights', [])]
    unclear = states.count('sending') + states.count('uncertain')
    if unclear:
        add('poll_unclear', f'{unclear} Abstimmungsversand unklar', 'Zielkanal und gespeicherten Versandstatus prüfen, bevor du erneut veröffentlichst.', 1)
    if streams is None:
        add('stream_journal', 'Stream-Protokoll nicht lesbar', 'Im Creator Hub prüfen und Überwachung gestoppt lassen.', 2)
    elif streams.get('unclear'):
        add('stream_unclear', f"{streams['unclear']} Stream-Versandversuche unklar", 'Nachrichten in Discord prüfen. Diese Streams werden nicht automatisch erneut gesendet.', 2)
    if states.count('due'):
        add('poll_due', f"{states.count('due')} Abstimmungen fällig", 'Versand benötigt die laufende App, den passenden verbundenen Server und freien Hintergrundbetrieb.', 1)
    stopped = states.count('expired') + states.count('cancelled')
    if stopped:
        add('poll_stopped', f'{stopped} Veröffentlichungspläne gestoppt', 'Termin abgelaufen oder abgesagt. Gespeicherte Planung prüfen.', 1)
    if streams and streams.get('errors'):
        add('stream_errors', f"{streams['errors']} aktive Quellen mit Prüfproblemen", 'Letzten Abruf im Creator Hub prüfen und Ursache beheben.', 2)
    if streams and streams.get('active') and not monitoring:
        add('stream_stopped', 'Stream-Überwachung gestoppt', f"{streams['active']} Quellen sind freigegeben. Zugangsdaten und Verbindung prüfen; Sitzung bewusst starten.", 2)
    qualities = [activity_quality(s, now) for s in data.get('activity', {}).values()]
    unreliable = sum(q != 'fresh' for q in qualities)
    if unreliable:
        add('activity', f'{unreliable} Kanalstichproben prüfen', f"{qualities.count('stale')} veraltet · {qualities.count('limited')} begrenzt/unbestätigt · {sum(q in ('future', 'invalid', 'missing') for q in qualities)} nicht verwendbar. Vor Entscheidungen neu erfassen.", 0)
    applications = sum(c.get('status') == 'Bewerbung' for c in data.get('creators', []))
    if applications:
        add('applications', f'{applications} offene Creator-Bewerbungen', 'Bewerbungen und lokale Notizen im Creator Hub durchsehen.', 2)
    return items
