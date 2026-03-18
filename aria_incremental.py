#!/usr/bin/env python3
"""
aria_incremental.py — Incremental Spherical Knowledge Indexer
Srishti DB v1.0 — Add new files without rebuilding

Spherical Coordinate Database — Dr. K.S. Venkatesh
Code: Dr. K.S. Venkatesh + Claude (SI)
License: GNU GPL 3.0 — free for all, profit for none

Scans a folder and adds ONLY new files to srishti3.db.
Files already in DB are skipped — no duplicates, no rebuilds.
Existing spherical coordinates are never changed.

Usage:
    python3 aria_incremental.py /path/to/new/folder
    python3 aria_incremental.py /path/to/folder --db ~/srishti3.db
    python3 aria_incremental.py --stats
"""

import os
import re
import sys
import math
import sqlite3
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── GOLDEN RATIO ──────────────────────────────────────────────────────────────
PHI = (1 + math.sqrt(5)) / 2

# ── DEFAULT DB ────────────────────────────────────────────────────────────────
DEFAULT_DB = str(Path.home() / "srishti3.db")

# ── DOMAIN REGISTRY — must match aria_setup.py exactly ──────────────────────
DOMAINS = [
    "physics",            # r(1)
    "chemistry",          # r(2)
    "biology",            # r(3)
    "mathematics",        # r(4)
    "science_fiction",    # r(5)
    "fantasy",            # r(6)
    "pictures_paintings", # r(7)
    "medicine",           # r(8)
    "religion",           # r(9)
    "philosophy",         # r(10)
    "history",            # r(11)
    "geography",          # r(12)
    "music",              # r(13)
    "computer_science",   # r(14)
    "astrology",          # r(15)
    "electronics",        # r(16)
    "fiction",            # r(17)
    "engineering_technology", # r(18)
    "languages",          # r(19)
]

DOMAIN_R = {domain: PHI ** (i + 1) for i, domain in enumerate(DOMAINS)}

