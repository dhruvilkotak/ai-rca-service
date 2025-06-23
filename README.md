# 🤖 AI RCA Service

This microservice uses OpenAI (GPT) to perform root cause analysis (RCA) on infrastructure logs. It is part of the **AI Infrastructure Monitoring System** and serves as the intelligence engine behind automated alert summarization.

---

## 📦 Features

- Accepts raw infrastructure logs as input
- Returns GPT-generated RCA summary with confidence score
- FastAPI-based API with input validation
- Can be deployed independently (e.g., Render, Railway)

---

## 🚀 How It Works

1. Accepts a POST request with a `logContext` string
2. Sends it to the OpenAI API (`gpt-3.5-turbo`)
3. Returns:
   - `summary`: root cause
   - `confidence`: static (for now)

---

## 🔧 Example Request

```bash
curl -X POST http://localhost:8000/rca \
  -H "Content-Type: application/json" \
  -d '{"logContext": "Service crash due to missing DB_PASSWORD env variable"}'
  ```

## Sample Response
```bash
{
  "summary": "The service crashed because the environment variable DB_PASSWORD was not set.",
  "confidence": 0.9
}```
