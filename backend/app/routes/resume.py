# ============================================================
# Resume Routes — API Endpoints for Resume Management
# ============================================================
# These are the HTTP endpoints that the frontend (or Postman/curl)
# calls to interact with resumes.
#
# CONCEPT: REST API Endpoints
# ───────────────────────────
# REST = Representational State Transfer
# It's a convention for designing URLs:
#
#   POST   /api/resumes/upload  → Create (upload a new resume)
#   GET    /api/resumes         → Read (list all resumes)
#   GET    /api/resumes/{id}    → Read (get one resume)
#   DELETE /api/resumes/{id}    → Delete (remove a resume)
#
# Each endpoint has:
#   - HTTP method (GET, POST, DELETE)
#   - URL path
#   - Request data (what the user sends)
#   - Response data (what we send back)
#
# CONCEPT: APIRouter
# ──────────────────
# FastAPI's Router groups related endpoints together.
# Instead of defining all routes in main.py (messy), we put
# resume routes in this file, job routes in another, etc.
# Then main.py just includes each router.
# ============================================================

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config.database import db
from app.models.resume import ResumeListItem, ResumeResponse
from app.services.embedding_service import generate_embedding, generate_embeddings_batch
from app.services.resume_parser import (
    extract_text_from_pdf,
    get_word_count,
    parse_sections,
)

# Create a router with:
#   prefix="/api/resumes" → all routes start with /api/resumes
#   tags=["Resumes"] → groups them in the auto-generated docs
router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    title: str = Form(default=None, description="Optional label for this resume"),
):
    """
    Upload a PDF resume, parse it, generate embeddings, and store everything.
    
    WHAT HAPPENS STEP BY STEP:
    ──────────────────────────
    1. VALIDATE: Check file is a PDF and not too large
    2. READ: Read the PDF bytes into memory
    3. EXTRACT: Use PyMuPDF to get raw text from the PDF
    4. PARSE: Split text into sections (skills, education, etc.)
    5. EMBED: Generate vector embeddings for each section
    6. STORE: Save everything to MongoDB
    7. RESPOND: Return the parsed resume data to the user
    
    CONCEPT: UploadFile
    ───────────────────
    When you upload a file through a web form or Postman,
    it arrives as an UploadFile object with:
      - file.filename → "hamza_resume.pdf"
      - file.content_type → "application/pdf"
      - file.read() → the actual bytes of the file
    
    CONCEPT: Form(...) vs Body(...)
    ───────────────────────────────
    When sending files, you can't use JSON body (it's binary data).
    Instead, you use "multipart form data" — the same format
    browsers use when you submit a form with a file input.
    Form(...) reads text fields from this multipart data.
    """

    # ── Step 1: Validate ──────────────────────────────────
    # Check that it's actually a PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file."
        )

    # Read the file bytes
    pdf_bytes = await file.read()

    # Check file size
    if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    # Check it's not empty
    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    # ── Step 2: Extract text from PDF ─────────────────────
    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Could not read PDF: {str(e)}. Make sure it's a valid PDF."
        )

    # Verify we actually got text
    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract meaningful text from this PDF. "
                   "It might be a scanned image — we need text-based PDFs."
        )

    # ── Step 3: Parse into sections ───────────────────────
    sections = parse_sections(raw_text)
    word_count = get_word_count(raw_text)

    print(f"📄 Parsed resume: {len(sections)} sections, {word_count} words")
    for sec in sections:
        print(f"   └─ {sec['section_type']}: {len(sec['content'])} chars")

    # ── Step 4: Generate embeddings ───────────────────────
    # We embed each section separately AND the full resume
    #
    # WHY both?
    # - Section embeddings: for precise matching ("does this job
    #   need skills I have?")
    # - Full embedding: for overall similarity ("is this job in
    #   my general field?")
    has_embedding = False
    section_embeddings = []
    full_embedding = None

    try:
        # Embed all sections in one batch (efficient!)
        section_texts = [sec["content"] for sec in sections]
        section_embeddings = await generate_embeddings_batch(section_texts)

        # Also embed the full resume text
        full_embedding = await generate_embedding(raw_text)

        has_embedding = True
        print(f"🧠 Generated embeddings: {len(section_embeddings)} sections + 1 full resume")

    except Exception as e:
        # If embedding fails, we still save the resume — just without embeddings.
        # The user can retry later. This is the "graceful degradation" pattern:
        # better to partially work than to completely fail.
        print(f"⚠️ Embedding generation failed (resume still saved): {e}")

    # ── Step 5: Store in MongoDB ──────────────────────────
    #
    # CONCEPT: MongoDB Document Structure
    # ────────────────────────────────────
    # A MongoDB document is like a JSON object. It can contain:
    # - Strings, numbers, booleans
    # - Nested objects
    # - Arrays (lists)
    # - Dates
    #
    # Unlike SQL, there's no schema to create upfront.
    # You just insert a document and MongoDB stores it.
    # This is why MongoDB is called "schemaless" (though
    # "schema-flexible" is more accurate).

    # Build the section data (text + embedding paired together)
    sections_data = []
    for i, sec in enumerate(sections):
        section_doc = {
            "section_type": sec["section_type"],
            "content": sec["content"],
        }
        # Add embedding if we have one
        if i < len(section_embeddings):
            section_doc["embedding"] = section_embeddings[i]
        sections_data.append(section_doc)

    # The full document we're saving
    resume_doc = {
        "title": title or file.filename.replace(".pdf", "").replace("_", " ").title(),
        "file_name": file.filename,
        "raw_text": raw_text,
        "sections": sections_data,
        "word_count": word_count,
        "has_embedding": has_embedding,
        "full_embedding": full_embedding,
        "created_at": datetime.now(timezone.utc),
    }

    # Insert into MongoDB
    # insert_one() adds the document and returns the generated _id
    collection = db.get_collection("resumes")
    result = await collection.insert_one(resume_doc)

    # MongoDB generates a unique ObjectId for every document.
    # ObjectId is a 12-byte identifier that includes:
    #   - timestamp (when it was created)
    #   - machine ID
    #   - process ID
    #   - counter
    # This means IDs are unique across all machines worldwide.
    resume_id = str(result.inserted_id)
    print(f"💾 Saved resume to MongoDB with ID: {resume_id}")

    # ── Step 6: Return response ───────────────────────────
    return ResumeResponse(
        id=resume_id,
        title=resume_doc["title"],
        file_name=file.filename,
        raw_text=raw_text,
        sections=[
            {"section_type": s["section_type"], "content": s["content"]}
            for s in sections
        ],
        word_count=word_count,
        has_embedding=has_embedding,
        created_at=resume_doc["created_at"].isoformat(),
        message=f"✅ Resume parsed successfully! "
                f"{len(sections)} sections detected, {word_count} words. "
                f"{'Embeddings generated.' if has_embedding else 'Embeddings pending.'}",
    )


