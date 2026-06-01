=== ENGLISH ===

WINDOWS USERS:
Simply download main.exe and double-click it. Everything you need is included inside the file. No additional installation required.

MAC/LINUX USERS:
Follow the Python installation instructions below to run the app from the terminal.

=== GERMAN ===

WINDOWS-BENUTZER:
Laden Sie einfach main.exe herunter und doppelklicken Sie darauf. Alles, was Sie brauchen, ist in der Datei enthalten. Keine zusätzliche Installation erforderlich.

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
  * This tool works only on text-based PDFs. Scanned documents (paper
    documents photographed or photocopied into PDF) cannot be processed.

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
This may take 1–3 minutes depending on your internet connection.

------------------------------------------------------------------------------
STEP 5 — DOWNLOAD THE LANGUAGE MODEL
------------------------------------------------------------------------------
The program uses a language model to recognize names. Download it with this
command (type it in the Terminal and press Enter):

    python -m spacy download en_core_web_sm

  (On Mac or Linux, you may need to type "python3" instead of "python".)

Wait for the download to complete. This only needs to be done once.

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
  1. Click "Choose PDF" and select the document you want to anonymize.

  2. Click "Analyze PDF". The program will scan the document and display a
     list of all detected person names with their frequency count.

  3. Review the list. All names are checked (☑) by default.
     - Click any row to uncheck (☐) a name you do NOT want redacted.
     - Use "Deselect All" to uncheck everything, then check only the names
       you want removed.

  4. When satisfied with your selection, click "Redact PDF".

  5. The program will save a new file called:
         yourfilename_anonymized.pdf
     in the same folder as your original PDF. A confirmation message will
     show you the exact file path.

  6. Your original PDF remains untouched.

------------------------------------------------------------------------------
TROUBLESHOOTING
------------------------------------------------------------------------------
PROBLEM: "python is not recognized as a command" (Windows)
SOLUTION: Python was installed without "Add Python to PATH" checked.
          Uninstall Python, reinstall it, and tick that checkbox.

PROBLEM: The program says the PDF is a scanned image
SOLUTION: This tool only works on text-based PDFs (documents created
          digitally). Scanned paper documents cannot be processed without
          additional OCR software. Try to obtain the original digital version
          of the document.

PROBLEM: A name was not detected
SOLUTION: The AI may miss uncommon or foreign names. After redaction,
          manually search the anonymized PDF for any missed names.

PROBLEM: A name was wrongly detected (e.g., a place name or organization)
SOLUTION: Simply uncheck that row in the list before clicking "Redact PDF".

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
  * Dieses Tool funktioniert nur bei textbasierten PDFs. Eingescannte
    Dokumente (Papier, das als PDF fotografiert oder kopiert wurde) können
    nicht verarbeitet werden.

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
Dies kann je nach Internetverbindung 1 bis 3 Minuten dauern.

------------------------------------------------------------------------------
SCHRITT 5 — DAS SPRACHMODELL HERUNTERLADEN
------------------------------------------------------------------------------
Das Programm verwendet ein Sprachmodell zur Namenserkennung. Laden Sie es
mit diesem Befehl herunter (im Terminal eingeben und Enter drücken):

    python -m spacy download en_core_web_sm

  (Auf Mac oder Linux müssen Sie möglicherweise "python3" statt "python"
  eingeben.)

Warten Sie, bis der Download abgeschlossen ist. Dies muss nur einmal
durchgeführt werden.

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
  1. Klicken Sie auf "Choose PDF" und wählen Sie das zu anonymisierende
     Dokument aus.

  2. Klicken Sie auf "Analyze PDF". Das Programm durchsucht das Dokument
     und zeigt eine Liste aller erkannten Personennamen mit ihrer
     Häufigkeit an.

  3. Überprüfen Sie die Liste. Alle Namen sind standardmäßig angehakt (☑).
     - Klicken Sie auf eine Zeile, um einen Namen abzuhaken (☐), der NICHT
       geschwärzt werden soll.
     - Verwenden Sie "Deselect All", um alle Haken zu entfernen, und haken
       Sie dann nur die Namen an, die Sie entfernen möchten.

  4. Wenn Sie mit Ihrer Auswahl zufrieden sind, klicken Sie auf "Redact PDF".

  5. Das Programm speichert eine neue Datei mit dem Namen:
         IhreDateiname_anonymized.pdf
     im selben Ordner wie Ihr Original-PDF. Eine Bestätigungsmeldung zeigt
     Ihnen den genauen Dateipfad an.

  6. Ihr Original-PDF bleibt unverändert.

------------------------------------------------------------------------------
FEHLERBEHEBUNG
------------------------------------------------------------------------------
PROBLEM: "python wird nicht als Befehl erkannt" (Windows)
LÖSUNG:  Python wurde ohne aktiviertes "Add Python to PATH" installiert.
         Deinstallieren Sie Python, installieren Sie es neu und aktivieren
         Sie dabei dieses Kontrollkästchen.

PROBLEM: Das Programm meldet, das PDF sei ein eingescanntes Bild
LÖSUNG:  Dieses Tool funktioniert nur bei textbasierten PDFs (digital
         erstellte Dokumente). Eingescannte Papierdokumente können ohne
         zusätzliche OCR-Software nicht verarbeitet werden. Versuchen Sie,
         die ursprüngliche digitale Version des Dokuments zu beschaffen.

PROBLEM: Ein Name wurde nicht erkannt
LÖSUNG:  Die KI kann ungebräuchliche oder fremdsprachige Namen übersehen.
         Durchsuchen Sie nach der Schwärzung das anonymisierte PDF manuell
         nach möglicherweise übersehenen Namen.

PROBLEM: Ein Name wurde fälschlicherweise erkannt (z. B. ein Ort oder
         eine Organisation)
LÖSUNG:  Entfernen Sie einfach den Haken bei dieser Zeile in der Liste,
         bevor Sie auf "Redact PDF" klicken.

PROBLEM: Das Programm stürzt beim Öffnen einer PDF-Datei ab
LÖSUNG:  Das PDF ist möglicherweise passwortgeschützt oder beschädigt.
         Versuchen Sie, es zuerst in einem PDF-Betrachter zu öffnen.
         Wenn es verschlüsselt ist, müssen Sie es entsperren, bevor Sie
         dieses Tool verwenden können.

PROBLEM: Fehlermeldung "No module named ..." im Terminal
LÖSUNG:  Wiederholen Sie Schritt 4 (pip install -r requirements.txt).
         Stellen Sie sicher, dass Sie sich beim Ausführen des Befehls im
         richtigen Ordner befinden.

PROBLEM: Der Befehl "pip" wird nicht gefunden
LÖSUNG:  Ersetzen Sie "pip" durch "pip3" in Schritt 4, oder verwenden Sie:
             python -m pip install -r requirements.txt

==============================================================================
