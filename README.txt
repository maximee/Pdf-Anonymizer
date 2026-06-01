=== ENGLISH ===

WINDOWS USERS:
Simply download Pdf-Anonymizer.zip, double-click it and start the PDF-Anonymizer application. Everything you need is included inside the file. No additional installation required.

MAC/LINUX USERS:
Follow the Python installation instructions below to run the app from the terminal.

=== GERMAN ===

WINDOWS-BENUTZER:
Laden Sie einfach Pdf-Anonymizer.zip herunter, doppelklicken Sie darauf und starten sie das PDF-Anonymizer programm. Alles, was Sie brauchen, ist in der Datei enthalten. Keine zusätzliche Installation erforderlich.

MAC/LINUX-BENUTZER:
Folgen Sie den Python-Installationsanweisungen unten, um die App vom Terminal aus auszuführen.

==============================================================================
=== ENGLISH ===
==============================================================================

PDF ANONYMIZER — Setup and Usage Guide
For legal professionals | No coding experience required

------------------------------------------------------------------------------
WHAT THIS PROGRAM DOES
------------------------------------------------------------------------------
PDF Anonymizer reads a PDF document, automatically detects all person names
using artificial intelligence, and lets you review those names before creating
a new, redacted copy of the document with the selected names blacked out.

The program includes:
  • Automatic name detection (AI-powered)
  • Interactive PDF viewer with zoom controls
  • Real-time redaction preview as you toggle names
  • Manual text selection for missed redactions
  • Support for both text-based and scanned PDFs (with OCR)

The original PDF is never changed. A separate file named
    yourfile_anonymized.pdf
is saved in the same folder as your original.

------------------------------------------------------------------------------
!! IMPORTANT SAFETY NOTICE — READ BEFORE YOU BEGIN !!
------------------------------------------------------------------------------
  * This program NEVER modifies or deletes your original PDF.
  * The redacted copy is saved as a NEW file alongside the original.
  * Always keep a backup of your original PDF in a secure location.
  * The redaction covers names visually (black boxes). For court-level
    filings, verify the output meets the specific standards required by
    your jurisdiction before submission.
  * Scanned PDFs (documents photographed or photocopied into PDF format)
    require OCR processing, which takes 1-2 minutes per 10 pages.

------------------------------------------------------------------------------
STEP 1 — INSTALL PYTHON
------------------------------------------------------------------------------
Python is the programming language this tool is built on. You only need to
install it once.

  WINDOWS
  -------
  1. Open your web browser and go to:  https://www.python.org/downloads/
  2. Click the yellow "Download Python 3.x.x" button.
  3. Once downloaded, run the installer file (python-3.x.x.exe).
  4. IMPORTANT: On the first screen of the installer, tick the checkbox
     labeled "Add Python to PATH" before clicking anything else.
     If you skip this step, Step 3 commands will not work.
  5. Click "Install Now" and wait for it to finish.
  6. Click "Close" when done.

  MAC
  ---
  1. Open your web browser and go to:  https://www.python.org/downloads/
  2. Click the yellow "Download Python 3.x.x" button.
  3. Once downloaded, open the .pkg file and follow the installation steps.
  4. Click through all the default options and enter your Mac password if
     asked.

  LINUX (Ubuntu / Debian)
  -----------------------
  Open a Terminal and run:
      sudo apt update && sudo apt install python3 python3-pip

  LINUX (Fedora / RHEL)
  ----------------------
  Open a Terminal and run:
      sudo dnf install python3

------------------------------------------------------------------------------
STEP 2 — OPEN THE TERMINAL (COMMAND LINE)
------------------------------------------------------------------------------
The Terminal lets you type instructions directly to your computer. You will
only need it during setup — not when using the program day-to-day.

  WINDOWS
  -------
  Press the Windows key, type "cmd", and press Enter.
  A black window with white text will open. This is the Command Prompt.

  MAC
  ---
  Press Command + Space, type "Terminal", and press Enter.
  A window with a text prompt will open.

  LINUX
  -----
  Right-click on the desktop and choose "Open Terminal", or search for
  "Terminal" in your applications menu.

------------------------------------------------------------------------------
STEP 3 — NAVIGATE TO THE PROGRAM FOLDER
------------------------------------------------------------------------------
In the Terminal, you need to move into the folder where main.py is saved.
Type the following command and press Enter (replace the path with your actual
folder location):

  WINDOWS example:
      cd "C:\Users\YourName\Documents\Pdf-anonymizer"

  MAC / LINUX example:
      cd "/Users/YourName/Documents/Pdf-anonymizer"

