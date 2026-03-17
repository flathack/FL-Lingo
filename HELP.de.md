# FL Lingo — Hilfe

**Version:** 0.1.1  
**Entwickelt von:** Aldenmar Odin — flathack  
**GitHub:** [github.com/flathack/FL-Lingo](https://github.com/flathack/FL-Lingo)  
**Discord:** [discord.com/invite/RENtMMcc](https://discord.com/invite/RENtMMcc)

---

## Inhaltsverzeichnis

1. [Was ist FL Lingo?](#1-was-ist-fl-lingo)
2. [Installation und Start](#2-installation-und-start)
3. [Die zwei Modi](#3-die-zwei-modi)
4. [Simple Mode — Schnellanleitung](#4-simple-mode--schnellanleitung)
5. [Expert Mode — Überblick](#5-expert-mode--überblick)
   - [Vorbereitung](#51-vorbereitung)
   - [Scan](#52-scan)
   - [Bearbeitung](#53-bearbeitung)
   - [Zusatz (Import / Export / Auto-Übersetzen)](#54-zusatz-import--export--auto-übersetzen)
   - [Übersetzen (Anwenden)](#55-übersetzen-anwenden)
6. [Der Editor-Arbeitsbereich](#6-der-editor-arbeitsbereich)
   - [Filter](#61-filter)
   - [Quell- und Zieltextvorschau](#62-quell--und-zieltextvorschau)
   - [Manuelle Bearbeitung](#63-manuelle-bearbeitung)
7. [DLL-Analyse](#7-dll-analyse)
8. [Terminologie und Pattern](#8-terminologie-und-pattern)
9. [Mod Overrides](#9-mod-overrides)
10. [Export und Import für externe Übersetzung](#10-export-und-import-für-externe-übersetzung)
11. [Automatische Übersetzung (Bulk Translate)](#11-automatische-übersetzung-bulk-translate)
12. [Projektdateien (.FLLingo)](#12-projektdateien-fllingo)
13. [Backups und Wiederherstellung](#13-backups-und-wiederherstellung)
14. [Updates](#14-updates)
15. [Menüleiste](#15-menüleiste)
16. [Statuswerte und Fortschritt](#16-statuswerte-und-fortschritt)
17. [Einstellungen](#17-einstellungen)
18. [Sprachen und Themes](#18-sprachen-und-themes)
19. [Sicherheitshinweise](#19-sicherheitshinweise)
20. [Häufige Fragen (FAQ)](#20-häufige-fragen-faq)
21. [Fehlerbehebung](#21-fehlerbehebung)
22. [Technische Details](#22-technische-details)

---

## 1. Was ist FL Lingo?

FL Lingo ist ein Relocalization-Tool für Freelancer-Mods. Viele Freelancer-Mods liefern nur englischsprachige Texte mit — FL Lingo hilft dabei, die mod-spezifischen Inhalte in andere Sprachen zu übersetzen, typischerweise Deutsch.

**Die drei Kernaufgaben:**

1. **Referenztexte finden:** FL Lingo vergleicht die Mod-Installation mit einer sauberen Referenzinstallation und erkennt automatisch, welche Mod-Texte bekannten Referenztexten entsprechen und wiederverwendet werden können.
2. **Mod-spezifische Texte identifizieren:** Neue Texte, die nur in der Mod existieren, werden als „offen" markiert und können extern oder manuell übersetzt werden.
3. **Zurückschreiben:** FL Lingo schreibt die fertigen Übersetzungen sicher in die Ressourcen-DLLs der Mod-Installation zurück — mit automatischem Backup.

**Unterstützte Ressourcentypen:**

- String-Tabellen (`RT_STRING`) aus Ressourcen-DLLs
- Infocards / HTML-Ressourcen (`RT_HTML`) aus Ressourcen-DLLs
- DLL-Referenzen werden über `EXE\freelancer.ini` erkannt

**Typisch betroffene Dateien:**

- `InfoCards.dll`, `MiscText.dll`, `MiscTextInfo2.dll`
- `NameResources.dll`, `EquipResources.dll`
- `OfferBribeResources.dll` und weitere

---

## 2. Installation und Start

### Option A: Windows-Executable (empfohlen)

Lade das aktuelle Release von [GitHub Releases](https://github.com/flathack/FL-Lingo/releases) herunter und starte `FL-Lingo.exe`.

### Option B: Aus dem Quellcode

**Voraussetzungen:** Python 3.11+

```bash
# Virtuelle Umgebung erstellen
python -m venv .venv

# Aktivieren (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Aktivieren (Linux/macOS)
source .venv/bin/activate

# Installieren
python -m pip install -U pip
python -m pip install -e .[all]

# Starten
python launch.py
```

### Projektdatei direkt öffnen

```bash
python launch.py pfad/zum/projekt.FLLingo
```

---

## 3. Die zwei Modi

FL Lingo bietet zwei Benutzeroberflächen, die oben in der Leiste umgeschaltet werden können:

| Modus | Beschreibung |
|-------|-------------|
| **Simple Mode** | Geführter Drei-Spalten-Ablauf: Ordner wählen → Scannen → Übersetzen. Ideal für den Standardfall. |
| **Expert Mode** | Voller Zugriff auf Editor, Filter, DLL-Analyse, Terminologie, Import/Export und Projektverwaltung. |

---

## 4. Simple Mode — Schnellanleitung

Der Simple Mode führt dich in drei Spalten durch den gesamten Vorgang:

### Spalte 1: Ordnerwahl

| Feld | Beschreibung |
|------|-------------|
| **Mod-Installation** | Der Freelancer-Ordner mit der installierten Mod (meistens englisch). |
| **Freelancer-Installation** | Eine saubere Referenzinstallation in der Zielsprache (z.B. Deutsch). |
| **Englische Vanilla-Installation** *(optional)* | Eine englische Original-Installation — wird für den Funkspruch-Merge (UTF-Voicefiles) benötigt. |

### Spalte 2: Scan

Klicke **„Scan starten"**, um beide Installationen zu laden und zu vergleichen. Danach siehst du:

- Ein Kreisdiagramm mit dem Übersetzungsfortschritt
- Audio-Fortschritt (welche deutschen Voice-Dateien schon vorhanden sind)
- Voiceline-Fortschritt (UTF-Funksprüche)
- Eine Zusammenfassung mit Einträgen, automatischen Matches und offenen Texten

### Spalte 3: Übersetzen

Nach dem Scan kannst du:

- **Übersetzung anwenden:** Schreibt alle verfügbaren Übersetzungen in die Mod-Installation.
- **Audio auch kopieren:** Kopiert zusätzlich deutsche Voice-Dateien aus der Referenz (Checkbox).

---

## 5. Expert Mode — Überblick

Der Expert Mode zeigt auf der Startseite fünf aufeinanderfolgende Abschnitte:

### 5.1 Vorbereitung

| Element | Beschreibung |
|---------|-------------|
| **Spiel mit Mod / aktuelles Spiel** | Pfad zur Mod-Installation. |
| **Referenzinstallation / Vergleichsspiel** | Pfad zur sauberen Referenzinstallation. |
| **Englische Vanilla-Installation** *(optional)* | Pfad für Voice-Merge. |
| **Quellsprache / Zielsprache** | Sprachpaar einstellen (z.B. en → de). |
| **Toolchain installieren** | Installiert die LLVM-Resource-Tools, die zum Patchen der DLLs benötigt werden. |

### 5.2 Scan

| Element | Beschreibung |
|---------|-------------|
| **Scan starten** | Lädt die Mod-Installation und vergleicht sie automatisch mit der Referenz. |
| **Infocards einbeziehen** | Wenn aktiv, werden auch mehrzeilige Infocards in den Scan einbezogen. |

Nach dem Scan erscheint eine Zusammenfassung: Gesamteinträge, automatische Matches, manuelle Übersetzungen, offene Einträge und betroffene DLLs.

### 5.3 Bearbeitung

Dieser Abschnitt wird erst nach einem erfolgreichen Scan sichtbar. Er enthält einen Link zum **Editor-Arbeitsbereich** (Tab „Offene Übersetzungen"), in dem einzelne Einträge manuell bearbeitet werden können.

### 5.4 Zusatz (Import / Export / Auto-Übersetzen)

| Button | Beschreibung |
|--------|-------------|
| **Offene Einträge exportieren** | Exportiert alle offenen Einträge als JSON für externe Übersetzung. |
| **Lange offene Texte exportieren** | Exportiert nur lange offene Texte (z.B. Infocards) als JSON. |
| **Übersetzung importieren** | Importiert eine extern übersetzte JSON-Datei und übernimmt die Texte als manuelle Übersetzungen. |
| **Importierte Texte entfernen** | Entfernt alle manuell importierten Übersetzungen. |
| **Alle offenen automatisch übersetzen** | Öffnet den Bulk-Translate-Dialog für automatische Übersetzung aller offenen Einträge per Translator-API. |

Jeder Button hat ein **?**-Symbol daneben, das bei Klick oder Hover eine Erklärung zeigt.

### 5.5 Übersetzen (Anwenden)

| Button | Beschreibung |
|--------|-------------|
| **Text übersetzen** | Schreibt die verfügbaren Übersetzungen in die Mod-DLLs. |
| **Deutsche Audio kopieren** | Kopiert deutsche Voice-Dateien aus der Referenz in die Mod-Installation. |
| **Deutsche Funksprüche mergen** | Ersetzt unveränderte englische Funksprüche in UTF-Dateien durch deutsche Entsprechungen. |
| **Alles übersetzen** *(großer grüner Button)* | Führt Text-Übersetzung, Audio-Kopie und Funkspruch-Merge auf einmal aus. |

Darunter erscheinen:

- **Übersetzungsfortschritt:** Segmentierter Fortschrittsbalken + Audio- und Voice-Fortschritt.
- **Übersetzungsdurchlauf:** Live-Status während des DLL-Schreibens mit aktuellem DLL-Namen, Fortschrittsbalken und Eintrags-Log.

---

## 6. Der Editor-Arbeitsbereich

Im Tab **„Offene Übersetzungen"** findest du den Kern-Editor mit Tabelle, Filtern und Vorschaubereich.

### 6.1 Filter

Die Filterleiste oben erlaubt es, die Eintrags-Tabelle gezielt einzugrenzen. Jeder Filter hat ein **?**-Symbol mit Erklärung.

| Filter | Beschreibung |
|--------|-------------|
| **Typ** *(Kind)* | Filtert nach String oder Infocard. |
| **DLL** | Filtert nach einer bestimmten Ressourcen-DLL. |
| **Status** | Filtert nach Status: automatisch, manuell, offen, etc. |
| **Nur mit Referenz** | Zeigt nur Einträge, die eine Referenzübersetzung haben. |
| **Nur geänderte** | Zeigt nur Einträge, die sich vom Original unterscheiden. |
| **Suche** | Volltextsuche über Quelltext und Zieltext. |

Über der Tabelle kann außerdem die **Alte-Text-Quelle** gewählt werden — damit lässt sich ein früheres Backup als Vergleichstext verwenden.

### 6.2 Quell- und Zieltextvorschau

Die Detailansicht rechts zeigt:

| Bereich | Beschreibung |
|---------|-------------|
| **Quelltext** *(links oben)* | Der aktuelle Text aus der Mod-Installation. Nur lesbar. Rechtsklick bietet Terminologie-Optionen. |
| **Zieltext / Referenztext** *(links unten)* | Der Text aus der Referenz oder die manuelle Übersetzung. Direkt editierbar. |

### 6.3 Manuelle Bearbeitung

Unter dem Zieltext-Feld befinden sich drei Aktionsbuttons (jeweils mit **?**-Hilfe):

| Button | Beschreibung |
|--------|-------------|
| **Übersetzen** | Übersetzt den Quelltext per externem Translator (z.B. Google Translate) und schreibt das Ergebnis in den Zieltext. |
| **Manuelle Änderung zurücksetzen** | Setzt die manuelle Übersetzung für diesen Eintrag auf den Originaltext zurück. |
| **Änderung speichern** | Speichert die manuelle Änderung im Zieltextfeld als Übersetzung für diesen Eintrag. |

**Rechtsklick-Kontextmenü** auf den Quell- oder Zieltext bietet außerdem:

- Auswahl als Quell-Term verwenden
- Auswahl als Ziel-Term verwenden
- Mapping für Auswahl speichern
- Mod Override erstellen (Original behalten oder mit benutzerdefiniertem Text)

---

## 7. DLL-Analyse

Im Tab **„DLL-Analyse"** zeigt FL Lingo für jede betroffene DLL eine Übersicht:

| Spalte | Beschreibung |
|--------|-------------|
| **DLL** | Name der Ressourcen-DLL. |
| **Status** | Komplett abgedeckt, teilweise offen oder nur begrenzte Abdeckung. |
| **Abdeckung** | Anteil der Einträge, die automatisch oder manuell übersetzt sind. |
| **Bereit** | Einträge, die FL Lingo direkt anwenden kann. |
| **Offen** | Einträge, die noch übersetzt werden müssen. |
| **Mit Referenz** | Einträge mit passendem Gegenstück in der Referenzinstallation. |
| **Aktion** | Die empfohlene Aktion beim Anwenden (komplett patchen, Teile patchen, manuell prüfen). |

**DLL-Schreibstrategien:**

| Strategie | Bedeutung |
|-----------|-----------|
| **Komplett abgedeckt** | Alle Einträge aus der Referenz vorhanden — sicherer Komplett-Patch. |
| **Teilweise abgedeckt** | Einige Einträge passen, andere sind offen — nur gematchte Einträge werden gepatcht. |
| **Begrenzte Abdeckung** | Wenig automatische Abdeckung — manuelle Prüfung empfohlen. |

---

## 8. Terminologie und Pattern

Im Tab **„Terminologie"** pflegst du sprachspezifische Terminologie-Mappings und Pattern-Regeln.

### Terminologie-Mapping

Ordne hier Quellbegriffe einem Zielbegriff zu (z.B. „Battleship" → „Schlachtschiff"). FL Lingo nutzt diese Mappings für:

- Glossar-Export
- Bekannte Ersetzung von Begriffen
- Übersetzungsvorschläge für offene Einträge
- Konsistente Bezeichnung von Fraktionen, Orten und Rollen

| Feld | Beschreibung |
|------|-------------|
| **Quell-Term** | Der Originalbegriff. |
| **Ziel-Term** | Die gewünschte Übersetzung. |
| **Auswahl verwenden** | Füllt die Felder aus der aktuellen Textauswahl. |
| **Mapping speichern** | Speichert das Mapping in die aktive Terminologie-Datei. |

### Pattern-Regeln

Pattern-Regeln ersetzen wiederkehrende Textmuster automatisch.

| Feld | Beschreibung |
|------|-------------|
| **Pattern-Quelle** | Das Suchmuster. |
| **Pattern-Ziel** | Der Ersetzungstext. |
| **Pattern speichern** | Speichert die Pattern-Regel. |
| **Listen neu laden** | Lädt Terminologie und Pattern von der Festplatte neu. |

**Terminologie-Dateien:**

- `data/terminology.de.json` — Deutsche Terminologie
- `data/terminology.en.json` — Englische Terminologie

Die aktive Datei richtet sich nach der gewählten Zielsprache.

---

## 9. Mod Overrides

Im Tab **„Mod Overrides"** kannst du für einzelne Einträge festlegen, dass FL Lingo den Original-Mod-Text beibehalten oder einen benutzerdefinierten Text verwenden soll — unabhängig davon, was die Referenz sagt.

| Button | Beschreibung |
|--------|-------------|
| **Overrides neu laden** | Lädt die Override-Daten von der Festplatte. |
| **Ausgewählten Override löschen** | Entfernt den markierten Override-Eintrag. |

Overrides werden auch über das **Rechtsklick-Kontextmenü** im Editor erstellt.

---

## 10. Export und Import für externe Übersetzung

FL Lingo unterstützt einen JSON-basierten Workflow für externe Übersetzung:

### Export

1. **Offene Einträge exportieren:** Exportiert alle Einträge mit Status „Mod-Only" (ohne vorhandene Referenz) als JSON-Datei.
2. **Lange offene Texte exportieren:** Exportiert nur lange offene Texte (z.B. Infocards) — nützlich für separate Bearbeitung.
3. **Sichtbares JSON exportieren:** Exportiert die aktuell gefilterte/sichtbare Tabelle als JSON.

### Import

- **Übersetzung importieren:** Importiert eine extern übersetzte JSON-Datei. Die Texte werden als manuelle Übersetzungen übernommen.
- **Importierte Texte entfernen:** Setzt alle manuell importierten Übersetzungen zurück.

Das JSON-Dateiformat enthält pro Eintrag:
- DLL-Name und Ressource-ID
- Originaltext (Quelltext)
- Platzhalter für den übersetzten Text

---

## 11. Automatische Übersetzung (Bulk Translate)

Über den Button **„Alle offenen automatisch übersetzen"** öffnet sich ein Dialog, mit dem offene Einträge per externer Translator-API übersetzt werden können.

### Bedienung

1. **Mindestlänge einstellen:** Filtert kurze Einträge aus (z.B. nur Texte ab 50 Zeichen übersetzen).
2. **Vorschau:** Zeigt alle zu übersetzenden Einträge und deren Anzahl an, bevor die Übersetzung startet.
3. **Starten:** Beginnt die automatische Übersetzung.
4. **Pause / Weiter:** Pausiert den Vorgang jederzeit. Der bisherige Fortschritt wird gespeichert.
5. **Schließen:** Beendet den Dialog. Bereits übersetzte Einträge werden im Projekt gespeichert.

Die Ergebnistabelle zeigt für jeden Eintrag:
- DLL/ID-Referenz
- Alter Text (Quelltext)
- Neuer Text (Übersetzung)

### Translator-API konfigurieren

Über **Einstellungen → Translator API…** kannst du den Übersetzungsanbieter und optional einen API-Schlüssel konfigurieren.

| Einstellung | Beschreibung |
|-------------|-------------|
| **Anbieter** | Derzeit unterstützt: Google Translate (über `deep-translator`). |
| **API-Schlüssel** | Nicht erforderlich für kostenloses Google Translate. Für andere Anbieter oder höhere Rate Limits optional. |

---

## 12. Projektdateien (.FLLingo)

FL Lingo kann vollständige Arbeitssitzungen als `.FLLingo`-Projektdateien speichern und laden.

**Eine Projektdatei speichert:**

- Gewählte Installationspfade
- Sprachpaar (Quell- und Zielsprache)
- Infocards-Option
- Gepaarter Kataloginstand
- Manuelle Übersetzungen
- DLL-Analyse-Zustand

**Dateizuordnung:** Über **Datei → .FLLingo verknüpfen…** kann die Dateierweiterung registriert werden, sodass Projektdateien per Doppelklick FL Lingo öffnen.

### Projekt-Aktionen (Menü „Datei")

| Aktion | Beschreibung |
|--------|-------------|
| **Projekt laden** | Öffnen einer bestehenden `.FLLingo`-Datei. |
| **Neues Projekt** | Leeres Projekt beginnen. |
| **Projekt neu aufbauen** | Projekt aus Spieldaten neu erstellen (manuelle Bearbeitungen gehen verloren). |
| **Projekt speichern** | Aktuellen Stand speichern. |
| **Projekt speichern als** | Unter neuem Namen speichern. |

---

## 13. Backups und Wiederherstellung

FL Lingo erstellt vor jedem Schreibvorgang automatisch ein Backup der betroffenen DLL-Dateien.

| Funktion | Beschreibung |
|----------|-------------|
| **Automatisches Backup** | Bei jedem „Übersetzen" werden die Original-DLLs gesichert. |
| **Backup wiederherstellen** | Über **Datei → Backup wiederherstellen…** kann ein früherer Stand wiederhergestellt werden. |
| **Apply-Resume** | Wird ein Übersetzungslauf unterbrochen, kann er beim nächsten Mal fortgesetzt werden. |

---

## 14. Updates

FL Lingo prüft automatisch beim Start (nach ca. 1 Sekunde) auf neue Versionen via GitHub Releases.

### Automatischer Update-Check

- Kann im Hintergrund deaktiviert werden (via Umgebungsvariable `FLATLAS_DISABLE_STARTUP_UPDATE_CHECK=1`).
- Bereits verworfene Versionen werden nicht erneut angezeigt.

### Manueller Update-Check

Über **Hilfe → Auf Updates prüfen…** kann jederzeit manuell geprüft werden.

### Update installieren (Windows-Executable)

Wenn FL Lingo als gepackte `.exe` läuft und ein passendes Update-Paket vorhanden ist:

1. Klicke **„Update installieren"** im Update-Dialog.
2. Das Update wird heruntergeladen (mit Fortschrittsanzeige).
3. Der Updater (`FLLingoUpdater.exe`) übernimmt: wartet auf App-Ende → kopiert neue Dateien → startet FL Lingo neu.

Falls kein automatisches Update möglich ist, kannst du über **„Release öffnen"** die GitHub-Seite öffnen und das Update manuell herunterladen.

---

## 15. Menüleiste

### Datei

| Eintrag | Beschreibung |
|---------|-------------|
| Spiel laden | Mod-Installation in den Katalog laden. |
| Mit Referenz vergleichen | Geladene Quelle gegen Referenz vergleichen. |
| Projekt laden / Neues Projekt / Neu aufbauen | Projektverwaltung. |
| Projekt speichern / Speichern als | Arbeit sichern. |
| Backup wiederherstellen | Früheren DLL-Stand wiederherstellen. |
| .FLLingo verknüpfen | Dateizuordnung einrichten. |
| Sichtbares JSON exportieren | Gefilterte Tabelle als JSON exportieren. |
| Offene Einträge / Lange Texte exportieren | Für externe Übersetzung exportieren. |
| Übersetzung importieren | Externe Übersetzung importieren. |
| Deutsche Audio kopieren | Voice-Dateien kopieren. |
| Deutsche Funksprüche mergen | UTF-Voice-Dateien mergen. |
| Patch zusammenbauen | Verteilbaren Patch-Ordner erstellen. |
| Text übersetzen | Übersetzungen in DLLs schreiben. |

### Ansicht

| Eintrag | Beschreibung |
|---------|-------------|
| DLL-Analyse anzeigen | Wechselt zum DLL-Tab. |
| Einträge anzeigen | Wechselt zum Eintrags-Tab. |

### Einstellungen

| Eintrag | Beschreibung |
|---------|-------------|
| Erscheinungsbild | Theme wählen (hell, dunkel, Hochkontrast). |
| Terminologie öffnen | Terminologie-Datei im externen Editor öffnen. |
| Toolchain installieren | LLVM-Tools installieren. |
| Translator API | Übersetzer-Anbieter und API-Key konfigurieren. |

### Sprache

Wechselt die UI-Sprache: Englisch, Deutsch, Französisch, Spanisch, Russisch.

### Hilfe

| Eintrag | Beschreibung |
|---------|-------------|
| Auf Updates prüfen | Prüft GitHub auf neue Releases. |
| Hilfe öffnen | Öffnet das integrierte HTML-Hilfefenster. |
| Über FL Lingo | Zeigt Version, Entwickler und Links. |

---

## 16. Statuswerte und Fortschritt

### Eintrags-Status

| Status | Farbe | Bedeutung |
|--------|-------|-----------|
| **Bereits lokalisiert** | 🟣 Lila | Der Quelltext stimmt bereits mit der Referenz überein. |
| **Automatisch übernehmbar** | 🟢 Grün | Der Referenztext unterscheidet sich — bereit zum Anwenden. |
| **Manuell übersetzt** | 🟢 Grün | Benutzer- oder importierte Übersetzung vorhanden. |
| **Mod-Only** | ⚪ Grau | Kein Referenzmatch vorhanden — muss manuell oder extern übersetzt werden. |
| **Übersprungen** | 🟡 Gelb | Platzhalter, Zahlen, Eigennamen — bewusst nicht übersetzt. |

### Fortschrittsanzeigen

| Anzeige | Format |
|---------|--------|
| **Übersetzungsfortschritt** | Prozent · bearbeitete/gesamt Einträge · bereits lokalisiert · bereit zum Anwenden · übersprungen |
| **Audio-Fortschritt** | Prozent · vorhandene/gesamt deutsche Voice-Dateien · offene |
| **Voiceline-Fortschritt** | Prozent deutsch · DE/gesamt · ersetzbar · Mod-geändert · Dateien |

### Legende Fortschrittsbalken

- **Lila** = bereits im Spiel übersetzt
- **Grün** = bereit zum Anwenden
- **Gelb** = bewusst übersprungen
- **Grau** = offen

---

## 17. Einstellungen

### Erscheinungsbild

Über **Einstellungen → Erscheinungsbild** kann das Theme gewählt werden.

### Translator API

Über **Einstellungen → Translator API** wird der Übersetzer konfiguriert:

- **Anbieter:** Google Translate (über `deep-translator`)
- **API-Schlüssel:** Optional, für kostenloses Google Translate nicht erforderlich.

### Umgebungsvariablen

| Variable | Wirkung |
|----------|---------|
| `FLATLAS_DISABLE_STARTUP_UPDATE_CHECK=1` | Deaktiviert den automatischen Update-Check beim Start. |
| `FLATLAS_TOOLCHAIN_DIR` | Setzt den Pfad zur externen Resource-Toolchain (LLVM-Tools). |

---

## 18. Sprachen und Themes

### UI-Sprachen

| Sprache | Abdeckung |
|---------|-----------|
| **Deutsch** | Vollständig |
| **Englisch** | Vollständig |
| **Französisch** | Teilweise (Kernlabels, Menüs, Updates) |
| **Spanisch** | Teilweise |
| **Russisch** | Teilweise (transliteriert) |

Die Sprache wird über das Menü **Sprache** gewechselt und zur Laufzeit sofort angewendet.

### Themes

| Theme | Beschreibung |
|-------|-------------|
| **light** | Heller Hintergrund |
| **dark** | Dunkler Hintergrund (Standard) |
| **high contrast** | Hoher Kontrast für bessere Lesbarkeit |

---

## 19. Sicherheitshinweise

FL Lingo modifiziert Freelancer-Ressourcen-DLLs. Vor jedem Schreibvorgang wird automatisch ein Backup erstellt.

**Empfehlungen:**

- Teste zuerst auf einer **Kopie** des Spiels.
- Halte eine saubere Referenzinstallation **unverändert** bereit.
- Überprüfe die Ergebnisse mit echten Mods, bevor du es auf deine Hauptinstallation anwendest.
- Nutze die **Backup-Wiederherstellung**, falls etwas nicht stimmt.

---

## 20. Häufige Fragen (FAQ)

### Was ist die „Referenzinstallation"?

Eine saubere, unmodifizierte Freelancer-Installation in der Zielsprache (z.B. eine deutsche Vanilla-Installation). FL Lingo nutzt diese als Quelle für bekannte Übersetzungen.

### Brauche ich die englische Vanilla-Installation?

Nur optional — sie wird für den Voice-Line-Merge (UTF-Funksprüche) benötigt. Dabei werden englische Funksprüche in der Mod mit deutschen aus der Referenz verglichen und ersetzt.

### Was bedeutet „Mod-Only"?

Ein Eintrag, der in der Mod existiert, aber kein Gegenstück in der Referenzinstallation hat. Diese Texte wurden von der Mod neu hinzugefügt und müssen manuell oder extern übersetzt werden.

### Kann ich den Vorgang unterbrechen und fortsetzen?

Ja. Sowohl der Apply-Lauf als auch die Bulk-Übersetzung können pausiert und beim nächsten Mal fortgesetzt werden. Der Fortschritt wird im Projekt gespeichert.

### Was passiert, wenn FL Lingo eine DLL als „unsicher" einstuft?

FL Lingo überschreibt die DLL nicht blind. Stattdessen wird empfohlen, die Einträge manuell zu prüfen. Nur bestätigte Einträge werden gepatcht.

### Kann ich eigene Übersetzungen korrigieren?

Ja. Im Editor-Tab kannst du den Zieltext direkt editieren und über **„Änderung speichern"** als manuelle Übersetzung festlegen.

### Was macht der Patch-Zusammenbau?

Er erstellt einen verteilbaren Ordner mit allen veränderten DLLs und einem Manifest — nützlich, wenn du deine Übersetzung als Patch weitergeben möchtest.

---

## 21. Fehlerbehebung

### „Keine Resource-Toolchain gefunden"

FL Lingo benötigt LLVM-Resource-Tools (`llvm-rc`, `llvm-windres`) zum Patchen von DLLs. Installiere sie über **Einstellungen → Toolchain installieren** oder setze die Umgebungsvariable `FLATLAS_TOOLCHAIN_DIR`.

### „deep-translator ist nicht installiert"

Die automatische Übersetzung benötigt das Python-Paket `deep-translator`. Installiere es mit:

```bash
pip install deep-translator
```

Bei der Windows-Executable ist es bereits enthalten.

### Update-Prüfung schlägt fehl

Prüfe deine Internetverbindung. FL Lingo versucht drei Fallback-Methoden (API mit TLS, API ohne TLS-Verifizierung, URL-Redirect-Parsing). Bei Firewall-Problemen kann der Check manuell über **Hilfe → Auf Updates prüfen** wiederholt werden.

### Übersetzung wird nicht angewendet

Stelle sicher, dass:
1. Beide Installationen geladen und verglichen sind.
2. Die Resource-Toolchain verfügbar ist.
3. Mindestens eine DLL „bereit" oder „teilweise abgedeckt" ist.

---

## 22. Technische Details

### Projektstruktur

| Datei / Ordner | Zweck |
|----------------|-------|
| `launch.py` | Startpunkt und zentrale App-Defaults |
| `src/flatlas_translator/ui_app.py` | Hauptfenster |
| `src/flatlas_translator/ui_builders.py` | Widget- und Seitenaufbau |
| `src/flatlas_translator/ui_state.py` | UI-Zustand und Refresh-Logik |
| `src/flatlas_translator/ui_editor.py` | Editor und Terminologie-Interaktionen |
| `src/flatlas_translator/ui_workflows.py` | Import/Export, Projekt, Hilfe und Update-Workflows |
| `src/flatlas_translator/ui_session.py` | Session, Katalog und Apply-Controller |
| `src/flatlas_translator/ui_chrome.py` | Fenstertitel, Retranslate, Status, Footer |
| `src/flatlas_translator/ui_strings.py` | Eingebaute UI-Texte und URLs |
| `src/flatlas_translator/catalog.py` | Katalogaufbau und Pairing |
| `src/flatlas_translator/dll_resources.py` | Ressourcen-Extraktion aus DLLs |
| `src/flatlas_translator/resource_writer.py` | Schreib-/Apply-Logik |
| `src/flatlas_translator/terminology.py` | Terminologie und Vorschläge |
| `src/flatlas_translator/project_io.py` | `.FLLingo`-Projektformat |
| `Languages/` | UI-Übersetzungsdateien (partielle Overrides) |
| `data/help/` | HTML-Hilfedateien |
| `data/` | Terminologie und App-Daten |
| `tests/` | Automatisierte Tests |
| `fllingo_updater.py` | Standalone-Updater-Skript (→ `FLLingoUpdater.exe`) |

### Abhängigkeiten

| Paket | Zweck |
|-------|-------|
| `PySide6 ≥ 6.6` | GUI-Framework (Qt6) |
| `pefile ≥ 2023.2.7` | Ressourcen-DLLs lesen |
| `deep-translator ≥ 1.11` | Externe Übersetzungs-API |

### Plattformstatus

| Plattform | Status |
|-----------|--------|
| **Windows** | Vollständig: Vergleich, Export/Import, DLL-Patching, Audio-Kopie, Voice-Merge |
| **Linux** | Vollständig: Gleicher Workflow wie Windows, einschließlich DLL-Schreibfunktion |

### Tests ausführen

```bash
# Alle Tests
python -m pytest

# GUI-Smoke-Tests (headless)
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_ui_smoke.py
```

---

*FL Lingo — Developed by Aldenmar Odin — flathack*
