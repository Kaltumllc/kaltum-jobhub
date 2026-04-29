"""
Kaltum JobHub — FastAPI Backend
Deploy on Render.com
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import anthropic
import httpx
import os

app = FastAPI(title="Kaltum JobHub API", version="1.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# Models
class CoverLetterRequest(BaseModel):
    company: str
    title: str
    job_description: Optional[str] = ""
    background: Optional[str] = ""
    tone: Optional[str] = "professional"


class ResumeEnhanceRequest(BaseModel):
    experience: str
    target_role: Optional[str] = ""


# Health
@app.get("/")
def root():
    return {"status": "Kaltum JobHub API running", "version": "1.0.1"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Job Search
@app.get("/jobs/search")
async def search_jobs(role: str, location: str = "remote", limit: int = 15):
    """
    Search remote jobs from Remotive free jobs API.
    Note: Remotive mainly returns remote roles, so location is returned for display,
    but the provider may not strictly filter by city.
    """
    try:
        role_clean = role.strip()

        if not role_clean:
            raise HTTPException(status_code=400, detail="Role is required")

        safe_limit = max(1, min(limit, 30))

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": role_clean},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Kaltum-JobHub/1.0"
                }
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Job provider error: HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Job provider returned invalid data. Please try again."
            )

        provider_jobs = data.get("jobs", [])
        matches = []

        for job in provider_jobs[:safe_limit]:
            matches.append({
                "id": job.get("id"),
                "company": job.get("company_name") or "Unknown",
                "title": job.get("title") or "Role",
                "location": job.get("candidate_required_location") or "Remote",
                "salary": job.get("salary") or "",
                "url": job.get("url") or "",
                "tags": job.get("tags") or [],
                "category": job.get("category") or "",
                "source": "Remotive"
            })

        return {
            "jobs": matches,
            "total": len(matches),
            "role": role_clean,
            "location": location,
            "source": "Remotive"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# Cover Letter
@app.post("/ai/cover-letter")
async def generate_cover_letter(req: CoverLetterRequest):
    """Generate a personalized cover letter using Claude AI."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    tone_map = {
        "professional": "professional, confident, and polished",
        "warm": "warm, personable, and genuine",
        "concise": "concise and direct, under 200 words",
        "enthusiastic": "enthusiastic and energetic"
    }

    prompt = f"""Write a compelling cover letter for someone applying to be a "{req.title}" at "{req.company}".

Job Description: {req.job_description or "Not provided - write a strong general letter."}
Candidate Background: {req.background or "Experienced professional."}
Tone: {tone_map.get(req.tone, tone_map["professional"])}

Rules:
- Open with "Dear Hiring Manager,"
- Use 3 to 4 paragraphs
- Keep it under 350 words
- Avoid cliches like "I am writing to express my interest"
- Make the opening memorable
- Sign off as "Sincerely, [Your Name]"
- Write it ready to send"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "letter": message.content[0].text,
            "company": req.company,
            "title": req.title
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Resume Enhance
@app.post("/ai/enhance-resume")
async def enhance_resume(req: ResumeEnhanceRequest):
    """Enhance resume bullet points using Claude AI."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    prompt = f"""Rewrite these resume bullet points to be stronger, more impactful, and ATS-friendly for a {req.target_role or "professional"} role.

Use strong action verbs, add quantification where reasonable, and keep the writing concise.

Return ONLY the improved bullet points, with no explanation:

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
