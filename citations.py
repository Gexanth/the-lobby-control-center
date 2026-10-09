"""Local lookup of AI activity references; never a factual-accuracy verdict."""
import re
from evidence import QUALITY


def source_index(context):
    evidence=(context or {}).get('community',{}).get('activity_evidence',{})
    sources={}
    for row in evidence.get('channels',[])[:50]:
        for point in [row.get('latest',{})]+row.get('recent_points',[])[-12:]:
            key=point.get('source_id')
            if key:
                sources[key]={'channel_id':row.get('channel_id'),**{k:point.get(k) for k in
                    ('checked_at','quality','messages_24h','participants_24h','coverage')}}
    return sources


def reference_report(text,sources):
    refs=list(dict.fromkeys(re.findall(r'\[\s*(ACT-[^\]\s]{1,100})\s*\]',text)))
    if not refs:return 'Keine ACT-Quellenangabe im ausgewählten Text. Aussagen sind nicht automatisch geprüft.'
    lines=[]
    for key in refs[:10]:
        p=sources.get(key)
        if p is None:lines.append(f'[{key}] Unbekannte Quelle: nicht im Kontext dieser Antwort enthalten.');continue
        lines.append(f"[{key}] Kanal {p['channel_id']} · {p['checked_at']} · {QUALITY.get(p['quality'],'Unbekannt')}")
        if p['quality'] in ('fresh','stale','limited'):
            lines.append(f"24h-Stichprobe: {p['messages_24h']} Nachrichten / {p['participants_24h']} Beteiligte · Abdeckung: {p['coverage']}")
        else:lines.append('Messwerte nicht verwendbar.')
    if len(refs)>10:lines.append(f'{len(refs)-10} weitere Quellenangaben hier nicht aufgeführt.')
    lines.append('Nur Quellenzuordnung geprüft; Aussage, Aktualität und Empfehlung selbst prüfen. Überlappende Stichproben nicht summieren.')
    return '\n'.join(lines)
