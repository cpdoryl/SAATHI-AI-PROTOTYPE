# Model Document 12: Clinical Assessment Models
## All 8 Standardised Assessments — Complete Reference
## Saathi AI Therapeutic Co-Pilot Platform

---

## Table of Contents
1. [Overview & Clinical Purpose](#1-overview--clinical-purpose)
2. [PHQ-9 — Patient Health Questionnaire-9 (Depression)](#2-phq-9--patient-health-questionnaire-9)
3. [GAD-7 — Generalized Anxiety Disorder-7](#3-gad-7--generalized-anxiety-disorder-7)
4. [DASS-21 — Depression Anxiety Stress Scales](#4-dass-21--depression-anxiety-stress-scales)
5. [PSS-10 — Perceived Stress Scale](#5-pss-10--perceived-stress-scale)
6. [WEMWBS — Warwick-Edinburgh Mental Well-Being Scale](#6-wemwbs--warwick-edinburgh-mental-well-being-scale)
7. [PCL-5 — PTSD Checklist for DSM-5](#7-pcl-5--ptsd-checklist-for-dsm-5)
8. [AUDIT — Alcohol Use Disorders Identification Test](#8-audit--alcohol-use-disorders-identification-test)
9. [CAGE-AID — Cut-Annoyed-Guilty-Eye Opener (Adapted Including Drugs)](#9-cage-aid)
10. [Assessment Administration Flow in Saathi](#10-assessment-administration-flow-in-saathi)
11. [Scoring Service Integration](#11-scoring-service-integration)
12. [Post-Assessment LLM Prompt Context](#12-post-assessment-llm-prompt-context)
13. [Assessment Report Generation](#13-assessment-report-generation)
14. [Longitudinal Tracking & Progress Monitoring](#14-longitudinal-tracking--progress-monitoring)
15. [Clinical Limitations & Disclaimer](#15-clinical-limitations--disclaimer)

---

## 1. Overview & Clinical Purpose

### Why Standardised Assessments?
The 8 validated clinical assessments in Saathi serve three core functions:

1. **Baseline measurement**: Establish a quantified starting point for each user's mental health status across dimensions (depression, anxiety, stress, PTSD, substance use, wellbeing)
2. **Progress tracking**: Re-administer assessments at intervals to measure change — enabling data-driven evidence of therapeutic effectiveness
3. **Clinical routing**: Assessment scores inform the Assessment Router (Model 10) and trigger appropriate therapeutic interventions, referral decisions, and escalation protocols

### Assessment Selection Rationale

| Assessment | Condition | Evidence Base | Validation Context |
|------------|-----------|---------------|--------------------|
| PHQ-9 | Depression | Gold standard; Spitzer et al. 1999 | Primary care, mental health, general population |
| GAD-7 | Anxiety | Spitzer et al. 2006 | Primary care; strong cross-cultural validity |
| DASS-21 | Depression+Anxiety+Stress | Lovibond & Lovibond 1995 | Clinical + general population; validated in India |
| PSS-10 | Perceived Stress | Cohen et al. 1983 | Occupational health; widely used in India |
| WEMWBS | Mental Wellbeing | Tennant et al. 2007 | Positive health outcomes tracking |
| PCL-5 | PTSD | Weathers et al. 2013 | DSM-5 aligned; trauma screening |
| AUDIT | Alcohol Use | WHO / Babor et al. 2001 | Cross-cultural; validated in India |
| CAGE-AID | Drug/Alcohol | Brown & Rounds 1995 | Brief screening; primary care |

### Assessment Timing in the Platform

```
User Journey → Assessment Points:
├── Intake (first session)      → DASS-21 + PHQ-9 or GAD-7 (based on router)
├── Week 2 check-in             → PSS-10 or WEMWBS (progress)
├── Month 1                     → Full re-assessment (same instruments as intake)
├── Post-crisis                 → PHQ-9 Q9 monitoring + PCL-5 if trauma indicated
├── On-request                  → User can request any assessment at any time
└── Router-triggered            → Assessment Router (Model 10) recommends proactively
```

---

## 2. PHQ-9 — Patient Health Questionnaire-9

### 2.1 Clinical Background

**Full Name**: Patient Health Questionnaire-9
**Developed by**: Spitzer, Kroenke, Williams (1999), Primary Care Evaluation of Mental Disorders (PRIME-MD) project
**Purpose**: Screen for and measure severity of Major Depressive Disorder (MDD)
**Gold standard**: Most widely used depression screener globally; validated across 50+ languages including Hindi
**Time to complete**: 2–3 minutes (9 questions)
**Scoring range**: 0–27

**Psychometric Properties (English):**
| Property | Value |
|----------|-------|
| Internal consistency (Cronbach's α) | 0.86–0.89 |
| Test-retest reliability | 0.84 |
| Sensitivity for MDD | 88% |
| Specificity for MDD | 88% |
| AUC | 0.95 |

**Validation in India:**
- Validated in Indian primary care (Ganguli et al., 2010): Sensitivity 0.79, Specificity 0.73
- Hindi version validated with Cronbach's α = 0.81 (Yeung et al., 2008)
- Recommended cutoff for India: ≥10 (same as global)

### 2.2 All 9 Questions (DSM-5 Criteria Aligned)

```
Over the last 2 weeks, how often have you been bothered by any of the following problems?

Response options:
0 = Not at all
1 = Several days
2 = More than half the days
3 = Nearly every day
```

| Q# | Question | DSM-5 Criterion |
|----|----------|-----------------|
| Q1 | Little interest or pleasure in doing things | Anhedonia |
| Q2 | Feeling down, depressed, or hopeless | Depressed mood |
| Q3 | Trouble falling or staying asleep, or sleeping too much | Sleep disturbance |
| Q4 | Feeling tired or having little energy | Fatigue |
| Q5 | Poor appetite or overeating | Appetite/weight change |
| Q6 | Feeling bad about yourself — or that you are a failure or have let yourself or your family down | Worthlessness/guilt |
| Q7 | Trouble concentrating on things, such as reading the newspaper or watching television | Concentration |
| Q8 | Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual | Psychomotor changes |
| Q9 | Thoughts that you would be better off dead, or of hurting yourself in some way | Suicidal ideation |

### 2.3 Scoring Algorithm

```python
@staticmethod
def score_phq9(responses: dict) -> dict:
    """
    PHQ-9 Scoring Algorithm
    Items: q1–q9 each scored 0–3
    Total: sum of all 9 items (0–27)
    """
    questions = [
        'q1_little_interest', 'q2_feeling_down', 'q3_sleep_problems',
        'q4_feeling_tired', 'q5_appetite_changes', 'q6_feeling_bad',
        'q7_concentration', 'q8_moving_slowly', 'q9_self_harm'
    ]
    total = sum(responses.get(q, 0) for q in questions)

    # Severity classification
    severity_map = [
        (4,  "none",              "No clinically significant depression"),
        (9,  "mild",              "Mild depression"),
        (14, "moderate",          "Moderate depression"),
        (19, "moderately_severe", "Moderately severe depression"),
        (27, "severe",            "Severe depression")
    ]
    severity, label = next(
        (s, l) for thresh, s, l in severity_map if total <= thresh
    )

    # Q9 CRISIS FLAG — mandatory escalation check
    q9_score = responses.get('q9_self_harm', 0)
    crisis_indicators = []
    if q9_score >= 1:
        crisis_indicators.append({
            "question": "Q9: Thoughts of self-harm or being better off dead",
            "response_value": q9_score,
            "response_label": ["Not at all","Several days","More than half days","Nearly every day"][q9_score],
            "concern_level": "critical" if q9_score >= 2 else "high",
            "action_required": "IMMEDIATE safety assessment required" if q9_score >= 2 else "Safety check recommended"
        })

    # MDD DSM-5 criteria: Q1 or Q2 must score ≥2 (criterion A)
    criterion_a_met = responses.get('q1_little_interest', 0) >= 2 or responses.get('q2_feeling_down', 0) >= 2

    # Functional impairment question (asked separately in clinical version)
    # In Saathi: assumed if total ≥ 5

    return {
        "assessment": "PHQ-9",
        "total_score": total,
        "max_score": 27,
        "severity_level": severity,
        "clinical_label": label,
        "criterion_a_met": criterion_a_met,
        "crisis_indicators": crisis_indicators,
        "requires_intervention": total >= 10 or q9_score >= 1,
        "referral_suggested": total >= 15 or q9_score >= 2,
        "item_scores": {q: responses.get(q, 0) for q in questions},
        "recommendations": _phq9_recommendations(total, q9_score)
    }

def _phq9_recommendations(total: int, q9: int) -> list:
    recs = []
    if q9 >= 2:
        recs.append("PRIORITY: Immediate safety assessment — suicidal ideation present")
        recs.append("Notify clinical team and conduct safety planning")
    elif q9 == 1:
        recs.append("Assess safety — passive suicidal ideation indicated")
    if total >= 20:
        recs.append("Severe depression: immediate referral to psychiatrist or therapist")
        recs.append("Consider medication evaluation")
    elif total >= 15:
        recs.append("Moderately severe: referral for CBT/IPT therapy recommended")
        recs.append("Monitor weekly; re-assess in 2 weeks")
    elif total >= 10:
        recs.append("Moderate: therapy (CBT, behavioural activation) recommended")
    elif total >= 5:
        recs.append("Mild: psychoeducation, self-help resources, monitor")
        recs.append("Re-assess in 4 weeks")
    return recs
```

### 2.4 Severity Table

| Score | Severity | Action |
|-------|----------|--------|
| 0–4 | None | No action needed; monitor |
| 5–9 | Mild | Psychoeducation, self-help, re-assess in 4 weeks |
| 10–14 | Moderate | Consider therapy (CBT, IPT); monitor closely |
| 15–19 | Moderately Severe | Therapy + consider medication; weekly monitoring |
| 20–27 | Severe | Immediate referral; pharmacotherapy likely needed |
| Any Q9 ≥1 | **CRISIS FLAG** | Safety assessment regardless of total score |

### 2.5 Minimal Clinically Important Difference (MCID)
- **Response**: ≥5-point reduction from baseline
- **Remission**: Total score ≤4
- **Recovery**: Sustained score ≤4 for ≥4 weeks

---

## 3. GAD-7 — Generalized Anxiety Disorder-7

### 3.1 Clinical Background

**Full Name**: Generalized Anxiety Disorder 7-item scale
**Developed by**: Spitzer, Kroenke, Williams, Löwe (2006)
**Purpose**: Screen for and measure severity of Generalized Anxiety Disorder
**Time to complete**: 2 minutes (7 questions)
**Scoring range**: 0–21
**Validated in India**: Yes (Ganguli et al.; α = 0.82)

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Internal consistency (α) | 0.92 |
| Test-retest reliability | 0.83 |
| Sensitivity for GAD | 89% |
| Specificity for GAD | 82% |
| Cutoff (recommended) | ≥10 |

### 3.2 All 7 Questions (DSM-5 GAD Criteria Aligned)

```
Over the last 2 weeks, how often have you been bothered by the following problems?

0 = Not at all | 1 = Several days | 2 = More than half the days | 3 = Nearly every day
```

| Q# | Question | DSM-5 Criterion |
|----|----------|-----------------|
| Q1 | Feeling nervous, anxious, or on edge | Excessive anxiety/worry |
| Q2 | Not being able to stop or control worrying | Difficulty controlling worry |
| Q3 | Worrying too much about different things | Multi-focus anxiety |
| Q4 | Trouble relaxing | Restlessness/keyed up |
| Q5 | Being so restless that it is hard to sit still | Restlessness |
| Q6 | Becoming easily annoyed or irritable | Irritability |
| Q7 | Feeling afraid, as if something awful might happen | Sense of impending doom |

### 3.3 Scoring Algorithm

```python
@staticmethod
def score_gad7(responses: dict) -> dict:
    questions = [
        'q1_feeling_nervous', 'q2_not_stop_worrying', 'q3_worrying_too_much',
        'q4_trouble_relaxing', 'q5_being_restless', 'q6_easily_annoyed', 'q7_feeling_afraid'
    ]
    total = sum(responses.get(q, 0) for q in questions)

    severity_map = [
        (4,  "minimal",  "Minimal anxiety — below clinical threshold"),
        (9,  "mild",     "Mild anxiety"),
        (14, "moderate", "Moderate anxiety"),
        (21, "severe",   "Severe anxiety")
    ]
    severity, label = next((s, l) for thresh, s, l in severity_map if total <= thresh)

    # Panic disorder indicator: Q7 ≥ 2 (fear of something awful)
    panic_indicator = responses.get('q7_feeling_afraid', 0) >= 2

    return {
        "assessment": "GAD-7",
        "total_score": total,
        "max_score": 21,
        "severity_level": severity,
        "clinical_label": label,
        "panic_indicator": panic_indicator,
        "requires_intervention": total >= 10,
        "referral_suggested": total >= 15,
        "item_scores": {q: responses.get(q, 0) for q in questions},
        "recommendations": _gad7_recommendations(total)
    }
```

### 3.4 Severity Table

| Score | Severity | Action |
|-------|----------|--------|
| 0–4 | Minimal | No action; lifestyle guidance |
| 5–9 | Mild | Psychoeducation, relaxation techniques, self-monitoring |
| 10–14 | Moderate | CBT (worry management, grounding); consider referral |
| 15–21 | Severe | Referral for therapy + medication evaluation; urgent |

### 3.5 GAD-7 Use Beyond GAD
The GAD-7 also screens (lower sensitivity) for:
- Panic disorder (sensitivity 74%, specificity 81%)
- Social anxiety disorder (sensitivity 72%, specificity 80%)
- Post-traumatic stress disorder (sensitivity 66%, specificity 81%)

---

## 4. DASS-21 — Depression Anxiety Stress Scales

### 4.1 Clinical Background

**Full Name**: Depression Anxiety Stress Scales (21-item short form)
**Developed by**: Lovibond & Lovibond (1995), University of New South Wales
**Purpose**: Simultaneously measure severity of depression, anxiety, and stress symptoms
**Time to complete**: 5–7 minutes (21 questions — 7 per subscale)
**Note**: Scores are **multiplied by 2** to align with DASS-42 norms
**Validated in India**: Yes (Sahoo et al., 2015); validated in Hindi (α: D=0.87, A=0.82, S=0.85)

### 4.2 All 21 Items by Subscale

```
Please rate how much each statement applied to you over the past week.

0 = Did not apply to me at all
1 = Applied to me to some degree, or some of the time
2 = Applied to me to a considerable degree, or a good part of the time
3 = Applied to me very much, or most of the time
```

**DEPRESSION Subscale (7 items):**
| Item | Statement |
|------|-----------|
| D1 | I couldn't seem to experience any positive feeling at all |
| D2 | I found it difficult to work up the initiative to do things |
| D3 | I felt that I had nothing to look forward to |
| D4 | I felt sad and depressed |
| D5 | I felt that I had lost interest in just about everything |
| D6 | I felt I wasn't worth much as a person |
| D7 | I felt that life wasn't worthwhile |

**ANXIETY Subscale (7 items):**
| Item | Statement |
|------|-----------|
| A1 | I was aware of dryness of my mouth |
| A2 | I experienced breathing difficulty |
| A3 | I experienced trembling (e.g. in the hands) |
| A4 | I was worried about situations in which I might panic |
| A5 | I felt I was close to panic |
| A6 | I was aware of the action of my heart in the absence of physical exertion |
| A7 | I felt scared without any good reason |

**STRESS Subscale (7 items):**
| Item | Statement |
|------|-----------|
| S1 | I found it hard to wind down |
| S2 | I tended to over-react to situations |
| S3 | I felt that I was using a lot of nervous energy |
| S4 | I found myself getting agitated |
| S5 | I found it difficult to relax |
| S6 | I was intolerant of anything that kept me from getting on with what I was doing |
| S7 | I felt that I was rather touchy |

### 4.3 Scoring Algorithm

```python
@staticmethod
def score_dass21(responses: dict) -> dict:
    # Raw scores (0–21 each subscale)
    depression_raw = sum(responses.get(f'd{i}', 0) for i in range(1, 8))
    anxiety_raw = sum(responses.get(f'a{i}', 0) for i in range(1, 8))
    stress_raw = sum(responses.get(f's{i}', 0) for i in range(1, 8))

    # Multiply by 2 to align with DASS-42 norms (standard requirement)
    d_score = depression_raw * 2
    a_score = anxiety_raw * 2
    s_score = stress_raw * 2

    # Severity cutoffs (using DASS-42 equivalent scores)
    def classify(score, thresholds):
        labels = ["normal", "mild", "moderate", "severe", "extremely_severe"]
        for i, thresh in enumerate(thresholds):
            if score <= thresh:
                return labels[i]
        return labels[-1]

    d_severity = classify(d_score, [9, 13, 20, 27])    # Depression thresholds
    a_severity = classify(a_score, [7, 9, 14, 19])     # Anxiety thresholds
    s_severity = classify(s_score, [14, 18, 25, 33])   # Stress thresholds

    total = d_score + a_score + s_score

    return {
        "assessment": "DASS-21",
        "total_score": total,
        "max_score": 126,
        "subscale_scores": {
            "depression": {"raw": depression_raw, "scaled": d_score, "severity": d_severity},
            "anxiety":    {"raw": anxiety_raw,    "scaled": a_score, "severity": a_severity},
            "stress":     {"raw": stress_raw,     "scaled": s_score, "severity": s_severity}
        },
        "primary_concern": max(
            [("depression", d_score), ("anxiety", a_score), ("stress", s_score)],
            key=lambda x: x[1]
        )[0],
        "requires_intervention": any(s in ["moderate","severe","extremely_severe"]
                                     for s in [d_severity, a_severity, s_severity]),
        "referral_suggested": any(s in ["severe","extremely_severe"]
                                  for s in [d_severity, a_severity, s_severity]),
        "recommendations": _dass21_recommendations(d_score, a_score, s_score,
                                                    d_severity, a_severity, s_severity)
    }
```

### 4.4 DASS-21 Severity Tables

**Depression subscale (scaled score):**
| Score | Severity |
|-------|----------|
| 0–9 | Normal |
| 10–13 | Mild |
| 14–20 | Moderate |
| 21–27 | Severe |
| 28+ | Extremely Severe |

**Anxiety subscale (scaled score):**
| Score | Severity |
|-------|----------|
| 0–7 | Normal |
| 8–9 | Mild |
| 10–14 | Moderate |
| 15–19 | Severe |
| 20+ | Extremely Severe |

**Stress subscale (scaled score):**
| Score | Severity |
|-------|----------|
| 0–14 | Normal |
| 15–18 | Mild |
| 19–25 | Moderate |
| 26–33 | Severe |
| 34+ | Extremely Severe |

---

## 5. PSS-10 — Perceived Stress Scale

### 5.1 Clinical Background

**Full Name**: Perceived Stress Scale (10-item version)
**Developed by**: Cohen, Kamarck, Mermelstein (1983), Carnegie Mellon University
**Purpose**: Measure the degree to which situations in one's life are appraised as stressful
**Time to complete**: 3 minutes (10 questions)
**Scoring range**: 0–40
**Key feature**: Measures *perceived* stress (subjective appraisal), not objective stressors
**Validated in India**: Yes; widely used in Indian occupational health research; Hindi PSS validated (α = 0.83)

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Internal consistency (α) | 0.84–0.86 |
| Test-retest reliability (2 weeks) | 0.85 |
| Convergent validity | Correlated with anxiety (r=0.65), depression (r=0.58) |

### 5.2 All 10 Questions

```
The questions ask about your feelings and thoughts during the last month.
0 = Never | 1 = Almost Never | 2 = Sometimes | 3 = Fairly Often | 4 = Very Often
```

**Regular-scored items (sum directly):**
| Q# | Question |
|----|---------|
| Q1 | In the last month, how often have you been upset because of something that happened unexpectedly? |
| Q2 | In the last month, how often have you felt that you were unable to control the important things in your life? |
| Q3 | In the last month, how often have you felt nervous and stressed? |
| Q6 | In the last month, how often have you been angered because of things that were outside of your control? |
| Q9 | In the last month, how often have you been angered because of things that were outside of your control? |
| Q10 | In the last month, how often have you felt difficulties were piling up so high that you could not overcome them? |

**Reverse-scored items (subtract from 4):**
| Q# | Question | Reverse formula |
|----|---------|----------------|
| Q4 | In the last month, how often have you felt confident about your ability to handle your personal problems? | 4 - score |
| Q5 | In the last month, how often have you felt that things were going your way? | 4 - score |
| Q7 | In the last month, how often have you been able to control irritations in your life? | 4 - score |
| Q8 | In the last month, how often have you felt that you were on top of things? | 4 - score |

### 5.3 Scoring Algorithm

```python
@staticmethod
def score_pss10(responses: dict) -> dict:
    regular_items = ['q1_upset', 'q2_unable_control', 'q3_nervous_stressed',
                     'q6_could_not_cope', 'q9_angered', 'q10_difficulties_piling']
    reverse_items = ['q4_confident', 'q5_things_going_way',
                     'q7_control_irritations', 'q8_on_top_of_things']

    regular_sum = sum(responses.get(q, 0) for q in regular_items)
    reverse_sum = sum(4 - responses.get(q, 4) for q in reverse_items)
    total = regular_sum + reverse_sum  # Range: 0–40

    # Indian adult normative data (Cohen & Janicki-Deverts, 2012 adapted)
    if total <= 13:
        level, label = "low", "Low perceived stress — within healthy range"
    elif total <= 26:
        level, label = "moderate", "Moderate perceived stress — warrants monitoring"
    else:
        level, label = "high", "High perceived stress — intervention recommended"

    # Subscale analysis
    perceived_helplessness = regular_sum   # items 1,2,3,6,9,10
    perceived_efficacy = reverse_sum       # items 4,5,7,8 (before reversal)

    return {
        "assessment": "PSS-10",
        "total_score": total,
        "max_score": 40,
        "stress_level": level,
        "clinical_label": label,
        "subscales": {
            "perceived_helplessness": perceived_helplessness,
            "perceived_self_efficacy": reverse_sum
        },
        "requires_intervention": total >= 27,
        "recommendations": _pss10_recommendations(total)
    }
```

### 5.4 Severity Table

| Score | Stress Level | Recommendations |
|-------|-------------|-----------------|
| 0–13 | Low | Maintain healthy practices; positive reinforcement |
| 14–26 | Moderate | Stress management skills; mindfulness; check-in in 4 weeks |
| 27–40 | High | Intervention recommended; therapy, stress inoculation, burnout prevention |

**Gender Norms (Cohen & Janicki-Deverts 2012):**
- Women tend to score 2–3 points higher than men (normative)
- Younger adults (18–29) tend to score higher than older adults

---

## 6. WEMWBS — Warwick-Edinburgh Mental Well-Being Scale

### 6.1 Clinical Background

**Full Name**: Warwick-Edinburgh Mental Well-Being Scale
**Developed by**: Tennant et al. (2007), Universities of Warwick and Edinburgh
**Purpose**: Measure positive mental health and wellbeing — covers hedonic and eudaimonic wellbeing
**Time to complete**: 4 minutes (14 questions)
**Scoring range**: 14–70
**Key distinction**: Unlike all other assessments, WEMWBS measures *positive* mental health — not pathology. Higher scores = better wellbeing.
**License**: Free for non-commercial use; commercial licence required (Saathi must obtain licence from University of Warwick)

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Internal consistency (α) | 0.91 |
| Test-retest reliability | 0.83 |
| Sensitivity to change | Demonstrated in RCT interventions |
| Cross-cultural validity | Validated in 20+ countries including India |

### 6.2 All 14 Statements

```
Below are some statements about feelings and thoughts.
Please select the answer that best describes your experience of each over the last 2 weeks.

1 = None of the time | 2 = Rarely | 3 = Some of the time | 4 = Often | 5 = All of the time
```

| Q# | Statement | Domain |
|----|-----------|--------|
| Q1 | I've been feeling optimistic about the future | Hedonic |
| Q2 | I've been feeling useful | Eudaimonic |
| Q3 | I've been feeling relaxed | Hedonic |
| Q4 | I've been feeling interested in other people | Social |
| Q5 | I've had energy to spare | Physical |
| Q6 | I've been dealing with problems well | Eudaimonic |
| Q7 | I've been thinking clearly | Cognitive |
| Q8 | I've been feeling good about myself | Self-worth |
| Q9 | I've been feeling close to other people | Social |
| Q10 | I've been feeling confident | Self-efficacy |
| Q11 | I've been able to make up my own mind about things | Autonomy |
| Q12 | I've been feeling loved | Social/emotional |
| Q13 | I've been interested in new things | Growth |
| Q14 | I've been feeling cheerful | Hedonic |

### 6.3 Scoring Algorithm

```python
@staticmethod
def score_wemwbs(responses: dict) -> dict:
    questions = [f'q{i}' for i in range(1, 15)]
    total = sum(responses.get(q, 1) for q in questions)  # Min = 14 (all 1s)

    # Population mean (UK adults): 51.6; India: similar range
    if total < 40:
        level, label = "low", "Low mental wellbeing — below population average"
    elif total < 60:
        level, label = "moderate", "Moderate mental wellbeing — within average range"
    else:
        level, label = "high", "High mental wellbeing — above population average"

    # Flag items with very low scores (=1) for clinical attention
    low_items = [q for q in questions if responses.get(q, 3) == 1]

    return {
        "assessment": "WEMWBS",
        "total_score": total,
        "max_score": 70,
        "min_score": 14,
        "wellbeing_level": level,
        "clinical_label": label,
        "population_comparison": "below average" if total < 40 else "average" if total < 55 else "above average",
        "low_scoring_items": low_items,  # Items scoring 1 = no time
        "requires_intervention": total < 40,
        "recommendations": _wemwbs_recommendations(total, low_items)
    }
```

### 6.4 Interpretation Table

| Score | Level | Interpretation |
|-------|-------|---------------|
| 14–39 | Low | Below population average; wellbeing support recommended |
| 40–59 | Moderate | Average range; positive psychology interventions helpful |
| 60–70 | High | Above average; maintain and build on protective factors |

**MCID**: 3-point change represents a meaningful difference in wellbeing

---

## 7. PCL-5 — PTSD Checklist for DSM-5

### 7.1 Clinical Background

**Full Name**: PTSD Checklist for DSM-5
**Developed by**: Weathers, Litz, Keane et al. (2013), National Center for PTSD / US Department of Veterans Affairs
**Purpose**: Screen for PTSD and measure symptom severity across DSM-5 clusters
**Time to complete**: 7–10 minutes (20 questions)
**Scoring range**: 0–80
**Provisional PTSD threshold**: ≥31–33 (varies by study; 33 recommended)
**Note**: PCL-5 requires a traumatic event (Criterion A). Saathi asks about index trauma in conversation before administering.

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Internal consistency (α) | 0.96 |
| Test-retest reliability (1 week) | 0.84 |
| Sensitivity at cutoff 33 | 0.78 |
| Specificity at cutoff 33 | 0.87 |

**Validated in India:** Preliminary validation shows acceptable psychometric properties (Rajkumar et al., 2021); recommended for use with Indian populations with clinical judgement.

### 7.2 DSM-5 PTSD Criterion Structure

PCL-5 maps directly to DSM-5 PTSD criteria:

| Cluster | DSM-5 Criterion | Items | Max Score |
|---------|-----------------|-------|-----------|
| B — Intrusion symptoms | ≥1 B symptom ≥2 required | Q1–Q5 | 20 |
| C — Avoidance | ≥1 C symptom ≥2 required | Q6–Q7 | 8 |
| D — Negative alterations in cognition/mood | ≥2 D symptoms ≥2 required | Q8–Q14 | 28 |
| E — Alterations in arousal/reactivity | ≥2 E symptoms ≥2 required | Q15–Q20 | 24 |

### 7.3 All 20 Questions

```
In the past month, how much were you bothered by:

0 = Not at all | 1 = A little bit | 2 = Moderately | 3 = Quite a bit | 4 = Extremely
```

**Cluster B — Intrusion:**
| Q# | Question |
|----|---------|
| Q1 | Repeated, disturbing, and unwanted memories of the stressful experience |
| Q2 | Repeated, disturbing dreams of the stressful experience |
| Q3 | Suddenly feeling or acting as if the stressful experience were actually happening again (as if you were actually back there reliving it) |
| Q4 | Feeling very upset when something reminded you of the stressful experience |
| Q5 | Having strong physical reactions when something reminded you of the stressful experience |

**Cluster C — Avoidance:**
| Q# | Question |
|----|---------|
| Q6 | Avoiding internal reminders of the stressful experience (thoughts, feelings, or physical sensations) |
| Q7 | Avoiding external reminders of the stressful experience (people, places, conversations, activities, objects, or situations) |

**Cluster D — Cognitions/Mood:**
| Q# | Question |
|----|---------|
| Q8 | Trouble remembering important parts of the stressful experience |
| Q9 | Having strong negative beliefs about yourself, other people, or the world |
| Q10 | Blaming yourself or someone else for the stressful experience or what happened after it |
| Q11 | Having strong negative feelings such as fear, horror, anger, guilt, or shame |
| Q12 | Loss of interest in activities that you used to enjoy |
| Q13 | Feeling distant or cut off from other people |
| Q14 | Trouble experiencing positive feelings |

**Cluster E — Arousal/Reactivity:**
| Q# | Question |
|----|---------|
| Q15 | Irritable behavior, angry outbursts, or acting aggressively |
| Q16 | Taking too many risks or doing things that could cause you harm |
| Q17 | Being "superalert" or watchful or on guard |
| Q18 | Feeling jumpy or easily startled |
| Q19 | Having difficulty concentrating |
| Q20 | Trouble falling or staying asleep |

### 7.4 Scoring Algorithm

```python
@staticmethod
def score_pcl5(responses: dict) -> dict:
    # Cluster scores
    cluster_b = sum(responses.get(f'q{i}', 0) for i in range(1, 6))   # Q1–Q5
    cluster_c = sum(responses.get(f'q{i}', 0) for i in range(6, 8))   # Q6–Q7
    cluster_d = sum(responses.get(f'q{i}', 0) for i in range(8, 15))  # Q8–Q14
    cluster_e = sum(responses.get(f'q{i}', 0) for i in range(15, 21)) # Q15–Q20
    total = cluster_b + cluster_c + cluster_d + cluster_e  # 0–80

    # Severity classification
    if total < 31:
        severity = "none_to_mild"
        label = "No PTSD or sub-clinical symptoms"
    elif total < 45:
        severity = "moderate"
        label = "Moderate PTSD symptoms — clinical evaluation recommended"
    elif total < 60:
        severity = "severe"
        label = "Severe PTSD symptoms — trauma-focused therapy indicated"
    else:
        severity = "extreme"
        label = "Extreme PTSD symptoms — urgent clinical evaluation"

    # DSM-5 Provisional PTSD criteria check
    # Criterion A assumed (trauma exposure confirmed in conversation)
    criterion_b = cluster_b >= 2    # ≥1 intrusion item scored ≥2
    criterion_c = cluster_c >= 2    # ≥1 avoidance item scored ≥2
    criterion_d = cluster_d >= 4    # ≥2 cognition/mood items scored ≥2 (approx)
    criterion_e = cluster_e >= 4    # ≥2 arousal items scored ≥2 (approx)

    provisional_ptsd = total >= 33 and all([criterion_b, criterion_c, criterion_d, criterion_e])

    return {
        "assessment": "PCL-5",
        "total_score": total,
        "max_score": 80,
        "severity_level": severity,
        "clinical_label": label,
        "cluster_scores": {
            "B_intrusion": cluster_b,
            "C_avoidance": cluster_c,
            "D_cognition_mood": cluster_d,
            "E_arousal_reactivity": cluster_e
        },
        "dsm5_criteria": {
            "B_met": criterion_b,
            "C_met": criterion_c,
            "D_met": criterion_d,
            "E_met": criterion_e,
            "provisional_ptsd_diagnosis": provisional_ptsd
        },
        "requires_intervention": total >= 31,
        "referral_suggested": total >= 45 or provisional_ptsd,
        "recommended_therapies": ["Prolonged Exposure (PE)", "Cognitive Processing Therapy (CPT)", "EMDR"]
        if total >= 33 else ["Trauma-informed counselling", "Stabilisation techniques"],
        "recommendations": _pcl5_recommendations(total, provisional_ptsd)
    }
```

### 7.5 PCL-5 Severity Table

| Score | Severity | Action |
|-------|----------|--------|
| 0–30 | None to Mild | Monitor; psychoeducation about trauma responses |
| 31–44 | Moderate | Clinical evaluation; trauma-informed counselling |
| 45–59 | Severe | Trauma-focused therapy (PE/CPT/EMDR); urgent referral |
| 60–80 | Extreme | Immediate psychiatric evaluation; may need intensive treatment |

**Provisional PTSD diagnosis (cutoff ≥33)**: Recommend full CAPS-5 interview by clinician.

---

## 8. AUDIT — Alcohol Use Disorders Identification Test

### 8.1 Clinical Background

**Full Name**: Alcohol Use Disorders Identification Test
**Developed by**: Babor, Higgins-Biddle, Saunders, Monteiro for the WHO (2001)
**Purpose**: Identify hazardous and harmful alcohol use and alcohol dependence
**Time to complete**: 3 minutes (10 questions)
**Scoring range**: 0–40
**WHO Recommendation**: Widely recommended for use in primary care settings globally
**Validated in India**: Yes (Benegal et al., 2003); widely used in Indian clinical settings

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Internal consistency (α) | 0.86 |
| Sensitivity for hazardous use | 92% |
| Specificity for hazardous use | 93% |
| Recommended cutoff (men) | ≥8 |
| Recommended cutoff (women) | ≥7 |

### 8.2 All 10 Questions

**Questions Q1–Q3: Alcohol Consumption (Hazardous Use Zone)**

| Q# | Question | Response Options |
|----|---------|-----------------|
| Q1 | How often do you have a drink containing alcohol? | 0=Never, 1=Monthly or less, 2=2–4 times/month, 3=2–3 times/week, 4=4+ times/week |
| Q2 | How many units of alcohol do you drink on a typical day when you are drinking? | 0=1–2, 1=3–4, 2=5–6, 3=7–9, 4=10+ |
| Q3 | How often do you have six or more units if female, or eight or more if male, on a single occasion in the last year? | 0=Never, 1=Less than monthly, 2=Monthly, 3=Weekly, 4=Daily/almost daily |

**Questions Q4–Q6: Dependence Symptoms**

| Q# | Question | Response Options |
|----|---------|-----------------|
| Q4 | How often during the last year have you found that you were not able to stop drinking once you had started? | 0=Never to 4=Daily/almost daily |
| Q5 | How often during the last year have you failed to do what was normally expected from you because of your drinking? | 0=Never to 4=Daily/almost daily |
| Q6 | How often during the last year have you needed an alcoholic drink in the morning to get yourself going after a heavy drinking session? | 0=Never to 4=Daily/almost daily |

**Questions Q7–Q10: Harmful Use**

| Q# | Question | Response Options |
|----|---------|-----------------|
| Q7 | How often during the last year have you had a feeling of guilt or remorse after drinking? | 0=Never to 4=Daily/almost daily |
| Q8 | How often during the last year have you been unable to remember what happened the night before because you had been drinking? | 0=Never to 4=Daily/almost daily |
| Q9 | Have you or somebody else been injured as a result of your drinking? | 0=No, 2=Yes but not in last year, 4=Yes during the last year |
| Q10 | Has a relative, friend, doctor, or other health worker been concerned about your drinking or suggested that you cut down? | 0=No, 2=Yes but not in last year, 4=Yes during the last year |

### 8.3 Scoring Algorithm

```python
@staticmethod
def score_audit(responses: dict) -> dict:
    questions = [f'q{i}' for i in range(1, 11)]
    total = sum(responses.get(q, 0) for q in questions)  # Range 0–40

    # WHO risk zones
    if total <= 7:
        zone = "Zone_I_low_risk"
        level = "low"
        label = "Low risk — sensible drinking"
    elif total <= 15:
        zone = "Zone_II_hazardous"
        level = "hazardous"
        label = "Hazardous use — increased risk of harm"
    elif total <= 19:
        zone = "Zone_III_harmful"
        level = "harmful"
        label = "Harmful use — alcohol causing harm"
    else:
        zone = "Zone_IV_dependent"
        level = "dependent"
        label = "Possible alcohol dependence"

    # Dependence sub-score (Q4–Q6)
    dependence_score = sum(responses.get(f'q{i}', 0) for i in range(4, 7))
    dependence_likely = dependence_score >= 4

    # Gender-specific note
    # WHO recommends lower threshold for women (≥7 vs ≥8 for men)

    # Q9 and Q10: injury/concern flags
    injury_flag = responses.get('q9', 0) >= 2
    concern_flag = responses.get('q10', 0) >= 2

    return {
        "assessment": "AUDIT",
        "total_score": total,
        "max_score": 40,
        "who_risk_zone": zone,
        "risk_level": level,
        "clinical_label": label,
        "dependence_likely": dependence_likely,
        "dependence_score": dependence_score,
        "injury_flag": injury_flag,
        "concern_from_others": concern_flag,
        "requires_intervention": total >= 8,
        "referral_suggested": total >= 16,
        "recommendations": _audit_recommendations(total, dependence_likely)
    }
```

### 8.4 AUDIT Risk Zones and WHO Interventions

| Score | Zone | Intervention Level |
|-------|------|--------------------|
| 0–7 | Zone I — Low Risk | Alcohol education; positive reinforcement |
| 8–15 | Zone II — Hazardous | Simple advice; brief motivational counselling |
| 16–19 | Zone III — Harmful | Brief counselling + monitoring; addiction referral |
| 20–40 | Zone IV — Dependent | Referral to addiction specialist; detox evaluation |

---

## 9. CAGE-AID

### 9.1 Clinical Background

**Full Name**: CAGE questionnaire Adapted to Include Drugs
**Original CAGE developed by**: Ewing, 1984 (alcohol); AID adaptation by Brown & Rounds, 1995
**Purpose**: Ultra-brief screen for drug and alcohol problems
**Time to complete**: <1 minute (4 yes/no questions)
**Scoring range**: 0–4 (1 point per "Yes")
**Validated in India**: CAGE widely used in Indian clinical settings; AID version acceptable

**Psychometric Properties:**
| Property | Value |
|----------|-------|
| Sensitivity for AUD (cutoff ≥2) | 74–89% |
| Specificity for AUD (cutoff ≥2) | 79–95% |
| Sensitivity for DUD | 70% |
| Simple, easy to remember | "CAGE" acronym |

### 9.2 All 4 Questions

```
These are yes/no questions about your past and present use of alcohol or drugs
(including prescription medications used in ways not intended by the prescriber)

Yes = 1 point | No = 0 points
```

| Letter | Q# | Question |
|--------|----|---------|
| **C** — Cut down | Q1 | Have you ever felt you ought to **Cut down** on your drinking or drug use? |
| **A** — Annoyed | Q2 | Have people **Annoyed** you by criticizing your drinking or drug use? |
| **G** — Guilty | Q3 | Have you ever felt bad or **Guilty** about your drinking or drug use? |
| **E** — Eye-opener | Q4 | Have you ever had a drink or used drugs first thing in the morning (**Eye-opener**) to steady your nerves or to get rid of a hangover? |

### 9.3 Scoring Algorithm

```python
@staticmethod
def score_cageaid(responses: dict) -> dict:
    questions = ['q1_cut_down', 'q2_annoyed', 'q3_guilty', 'q4_eye_opener']
    total = sum(1 for q in questions if responses.get(q, False))  # Count Yes responses

    if total == 0:
        level, label = "none", "No significant risk indicated"
    elif total == 1:
        level, label = "low", "Low risk — one indicator present"
    elif total == 2:
        level, label = "moderate", "Moderate risk — two indicators suggest possible disorder"
    else:  # 3–4
        level, label = "high", "High risk — three or more indicators strongly suggest substance use disorder"

    # Q4 (eye-opener) is the most specific for dependence
    dependence_indicator = responses.get('q4_eye_opener', False)

    return {
        "assessment": "CAGE-AID",
        "total_score": total,
        "max_score": 4,
        "risk_level": level,
        "clinical_label": label,
        "positive_items": [q for q in questions if responses.get(q, False)],
        "dependence_indicator": dependence_indicator,
        "requires_intervention": total >= 2,
        "referral_suggested": total >= 3,
        "next_step": "AUDIT" if total >= 2 else None,  # Progress to AUDIT for detail
        "recommendations": _cageaid_recommendations(total, dependence_indicator)
    }
```

### 9.4 CAGE-AID Scoring Table

| Score | Risk Level | Action |
|-------|-----------|--------|
| 0 | None | No action — reassure |
| 1 | Low | Note for record; gentle psychoeducation |
| 2 | Moderate | Administer AUDIT for detail; brief intervention |
| 3–4 | High | Comprehensive assessment; addiction referral |
| Q4 = Yes | Dependence flag | Physical dependence possible; medical assessment |

---

## 10. Assessment Administration Flow in Saathi

### 10.1 Conversational Administration Protocol

Assessments are NOT presented as a clinical form — they are administered **conversationally** by the AI:

```python
ASSESSMENT_CONVERSATION_FLOW = {
    "introduction": """
"I'd like to understand better how you've been doing. Would it be okay if I asked you a
series of questions? They're a standard set used widely to get a clearer picture of how
you're feeling. It should take about {duration} minutes. Everything is completely private."
""",
    "question_framing": {
        "PHQ-9": "Over the last two weeks, how often have you been bothered by...",
        "GAD-7": "Over the last two weeks, how often have you been bothered by...",
        "DASS-21": "Over the past week, how much has this applied to you...",
        "PSS-10": "In the last month, how often have you felt...",
        "WEMWBS": "Over the last two weeks, how much of the time have you felt...",
        "PCL-5": "In the past month, how much were you bothered by...",
        "AUDIT": "I'd like to ask about your relationship with alcohol...",
        "CAGE-AID": "I'd like to ask you four brief questions about alcohol and substances..."
    },
    "one_question_at_a_time": True,  # Never show all questions at once
    "allow_pause": True,             # User can pause and continue later
    "allow_skip": True,              # User can skip uncomfortable questions
    "response_acknowledgment": True, # AI acknowledges each answer briefly
    "PCL5_special_handling": """
Before starting PCL-5, the AI must:
1. Ask about the traumatic event gently
2. Get consent to ask about trauma symptoms
3. Remind user they can stop at any time
4. Have crisis protocol ready
"""
}
```

### 10.2 Response Format for Each Assessment

```python
# Standard response options mapped to integers
RESPONSE_SCALES = {
    "PHQ-9_GAD-7": {
        0: "Not at all",
        1: "Several days",
        2: "More than half the days",
        3: "Nearly every day"
    },
    "DASS-21": {
        0: "Did not apply to me at all",
        1: "Applied to me some of the time",
        2: "Applied to me a considerable degree",
        3: "Applied to me very much"
    },
    "PSS-10": {
        0: "Never",
        1: "Almost never",
        2: "Sometimes",
        3: "Fairly often",
        4: "Very often"
    },
    "WEMWBS": {
        1: "None of the time",
        2: "Rarely",
        3: "Some of the time",
        4: "Often",
        5: "All of the time"
    },
    "PCL-5": {
        0: "Not at all",
        1: "A little bit",
        2: "Moderately",
        3: "Quite a bit",
        4: "Extremely"
    },
    "CAGE-AID": {
        True: "Yes",
        False: "No"
    }
}
```

---

## 11. Scoring Service Integration

### 11.1 Master Scoring Router

```python
# therapeutic-copilot/server/services/assessment_scoring_service.py

class AssessmentScoringService:

    ASSESSMENT_MAP = {
        "PHQ9":   AssessmentScoringService.score_phq9,
        "GAD7":   AssessmentScoringService.score_gad7,
        "DASS21": AssessmentScoringService.score_dass21,
        "PSS10":  AssessmentScoringService.score_pss10,
        "WEMWBS": AssessmentScoringService.score_wemwbs,
        "PCL5":   AssessmentScoringService.score_pcl5,
        "AUDIT":  AssessmentScoringService.score_audit,
        "CAGEAID":AssessmentScoringService.score_cageaid
    }

    @classmethod
    def score_assessment(cls, assessment_type: str, responses: dict) -> dict:
        func = cls.ASSESSMENT_MAP.get(assessment_type.upper().replace("-",""))
        if not func:
            raise ValueError(f"Unknown assessment: {assessment_type}")
        result = func(responses)
        result['scored_at'] = datetime.utcnow().isoformat()
        result['version'] = "1.0"
        # Post-scoring crisis check
        cls._check_and_escalate(result, assessment_type)
        return result

    @staticmethod
    def _check_and_escalate(result: dict, assessment_type: str):
        """Auto-trigger crisis containment if assessment reveals crisis indicator."""
        from services.crisis_containment_service import CrisisContainmentService
        crisis_indicators = result.get('crisis_indicators', [])
        if crisis_indicators:
            CrisisContainmentService().flag_assessment_crisis(
                assessment_type=assessment_type,
                indicators=crisis_indicators,
                score=result
            )
```

---

## 12. Post-Assessment LLM Prompt Context

### 12.1 Severity-to-Prompt Mapping

```python
ASSESSMENT_RESPONSE_SCRIPTS = {
    "PHQ-9": {
        "none":              "Their PHQ-9 shows minimal depression. Celebrate their resilience. Discuss protective factors.",
        "mild":              "Mild depression indicated. Validate their experience — mild doesn't mean 'not real'. Introduce behavioural activation concepts.",
        "moderate":          "Moderate depression. Take time to validate the difficulty. Gently discuss therapy options. Normalise seeking help.",
        "moderately_severe": "Moderately severe depression. Express genuine concern. Discuss referral naturally. Safety-check.",
        "severe":            "PRIORITY: Severe depression + possible safety risk. Safety check first. Referral essential. Express care clearly.",
        "crisis_q9":         "Q9 FLAGGED: Address safety immediately before discussing score. Do not proceed to debrief until safety is established."
    },
    "GAD-7": {
        "minimal":  "Below clinical threshold. Normalise anxiety. Brief psychoeducation about anxiety as adaptive.",
        "mild":     "Mild anxiety. Validate the difficulty. Introduce breathing / grounding. No catastrophising.",
        "moderate": "Moderate anxiety. CBT psychoeducation (thoughts → feelings → behaviour). Discuss worry management.",
        "severe":   "Severe anxiety. Express care. Discuss therapy. Check for panic attacks and avoidance patterns."
    },
    "PCL-5": {
        "none_to_mild": "Sub-threshold PTSD. Acknowledge any trauma history shared. Normalise trauma responses.",
        "moderate":     "PTSD symptoms present. Trauma-informed response. Do not probe for trauma details. Discuss therapy options gently.",
        "severe":       "Severe PTSD. Safety first. Validate dissociation / avoidance. Recommend trauma-focused therapy urgently.",
        "extreme":      "Extreme PTSD — treat as clinical priority. Immediate referral language. Stay with them."
    }
}

def build_post_assessment_prompt_block(assessment: str, result: dict) -> str:
    severity = result.get('severity_level') or result.get('risk_level') or result.get('stress_level') or result.get('wellbeing_level')
    script = ASSESSMENT_RESPONSE_SCRIPTS.get(assessment, {}).get(severity, "")
    crisis_flag = bool(result.get('crisis_indicators'))

    block = f"""
## Post-Assessment Context: {assessment}
- Score: {result['total_score']}/{result['max_score']}
- Severity/Level: {severity}
- Intervention Required: {result.get('requires_intervention', False)}
- Crisis Flag: {'⚠️ YES — SAFETY FIRST' if crisis_flag else 'No'}

Clinical Response Instruction:
{script}

Recommendations from scoring system:
{result.get('recommendations', 'Standard care')}

IMPORTANT: Deliver score results with warmth and context. Never read out numbers coldly.
Frame the score as 'a snapshot' not a diagnosis. Always validate effort in completing the assessment.
"""
    if crisis_flag:
        block = "⚠️ CRISIS FLAG ACTIVE — See Crisis Containment Protocol\n\n" + block
    return block
```

---

## 13. Assessment Report Generation

### 13.1 Individual Session Report Schema

```python
ASSESSMENT_REPORT_SCHEMA = {
    "report_id": "uuid",
    "user_id": "anonymized_hash",
    "session_id": "string",
    "generated_at": "ISO 8601",
    "assessment_type": "PHQ-9 | GAD-7 | DASS-21 | PSS-10 | WEMWBS | PCL-5 | AUDIT | CAGE-AID",
    "version": "1.0",
    "administration_method": "conversational_ai",

    # Scores
    "total_score": "integer",
    "max_score": "integer",
    "severity_level": "string",
    "clinical_label": "string",
    "subscale_scores": "dict (if applicable)",

    # Clinical flags
    "crisis_indicators": "list",
    "requires_intervention": "boolean",
    "referral_suggested": "boolean",

    # Context
    "administering_ai_stage": "Stage 1 | Stage 2",
    "therapeutic_step_at_time": "string",
    "emotion_at_time": "string",  # from emotion classifier

    # Recommendations
    "recommendations": "string",
    "next_assessment_date": "ISO date",

    # Therapist section (filled by human)
    "therapist_notes": "string | null",
    "therapist_id": "string | null",
    "clinical_review_date": "ISO date | null"
}
```

### 13.2 Longitudinal Comparison Report

```python
def generate_progress_report(user_id: str, assessment_type: str, history: list) -> dict:
    """Generate longitudinal progress report across multiple administrations."""
    if len(history) < 2:
        return {"error": "Need at least 2 administrations for progress report"}

    scores = [h['total_score'] for h in history]
    dates = [h['generated_at'] for h in history]

    baseline = scores[0]
    latest = scores[-1]
    change = latest - baseline
    pct_change = (change / baseline * 100) if baseline > 0 else 0

    # MCID (Minimal Clinically Important Difference)
    MCID = {"PHQ-9": 5, "GAD-7": 4, "DASS-21": 6, "PSS-10": 4, "WEMWBS": 3, "PCL-5": 10}
    mcid = MCID.get(assessment_type, 5)
    clinically_significant = abs(change) >= mcid

    trend = "improving" if change < 0 else ("worsening" if change > 0 else "stable")
    # Note: for WEMWBS, higher = better (reverse interpretation)
    if assessment_type == "WEMWBS":
        trend = "improving" if change > 0 else ("worsening" if change < 0 else "stable")

    return {
        "assessment_type": assessment_type,
        "administration_count": len(history),
        "date_range": {"first": dates[0], "last": dates[-1]},
        "score_history": list(zip(dates, scores)),
        "baseline_score": baseline,
        "current_score": latest,
        "score_change": change,
        "percent_change": round(pct_change, 1),
        "trend": trend,
        "clinically_significant_change": clinically_significant,
        "mcid_threshold": mcid,
        "severity_progression": [h['severity_level'] for h in history],
        "narrative": _generate_progress_narrative(assessment_type, trend, change, clinically_significant)
    }
```

---

## 14. Longitudinal Tracking & Progress Monitoring

### 14.1 Re-administration Schedule

```python
REASSESSMENT_SCHEDULE = {
    "PHQ-9":   {"initial_weeks": 2, "stable_weeks": 4,  "note": "Monthly in maintenance"},
    "GAD-7":   {"initial_weeks": 2, "stable_weeks": 4,  "note": "Monthly in maintenance"},
    "DASS-21": {"initial_weeks": 4, "stable_weeks": 8,  "note": "Quarterly in maintenance"},
    "PSS-10":  {"initial_weeks": 4, "stable_weeks": 8,  "note": "Quarterly"},
    "WEMWBS":  {"initial_weeks": 4, "stable_weeks": 8,  "note": "Track positive change"},
    "PCL-5":   {"initial_weeks": 4, "stable_weeks": 8,  "note": "After trauma processing"},
    "AUDIT":   {"initial_weeks": 4, "stable_weeks": 12, "note": "Quarterly"},
    "CAGE-AID":{"initial_weeks": 4, "stable_weeks": 12, "note": "If AUDIT indicated"}
}
```

### 14.2 Progress Threshold Alerts

```python
PROGRESS_ALERTS = {
    "worsening_threshold": {
        "PHQ-9": 5,    # ≥5 point increase = clinical concern
        "GAD-7": 4,
        "PCL-5": 10
    },
    "remission_threshold": {
        "PHQ-9": 4,    # Score ≤4 = remission
        "GAD-7": 4,    # Score ≤4 = remission
        "PCL-5": 30    # Score <31 = no longer provisional PTSD
    },
    "recovery_threshold": {
        "PHQ-9": 4,    # Sustained ≤4 for 4 weeks
        "WEMWBS": 60   # Above 60 = high wellbeing
    }
}
```

---

## 15. Clinical Limitations & Disclaimer

### 15.1 What These Assessments Are NOT

1. **Not diagnostic**: Only a licensed clinician can diagnose a mental health disorder. Assessment scores indicate severity of *symptoms*, not the presence of a clinical disorder.
2. **Not sufficient alone**: Assessments must be interpreted in the context of the full clinical picture, history, and functional impairment.
3. **Not crisis tools**: PHQ-9 Q9 and PCL-5 indicate risk; they are NOT substitutes for a full suicide risk assessment (C-SSRS interview).
4. **Not culturally universal without adjustment**: While all 8 assessments have Indian validation, some items may have different cultural loading. Clinician judgement applies.

### 15.2 AI-Specific Limitations

- Saathi administers assessments conversationally — responses may differ from paper-based administration (known phenomenon; typically small effect)
- Users may under-report due to perceived AI judgement (stigma effect)
- Translation/language: Hindi versions used where available; other language versions require separate validation

### 15.3 Required Disclaimers (Shown to User)

```
These questions are a screening tool only. Your results are private and
are used to help understand how you're doing and guide your support.
A score does not constitute a clinical diagnosis. If you are concerned
about your mental health, please speak with a qualified professional.

If you are in crisis or in immediate danger, please call 112 (India)
or Vandrevala Foundation: 1860-2662-345 (24/7).
```

---

## Summary Table

| Assessment | Items | Time | Range | Condition | Crisis Flag |
|------------|-------|------|-------|-----------|-------------|
| PHQ-9 | 9 | 2–3 min | 0–27 | Depression | Q9 ≥1 |
| GAD-7 | 7 | 2 min | 0–21 | Anxiety | None built-in |
| DASS-21 | 21 | 5–7 min | 0–126 | Dep+Anx+Stress | Severe subscales |
| PSS-10 | 10 | 3 min | 0–40 | Perceived Stress | High (≥27) |
| WEMWBS | 14 | 4 min | 14–70 | Wellbeing (positive) | Low (<40) |
| PCL-5 | 20 | 7–10 min | 0–80 | PTSD | Provisional ≥33 |
| AUDIT | 10 | 3 min | 0–40 | Alcohol Use | Q9 injury + score ≥16 |
| CAGE-AID | 4 | 1 min | 0–4 | Drug/Alcohol Screen | Score ≥2 → escalate |

---

*Document Version: 1.0 | Assessment Scoring Version: assessment_scoring_saathi_v1 | Last Updated: 2025-03*
*All assessments are used under their respective licences. PHQ-9 and GAD-7 are in the public domain. WEMWBS requires a commercial licence from the University of Warwick. AUDIT is reproduced with permission from the WHO.*