# ── DOMAIN HINTS ─────────────────────────────────────────────────────────────
DOMAIN_HINTS = {
    "physics": [
        "physics", "quantum", "relativity", "mechanics", "thermodynamics",
        "electrodynamics", "feynman", "einstein", "maxwell", "optics",
        "spacetime", "cosmology", "astronomy", "astrophysics", "nuclear",
        "particle", "atomic", "plasma", "condensed", "fluid", "acoustic",
        "gravitation", "radiation", "boltzmann", "entropy", "photon",
        "heisenberg", "schrodinger", "dirac", "bohr", "planck",
    ],
    "chemistry": [
        "chemistry", "organic", "inorganic", "molecule", "reaction",
        "periodic", "element", "compound", "bonding", "acid", "base",
        "polymer", "electrochemistry", "spectroscopy", "chromatography",
        "biochemistry", "thermochemistry", "kinetics", "catalyst",
        "oxidation", "reduction", "valence", "orbital", "isotope",
    ],
    "biology": [
        "biology", "genetics", "cell", "evolution", "dna", "rna",
        "protein", "enzyme", "metabolism", "neuron", "ecology",
        "taxonomy", "botany", "zoology", "microbiology", "virus",
        "bacteria", "immune", "embryo", "genome", "species",
        "photosynthesis", "mitosis", "chromosome", "mutation",
    ],
    "mathematics": [
        "mathematics", "math", "algebra", "calculus", "geometry",
        "theorem", "equation", "topology", "statistics", "probability",
        "number", "function", "integral", "derivative", "matrix",
        "vector", "tensor", "differential", "analysis", "logic",
        "prime", "fibonacci", "fourier", "laplace", "euler",
    ],
    "science_fiction": [
        "scifi", "asimov", "clarke", "heinlein", "philip dick",
        "le guin", "iain banks", "cyberpunk", "dystopia", "spaceship",
        "alien", "robot", "androids", "foundation", "dune", "hyperion",
        "culture", "ringworld", "neuromancer", "blade runner",
    ],
    "fantasy": [
        "fantasy", "tolkien", "jordan", "pratchett", "eddings", "feist",
        "sanderson", "martin", "dragonlance", "forgotten realms",
        "discworld", "malazan", "wizard", "dragon", "magic", "hobbit",
        "rings", "belgarath", "wheel of time", "mistborn",
    ],
    "pictures_paintings": [
        "painting", "art", "illustration", "photography", "renaissance",
        "impressionism", "baroque", "cubism", "surrealism", "sketch",
        "watercolour", "portrait", "landscape", "gallery", "museum",
        "davinci", "picasso", "monet", "rembrandt", "tanjore",
    ],
    "medicine": [
        "medicine", "anatomy", "physiology", "pathology", "pharmacology",
        "surgery", "cardiology", "neurology", "psychiatry", "psychology",
        "oncology", "ayurveda", "acupuncture", "clinical", "disease",
        "therapy", "drug", "health", "diagnosis", "treatment",
        "ligament", "nerve", "muscle", "organ", "tissue",
        "freud", "jung", "cognitive", "behaviour", "mental",
    ],
    "religion": [
        "religion", "hinduism", "vedanta", "buddhism", "christianity",
        "islam", "judaism", "sikhism", "jainism", "taoism", "shinto",
        "vedas", "upanishad", "gita", "quran", "bible", "torah",
        "krishna", "shiva", "vishnu", "allah", "jesus", "buddha",
        "mantra", "tantra", "yoga", "meditation", "spiritual",
    ],
    "philosophy": [
        "philosophy", "metaphysics", "epistemology", "ethics",
        "consciousness", "ontology", "logic", "aesthetics",
        "existentialism", "phenomenology", "stoicism", "vedanta",
        "advaita", "kant", "hegel", "nietzsche", "plato", "aristotle",
        "schopenhauer", "wittgenstein", "descartes", "spinoza",
    ],
    "history": [
        "history", "ancient", "civilization", "medieval", "empire",
        "war", "revolution", "archaeology", "dynasty", "colonial",
        "renaissance", "byzantine", "mughal", "roman", "greek",
        "egyptian", "persian", "viking", "crusade", "independence",
        "majumdar", "nehru", "gandhi", "churchill", "napoleon",
    ],
    "geography": [
        "geography", "geomorphology", "climate", "ocean", "river",
        "mountain", "continent", "country", "region", "cartography",
        "map", "terrain", "geology", "plate", "tectonic", "volcano",
        "glacier", "ecosystem", "biome", "weather", "atmosphere",
    ],
    "music": [
        "music", "carnatic", "hindustani", "classical", "symphony",
        "opera", "jazz", "blues", "folk", "soundtrack", "melody",
        "harmony", "rhythm", "composition", "instrument", "orchestra",
        "yanni", "vangelis", "kitaro", "beethoven", "mozart", "bach",
    ],
    "computer_science": [
        "python", "javascript", "programming", "algorithm", "database",
        "linux", "software", "code", "network", "artificial intelligence",
        "machine learning", "neural", "compiler", "operating system",
        "function", "class", "data structure", "recursion", "binary",
        "internet", "server", "client", "api", "framework",
    ],
    "astrology": [
        "astrology", "jyotish", "horoscope", "kundali", "nakshatra",
        "rashi", "dasha", "graha", "transit", "panchanga", "muhurta",
        "vedic astrology", "zodiac", "ascendant", "planet", "house",
        "aspect", "conjunction", "numerology", "tarot",
    ],
    "electronics": [
        "electronics", "circuit", "transistor", "diode", "mosfet",
        "arduino", "raspberry", "microcontroller", "voltage", "current",
        "resistor", "capacitor", "inductor", "amplifier", "filter",
        "signal", "digital", "analog", "pcb", "semiconductor",
        "oscillator", "modulation", "frequency", "impedance",
    ],
    "fiction": [
        "fiction", "novel", "story", "adventure", "detective", "crime",
        "thriller", "mystery", "horror", "sherlock", "holmes", "doyle",
        "christie", "poirot", "cussler", "clancy", "grisham",
        "hemingway", "dickens", "hardy", "wodehouse", "jeeves",
        "jean auel", "clan", "cave bear",
    ],
    "engineering_technology": [
        "engineering", "mechanical", "civil", "structural", "aerospace",
        "materials", "manufacturing", "fabrication", "construction",
        "thermodynamics", "fluid", "control", "robotics", "nanotechnology",
        "biomedical", "industrial", "systems", "telecommunications",
        "power", "turbine", "bridge", "beam", "stress", "strain",
    ],
    "languages": [
        "grammar", "language", "linguistics", "vocabulary", "dictionary",
        "thesaurus", "etymology", "phonetics", "semantics", "syntax",
        "russian", "sanskrit", "tamil", "hindi", "latin", "greek",
        "arabic", "french", "german", "spanish", "portuguese",
        "japanese", "mandarin", "translation", "lexicon", "morphology",
    ],
}