@router.get("", response_model=list[ResumeListItem])
async def list_resumes():
    """
    List all uploaded resumes (without full text — just metadata).
    
    CONCEPT: Projection
    ───────────────────
    In MongoDB, you can choose WHICH fields to return.
    This is called "projection". We exclude raw_text and embeddings
    because they're large and not needed for a list view.
    
    In SQL terms:
      SELECT id, title, file_name FROM resumes
    vs
      SELECT * FROM resumes  (returns everything, wasteful)
    """
    collection = db.get_collection("resumes")

    # projection: 1 = include, 0 = exclude
    # We include metadata fields and exclude large fields
    cursor = collection.find(
        {},  # {} means "find all documents"
        {
            "raw_text": 0,           # Exclude (too large for list view)
            "sections": 0,           # Exclude (contains embeddings)
            "full_embedding": 0,     # Exclude (768 numbers per resume)
        }
    ).sort("created_at", -1)  # Sort newest first (-1 = descending)

    resumes = []
    async for doc in cursor:
        resumes.append(ResumeListItem(
            id=str(doc["_id"]),
            title=doc.get("title", "Untitled"),
            file_name=doc.get("file_name", "unknown.pdf"),
            word_count=doc.get("word_count", 0),
            has_embedding=doc.get("has_embedding", False),
            created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
        ))

    return resumes


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: str):
    """
    Get a single resume by its ID (includes full text and sections).
    
    CONCEPT: Path Parameters
    ────────────────────────
    The {resume_id} in the URL is a path parameter.
    GET /api/resumes/507f1f77bcf86cd799439011
    → resume_id = "507f1f77bcf86cd799439011"
    
    FastAPI automatically extracts it and passes it to this function.
    """
    collection = db.get_collection("resumes")

    # Validate the ID format
    try:
        obj_id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume ID format")

    # Find the document (exclude raw embedding arrays from response)
    doc = await collection.find_one(
        {"_id": obj_id},
        {"full_embedding": 0, "sections.embedding": 0}
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    return ResumeResponse(
        id=str(doc["_id"]),
        title=doc.get("title", "Untitled"),
        file_name=doc.get("file_name", "unknown.pdf"),
        raw_text=doc.get("raw_text", ""),
        sections=[
            {"section_type": s["section_type"], "content": s["content"]}
            for s in doc.get("sections", [])
        ],
        word_count=doc.get("word_count", 0),
        has_embedding=doc.get("has_embedding", False),
        created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
        message="Resume retrieved successfully",
    )


@router.delete("/{resume_id}")
async def delete_resume(resume_id: str):
    """Delete a resume by ID."""
    collection = db.get_collection("resumes")

    try:
        obj_id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume ID format")

    result = await collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found")

    return {"message": f"✅ Resume {resume_id} deleted successfully"}


@router.post("/{resume_id}/embed")
async def re_embed_resume(resume_id: str):
    """
    Regenerate embeddings for an existing resume.

    Use this when a resume was uploaded before embeddings were working,
    or to refresh embeddings with a new model.
    """
    collection = db.get_collection("resumes")

    try:
        obj_id = ObjectId(resume_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid resume ID format")

    doc = await collection.find_one({"_id": obj_id}, {"raw_text": 1, "sections": 1, "title": 1})

    if not doc:
        raise HTTPException(status_code=404, detail="Resume not found")

    raw_text = doc.get("raw_text", "")
    if not raw_text:
        raise HTTPException(status_code=422, detail="Resume has no text to embed")

    try:
        full_embedding = await generate_embedding(raw_text)

        sections = doc.get("sections", [])
        section_texts = [s.get("content", "") for s in sections if s.get("content")]
        section_embeddings = await generate_embeddings_batch(section_texts) if section_texts else []

        updated_sections = []
        for i, sec in enumerate(sections):
            updated_sec = {"section_type": sec.get("section_type"), "content": sec.get("content", "")}
            if i < len(section_embeddings):
                updated_sec["embedding"] = section_embeddings[i]
            updated_sections.append(updated_sec)

        await collection.update_one(
            {"_id": obj_id},
            {"$set": {
                "full_embedding": full_embedding,
                "sections": updated_sections,
                "has_embedding": True,
            }}
        )

        print(f"✅ Re-embedded resume: {doc.get('title', resume_id)}")
        return {
            "message": "✅ Embeddings regenerated successfully",
            "resume_id": resume_id,
            "embedding_dimensions": len(full_embedding),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")