Tip: You can drag the folder from Finder (Mac) or File Explorer (Windows)
directly into the Terminal window and it will fill in the path for you.

------------------------------------------------------------------------------
STEP 4 — INSTALL THE REQUIRED LIBRARIES
------------------------------------------------------------------------------
Libraries are small add-on packages the program needs to work. This step
downloads and installs them automatically. You only need to do this once.

In the Terminal, type the following command exactly and press Enter:

    pip install -r requirements.txt

  (On Mac or Linux, you may need to type "pip3" instead of "pip".)

Wait until you see a message confirming everything was installed successfully.
This may take 2–5 minutes depending on your internet connection (includes
downloading the OCR model for scanned PDFs).

------------------------------------------------------------------------------
STEP 5 — DOWNLOAD THE LANGUAGE MODELS
------------------------------------------------------------------------------
The program uses language models to recognize names and extract text from
scanned documents. Download them with these commands (type them in the
Terminal and press Enter):

    python -m spacy download en_core_web_sm

  (On Mac or Linux, you may need to type "python3" instead of "python".)

Wait for the downloads to complete. This only needs to be done once.

On first use with a scanned PDF, the app will download additional OCR models
(this happens automatically).

------------------------------------------------------------------------------
STEP 6 — RUN THE PROGRAM
------------------------------------------------------------------------------
In the Terminal, type the following command and press Enter:

    python main.py

  (On Mac or Linux, you may need to type "python3" instead of "python".)

The PDF Anonymizer window will open. You can now close the Terminal.
To open the program again in the future, repeat only this step.

------------------------------------------------------------------------------
HOW TO USE THE PROGRAM
------------------------------------------------------------------------------

WORKFLOW:

  1. Click "Choose PDF" and select the document you want to anonymize.

  2. Click "Analyze PDF". The program will scan the document and:
     - Display the first page in the PDF viewer (left side)
     - Show a list of all detected person names (right side)
     - For scanned PDFs: this may take 1-2 minutes per 10 pages

  3. REVIEW THE DOCUMENT:
     - Use [Prev] [Next] buttons to navigate through pages
     - Use [Zoom −] [Zoom +] to see details
     - As you check/uncheck names on the right, the redactions appear/disappear
       on the PDF in real-time (you see exactly what will be redacted)

  4. IMPROVE THE DETECTION:
     - Uncheck any detected names you do NOT want redacted
     - If a name was missed, click "Select Text to Redact"
     - Click on the missed text in the PDF viewer (it will highlight in blue)
     - Click "Confirm Selections" to add it to the redaction list
     - Uncheck names in the preview table if they're wrong detections

  5. When satisfied, click "Redact PDF".

  6. The program will save a new file called:
         yourfilename_anonymized.pdf
     in the same folder as your original PDF. A confirmation message will
     show you the exact file path.

  7. Your original PDF remains untouched.

TIPS:
  • Use the filter strictness slider to adjust how aggressive the name
    detection is (useful for German documents with many capitalized words)
  • For German legal documents: Higher strictness (7-10) reduces false
    positives but may miss some names
  • Always review the PDF viewer before exporting to verify redactions
    look correct

------------------------------------------------------------------------------
TROUBLESHOOTING
------------------------------------------------------------------------------
PROBLEM: "python is not recognized as a command" (Windows)
SOLUTION: Python was installed without "Add Python to PATH" checked.
          Uninstall Python, reinstall it, and tick that checkbox.

PROBLEM: Installation takes a very long time
SOLUTION: The OCR library (easyocr) is large (~500MB download). This is
          normal on first installation. Subsequent uses will be faster.

PROBLEM: "No module named easyocr" when opening a scanned PDF
SOLUTION: Repeat Step 4 (pip install -r requirements.txt). Make sure you
          completed Step 4 fully.

PROBLEM: A scanned PDF takes very long to process
SOLUTION: This is normal. OCR processing takes 1-2 minutes per 10 pages.
          The program will show a progress message. Be patient and do not
          close the window.

PROBLEM: The PDF viewer doesn't display the document
SOLUTION: The PDF may be corrupted or password-protected. Try opening it
          in another PDF viewer first. If it's encrypted, you will need to
          unlock it before using this tool.

PROBLEM: A name was not detected
SOLUTION: The AI may miss uncommon or foreign names. Use the "Select Text
          to Redact" feature to manually mark missed names.

PROBLEM: A name was wrongly detected (e.g., a place name or organization)
SOLUTION: Simply uncheck that row in the list before clicking "Redact PDF".
          For German documents, adjust the filter strictness slider.

