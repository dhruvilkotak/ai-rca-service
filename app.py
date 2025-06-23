from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env values into environment

app = FastAPI()

class RCARequest(BaseModel):
    logContext: str

class RCAResponse(BaseModel):
    summary: str
    confidence: float

# Secure: Use env variable
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/rca", response_model=RCAResponse)
def generate_rca(request: RCARequest):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Summarize this log: {request.logContext}"}],
            temperature=0.3
        )
        summary = response.choices[0].message.content
        return RCAResponse(summary=summary, confidence=0.90)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