# ── FILE EXTENSION PHI VALUES ─────────────────────────────────────────────────
EXT_PHI = {
    ".txt": 1.0, ".text": 1.5, ".md": 2.0, ".rst": 2.5,
    ".pdf": 10.0, ".doc": 11.0, ".docx": 12.0, ".odt": 13.0, ".rtf": 14.0,
    ".epub": 20.0, ".lit": 21.0, ".mobi": 22.0, ".azw": 23.0,
    ".azw3": 24.0, ".fb2": 25.0,
    ".html": 30.0, ".htm": 30.5, ".xml": 31.0, ".json": 32.0,
    ".py": 40.0, ".js": 41.0, ".c": 42.0, ".cpp": 43.0,
    ".h": 44.0, ".java": 45.0, ".sh": 46.0, ".bash": 46.5,
    ".csv": 50.0, ".tsv": 51.0, ".sql": 52.0,
    ".jpg": 60.0, ".jpeg": 60.5, ".png": 61.0, ".gif": 62.0,
    ".bmp": 63.0, ".svg": 64.0, ".tiff": 65.0, ".webp": 66.0,
    ".mp3": 70.0, ".wav": 71.0, ".flac": 72.0, ".ogg": 73.0,
    ".m4a": 74.0, ".aac": 75.0,
    ".mp4": 80.0, ".mkv": 81.0, ".avi": 82.0, ".mov": 83.0,
    ".wmv": 84.0, ".webm": 85.0,
    ".chm": 90.0, ".djvu": 91.0,
    ".zip": 100.0, ".tar": 101.0, ".gz": 102.0, ".7z": 103.0, ".rar": 104.0,
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
    ".db", ".db-wal", ".db-shm", ".sqlite",
    ".tmp", ".temp", ".bak", ".swp",
}

SKIP_NAMES = {
    "desktop.ini", "thumbs.db", "albumart.jpg",
    "folder.jpg", "folder.png", "cover.jpg", "cover.png",
    "metadata.opf", ".gitignore",
}

STOP = {
    "the", "and", "for", "are", "you", "can", "show", "what", "how",
    "have", "this", "that", "with", "from", "all", "any", "give",
    "about", "tell", "some", "when", "where", "was", "who", "which",
    "will", "been", "they", "their", "also", "more", "then", "than",
    "into", "your", "our", "its", "but", "not", "had", "has", "did",
    "does", "her", "him", "his", "she", "were", "would", "could",
    "should", "may", "might", "media", "data", "home", "local",
    "http", "https", "www", "com", "org", "net", "html", "file",
    "path", "folder", "drive", "disk", "true", "false", "none",
    "null", "self", "args", "return", "def", "class", "import",
}

READABLE_EXT = {
    ".txt", ".text", ".md", ".rst", ".html", ".htm",
    ".py", ".js", ".c", ".cpp", ".h", ".sh", ".bash",
    ".csv", ".json", ".xml", ".sql",
}

MAX_CONTENT_CHARS = 2000

# ── THETA CACHE ───────────────────────────────────────────────────────────────
_theta_cache = {}
_theta_counter = {}


# ── HELPERS ───────────────────────────────────────────────────────────────────
def extract_keywords(text, limit=10):
    if not text:
        return []
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    words = [w for w in words if w not in STOP]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]]


def read_file_content(filepath, max_chars=MAX_CONTENT_CHARS):
    ext = Path(filepath).suffix.lower()
    if ext not in READABLE_EXT:
        return ""
    try:
        with open(filepath, "r", errors="ignore", encoding="utf-8") as f:
            return f.read(max_chars).strip()
    except Exception:
        return ""


