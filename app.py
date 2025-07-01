from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RCARequest(BaseModel):
    logContext: str
    fileContent: Optional[str] = None

class RCAResponse(BaseModel):
    summary: str
    suggested_fix: str
    file_path: str
    start_line: int
    end_line: int
    replacement_code: list[str]

def extract_context_window(file_content: str, target_line: int, window_size: int = 20) -> str:
    """
    Get a snippet of the file around the target_line (+/- window_size)
    """
    lines = file_content.splitlines()
    start = max(target_line - window_size, 0)
    end = min(target_line + window_size, len(lines))
    snippet = "\n".join(lines[start:end])
    return snippet

@app.post("/rca", response_model=RCAResponse)
async def analyze_log(request: RCARequest):
    try:
        # Try to extract the top frame line number from the stack trace
        import re
        match = re.search(r"\((.*\.java):(\d+)\)", request.logContext)
        if not match:
            raise HTTPException(status_code=400, detail="Could not parse line number from stack trace.")

        file_path = match.group(1)
        line_number = int(match.group(2))

        # Get the relevant code snippet window
        snippet = "(no file content available)"
        if request.fileContent:
            snippet = extract_context_window(request.fileContent, line_number)

        # Compose prompt
        user_prompt = f"""Analyze this Java stack trace:
{request.logContext}

Relevant snippet of {file_path}:
{snippet}

Respond strictly in this JSON format:
{{
  "summary": "...",
  "suggested_fix": "...",
  "file_path": "...",
  "start_line": {line_number},
  "end_line": {line_number},
  "replacement_code": ["line1", "line2"]
}}
No markdown, no explanations, no additional text.
"""

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior DevOps RCA assistant."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.2
        )

        raw = completion.choices[0].message.content.strip()
        print("🟢 Raw GPT response:\n", raw)

        try:
            parsed = json.loads(raw)
            return RCAResponse(
                summary=parsed["summary"],
                suggested_fix=parsed["suggested_fix"],
                file_path=parsed["file_path"],
                start_line=parsed["start_line"],
                end_line=parsed["end_line"],
                replacement_code=parsed["replacement_code"]
            )
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="GPT returned invalid JSON: " + raw)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))