# JobLens

**AI-powered Job Research & Intelligence Platform** — an autonomous pipeline that discovers companies and job openings, verifies them with an LLM, and surfaces active opportunities on a dashboard.

---

## Architecture

**Research Engine** (Python)
- [Apify](https://apify.com) — web discovery and page fetching
- [Claude / Anthropic](https://www.anthropic.com) — structured extraction and verification of companies and job postings
- SQL Server — persistence (`research.Companies`, `research.Jobs`, `research.JobSources`, `research.SearchHistory`)

**Application**
- ASP.NET Core Web API (.NET 8) — read-only REST layer over the research data
- Angular 21 + TypeScript + Tailwind CSS — dashboard frontend

**Dashboard tabs**
- Overview, Companies, Jobs, Job Sources, Search History

The dashboard runs in one of two modes, chosen at build time:

```text
Local Mode
Research Engine → SQL Server → ASP.NET Core API → Angular Dashboard
```

```text
Demo Mode
Synthetic Demo Dataset → Angular Dashboard
```

**Local Mode** reads real data produced by the research engine, through the API, from your own SQL Server instance.

**Demo Mode** is a self-contained build for portfolio/demo purposes: it reads a static, synthetic dataset bundled with the app and needs **no backend and no SQL Server** to run. The demo dataset is fabricated for demonstration only and does **not** represent live job listings — nothing in it should be treated as a real, current opportunity.

---

## Tech stack

| Layer           | Technology                              |
| ---------------- | ---------------------------------------- |
| Research Engine  | Python, Apify, Claude (Anthropic API)    |
| Backend API      | ASP.NET Core Web API (.NET 8), EF Core   |
| Frontend         | Angular 21, TypeScript, Tailwind CSS     |
| Database         | SQL Server                               |

---

## Repository structure

```
JobLens/
├── research-engine/        Python research pipeline (Apify + Claude → SQL Server)
├── backend/
│   └── JobLens.API/        ASP.NET Core Web API (read-only research data endpoints)
├── frontend/
│   └── joblens-web/        Angular dashboard (Local Mode + Demo Mode)
└── README.md
```

---

## Getting started

### Local Mode (real data)

Requires .NET 8 SDK, Node.js 20+, and a SQL Server instance with the research engine's schema already applied.

```bash
cd backend/JobLens.API
cp appsettings.Development.json.example appsettings.Development.json
# edit appsettings.Development.json with your SQL Server connection string
dotnet run
```

```bash
cd frontend/joblens-web
npm install
npm start
```

Dashboard: `http://localhost:4200` · API: `http://localhost:5020`

### Demo Mode (no backend needed)

```bash
cd frontend/joblens-web
npm install
npx ng serve --configuration demo
```

Serves the dashboard against the bundled synthetic dataset only — no API, no database.

---

## Configuration

Secrets are **not** committed. The backend reads its connection string from `appsettings.Development.json` (git-ignored); use `appsettings.Development.json.example` as a template:

- `ConnectionStrings:DefaultConnection` — SQL Server connection string

The research engine's own credentials (Anthropic API key, Apify token, database connection) live in `research-engine/.env` (git-ignored) — see `research-engine/.env.example`.

---

## License

Not yet licensed. All rights reserved by the author.
