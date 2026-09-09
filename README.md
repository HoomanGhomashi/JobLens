# JobLens

**AI-Powered Job Application Tracker** — keep every application, interview, and follow-up in one place, and let AI help you tailor, summarize, and analyze your job search.

---

## What it does

JobLens helps job seekers manage their pipeline end to end:

- Track applications through stages (Saved → Applied → Interview → Offer → Rejected)
- Store job descriptions, contacts, notes, and important dates
- AI assistance (Google Gemini): summarize job postings, extract key requirements,
  match them against your profile, and draft tailored cover letters
- Personal dashboard with status breakdown and activity over time
- Secure multi-user access with JWT authentication

> Status: **Phase 0 — project scaffolding.** Features above are the product goal;
> see the roadmap for what is actually built.

---

## Tech stack

| Layer      | Technology                                   |
| ---------- | -------------------------------------------- |
| Backend    | ASP.NET Core Web API (.NET 8)                |
| Frontend   | Angular 21 + TypeScript                      |
| Styling    | Tailwind CSS                                 |
| Database   | SQL Server (EF Core)                         |
| AI         | Google Gemini API                           |
| Auth       | JWT (bearer tokens)                          |

---

## Repository structure

```
JobLens/
├── backend/
│   └── JobLens.API/        ASP.NET Core Web API
├── frontend/
│   └── joblens-web/        Angular 21 application
├── .editorconfig
├── .gitattributes
├── .gitignore
└── README.md
```

---

## Getting started

### Prerequisites

- .NET 8 SDK
- Node.js 20+ and npm
- SQL Server (LocalDB, Express, or full)
- A Google Gemini API key

### Backend

```bash
cd backend/JobLens.API
cp appsettings.Development.json.example appsettings.Development.json
# edit appsettings.Development.json: connection string, JWT key, Gemini API key
dotnet restore
dotnet run
```

API runs at `https://localhost:5001` (see `Properties/launchSettings.json`).

### Frontend

```bash
cd frontend/joblens-web
npm install
npm start
```

App runs at `http://localhost:4200`.

---

## Configuration

Secrets are **not** committed. The backend reads configuration from
`appsettings.Development.json` (git-ignored). Use
`appsettings.Development.json.example` as a template:

- `ConnectionStrings:DefaultConnection` — SQL Server connection string
- `Jwt:Key` / `Jwt:Issuer` / `Jwt:Audience` — JWT signing settings
- `Gemini:ApiKey` — Google Gemini API key

---

## Roadmap

- [x] **Phase 0** — Repository setup, backend & frontend scaffolding
- [ ] **Phase 1** — Data model, EF Core migrations, applications CRUD
- [ ] **Phase 2** — JWT authentication and user accounts
- [ ] **Phase 3** — Angular UI: list, board, and detail views with Tailwind
- [ ] **Phase 4** — Gemini integration: posting summaries and cover-letter drafts
- [ ] **Phase 5** — Dashboard and analytics

---

## License

Not yet licensed. All rights reserved by the author.
