"""Compare recorded snapshots without inventing trends or adding windows."""
from datetime import datetime,timezone
from evidence import evidence_point,QUALITY
from community import parse_time,CommunityError


def compare_samples(channel,history,now=None):
    now=now or datetime.now(timezone.utc)
    points=[];seen=set()
    for sample in reversed(history):
        stamp=sample.get('checked_at')
        if stamp in seen:continue
        seen.add(stamp);points.append(evidence_point(channel,sample,now))
        if len(points)==2:break
    if len(points)<2:return 'Messvergleich: Mindestens zwei unterschiedliche Erfassungszeitpunkte dieses Kanals erforderlich.'
    lines=['Zwei zuletzt gespeicherte Messungen · keine Wachstumsstatistik']
    for label,p in zip(('Neuere Erfassung','Vorherige Erfassung'),points):
        try:stamp=parse_time(p['checked_at']).astimezone().strftime('%d.%m.%Y %H:%M %Z')
        except (CommunityError,OverflowError,OSError):stamp='Ungültiger Zeitpunkt'
        counts=f"{p['messages_24h']} Nachrichten / {p['participants_24h']} Personen" if p['messages_24h'] is not None else 'Werte nicht verwendbar'
        lines.append(f"{label}: {stamp} · {counts} · {QUALITY.get(p['quality'],'Unbekannt')}")
    if any(p['quality'] not in ('fresh','stale') for p in points) or points[0]['coverage']!=points[1]['coverage']:
        lines.append('Datenlücke: begrenzte, ungültige oder unterschiedliche Abdeckung. Werte nicht direkt vergleichbar.')
    else:lines.append('Zwei überlappende 24h-Fenster: weder addieren noch als Mitgliederwachstum deuten.')
    return '\n'.join(lines)
