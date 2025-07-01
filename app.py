from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

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
    fileContent: str | None = None

class RCAResponse(BaseModel):
    summary: str
    suggested_fix: str
    file_path: str
    start_line: int
    end_line: int
    replacement_code: list[str]

@app.post("/rca", response_model=RCAResponse)
async def analyze_log(request: RCARequest):
    try:
        user_prompt = f"""Analyze this Java stack trace:
{request.logContext}

Here is the *relevant source file*:
{request.fileContent or "(file content unavailable)"}

Respond strictly in this JSON format:
{{
  "summary": "...",
  "suggested_fix": "...",
  "file_path": "...",
  "start_line": 42,
  "end_line": 42,
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

        import json
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
            print("❌ Failed to parse GPT output:")
            print(raw)
            raise HTTPException(status_code=500, detail="RCA engine returned invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))