# Demo Data Seeding Usage

This document explains how to use the demo data seeding feature for local testing.

## Quick Start

To run the application with demo data:

```bash
SEED_DEMO=1 uvicorn src.app.main:app --reload
```

This will:
1. Initialize the database
2. Automatically populate demo data on startup
3. Display seed confirmation in console

## Demo Login Credentials

After seeding, you can login with these accounts:

### Admin User
- **Email:** admin@demo.com
- **Password:** demo1234
- **Role:** Admin

### Privacy Officer
- **Email:** privacy@demo.com
- **Password:** demo1234
- **Role:** Privacy Officer

## Demo Organization

- **Name:** Acme IT Services
- **ABN:** 12345678901
- **Industry:** Information Technology
- **Employees:** 50

## Seeded Data

The demo includes:

### IPP Assessments (11 total)
- **7 Compliant:** IPPs 1-7 (Collection, Use/Disclosure, Data Quality, Security, Openness, Access, Correction)
- **2 Partially Compliant:** IPPs 8-9 (Accuracy before use, Government IDs)
- **2 Not Assessed:** IPPs 10-11 (Cross-border transfer, Sensitive information)

### Privacy Impact Assessments (2 total)
1. **Customer Portal Migration to Cloud** (Approved, Medium Risk)
2. **Employee Wellness Program** (Draft, High Risk)

### Data Register Entries (3 total)
1. Customer Contact Information
2. Employee HR Records
3. Website Analytics Data

### Access Requests (1 total)
- Request from John Smith (In Progress)
- Type: Access request
- Due in 25 days

### Breach Incidents (1 total)
- Unauthorized Access to Test Database
- Status: Contained
- Severity: Medium
- Affected Records: 1,247

## Idempotent Seeding

The seed function is idempotent - running it multiple times will not create duplicate data. It checks for the existence of the demo organization (ABN: 12345678901) and skips seeding if it already exists.

## Testing

Run the seed tests to verify functionality:

```bash
python3 -m pytest tests/test_seed.py -v
```

## Docker Usage

To run with Docker and demo data:

```bash
docker-compose up -e SEED_DEMO=1
```

Or add to docker-compose.yml:

```yaml
services:
  web:
    environment:
      - SEED_DEMO=1
```