PROBLEM: The program crashes when opening a PDF
SOLUTION: The PDF may be password-protected or corrupted. Try opening it
          in a PDF viewer first. If it is encrypted, you will need to unlock
          it before using this tool.

PROBLEM: "No module named ..." error in the Terminal
SOLUTION: Repeat Step 4 (pip install -r requirements.txt). Make sure you
          are in the correct folder when you run the command.

PROBLEM: The pip command is not found
SOLUTION: Try replacing "pip" with "pip3" in Step 4, or run:
              python -m pip install -r requirements.txt

PROBLEM: Text selection tool doesn't work / I can't click on text
SOLUTION: Make sure you clicked "Select Text to Redact" button first.
          The button activates selection mode. Then click on the text you
          want to redact in the PDF viewer.


==============================================================================
=== GERMAN ===
==============================================================================

PDF ANONYMIZER — Einrichtungs- und Benutzeranleitung
Für Rechtsanwälte und Juristen | Keine Programmierkenntnisse erforderlich

------------------------------------------------------------------------------
WAS DIESES PROGRAMM TUT
------------------------------------------------------------------------------
PDF Anonymizer liest ein PDF-Dokument, erkennt mithilfe künstlicher
Intelligenz automatisch alle Personennamen und ermöglicht es Ihnen, diese
Namen zu überprüfen, bevor eine neue, geschwärzte Kopie des Dokuments
erstellt wird.

Das Programm bietet:
  • Automatische Namenserkennung (KI-gestützt)
  • Interaktiver PDF-Viewer mit Zoomfunktion
  • Echtzeit-Schwärzungsvorschau beim Umschalten von Namen
  • Manuelle Textauswahl für übersehene Schwärzungen
  • Unterstützung für textbasierte und eingescannte PDFs (mit OCR)

Das Original-PDF wird niemals verändert. Eine separate Datei mit dem Namen
    IhreDatei_anonymized.pdf
wird im selben Ordner wie Ihr Original gespeichert.

------------------------------------------------------------------------------
!! WICHTIGER SICHERHEITSHINWEIS — BITTE VOR BEGINN LESEN !!
------------------------------------------------------------------------------
  * Dieses Programm verändert oder löscht Ihr Original-PDF NIEMALS.
  * Die geschwärzte Kopie wird als NEUE Datei neben dem Original gespeichert.
  * Bewahren Sie immer eine Sicherungskopie Ihres Original-PDFs an einem
    sicheren Ort auf.
  * Die Schwärzung überdeckt Namen visuell (schwarze Balken). Für
    Gerichtseinreichungen prüfen Sie bitte, ob der Ausdruck den
    spezifischen Anforderungen Ihrer Jurisdiktion entspricht.
  * Eingescannte PDFs (Papier, das als PDF fotografiert oder kopiert wurde)
    erfordern OCR-Verarbeitung, was 1-2 Minuten pro 10 Seiten dauert.

------------------------------------------------------------------------------
SCHRITT 1 — PYTHON INSTALLIEREN
------------------------------------------------------------------------------
Python ist die Programmiersprache, auf der dieses Tool basiert. Sie müssen
es nur einmal installieren.

  WINDOWS
  -------
  1. Öffnen Sie Ihren Browser und gehen Sie zu:  https://www.python.org/downloads/
  2. Klicken Sie auf die gelbe Schaltfläche "Download Python 3.x.x".
  3. Führen Sie nach dem Herunterladen die Installationsdatei aus
     (python-3.x.x.exe).
  4. WICHTIG: Aktivieren Sie auf dem ersten Bildschirm des Installationsprogramms
     das Kontrollkästchen "Add Python to PATH", bevor Sie auf etwas anderes
     klicken. Wenn Sie diesen Schritt überspringen, funktionieren die
     Befehle in Schritt 4 nicht.
  5. Klicken Sie auf "Install Now" und warten Sie, bis die Installation
     abgeschlossen ist.
  6. Klicken Sie auf "Close", wenn die Installation fertig ist.

  MAC
  ---
  1. Öffnen Sie Ihren Browser und gehen Sie zu:  https://www.python.org/downloads/
  2. Klicken Sie auf die gelbe Schaltfläche "Download Python 3.x.x".
  3. Öffnen Sie nach dem Herunterladen die .pkg-Datei und folgen Sie den
     Installationsschritten.
  4. Klicken Sie durch alle Standardoptionen und geben Sie Ihr Mac-Passwort
     ein, wenn Sie dazu aufgefordert werden.

  LINUX (Ubuntu / Debian)
  -----------------------
  Öffnen Sie ein Terminal und geben Sie folgenden Befehl ein:
      sudo apt update && sudo apt install python3 python3-pip

  LINUX (Fedora / RHEL)
  ---------------------
  Öffnen Sie ein Terminal und geben Sie folgenden Befehl ein:
      sudo dnf install python3

