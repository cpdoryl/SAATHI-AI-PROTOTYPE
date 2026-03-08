# SAATHI AI — Database Blueprint
## PostgreSQL + SQLAlchemy + Alembic
### Version: 1.0 | Date: 2026-03-08 | Status: In Progress

---

## 1. DATABASE DESIGN PRINCIPLES

- Multi-tenant: every table scoped to `tenant_id`
- UUID primary keys (not auto-increment integers)
- Soft deletes via `is_active` flag (not physical DELETE)
- Async SQLAlchemy 2.0 (`AsyncSession`) throughout
- SQLite for local dev, PostgreSQL for production
- All migrations via Alembic (never `Base.metadata.create_all` in prod)

---

## 2. TABLE SPECIFICATIONS

### `tenants`
```sql
id              VARCHAR PK DEFAULT uuid_generate_v4()
name            VARCHAR(255) NOT NULL
domain          VARCHAR(255) UNIQUE NOT NULL      -- e.g. "apollo.saathai.in"
widget_token    VARCHAR(255) UNIQUE NOT NULL      -- embedded in <script> tag
plan            VARCHAR(50) DEFAULT 'basic'       -- basic/professional/enterprise
is_active       BOOLEAN DEFAULT TRUE
pinecone_namespace VARCHAR(255)                   -- per-tenant RAG namespace
razorpay_account_id VARCHAR(255)
created_at      TIMESTAMP DEFAULT NOW()
```

### `clinicians`
```sql
id                    VARCHAR PK DEFAULT uuid_generate_v4()
tenant_id             VARCHAR FK → tenants.id NOT NULL
email                 VARCHAR(255) UNIQUE NOT NULL
hashed_password       VARCHAR(255) NOT NULL         -- bcrypt, cost=12
full_name             VARCHAR(255) NOT NULL
specialization        VARCHAR(255)
google_calendar_token TEXT                          -- encrypted OAuth2 JSON
is_active             BOOLEAN DEFAULT TRUE
created_at            TIMESTAMP DEFAULT NOW()
```

### `patients`
```sql
id                  VARCHAR PK DEFAULT uuid_generate_v4()
tenant_id           VARCHAR FK → tenants.id NOT NULL
clinician_id        VARCHAR FK → clinicians.id NULLABLE
full_name           VARCHAR(255)
phone               VARCHAR(20)
email               VARCHAR(255)
stage               ENUM('lead','active','dropout','archived') DEFAULT 'lead'
language            VARCHAR(10) DEFAULT 'en'
cultural_context    VARCHAR(50)                    -- 'indian_urban'/'indian_rural'
last_active         TIMESTAMP DEFAULT NOW()
dropout_risk_score  FLOAT DEFAULT 0.0              -- 0.0-1.0, updated daily
created_at          TIMESTAMP DEFAULT NOW()
```
**Index**: `(tenant_id, stage)` for dashboard queries

### `therapy_sessions`
```sql
id              VARCHAR PK DEFAULT uuid_generate_v4()
patient_id      VARCHAR FK → patients.id NOT NULL
stage           INTEGER DEFAULT 1                 -- 1=lead, 2=therapy, 3=dropout
current_step    INTEGER DEFAULT 0                 -- 0-11 CBT steps
status          ENUM('pending','in_progress','completed','crisis_escalated')
crisis_score    FLOAT DEFAULT 0.0
session_summary TEXT                              -- AI-generated at session end
ai_insights     JSON                              -- structured AI analysis
started_at      TIMESTAMP DEFAULT NOW()
ended_at        TIMESTAMP NULLABLE
```
**Index**: `(patient_id, status)` for active session lookup

### `chat_messages`
```sql
id                      VARCHAR PK DEFAULT uuid_generate_v4()
session_id              VARCHAR FK → therapy_sessions.id NOT NULL
role                    VARCHAR(20) NOT NULL       -- 'user'|'assistant'
content                 TEXT NOT NULL
crisis_keywords_detected JSON                      -- [{keyword, weight}]
created_at              TIMESTAMP DEFAULT NOW()
```
**Index**: `(session_id, created_at)` for message history

### `assessments`
```sql
id              VARCHAR PK DEFAULT uuid_generate_v4()
patient_id      VARCHAR FK → patients.id NOT NULL
assessment_type VARCHAR(20) NOT NULL              -- 'PHQ-9'|'GAD-7'|etc.
responses       JSON NOT NULL                     -- [0,1,2,3,...] answer array
score           FLOAT
severity        VARCHAR(50)                       -- 'minimal'|'mild'|'moderate'|'severe'
administered_at TIMESTAMP DEFAULT NOW()
```
**Index**: `(patient_id, assessment_type)` for history queries

### `appointments`
```sql
id                  VARCHAR PK DEFAULT uuid_generate_v4()
patient_id          VARCHAR FK → patients.id NOT NULL
clinician_id        VARCHAR FK → clinicians.id NOT NULL
scheduled_at        TIMESTAMP NOT NULL
duration_minutes    INTEGER DEFAULT 60
status              ENUM('scheduled','confirmed','completed','cancelled','no_show')
google_event_id     VARCHAR(255)                  -- Google Calendar event ID
razorpay_order_id   VARCHAR(255)
amount_inr          FLOAT
payment_status      VARCHAR(50) DEFAULT 'pending' -- pending|paid|failed|refunded
created_at          TIMESTAMP DEFAULT NOW()
```

---

## 3. MISSING TABLES TO ADD

### `audit_logs` (security requirement)
```sql
id          VARCHAR PK
actor_id    VARCHAR                     -- clinician_id or system
action      VARCHAR(100)               -- 'login'|'view_patient'|'export_data'
resource    VARCHAR(100)               -- 'patient:uuid'|'session:uuid'
ip_address  VARCHAR(45)
created_at  TIMESTAMP DEFAULT NOW()
```

### `widget_sessions` (widget-specific session tracking)
```sql
id          VARCHAR PK
tenant_id   VARCHAR FK → tenants.id
session_id  VARCHAR FK → therapy_sessions.id
widget_token VARCHAR(255)
ip_address  VARCHAR(45)
user_agent  TEXT
created_at  TIMESTAMP DEFAULT NOW()
```

---

## 4. PENDING DATABASE TASKS

| Task | Priority | File |
|------|----------|------|
| Create `audit_logs` model + Alembic migration | HIGH | `models.py` |
| Create `widget_sessions` model | MEDIUM | `models.py` |
| Add indexes on hot query paths | HIGH | Alembic migration |
| Create `scripts/setup_db.py` seeding script | HIGH | `scripts/` |
| Create `scripts/seed_test_data.py` | HIGH | `scripts/` |
| Verify Alembic migration applies cleanly on fresh DB | HIGH | `alembic/` |

---

## 5. SEEDING SCRIPT (`scripts/setup_db.py`)

Creates one demo tenant + clinician for local development:
```python
# Creates:
# - Tenant: "Demo Clinic" with widget_token="demo-token-123"
# - Clinician: admin@demo.com / password: Demo@1234
# - 3 sample patients (LEAD, ACTIVE, DROPOUT stages)
# - 1 sample therapy session with 5 chat messages
# - 1 sample PHQ-9 assessment
```

---

## 6. COMPLETION CRITERIA

Database is complete when:
- [ ] `alembic upgrade head` runs cleanly on fresh PostgreSQL
- [ ] All 7 original tables + 2 new tables created
- [ ] Indexes applied on hot query paths
- [ ] `scripts/setup_db.py` creates demo data without errors
- [ ] `pytest tests/test_database.py` passes (MISSING — needs creating)
