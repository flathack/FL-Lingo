# FL Lingo Project Plan

Stand: 2026-03-10

## 1. Produktziel

FL Lingo ist ein Desktop-Werkzeug fuer Freelancer-Mod-ReLocalization. Das Programm soll einen modifizierten Spielstand mit einer sauberen Referenzinstallation vergleichen, sichere Uebersetzungen automatisch wiederherstellen, offene Mod-Texte fuer externe oder manuelle Uebersetzung aufbereiten und die fertigen Texte sicher in die Ressourcen-DLLs zurueckschreiben.

## 2. Kernanforderungen

### A. Installationen und Daten

- Freelancer-Installationen laden und die relevanten DLLs ueber `freelancer.ini` erkennen.
- `RT_STRING` und `RT_HTML`/Infocard-Ressourcen lesen.
- Quelle und Referenz per DLL-Name, Ressourcentyp und lokaler ID paaren.
- Unterschiede und Status pro Eintrag nachvollziehbar darstellen.

### B. Uebersetzungsworkflow

- automatisch uebernehmbare Referenztexte erkennen
- bereits lokalisierte Eintraege erkennen
- mod-only Eintraege fuer manuelle oder externe Bearbeitung markieren
- Export und Import fuer externe Uebersetzung anbieten
- manuelle Bearbeitung einzelner Eintraege erlauben
- Terminologie- und Pattern-Regeln fuer Vorschlaege verwenden

### C. Sichere Rueckschreibung

- vor jedem Apply automatisch Backups erstellen
- DLL-Strategie pro Datei bestimmen: komplett ersetzen, patchen, blockieren
- Apply-Lauf mit Fortschritt und Wiederaufnahme absichern
- Backups aus der App heraus wiederherstellen koennen

### D. Bedienung

- einfacher gefuehrter Modus fuer Standardnutzer
- Expertenmodus fuer Analyse, Filter, manuelle Nacharbeit und Terminologiepflege
- klare Statusfarben und Fortschrittsdarstellung
- mehrsprachige UI und Hilfe

### E. Plattform und Distribution

- Windows und Linux unterstuetzen
- aus Source startbar sein
- Windows-Build fuer Release bereitstellen
- saubere Abhaengigkeiten und reproduzierbarer Setup

### F. Qualitaet

- automatisierte Tests fuer Kernlogik
- stabile Projektdateien (`.FLLingo`)
- konsistente Dokumentation fuer Workflow und Grenzen

## 3. Nicht-Ziele

- freie Volltext-Maschinenuebersetzung im Tool
- semantische Neuinterpretation falsch gemoddeter Resource-IDs
- vollautomatische inhaltliche Qualitaetssicherung aller externen Uebersetzungen

## 4. Projektphasen

### Phase 1. Kernfunktion stabilisieren

- Katalogaufbau, Matching, Statusmodell, Export/Import, Projektdateien
- Linux- und Windows-Schreibpfad robust machen
- Backup- und Restore-Pfad absichern

### Phase 2. Workflow fuer Anwender schaerfen

- Simple Mode fuer Standardfaelle
- Expertenmodus strukturieren
- Hilfetexte, Tooltips und Statusmeldungen vereinheitlichen
- Default-Filter und Fortschrittsanzeigen auf reale Arbeitsablaeufe ausrichten

### Phase 3. Datenqualitaet und Sprachpflege

- Terminologie-Dateien pro Sprache erweitern
- UI-Uebersetzungen konsistent pflegen
- Help-Dateien und README synchron halten

### Phase 4. Produktreife

- reale Mod-Validierung mit grossen Installationen
- Release-Checkliste und Packaging haerten
- Smoke-Tests fuer GUI und Sprachdateien ergaenzen

## 5. Soll-/Ist-Abgleich

| Bereich | Soll | Ist | Bewertung |
|---|---|---|---|
| Install laden und vergleichen | stabil und alltagstauglich | vorhanden, testabgedeckt, GUI und CLI vorhanden | gut |
| String- und Infocard-Unterstuetzung | beide Ressourcentypen | vorhanden | gut |
| Statusmodell | auto / lokalisiert / manuell / mod-only | vorhanden | gut |
| Export / Import | offener Inhalt und Rueckimport | vorhanden | gut |
| Manuelle Bearbeitung | Editor mit Speichern / Reset | vorhanden | gut |
| Terminologie / Pattern | sprachabhaengige Vorschlaege | vorhanden, aber Sprachabdeckung begrenzt | teilweise |
| DLL-Analyse | sichere Strategie je DLL | vorhanden | gut |
| Backup / Restore | Backup vor Apply und Restore in App | vorhanden | gut |
| Apply-Resume | unterbrochene Laeufe fortsetzen | vorhanden | gut |
| Simple Mode | schneller 3-Spalten-Workflow | vorhanden, funktional schon deutlich verbessert | teilweise |
| Expertenmodus | tiefe Analyse und Nacharbeit | vorhanden | gut |
| Linux-Support | gleicher Kernworkflow wie Windows | grossenteils vorhanden; realer Feldtest weiter noetig | teilweise |
| UI-Lokalisierung | konsistent ueber alle Quellen | eingebaute Basistexte jetzt zentral in `ui_strings.py`; externe JSON-Dateien sind partielle Overrides, muessen aber weiter validiert werden | teilweise |
| Hilfe / README | aktuelle Produktlage spiegeln | teilweise veraltet und nicht mehr voll synchron | schwach |
| CLI | sinnvolle technische Nebenoberflaeche | nur fuer Inspektion, kein voller Workflow | teilweise |
| Testqualitaet | Kernlogik breit abdecken | 12 Testdateien, Kernlogik gut abgedeckt, GUI kaum | teilweise |
| Architektur | wartbare Modulgroessen | UI inzwischen in `ui_app.py`, `ui_builders.py`, `ui_state.py`, `ui_editor.py`, `ui_workflows.py`, `ui_session.py`, `ui_chrome.py`, `ui_strings.py` getrennt; Main-Window-Datei nur noch 184 Zeilen | gut |

