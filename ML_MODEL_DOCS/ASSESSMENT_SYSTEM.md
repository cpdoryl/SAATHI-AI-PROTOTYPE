# SAATHI AI — Psychological Assessment System
## Document: Clinical Assessment Module
### Version: 1.0 | Date: 2026-03-17 | Status: COMPLETE

---

## 1. SYSTEM OVERVIEW

The SAATHI AI Assessment System delivers 8 validated clinical screening instruments
within the therapeutic chat workflow. Assessments are administered conversationally,
scored automatically, and presented as interactive charts and a printable report.

### The 8 Assessments

| ID      | Full Name                            | Condition        | Questions | Max Score | Time   |
|---------|--------------------------------------|------------------|-----------|-----------|--------|
| PHQ-9   | Patient Health Questionnaire-9       | Depression       | 9         | 27        | ~3 min |
| GAD-7   | Generalized Anxiety Disorder-7       | Anxiety          | 7         | 21        | ~2 min |
| PCL-5   | PTSD Checklist for DSM-5             | PTSD             | 20        | 80        | ~7 min |
| ISI     | Insomnia Severity Index              | Insomnia         | 7         | 28        | ~2 min |
| OCI-R   | Obsessive Compulsive Inventory-Rev.  | OCD              | 18        | 72        | ~5 min |
| SPIN    | Social Phobia Inventory              | Social Anxiety   | 17        | 68        | ~4 min |
| PSS-10  | Perceived Stress Scale               | Stress           | 10        | 40        | ~3 min |
| WHO-5   | WHO Well-Being Index                 | Wellbeing        | 5         | 100       | ~1 min |

---

## 2. ARCHITECTURE

```
Patient conversation
      |
      v
AssessmentRouterService.route(history)        ← triggers after 3+ therapeutic turns
      |
      +---> rule-based signal detection (production)
      |     OR RoBERTa ML model (when weights trained)
      |
      v
Chat UI offers primary assessment naturally
      |
      v
AssessmentPage (React)
      |
      +---> Dashboard view (8 assessment cards)
      +---> Taking view   (question-by-question form)
      +---> Results view  (score gauge + radar + bar charts + severity)
      +---> Report view   (printable clinical summary with tables + charts)
      |
      v
POST /api/v1/assessments/{patient_id}/submit
      |
      v
AssessmentService.score()                     ← subscale scoring, crisis detection
AssessmentService.generate_report()           ← clinical report with recommendations
      |
      v
DB → Assessment table (score, severity, crisis_flag, responses)
```

---

## 3. SCORING LOGIC

### 3.1 Subscale Dimensions

Each assessment is broken into clinical subscales for multi-dimensional charting:

| Assessment | Subscales |
|------------|-----------|
| PHQ-9      | Mood, Sleep & Energy, Appetite, Self-Worth, Concentration, Psychomotor, Suicidal Ideation |
| GAD-7      | Worry, Restlessness, Irritability, Fear |
| PCL-5      | Intrusion, Avoidance, Negative Cognitions, Hyperarousal |
| ISI        | Sleep Onset, Sleep Maintenance, Sleep Satisfaction, Daytime Impact |
| OCI-R      | Hoarding, Checking, Ordering, Counting, Contamination, Obsessing |
| SPIN       | Fear, Avoidance, Physiological |
| PSS-10     | Perceived Stress, Perceived Coping |
| WHO-5      | Positive Mood, Vitality, General Interest |

### 3.2 Special Scoring Rules

**PSS (Perceived Stress Scale)**:
Items 4, 5, 7, 8 (1-indexed) are **reverse-scored**. Score = max_val - raw_response.

**WHO-5**:
Raw total (0–25) is **multiplied by 4** to produce 0–100 scale.

### 3.3 Severity Bands