------------------------------------------------------------------------------
SCHRITT 2 — DAS TERMINAL ÖFFNEN (BEFEHLSEINGABE)
------------------------------------------------------------------------------
Das Terminal ermöglicht es Ihnen, Anweisungen direkt an Ihren Computer zu
tippen. Sie benötigen es nur während der Einrichtung — nicht bei der
täglichen Nutzung des Programms.

  WINDOWS
  -------
  Drücken Sie die Windows-Taste, tippen Sie "cmd" und drücken Sie Enter.
  Ein schwarzes Fenster mit weißem Text öffnet sich. Dies ist die
  Eingabeaufforderung.

  MAC
  ---
  Drücken Sie Command + Leertaste, tippen Sie "Terminal" und drücken Sie
  Enter. Ein Fenster mit einer Texteingabe öffnet sich.

  LINUX
  -----
  Klicken Sie mit der rechten Maustaste auf den Desktop und wählen Sie
  "Terminal öffnen", oder suchen Sie "Terminal" in Ihrem Anwendungsmenü.

------------------------------------------------------------------------------
SCHRITT 3 — ZUM PROGRAMMORDNER NAVIGIEREN
------------------------------------------------------------------------------
Im Terminal müssen Sie in den Ordner wechseln, in dem die Datei main.py
gespeichert ist. Geben Sie folgenden Befehl ein und drücken Sie Enter
(ersetzen Sie den Pfad durch Ihren tatsächlichen Ordnerstandort):

  WINDOWS Beispiel:
      cd "C:\Benutzer\IhrName\Dokumente\Pdf-anonymizer"

  MAC / LINUX Beispiel:
      cd "/Users/IhrName/Dokumente/Pdf-anonymizer"

Tipp: Sie können den Ordner aus dem Finder (Mac) oder dem Datei-Explorer
(Windows) direkt in das Terminal-Fenster ziehen, und der Pfad wird
automatisch eingetragen.

------------------------------------------------------------------------------
SCHRITT 4 — DIE ERFORDERLICHEN BIBLIOTHEKEN INSTALLIEREN
------------------------------------------------------------------------------
Bibliotheken sind kleine Zusatzpakete, die das Programm zum Funktionieren
benötigt. Dieser Schritt lädt und installiert sie automatisch. Sie müssen
dies nur einmal tun.

Geben Sie im Terminal folgenden Befehl genau so ein und drücken Sie Enter:

    pip install -r requirements.txt

  (Auf Mac oder Linux müssen Sie möglicherweise "pip3" statt "pip" eingeben.)

Warten Sie, bis eine Meldung die erfolgreiche Installation bestätigt.
Dies kann je nach Internetverbindung 2–5 Minuten dauern (einschließlich
Herunterladen des OCR-Modells für eingescannte PDFs).

------------------------------------------------------------------------------
SCHRITT 5 — DIE SPRACHMODELLE HERUNTERLADEN
------------------------------------------------------------------------------
Das Programm verwendet Sprachmodelle zur Namenserkennung und zum Extrahieren
von Text aus eingescannten Dokumenten. Laden Sie sie mit diesen Befehlen
herunter (geben Sie sie im Terminal ein und drücken Sie Enter):

    python -m spacy download en_core_web_sm

  (Auf Mac oder Linux müssen Sie möglicherweise "python3" statt "python"
  eingeben.)

Warten Sie, bis die Downloads abgeschlossen sind. Dies muss nur einmal
durchgeführt werden.

Bei der ersten Verwendung mit einem eingescannten PDF lädt die App
automatisch zusätzliche OCR-Modelle herunter.

------------------------------------------------------------------------------
SCHRITT 6 — DAS PROGRAMM STARTEN
------------------------------------------------------------------------------
Geben Sie im Terminal folgenden Befehl ein und drücken Sie Enter:

    python main.py

  (Auf Mac oder Linux müssen Sie möglicherweise "python3" statt "python"
  eingeben.)

Das PDF Anonymizer-Fenster wird geöffnet. Sie können das Terminal nun
schließen. Um das Programm in Zukunft erneut zu öffnen, wiederholen Sie
nur diesen Schritt.

------------------------------------------------------------------------------
VERWENDUNG DES PROGRAMMS
------------------------------------------------------------------------------