## 6. Wichtigste Luecken

### 1. Dokumentation ist nicht mehr voll aktuell

- [`readme.md`](/home/steven/FL-Lingo/readme.md) und die Hilfe-Dateien muessen auf den heutigen Linux-Stand und den aktuellen Simple-/Expert-Mode gebracht werden.
- [`data/help/help.de.html`](/home/steven/FL-Lingo/data/help/help.de.html) enthaelt noch viele ASCII-Umschriften statt echter Umlaute.
- README, Hilfe und aktuelles UI laufen sprachlich und funktional auseinander.

### 2. Sprachdatei-Strategie ist noch nicht ganz abgeschlossen

- Externe UI-Sprachdateien koennen eingebettete Fallback-Texte still ueberschreiben.
- Das hat bereits konkret zu Inkonsistenzen bei deutschen Umlauten gefuehrt.
- Die Lage ist besser als zuvor: Basistexte sind jetzt zentral in [`ui_strings.py`](/home/steven/FL-Lingo/src/flatlas_translator/ui_strings.py), und die JSON-Dateien werden als partielle Overrides behandelt.
- Es fehlt aber weiter ein klar dokumentierter Pflegeprozess pro Sprache.

### 3. GUI-Testabdeckung fehlt fast komplett

- Die Kernlogik ist ordentlich getestet.
- Simple Mode, Expert-Mode-Navigation, Default-Filter, Sprachwechsel und Progress-Darstellung haben keine echte GUI-Sicherheitsleine.
- Das macht UI-Refactorings riskant.

### 4. Produktfuehrung fuer Erstnutzer ist noch nicht ganz fertig

- Der Simple Mode ist deutlich besser als vorher, aber noch kein vollständig gefuehrter Wizard.
- Begriffe wie Referenz, mod-only, DLL-Strategie und Terminologie setzen noch Vorwissen voraus.
- Hilfe, Tooltips und Statusmeldungen koennen weiter auf Standardanwender zugeschnitten werden.

## 7. Empfohlene Prioritaeten

### Prioritaet 1. Doku- und Sprachhygiene

- `Languages/` als partielle Override-Dateien dokumentieren und weiter pruefen
- deutsche Hilfe-Datei auf echte Umlaute und aktuelle Begriffe bringen
- README an den realen Linux-Stand und die aktuelle UI-Struktur anpassen

### Prioritaet 2. GUI-Sicherheit erhoehen

- Smoke-Tests fuer Start, Moduswechsel und Sprachwechsel
- Tests fuer Default-Filter im Untertab
- Tests fuer Progress-Anzeige und Apply-Button-Enablement

### Prioritaet 3. Produktpolish

- Simple Mode weiter auf Erstnutzer trimmen
- besseres Empty-State- und Fehlerdesign
- Abschlussbericht nach Apply mit klarerem Ergebnisbild

### Prioritaet 4. Weitere Architekturpflege nur gezielt

- die neue Modulstruktur stabil halten statt weiter kleinteilig zu zerschneiden
- nur noch bei echtem Wartungsgewinn weitere Presenter/Controller extrahieren
- eher Schnittstellen und Tests schaerfen als weitere Dateiaufspaltung erzwingen

## 8. Konkreter Arbeitsplan

### Sprint 1. Struktur und Hygiene

- Architekturstand konsolidieren und neue Modulgrenzen dokumentieren
- Sprachdateien als Override-Schicht validieren und Pflegeprozess festhalten
- README und Hilfe synchronisieren

### Sprint 2. GUI-Qualitaet

- GUI-Smoke-Tests aufbauen
- Default-Filter, Moduswechsel und Progress visual regressions absichern
- Simple Mode weiter vereinfachen

### Sprint 3. Reale Mod-Validierung

- Testmatrix fuer 2 bis 3 grosse Mods
- Dokumentierte Edge Cases fuer DLL-Write, Infocards und Terminologie sammeln
- Konflikterkennung fuer problematische DLLs schaerfen

### Sprint 4. Release-Vorbereitung

- saubere externe Sprachdateien fuer alle Sprachen
- Packaging-Check fuer Windows und Linux
- Release-Checkliste und Support-Dokumentation

## 9. Fazit

FL Lingo ist bereits ein funktionales Arbeitswerkzeug mit starker Kernlogik und inzwischen deutlich besserer UI-Architektur. Die groessten naechsten Schritte liegen jetzt weniger in weiterer Zerlegung des Codes als in Sprach-/Doku-Konsistenz, GUI-Testbarkeit und Produktreife fuer Erstnutzer.
