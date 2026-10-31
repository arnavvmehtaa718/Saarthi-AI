# Saarthi AI – Government Benefits Navigator Portal

Saarthi AI is an enterprise-grade, AI-native multi-agent platform designed to act as an autonomous digital caseworker for citizens seeking government welfare benefits. It empowers users to build structured demographic profiles, discover central government schemes, verify eligibility with detailed reasoning traces, scan files in a secure document vault with hybrid OCR, and generate step-by-step application timelines.

---

## 🌐 Live Demo

Experience the live deployed platform:
* **Frontend Portal (Vercel)**: [https://saarthi-ai-dev.vercel.app](https://saarthi-ai-dev.vercel.app)
* **Backend API Gateway (Render)**: [https://saarthi-ai-ztrc.onrender.com](https://saarthi-ai-ztrc.onrender.com)

---

## ✨ Application Screenshots

### 1. Welcome Onboarding Landing Page
A clean, welcoming landing page enabling guest sessions, setting language preferences, and onboarding citizens into the digital casework environment.
![Landing Page](images/landing_page.png)

### 2. Analytics Dashboard & Profile Optimizer
An interactive simulation matrix calculating scheme matches instantly upon profile variations (State residency, Age, Category, Annual income). Includes interactive breakdown charts.
![Dashboard Overview](images/dashboard_overview.png)

### 3. Caseworker AI Assistant Panel
An advanced chat advisor collaborating with orchestrator agents in the background to answer queries, draft cover letters, and suggest schemes.
![AI Assistant](images/chat_assistant_dark.png)

---

## ⚙️ Citizen Journey & Multi-Agent Workflow

The system relies on a **Planner-Critic-Reflection** pattern, distributing tasks among 10 cooperative background agents. Below is the workflow triggered when a citizen interacts with the portal:

```mermaid
sequenceDiagram
    autonumber
    actor User as Citizen (User)
    participant Client as React Next.js Dashboard
    participant Backend as FastAPI Gateway
    participant Agent as Caseworker Agent (Orchestrator)
    participant DB as SQLite DB (SQLModel)
    participant Deadline as Deadline Agent
    
    User->>Client: Click "Apply" on matched scheme
    Client->>Backend: POST /schemes/status (Applied)
    Backend->>DB: Save UserScheme entry with applied status
    Backend->>Agent: Request timeline generation
    Note over Agent,Deadline: Deadline agent maps approval stage durations
    Agent->>Deadline: Calculate milestone date rules
    Deadline->>Agent: Return list of 4 progress events
    Agent->>DB: Save timeline events (Submitted -> Doc Verified -> Eligibility -> Approval)
    Backend-->>Client: Success response (Refresh Analytics)
    Note over Client: UI auto-navigates to Timeline tab
    Client->>User: Display live milestone timeline
```

### Specialized Cooperative Agent Roles:
1. **Planner Agent**: Schedules validation sequences.
2. **Citizen Profile Agent**: Formulates demographic vectors from chat context.
3. **Scheme Discovery Agent**: Queries databases for rules-based filter matches.
4. **Eligibility Agent**: Performs strict fine-print checks (e.g. state-specific rules and age restrictions).
5. **Document Intelligence Agent**: Triggers OCR engines, checking document expiration and duplicates.
6. **Application Prep Agent**: Drafts formal cover letters in plain text or markdown.
7. **Deadline Monitor Agent**: Computes stage durations and schedules milestone logs.
8. **Legal Policy Agent (ELI15)**: Simplifies dense legal rules into citizen-comprehensible text.
9. **Recommendation Agent (NGO/Coop)**: Suggests community schemes and direct local helpdesks.
10. **Translator Agent**: Automatically localizes texts into English and Hindi dynamically.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Client[Next.js Client Dashboard] <--> |REST API / JWT| Gateway[FastAPI Backend Gateway]
    Gateway <--> |SQLite / PostgreSQL| DB[(SQLModel Database)]
    Gateway --> |Coordination| Orchestrator[Multi-Agent Orchestrator]
    
    subgraph Multi-Agent Collaboration Network
        Orchestrator --> Planner[Planner Agent]
        Orchestrator --> Profile[Citizen Profile Agent]
        Orchestrator --> Discovery[Scheme Discovery Agent]
        Orchestrator --> Eligibility[Eligibility Agent]
        Orchestrator --> DocIntel[Document Intelligence Agent]
        Orchestrator --> Prep[Application Prep Agent]
        Orchestrator --> Deadline[Deadline Monitor Agent]
        Orchestrator --> Legal[Legal Policy Agent ELI15]
        Orchestrator --> Rec[Recommendation Agent NGO]
        Orchestrator --> Trans[AI Translator Agent]
        Orchestrator --> Memory[Memory Agent]
        
        Critic[Critic Agent] --> |Validation & Self-Correction| Orchestrator
    end
    
    subgraph Services
        DocIntel --> |Hybrid OCR| OCRService[OCR Service]
        OCRService --> LocalScan[Local Regex & PyPDF Parser]
        OCRService --> MultimodalAI[Gemma 4 Vision Multimodal OCR]
    end
```

---

## 📂 Directory Structure

```
saarthi-ai/
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI workflow
├── backend/
│   ├── app/                 # Multi-agent implementation
│   │   ├── agents/          # Agent orchestration classes
│   │   ├── core/            # Security, database, configuration
│   │   ├── routes/          # FastAPI routers
│   │   ├── services/        # Auxiliary services (OCR parser)
│   │   ├── models.py        # SQLModel schemas
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # pytest test suite
│   ├── requirements.txt     # Python packages
│   └── Dockerfile
├── frontend/
│   ├── app/                 # Next.js App Router
│   ├── components/          # React Components (Vault, Simulator, Accessibility)
│   ├── public/              # Static assets
│   │   └── images/          # Illustration graphics
│   ├── package.json
│   └── Dockerfile
├── images/                  # Project screenshots (used in README)
│   ├── landing_page.png
│   ├── dashboard_overview.png
│   └── chat_assistant_dark.png
├── docker-compose.yml
└── README.md
```

---

## 🧪 CI/CD Workflows

This project includes a **GitHub Actions CI Pipeline** configured in `.github/workflows/ci.yml`. On every `push` and `pull_request` to the `main` or `master` branches, the runner:
1. Sets up Python, installs dependencies, and runs the backend unit test suite (`pytest`).
2. Sets up Node.js, installs frontend packages (`npm ci`), and runs `npm run build` to validate React/Next.js syntax and configuration.

---

## 🚀 Local Setup & Quickstart

### Prerequisites
* Python 3.11+
* Node.js 20+
* npm

### 1. Setup Backend
1. Open a terminal in the `backend/` directory.
2. Initialize virtual environment and install packages:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. Copy `backend/.env.example` to `backend/.env` and fill in your values. The backend loads this file automatically:
   ```
   DATABASE_URL=sqlite:///./saarthi.db
   SECRET_KEY=replace-with-a-long-random-string
   ENVIRONMENT=development

   # Deterministic offline mode (default)
   AI_PROVIDER=mock

   # Gemma 4 via a self-hosted OpenAI-compatible vLLM/Ollama endpoint
   AI_PROVIDER=gemma
   GEMMA_BASE_URL=http://127.0.0.1:8000/v1
   GEMMA_API_KEY=local-gemma
   GEMMA_MODEL=google/gemma-4-12B-it   # or google/gemma-4-31B-it

   # Or Gemma 4 through the Gemini API when GEMMA_BASE_URL is empty
   GEMINI_API_KEY=your_gemini_api_key
   GEMMA_GEMINI_MODEL=gemma-4-31b-it   # or gemma-4-26b-a4b-it
   ```
   *`AI_PROVIDER=mock` keeps every response deterministic and offline. Raw document bytes are only sent to a self-hosted Gemma 4 endpoint; PDFs are parsed locally and only redacted text is sent. Check the active provider at `GET /ai/status`.*

   To run the live Gemma 4 text, JSON, vision, and multilingual tests, configure a real key/endpoint and opt in:
   ```bash
   RUN_LIVE_GEMMA=1 pytest tests/test_live_gemma.py -v
   ```
   Without `RUN_LIVE_GEMMA=1` or a configured key/endpoint these tests skip instead of faking a successful inference.
4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *The SQLite database will automatically initialize and seed standard Indian Central welfare schemes on startup.*

### 2. Setup Frontend
1. Open a new terminal in the `frontend/` directory.
2. Copy `.env.example` to `.env` and set `NEXT_PUBLIC_API_URL` to your backend (defaults to `http://localhost:8000`).
3. Build and launch Next.js in development mode:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:3000` in your web browser. Note that the live production frontend is deployed on Vercel at [https://saarthi-ai-dev.vercel.app](https://saarthi-ai-dev.vercel.app).

---

## 🐳 Running with Docker Compose

To run the entire platform with containerized services locally:
```bash
docker-compose up --build
```
This launches the backend locally on `http://localhost:8000` (live production backend is on Render: `https://saarthi-ai-ztrc.onrender.com`) and the Next.js portal locally on `http://localhost:3000` (live production frontend is on Vercel: `https://saarthi-ai-dev.vercel.app`).

---

## ☁️ Deployment

* **Frontend**: Hosted on Vercel ([https://saarthi-ai-dev.vercel.app](https://saarthi-ai-dev.vercel.app))
* **Backend**: Hosted on Render ([https://saarthi-ai-ztrc.onrender.com](https://saarthi-ai-ztrc.onrender.com))
* **Communication**: The frontend communicates with the deployed backend using environment variables (specifically `NEXT_PUBLIC_API_URL` pointing to the Render URL).

### Deployment environment checklist

The repository does not include `render.yaml` or `vercel.json`; configure these values in the Render and Vercel dashboards.

**Render service settings**

| Setting | Value |
| --- | --- |
| Runtime | Docker (`backend/Dockerfile`, honors Render's `$PORT`) or Python 3.11 |
| Root Directory | `backend` |
| Build Command (Python runtime) | `pip install -r requirements.txt` |
| Start Command (Python runtime) | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

Render deploys from the pushed Git branch. Commit and push the updated backend before triggering a deploy, or use **Manual Deploy → Deploy latest commit** after the push.

**Render persistence**

SQLite and uploaded documents live on the local filesystem. On Render's ephemeral filesystem they are lost on every restart or redeploy. Attach a persistent disk (for example mounted at `/var/data`) and point both paths at it:

```
DATABASE_URL=sqlite:////var/data/saarthi.db
UPLOAD_DIR=/var/data/uploads
```

Render's free instance type does not support persistent disks. Use a paid disk or an external PostgreSQL URL for `DATABASE_URL` if data must survive restarts.

**Render backend environment**
```
ENVIRONMENT=production
AI_PROVIDER=gemma
GEMINI_API_KEY=<real key>                 # hosted Gemma 4 via Gemini API
# OR
GEMMA_BASE_URL=<private vLLM/Ollama URL>  # self-hosted Gemma 4
GEMMA_API_KEY=<endpoint key, if required>
GEMMA_GEMINI_MODEL=gemma-4-31b-it
GEMMA_MODEL=google/gemma-4-12B-it
GEMMA_ALLOW_DOCUMENT_BYTES=false
AI_TIMEOUT_SECONDS=90
AI_MAX_RETRIES=1
SECRET_KEY=<long random string>
DATABASE_URL=<persistent database URL>
ALLOWED_ORIGINS=https://saarthi-ai-dev.vercel.app
UPLOAD_DIR=<persistent disk path>
MAX_UPLOAD_BYTES=10485760
ALLOWED_UPLOAD_EXTENSIONS=pdf,png,jpg,jpeg
```

Do not set `GEMMA_ALLOW_DOCUMENT_BYTES=true` for a hosted endpoint unless you accept sending raw identity-document images off-device. PDFs are always parsed locally and only redacted text is sent.

**Vercel frontend environment**
```
NEXT_PUBLIC_API_URL=https://saarthi-ai-ztrc.onrender.com
```

Redeploy the Vercel project after changing this value because `NEXT_PUBLIC_*` variables are baked in at build time.

After deploying, verify `GET /health` returns `{"status": "ok"}` and `GET /ai/status` reports `mode: "live"`, `is_gemma: true`, and the expected `gemma_mode`. A `404` from either endpoint means the Render backend is still running an older build and must be redeployed.
