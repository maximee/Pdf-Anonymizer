#!/usr/bin/env python3
"""
PDF Anonymizer — main.py
========================
Detects person names in text-based PDFs and creates a redacted copy
with every selected name covered by a solid black rectangle.

Run this file to open the application:
    python main.py          (Windows)
    python3 main.py         (Mac / Linux)

Required libraries (install once via: pip install -r requirements.txt):
    pdfplumber  — reads text and word positions from PDF files
    spacy       — AI model that identifies person names in text
    reportlab   — draws the black redaction rectangles
    pypdf       — merges the redaction layer onto the original PDF
"""

import io           # for building files in memory without touching disk
import os           # for file path operations (basename, dirname, splitext)
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import Counter  # dictionary that automatically counts items

import pdfplumber
import spacy
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter


# Load the spaCy English NER model once when the program starts.
# Keeping it at module level avoids reloading it on every button click.
# If the model has not been downloaded yet, _NLP is set to None and
# main() will exit with a clear installation instruction.
try:
    _NLP = spacy.load("en_core_web_sm")
except OSError:
    _NLP = None


# ==============================================================================
# SECTION 1 — PDF READING
# Responsible for opening a PDF file and extracting the text content along
# with the exact position of every word on every page. The position data is
# what lets us later draw black boxes in precisely the right spots.
# ==============================================================================

def extract_pdf_data(filepath: str) -> list[dict]:
    """
    Open a PDF file and return a list of page dictionaries.

    Each dictionary in the returned list represents one page and contains:
        "width"  — page width in points (1 point = 1/72 inch)
        "height" — page height in points
        "words"  — list of word objects from pdfplumber, each with the
                   keys: text, x0, top, x1, bottom (positions on the page)

    How it works:
        pdfplumber reads the internal structure of the PDF and extracts
        every word along with its bounding box — the rectangular region
        it occupies on the page. We collect these word objects page by page.

    Error handling:
        If the joined text of all words is empty, the PDF contains no
        machine-readable text. This happens with scanned documents (images
        of paper). We raise ValueError with a user-friendly message rather
        than silently returning empty results.

    Parameters:
        filepath — absolute or relative path to the PDF file

    Returns:
        list of page dicts, one per page

    Raises:
        ValueError   — PDF has no extractable text (likely a scanned image)
        Exception    — file not found, corrupted, or password-protected
    """
    pages: list[dict] = []

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            # extract_words groups individual characters into word tokens
            # and records each word's bounding box.
            # x_tolerance / y_tolerance control how far apart characters
            # can be and still be considered part of the same word.
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            pages.append({
                "width":  float(page.width),
                "height": float(page.height),
                "words":  words,
            })

    # If every page returned zero words, the PDF is image-based (scanned).
    all_text = " ".join(w["text"] for p in pages for w in p["words"]).strip()
    if not all_text:
        raise ValueError(
            "This PDF appears to be a scanned image. "
            "Text extraction failed. OCR support is not yet available."
        )

    return pages


# ==============================================================================
# SECTION 2 — NAME DETECTION
# Responsible for reading the extracted text and identifying which words
# are person names. Uses spaCy's pre-trained Named Entity Recognition (NER)
# model, which has learned to recognise names from millions of text examples.
# ==============================================================================

def detect_names(pages: list[dict]) -> Counter:
    """
    Scan every page of the document and return a frequency count of all
    detected person names.

    How it works:
        For each page, we join all the extracted words into a single text
        string and pass it to spaCy. spaCy's NER engine labels spans of
        text with entity types such as PERSON, ORG (organisation), GPE
        (country / city), etc. We keep only PERSON entities.

        The result is a Counter (a dict subclass) where:
            key   = name string exactly as it appeared in the document
            value = total number of times that name was detected

    Filtering:
        Names shorter than 2 characters or consisting only of digits are
        discarded — these are common NER false positives (e.g. a stray "A"
        or a year mis-tagged as a name).

    Parameters:
        pages — list of page dicts returned by extract_pdf_data()

    Returns:
        Counter mapping name strings to their occurrence count.
        Returns an empty Counter if no names are found.
    """
    counts: Counter = Counter()

    for page in pages:
        # Reconstruct the page text from individual word tokens.
        text = " ".join(w["text"] for w in page["words"])

        # _NLP processes the text through spaCy's NLP pipeline:
        # tokenisation → part-of-speech tagging → named entity recognition.
        doc = _NLP(text)

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                # Filter out trivially short or numeric false positives.
                if len(name) >= 2 and not name.isdigit():
                    counts[name] += 1

    return counts


