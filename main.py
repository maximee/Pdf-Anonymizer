#!/usr/bin/env python3
"""
PDF Anonymizer — main.py
========================
Detects and redacts person names in text-based and scanned PDFs.

Features:
  • Interactive PDF viewer with real-time redaction preview
  • Manual text-selection tool (click text → blue highlight → export)
  • Rotation-aware redaction overlay
  • German false-positive filtering with 1–10 strictness slider

Run:
    python3 main.py

Required:
    pip install pdfplumber spacy reportlab pypdf easyocr pillow pypdfium2
    python -m spacy download en_core_web_sm
"""

import hashlib
import io
import os
import pickle
import tempfile
import threading
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox, ttk

import pdfplumber
import spacy
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageTk

try:
    import easyocr
    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False


# ==============================================================================
# SECTION 1 — CONSTANTS
# ==============================================================================

OCR_DPI          = 150   # render DPI for OCR processing
VIEWER_BASE_DPI  = 96    # render DPI for the interactive PDF viewer
MAX_CACHED_PAGES = 20    # max pages to keep in the viewer image cache
MIN_TEXT_WORDS   = 5     # pages below this word count → OCR path
LOW_CONF         = 0.50  # EasyOCR score below this → OCR quality warning
DEFAULT_STRICTNESS = 5   # default slider position (1 = permissive, 10 = strict)

FREQ_THRESHOLD_BALANCED = 20
FREQ_THRESHOLD_STRICT   = 15

GERMAN_LEGAL_NOUNS: frozenset[str] = frozenset({
    "gericht", "amtsgericht", "landgericht", "oberlandesgericht",
    "bundesgericht", "verfassungsgericht", "kammer", "senat", "instanz",
    "richter", "richterin", "anwalt", "anwältin", "rechtsanwalt",
    "rechtsanwältin", "staatsanwalt", "staatsanwältin", "notar", "notarin",
    "zeuge", "zeugin", "kläger", "klägerin", "beklagte", "beklagter",
    "antragsteller", "antragstellerin", "antragsgegner", "antragsgegnerin",
    "antrag", "beschluss", "urteil", "bescheid", "klage", "beschwerde",
    "revision", "berufung", "widerspruch", "einspruch", "verfahren",
    "rechtsstreit", "schriftsatz", "schreiben", "anlage", "beilage",
    "akte", "aktenzeichen", "protokoll", "niederschrift", "erklärung",
    "vollmacht", "vollmachten", "vertrag", "vereinbarung", "urkunde",
    "partei", "parteien", "gesellschaft", "unternehmen", "firma", "bank",
    "behörde", "amt", "ministerium", "verwaltung", "körperschaft",
    "gesetz", "artikel", "absatz", "paragraph", "satz", "ziffer",
    "abschnitt", "kapitel", "punkt", "nummer", "seite", "anlage",
    "datum", "unterschrift", "unterschriften", "beglaubigung",
    "sachverhalt", "begründung", "tenor", "entscheidung", "feststellung",
    "verfügung", "anordnung", "auflage", "bedingung", "frist",
    "zustellung", "bekanntmachung", "veröffentlichung",
    "herr", "herrn",
})

TITLE_WORDS: frozenset[str] = frozenset({
    "dr.", "dr", "prof.", "prof", "professor",
    "herr", "herrn", "frau",
    "mr.", "mr", "mrs.", "mrs", "ms.", "ms",
    "dipl.", "ing.", "mag.", "dres.",
    "rechtsanwalt", "rechtsanwältin",
    "anwalt", "anwältin",
    "richter", "richterin",
    "zeuge", "zeugin",
    "sachverständiger", "sachverständige",
    "bevollmächtigter", "bevollmächtigte",
    "angeklagter", "angeklagte",
    "kläger", "klägerin",
    "beklagter", "beklagte",
    "staatsanwalt", "staatsanwältin",
    "notar", "notarin",
    "antragsteller", "antragstellerin",
    "landrat", "bürgermeister", "bürgermeisterin",
    "senator", "senatorin",
    "abgeordneter", "abgeordnete",
})

TITLE_BASE: frozenset[str] = frozenset(t.rstrip(".") for t in TITLE_WORDS)

DEGREE_SUFFIXES: frozenset[str] = frozenset({
    "med.", "jur.", "phil.", "nat.", "rer.", "habil.",
    "h.c.", "i.r.", "a.d.", "e.h.",
})

GERMAN_ARTICLES: frozenset[str] = frozenset({
    "der", "die", "das", "dem", "den", "des",
    "ein", "eine", "einen", "einem", "einer", "eines",
    "von", "in", "zu", "bei", "mit", "nach", "seit",
    "über", "unter", "auf", "an", "für", "durch", "gegen",
})


# ==============================================================================
# SECTION 2 — MODEL SINGLETONS
# ==============================================================================

_NLP        = None
_OCR_READER = None

try:
    _NLP = spacy.load("en_core_web_sm")
except OSError:
    pass


def _get_ocr_reader() -> "easyocr.Reader":
    global _OCR_READER
    if _OCR_READER is None:
        if not _EASYOCR_AVAILABLE:
            raise RuntimeError("EasyOCR not installed. Run: pip install easyocr")
        _OCR_READER = easyocr.Reader(["en"], gpu=False)
    return _OCR_READER


# ==============================================================================
# SECTION 3 — OCR CACHING
# ==============================================================================

def _cache_key(filepath: str) -> str:
    return hashlib.md5(f"{filepath}:{os.path.getmtime(filepath)}".encode()).hexdigest()

def _cache_path(filepath: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"pdfanon_{_cache_key(filepath)}.pkl")

def _load_cache(filepath: str) -> list[dict] | None:
    try:
        with open(_cache_path(filepath), "rb") as f:
            return pickle.load(f)
    except Exception:
        return None

def _save_cache(filepath: str, pages: list[dict]) -> None:
    try:
        with open(_cache_path(filepath), "wb") as f:
            pickle.dump(pages, f)
    except Exception:
        pass


# ==============================================================================
# SECTION 4 — PAGE CLASSIFICATION
# ==============================================================================

def _classify_page(plumber_page) -> str:
    words = plumber_page.extract_words(x_tolerance=3, y_tolerance=3)
    return "text" if len(words) >= MIN_TEXT_WORDS else "ocr"


# ==============================================================================
# SECTION 5 — TEXT EXTRACTION  (pdfplumber)
# ==============================================================================

def _extract_text_words(plumber_page) -> list[dict]:
    return [
        {
            "text":       w["text"],
            "x0":         w["x0"],
            "top":        w["top"],
            "x1":         w["x1"],
            "bottom":     w["bottom"],
            "confidence": 1.0,
            "mode":       "text",
        }
        for w in plumber_page.extract_words(x_tolerance=3, y_tolerance=3)
    ]


# ==============================================================================
# SECTION 6 — OCR EXTRACTION  (pypdfium2 + EasyOCR)
# ==============================================================================

