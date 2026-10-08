import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


def analyze_resume(resume_text, user_goal): 

    if not os.getenv("GROQ_API_KEY"):
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_question": [],
            "error": "GROQ_API_KEY is missing in .env"
        }

    prompt = f"""
You are a senior software engineer and hiring manager.

Analyze this resume for the target career role.

Target role:
{user_goal}

Rules:
- Extract only skills relevant to the target role.
- Ignore irrelevant skills.
- Identify genuine missing skills.
- Create a roadmap only for missing skills.
- Generate interview questions relevant to the target role.
- Do not invent skills.
- Return ONLY valid JSON. 

Return exactly:

{{
    "skills": [],
    "missing_skills": [],
    "roadmap": [],
    "interview_question": []
}}

Resume:
{resume_text}
"""

    try:
        response = client.responses.create(
            model="openai/gpt-oss-20b",
            input=prompt
        )

        content = response.output_text.strip()

        # Remove markdown if model returns it
        if content.startswith("```json"):
            content = content[7:]

        if content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Find JSON
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("AI did not return valid JSON")

        result = json.loads(content[start:end])

        return {
            "skills": result.get("skills", []),
            "missing_skills": result.get("missing_skills", []),
            "roadmap": result.get("roadmap", []),
            "interview_question": result.get(
                "interview_question", []
            )
        }

    except Exception as e:
        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_question": [],
            "error": str(e)
        }