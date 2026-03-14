# 90-Day Go-To-Market Execution Plan

*Updated March 13, 2026 — aligned with existing MyImaginationAI infrastructure*

---

## Existing Infrastructure (Already Paid For)

MyImaginationAI already runs 2 products (PermitAI, GrantsAI) on a single Vultr VPS. The PRIS Act portal slots in as **product #3** with zero additional hosting cost.

| Resource | Already Have | Incremental Cost |
|----------|-------------|-----------------|
| ABN (63 211 916 606) | Sole Trader registered | $0 |
| Vultr VPS (Sydney, 2vCPU/4GB) | Running PermitAI + GrantsAI | $0 (same VPS) |
| Cloudflare (DNS, CDN, SSL, WAF) | Both domains configured | $0 |
| Stripe (Live, AU) | PermitAI subscriptions active | $0 (tx fees only) |
| Resend (free tier) | PermitAI transactional email | $0 (add domain) |
| Caddy (reverse proxy) | Shared across products | $0 (add route) |
| Docker Compose | Both products containerized | $0 (add -p prisact) |
| PostgreSQL | Running on VPS | $0 (add database) |

**Incremental cost to launch PRIS Act portal: ~$10/year (domain only)**

---

## What Needs to Happen

### Week 1: Domain + Deployment

| Task | Details | Cost |
|------|---------|------|
| Register domain | `prisact.com.au` via VentraIP | ~$10/year |
| Register business name | "PrisAct" or "PRIS Act Portal" via ASIC | ~$40 |
| Add DNS to Cloudflare | Point to Vultr VPS IP (139.180.166.222) | $0 |
| Add Caddy route | `prisact.com.au` -> `prisact-web:8000` | $0 |
| Add Resend domain | `noreply@prisact.com.au` for transactional email | $0 |
| Add Stripe product | $99/mo Starter, $199/mo Professional | $0 |
| Deploy Docker stack | `docker-compose -p prisact up -d` on VPS | $0 |
| Switch SQLite to PostgreSQL | Create `prisact` database on existing Postgres | $0 |

**Week 1 cost: ~$50 total**

### Week 2: Production Hardening (via Agent Loops)

Tasks to add to `prd.json` and run through Agent Loops:

- TASK-032: Resend email integration (password reset, notification emails)
- TASK-033: Stripe checkout integration ($99/mo, $199/mo plans)
- TASK-034: PostgreSQL configuration (replace SQLite for production)
- TASK-035: Production Docker setup (gunicorn, health checks, env vars)
- TASK-036: Terms of Service + Privacy Policy pages
- TASK-037: Email verification on registration

### Week 3-6: Customer Acquisition

| Action | Details | Cost |
|--------|---------|------|
| Scrape Tenders WA | Build lead list of CSPs from CUA registries | $0 |
| Cold email via Resend/Brevo | 100-200 targeted emails to compliance officers | $0 |
| LinkedIn outreach | Direct messages to WA IT/construction/cleaning company owners | $0 |
| Partner with accountants | Offer affiliate deal to WA accounting firms | $0 |
| Landing page SEO | Target "PRIS Act compliance" + "WA privacy law" keywords | $0 |

**Target: 10-15 paying customers by end of Week 6**

### Week 7-12: Scale + Product #4

| Action | Details | Cost |
|--------|---------|------|
| Refine based on feedback | Fix issues, add PDF reports via Agent Loops | ~$50 API |
| LinkedIn ads (Perth only) | Hyper-local targeting of WA govt contractors | $200-500 |
| Build NDIS Compliance Portal | Product #4 via Agent Loops, 48h build | ~$50 API |
| Deploy NDIS portal | Same VPS, same stack, new domain | ~$10/yr domain |

---

## Pricing

| Plan | Price | Target |
|------|-------|--------|
| **Starter** | $99/month | 1-5 users, single org |
| **Professional** | $199/month | Unlimited users, priority support |
| **Annual** | $990/year (2 months free) | Lock in early adopters |

At $99/month: need 100 customers for $10K MRR
At $149/month (blended): need 67 customers for $10K MRR

---

## MyImaginationAI Product Portfolio

```
MyImaginationAI (Sole Trader, ABN 63 211 916 606)
├── PermitAI (permitai.com.au) — Building permit AI assistant
├── GrantsAI (grantsai.com.au) — Government grants matching
├── PRIS Act Portal (prisact.com.au) — WA privacy compliance ← NEW
└── NDIS Compliance (ndiscompliance.com.au) — Coming Week 10
```

All running on a single $24/month Vultr VPS in Sydney.

---

## Total Budget Required

| Item | Cost |
|------|------|
| Domain (prisact.com.au) | $10/year |
| ASIC business name registration | $40 |
| Agent Loops API (production tasks) | ~$50 |
| Agent Loops API (NDIS product) | ~$50 |
| LinkedIn ads (Week 7+) | $200-500 |
| **Total to launch** | **~$100** |
| **Total for 90 days** | **~$350-600** |

Everything else is already running and paid for.
