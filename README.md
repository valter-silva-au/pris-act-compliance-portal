# WA PRIS Act Compliance Portal

![CI](https://github.com/valter-silva-au/pris-act-compliance-portal/actions/workflows/ci.yml/badge.svg)

A web application for Western Australian Contracted Service Providers (CSPs) to manage privacy compliance under the **Privacy and Responsible Information Sharing Act 2024**.

## The Problem

The WA PRIS Act takes effect **July 1, 2026**. Any private business contracting with WA government agencies must comply with 11 Information Privacy Principles (IPPs) or risk losing their contracts. Most SMEs are unprepared — and legal consultants charge $5K+ for manual compliance.

## Features

| Feature | Description |
|---------|-------------|
| **IPP Compliance Checklist** | Self-assess against all 11 Information Privacy Principles with auto-save |
| **Privacy Officer Management** | Designate, track, and manage your mandatory Privacy Officer |
| **Privacy Impact Assessments** | Full PIA workflow: draft, review, approve/reject with risk levels |
| **Personal Information Register** | Map what data you hold, where it's stored, who accesses it |
| **Access/Correction Requests** | Track individual requests with 45-day deadline enforcement |
| **Breach Incident Logger** | Log incidents with severity, containment, and reporting timeline |
| **Compliance Dashboard** | At-a-glance status across all compliance areas |
| **Onboarding Wizard** | 4-step guided setup for new organizations |
| **Notifications** | In-app alerts for overdue requests, stale PIAs, non-compliant IPPs |
| **Audit Trail** | Timestamped log of all compliance actions for regulatory evidence |
| **Multi-tenant** | Organization isolation with role-based access (Admin, Privacy Officer, Staff) |
| **Dark/Light/System Theme** | Collapsible, responsive sidebar with theme selector |
| **Field Validation** | Australian phone format, ABN check digit, email, length limits on all fields |

## Quick Start

```bash
# Clone
git clone https://github.com/valter-silva-au/pris-act-compliance-portal.git
cd pris-act-compliance-portal

# Set up
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run with demo data
rm -f *.db
SECRET_KEY=change-me-in-production SEED_DEMO=1 uvicorn src.app.main:app --port 8080 --reload

# Open http://localhost:8080
# Login: admin@demo.com / demo1234
```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.com | demo1234 |
| Privacy Officer | privacy@demo.com | demo1234 |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite (dev) / PostgreSQL (prod)
- **Frontend:** Jinja2 templates, HTMX, Tailwind CSS (CDN)
- **Auth:** JWT via python-jose, bcrypt password hashing, cookie-based sessions
- **Validation:** Custom validators (AU phone, ABN check digit, email, enums, length)
- **Infrastructure:** Docker, GitHub Actions CI

## Docker

```bash
docker-compose up --build
# App available at http://localhost:8000
```

## Running Tests

```bash
source .venv/bin/activate
python3 -m pytest tests/ -v
```

## Project Structure

```
src/app/
  main.py              # FastAPI app, lifespan, router registration
  auth.py              # JWT auth, password hashing, login/register API
  models.py            # SQLAlchemy ORM models (11 models)
  database.py          # Engine, session, init_db()
  validators.py        # 13 reusable validators (phone, ABN, email, etc.)
  ipp.py               # IPP compliance checklist routes
  notifications.py     # In-app notification system
  seed.py              # Demo data seeding
  routes/
    web.py             # All HTML page routes (~2300 lines)
  templates/
    base.html          # Layout: responsive sidebar, theme, notifications
    dashboard.html     # Compliance overview
    ipp_checklist.html # 11 IPP self-assessment
    privacy_officer.html
    pias_*.html        # PIA list, detail, create
    data_register.html
    requests.html
    incidents*.html
    onboarding*.html   # 4-step wizard
    landing.html       # Public marketing page
    settings.html      # Org settings
    team.html          # Team management
    audit_log.html     # Filterable audit trail
    login.html / register.html
tests/
  test_*.py            # 300+ tests covering all features
```

## Built Autonomously

This entire application was built by [Agent Loops](https://github.com/valter-silva-au/agent-loops) — an AI framework that autonomously generates software from structured product specs.

### Build Stats

| Metric | Value |
|--------|-------|
| Total tasks | 31 (30 completed, 1 blocked) |
| Agent Loops passes | 4 (initial build + 3 polish passes) |
| Total API cost | ~$54 |
| Total iterations | ~35 |
| Lines of Python | ~10,000 |
| Lines of HTML | ~4,000 |
| Test count | 300+ |
| Git commits | 60+ |

### Build Timeline

1. **Pass 1** (initial build): 20 tasks, 12 iterations, $20 — core app with all compliance features
2. **Pass 2** (bug fixes): 5 tasks, 8 iterations, $12 — bcrypt fix, template fixes, audit trail, seed data
3. **Pass 3** (validation): 1 large task — **blocked** (too big for single iteration)
4. **Pass 4** (validation, decomposed): 5 small tasks, 8 iterations, $11 — all validation wired in

**Key learning:** Small, focused tasks (1-2 iterations each) succeed. Large monolithic tasks get blocked by gutter detection.

## Documentation

- [Research](docs/RESEARCH.md) — Gemini Deep Research: market analysis, regulatory landscape, business model

## Pricing (Planned)

- **Starter:** $99/month (up to 5 users)
- **Professional:** $199/month (unlimited users)

## License

MIT
