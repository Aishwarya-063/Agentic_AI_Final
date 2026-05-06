# NestIQ Lite

A demo-first full-stack agentic relocation concierge.

## Run locally

### Backend
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn nestiq.main:app --reload --port 8000
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:5173

## Demo flow
1. Chat-style onboarding asks one question at a time.
2. Submit profile.
3. Five specialized agents run with live status updates.
4. Dashboard shows personalized neighborhoods, vibe cards, listings, checklist, and concierge chat.

## Why this is agentic for demo
This prototype uses a central orchestrator and multiple specialized agents. Each agent has a distinct role, produces structured output, and streams progress independently to the UI.
