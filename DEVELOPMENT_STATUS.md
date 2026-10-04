# Stand 0.1.5

- Windows-Desktop-App mit lokaler Aufgabenverwaltung.
- Discord-Übersicht und Formularaktionen: Erstellen, Umbenennen, Verschieben.
- KI-Planung per OpenAI Responses API; Einzelaktionen mit Vorschau.
- Quellcode-Updates per ZIP-Import oder konfigurierbarer HTTPS-Quelle.
- Stabiler Starter, getrennte Release-Ordner, Rücksetzung bei Startfehler,
  manuelle Wiederherstellung, Prüfung von ZIP-Pfaden und SHA-256.

## Noch offen

- Feste HTTPS-Downloadquelle einrichten und echten Windows-Updateablauf testen.
- Tägliche Entwicklungsaufgabe noch nicht aktiv: fünf Aufgabenplätze belegt.
- API-Aufrufe beim Nutzer liefern 429; Ursache im Code noch genauer unterscheiden.
- Löschen, Rollen, Berechtigungen, Nachrichten, Abstimmungen, mehrere KI-Aktionen.
- EXE-Installer/Updates und signierte Releases.

## Validierung

Update-Tests mit künstlichen Paketen: gültiges Manifest, Prüfsummenfehler,
Pfadtraversal, geänderte Abhängigkeiten, Versionsprüfung, Datenbestand,
Startfehler mit Rücksetzung und Einzelinstanz-Sperre. Keine echte
Veröffentlichung und kein Windows-Systemtest in dieser Umgebung.

## Für weitere Versionen

VERSION in version.py erhöhen. Update-Paketstruktur und Starter-Protokoll 1
beibehalten. Vorherige Aufgaben und Einstellungen erhalten. Bei Änderungen
an requirements.txt fordert der Updater eine manuelle Installation.