# ==============================================================================
# SECTION 3 — REDACTION
# Responsible for building the redacted output PDF. This happens in two steps:
#   1. Build an "overlay" PDF in memory — a blank PDF that contains only the
#      black rectangles at every name location.
#   2. Stamp that overlay onto the original PDF page by page and save the
#      result as a new file. The original is never touched.
# ==============================================================================

def _find_words_to_redact(words: list[dict], names: set[str]) -> set[int]:
    """
    Given a page's word list and a set of name strings, return the set of
    word indices (positions in the `words` list) that fall inside any name.

    Why this approach:
        spaCy detected names inside a reconstructed text string. To place
        black boxes accurately we need to know which individual word objects
        from pdfplumber correspond to each name. We do this by:

        1. Building a lookup table: character_position → word_index
           using the same " ".join() text that spaCy saw. Every character
           in the joined string is mapped back to which word it came from.

        2. Searching for each name as a substring (case-insensitive).

        3. For every character position inside a match, looking up the
           corresponding word index and adding it to the result set.

        This correctly handles multi-word names ("John Smith" → words 0 and 1)
        and names that appear multiple times in the document.

    Parameters:
        words — list of pdfplumber word dicts for a single page
        names — set of name strings selected by the user for redaction

    Returns:
        Set of integer indices into `words` that should be blacked out.
    """
    if not words or not names:
        return set()

    # Step 1: build the character-to-word-index map.
    char_to_idx: dict[int, int] = {}
    pos = 0
    for i, w in enumerate(words):
        for j in range(len(w["text"])):
            char_to_idx[pos + j] = i
        pos += len(w["text"]) + 1  # +1 for the space that " ".join inserts

    joined       = " ".join(w["text"] for w in words)
    joined_lower = joined.lower()

    # Step 2 & 3: search for each name and collect matching word indices.
    hits: set[int] = set()
    for name in names:
        needle = name.lower()
        start  = 0
        while True:
            idx = joined_lower.find(needle, start)
            if idx == -1:
                break   # no more occurrences of this name on this page
            for ci in range(idx, idx + len(name)):
                if ci in char_to_idx:
                    hits.add(char_to_idx[ci])
            start = idx + 1  # advance by 1 to catch overlapping matches

    return hits


def build_redaction_overlay(pages: list[dict], names: set[str]) -> bytes:
    """
    Create a PDF in memory that contains only black rectangles — one for
    each word that is part of a name to be redacted, on each page.

    This "overlay" PDF is transparent everywhere except where the black
    boxes are drawn. It is later merged on top of the original document
    so that the original text and layout are preserved beneath the boxes.

    Coordinate system note:
        pdfplumber returns "top" and "bottom" as distances measured from
        the TOP of the page (larger values = further down the page).
        reportlab draws from the BOTTOM of the page (larger y = higher up).
        The conversion is:  reportlab_y = page_height - pdfplumber_bottom

    Parameters:
        pages — list of page dicts from extract_pdf_data()
        names — set of name strings that should be blacked out

    Returns:
        Raw bytes of a valid PDF file (the overlay), ready to be merged.
    """
    buf = io.BytesIO()          # build the PDF in RAM, not on disk
    c   = rl_canvas.Canvas(buf)
    c.setFillColorRGB(0, 0, 0)  # black fill colour for all rectangles

    for page in pages:
        c.setPageSize((page["width"], page["height"]))
        indices = _find_words_to_redact(page["words"], names)

        for i in indices:
            word = page["words"][i]

            # Convert pdfplumber coordinates to reportlab coordinates.
            x    = word["x0"]
            rl_y = page["height"] - word["bottom"]  # lower-left corner y
            w    = word["x1"] - word["x0"]
            h    = word["bottom"] - word["top"]

            # Add a small vertical padding (10% of character height) so the
            # black box fully covers ascenders (tall letters like "h", "l")
            # and descenders (letters like "g", "p" that dip below the line).
            pad = h * 0.1
            c.rect(x, rl_y - pad, w, h + 2 * pad, fill=1, stroke=0)

        c.showPage()  # finalise this page and start the next

    c.save()
    buf.seek(0)
    return buf.read()