def _render_page(filepath: str, page_index: int, dpi: int = OCR_DPI) -> Image.Image:
    """Render a PDF page to an RGB PIL Image with pypdfium2."""
    doc    = pdfium.PdfDocument(filepath)
    page   = doc[page_index]
    bitmap = page.render(scale=dpi / 72.0, rotation=0)
    img    = bitmap.to_pil()
    doc.close()
    return img.convert("RGB") if img.mode != "RGB" else img


def _extract_ocr_words(
    filepath: str,
    page_index: int,
    vis_w_pts: float,
    vis_h_pts: float,
) -> list[dict]:
    img     = _render_page(filepath, page_index, OCR_DPI)
    scale_x = vis_w_pts / img.width
    scale_y = vis_h_pts / img.height

    reader  = _get_ocr_reader()
    buf     = io.BytesIO()
    img.save(buf, format="PNG")
    results = reader.readtext(buf.getvalue())

    words = []
    for bbox, text, conf in results:
        text = text.strip()
        if not text:
            continue
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        words.append({
            "text":       text,
            "x0":         min(xs) * scale_x,
            "top":        min(ys) * scale_y,
            "x1":         max(xs) * scale_x,
            "bottom":     max(ys) * scale_y,
            "confidence": float(conf),
            "mode":       "ocr",
        })
    return words


# ==============================================================================
# SECTION 7 — UNIFIED PDF DATA EXTRACTION
# ==============================================================================

def extract_pdf_data(
    filepath: str,
    progress_cb: callable = None,
    cancel_event: threading.Event = None,
) -> list[dict]:
    cached = _load_cache(filepath)
    if cached is not None:
        if progress_cb:
            progress_cb("Loaded from cache.")
        return cached

    pages:       list[dict] = []
    has_scanned: bool       = False

    with pdfplumber.open(filepath) as pdf:
        total = len(pdf.pages)
        for i, plumber_page in enumerate(pdf.pages):
            if cancel_event and cancel_event.is_set():
                break

            page_num = i + 1
            vis_w    = float(plumber_page.width)
            vis_h    = float(plumber_page.height)
            rotation = plumber_page.rotation or 0
            mode     = _classify_page(plumber_page)

            if progress_cb:
                tag = "text" if mode == "text" else "OCR — may take a minute"
                progress_cb(f"Processing page {page_num}/{total} [{tag}]…")

            if mode == "text":
                words = _extract_text_words(plumber_page)
            else:
                has_scanned = True
                if not _EASYOCR_AVAILABLE:
                    words, mode = [], "empty"
                else:
                    words = _extract_ocr_words(filepath, i, vis_w, vis_h)

            pages.append({
                "page_num": page_num,
                "width":    vis_w,
                "height":   vis_h,
                "rotation": rotation,
                "mode":     mode if words else "empty",
                "words":    words,
            })

    if not pages:
        raise ValueError("The PDF contains no pages.")

    all_text = " ".join(w["text"] for p in pages for w in p["words"]).strip()
    if not all_text:
        if has_scanned and not _EASYOCR_AVAILABLE:
            raise RuntimeError(
                "Scanned pages found but EasyOCR is not installed.\n"
                "Run: pip install easyocr"
            )
        raise ValueError(
            "No text could be extracted. If this is a scanned document, "
            "ensure EasyOCR is installed and try again."
        )

    if not (cancel_event and cancel_event.is_set()):
        _save_cache(filepath, pages)
    return pages


# ==============================================================================
# SECTION 8 — NAME DETECTION  (spaCy NER + German title-following detection)
# ==============================================================================

def _detect_title_following_names(words: list[dict]) -> list[tuple[str, list[int]]]:
    results: list[tuple[str, list[int]]] = []
    i = 0
    while i < len(words):
        wl = words[i]["text"].lower()
        if wl not in TITLE_WORDS and wl.rstrip(".") not in TITLE_BASE:
            i += 1
            continue
        j = i + 1
        while j < len(words):
            nw = words[j]["text"].lower()
            if nw in TITLE_WORDS or nw.rstrip(".") in TITLE_BASE or nw in DEGREE_SUFFIXES:
                j += 1
            else:
                break
        name_parts: list[str] = []
        name_indices: list[int] = []
        while j < len(words) and len(name_parts) < 3:
            wt  = words[j]["text"]
            wl2 = wt.lower()
            if not wt or not wt[0].isupper():
                break
            if wl2 in GERMAN_ARTICLES:
                break
            if wl2 in GERMAN_LEGAL_NOUNS:
                break
            if not any(c.isalpha() for c in wt):
                break
            name_parts.append(wt)
            name_indices.append(j)
            j += 1
        if name_parts:
            name = " ".join(name_parts)
            if len(name) >= 2 and not name.isdigit():
                results.append((name, name_indices))
        i += 1
    return results


def detect_names(pages: list[dict]) -> tuple[dict[str, dict], Counter]:
    word_counts: Counter = Counter(
        w["text"].lower() for p in pages for w in p["words"]
    )
    result: dict[str, dict] = {}

    for page in pages:
        words = page["words"]
        if not words:
            continue
        text = " ".join(w["text"] for w in words)
        doc  = _NLP(text)

        char_to_idx: dict[int, int] = {}
        pos = 0
        for i, w in enumerate(words):
            for j in range(len(w["text"])):
                char_to_idx[pos + j] = i
            pos += len(w["text"]) + 1

        page_names: dict[str, dict] = {}

        for ent in doc.ents:
            if ent.label_ != "PERSON":
                continue
            name = ent.text.strip()
            if len(name) < 2 or name.isdigit():
                continue
            tokens = name.split()
            start  = 0
            while start < len(tokens) and tokens[start].lower().rstrip(".") in TITLE_BASE:
                start += 1
            clean_name = " ".join(tokens[start:]).strip()
            if not clean_name:
                continue
            entity_has_title_prefix = (start > 0)

            w_indices = {
                char_to_idx[c]
                for c in range(ent.start_char, ent.end_char)
                if c in char_to_idx
            }
            min_conf = min((words[i]["confidence"] for i in w_indices), default=1.0)
            sources  = {words[i]["mode"] for i in w_indices}

            prev_text = doc[ent.start - 1].text if ent.start > 0 else ""
            follows_title = (
                entity_has_title_prefix
                or prev_text.lower() in TITLE_WORDS
                or prev_text.lower().rstrip(".") in TITLE_BASE
            )
            preceded_by_article = prev_text.lower() in GERMAN_ARTICLES
            name_tokens_lower    = {t.lower() for t in clean_name.split()}
            in_german_nouns      = bool(name_tokens_lower & GERMAN_LEGAL_NOUNS)
            is_multiword         = len(clean_name.split()) > 1

            if clean_name not in page_names:
                page_names[clean_name] = {
                    "count": 1, "min_confidence": min_conf,
                    "sources": sources, "follows_title": follows_title,
                    "preceded_by_article": preceded_by_article,
                    "in_german_nouns": in_german_nouns, "is_multiword": is_multiword,
                }
            else:
                pd = page_names[clean_name]
                pd["count"]               += 1
                pd["min_confidence"]       = min(pd["min_confidence"], min_conf)
                pd["sources"]             |= sources
                pd["follows_title"]       |= follows_title
                pd["preceded_by_article"] |= preceded_by_article

        for title_name, name_indices in _detect_title_following_names(words):
            if len(title_name) < 2 or title_name.isdigit():
                continue
            if title_name in page_names:
                page_names[title_name]["follows_title"] = True
                continue
            w_indices = set(name_indices)
            min_conf  = min((words[i]["confidence"] for i in w_indices), default=1.0)
            sources   = {words[i]["mode"] for i in w_indices}
            tl        = {t.lower() for t in title_name.split()}
            page_names[title_name] = {
                "count": 1, "min_confidence": min_conf, "sources": sources,
                "follows_title": True, "preceded_by_article": False,
                "in_german_nouns": bool(tl & GERMAN_LEGAL_NOUNS),
                "is_multiword": len(title_name.split()) > 1,
            }

        for name, pd in page_names.items():
            if name not in result:
                result[name] = {
                    "count": pd["count"], "min_confidence": pd["min_confidence"],
                    "low_confidence": pd["min_confidence"] < LOW_CONF,
                    "sources": pd["sources"], "is_multiword": pd["is_multiword"],
                    "follows_title": pd["follows_title"],
                    "preceded_by_article": pd["preceded_by_article"],
                    "in_german_nouns": pd["in_german_nouns"],
                    "name_confidence": "medium",
                }
            else:
                info    = result[name]
                new_min = min(info["min_confidence"], pd["min_confidence"])
                info["count"]               += pd["count"]
                info["min_confidence"]       = new_min
                info["low_confidence"]       = new_min < LOW_CONF
                info["sources"]             |= pd["sources"]
                info["follows_title"]       |= pd["follows_title"]
                info["preceded_by_article"] |= pd["preceded_by_article"]
                info["in_german_nouns"]     |= pd["in_german_nouns"]

    for name, info in result.items():
        info["name_confidence"] = _compute_name_confidence(name, info, word_counts)

    return result, word_counts


