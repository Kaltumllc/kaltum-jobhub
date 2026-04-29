"""
Kaltum Job Search — FastAPI Backend
Deploy on Render.com (free tier)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import anthropic
import httpx
import os

app = FastAPI(title="Kaltum API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Models ─────────────────────────────────────────────────────────
class CoverLetterRequest(BaseModel):
    company: str
    title: str
    job_description: Optional[str] = ""
    background: Optional[str] = ""
    tone: Optional[str] = "professional"

class ResumeEnhanceRequest(BaseModel):
    experience: str
    target_role: Optional[str] = ""

# ── Health ─────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Kaltum API running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Job Search ─────────────────────────────────────────────────────
@app.get("/jobs/search")
async def search_jobs(role: str, location: str = "remote", limit: int = 15):
    """Search jobs from RemoteOK (free, no key needed)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://remoteok.com/api",
                headers={"User-Agent": "Kaltum-JobSearch/1.0"},
                timeout=10
            )
            data = resp.json()

        role_lower = role.lower()
        matches = []

        for job in data[1:]:
            if not isinstance(job, dict):
                continue
            title = (job.get("position") or "").lower()
            tags = " ".join(job.get("tags") or []).lower()
            if any(w in title or w in tags for w in role_lower.split()):
                matches.append({
                    "id": job.get("id"),
                    "company": job.get("company", "Unknown"),
                    "title": job.get("position", ""),
                    "location": "Remote",
                    "salary": job.get("salary", ""),
                    "url": job.get("url", ""),
                    "tags": job.get("tags", []),
                    "source": "RemoteOK"
                })
            if len(matches) >= limit:
                break

        return {"jobs": matches, "total": len(matches), "role": role}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Cover Letter ───────────────────────────────────────────────────
@app.post("/ai/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest):
    """Generate a personalized cover letter using Claude AI."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    tone_map = {
        "professional": "professional, confident, and polished",
        "warm": "warm, personable, and genuine",
        "concise": "concise and direct (under 200 words)",
        "enthusiastic": "enthusiastic and energetic"
    }

    prompt = f"""Write a compelling cover letter for someone applying to be a "{req.title}" at "{req.company}".

Job Description: {req.job_description or 'Not provided — write a strong general letter.'}
Candidate Background: {req.background or 'Experienced professional.'}
Tone: {tone_map.get(req.tone, tone_map['professional'])}

Rules:
- Open with "Dear Hiring Manager,"
- 3-4 paragraphs, under 350 words
- Avoid clichés like "I am writing to express my interest"
- Make the opening memorable
- Sign off as "Sincerely, [Your Name]"
- Write it ready to send — no placeholder brackets"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"letter": message.content[0].text, "company": req.company, "title": req.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Resume Enhance ─────────────────────────────────────────────────
@app.post("/ai/enhance-resume")
async def enhance_resume(req: ResumeEnhanceRequest):
    """Enhance resume bullet points using Claude AI."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    prompt = f"""Rewrite these resume bullet points to be stronger, more impactful, and ATS-friendly for a {req.target_role or 'professional'} role.
Use strong action verbs, add quantification where reasonable, and keep concise.
Return ONLY the improved bullet points, no explanation:

{req.experience}"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"enhanced": message.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