def classify_domain(path, name, content=""):
    text = (path + " " + name + " " + content).lower()
    scores = {}
    for domain, hints in DOMAIN_HINTS.items():
        score = sum(1 for hint in hints if hint in text)
        if score > 0:
            scores[domain] = score
    if not scores:
        return "fiction", 0.3
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(scores[best] / max(total, 1), 3)
    return best, confidence


def classify_subdomain(domain, path, name, content=""):
    text = (path + " " + name + " " + content).lower()

    subdomain_hints = {
        "physics": {
            "thermodynamics": ["thermo", "heat", "entropy", "boltzmann", "carnot"],
            "quantum_mechanics": ["quantum", "schrodinger", "heisenberg", "wave function"],
            "electrodynamics": ["electro", "maxwell", "electromagnetic", "gauss"],
            "relativity": ["relativity", "einstein", "spacetime", "lorentz"],
            "astrophysics": ["astro", "star", "galaxy", "nebula", "pulsar"],
            "cosmology": ["cosmology", "universe", "big bang", "hubble", "cosmic"],
            "mechanics": ["mechanics", "newton", "force", "motion", "velocity"],
            "optics": ["optics", "light", "lens", "refraction", "laser"],
            "nuclear_physics": ["nuclear", "fission", "fusion", "radioactive"],
        },
        "chemistry": {
            "organic_chemistry": ["organic", "carbon", "hydrocarbon", "alkane", "benzene"],
            "inorganic_chemistry": ["inorganic", "metal", "salt", "oxide"],
            "biochemistry": ["biochem", "protein", "enzyme", "atp", "glucose"],
            "physical_chemistry": ["physical", "thermochem", "kinetics", "equilibrium"],
            "analytical_chemistry": ["analytical", "titration", "spectroscopy"],
        },
        "medicine": {
            "anatomy": ["anatomy", "bone", "muscle", "organ", "skeletal"],
            "physiology": ["physiology", "function", "system", "homeostasis"],
            "pharmacology": ["drug", "pharmacology", "dose", "receptor"],
            "psychology": ["psychology", "behaviour", "cognitive", "freud", "jung"],
            "ayurveda": ["ayurveda", "vata", "pitta", "kapha", "dosha"],
            "neurology": ["neuro", "brain", "nerve", "synapse", "cortex"],
            "surgery": ["surgery", "surgical", "operation", "procedure"],
        },
        "mathematics": {
            "calculus": ["calculus", "integral", "derivative", "differential"],
            "algebra": ["algebra", "equation", "polynomial", "matrix", "linear"],
            "geometry": ["geometry", "triangle", "circle", "polygon"],
            "statistics": ["statistics", "probability", "distribution", "mean"],
            "number_theory": ["prime", "number theory", "divisibility"],
        },
        "fiction": {
            "detective": ["detective", "sherlock", "holmes", "poirot", "mystery"],
            "adventure": ["adventure", "cussler", "clancy", "action", "quest"],
            "thriller": ["thriller", "suspense", "spy", "le carre"],
            "classics": ["dickens", "hardy", "austen", "thackeray"],
            "horror": ["horror", "ghost", "supernatural", "lovecraft"],
        },
        "engineering_technology": {
            "mechanical_engineering": ["mechanical", "machine", "engine", "turbine"],
            "civil_engineering": ["civil", "structural", "bridge", "concrete"],
            "electrical_engineering": ["electrical", "power", "circuit", "motor"],
            "aerospace_engineering": ["aerospace", "aircraft", "rocket", "satellite"],
            "materials_science": ["materials", "alloy", "composite", "polymer"],
            "control_engineering": ["control", "feedback", "pid", "servo"],
            "telecommunications": ["telecom", "wireless", "antenna", "frequency"],
        },
        "languages": {
            "english_grammar": ["grammar", "syntax", "parsing", "tense", "clause"],
            "linguistics": ["linguistics", "morphology", "phonology", "semantics"],
            "russian": ["russian", "cyrillic", "slavic", "moscow"],
            "sanskrit": ["sanskrit", "devanagari", "vedic", "panini"],
            "dictionaries": ["dictionary", "lexicon", "thesaurus", "vocabulary"],
            "translation": ["translation", "interpret", "bilingual"],
        },
        "history": {
            "ancient_history": ["ancient", "mesopotamia", "egypt", "rome", "greece"],
            "medieval_history": ["medieval", "crusade", "feudal", "byzantine"],
            "indian_history": ["india", "mughal", "british raj", "independence"],
            "world_war": ["world war", "ww1", "ww2", "nazi", "allied"],
            "modern_history": ["modern", "revolution", "cold war"],
        },
        "computer_science": {
            "programming_languages": ["python", "javascript", "java", "rust"],
            "algorithms": ["algorithm", "sorting", "searching", "complexity"],
            "artificial_intelligence": ["artificial intelligence", "machine learning", "neural"],
            "operating_systems": ["linux", "windows", "kernel", "process"],
            "database_systems": ["database", "sql", "query", "index"],
        },
        "electronics": {
            "circuit_theory": ["circuit", "ohm", "kirchhoff", "resistor"],
            "semiconductor_devices": ["transistor", "diode", "mosfet", "bjt"],
            "digital_electronics": ["digital", "logic", "gate", "flip flop"],
            "microcontrollers": ["arduino", "raspberry", "microcontroller", "embedded"],
            "signal_processing": ["signal", "filter", "fourier", "sampling"],
        },
    }

    domain_map = subdomain_hints.get(domain, {})
    if domain_map:
        scores = {}
        for sub, hints in domain_map.items():
            score = sum(1 for h in hints if h in text)
            if score > 0:
                scores[sub] = score
        if scores:
            return max(scores, key=scores.get)

    parts = Path(path).parts
    for part in reversed(parts[:-1]):
        clean = part.lower().replace(" ", "_").replace("-", "_")
        if len(clean) > 3 and clean not in {"media", "venkatesh", "data", "data3", "home", "srishti"}:
            return clean[:40]

    return "general"