def _compute_name_confidence(name: str, info: dict, word_counts: Counter) -> str:
    if info["follows_title"] and not info["in_german_nouns"]:
        return "high"
    if info["in_german_nouns"]:
        return "low"
    doc_freq = word_counts.get(name.lower(), 0)
    if doc_freq > FREQ_THRESHOLD_BALANCED:
        return "low"
    if info["is_multiword"]:
        return "high"
    return "medium"


# ==============================================================================
# SECTION 9 — GERMAN FILTERING
# ==============================================================================

def filter_names(
    name_data: dict[str, dict],
    word_counts: Counter,
    strictness: int,
) -> dict[str, dict]:
    return {
        name: info
        for name, info in name_data.items()
        if _keep_name(name, info, word_counts, strictness)
    }


def _keep_name(name: str, info: dict, word_counts: Counter, strictness: int) -> bool:
    if info["follows_title"] and not info["in_german_nouns"]:
        return True
    if strictness <= 3:
        return True
    doc_freq = word_counts.get(name.lower(), 0)
    if strictness <= 6:
        if info["in_german_nouns"]:
            return False
        if doc_freq > FREQ_THRESHOLD_BALANCED:
            return False
        return True
    if info["in_german_nouns"]:
        return False
    if info["is_multiword"]:
        return True
    if info["count"] < 2:
        return False
    if doc_freq > FREQ_THRESHOLD_STRICT:
        return False
    return True


def _strictness_label(v: int) -> str:
    if v <= 3:
        return "Permissive"
    if v <= 6:
        return "Balanced"
    return "Strict"


# ==============================================================================
# SECTION 10 — WORD → REDACT INDEX MAPPING
# ==============================================================================

def _find_words_to_redact(words: list[dict], names: set[str]) -> set[int]:
    if not words or not names:
        return set()
    char_to_idx: dict[int, int] = {}
    pos = 0
    for i, w in enumerate(words):
        for j in range(len(w["text"])):
            char_to_idx[pos + j] = i
        pos += len(w["text"]) + 1
    joined       = " ".join(w["text"] for w in words)
    joined_lower = joined.lower()
    hits: set[int] = set()
    for name in names:
        needle, start = name.lower(), 0
        while True:
            idx = joined_lower.find(needle, start)
            if idx == -1:
                break
            for ci in range(idx, idx + len(name)):
                if ci in char_to_idx:
                    hits.add(char_to_idx[ci])
            start = idx + 1
    return hits


# ==============================================================================
# SECTION 11 — ROTATION UTILITIES
# ==============================================================================

def _raw_dims(vis_w: float, vis_h: float, rotation: int) -> tuple[float, float]:
    return (vis_h, vis_w) if rotation in (90, 270) else (vis_w, vis_h)


def _word_to_raw_rect(
    word: dict,
    vis_h: float,
    raw_w: float,
    raw_h: float,
    rotation: int,
) -> tuple[float, float, float, float]:
    x_l   = word["x0"]
    x_r   = word["x1"]
    y_top = vis_h - word["top"]
    y_bot = vis_h - word["bottom"]
    corners_vis = [(x_l, y_top), (x_r, y_top), (x_r, y_bot), (x_l, y_bot)]

    def to_raw(xv: float, yv: float) -> tuple[float, float]:
        if rotation == 0:   return xv, yv
        if rotation == 90:  return raw_w - yv, xv
        if rotation == 180: return raw_w - xv, raw_h - yv
        if rotation == 270: return yv, raw_h - xv
        return xv, yv

    corners_raw = [to_raw(x, y) for x, y in corners_vis]
    rxs = [c[0] for c in corners_raw]
    rys = [c[1] for c in corners_raw]
    x0 = min(rxs); y0 = min(rys)
    return x0, y0, max(rxs) - x0, max(rys) - y0


# ==============================================================================
# SECTION 12 — REDACTION OVERLAY  (rotation-aware, supports manual redactions)
# ==============================================================================

def build_redaction_overlay(
    pages: list[dict],
    names: set[str],
    manual_redactions: list[dict] | None = None,
) -> bytes:
    """
    Build a PDF overlay with black rectangles over name occurrences and any
    manually-selected words. manual_redactions items must have keys:
    page_num, x0, top, x1, bottom (visual-space coordinates).
    """
    buf = io.BytesIO()
    c   = rl_canvas.Canvas(buf)
    c.setFillColorRGB(0, 0, 0)

    manual_by_page: dict[int, list[dict]] = {}
    if manual_redactions:
        for mr in manual_redactions:
            manual_by_page.setdefault(mr["page_num"], []).append(mr)

    for page in pages:
        vis_w    = page["width"]
        vis_h    = page["height"]
        rotation = page.get("rotation", 0)
        raw_w, raw_h = _raw_dims(vis_w, vis_h, rotation)
        c.setPageSize((raw_w, raw_h))

        # Auto redactions from checked names
        for i in _find_words_to_redact(page["words"], names):
            word = page["words"][i]
            x, y, w, h = _word_to_raw_rect(word, vis_h, raw_w, raw_h, rotation)
            pad = h * 0.1
            c.rect(x, y - pad, w, h + 2 * pad, fill=1, stroke=0)

        # Manual redactions
        for mr in manual_by_page.get(page["page_num"], []):
            x, y, w, h = _word_to_raw_rect(mr, vis_h, raw_w, raw_h, rotation)
            pad = h * 0.1
            c.rect(x, y - pad, w, h + 2 * pad, fill=1, stroke=0)

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()


