#!/usr/bin/env python3
"""
PDF Anonymizer
Detects person names in text-based PDFs and creates a redacted copy
with names covered by solid black rectangles.

Dependencies: pdfplumber, spacy (+ en_core_web_sm model), reportlab, pypdf
"""

import io
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import Counter

import pdfplumber
import spacy
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter

# Load the spaCy NER model once at startup.
# If the model is missing, _NLP stays None and main() exits with instructions.
try:
    _NLP = spacy.load("en_core_web_sm")
except OSError:
    _NLP = None


# ─── PDF text extraction ──────────────────────────────────────────────────────

def extract_pdf_data(filepath: str) -> list[dict]:
    """
    Open the PDF and return a list of per-page dicts, each with:
      width, height : page dimensions in points
      words         : list of pdfplumber word dicts
                      (keys: text, x0, top, x1, bottom)

    Raises ValueError when no text can be extracted (scanned / image-only PDF).
    """
    pages: list[dict] = []

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            pages.append({
                "width":  float(page.width),
                "height": float(page.height),
                "words":  words,
            })

    all_text = " ".join(w["text"] for p in pages for w in p["words"]).strip()
    if not all_text:
        raise ValueError(
            "This PDF appears to be a scanned image. "
            "Text extraction failed. OCR support is not yet available."
        )
    return pages


# ─── Name detection ───────────────────────────────────────────────────────────

def detect_names(pages: list[dict]) -> Counter:
    """
    Run spaCy NER on each page and return a Counter mapping each detected
    PERSON name to the number of times it appears across the whole document.
    """
    counts: Counter = Counter()

    for page in pages:
        text = " ".join(w["text"] for w in page["words"])
        doc = _NLP(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                # Skip single-character tokens and pure numbers (common NER errors)
                if len(name) >= 2 and not name.isdigit():
                    counts[name] += 1

    return counts


# ─── Redaction overlay ────────────────────────────────────────────────────────

def _find_words_to_redact(words: list[dict], names: set[str]) -> set[int]:
    """
    Return the set of indices into `words` that are part of any name in `names`.

    Strategy: build a character→word-index map over the page's joined text,
    then search for each name and collect the indices of all covered words.
    This correctly handles multi-word names and partial-token matches.
    """
    if not words or not names:
        return set()

    # Map each character position in the joined string back to a word index.
    char_to_idx: dict[int, int] = {}
    pos = 0
    for i, w in enumerate(words):
        for j in range(len(w["text"])):
            char_to_idx[pos + j] = i
        pos += len(w["text"]) + 1  # +1 accounts for the space " ".join inserts

    joined       = " ".join(w["text"] for w in words)
    joined_lower = joined.lower()

    hits: set[int] = set()
    for name in names:
        needle = name.lower()
        start  = 0
        while True:
            idx = joined_lower.find(needle, start)
            if idx == -1:
                break
            # Collect every word that this name span overlaps
            for ci in range(idx, idx + len(name)):
                if ci in char_to_idx:
                    hits.add(char_to_idx[ci])
            start = idx + 1  # allow overlapping matches

    return hits


def build_redaction_overlay(pages: list[dict], names: set[str]) -> bytes:
    """
    Build a PDF overlay (returned as raw bytes) containing only the black
    rectangles that need to be placed on top of each name occurrence.

    The overlay is later merged onto the original PDF so that all original
    content is preserved underneath the redaction boxes.
    """
    buf = io.BytesIO()
    c   = rl_canvas.Canvas(buf)
    c.setFillColorRGB(0, 0, 0)  # solid black fill

    for page in pages:
        c.setPageSize((page["width"], page["height"]))
        indices = _find_words_to_redact(page["words"], names)

        for i in indices:
            word = page["words"][i]
            x    = word["x0"]
            # pdfplumber "top"/"bottom" are distances from the TOP of the page.
            # reportlab measures y from the BOTTOM, so we invert.
            rl_y = page["height"] - word["bottom"]   # lower-left y in reportlab
            w    = word["x1"] - word["x0"]
            h    = word["bottom"] - word["top"]
            pad  = h * 0.1  # slight vertical padding to cover ascenders/descenders
            c.rect(x, rl_y - pad, w, h + 2 * pad, fill=1, stroke=0)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()


def save_redacted_pdf(source: str, overlay: bytes, dest: str) -> None:
    """
    Merge the redaction overlay onto every page of the source PDF
    and write the result to dest.

    The original file is never modified.
    """
    reader         = PdfReader(source)
    overlay_reader = PdfReader(io.BytesIO(overlay))
    writer         = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)

    with open(dest, "wb") as f:
        writer.write(f)


