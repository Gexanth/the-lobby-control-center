THE LOBBY CONTROL CENTER — Version 0.1.5

NEU: UPDATES
Unter Updates neue ZIP-Pakete übernehmen oder eine feste HTTPS-Quelle
einrichten. Details in UPDATES.md. Diese Version einmal neu entpacken
und danach immer den mitgelieferten start.bat-Starter verwenden.
Die automatische Quelle ist noch nicht eingerichtet.

UPDATE UND START
Alte App schließen, dieses ZIP vollständig entpacken, start.bat öffnen.
Python 3.11+ und Internet für die erste Paketinstallation werden benötigt.
Gespeicherte Aufgaben bleiben unter
%USERPROFILE%\.the_lobby_control_center\tasks.json erhalten.

DISCORD
Unter Discord Bot-Token und Server-ID eingeben und Verbindung prüfen.
Server-ID: Discord-Entwicklermodus aktivieren, Rechtsklick auf den Server,
Server-ID kopieren. Alternativ DISCORD_BOT_TOKEN / DISCORD_GUILD_ID in
der Umgebung setzen. Das Token nicht in ChatGPT hochladen.
Der Bot muss Mitglied des Servers sein und Kanäle verwalten dürfen.
Das Token bleibt während der Verbindung im Arbeitsspeicher und wird nicht
auf Festplatte gespeichert. Verbindung trennen oder App schließen leert
es aus der App-Sitzung. Während laufender Abrufe bitte kurz abwarten.
Mit dem Verbindungsbutton kannst du dieselbe Sitzung aktualisieren.

KANÄLE VERWALTEN
1. Nach dem Verbinden den Tab „Kanäle verwalten“ öffnen.
2. Erstellen, Umbenennen oder Verschieben auswählen.
3. Name bzw. vorhandenen Kanal und Zielkategorie auswählen.
   Neue Kanäle: Text, Sprache oder Kategorie.
   „Ohne Kategorie“ verschiebt einen Kanal aus seiner Kategorie.
4. Einen Grund für das Discord-Protokoll eingeben.
5. Änderung prüfen klicken, Vorschau lesen, „Jetzt ausführen“ klicken.
   Abbrechen sendet keine Schreibaktion.
6. Das Ergebnis wird angezeigt; die Übersicht wird anschließend aktualisiert.
   Wird die Aktualisierung nach einer bestätigten Änderung abgelehnt,
   wurde die Änderung trotzdem ausgeführt; später die Übersicht neu laden.
Bei Verbindungsfehlern während einer Schreibaktion kann das Ergebnis
ungewiss sein. Vor erneuter Ausführung den Server prüfen. Keine
automatischen Wiederholungen. Änderungen seit der Vorschau werden erkannt.
Die App sendet bei Verschiebungen nur die neue Kategorie-ID und fordert
keine zusätzliche Synchronisierung der Kanalberechtigungen an.

KI-ASSISTENT EINRICHTEN
1. Einen OpenAI-API-Schlüssel unter https://platform.openai.com/api-keys
   erstellen und ausschließlich in der App unter Einstellungen eingeben.
2. Voreingestelltes Modell: gpt-4.1-mini. Es lässt sich ändern, muss aber
   Responses API und strukturierte Ausgaben unterstützen.
3. Für Kanalaufträge zuerst Discord verbinden und Übersicht laden.
4. Unter Assistent einen Auftrag eingeben und „An KI senden“ anklicken.
5. Bei einer vorgeschlagenen Aktion „Vorgeschlagene Aktion prüfen“ anklicken.
   Die App zeigt die konkrete Vorschau. Erst „Jetzt ausführen“ sendet
   die Änderung an Discord.
Beispiel: Erstelle einen Textkanal namens test in der Kategorie EVENTS.
Fragen und Ideen werden als Text beantwortet. Bei unklaren Kanalnamen
soll die KI nachfragen. Aktuell genau eine Kanalaktion pro Auftrag.
Löschen, Rollen, Nachrichten, Abstimmungen und Automationen sind noch
nicht an die KI angebunden. Bestehende Kanalaktionen bleiben verfügbar.

API-NUTZUNG UND DATEN
OpenAI-API-Nutzung kann separat berechnete Kosten verursachen.
Der API-Schlüssel bleibt nur in der Sitzung; alternativ wird OPENAI_API_KEY
beim Start aus der Umgebung gelesen. Über Einstellungen lässt er sich
entfernen. Keine Speicherung von Schlüsseln auf Festplatte durch die App.
An OpenAI gehen Auftrag, maximal acht bisherige Gesprächsbeiträge und
Servername/-ID sowie Kanalnamen, Kanaltypen und Kategoriezuordnung mit IDs.
Keine Discord-Tokens, Rollenlisten, Mitglieder oder Discord-Nachrichten.
Die App fordert mit store=false keine Speicherung des Responses-Objekts an;
dies ist keine Zusicherung vollständiger Datenlöschung beim Anbieter.
Der App-Chat bleibt nur in der Sitzung und übernimmt nicht diesen ChatGPT-Chat.
„Gespräch leeren“ entfernt den lokalen Verlauf und den Aktionsvorschlag.
„Nur als Aufgabe speichern“ speichert den Eingabetext lokal ohne KI-Anfrage.
Die KI führt weder Code noch beliebige HTTP-Anfragen aus. Vorschläge werden
lokal auf erlaubte Aktionen und vorhandene Kanal-/Kategorie-IDs geprüft.
Keine automatischen Wiederholungen nach API-Fehlern.

PROTOKOLL
%USERPROFILE%\.the_lobby_control_center\discord.sqlite3
Enthält Zeit, HTTP-Methode und API-Pfad der ausgeführten Änderungen,
keine Tokens oder Nachrichteninhalte.

EXE BAUEN
Auf Windows build_exe.bat öffnen.
Ergebnis: dist\The Lobby Control Center.exe
Dieses ZIP enthält Quellcode, keine vorgebaute Windows-EXE.

VALIDIERUNG
Simulierte Discord-Antworten: Vorschau ohne Schreiben, Erstellen,
Umbenennen, Verschieben, Kategorie entfernen, Ablehnung falscher
Server/Zielkategorien, Änderungen seit Vorschau, Schreibsperre sowie
asynchrone Oberfläche und Fehleranzeige geprüft. Zusätzlich strukturierte
KI-Antworten, ungültige IDs, Ablehnungen, unvollständige Antworten, API-Fehler,
Datenfilterung und Übergabe vom Chat an die Kanalvorschau geprüft. Der echte KI-Aufruf benötigt deinen API-Schlüssel und wurde hier nicht
ausgeführt. Windows-EXE-Bau muss auf dem Ziel-PC geprüft werden.

API-Referenz: https://docs.discord.com/developers/resources/channel

OpenAI-Dokumentation: https://developers.openai.com/api/docs/guides/structured-outputs
API-Preise: https://developers.openai.com/api/docs/pricing