# ==============================================================================
# SECTION 13 — PDF OUTPUT
# ==============================================================================

def save_redacted_pdf(source: str, overlay: bytes, dest: str) -> None:
    reader         = PdfReader(source)
    overlay_reader = PdfReader(io.BytesIO(overlay))
    writer         = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[i])
        writer.add_page(page)
    with open(dest, "wb") as f:
        writer.write(f)


# ==============================================================================
# SECTION 14 — GUI
# ==============================================================================

class AnonymizerApp(tk.Tk):
    """
    Main window.  Layout (grid rows on self):
        0  toolbar  (file picker + analyze + select-mode button)
        1  separator
        2  main pane  [weight=1]  ←  viewer (left) + sidebar (right)
        3  separator
        4  bottom bar  (status + export controls)

    The sidebar is a fixed-width (~375 px) panel on the right containing:
        • Detected Names treeview
        • Filter-strictness slider + summary
        • Manual Redactions listbox

    Threading: analysis + redaction run on daemon threads;
    all GUI mutations go through self.after(0, ...).
    """

    # Discrete zoom levels; user can also get a non-discrete value from "Fit"
    ZOOM_LEVELS = [0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

    def __init__(self) -> None:
        super().__init__()
        self.title("PDF Anonymizer")
        self.minsize(1040, 680)
        self.resizable(True, True)

        # ── Analysis state ────────────────────────────────────────────────
        self._filepath:    str | None        = None
        self._pages:       list[dict] | None = None
        self._name_data:   dict | None       = None
        self._word_counts: Counter | None    = None
        self._items: dict[str, tuple[str, tk.BooleanVar]] = {}
        self._cancel_event  = threading.Event()
        self._filter_job_id = None
        self._strictness_var = tk.IntVar(value=DEFAULT_STRICTNESS)

        # ── Viewer state ─────────────────────────────────────────────────
        self._current_page: int   = 1
        self._total_pages:  int   = 0
        self._zoom:         float = 1.0
        self._page_cache: dict[int, Image.Image] = {}
        self._viewer_photo: ImageTk.PhotoImage | None = None
        self._pdfium_doc = None
        self._viewer_refresh_job = None

        # ── Select-mode state ─────────────────────────────────────────────
        self._select_mode: bool   = False
        self._manual_redactions: list[dict] = []

        self._build_ui()

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_toolbar()
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew")
        self._build_main_pane()
        ttk.Separator(self, orient="horizontal").grid(row=3, column=0, sticky="ew")
        self._build_bottom_bar()

    # ── Toolbar ──────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, padx=12, pady=8)
        bar.grid(row=0, column=0, sticky="ew")
        bar.columnconfigure(2, weight=1)

        tk.Button(bar, text="Choose PDF", command=self._choose_file,
                  width=12).grid(row=0, column=0, padx=(0, 6))

        self._analyze_btn = tk.Button(
            bar, text="Analyze PDF", command=self._start_analysis,
            state="disabled", width=13,
        )
        self._analyze_btn.grid(row=0, column=1, padx=(0, 12))

        # File info
        info = tk.Frame(bar)
        info.grid(row=0, column=2, sticky="ew")
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

        # Select-mode toggle
        self._select_btn = tk.Button(
            bar, text="✏  Select Text to Redact",
            command=self._toggle_select_mode,
            state="disabled", width=22,
        )
        self._select_btn.grid(row=0, column=3, padx=(12, 0))

    # ── Main pane (viewer + sidebar) ─────────────────────────────────────────

    def _build_main_pane(self) -> None:
        main = tk.Frame(self)
        main.grid(row=2, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(2, weight=0)
        main.rowconfigure(0, weight=1)

        self._build_viewer_panel(main)
        ttk.Separator(main, orient="vertical").grid(
            row=0, column=1, sticky="ns", padx=3)
        self._build_sidebar_panel(main)

    # ── PDF Viewer panel ─────────────────────────────────────────────────────

    def _build_viewer_panel(self, parent: tk.Frame) -> None:
        viewer = tk.Frame(parent)
        viewer.grid(row=0, column=0, sticky="nsew")
        viewer.columnconfigure(0, weight=1)
        viewer.rowconfigure(1, weight=1)

        # Controls row
        ctrl = tk.Frame(viewer, padx=8, pady=5)
        ctrl.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Page navigation
        self._prev_btn = tk.Button(
            ctrl, text="◀", command=self._prev_page,
            state="disabled", width=3, padx=2,
        )
        self._prev_btn.pack(side="left", padx=(0, 3))

        self._page_lbl = tk.Label(ctrl, text="— / —", width=10)
        self._page_lbl.pack(side="left")

        self._next_btn = tk.Button(
            ctrl, text="▶", command=self._next_page,
            state="disabled", width=3, padx=2,
        )
        self._next_btn.pack(side="left", padx=(3, 14))

        tk.Label(ctrl, text="Go to page:").pack(side="left", padx=(0, 4))
        self._jump_var   = tk.StringVar()
        self._jump_entry = tk.Entry(
            ctrl, textvariable=self._jump_var, width=5, state="disabled",
        )
        self._jump_entry.pack(side="left", padx=(0, 4))
        self._jump_entry.bind("<Return>", self._jump_to_page)

        tk.Button(ctrl, text="Go", command=self._jump_to_page,
                  width=4).pack(side="left", padx=(0, 18))

        # Zoom controls
        tk.Label(ctrl, text="Zoom:").pack(side="left", padx=(0, 4))
        self._zoom_out_btn = tk.Button(
            ctrl, text="−", command=self._zoom_out,
            state="disabled", width=2, padx=1,
        )
        self._zoom_out_btn.pack(side="left", padx=(0, 3))

        self._zoom_lbl = tk.Label(ctrl, text="100%", width=5)
        self._zoom_lbl.pack(side="left")

        self._zoom_in_btn = tk.Button(
            ctrl, text="+", command=self._zoom_in,
            state="disabled", width=2, padx=1,
        )
        self._zoom_in_btn.pack(side="left", padx=(3, 4))

        self._fit_btn = tk.Button(
            ctrl, text="Fit", command=self._fit_to_width,
            state="disabled", width=4,
        )
        self._fit_btn.pack(side="left", padx=(4, 0))

        # Canvas + scrollbars
        cf = tk.Frame(viewer)
        cf.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        cf.columnconfigure(0, weight=1)
        cf.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(cf, bg="#d0d0d0", cursor="arrow",
                                  highlightthickness=0)
        vsb = ttk.Scrollbar(cf, orient="vertical",   command=self._canvas.yview)
        hsb = ttk.Scrollbar(cf, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._canvas.bind("<Button-1>",   self._on_canvas_click)
        self._canvas.bind("<Configure>",  self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>",
            lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>",
            lambda e: self._canvas.yview_scroll(1,  "units"))

        self._show_viewer_placeholder()

    # ── Sidebar panel ─────────────────────────────────────────────────────────

    def _build_sidebar_panel(self, parent: tk.Frame) -> None:
        sb = tk.Frame(parent, width=378)
        sb.grid(row=0, column=2, sticky="nsew", padx=(0, 8), pady=8)
        sb.columnconfigure(0, weight=1)
        sb.rowconfigure(1, weight=3)   # tree
        sb.rowconfigure(8, weight=2)   # manual list
        sb.grid_propagate(False)

        # ── Detected Names ────────────────────────────────────────────────
        hdr1 = tk.Frame(sb)
        hdr1.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        hdr1.columnconfigure(0, weight=1)
        tk.Label(hdr1, text="Detected Names",
                 font=("TkDefaultFont", 10, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w")

        tree_frame = tk.Frame(sb)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("check", "name", "count", "conf", "source")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="browse")
        self._tree.heading("check",  text="✓")
        self._tree.heading("name",   text="Name")
        self._tree.heading("count",  text="#")
        self._tree.heading("conf",   text="Conf.")
        self._tree.heading("source", text="Src")
        self._tree.column("check",  width=30,  anchor="center", stretch=False)
        self._tree.column("name",   width=168, anchor="w")
        self._tree.column("count",  width=38,  anchor="center", stretch=False)
        self._tree.column("conf",   width=52,  anchor="center", stretch=False)
        self._tree.column("source", width=58,  anchor="center", stretch=False)
        self._tree.bind("<ButtonRelease-1>", self._toggle_row)

        self._tree.tag_configure("conf_high", foreground="#1a7a1a")
        self._tree.tag_configure("conf_med",  foreground="#b8860b")
        self._tree.tag_configure("conf_low",  foreground="#c0392b")

        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        tree_vsb.grid(row=0, column=1, sticky="ns")

        # ── Filter strictness ─────────────────────────────────────────────
        ttk.Separator(sb, orient="horizontal").grid(
            row=2, column=0, sticky="ew", pady=5)

        filt = tk.Frame(sb)
        filt.grid(row=3, column=0, sticky="ew")
        filt.columnconfigure(1, weight=1)

        tk.Label(filt, text="Filter strictness:", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 6))
        self._strictness_slider = ttk.Scale(
            filt, from_=1, to=10, orient="horizontal",
            variable=self._strictness_var,
            command=self._on_strictness_change,
        )
        self._strictness_slider.grid(row=0, column=1, sticky="ew")
        self._strictness_lbl = tk.Label(
            filt,
            text=f"{DEFAULT_STRICTNESS} — {_strictness_label(DEFAULT_STRICTNESS)}",
            width=14, anchor="w",
        )
        self._strictness_lbl.grid(row=0, column=2, padx=(6, 0))
        tk.Label(
            filt, text="1=loose  5=balanced  10=strict",
            fg="gray", font=("TkDefaultFont", 8),
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # Summary label
        self._summary_lbl = tk.Label(
            sb, text="", anchor="nw", justify="left",
            wraplength=358, fg="#444",
        )
        self._summary_lbl.grid(row=4, column=0, sticky="ew", pady=(4, 0))

        # ── Manual Redactions ─────────────────────────────────────────────
        ttk.Separator(sb, orient="horizontal").grid(
            row=5, column=0, sticky="ew", pady=6)

        hdr2 = tk.Frame(sb)
        hdr2.grid(row=6, column=0, sticky="ew", pady=(0, 3))
        hdr2.columnconfigure(0, weight=1)
        tk.Label(hdr2, text="Manual Redactions",
                 font=("TkDefaultFont", 10, "bold"), anchor="w").grid(
            row=0, column=0, sticky="w")
        self._clear_manual_btn = tk.Button(
            hdr2, text="Clear All",
            command=self._clear_manual_redactions,
            state="disabled", width=8,
        )
        self._clear_manual_btn.grid(row=0, column=1, padx=(4, 0))

        lf = tk.Frame(sb)
        lf.grid(row=7, column=0, sticky="nsew")  # NOTE: row 7 not 8; weight set below
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        # override: manual list at row 7
        sb.rowconfigure(7, weight=2)
        sb.rowconfigure(8, weight=0)

        self._manual_list = tk.Listbox(
            lf, selectmode="single", height=6,
            activestyle="dotbox", font=("TkDefaultFont", 9),
        )
        man_vsb = ttk.Scrollbar(lf, orient="vertical",
                                 command=self._manual_list.yview)
        self._manual_list.configure(yscrollcommand=man_vsb.set)
        self._manual_list.grid(row=0, column=0, sticky="nsew")
        man_vsb.grid(row=0, column=1, sticky="ns")

        self._remove_manual_btn = tk.Button(
            sb, text="Remove Selected",
            command=self._remove_selected_manual,
            state="disabled",
        )
        self._remove_manual_btn.grid(row=8, column=0, sticky="w", pady=(4, 0))

    # ── Bottom bar ────────────────────────────────────────────────────────────

    def _build_bottom_bar(self) -> None:
        bottom = tk.Frame(self, padx=12, pady=8)
        bottom.grid(row=4, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        left = tk.Frame(bottom)
        left.grid(row=0, column=0, sticky="ew")
        left.columnconfigure(0, weight=1)

        self._status_lbl = tk.Label(left, text="", anchor="w", fg="gray")
        self._status_lbl.grid(row=0, column=0, sticky="ew")
        self._progress = ttk.Progressbar(left, mode="indeterminate", length=280)

        btns = tk.Frame(bottom)
        btns.grid(row=0, column=1)

        self._cancel_btn = tk.Button(
            btns, text="Cancel", command=self._cancel_analysis,
            state="disabled", width=8,
        )
        self._cancel_btn.pack(side="left", padx=(0, 8))

        self._sel_all_btn = tk.Button(
            btns, text="Select All", command=self._select_all, state="disabled",
        )
        self._sel_all_btn.pack(side="left", padx=(0, 4))

        self._desel_all_btn = tk.Button(
            btns, text="Deselect All", command=self._deselect_all, state="disabled",
        )
        self._desel_all_btn.pack(side="left", padx=(0, 14))

        self._redact_btn = tk.Button(
            btns, text="Export Anonymized PDF",
            command=self._start_redaction,
            state="disabled", width=22,
            bg="#c0392b", fg="white",
            activebackground="#922b21", activeforeground="white",
        )
        self._redact_btn.pack(side="left")

    # =========================================================================
    # VIEWER — RENDERING
    # =========================================================================

    def _get_base_image(self, page_num: int) -> Image.Image:
        """Return cached base PIL image for the page (renders if needed)."""
        if page_num not in self._page_cache:
            if len(self._page_cache) >= MAX_CACHED_PAGES:
                self._page_cache.pop(next(iter(self._page_cache)))
            if self._pdfium_doc is None:
                return Image.new("RGB", (612, 792), color=(220, 220, 220))
            pg     = self._pdfium_doc[page_num - 1]
            bm     = pg.render(scale=VIEWER_BASE_DPI / 72.0, rotation=0)
            img    = bm.to_pil()
            self._page_cache[page_num] = (
                img.convert("RGB") if img.mode != "RGB" else img
            )
        return self._page_cache[page_num]

    def _render_viewer_image(self, page_num: int) -> Image.Image:
        """
        Build the display image for page_num at current zoom with overlay boxes:
        - Auto-redacted names  → opaque black  (solid preview)
        - Manual selections    → semi-transparent blue
        """
        base = self._get_base_image(page_num).copy()

        new_w = max(1, int(base.width  * self._zoom))
        new_h = max(1, int(base.height * self._zoom))
        img   = base.resize((new_w, new_h), Image.LANCZOS)

        if self._pages is None:
            return img

        # scale: PDF visual points → display pixels
        scale = (VIEWER_BASE_DPI / 72.0) * self._zoom

        overlay = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        page_data = self._pages[page_num - 1]
        words     = page_data["words"]

        # Auto redactions (black, mostly opaque)
        checked_names = {
            name for name, var in self._items.values() if var.get()
        }
        if checked_names:
            for i in _find_words_to_redact(words, checked_names):
                w   = words[i]
                pad = (w["bottom"] - w["top"]) * 0.1
                draw.rectangle(
                    [int(w["x0"] * scale),
                     int((w["top"]    - pad) * scale),
                     int(w["x1"] * scale),
                     int((w["bottom"] + pad) * scale)],
                    fill=(0, 0, 0, 220),
                )

        # Manual redactions (blue, semi-transparent)
        for mr in self._manual_redactions:
            if mr["page_num"] == page_num:
                draw.rectangle(
                    [int(mr["x0"]     * scale),
                     int(mr["top"]    * scale),
                     int(mr["x1"]     * scale),
                     int(mr["bottom"] * scale)],
                    fill=(30, 100, 220, 160),
                )

        result = Image.alpha_composite(img.convert("RGBA"), overlay)
        return result.convert("RGB")

    def _display_current_page(self) -> None:
        """Render and show the current page on the canvas."""
        self._viewer_refresh_job = None
        if not self._pages or self._pdfium_doc is None:
            return
        try:
            img   = self._render_viewer_image(self._current_page)
            photo = ImageTk.PhotoImage(img)
            self._viewer_photo = photo  # prevent GC
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            self._canvas.configure(scrollregion=(0, 0, img.width, img.height))
        except Exception as exc:
            self._canvas.delete("all")
            self._canvas.create_text(
                200, 150,
                text=f"Render error:\n{exc}",
                fill="red", font=("TkDefaultFont", 10),
            )

    def _trigger_viewer_refresh(self) -> None:
        """Debounced viewer refresh (80 ms) — avoids re-rendering on every keystroke."""
        if self._viewer_refresh_job is not None:
            self.after_cancel(self._viewer_refresh_job)
        self._viewer_refresh_job = self.after(80, self._display_current_page)

    def _show_viewer_placeholder(self) -> None:
        self._canvas.delete("all")
        w = max(self._canvas.winfo_width(),  200)
        h = max(self._canvas.winfo_height(), 120)
        self._canvas.create_text(
            w // 2, h // 2,
            text="Open a PDF and click  \"Analyze PDF\"  to begin.",
            fill="#999", font=("TkDefaultFont", 11),
            justify="center",
        )
        self._canvas.configure(scrollregion=(0, 0, w, h))

    # =========================================================================
    # VIEWER — NAVIGATION & ZOOM
    # =========================================================================

    def _goto_page(self, page_num: int) -> None:
        if not self._pages:
            return
        page_num = max(1, min(self._total_pages, page_num))
        if page_num == self._current_page:
            return
        self._current_page = page_num
        self._update_nav_controls()
        self._display_current_page()

    def _prev_page(self) -> None:
        self._goto_page(self._current_page - 1)

    def _next_page(self) -> None:
        self._goto_page(self._current_page + 1)

    def _jump_to_page(self, _event=None) -> None:
        try:
            self._goto_page(int(self._jump_var.get()))
        except ValueError:
            pass
        self._jump_var.set("")

    def _update_nav_controls(self) -> None:
        self._page_lbl.config(
            text=f"{self._current_page} / {self._total_pages}")
        self._prev_btn.config(
            state="normal" if self._current_page > 1 else "disabled")
        self._next_btn.config(
            state="normal" if self._current_page < self._total_pages else "disabled")

    def _zoom_in(self) -> None:
        new_idx = len(self.ZOOM_LEVELS) - 1
        for i, z in enumerate(self.ZOOM_LEVELS):
            if z > self._zoom + 0.01:
                new_idx = i
                break
        self._apply_zoom(self.ZOOM_LEVELS[new_idx])

    def _zoom_out(self) -> None:
        new_idx = 0
        for i in range(len(self.ZOOM_LEVELS) - 1, -1, -1):
            if self.ZOOM_LEVELS[i] < self._zoom - 0.01:
                new_idx = i
                break
        self._apply_zoom(self.ZOOM_LEVELS[new_idx])

    def _apply_zoom(self, zoom: float) -> None:
        self._zoom = max(0.1, min(4.0, zoom))
        self._zoom_lbl.config(text=f"{int(round(self._zoom * 100))}%")
        self._display_current_page()

    def _fit_to_width(self) -> None:
        if not self._pages:
            return
        self._canvas.update_idletasks()
        canvas_w = max(100, self._canvas.winfo_width() - 25)
        base_px_w = (
            self._pages[self._current_page - 1]["width"] * (VIEWER_BASE_DPI / 72.0)
        )
        self._apply_zoom(canvas_w / base_px_w)

    # =========================================================================
    # VIEWER — CANVAS EVENTS
    # =========================================================================

    def _on_canvas_configure(self, _event: tk.Event) -> None:
        if self._pages is None:
            self._show_viewer_placeholder()

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta > 0:
            self._canvas.yview_scroll(-1, "units")
        elif event.delta < 0:
            self._canvas.yview_scroll(1, "units")

    def _on_canvas_click(self, event: tk.Event) -> None:
        """In select-mode: identify word under cursor and add as manual redaction."""
        if not self._select_mode or not self._pages:
            return

        # canvas coords accounting for scroll
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)

        # convert display pixels → PDF visual points
        scale  = (VIEWER_BASE_DPI / 72.0) * self._zoom
        pdf_x  = cx / scale
        pdf_y  = cy / scale

        page_data = self._pages[self._current_page - 1]
        tol = 3.0  # tolerance in PDF points
        for i, word in enumerate(page_data["words"]):
            if (word["x0"] - tol <= pdf_x <= word["x1"]  + tol and
                    word["top"] - tol <= pdf_y <= word["bottom"] + tol):
                self._add_manual_redaction(self._current_page, i, word)
                return

    # =========================================================================
    # MANUAL REDACTIONS
    # =========================================================================

    def _toggle_select_mode(self) -> None:
        self._select_mode = not self._select_mode
        if self._select_mode:
            self._select_btn.config(
                text="⬛  Stop Selecting",
                bg="#c0392b", fg="white",
                activebackground="#922b21", activeforeground="white",
            )
            self._canvas.config(cursor="crosshair")
        else:
            self._select_btn.config(
                text="✏  Select Text to Redact",
                bg="SystemButtonFace",
                fg="SystemButtonText",
                activebackground="SystemButtonFace",
                activeforeground="SystemButtonText",
            )
            self._canvas.config(cursor="arrow")

    def _add_manual_redaction(self, page_num: int, word_idx: int, word: dict) -> None:
        # Deduplicate
        for mr in self._manual_redactions:
            if mr["page_num"] == page_num and mr["word_idx"] == word_idx:
                return
        self._manual_redactions.append({
            "page_num": page_num,
            "word_idx": word_idx,
            "text":     word["text"],
            "x0":       word["x0"],
            "top":      word["top"],
            "x1":       word["x1"],
            "bottom":   word["bottom"],
        })
        self._update_manual_list()
        self._display_current_page()

    def _remove_selected_manual(self) -> None:
        sel = self._manual_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if 0 <= idx < len(self._manual_redactions):
            del self._manual_redactions[idx]
            self._update_manual_list()
            self._display_current_page()

    def _clear_manual_redactions(self) -> None:
        self._manual_redactions.clear()
        self._update_manual_list()
        if self._pages:
            self._display_current_page()

    def _update_manual_list(self) -> None:
        self._manual_list.delete(0, "end")
        for mr in self._manual_redactions:
            self._manual_list.insert(
                "end", f"p.{mr['page_num']}: \"{mr['text']}\"")
        has = bool(self._manual_redactions)
        self._remove_manual_btn.config(state="normal" if has else "disabled")
        self._clear_manual_btn.config(state="normal"  if has else "disabled")

    # =========================================================================
    # FILE SELECTION
    # =========================================================================

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
        self._reset_state()

    # =========================================================================
    # ANALYSIS  (threaded)
    # =========================================================================

    def _start_analysis(self) -> None:
        if not self._filepath:
            return
        self._reset_state()
        self._cancel_event.clear()
        self._set_busy(True)
        self._set_status("Starting analysis…")
        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self) -> None:
        def progress(msg: str) -> None:
            self.after(0, self._set_status, msg)

        try:
            pages = extract_pdf_data(
                self._filepath,
                progress_cb=progress,
                cancel_event=self._cancel_event,
            )
        except (ValueError, RuntimeError) as exc:
            self.after(0, self._on_error, "warning", str(exc))
            return
        except Exception as exc:
            self.after(0, self._on_error, "error", f"Failed to read PDF:\n{exc}")
            return

        if self._cancel_event.is_set():
            self.after(0, self._on_cancelled)
            return

        progress("Detecting names…")
        try:
            name_data, word_counts = detect_names(pages)
        except Exception as exc:
            self.after(0, self._on_error, "error", f"Name detection failed:\n{exc}")
            return

        self.after(0, self._on_analysis_done, pages, name_data, word_counts)

    def _on_analysis_done(
        self, pages: list[dict], name_data: dict, word_counts: Counter
    ) -> None:
        self._pages       = pages
        self._name_data   = name_data
        self._word_counts = word_counts
        self._total_pages = len(pages)
        self._current_page = 1

        # Open pdfium document for viewer rendering
        if self._pdfium_doc is not None:
            self._pdfium_doc.close()
        self._page_cache.clear()
        self._pdfium_doc = pdfium.PdfDocument(self._filepath)

        self._set_busy(False)
        self._set_status("")

        # Enable viewer controls
        self._update_nav_controls()
        self._enable_viewer_controls(True)
        self._select_btn.config(state="normal")

        # Auto-fit first page
        self._fit_to_width()  # calls _display_current_page internally

        # Compute filtered names and populate sidebar
        strictness = self._strictness_var.get()
        filtered   = filter_names(name_data, word_counts, strictness)

        text_p  = sum(1 for p in pages if p["mode"] == "text")
        ocr_p   = sum(1 for p in pages if p["mode"] == "ocr")
        empty_p = sum(1 for p in pages if p["mode"] == "empty")
        rot_p   = sum(1 for p in pages if p.get("rotation", 0) != 0)
        mode_note = self._mode_note(len(pages), text_p, ocr_p, empty_p, rot_p)

        if not filtered:
            no_names_msg = "No person names detected"
            if name_data:
                no_names_msg += (
                    f" at strictness {strictness} "
                    f"({len(name_data)} hidden by filter)"
                )
            self._summary_lbl.config(text=f"{no_names_msg}. {mode_note}")
            return

        self._rebuild_summary(filtered, mode_note)
        self._populate_table(filtered)
        self._redact_btn.config(state="normal")
        self._sel_all_btn.config(state="normal")
        self._desel_all_btn.config(state="normal")

    def _rebuild_summary(self, filtered: dict, mode_note: str = "") -> None:
        total    = sum(d["count"] for d in filtered.values())
        unique   = len(filtered)
        low_ocr  = sum(1 for d in filtered.values() if d["low_confidence"])
        low_name = sum(1 for d in filtered.values() if d["name_confidence"] == "low")
        hidden   = len(self._name_data) - unique if self._name_data else 0

        lines = [
            f"Found {total} instance{'s' if total != 1 else ''} of "
            f"{unique} unique name{'s' if unique != 1 else ''}. {mode_note}"
        ]
        if hidden:
            lines.append(
                f"  {hidden} detection{'s' if hidden != 1 else ''} "
                "hidden by filter."
            )
        if low_name:
            lines.append(
                f"  {low_name} LOW-confidence name{'s' if low_name != 1 else ''} "
                "shown in red (unchecked by default)."
            )
        if low_ocr:
            lines.append(
                f"  {low_ocr} detection{'s' if low_ocr != 1 else ''} "
                "have low OCR quality."
            )
        self._summary_lbl.config(text="\n".join(lines))

    def _on_error(self, kind: str, msg: str) -> None:
        self._set_busy(False)
        self._set_status("")
        if kind == "warning":
            messagebox.showwarning("Cannot Process PDF", msg)
        else:
            messagebox.showerror("Error", msg)

    def _on_cancelled(self) -> None:
        self._set_busy(False)
        self._set_status("Analysis cancelled.")

    def _cancel_analysis(self) -> None:
        self._cancel_event.set()
        self._cancel_btn.config(state="disabled")
        self._set_status("Cancelling — finishing current page…")

    # =========================================================================
    # STRICTNESS SLIDER
    # =========================================================================

    def _on_strictness_change(self, val: str) -> None:
        v = int(float(val))
        self._strictness_lbl.config(text=f"{v} — {_strictness_label(v)}")
        if self._filter_job_id is not None:
            self.after_cancel(self._filter_job_id)
        self._filter_job_id = self.after(150, self._refresh_filtered_table)

    def _refresh_filtered_table(self) -> None:
        self._filter_job_id = None
        if self._name_data is None:
            return
        strictness = self._strictness_var.get()
        filtered   = filter_names(self._name_data, self._word_counts, strictness)
        if not filtered:
            self._tree.delete(*self._tree.get_children())
            self._items.clear()
            self._summary_lbl.config(
                text=f"No names at strictness {strictness}. Reduce to show more."
            )
            self._redact_btn.config(state="disabled")
            self._sel_all_btn.config(state="disabled")
            self._desel_all_btn.config(state="disabled")
            self._trigger_viewer_refresh()
            return
        self._rebuild_summary(filtered)
        self._populate_table(filtered)
        self._redact_btn.config(state="normal")
        self._sel_all_btn.config(state="normal")
        self._desel_all_btn.config(state="normal")
        self._trigger_viewer_refresh()

    # =========================================================================
    # REDACTION / EXPORT
    # =========================================================================

    def _start_redaction(self) -> None:
        selected = {name for (name, var) in self._items.values() if var.get()}
        if not selected and not self._manual_redactions:
            messagebox.showwarning(
                "Nothing Selected",
                "No names are checked and no text is manually selected.",
            )
            return

        base, _     = os.path.splitext(self._filepath)
        output_path = base + "_anonymized.pdf"

        self._set_status("Generating redacted PDF…")
        self._redact_btn.config(state="disabled")

        manual_snapshot = list(self._manual_redactions)

        def worker() -> None:
            try:
                overlay = build_redaction_overlay(
                    self._pages, selected, manual_snapshot)
                save_redacted_pdf(self._filepath, overlay, output_path)
                self.after(0, self._on_redaction_done, output_path)
            except Exception as exc:
                self.after(0, self._on_redaction_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_redaction_done(self, path: str) -> None:
        self._set_status("")
        self._redact_btn.config(state="normal")
        messagebox.showinfo("Export Complete",
                             f"Saved anonymized PDF to:\n{path}")

    def _on_redaction_error(self, msg: str) -> None:
        self._set_status("")
        self._redact_btn.config(state="normal")
        messagebox.showerror("Export Failed", f"An error occurred:\n{msg}")

    # =========================================================================
    # NAME TABLE
    # =========================================================================

    def _populate_table(self, filtered: dict) -> None:
        self._tree.delete(*self._tree.get_children())
        self._items.clear()

        for i, (name, info) in enumerate(
            sorted(filtered.items(), key=lambda kv: kv[1]["count"], reverse=True)
        ):
            iid     = str(i)
            nc      = info["name_confidence"]
            low_ocr = info["low_confidence"]
            checked = nc != "low" and not low_ocr
            var     = tk.BooleanVar(value=checked)
            self._items[iid] = (name, var)

            symbol    = "☑" if checked else "☐"
            conf_text = {"high": "HIGH", "medium": "MED", "low": "LOW"}.get(nc, "MED")
            if "ocr" in info.get("sources", set()):
                source = "OCR ⚠" if low_ocr else "OCR ✓"
            else:
                source = ""

            tag = f"conf_{nc if nc in ('high', 'low') else 'med'}"
            self._tree.insert(
                "", "end", iid=iid,
                values=(symbol, name, info["count"], conf_text, source),
                tags=(tag,),
            )

        self._trigger_viewer_refresh()

    def _toggle_row(self, event: tk.Event) -> None:
        iid = self._tree.identify_row(event.y)
        if not iid or iid not in self._items:
            return
        _, var = self._items[iid]
        var.set(not var.get())
        symbol = "☑" if var.get() else "☐"
        vals = self._tree.item(iid, "values")
        self._tree.item(iid, values=(symbol, vals[1], vals[2], vals[3], vals[4]))
        self._trigger_viewer_refresh()

    def _select_all(self) -> None:
        for iid, (_, var) in self._items.items():
            var.set(True)
            vals = self._tree.item(iid, "values")
            self._tree.item(iid, values=("☑", vals[1], vals[2], vals[3], vals[4]))
        self._trigger_viewer_refresh()

    def _deselect_all(self) -> None:
        for iid, (_, var) in self._items.items():
            var.set(False)
            vals = self._tree.item(iid, "values")
            self._tree.item(iid, values=("☐", vals[1], vals[2], vals[3], vals[4]))
        self._trigger_viewer_refresh()

    # =========================================================================
    # STATE HELPERS
    # =========================================================================

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self._analyze_btn.config(state="disabled")
            self._cancel_btn.config(state="normal")
            self._redact_btn.config(state="disabled")
            self._sel_all_btn.config(state="disabled")
            self._desel_all_btn.config(state="disabled")
            self._select_btn.config(state="disabled")
            self._enable_viewer_controls(False)
            self._progress.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self._progress.start(12)
        else:
            self._analyze_btn.config(
                state="normal" if self._filepath else "disabled")
            self._cancel_btn.config(state="disabled")
            self._progress.stop()
            self._progress.grid_forget()

    def _enable_viewer_controls(self, enabled: bool) -> None:
        st = "normal" if enabled else "disabled"
        self._next_btn.config(state=st)
        self._prev_btn.config(state=st)
        self._jump_entry.config(state=st)
        self._zoom_in_btn.config(state=st)
        self._zoom_out_btn.config(state=st)
        self._fit_btn.config(state=st)
        if enabled:
            self._update_nav_controls()

    def _reset_state(self) -> None:
        # Close pdfium document
        if self._pdfium_doc is not None:
            self._pdfium_doc.close()
            self._pdfium_doc = None
        self._page_cache.clear()

        self._pages       = None
        self._name_data   = None
        self._word_counts = None
        self._total_pages = 0
        self._current_page = 1
        self._zoom = 1.0
        self._zoom_lbl.config(text="100%")

        # Clear manual state
        self._manual_redactions.clear()
        self._update_manual_list()
        if self._select_mode:
            self._toggle_select_mode()

        self._items.clear()
        self._tree.delete(*self._tree.get_children())
        self._summary_lbl.config(text="")
        self._status_lbl.config(text="")
        self._redact_btn.config(state="disabled")
        self._sel_all_btn.config(state="disabled")
        self._desel_all_btn.config(state="disabled")
        self._select_btn.config(state="disabled")

        self._page_lbl.config(text="— / —")
        self._enable_viewer_controls(False)
        self._viewer_photo = None
        self._show_viewer_placeholder()

    def _set_status(self, msg: str) -> None:
        self._status_lbl.config(text=msg)
        self.update_idletasks()

    @staticmethod
    def _mode_note(
        total: int, text: int, ocr: int, empty: int, rotated: int
    ) -> str:
        parts = []
        if text:  parts.append(f"{text} text")
        if ocr:   parts.append(f"{ocr} scanned/OCR")
        if empty: parts.append(f"{empty} unreadable")
        noun = "page" if total == 1 else "pages"
        s = (f"({total} {noun}: {' + '.join(parts)})"
             if parts else f"({total} {noun})")
        if rotated:
            s += f" [{rotated} rotated page{'s' if rotated != 1 else ''}]"
        return s


# ==============================================================================
# SECTION 15 — ENTRY POINT
# ==============================================================================

def main() -> None:
    if _NLP is None:
        print(
            "ERROR: spaCy model 'en_core_web_sm' is not installed.\n"
            "Fix:   python -m spacy download en_core_web_sm"
        )
        raise SystemExit(1)
    AnonymizerApp().mainloop()


if __name__ == "__main__":
    main()
