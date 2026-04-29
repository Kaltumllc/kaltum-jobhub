"""
Kaltum JobHub — FastAPI Backend
Adzuna + Remotive job search
Deploy on Render.com
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import anthropic
import httpx
import os

app = FastAPI(title="Kaltum JobHub API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")
USAJOBS_USER_AGENT = os.getenv("USAJOBS_USER_AGENT", "")


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
    return {"status": "Kaltum JobHub API running", "version": "1.2.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


def normalize_adzuna_job(job: dict) -> dict:
    company = (job.get("company") or {}).get("display_name") or "Unknown"
    location = (job.get("location") or {}).get("display_name") or "USA"

    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    salary = ""

    if salary_min and salary_max:
        salary = f"${int(salary_min):,} - ${int(salary_max):,}"
    elif salary_min:
        salary = f"From ${int(salary_min):,}"
    elif salary_max:
        salary = f"Up to ${int(salary_max):,}"

    return {
        "id": job.get("id"),
        "company": company,
        "title": job.get("title") or "Role",
        "location": location,
        "salary": salary,
        "url": job.get("redirect_url") or "",
        "description": job.get("description") or "",
        "category": (job.get("category") or {}).get("label") or "",
        "source": "Adzuna"
    }


def normalize_remotive_job(job: dict) -> dict:
    return {
        "id": job.get("id"),
        "company": job.get("company_name") or "Unknown",
        "title": job.get("title") or "Role",
        "location": job.get("candidate_required_location") or "Remote",
        "salary": job.get("salary") or "",
        "url": job.get("url") or "",
        "description": job.get("description") or "",
        "category": job.get("category") or "",
        "source": "Remotive"
    }


def normalize_usajobs_job(item: dict) -> dict:
    descriptor = item.get("MatchedObjectDescriptor", {}) or {}
    user_area = descriptor.get("UserArea", {}) or {}
    details = user_area.get("Details", {}) or {}

    org = descriptor.get("OrganizationName") or details.get("AgencyMarketingStatement") or "Federal Government"
    title = descriptor.get("PositionTitle") or "Federal Role"
    location_items = descriptor.get("PositionLocation", []) or []
    location = "USA"

    if location_items:
        location_parts = []
        for loc in location_items[:3]:
            name = loc.get("LocationName")
            if name:
                location_parts.append(name)
        if location_parts:
            location = " | ".join(location_parts)

    salary_min = descriptor.get("PositionRemuneration", [{}])[0].get("MinimumRange") if descriptor.get("PositionRemuneration") else ""
    salary_max = descriptor.get("PositionRemuneration", [{}])[0].get("MaximumRange") if descriptor.get("PositionRemuneration") else ""
    salary = ""

    if salary_min and salary_max:
        salary = f"${salary_min} - ${salary_max}"

    url = descriptor.get("PositionURI") or ""

    return {
        "id": descriptor.get("PositionID") or item.get("MatchedObjectId"),
        "company": org,
        "title": title,
        "location": location,
        "salary": salary,
        "url": url,
        "description": descriptor.get("QualificationSummary") or descriptor.get("UserArea", {}).get("Details", {}).get("JobSummary", ""),
        "category": "Federal Government",
        "source": "USAJOBS"
    }


# Job Search
@app.get("/jobs/search")
async def search_jobs(
    role: str,
    location: str = "usa",
    company: str = "",
    limit: int = 15
):
    """
    Search USA jobs using Adzuna first.
    Falls back to Remotive if Adzuna is unavailable or returns no jobs.
    Examples:
    /jobs/search?role=data analyst&location=boston&company=amazon
    /jobs/search?role=software engineer&location=california&company=google
    """
    role_clean = role.strip()
    location_clean = location.strip() or "usa"
    company_clean = company.strip()
    safe_limit = max(1, min(limit, 50))

    if not role_clean:
        raise HTTPException(status_code=400, detail="Role is required")

    query = role_clean
    if company_clean and company_clean.lower() not in ["all", "any"]:
        query = f"{company_clean} {role_clean}"

    all_jobs = []

    # 1. Adzuna USA job search
    if ADZUNA_APP_ID and ADZUNA_APP_KEY:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    "https://api.adzuna.com/v1/api/jobs/us/search/1",
                    params={
                        "app_id": ADZUNA_APP_ID,
                        "app_key": ADZUNA_APP_KEY,
                        "what": query,
                        "where": location_clean,
                        "results_per_page": safe_limit,
                        "sort_by": "date",
                        "content-type": "application/json",
                    },
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Kaltum-JobHub/1.1"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                all_jobs = [normalize_adzuna_job(job) for job in results]

        except Exception:
            all_jobs = []

    # 2. USAJOBS federal job search
    if not all_jobs and USAJOBS_API_KEY and USAJOBS_USER_AGENT:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    "https://data.usajobs.gov/api/search",
                    params={
                        "Keyword": query,
                        "LocationName": location_clean,
                        "ResultsPerPage": safe_limit
                    },
                    headers={
                        "Host": "data.usajobs.gov",
                        "User-Agent": USAJOBS_USER_AGENT,
                        "Authorization-Key": USAJOBS_API_KEY,
                        "Accept": "application/json"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                search_result = data.get("SearchResult", {}) or {}
                items = search_result.get("SearchResultItems", []) or []
                all_jobs = [normalize_usajobs_job(item) for item in items[:safe_limit]]

        except Exception:
            all_jobs = []

    # 3. Remotive fallback
    if not all_jobs:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    "https://remotive.com/api/remote-jobs",
                    params={"search": query},
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "Kaltum-JobHub/1.1"
                    }
                )

            if response.status_code == 200:
                data = response.json()
                results = data.get("jobs", [])
                all_jobs = [normalize_remotive_job(job) for job in results[:safe_limit]]

        except Exception:
            all_jobs = []

    return {
        "jobs": all_jobs[:safe_limit],
        "total": len(all_jobs[:safe_limit]),
        "role": role_clean,
        "location": location_clean,
        "company": company_clean or "all",
        "source": all_jobs[0].get("source") if all_jobs else "None"
    }


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
