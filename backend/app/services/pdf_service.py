# ============================================================
# PDF Service — Professional Resume & Cover Letter PDF Generation
# ============================================================
# Uses WeasyPrint (HTML→PDF) with Jinja2 templates.
# Falls back to reportlab if WeasyPrint is unavailable.
# ============================================================

import io
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _render_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with context."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        template = env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        raise RuntimeError(f"Template rendering failed: {e}")


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML string to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
        pdf_bytes = HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
        return pdf_bytes
    except ImportError:
        # WeasyPrint not available — use reportlab fallback
        return _reportlab_fallback(html)
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")


def _reportlab_fallback(html: str) -> bytes:
    """Minimal PDF fallback using reportlab if WeasyPrint is unavailable."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        import re

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        story = []

        # Strip HTML and add as paragraphs
        text = re.sub(r"<[^>]+>", "\n", html)
        for line in text.split("\n"):
            line = line.strip()
            if line:
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 4))

        doc.build(story)
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"PDF fallback also failed: {e}")


def generate_resume_pdf(
    name: str,
    contact: dict,
    summary: str,
    skills: list[str],
    experience: list[dict],
    education: list[dict],
    projects: list[dict],
    certifications: list[str],
    job_title: str = "",
    matched_keywords: list[str] = None,
) -> bytes:
    """
    Generate a professional ATS-compliant resume PDF.

    Args:
        name: Full name
        contact: {email, phone, linkedin, github, location}
        summary: Professional summary paragraph
        skills: List of skill strings
        experience: List of {title, company, dates, bullets: [str]}
        education: List of {degree, school, dates, gpa}
        projects: List of {name, description, technologies}
        certifications: List of certification strings
        job_title: Target job title (for tailoring)
        matched_keywords: Keywords from JD to highlight

    Returns:
        PDF as bytes (ready to send as HTTP response)
    """
    context = {
        "name": name,
        "contact": contact,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "job_title": job_title,
        "matched_keywords": matched_keywords or [],
        "generated_at": datetime.now().strftime("%B %Y"),
    }

    html = _render_html("resume_ats.html", context)
    return _html_to_pdf(html)


def generate_resume_pdf_from_text(
    optimized_text: str,
    name: str = "Candidate",
    job_title: str = "",
) -> bytes:
    """
    Generate a resume PDF directly from ATS-optimized text.
    Parses the text into sections automatically.
    """
    sections = _parse_resume_text(optimized_text)

    return generate_resume_pdf(
        name=sections.get("name", name),
        contact=sections.get("contact", {}),
        summary=sections.get("summary", ""),
        skills=sections.get("skills", []),
        experience=sections.get("experience", []),
        education=sections.get("education", []),
        projects=sections.get("projects", []),
        certifications=sections.get("certifications", []),
        job_title=job_title,
    )


def generate_cover_letter_pdf(
    cover_letter_text: str,
    name: str,
    company: str,
    job_title: str,
    contact: Optional[dict] = None,
) -> bytes:
    """Generate a professional cover letter PDF."""
    context = {
        "letter_text": cover_letter_text,
        "name": name,
        "company": company,
        "job_title": job_title,
        "contact": contact or {},
        "date": datetime.now().strftime("%B %d, %Y"),
    }

    html = _render_html("cover_letter.html", context)
    return _html_to_pdf(html)


def _parse_resume_text(text: str) -> dict:
    """
    Heuristically parse an ATS-optimized resume text into sections.
    Returns a dict with sections that can be fed into the template.
    """
    import re

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    result = {
        "name": "",
        "contact": {},
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
    }

    if lines:
        result["name"] = lines[0]

    section_markers = {
        "summary": re.compile(r"^(summary|profile|objective|about)", re.I),
        "skills": re.compile(r"^(skills|technical skills|core competencies|expertise)", re.I),
        "experience": re.compile(r"^(experience|work experience|employment|professional experience)", re.I),
        "education": re.compile(r"^(education|academic|qualifications)", re.I),
        "projects": re.compile(r"^(projects|portfolio|work samples)", re.I),
        "certifications": re.compile(r"^(certifications?|certificates?|credentials)", re.I),
    }

    current_section = None
    current_block: list[str] = []

    def flush_block():
        if not current_section or not current_block:
            return
        content = " ".join(current_block)
        if current_section == "summary":
            result["summary"] = content
        elif current_section == "skills":
            # Split by comma, pipe, bullet
            raw = re.split(r"[,|•·\n]", content)
            result["skills"] = [s.strip() for s in raw if s.strip()]
        elif current_section in ("experience", "education", "projects"):
            result[current_section].append({"raw": content})
        elif current_section == "certifications":
            result["certifications"].extend(
                s.strip() for s in re.split(r"[,\n•·]", content) if s.strip()
            )

    for line in lines[1:]:
        matched_sec = None
        for sec_name, pattern in section_markers.items():
            if pattern.match(line):
                matched_sec = sec_name
                break

        if matched_sec:
            flush_block()
            current_section = matched_sec
            current_block = []
        elif current_section:
            current_block.append(line)

    flush_block()
    return result
