from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json
import re

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
    file_path: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    operation: str
    final_code: list[str]

def extract_context_window(file_content: str, target_line: int, window_size: int = 20) -> str:
    lines = file_content.splitlines()
    start = max(target_line - window_size, 0)
    end = min(target_line + window_size, len(lines))
    return "\n".join(lines[start:end])

@app.post("/rca", response_model=RCAResponse)
async def analyze_log(request: RCARequest):
    try:
        # try to parse a line number from log, if any
        line_number = None
        file_path = None
        m = re.search(r"\((.*):(\d+)\)", request.logContext)
        if m:
            file_path = m.group(1)
            line_number = int(m.group(2))

        snippet = "(no file content available)"
        if request.fileContent and line_number:
            snippet = extract_context_window(request.fileContent, line_number)

        # final prompt with strict instructions
        user_prompt = f"""
You are an expert root cause analysis assistant. Given the failure log and file snippet, identify the root cause and generate a fix. 
Respond strictly in valid JSON with no markdown or code fences. Provide the following fields:

- summary: short explanation of root cause
- suggested_fix: how to fix
- file_path: absolute or relative path, or null if unknown
- start_line: integer line to patch, or null if unknown
- end_line: integer line to patch, or null if unknown
- operation: one of [insert, replace, delete, no-op]
- final_code: JSON array of strings, each line of code, never a single multiline string

If you cannot determine a safe patch, set operation to "no-op" with a suggested_fix. 

Example:
{{
  "summary": "Short explanation",
  "suggested_fix": "How to fix",
  "file_path": "src/com/controller/Controller.java",
  "start_line": 42,
  "end_line": 42,
  "operation": "insert",
  "final_code": [
    "line 1",
    "line 2"
  ]
}}

Log:
{request.logContext}

Snippet:
{snippet}

Strictly return valid JSON only, no markdown, no code fences, no explanations.
"""

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior DevOps RCA assistant."},
                {"role": "user", "content": user_prompt}
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
                file_path=parsed.get("file_path"),
                start_line=parsed.get("start_line"),
                end_line=parsed.get("end_line"),
                operation=parsed["operation"],
                final_code=parsed["final_code"]
            )
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON returned by GPT:\n{raw}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))