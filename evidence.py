"""Bounded, privacy-limited evidence shared by the Dashboard and AI context."""
from datetime import datetime, timezone
from hashlib import sha256
from community import parse_time,CommunityError
from engagement import activity_quality

QUALITY={'fresh':'Aktuell','stale':'Veraltet','limited':'Begrenzt/unbestätigt',
         'future':'PC-Uhr prüfen','invalid':'Nicht verwendbar','missing':'Keine Daten'}


def evidence_point(channel, point, now):
    quality=activity_quality(point,now)
    messages,people=point.get('messages_24h'),point.get('participants_24h')
    if not (type(messages) is int and type(people) is int and 0<=people<=messages):quality='invalid'
    identity=f"{channel}|{point.get('checked_at')}|{messages}|{people}|{point.get('coverage')}"
    return {'source_id':'ACT-'+sha256(identity.encode()).hexdigest()[:16],
            'checked_at':point.get('checked_at'),'quality':quality,
            'messages_24h':messages if quality in ('fresh','stale','limited') else None,
            'participants_24h':people if quality in ('fresh','stale','limited') else None,
            'coverage':point.get('coverage')}


def activity_evidence(data, now=None):
    now=now or datetime.now(timezone.utc)
    rows=[]
    for channel,sample in sorted(data.get('activity',{}).items()):
        history=data.get('activity_history',{}).get(channel,[])
        points=[evidence_point(channel,point,now) for point in history[-12:]]
        latest=evidence_point(channel,sample,now)
        rows.append({'channel_id':channel,'quality':latest['quality'],'latest':latest,
                     'checked_at':sample.get('checked_at'),'history_points':len(history),
                     'recent_points':points})
    return {'generated_at':now.isoformat(),'channels':rows[:50],
            'limits':'Überlappende 24h-Stichproben je Kanal, maximal 12 Verlaufspunkte je Kanal und 50 Kanäle. Nicht summieren. Keine vollständige Serverstatistik, kein Wachstum und keine Kausalität ableitbar.'}


def evidence_preview(evidence):
    def timestamp(value):
        try:return parse_time(value).astimezone().strftime('%d.%m.%Y %H:%M %Z')
        except (CommunityError,OverflowError,OSError):return 'Zeitpunkt unbekannt'
    coverage={'window_reached':'24h-Zeitfenster erreicht','history_end':'Kanalhistorie vollständig erreicht','capped':'Abrufgrenze erreicht'}
    lines=['AKTIVITÄT · DATENGRUNDLAGE', 'Vorschau erstellt: '+timestamp(evidence.get('generated_at')),
           'Zeitangaben enthalten die Zeitzone. Quellenkennungen gelten für einzelne Messungen.', '']
    rows=evidence.get('channels',[])
    if not rows:lines.append('Keine Aktivitätsmessungen vorhanden. Unter Aktivität einen Kanal messen.')
    for row in rows:
        lines.append('Kanal '+str(row['channel_id'])+' · '+QUALITY.get(row['quality'],'Unbekannt'))
        points=[row['latest']]+list(reversed(row['recent_points']))
        seen=set()
        for p in points:
            if p['source_id'] in seen:continue
            seen.add(p['source_id'])
            counts=f"{p['messages_24h']} Nachrichten / {p['participants_24h']} Beteiligte" if p['messages_24h'] is not None else 'Messwerte ausgeblendet'
            lines.append(f"[{p['source_id']}] {timestamp(p['checked_at'])} · {QUALITY.get(p['quality'],'Unbekannt')}")
            lines.append(f"{counts} · Abdeckung: {coverage.get(p.get('coverage'),'Begrenzt / unbekannt')}")
        if row['quality']!='fresh':lines.append('Nächster Schritt: Messung aktualisieren bzw. Abdeckung und PC-Uhr prüfen; keine aktuelle Inaktivität daraus ableiten.')
        lines.append('')
    lines.append(evidence.get('limits',''))
    lines.append('Zusätzlich erhält die KI die Serverstruktur, bis zu 10 geplante Lobby Nights (Titel, Termin, Optionen, Status) und Creator-Statussummen. Keine Nachrichtentexte oder Creator-Notizen. Beim Start wird der Kontext neu erstellt.')
    return '\n'.join(lines)
