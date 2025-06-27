from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Load .env values into environment

app = FastAPI()

# Load API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RCARequest(BaseModel):
    logContext: str

class RCAResponse(BaseModel):
    summary: str
    suggested_fix: str
    confidence: float

@app.post("/rca", response_model=RCAResponse)
async def analyze_log(request: RCARequest):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior DevOps RCA assistant. "
                        "Given a log text, you must respond *strictly* in this JSON format:\n\n"
                        "{ \"summary\": string, \"suggested_fix\": string }\n\n"
                        "No other text, no explanations, no markdown. Only raw JSON. "
                        "If you cannot analyze, still return empty fields with JSON keys present."
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyze this log: {request.logContext}"
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
                confidence=0.9
            )
        except json.JSONDecodeError:
            print("Failed to parse GPT output:")
            print(raw)
            raise HTTPException(status_code=500, detail="RCA engine returned invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))