ARBEITSABLAUF:

  1. Klicken Sie auf "Choose PDF" und wählen Sie das zu anonymisierende
     Dokument aus.

  2. Klicken Sie auf "Analyze PDF". Das Programm wird:
     - Die erste Seite im PDF-Viewer anzeigen (linke Seite)
     - Eine Liste aller erkannten Personennamen anzeigen (rechte Seite)
     - Bei eingescannten PDFs: Dies kann 1-2 Minuten pro 10 Seiten dauern

  3. DOKUMENT ÜBERPRÜFEN:
     - Nutzen Sie die Schaltflächen [Prev] [Next] zur Navigation zwischen
       Seiten
     - Nutzen Sie [Zoom −] [Zoom +], um Details zu sehen
     - Während Sie Namen auf der rechten Seite an- oder abhaken, werden die
       Schwärzungen auf dem PDF in Echtzeit angezeigt (Sie sehen genau, was
       geschwärzt wird)

  4. ERKENNUNG VERBESSERN:
     - Haken Sie alle erkannten Namen ab, die NICHT geschwärzt werden sollen
     - Wenn ein Name übersehen wurde, klicken Sie auf "Select Text to Redact"
     - Klicken Sie auf den übersehenen Text im PDF-Viewer (er wird blau
       hervorgehoben)
     - Klicken Sie auf "Confirm Selections", um ihn zur Schwärzungsliste
       hinzuzufügen
     - Haken Sie Namen in der Vorschautabelle ab, wenn sie falsch erkannt
       wurden

  5. Wenn Sie zufrieden sind, klicken Sie auf "Redact PDF".

  6. Das Programm speichert eine neue Datei mit dem Namen:
         IhreDateiname_anonymized.pdf
     im selben Ordner wie Ihr Original-PDF. Eine Bestätigungsmeldung zeigt
     Ihnen den genauen Dateipfad an.

  7. Ihr Original-PDF bleibt unverändert.

TIPPS:
  • Verwenden Sie den Schieberegler für die Filtergenauigkeit, um die
    Aggressivität der Namenserkennung anzupassen (nützlich für deutsche
    Dokumente mit vielen großgeschriebenen Wörtern)
  • Für deutsche Rechtsdokumente: Höhere Genauigkeit (7-10) reduziert
    Fehlalarme, kann aber einige Namen übersehen
  • Überprüfen Sie immer den PDF-Viewer vor dem Export, um sicherzustellen,
    dass die Schwärzungen korrekt aussehen

------------------------------------------------------------------------------
FEHLERBEHEBUNG
------------------------------------------------------------------------------
PROBLEM: "python wird nicht als Befehl erkannt" (Windows)
LÖSUNG:  Python wurde ohne aktiviertes "Add Python to PATH" installiert.
         Deinstallieren Sie Python, installieren Sie es neu und aktivieren
         Sie dabei dieses Kontrollkästchen.

PROBLEM: Die Installation dauert sehr lange
LÖSUNG:  Die OCR-Bibliothek (easyocr) ist groß (~500 MB Download). Das ist
         normal bei der ersten Installation. Nachfolgende Verwendungen
         werden schneller.

PROBLEM: "No module named easyocr" beim Öffnen eines eingescannten PDF
LÖSUNG:  Wiederholen Sie Schritt 4 (pip install -r requirements.txt).
         Stellen Sie sicher, dass Sie Schritt 4 vollständig abgeschlossen
         haben.

PROBLEM: Ein eingescanntes PDF dauert sehr lange zum Verarbeiten
LÖSUNG:  Das ist normal. OCR-Verarbeitung dauert 1-2 Minuten pro 10 Seiten.
         Das Programm zeigt eine Fortschrittsmeldung an. Haben Sie Geduld
         und schließen Sie das Fenster nicht.

PROBLEM: Der PDF-Viewer zeigt das Dokument nicht an
LÖSUNG:  Das PDF ist möglicherweise beschädigt oder passwortgeschützt.
         Versuchen Sie, es zuerst in einem anderen PDF-Betrachter zu öffnen.
         Wenn es verschlüsselt ist, müssen Sie es entsperren, bevor Sie
         dieses Tool verwenden können.

PROBLEM: Ein Name wurde nicht erkannt
LÖSUNG:  Die KI kann ungebräuchliche oder fremdsprachige Namen übersehen.
         Verwenden Sie die Funktion "Select Text to Redact", um übersehene
         Namen manuell zu markieren.

PROBLEM: Ein Name wurde fälschlicherweise erkannt (z. B. ein Ort oder