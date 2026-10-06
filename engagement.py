"""Explainable participation ideas from aggregate activity; no AI/API calls."""
from datetime import timedelta
from community import parse_time,utcnow

COMPLETE={'window_reached','history_end'}
def activity_quality(sample,now=None):
    """Classify a stored snapshot without reading Discord or mutating local data."""
    if not sample:return 'missing'
    try:age=(now or utcnow())-parse_time(sample['checked_at'])
    except (ValueError,KeyError,TypeError):return 'invalid'
    if age<timedelta(0):return 'future'
    if age>timedelta(hours=6):return 'stale'
    messages=sample.get('messages_24h');people=sample.get('participants_24h')
    if not (type(messages) is int and type(people) is int and 0<=people<=messages):return 'invalid'
    if sample.get('coverage') not in COMPLETE:return 'limited'
    return 'fresh'

def engagement_ideas(sample,now=None):
    now=now or utcnow()
    reason='Noch keine aktuelle, bestätigte 24h-Erfassung. Die folgenden Texte sind allgemeine Ideen.'
    kind='general'
    if sample:
        quality=activity_quality(sample,now)
        messages=sample.get('messages_24h');people=sample.get('participants_24h')
        if quality=='fresh':
            reason=f'24h vor der Erfassung: {messages} menschliche Nachrichten von {people} Personen im ausgewählten Kanal. Kein Urteil über den gesamten Server.'
            if messages==0:kind='restart'
            elif people<=3:kind='invite'
            else:kind='continue'
        elif quality=='stale':reason='Die Erfassung ist älter als sechs Stunden. Aktualisiere sie vor einer datenbezogenen Entscheidung.'
        elif quality=='future':reason='Der Erfassungszeitpunkt liegt in der Zukunft. PC-Uhr prüfen und neu erfassen; nur allgemeine Ideen.'
        elif quality=='invalid':reason='Die gespeicherten 24h-Werte oder ihr Zeitpunkt sind nicht verwendbar. Neu erfassen; nur allgemeine Ideen.'
        elif quality=='limited':reason='Die Abdeckung ist begrenzt oder unbestätigt. Daraus lässt sich keine verlässliche Inaktivität ableiten.'
    first={
        'general':('Eine leichte Einstiegsfrage','Allgemeine Idee ohne Aktivitätsbehauptung.','Was zockt ihr gerade – und welches Spiel würdet ihr gern mal gemeinsam ausprobieren? 🎮'),
        'restart':('Ein Gespräch neu anstoßen','In der bestätigten Erfassung wurden keine menschlichen Nachrichten gefunden. Eine offene Frage kann den Einstieg erleichtern.','Was war euer Gaming-Highlight diese Woche? Ein Clip, ein Sieg oder einfach eine lustige Runde? 🎮'),
        'invite':('Weitere Leute ins Gespräch holen','Bis zu drei Personen in der Erfassung: als einfache Heuristik eine Frage wählen, bei der weitere Mitglieder leicht antworten können.','Wer hätte Lust auf eine gemeinsame Runde? Schreibt euer Spiel und wann ihr ungefähr Zeit habt – dann finden sich vielleicht Mitspieler. 🎮'),
        'continue':('Das Gespräch weiterführen','Mehr als drei Personen in der Erfassung: als einfache Heuristik ein gemeinsames Thema aufnehmen.','Was wäre eure perfekte gemeinsame Gaming-Runde: entspannt quatschen, zusammen bauen oder kompetitiv spielen? 🎮')
    }[kind]
    rows=[{'key':'activity','title':first[0],'why':first[1],'draft':first[2]},
          {'key':'lobby','title':'Vorschläge für Lobby Night sammeln','why':'Vorbereitung einer Abstimmung; daraus entsteht noch kein zugesagtes Event.','draft':'Welche Spiele wünscht ihr euch für eine Lobby Night? Schreibt gern auch dazu, welcher Wochentag und welche Uhrzeit euch passen. Eigene Vorschläge sind willkommen!'},
          {'key':'creator','title':'Creator kennenlernen','why':'Offene Frage für den Creator Hub; keine Zusage von Rollen oder Reichweite.','draft':'Streamt jemand von euch oder erstellt Gaming-Videos? Erzählt gern, was ihr macht und welche Inhalte euch interessieren. 🎥'}]
    return {'basis':reason,'kind':kind,'ideas':rows,'limits':'Regelbasierte Vorschläge, keine KI-Analyse. Nicht automatisch veröffentlichen und nicht alle Impulse auf einmal senden.'}
