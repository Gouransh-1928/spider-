"""
SPIDER — Resume Updater Skill
Searches for jobs, extracts skills/requirements, and updates your .docx resume.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests
from docx import Document
from docx.shared import Pt
from loguru import logger

from config.loader import CONFIG
from skills.web_search import WebSearch


class ResumeUpdater:
    """
    Searches for jobs matching user's skills and updates their .docx resume.
    """

    def __init__(self):
        self.resume_path = Path(CONFIG["resume"]["default_path"])
        self.web_search = WebSearch()
        self.ollama_url = CONFIG["brain"]["ollama_url"]
        self.model = CONFIG["brain"]["model"]

    def handle(self, user_input: str) -> str:
        """Parse command and update resume accordingly."""
        text = user_input.lower()

        if "update" in text and "resume" in text:
            # Extract job type from command
            job_query = self._extract_job_query(user_input)
            return self.update_resume_for_job(job_query)
        elif "create resume" in text or "make resume" in text:
            return self.create_resume_from_scratch()
        else:
            return "I can update your resume for a specific job type. Say: 'SPIDER, update my resume for [job type]'"

    def update_resume_for_job(self, job_query: str = "software developer") -> str:
        """
        1. Search for jobs matching the query
        2. Extract required skills from job descriptions
        3. Update the resume to highlight matching skills
        """
        logger.info(f"Updating resume for: {job_query}")

        # Step 1: Search for jobs
        job_results = self.web_search.search_jobs(job_query)
        if not job_results:
            return "I couldn't find any job listings to reference for the resume update."

        # Step 2: Extract skills from job descriptions
        all_descriptions = " ".join(r["snippet"] for r in job_results)
        extracted_skills = self._extract_skills_from_jd(all_descriptions)

        # Step 3: Load or create resume
        if not self.resume_path.exists():
            return (
                f"I don't see a resume at {self.resume_path}. "
                "Place your resume.docx in the data/resumes/ folder, or say 'create my resume'."
            )

        doc = Document(str(self.resume_path))

        # Step 4: Ask LLM to suggest additions based on the job & skills
        suggestions = self._get_resume_suggestions(job_query, extracted_skills, doc)

        # Step 5: Add a "Job-Specific Summary" section to the resume
        self._add_skills_section(doc, extracted_skills, suggestions)

        # Step 6: Save updated resume
        updated_path = self.resume_path.parent / f"resume_updated_{job_query.replace(' ', '_')}.docx"
        doc.save(str(updated_path))

        logger.info(f"Resume updated: {updated_path}")
        return (
            f"✅ Resume updated for '{job_query}'!\n"
            f"Saved to: {updated_path}\n\n"
            f"Key skills I added/highlighted:\n" +
            "\n".join(f"  • {s}" for s in extracted_skills[:10])
        )

    def create_resume_from_scratch(self) -> str:
        """Create a basic resume template."""
        doc = Document()
        
        # Title
        title = doc.add_heading("Your Name", 0)
        doc.add_paragraph("Email: your@email.com | Phone: +91-XXXXXXXXXX | LinkedIn: linkedin.com/in/yourprofile")
        
        doc.add_heading("Professional Summary", level=1)
        doc.add_paragraph("A motivated professional with expertise in [your field].")
        
        doc.add_heading("Skills", level=1)
        doc.add_paragraph("• Skill 1\n• Skill 2\n• Skill 3")
        
        doc.add_heading("Work Experience", level=1)
        doc.add_paragraph("Job Title — Company Name (Year - Year)\n• Responsibility 1\n• Responsibility 2")
        
        doc.add_heading("Education", level=1)
        doc.add_paragraph("Degree — University Name (Year)")
        
        doc.add_heading("Projects", level=1)
        doc.add_paragraph("Project Name — Brief description")

        self.resume_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(self.resume_path))
        
        return (
            f"I created a resume template at:\n{self.resume_path}\n\n"
            "Please fill in your details, then I can update it for specific jobs!"
        )

    def _extract_skills_from_jd(self, jd_text: str) -> List[str]:
        """Extract common skills/requirements from job description text."""
        # Common tech skills to look for
        skill_patterns = [
            r'\b(Python|Java|JavaScript|TypeScript|React|Node\.js|Django|Flask|FastAPI)\b',
            r'\b(SQL|MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|CI/CD|DevOps)\b',
            r'\b(Machine Learning|Deep Learning|NLP|AI|TensorFlow|PyTorch)\b',
            r'\b(HTML|CSS|REST API|GraphQL|Microservices)\b',
            r'\b(Git|Agile|Scrum|JIRA|Linux)\b',
            r'\b(Data Analysis|Excel|Power BI|Tableau|Pandas|NumPy)\b',
        ]

        found_skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, jd_text, re.IGNORECASE)
            found_skills.update(matches)

        return sorted(found_skills)

    def _get_resume_suggestions(self, job_query: str, skills: List[str], doc: Document) -> str:
        """Ask LLM (Groq or Ollama) for resume improvement suggestions."""
        doc_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())[:2000]
        skills_str = ", ".join(skills)

        prompt = (
            f"The user wants to apply for: {job_query}\n"
            f"Key skills required: {skills_str}\n"
            f"Their current resume:\n{doc_text}\n\n"
            "Suggest 3-5 specific bullet points to ADD to their resume to make it more relevant for this job. "
            "Be concrete and professional. Return only the bullet points."
        )

        provider = CONFIG["brain"].get("provider", "groq")
        model = CONFIG["brain"]["model"]

        try:
            if provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {CONFIG['brain'].get('groq_api_key', '')}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                }
                r = requests.post(url, headers=headers, json=payload, timeout=60)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
            else:
                r = requests.post(
                    f"{CONFIG['brain']['ollama_url']}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=60,
                )
                r.raise_for_status()
                return r.json()["response"].strip()
        except Exception as e:
            logger.error(f"LLM resume suggestion error: {e}")
            return ""

    def _add_skills_section(self, doc: Document, skills: List[str], suggestions: str) -> None:
        """Add/update a skills section in the resume."""
        # Add a horizontal rule and new section
        doc.add_paragraph("─" * 50)
        heading = doc.add_heading("Key Skills (Auto-Updated by SPIDER)", level=1)
        
        if skills:
            skills_para = doc.add_paragraph()
            skills_para.add_run(", ".join(skills)).bold = False

        if suggestions:
            doc.add_heading("Suggested Additions for This Role", level=2)
            doc.add_paragraph(suggestions)

    def _extract_job_query(self, text: str) -> str:
        """Extract the job type from the command."""
        # Pattern: "update my resume for [job type]"
        match = re.search(r'(?:for|as|a)\s+(.+?)(?:\s+job|\s+position|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "software developer"
