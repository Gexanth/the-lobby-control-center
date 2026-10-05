"""Explainable participation ideas from aggregate activity; no AI/API calls."""
from datetime import timedelta
from community import parse_time,utcnow

COMPLETE={'window_reached','history_end'}
def engagement_ideas(sample,now=None):
    now=now or utcnow()
    reason='Noch keine aktuelle, bestätigte 24h-Erfassung. Die folgenden Texte sind allgemeine Ideen.'
    kind='general'
    if sample:
        try:age=now-parse_time(sample['checked_at'])
        except (ValueError,KeyError):age=None
        messages=sample.get('messages_24h');people=sample.get('participants_24h')
        valid=type(messages) is int and type(people) is int and 0<=people<=messages
        if age is not None and timedelta(0)<=age<=timedelta(hours=6) and valid and sample.get('coverage') in COMPLETE:
            reason=f'Erfasste letzte 24h: {messages} menschliche Nachrichten von {people} Personen im ausgewählten Kanal. Kein Urteil über den gesamten Server.'
            if messages==0:kind='restart'
            elif people<=3:kind='invite'
            else:kind='continue'
        elif age is not None and age>timedelta(hours=6):reason='Die Erfassung ist älter als sechs Stunden. Aktualisiere sie vor einer datenbezogenen Entscheidung.'
        elif sample.get('coverage') not in COMPLETE:reason='Die Abdeckung ist begrenzt oder unbestätigt. Daraus lässt sich keine verlässliche Inaktivität ableiten.'
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
