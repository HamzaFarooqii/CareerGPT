# ============================================================
# Resume Parser — PDF to Structured Text
# ============================================================
# This service takes a PDF file and extracts:
#   1. Raw text (everything in the PDF)
#   2. Structured sections (education, skills, experience, etc.)
#
# CONCEPT: Why Parse PDFs?
# ────────────────────────
# A PDF is a visual format — it stores HOW text looks (fonts,
# positions, colors) but not WHAT the text MEANS. A PDF doesn't
# know that "EDUCATION" is a section header and "FAST NUCES" is
# a school name. That's what our parser figures out.
#
# CONCEPT: Why Sections (Chunking)?
# ─────────────────────────────────
# We split the resume into sections because:
#
#   1. BETTER EMBEDDINGS:
#      "Python, FastAPI, Docker, React" as a skills chunk
#      → produces a focused embedding that matches job skill requirements
#
#      vs. the entire 3-page resume in one chunk
#      → produces a diluted embedding that matches everything poorly
#
#   2. EXPLAINABILITY:
#      We can tell the user "Your SKILLS section matched this job"
#      instead of just "Your resume matched"
#
#   3. SMARTER MATCHING:
#      Job requires "3+ years experience" → we check the EXPERIENCE section
#      Job requires "BS in CS" → we check the EDUCATION section
# ============================================================

import re

import fitz  # PyMuPDF — the PDF reading library


# Section headers we look for in resumes.
# These are the most common section names across resume formats.
# We use regex patterns (case-insensitive) to match variations:
#   "SKILLS" / "Skills" / "Technical Skills" / "Key Skills" all match.
SECTION_PATTERNS = [
    (r"(?i)^(?:professional\s+)?summary|(?:career\s+)?objective|profile", "summary"),
    (r"(?i)^(?:technical\s+)?skills|competenc|technologies|tech\s+stack", "skills"),
    (r"(?i)^education|academic|qualification", "education"),
    (r"(?i)^(?:work\s+)?experience|employment|work\s+history", "experience"),
    (r"(?i)^projects?|key\s+projects|portfolio", "projects"),
    (r"(?i)^certif", "certifications"),
    (r"(?i)^(?:extra|co)[- ]?curricular|activit|volunteer", "activities"),
    (r"(?i)^interests?|hobbies", "interests"),
    (r"(?i)^references?", "references"),
]


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_bytes: The raw bytes of the PDF file.
                   When a user uploads a file, FastAPI gives us bytes.
    
    Returns:
        A single string with all the text from every page.
    
    HOW IT WORKS:
    1. fitz.open() reads the PDF bytes into memory
    2. We loop through every page
    3. page.get_text() extracts the text from that page
    4. We join all pages with newlines
    
    EDGE CASES WE HANDLE:
    - Multi-page resumes (loop through all pages)
    - PDFs with images (we skip images, only extract text)
    - Empty pages (we skip them with the .strip() check)
    """
    # stream=pdf_bytes tells PyMuPDF to read from memory
    # filetype="pdf" tells it what format to expect
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        # Only add non-empty pages
        if text.strip():
            pages_text.append(text.strip())

    doc.close()

    # Join all pages with double newlines (paragraph break)
    full_text = "\n\n".join(pages_text)

    return full_text


def parse_sections(raw_text: str) -> list[dict]:
    """
    Split raw resume text into labeled sections.
    
    Args:
        raw_text: The full text extracted from the PDF.
    
    Returns:
        A list of dicts like:
        [
            {"section_type": "summary", "content": "Software engineer..."},
            {"section_type": "skills", "content": "Python, FastAPI..."},
            {"section_type": "education", "content": "FAST NUCES..."},
            ...
        ]
    
    HOW THE ALGORITHM WORKS:
    ────────────────────────
    1. Split the text into lines
    2. For each line, check if it looks like a section header
       (matches one of our SECTION_PATTERNS)
    3. If it's a header → start a new section
    4. If it's not → append to the current section
    5. At the end, any text before the first header
       becomes a "header" section (usually the name/contact info)
    
    CONCEPT: Regular Expressions (regex)
    ─────────────────────────────────────
    re.match(pattern, text) checks if text matches a pattern.
    (?i) = case insensitive
    ^ = start of string
    | = OR
    \\s+ = one or more spaces
    ? = optional
    
    Example: r"(?i)^education|academic"
    Matches: "Education", "EDUCATION", "Academic Background"
    """
    lines = raw_text.split("\n")
    sections = []
    current_section = {"section_type": "header", "content": ""}

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            # Add a newline to preserve paragraph structure
            if current_section["content"]:
                current_section["content"] += "\n"
            continue

        # Check if this line is a section header
        matched_section = None
        for pattern, section_type in SECTION_PATTERNS:
            if re.match(pattern, stripped):
                matched_section = section_type
                break

        if matched_section:
            # Save the current section (if it has content)
            if current_section["content"].strip():
                sections.append({
                    "section_type": current_section["section_type"],
                    "content": current_section["content"].strip(),
                })

            # Start a new section
            current_section = {"section_type": matched_section, "content": ""}
        else:
            # Append this line to the current section
            current_section["content"] += stripped + "\n"

    # Don't forget the last section!
    if current_section["content"].strip():
        sections.append({
            "section_type": current_section["section_type"],
            "content": current_section["content"].strip(),
        })

    # If no sections were detected (maybe the resume doesn't have headers),
    # put everything into a single "full_resume" section.
    if len(sections) <= 1:
        return [{"section_type": "full_resume", "content": raw_text.strip()}]

    return sections


def get_word_count(text: str) -> int:
    """Count words in text. Simple but useful for stats."""
    return len(text.split())
