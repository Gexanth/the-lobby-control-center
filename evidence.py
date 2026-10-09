"""Bounded, privacy-limited evidence shared by the Dashboard and AI context."""
from datetime import datetime, timezone
from community import parse_time
from engagement import activity_quality

QUALITY={'fresh':'Aktuell','stale':'Veraltet','limited':'Begrenzt/unbestätigt',
         'future':'PC-Uhr prüfen','invalid':'Nicht verwendbar','missing':'Keine Daten'}


def activity_evidence(data, now=None):
    now=now or datetime.now(timezone.utc)
    rows=[]
    for channel,sample in sorted(data.get('activity',{}).items()):
        history=data.get('activity_history',{}).get(channel,[])
        points=[]
        for point in history[-12:]:
            quality=activity_quality(point,now)
            messages,people=point.get('messages_24h'),point.get('participants_24h')
            if not (type(messages) is int and type(people) is int and 0<=people<=messages):quality='invalid'
            # Invalid or future values are withheld rather than used as evidence.
            points.append({'checked_at':point.get('checked_at'),'quality':quality,
                           'messages_24h':point.get('messages_24h') if quality in ('fresh','stale','limited') else None,
                           'participants_24h':point.get('participants_24h') if quality in ('fresh','stale','limited') else None,
                           'coverage':point.get('coverage')})
        rows.append({'channel_id':channel,'quality':activity_quality(sample,now),
                     'checked_at':sample.get('checked_at'),'history_points':len(history),
                     'recent_points':points})
    return {'generated_at':now.isoformat(),'channels':rows[:50],
            'limits':'Überlappende 24h-Stichproben je Kanal, maximal 12 Verlaufspunkte je Kanal und 50 Kanäle. Nicht summieren. Keine vollständige Serverstatistik, kein Wachstum und keine Kausalität ableitbar.'}