| Assessment | Band | Range | Color |
|------------|------|-------|-------|
| PHQ-9 | None-Minimal | 0–4 | Green |
| PHQ-9 | Mild | 5–9 | Light Green |
| PHQ-9 | Moderate | 10–14 | Yellow |
| PHQ-9 | Moderately Severe | 15–19 | Orange |
| PHQ-9 | Severe | 20–27 | Red |
| GAD-7 | Minimal | 0–4 | Green |
| GAD-7 | Mild | 5–9 | Light Green |
| GAD-7 | Moderate | 10–14 | Yellow |
| GAD-7 | Severe | 15–21 | Red |
| PCL-5 | Minimal | 0–31 | Green |
| PCL-5 | Moderate | 32–44 | Yellow |
| PCL-5 | Moderately Severe | 45–59 | Orange |
| PCL-5 | Severe | 60–80 | Red |
| ISI | No Insomnia | 0–7 | Green |
| ISI | Subthreshold | 8–14 | Light Green |
| ISI | Moderate | 15–21 | Yellow |
| ISI | Severe | 22–28 | Red |
| OCI-R | Below Cutoff | 0–20 | Green |
| OCI-R | Mild-Moderate | 21–40 | Yellow |
| OCI-R | Moderate-Severe | 41–60 | Orange |
| OCI-R | Severe | 61–72 | Red |
| SPIN | Minimal | 0–20 | Green |
| SPIN | Mild | 21–30 | Light Green |
| SPIN | Moderate | 31–40 | Yellow |
| SPIN | Severe | 41–50 | Orange |
| SPIN | Very Severe | 51–68 | Red |
| PSS | Low Stress | 0–13 | Green |
| PSS | Moderate Stress | 14–26 | Yellow |
| PSS | High Stress | 27–40 | Red |
| WHO-5 | Likely Depression | 0–28 | Red |
| WHO-5 | Poor Wellbeing | 29–50 | Orange |
| WHO-5 | Moderate Wellbeing | 51–72 | Yellow |
| WHO-5 | Good Wellbeing | 73–100 | Green |

### 3.4 Crisis Detection

PHQ-9 Question 9 (suicidal ideation, 0-indexed: Q8) is flagged as a crisis
indicator. Any response ≥ 1 sets `crisis_flag = True` in the score result,
which:
- Displays an immediate crisis alert banner on the Results screen
- Logs a WARNING-level event in the server
- Appears prominently in the clinical report

---

## 4. API ENDPOINTS

### 4.1 List All Assessments
```
GET /api/v1/assessments/
Response: { assessments: [...], total: 8 }
```

### 4.2 Get Questions
```
GET /api/v1/assessments/{type}/questions
Example: GET /api/v1/assessments/PHQ-9/questions
Response: { assessment_type, assessment_name, condition, questions: [...] }
```

### 4.3 Quick Score (no DB)
```
POST /api/v1/assessments/score
Body: { assessment_type: "PHQ-9", responses: [0,1,2,0,1,0,1,0,0], generate_report: true }
Response: { score_result: {...}, report: {...} }
```

### 4.4 Submit + Persist
```
POST /api/v1/assessments/{patient_id}/submit
Body: { assessment_type: "PHQ-9", responses: [...], patient_name: "John" }
Response: { patient_id, record_id, score_result: {...}, report: {...} }
```

### 4.5 History
```
GET /api/v1/assessments/{patient_id}/history
Response: { patient_id, total, assessments: [...] }
```

### 4.6 Report
```
GET /api/v1/assessments/{patient_id}/report/{record_id}
Response: { patient_id, record_id, report: {...} }
```

---

## 5. FRONTEND COMPONENTS

### 5.1 AssessmentPage Views

| View | Description |
|------|-------------|
| `dashboard` | 8 assessment cards with gradient headers, condition icons, question counts |
| `taking` | Question-by-question form with progress bar, dot navigation, radio-style answers |
| `results` | Score gauge ring, radar chart, bar chart, dimension breakdown table, severity scale |
| `report` | Full printable report with tables, both charts, scoring guide, disclaimer |

### 5.2 Charts Used

| Chart | Library | Purpose |
|-------|---------|---------|
| Score gauge ring | SVG (custom) | Total score visualization |
| Radar chart | Recharts `RadarChart` | Multi-dimensional symptom profile vs. normal |
| Bar chart | Recharts `BarChart` | Per-subscale scores with normal range reference |
| Progress bars | Tailwind CSS | Per-dimension progress in results table |