def save_redacted_pdf(source: str, overlay: bytes, dest: str) -> None:
    """
    Merge the redaction overlay onto the original PDF and write the result
    to a new file. The source PDF is opened read-only and is never modified.

    How it works:
        pypdf reads both PDFs. For each page, it stamps the overlay page
        (which contains only the black boxes) on top of the original page.
        The merged pages are collected into a PdfWriter and written to dest.

    Parameters:
        source  — file path of the original (unredacted) PDF
        overlay — raw bytes of the overlay PDF from build_redaction_overlay()
        dest    — file path where the redacted PDF should be saved
    """
    reader         = PdfReader(source)
    overlay_reader = PdfReader(io.BytesIO(overlay))
    writer         = PdfWriter()

    for i, page in enumerate(reader.pages):
        # merge_page() draws the overlay content on top of the original page.
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)

    with open(dest, "wb") as f:
        writer.write(f)


# ==============================================================================
# SECTION 4 — GRAPHICAL USER INTERFACE
# The AnonymizerApp class builds and manages the application window.
# It inherits from tk.Tk (the main Tkinter window class) and uses a simple
# grid layout: file picker → summary label → names table → action buttons.
# ==============================================================================

class AnonymizerApp(tk.Tk):
    """
    Main application window.

    Instance state:
        _filepath    — full path of the currently selected PDF file, or None
        _pages       — page data returned by extract_pdf_data(), or None
        _name_counts — Counter of detected names, or None
        _items       — dict mapping treeview item id → (name_string, BooleanVar)
                       The BooleanVar tracks whether that name's row is checked.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Anonymizer")
        self.minsize(740, 560)
        self.resizable(True, True)

        # Application state — all None until the user selects and analyses a file.
        self._filepath:    str | None        = None
        self._pages:       list[dict] | None = None
        self._name_counts: Counter | None    = None
        self._items: dict[str, tuple[str, tk.BooleanVar]] = {}

        self._build_ui()

    # --------------------------------------------------------------------------
    # _build_ui
    # Creates every widget in the window and arranges them in a grid.
    # The grid has one column (index 0) that stretches horizontally (weight=1).
    # Row 3 (the names table) has weight=1 so it expands when the window
    # is resized vertically.
    # --------------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ── Row 0: File picker ─────────────────────────────────────────────
        # Three sub-columns: [Choose PDF button] [filename + path labels] [Analyze button]
        file_row = tk.Frame(self, padx=12, pady=10)
        file_row.grid(row=0, column=0, sticky="ew")
        file_row.columnconfigure(1, weight=1)

        tk.Button(file_row, text="Choose PDF", command=self._choose_file,
                  width=12).grid(row=0, column=0, padx=(0, 10))

        info = tk.Frame(file_row)
        info.grid(row=0, column=1, sticky="ew")
        info.columnconfigure(0, weight=1)

        # Filename shown in bold; directory path shown below in small gray text.
        self._filename_lbl = tk.Label(
            info, text="No file selected.", anchor="w",
            font=("TkDefaultFont", 11, "bold"),
        )
        self._filename_lbl.grid(row=0, column=0, sticky="ew")

        self._filepath_lbl = tk.Label(
            info, text="", anchor="w", fg="gray",
            font=("TkDefaultFont", 9),
        )
        self._filepath_lbl.grid(row=1, column=0, sticky="ew")

        # Analyze button is disabled until the user picks a file.
        self._analyze_btn = tk.Button(
            file_row, text="Analyze PDF", command=self._run_analysis,
            state="disabled", width=14,
        )
        self._analyze_btn.grid(row=0, column=2, padx=(10, 0))

        # ── Row 1: Horizontal separator line ──────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")

        # ── Row 2: Summary label ──────────────────────────────────────────
        # Shows "Found N instances of M unique names." after analysis,
        # or a "no names found" message.
        self._summary_lbl = tk.Label(self, text="", anchor="w", padx=12, pady=6)
        self._summary_lbl.grid(row=2, column=0, sticky="ew")

        # ── Row 3: Names table with scrollbar ─────────────────────────────
        # Three columns: checkbox symbol | name text | occurrence count.
        # Clicking any row toggles the checkbox (see _toggle_row).
        tbl_frame = tk.Frame(self, padx=12)
        tbl_frame.grid(row=3, column=0, sticky="nsew")
        tbl_frame.columnconfigure(0, weight=1)
        tbl_frame.rowconfigure(0, weight=1)

        cols = ("check", "name", "count")
        self._tree = ttk.Treeview(tbl_frame, columns=cols,
                                   show="headings", selectmode="browse")
        self._tree.heading("check", text="Redact")
        self._tree.heading("name",  text="Detected Name")
        self._tree.heading("count", text="Count")
        self._tree.column("check", width=60,  anchor="center", stretch=False)
        self._tree.column("name",  width=400, anchor="w")
        self._tree.column("count", width=70,  anchor="center", stretch=False)
        self._tree.bind("<ButtonRelease-1>", self._toggle_row)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ── Row 4: Bottom bar ─────────────────────────────────────────────
        # Left side: status text ("Reading PDF…", "Detecting names…", etc.)
        # Right side: Select All | Deselect All | Redact PDF buttons
        bottom = tk.Frame(self, padx=12, pady=10)
        bottom.grid(row=4, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self._status_lbl = tk.Label(bottom, text="", anchor="w", fg="gray")
        self._status_lbl.grid(row=0, column=0, sticky="ew")

        btns = tk.Frame(bottom)
        btns.grid(row=0, column=1)

        self._sel_all_btn = tk.Button(
            btns, text="Select All", command=self._select_all, state="disabled",
        )
        self._sel_all_btn.pack(side="left", padx=(0, 4))

        self._desel_all_btn = tk.Button(
            btns, text="Deselect All", command=self._deselect_all, state="disabled",
        )
        self._desel_all_btn.pack(side="left", padx=(0, 14))

        # The Redact button is red to signal it is a consequential action.
        # It is disabled until analysis finds at least one name.
        self._redact_btn = tk.Button(
            btns, text="Redact PDF", command=self._run_redaction,
            state="disabled", width=14,
            bg="#c0392b", fg="white",
            activebackground="#922b21", activeforeground="white",
        )
        self._redact_btn.pack(side="left")

    # --------------------------------------------------------------------------
    # _choose_file
    # Opens the operating system's standard file-picker dialog filtered to
    # PDF files. Stores the chosen path and resets all previous analysis
    # results so the UI is always consistent with the currently loaded file.
    # --------------------------------------------------------------------------

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return  # user cancelled the dialog — do nothing

        self._filepath = path
        # Display filename prominently and the directory path in small gray text.
        self._filename_lbl.config(text=os.path.basename(path))
        self._filepath_lbl.config(text=os.path.dirname(path))
        self._analyze_btn.config(state="normal")
        self._reset_analysis_state()

    # --------------------------------------------------------------------------
    # _run_analysis
    # Runs the two-stage analysis pipeline when the user clicks "Analyze PDF":
    #   Stage 1: extract_pdf_data() — read text and word positions from file
    #   Stage 2: detect_names()     — run spaCy NER to find person names
    # On success, populates the names table and enables the Redact button.
    # On any error, shows a user-friendly message dialog and stops cleanly.
    # --------------------------------------------------------------------------

    def _run_analysis(self) -> None:
        if not self._filepath:
            return

        self._reset_analysis_state()
        self._set_status("Reading PDF…")

        # Stage 1: extract text and word positions.
        try:
            self._pages = extract_pdf_data(self._filepath)
        except ValueError as exc:
            # ValueError means the PDF has no readable text (scanned image).
            self._set_status("")
            messagebox.showwarning("Cannot Read Text", str(exc))
            return
        except Exception as exc:
            # Any other error: corrupted file, wrong format, permissions, etc.
            self._set_status("")
            messagebox.showerror("Error", f"Failed to open PDF:\n{exc}")
            return

        # Stage 2: detect person names with spaCy NER.
        self._set_status("Detecting names…")
        try:
            self._name_counts = detect_names(self._pages)
        except Exception as exc:
            self._set_status("")
            messagebox.showerror("Error", f"Name detection failed:\n{exc}")
            return

        self._set_status("")

        if not self._name_counts:
            self._summary_lbl.config(
                text="No person names were detected in this document."
            )
            return

        # Show summary statistics and populate the table.
        total  = sum(self._name_counts.values())
        unique = len(self._name_counts)
        self._summary_lbl.config(
            text=(
                f"Found {total} instance{'s' if total != 1 else ''} of "
                f"{unique} unique name{'s' if unique != 1 else ''}. "
                "Uncheck any name to exclude it from redaction."
            )
        )
        self._populate_table()
        self._redact_btn.config(state="normal")
        self._sel_all_btn.config(state="normal")
        self._desel_all_btn.config(state="normal")

    # --------------------------------------------------------------------------
    # _run_redaction
    # Called when the user clicks "Redact PDF". Collects the set of names
    # whose checkboxes are ticked, generates the redacted PDF, and saves it.
    # Output filename: <original_basename>_anonymized.pdf in the same folder.
    # Shows a success dialog with the full output path on completion.
    # --------------------------------------------------------------------------

    def _run_redaction(self) -> None:
        # Collect only the names whose BooleanVar is True (checkbox ticked).
        selected = {name for (name, var) in self._items.values() if var.get()}
        if not selected:
            messagebox.showwarning("Nothing Selected",
                                    "No names are checked for redaction.")
            return

        # Build the output path: same directory, "_anonymized" suffix.
        base, _     = os.path.splitext(self._filepath)
        output_path = base + "_anonymized.pdf"

        self._set_status("Generating redacted PDF…")
        try:
            overlay = build_redaction_overlay(self._pages, selected)
            save_redacted_pdf(self._filepath, overlay, output_path)
        except Exception as exc:
            self._set_status("")
            messagebox.showerror("Redaction Failed", f"An error occurred:\n{exc}")
            return

        self._set_status("")
        messagebox.showinfo("Redaction Complete",
                             f"Saved redacted PDF to:\n{output_path}")

    # --------------------------------------------------------------------------
    # Table helpers — manage the names treeview
    # --------------------------------------------------------------------------

    def _populate_table(self) -> None:
        """
        Clear the treeview and fill it with the detected names, sorted from
        most frequent to least frequent (most_common() order).

        Each row stores a BooleanVar in self._items so we can read checkbox
        state without querying the widget for every row on every click.
        """
        self._tree.delete(*self._tree.get_children())
        self._items.clear()
        for i, (name, count) in enumerate(self._name_counts.most_common()):
            iid = str(i)
            var = tk.BooleanVar(value=True)   # all names checked by default
            self._items[iid] = (name, var)
            self._tree.insert("", "end", iid=iid, values=("☑", name, count))

    def _toggle_row(self, event: tk.Event) -> None:
        """
        Called on every mouse click in the table. Identifies the clicked row,
        flips its BooleanVar, and updates the ☑ / ☐ symbol in the first column.
        """
        iid = self._tree.identify_row(event.y)
        if not iid or iid not in self._items:
            return   # click was on a header or empty area — ignore
        name, var = self._items[iid]
        var.set(not var.get())
        symbol = "☑" if var.get() else "☐"
        count  = self._tree.item(iid, "values")[2]
        self._tree.item(iid, values=(symbol, name, count))

    def _select_all(self) -> None:
        """Set every row's checkbox to ticked (☑)."""
        for iid, (name, var) in self._items.items():
            var.set(True)
            count = self._tree.item(iid, "values")[2]
            self._tree.item(iid, values=("☑", name, count))

    def _deselect_all(self) -> None:
        """Set every row's checkbox to unticked (☐)."""
        for iid, (name, var) in self._items.items():
            var.set(False)
            count = self._tree.item(iid, "values")[2]
            self._tree.item(iid, values=("☐", name, count))

    def _reset_analysis_state(self) -> None:
        """
        Clear all analysis results and disable the action buttons.
        Called when a new file is selected or before re-running analysis,
        so the UI never shows results from a previous file.
        """
        self._pages       = None
        self._name_counts = None
        self._items.clear()
        self._tree.delete(*self._tree.get_children())
        self._summary_lbl.config(text="")
        self._status_lbl.config(text="")
        self._redact_btn.config(state="disabled")
        self._sel_all_btn.config(state="disabled")
        self._desel_all_btn.config(state="disabled")

    def _set_status(self, msg: str) -> None:
        """
        Update the status label at the bottom of the window.
        Calls update_idletasks() to force an immediate screen refresh —
        without this, Tkinter would wait until the current function returns
        before redrawing, so the "Reading PDF…" message would never be seen.
        """
        self._status_lbl.config(text=msg)
        self.update_idletasks()


# ==============================================================================
# ENTRY POINT
# main() is called when the script is run directly (python main.py).
# It checks that the spaCy model was loaded successfully before opening
# the window — if not, it prints a clear error with the fix command.
# ==============================================================================

def main() -> None:
    """Start the application. Exits immediately if the spaCy model is missing."""
    if _NLP is None:
        print(
            "ERROR: spaCy model 'en_core_web_sm' is not installed.\n"
            "Fix:   python -m spacy download en_core_web_sm"
        )
        raise SystemExit(1)

    app = AnonymizerApp()
    app.mainloop()  # hands control to Tkinter's event loop until window closes


if __name__ == "__main__":
    main()