def get_or_assign_theta(conn, domain, subdomain):
    global _theta_cache, _theta_counter
    if domain not in _theta_cache:
        rows = conn.execute("""
            SELECT s.name, s.theta FROM subdomains s
            JOIN domains d ON s.domain_id = d.id
            WHERE d.name = ?
        """, (domain,)).fetchall()
        _theta_cache[domain] = {r[0]: r[1] for r in rows}
        _theta_counter[domain] = max((r[1] for r in rows), default=0.0)

    if subdomain in _theta_cache[domain]:
        return _theta_cache[domain][subdomain]

    _theta_counter[domain] += 1.0
    new_theta = _theta_counter[domain]

    domain_row = conn.execute("SELECT id FROM domains WHERE name=?", (domain,)).fetchone()
    if domain_row:
        conn.execute(
            "INSERT OR IGNORE INTO subdomains (domain_id, name, theta, created_at) VALUES (?,?,?,?)",
            (domain_row[0], subdomain, new_theta, int(time.time()))
        )

    _theta_cache[domain][subdomain] = new_theta
    return new_theta


def get_phi(ext):
    ext = ext.lower()
    if ext in EXT_PHI:
        return EXT_PHI[ext]
    return 200.0 + (abs(hash(ext)) % 100)


# ── MAIN INCREMENTAL INDEXER ──────────────────────────────────────────────────
def index_incremental(scan_path, db_path):
    """
    Scan folder and add only NEW files to srishti3.db.
    Already indexed files are skipped silently.
    Spherical coordinates of existing files never touched.
    """
    scan_path = Path(scan_path)
    if not scan_path.exists():
        print(f"  ERROR: Path does not exist: {scan_path}")
        return

    if not Path(db_path).exists():
        print(f"  ERROR: DB not found: {db_path}")
        print(f"  Run aria_setup.py first to create the DB.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Load all existing paths
    existing = set(r[0] for r in conn.execute("SELECT path FROM files").fetchall())
    before = len(existing)
    print(f"  Existing files in DB : {before:,}")

    added = 0
    skipped = 0
    errors = 0
    start_time = time.time()
    last_print = start_time

    print(f"  Scanning: {scan_path}")

    for root, dirs, files in os.walk(scan_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            if filename.startswith("."):
                skipped += 1
                continue
            if filename.lower() in SKIP_NAMES:
                skipped += 1
                continue

            ext = Path(filename).suffix.lower()
            if ext in SKIP_EXTENSIONS:
                skipped += 1
                continue

            filepath = str(Path(root) / filename)

            if filepath in existing:
                skipped += 1
                continue

            try:
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = int(stat.st_mtime)

                content = read_file_content(filepath)
                domain, confidence = classify_domain(filepath, filename, content)
                subdomain = classify_subdomain(domain, filepath, filename, content)
                r_val = DOMAIN_R.get(domain, PHI)
                theta_val = get_or_assign_theta(conn, domain, subdomain)
                phi_val = get_phi(ext)

                kw_text = filename + " " + Path(filepath).parent.name + " " + content
                keywords = extract_keywords(kw_text, limit=8)

                conn.execute("""
                    INSERT OR IGNORE INTO files
                    (path, name, ext, size, mtime, domain, subdomain,
                     r, theta, phi, keywords, confidence, indexed_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    filepath, filename, ext, size, mtime,
                    domain, subdomain,
                    r_val, theta_val, phi_val,
                    ",".join(keywords), confidence,
                    int(time.time()),
                ))

                added += 1
                existing.add(filepath)

                if added % 100 == 0:
                    conn.commit()

                now = time.time()
                if now - last_print >= 5:
                    print(f"  Added {added} | elapsed {int(now-start_time)}s")
                    last_print = now

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  ERROR: {filename}: {e}")

    conn.commit()
    elapsed = int(time.time() - start_time)

    print(f"\n  {'─'*50}")
    print(f"  Incremental index : {scan_path}")
    print(f"  Target DB         : {db_path}")
    print(f"  {'─'*50}")
    print(f"  Existing files in DB : {before:,}")
    print(f"  Added  : {added} new files")
    print(f"  Skipped: {skipped} already indexed or excluded")
    print(f"  Errors : {errors}")
    print(f"  Total  : {before + added:,} files in DB")
    print(f"  Time   : {elapsed}s")

    conn.close()


# ── STATS ─────────────────────────────────────────────────────────────────────
def show_stats(db_path):
    if not Path(db_path).exists():
        print(f"  DB not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    subdomains_count = conn.execute("SELECT COUNT(*) FROM subdomains").fetchone()[0]

    print(f"\n  Srishti DB — {db_path}")
    print(f"  {'─'*50}")
    print(f"  Total files : {total:,}")
    print(f"  Subdomains  : {subdomains_count} auto-assigned")
    print(f"  phi         : {PHI:.16f}")
    print(f"\n  Domain shells:")

    rows = conn.execute("""
        SELECT d.name, d.r, d.r_index, COUNT(f.id) as cnt
        FROM domains d LEFT JOIN files f ON f.domain = d.name
        GROUP BY d.id ORDER BY d.r_index
    """).fetchall()

    for row in rows:
        print(f"  r({row[2]:>2}) = {row[1]:>12.4f}  {row[0]:<30} {row[3]:>6} files")

    conn.close()


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Srishti DB v1.0 — Incremental Indexer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 aria_incremental.py /media/venkatesh/DATA3/mathematics
  python3 aria_incremental.py /media/venkatesh/DATA3 --db ~/srishti3.db
  python3 aria_incremental.py --stats

phi = 1.6180339887498948482...
The universe is alongside.
        """
    )
    parser.add_argument("path", nargs="?", help="Folder to scan for new files")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"DB path (default: {DEFAULT_DB})")
    parser.add_argument("--stats", action="store_true", help="Show DB statistics")

    args = parser.parse_args()

    print("\n" + "═"*55)
    print("  Srishti DB v1.0 — Incremental Indexer")
    print("  Dr. K.S. Venkatesh + Claude (SI)")
    print("  GPL3 — free for all, profit for none")
    print(f"  phi = {PHI:.16f}")
    print("═"*55 + "\n")

    if args.stats:
        show_stats(args.db)
        return

    if not args.path:
        parser.print_help()
        return

    index_incremental(args.path, args.db)


if __name__ == "__main__":
    main()