### 5.3 Normal Range Display

The bar chart renders two bars per subscale:
- **Score** (indigo = within normal, orange = elevated)
- **Normal Max** (green, semi-transparent) — shows clinical normal ceiling

The radar chart overlays:
- **Your Score** (filled indigo polygon)
- **Normal Range** (dashed green polygon)

---

## 6. ASSESSMENT ROUTER

### 6.1 Rule-Based (Default)

The `AssessmentRouterService` uses keyword signal detection:
```python
svc = AssessmentRouterService()
result = svc.route(conversation_history)
# Triggers after 3+ therapeutic turns
```

Signal dictionaries map clinical keywords to each assessment.
Confidence = hits / (signal_count * 0.3), capped at 1.0.
Threshold: 0.15 (returns top 3 recommendations).

### 6.2 ML Mode (Trained Weights)

When `ASSESSMENT_ROUTER_MODEL_PATH` is set in config and trained
RoBERTa weights exist:

```env
ASSESSMENT_ROUTER_MODEL_PATH=./ml_models/assessment_router
```

The service auto-loads the model at startup and uses per-assessment
thresholds from `thresholds.json`. See `ML_MODEL_DOCS/10_ASSESSMENT_ROUTER.md`
for training details.

---

## 7. INTEGRATION WITH CHAT WORKFLOW

```python
# In chat_routes.py — after 3+ therapeutic turns

from services.assessment_router_service import AssessmentRouterService
router_svc = AssessmentRouterService()

assessment_result = router_svc.route(session.get_history())

if not assessment_result['no_assessment_needed']:
    offer = router_svc.build_offer_message(assessment_result)
    return {
        "message": offer,
        "assessment_suggested": assessment_result['primary_assessment'],
        "assessment_result": assessment_result,
    }
```

### LLM Prompt Injection (post-assessment)

```python
from services.assessment_service import AssessmentService
svc = AssessmentService()
context_block = svc.build_llm_context_block(score_result)
# Inject into LLM system prompt
```

---

## 8. REPORT STRUCTURE

Each report contains:

| Section | Content |
|---------|---------|
| Header | Assessment name, date, patient name |
| Score summary | Total score / max, severity badge |
| Clinical interpretation | Plain-language description |
| Crisis alert (if flagged) | Red banner with next steps |
| Domain scores table | Per-subscale: score, max, normal range, status |
| Radar chart | Symptom profile vs. normal |
| Bar chart | Domain scores vs. normal max |
| Elevated domains | Highlighted domains above normal |
| Score guide | Severity bands reference |
| Disclaimer | AI screening tool caveat |

---

## 9. FILES CREATED / MODIFIED

| File | Change |
|------|--------|
| `server/services/assessment_service.py` | Full rewrite — all 8 assessments, subscales, normal ranges, scoring, report generation |
| `server/services/assessment_router_service.py` | NEW — rule-based + ML router |
| `server/routes/assessment_routes.py` | Expanded — 6 endpoints including quick-score and report |
| `client/src/pages/AssessmentPage.tsx` | Full rewrite — 4 views, radar + bar charts, printable report |
| `ML_MODEL_DOCS/ASSESSMENT_SYSTEM.md` | NEW — this document |

---

## 10. KNOWN LIMITATIONS & NEXT STEPS

| Item | Priority | Notes |
|------|----------|-------|
| PCL-5, OCI-R, SPIN questions loaded inline in frontend | P2 | Move to API fetch for full question text |
| Assessment history UI (past results dashboard) | P1 | Patient portal needs timeline view |
| Longitudinal tracking chart | P2 | Show score trends over time |
| RoBERTa router training | P2 | Train with `10_assessment_router_v1.json` dataset |
| Email/PDF report delivery | P3 | Auto-send report to patient + clinician |
| Multi-language questions | P3 | Hindi/regional language support |

---

*Document Version: 1.0 | System Version: saathi_assessment_v1 | Last Updated: 2026-03-17*
