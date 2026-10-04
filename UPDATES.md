# Updates ab Version 0.1.5

## Einmalige Umstellung

Diese ZIP einmal vollständig entpacken und start.bat öffnen. Diesen Ordner
als festen Startordner behalten. Der Starter legt die Programmversionen
unter %USERPROFILE%\.the_lobby_control_center\releases ab. Dort liegen
Aufgaben und Update-Einstellungen getrennt von den Programmversionen.

## Update-ZIP ohne Hosting übernehmen

Neue Projekt-ZIP herunterladen. In der laufenden App unter Updates auf
„Heruntergeladene Update-ZIP auswählen“ klicken. Danach App schließen
und start.bat aus dem festen Startordner öffnen. Kein manuelles Kopieren
oder Ersetzen einzelner Programmdateien erforderlich. Nur neuere Pakete
ab Version 0.1.5 mit vollständiger Update-Struktur werden unterstützt.

## Automatische Downloads

Ab 0.1.6 ist die offizielle GitHub-Releasequelle für neue Installationen vorkonfiguriert und aktiviert. Bestehende Einstellungen bleiben erhalten. Quelle: https://github.com/Gexanth/the-lobby-control-center/releases/latest/download/release.json . Zum Aktivieren benötigt der
Betreiber eine feste HTTPS-Adresse einer release.json sowie eine HTTPS-
Downloadadresse pro veröffentlichtem ZIP. Die URLs müssen ohne interaktive
Anmeldung erreichbar sein. Keine Tokens in die URL schreiben.
Unter Updates die release.json-Adresse eintragen, automatisches Prüfen
aktivieren und speichern. Prüfung beim App-Start und alle sechs Stunden,
sofern die App läuft und kein anderer Vorgang aktiv ist. Downloads erfolgen
im Hintergrund; die Installation erfolgt erst beim nächsten start.bat-Start.
Ist die App geschlossen, läuft keine Prüfung.

Die Datei enthält: format=lobby-source-v1, launcher_version=1,
version als x.y.z, url als HTTPS-ZIP-Adresse und sha256 als Prüfsumme.
Mit build_update.py --url HTTPS-ZIP-ADRESSE kann der Betreiber Paket und
release.json erzeugen. Zuerst ZIP hochladen, anschließend release.json
veröffentlichen. Das Skript lädt selbst nichts hoch. Den Server nur für
getestete und freigegebene Versionen verwenden.

Die Quelle ist eine Vertrauensentscheidung: HTTPS und SHA-256 schützen
Übertragung und Übereinstimmung von Manifest/Paket. Es gibt noch keine
separate digitale Herausgebersignatur. Wer die Quelle kontrolliert, kann
Programmcode verteilen. Keine fremden Update-Adressen übernehmen.

## Wiederherstellung

Der Starter wartet bis zu 45 Sekunden auf die Startbestätigung der App.
Scheitert ein neu aktiviertes Update vorher, startet er einmal die vorherige
Version. Diese fehlgeschlagene Release-Version wird nicht automatisch
erneut heruntergeladen. Bei später auftretenden Problemen: App schließen,
restore_previous.bat öffnen. Es wird eine Vorgängerversion aufbewahrt.
Aufgabendaten werden dabei nicht zurückgesetzt. Für zukünftige Änderungen
am Datenformat sind rückwärtskompatible Migrationen erforderlich.

## Grenzen

Updates gelten aktuell für die Python-/start.bat-Ausgabe. Selbstgebaute
EXE-Dateien unterstützen diesen Updateweg nicht. Neue Python-Abhängigkeiten
oder Änderungen am Starter-Protokoll erfordern eine manuelle vollständige
Installation. Updates werden nach einem Download nie während einer
laufenden Sitzung ausgetauscht. Entwicklung und Veröffentlichung neuer
Versionen erfolgen weiterhin separat vom Herunterladen und Installieren.