# ─── GUI ──────────────────────────────────────────────────────────────────────

class AnonymizerApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Anonymizer")
        self.minsize(740, 560)
        self.resizable(True, True)

        self._filepath:    str | None     = None
        self._pages:       list[dict] | None = None
        self._name_counts: Counter | None = None
        # Maps treeview item id → (name_string, BooleanVar)
        self._items: dict[str, tuple[str, tk.BooleanVar]] = {}

        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # table row stretches vertically

        # ── File picker ──────────────────────────────────────────────────────
        file_row = tk.Frame(self, padx=12, pady=10)
        file_row.grid(row=0, column=0, sticky="ew")
        file_row.columnconfigure(1, weight=1)

        tk.Button(file_row, text="Choose PDF", command=self._choose_file,
                  width=12).grid(row=0, column=0, padx=(0, 10))

        info = tk.Frame(file_row)
        info.grid(row=0, column=1, sticky="ew")
        info.columnconfigure(0, weight=1)

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

        self._analyze_btn = tk.Button(
            file_row, text="Analyze PDF", command=self._run_analysis,
            state="disabled", width=14,
        )
        self._analyze_btn.grid(row=0, column=2, padx=(10, 0))

        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")

        # ── Summary ───────────────────────────────────────────────────────────
        self._summary_lbl = tk.Label(self, text="", anchor="w", padx=12, pady=6)
        self._summary_lbl.grid(row=2, column=0, sticky="ew")

        # ── Names table ───────────────────────────────────────────────────────
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

        # ── Bottom bar ────────────────────────────────────────────────────────
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

        self._redact_btn = tk.Button(
            btns, text="Redact PDF", command=self._run_redaction,
            state="disabled", width=14,
            bg="#c0392b", fg="white",
            activebackground="#922b21", activeforeground="white",
        )
        self._redact_btn.pack(side="left")

    # ── File selection ────────────────────────────────────────────────────────

    def _choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        self._filepath = path
        self._filename_lbl.config(text=os.path.basename(path))
        self._filepath_lbl.config(text=os.path.dirname(path))
        self._analyze_btn.config(state="normal")
        self._reset_analysis_state()

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _run_analysis(self) -> None:
        if not self._filepath:
            return

        self._reset_analysis_state()
        self._set_status("Reading PDF…")

        try:
            self._pages = extract_pdf_data(self._filepath)
        except ValueError as exc:
            self._set_status("")
            messagebox.showwarning("Cannot Read Text", str(exc))
            return
        except Exception as exc:
            self._set_status("")
            messagebox.showerror("Error", f"Failed to open PDF:\n{exc}")
            return

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

    # ── Redaction ─────────────────────────────────────────────────────────────

    def _run_redaction(self) -> None:
        selected = {name for (name, var) in self._items.values() if var.get()}
        if not selected:
            messagebox.showwarning("Nothing Selected",
                                    "No names are checked for redaction.")
            return

        base, _      = os.path.splitext(self._filepath)
        output_path  = base + "_anonymized.pdf"

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

    # ── Table helpers ─────────────────────────────────────────────────────────

    def _populate_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._items.clear()
        for i, (name, count) in enumerate(self._name_counts.most_common()):
            iid = str(i)
            var = tk.BooleanVar(value=True)
            self._items[iid] = (name, var)
            self._tree.insert("", "end", iid=iid, values=("☑", name, count))

    def _toggle_row(self, event: tk.Event) -> None:
        """Toggle the redact checkbox when the user clicks any cell in a row."""
        iid = self._tree.identify_row(event.y)
        if not iid or iid not in self._items:
            return
        name, var = self._items[iid]
        var.set(not var.get())
        symbol = "☑" if var.get() else "☐"
        count  = self._tree.item(iid, "values")[2]
        self._tree.item(iid, values=(symbol, name, count))

    def _select_all(self) -> None:
        for iid, (name, var) in self._items.items():
            var.set(True)
            count = self._tree.item(iid, "values")[2]
            self._tree.item(iid, values=("☑", name, count))

    def _deselect_all(self) -> None:
        for iid, (name, var) in self._items.items():
            var.set(False)
            count = self._tree.item(iid, "values")[2]
            self._tree.item(iid, values=("☐", name, count))

    def _reset_analysis_state(self) -> None:
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
        self._status_lbl.config(text=msg)
        self.update_idletasks()  # force redraw so the label updates immediately


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    if _NLP is None:
        print(
            "ERROR: spaCy model 'en_core_web_sm' is not installed.\n"
            "Fix:   python -m spacy download en_core_web_sm"
        )
        raise SystemExit(1)

    app = AnonymizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
