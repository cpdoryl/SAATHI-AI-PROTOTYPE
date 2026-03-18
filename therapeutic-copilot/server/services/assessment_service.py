"""
SAATHI AI — Clinical Assessment Service
Supports 8 validated instruments: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5

Each assessment includes:
  - Full question bank
  - Response scale + labels
  - Subscale dimension mapping (for radar/bar charts)
  - Scoring bands with clinical interpretation
  - Normal range references for chart display
"""
from typing import List, Dict, Optional
from datetime import datetime


# ─── Assessment Definitions ───────────────────────────────────────────────────

ASSESSMENTS: Dict[str, Dict] = {

    # ── PHQ-9: Patient Health Questionnaire (Depression) ──────────────────────
    "PHQ-9": {
        "name": "Patient Health Questionnaire-9",
        "short_name": "PHQ-9",
        "condition": "Depression",
        "description": "Screens for depressive symptoms over the past 2 weeks. 9 questions, ~3 minutes.",
        "instructions": "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
        "questions": [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
            "Trouble concentrating on things, such as reading the newspaper or watching television",
            "Moving or speaking so slowly that other people could have noticed — or being so fidgety or restless that you have been moving around a lot more than usual",
            "Thoughts that you would be better off dead, or of hurting yourself in some way",
        ],
        "scale": [0, 1, 2, 3],
        "labels": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
        "max_score": 27,
        "subscales": {
            "Mood": [0, 1],
            "Sleep & Energy": [2, 3],
            "Appetite": [4],
            "Self-Worth": [5],
            "Concentration": [6],
            "Psychomotor": [7],
            "Suicidal Ideation": [8],
        },
        "subscale_max": {
            "Mood": 6,
            "Sleep & Energy": 6,
            "Appetite": 3,
            "Self-Worth": 3,
            "Concentration": 3,
            "Psychomotor": 3,
            "Suicidal Ideation": 3,
        },
        "normal_ranges": {
            "Mood": {"min": 0, "max": 1},
            "Sleep & Energy": {"min": 0, "max": 1},
            "Appetite": {"min": 0, "max": 0},
            "Self-Worth": {"min": 0, "max": 0},
            "Concentration": {"min": 0, "max": 0},
            "Psychomotor": {"min": 0, "max": 0},
            "Suicidal Ideation": {"min": 0, "max": 0},
        },
        "scoring": [
            (0, 4, "None-Minimal", "No significant depressive symptoms. Continue healthy habits.", "#22c55e"),
            (5, 9, "Mild", "Mild depressive symptoms. Consider watchful waiting, self-care strategies.", "#86efac"),
            (10, 14, "Moderate", "Moderate depression. Treatment plan recommended — therapy and/or medication.", "#facc15"),
            (15, 19, "Moderately Severe", "Moderately severe depression. Active treatment strongly recommended.", "#f97316"),
            (20, 27, "Severe", "Severe depression. Immediate clinical intervention required.", "#ef4444"),
        ],
        "crisis_questions": [8],  # Q9 (0-indexed: 8) — suicidal ideation
    },

    # ── GAD-7: Generalized Anxiety Disorder Scale ──────────────────────────────
    "GAD-7": {
        "name": "Generalized Anxiety Disorder-7",
        "short_name": "GAD-7",
        "condition": "Anxiety",
        "description": "Screens for generalized anxiety disorder over the past 2 weeks. 7 questions, ~2 minutes.",
        "instructions": "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
        "questions": [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid, as if something awful might happen",
        ],
        "scale": [0, 1, 2, 3],
        "labels": ["Not at all", "Several days", "More than half the days", "Nearly every day"],
        "max_score": 21,
        "subscales": {
            "Worry": [0, 1, 2],
            "Restlessness": [3, 4],
            "Irritability": [5],
            "Fear": [6],
        },
        "subscale_max": {
            "Worry": 9,
            "Restlessness": 6,
            "Irritability": 3,
            "Fear": 3,
        },
        "normal_ranges": {
            "Worry": {"min": 0, "max": 2},
            "Restlessness": {"min": 0, "max": 1},
            "Irritability": {"min": 0, "max": 0},
            "Fear": {"min": 0, "max": 0},
        },
        "scoring": [
            (0, 4, "Minimal", "Minimal anxiety. No clinical concern at this time.", "#22c55e"),
            (5, 9, "Mild", "Mild anxiety. Monitor symptoms, consider self-management strategies.", "#86efac"),
            (10, 14, "Moderate", "Moderate anxiety. Therapy (CBT) recommended.", "#facc15"),
            (15, 21, "Severe", "Severe anxiety. Clinical evaluation and treatment urgently recommended.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── PCL-5: PTSD Checklist for DSM-5 ───────────────────────────────────────
    "PCL-5": {
        "name": "PTSD Checklist for DSM-5",
        "short_name": "PCL-5",
        "condition": "PTSD",
        "description": "Screens for post-traumatic stress disorder symptoms. 20 questions, ~7 minutes.",
        "instructions": "Below is a list of problems that people sometimes have in response to a very stressful experience. Please read each problem carefully and then indicate how much you have been bothered by that problem in the past month.",
        "questions": [
            # Criterion B – Intrusion (Q1-5)
            "Repeated, disturbing, and unwanted memories of the stressful experience",
            "Repeated, disturbing dreams of the stressful experience",
            "Suddenly feeling or acting as if the stressful experience were actually happening again (as if you were actually back there reliving it)",
            "Feeling very upset when something reminded you of the stressful experience",
            "Having strong physical reactions when something reminded you of the stressful experience (e.g., heart pounding, trouble breathing, sweating)",
            # Criterion C – Avoidance (Q6-7)
            "Avoiding memories, thoughts, or feelings related to the stressful experience",
            "Avoiding external reminders of the stressful experience (e.g., people, places, conversations, activities, objects, or situations)",
            # Criterion D – Negative Cognitions (Q8-14)
            "Trouble remembering important parts of the stressful experience",
            "Having strong negative beliefs about yourself, other people, or the world (e.g., having thoughts such as: I am bad, There is something seriously wrong with me, No one can be trusted, The world is completely dangerous)",
            "Blaming yourself or someone else for the stressful experience or what happened after it",
            "Having strong negative feelings such as fear, horror, anger, guilt, or shame",
            "Loss of interest in activities that you used to enjoy",
            "Feeling distant or cut off from other people",
            "Trouble experiencing positive feelings (e.g., being unable to have loving feelings for those close to you or feeling numb)",
            # Criterion E – Hyperarousal (Q15-20)
            "Irritable behavior, angry outbursts, or acting aggressively",
            "Taking too many risks or doing things that could cause you harm",
            "Being 'superalert' or watchful or on guard",
            "Feeling jumpy or easily startled",
            "Having difficulty concentrating",
            "Trouble falling or staying asleep",
        ],
        "scale": [0, 1, 2, 3, 4],
        "labels": ["Not at all", "A little bit", "Moderately", "Quite a bit", "Extremely"],
        "max_score": 80,
        "subscales": {
            "Intrusion": [0, 1, 2, 3, 4],
            "Avoidance": [5, 6],
            "Negative Cognitions": [7, 8, 9, 10, 11, 12, 13],
            "Hyperarousal": [14, 15, 16, 17, 18, 19],
        },
        "subscale_max": {
            "Intrusion": 20,
            "Avoidance": 8,
            "Negative Cognitions": 28,
            "Hyperarousal": 24,
        },
        "normal_ranges": {
            "Intrusion": {"min": 0, "max": 4},
            "Avoidance": {"min": 0, "max": 2},
            "Negative Cognitions": {"min": 0, "max": 5},
            "Hyperarousal": {"min": 0, "max": 5},
        },
        "scoring": [
            (0, 31, "Minimal", "Minimal PTSD symptoms. No significant clinical concern.", "#22c55e"),
            (32, 44, "Moderate", "Moderate PTSD symptoms. Clinical evaluation recommended.", "#facc15"),
            (45, 59, "Moderately Severe", "Moderately severe PTSD. Trauma-focused therapy strongly recommended.", "#f97316"),
            (60, 80, "Severe", "Severe PTSD symptoms. Immediate clinical intervention required.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── ISI: Insomnia Severity Index ───────────────────────────────────────────
    "ISI": {
        "name": "Insomnia Severity Index",
        "short_name": "ISI",
        "condition": "Insomnia",
        "description": "Assesses the nature, severity, and impact of insomnia. 7 questions, ~2 minutes.",
        "instructions": "Please rate the CURRENT (i.e. last 2 weeks) SEVERITY of your insomnia problem(s).",
        "questions": [
            "Difficulty falling asleep",
            "Difficulty staying asleep (waking up at night)",
            "Problems waking up too early in the morning",
            "How SATISFIED/DISSATISFIED are you with your current sleep pattern?",
            "How NOTICEABLE to others do you think your sleep problem is in terms of impairing the quality of your life?",
            "How WORRIED/DISTRESSED are you about your current sleep problem?",
            "To what extent do you consider your sleep problem to INTERFERE with your daily functioning (e.g. daytime fatigue, ability to function at work/daily chores, concentration, memory, mood etc.)?",
        ],
        "scale": [0, 1, 2, 3, 4],
        "labels": {
            0: ["None", "Mild", "Moderate", "Severe", "Very Severe"],
            1: ["None", "Mild", "Moderate", "Severe", "Very Severe"],
            2: ["None", "Mild", "Moderate", "Severe", "Very Severe"],
            3: ["Very satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very dissatisfied"],
            4: ["Not noticeable", "Barely", "Somewhat", "Much", "Very much noticeable"],
            5: ["Not worried", "A little", "Somewhat", "Much", "Very much worried"],
            6: ["Not at all interfering", "A little", "Somewhat", "Much", "Very much interfering"],
        },
        "max_score": 28,
        "subscales": {
            "Sleep Onset": [0],
            "Sleep Maintenance": [1, 2],
            "Sleep Satisfaction": [3],
            "Daytime Impact": [4, 5, 6],
        },
        "subscale_max": {
            "Sleep Onset": 4,
            "Sleep Maintenance": 8,
            "Sleep Satisfaction": 4,
            "Daytime Impact": 12,
        },
        "normal_ranges": {
            "Sleep Onset": {"min": 0, "max": 1},
            "Sleep Maintenance": {"min": 0, "max": 2},
            "Sleep Satisfaction": {"min": 0, "max": 1},
            "Daytime Impact": {"min": 0, "max": 2},
        },
        "scoring": [
            (0, 7, "No Insomnia", "No clinically significant insomnia. Sleep health is adequate.", "#22c55e"),
            (8, 14, "Subthreshold Insomnia", "Subthreshold insomnia. Sleep hygiene education recommended.", "#86efac"),
            (15, 21, "Moderate Insomnia", "Moderate insomnia. Cognitive Behavioral Therapy for Insomnia (CBT-I) recommended.", "#facc15"),
            (22, 28, "Severe Insomnia", "Severe insomnia. Medical evaluation and CBT-I urgently recommended.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── OCI-R: Obsessive Compulsive Inventory – Revised ───────────────────────
    "OCI-R": {
        "name": "Obsessive Compulsive Inventory — Revised",
        "short_name": "OCI-R",
        "condition": "OCD",
        "description": "Measures obsessive-compulsive symptoms across 6 domains. 18 questions, ~5 minutes.",
        "instructions": "The following statements refer to experiences that many people have in their everyday lives. Circle the number that best describes HOW MUCH that experience has DISTRESSED or BOTHERED you during the PAST MONTH.",
        "questions": [
            # Washing (Q1-3)
            "I have saved up so many things that they get in the way",
            "I check things more often than necessary",
            "I get upset if objects are not arranged properly",
            "I feel compelled to count while I am doing things",
            "I find it difficult to touch an object when I know it has been touched by strangers or certain people",
            "I find it difficult to control my own thoughts",
            "I collect things I don't need",
            "I repeatedly check doors, windows, drawers, etc.",
            "I get upset if others change the way I have arranged things",
            "I feel I have to repeat certain numbers",
            "I sometimes have to wash or clean myself simply because I feel contaminated",
            "I am upset by unpleasant thoughts that come into my mind against my will",
            "I avoid throwing things away because I am afraid I might need them later",
            "I repeatedly check gas and water taps and light switches after turning them off",
            "I need things to be arranged in a particular order",
            "I feel that there are good and bad numbers",
            "I wash my hands more often and longer than necessary",
            "I frequently get nasty thoughts and have difficulty in getting rid of them",
        ],
        "scale": [0, 1, 2, 3, 4],
        "labels": ["Not at all", "A little", "Moderately", "A lot", "Extremely"],
        "max_score": 72,
        "subscales": {
            "Hoarding": [0, 6, 12],
            "Checking": [1, 7, 13],
            "Ordering": [2, 8, 14],
            "Counting": [3, 9, 15],
            "Contamination": [4, 10, 16],
            "Obsessing": [5, 11, 17],
        },
        "subscale_max": {
            "Hoarding": 12,
            "Checking": 12,
            "Ordering": 12,
            "Counting": 12,
            "Contamination": 12,
            "Obsessing": 12,
        },
        "normal_ranges": {
            "Hoarding": {"min": 0, "max": 2},
            "Checking": {"min": 0, "max": 2},
            "Ordering": {"min": 0, "max": 2},
            "Counting": {"min": 0, "max": 2},
            "Contamination": {"min": 0, "max": 2},
            "Obsessing": {"min": 0, "max": 2},
        },
        "scoring": [
            (0, 20, "Below Cutoff", "OCD symptoms below clinical threshold. No significant concern.", "#22c55e"),
            (21, 40, "Mild-Moderate OCD", "Symptoms above OCD cutoff. Clinical assessment recommended.", "#facc15"),
            (41, 60, "Moderate-Severe OCD", "Significant OCD symptoms. ERP therapy and clinical review needed.", "#f97316"),
            (61, 72, "Severe OCD", "Severe OCD symptoms. Urgent clinical evaluation required.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── SPIN: Social Phobia Inventory ──────────────────────────────────────────
    "SPIN": {
        "name": "Social Phobia Inventory",
        "short_name": "SPIN",
        "condition": "Social Anxiety",
        "description": "Screens for social anxiety disorder across fear, avoidance, and physiological domains. 17 questions, ~4 minutes.",
        "instructions": "Please indicate how much the following problems have bothered you during the past week. Mark only one answer for each problem and be sure to answer all items.",
        "questions": [
            "I am afraid of people in authority",
            "I am bothered by blushing in front of people",
            "Parties and social events scare me",
            "I avoid talking to people I don't know",
            "Being criticized scares me a lot",
            "Fear of embarrassment causes me to avoid doing things or speaking to people",
            "Sweating in front of people causes me distress",
            "I avoid going to parties",
            "I avoid activities in which I am the center of attention",
            "Talking to strangers scares me",
            "I avoid having to give speeches",
            "I would do anything to avoid being criticized",
            "Heart palpitations bother me when I am around people",
            "I am afraid of doing things when people might be watching",
            "Being embarrassed or looking stupid are among my worst fears",
            "I avoid speaking to anyone in authority",
            "Trembling or shaking in front of others is distressing to me",
        ],
        "scale": [0, 1, 2, 3, 4],
        "labels": ["Not at all", "A little bit", "Somewhat", "Very much", "Extremely"],
        "max_score": 68,
        "subscales": {
            "Fear": [0, 4, 5, 7, 10, 14],
            "Avoidance": [2, 3, 8, 9, 13, 15],
            "Physiological": [1, 6, 12, 16, 11],
        },
        "subscale_max": {
            "Fear": 24,
            "Avoidance": 24,
            "Physiological": 20,
        },
        "normal_ranges": {
            "Fear": {"min": 0, "max": 5},
            "Avoidance": {"min": 0, "max": 5},
            "Physiological": {"min": 0, "max": 4},
        },
        "scoring": [
            (0, 20, "Minimal", "Minimal social anxiety. No significant concern.", "#22c55e"),
            (21, 30, "Mild", "Mild social anxiety. Consider self-help strategies.", "#86efac"),
            (31, 40, "Moderate", "Moderate social anxiety. CBT therapy recommended.", "#facc15"),
            (41, 50, "Severe", "Severe social anxiety. Clinical treatment required.", "#f97316"),
            (51, 68, "Very Severe", "Very severe social anxiety. Urgent clinical intervention.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── PSS: Perceived Stress Scale (10 items) ─────────────────────────────────
    "PSS": {
        "name": "Perceived Stress Scale",
        "short_name": "PSS-10",
        "condition": "Stress",
        "description": "Measures the degree to which situations in life are appraised as stressful. 10 questions, ~3 minutes.",
        "instructions": "The questions in this scale ask you about your feelings and thoughts during the last month. In each case, you will be asked to indicate how often you felt or thought a certain way.",
        "questions": [
            "In the last month, how often have you been upset because of something that happened unexpectedly?",
            "In the last month, how often have you felt that you were unable to control the important things in your life?",
            "In the last month, how often have you felt nervous and stressed?",
            "In the last month, how often have you felt confident about your ability to handle your personal problems?",  # reversed
            "In the last month, how often have you felt that things were going your way?",  # reversed
            "In the last month, how often have you found that you could not cope with all the things that you had to do?",
            "In the last month, how often have you been able to control irritations in your life?",  # reversed
            "In the last month, how often have you felt that you were on top of things?",  # reversed
            "In the last month, how often have you been angered because of things that were outside of your control?",
            "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?",
        ],
        "scale": [0, 1, 2, 3, 4],
        "labels": ["Never", "Almost never", "Sometimes", "Fairly often", "Very often"],
        "reversed_items": [3, 4, 6, 7],  # 0-indexed; these items are reverse-scored
        "max_score": 40,
        "subscales": {
            "Perceived Stress": [0, 1, 2, 5, 8, 9],
            "Perceived Coping": [3, 4, 6, 7],
        },
        "subscale_max": {
            "Perceived Stress": 24,
            "Perceived Coping": 16,
        },
        "normal_ranges": {
            "Perceived Stress": {"min": 0, "max": 8},
            "Perceived Coping": {"min": 8, "max": 16},
        },
        "scoring": [
            (0, 13, "Low Stress", "Low perceived stress. Good stress management skills evident.", "#22c55e"),
            (14, 26, "Moderate Stress", "Moderate stress. Consider stress management techniques, lifestyle review.", "#facc15"),
            (27, 40, "High Stress", "High perceived stress. Clinical support and stress reduction programs recommended.", "#ef4444"),
        ],
        "crisis_questions": [],
    },

    # ── WHO-5: WHO Well-Being Index ────────────────────────────────────────────
    "WHO-5": {
        "name": "WHO Well-Being Index",
        "short_name": "WHO-5",
        "condition": "Wellbeing",
        "description": "Measures current mental wellbeing. 5 questions, ~1 minute.",
        "instructions": "Please indicate for each of the following statements which is closest to how you have been feeling over the last two weeks. Notice that higher numbers mean better well-being.",
        "questions": [
            "I have felt cheerful and in good spirits",
            "I have felt calm and relaxed",
            "I have felt active and vigorous",
            "I woke up feeling fresh and rested",
            "My daily life has been filled with things that interest me",
        ],
        "scale": [0, 1, 2, 3, 4, 5],
        "labels": ["At no time", "Some of the time", "Less than half the time", "More than half the time", "Most of the time", "All of the time"],
        "max_score": 100,  # raw 0-25, multiply by 4
        "subscales": {
            "Positive Mood": [0, 1],
            "Vitality": [2, 3],
            "General Interest": [4],
        },
        "subscale_max": {
            "Positive Mood": 40,  # (5+5)*4
            "Vitality": 40,
            "General Interest": 20,
        },
        "normal_ranges": {
            "Positive Mood": {"min": 24, "max": 40},
            "Vitality": {"min": 24, "max": 40},
            "General Interest": {"min": 12, "max": 20},
        },
        "scoring": [
            (0, 28, "Likely Depression", "Score suggests possible depression. PHQ-9 follow-up screening strongly recommended.", "#ef4444"),
            (29, 50, "Poor Wellbeing", "Low wellbeing score. Therapeutic support and lifestyle review recommended.", "#f97316"),
            (51, 72, "Moderate Wellbeing", "Moderate wellbeing. Opportunities for improvement through targeted support.", "#facc15"),
            (73, 100, "Good Wellbeing", "Good mental wellbeing. Continue current positive practices.", "#22c55e"),
        ],
        "crisis_questions": [],
    },
}


# ─── Clinical Context for LLM prompt injection ────────────────────────────────

ASSESSMENT_CLINICAL_CONTEXT = {
    "PHQ-9": {
        "condition": "depression",
        "focus": "depressive symptoms: mood, anhedonia, energy, sleep, appetite, concentration, worthlessness, suicidal ideation",
        "prompt_instruction": "Administer PHQ-9 gently. For Q9 (suicidal ideation), follow up with extra care and activate crisis protocol if needed.",
    },
    "GAD-7": {
        "condition": "generalized anxiety",
        "focus": "anxiety symptoms: worry, nervousness, irritability, concentration, restlessness, physical tension",
        "prompt_instruction": "Administer GAD-7 calmly. Normalize anxiety about taking an anxiety assessment.",
    },
    "PCL-5": {
        "condition": "PTSD",
        "focus": "trauma response: intrusions, avoidance, negative cognitions, hyperarousal",
        "prompt_instruction": "PCL-5 involves asking about trauma symptoms. Proceed with extra care. Ask permission before each cluster. Have safety resources ready.",
    },
    "ISI": {
        "condition": "insomnia",
        "focus": "sleep onset, maintenance, early waking, satisfaction, daytime impairment",
        "prompt_instruction": "Assess insomnia impact warmly. Many patients feel embarrassed about sleep difficulties — normalize.",
    },
    "OCI-R": {
        "condition": "OCD",
        "focus": "obsessive-compulsive symptoms: hoarding, checking, ordering, counting, contamination, obsessing",
        "prompt_instruction": "OCI-R assesses compulsive behaviors. Approach without judgment. Normalize that many people have these experiences.",
    },
    "SPIN": {
        "condition": "social anxiety disorder",
        "focus": "social fear, avoidance, physiological reactions in social situations",
        "prompt_instruction": "SPIN assesses social situations. Many patients find social anxiety difficult to admit — use a warm, validating tone.",
    },
    "PSS": {
        "condition": "perceived stress",
        "focus": "stress overload, loss of control, coping ability",
        "prompt_instruction": "PSS measures life stress. Acknowledge external pressures. Explore sources of stress and coping resources.",
    },
    "WHO-5": {
        "condition": "mental wellbeing",
        "focus": "positive mood, vitality, general interest, calm, daily engagement",
        "prompt_instruction": "WHO-5 is a positive wellbeing measure. Use to track progress. If score is low, consider PHQ-9 follow-up.",
    },
}


# ─── AssessmentService ─────────────────────────────────────────────────────────

class AssessmentService:
    """Score and interpret all 8 validated clinical assessments."""

    def get_all_assessments(self) -> List[Dict]:
        """Return summary info for all assessments (for dashboard)."""
        return [
            {
                "id": key,
                "name": val["name"],
                "short_name": val["short_name"],
                "condition": val["condition"],
                "description": val["description"],
                "question_count": len(val["questions"]),
                "max_score": val["max_score"],
            }
            for key, val in ASSESSMENTS.items()
        ]

    def get_questions(self, assessment_type: str) -> List[Dict]:
        """Return full question bank for an assessment."""
        key = assessment_type.upper()
        data = ASSESSMENTS.get(key)
        if not data:
            return []
        questions = []
        for i, q_text in enumerate(data["questions"]):
            # ISI has per-question labels
            labels = data["labels"]
            if isinstance(labels, dict):
                labels = labels.get(i, ["0", "1", "2", "3", "4"])
            questions.append({
                "id": i,
                "text": q_text,
                "scale": data["scale"],
                "labels": labels,
                "is_crisis_question": i in data.get("crisis_questions", []),
                "is_reversed": i in data.get("reversed_items", []),
            })
        return questions

    def score(self, assessment_type: str, responses: List[int]) -> Dict:
        """
        Score an assessment and return full result with severity, subscales, normal ranges.
        Handles reversed items (PSS).
        """
        key = assessment_type.upper()
        data = ASSESSMENTS.get(key)
        if not data:
            return {"error": f"Unknown assessment: {assessment_type}"}

        if len(responses) != len(data["questions"]):
            return {"error": f"Expected {len(data['questions'])} responses, got {len(responses)}"}

        # ── Apply reversed scoring ───────────────────────────────────────────
        scored_responses = list(responses)
        max_val = max(data["scale"])
        for idx in data.get("reversed_items", []):
            if idx < len(scored_responses):
                scored_responses[idx] = max_val - scored_responses[idx]

        # ── Total score ───────────────────────────────────────────────────────
        raw_total = sum(scored_responses)

        # WHO-5: multiply by 4 to convert to 0-100 scale
        if key == "WHO-5":
            total = raw_total * 4
        else:
            total = raw_total

        # ── Severity band ─────────────────────────────────────────────────────
        severity = "Unknown"
        severity_color = "#94a3b8"
        interpretation = ""
        for low, high, label, interp, color in data["scoring"]:
            if low <= total <= high:
                severity = label
                interpretation = interp
                severity_color = color
                break

        # ── Subscale scores ───────────────────────────────────────────────────
        subscale_scores = {}
        for subscale_name, q_indices in data["subscales"].items():
            sub_raw = sum(scored_responses[i] for i in q_indices if i < len(scored_responses))
            # WHO-5 subscales also x4
            if key == "WHO-5":
                sub_raw = sub_raw * 4
            subscale_scores[subscale_name] = {
                "score": sub_raw,
                "max": data["subscale_max"][subscale_name],
                "percentage": round(sub_raw / data["subscale_max"][subscale_name] * 100, 1) if data["subscale_max"][subscale_name] > 0 else 0,
                "normal_min": data["normal_ranges"][subscale_name]["min"],
                "normal_max": data["normal_ranges"][subscale_name]["max"],
            }

        # ── Crisis check ──────────────────────────────────────────────────────
        crisis_flag = False
        crisis_details = []
        for crisis_q in data.get("crisis_questions", []):
            if crisis_q < len(responses) and responses[crisis_q] >= 1:
                crisis_flag = True
                crisis_details.append({
                    "question": crisis_q,
                    "text": data["questions"][crisis_q],
                    "response": responses[crisis_q],
                    "label": data["labels"][responses[crisis_q]] if isinstance(data["labels"], list) else str(responses[crisis_q]),
                })

        return {
            "assessment_type": key,
            "assessment_name": data["name"],
            "condition": data["condition"],
            "total_score": total,
            "max_possible": data["max_score"],
            "score_percentage": round(total / data["max_score"] * 100, 1),
            "severity": severity,
            "severity_color": severity_color,
            "interpretation": interpretation,
            "subscale_scores": subscale_scores,
            "crisis_flag": crisis_flag,
            "crisis_details": crisis_details,
            "responses": responses,
            "scored_at": datetime.utcnow().isoformat(),
        }

    def generate_report(self, assessment_type: str, score_result: Dict, patient_name: Optional[str] = None) -> Dict:
        """
        Generate a structured clinical report from a scored assessment.
        Designed to be human-readable (patient + clinician view).
        """
        key = assessment_type.upper()
        data = ASSESSMENTS.get(key)
        if not data or "error" in score_result:
            return {"error": "Cannot generate report"}

        total = score_result["total_score"]
        severity = score_result["severity"]
        subscales = score_result["subscale_scores"]

        # ── Identify elevated subscales ───────────────────────────────────────
        elevated = []
        for name, sub in subscales.items():
            if sub["score"] > sub["normal_max"]:
                elevated.append(name)

        # ── Clinical recommendations ──────────────────────────────────────────
        recommendations = _get_recommendations(key, severity, elevated)

        # ── Next steps ────────────────────────────────────────────────────────
        next_steps = _get_next_steps(key, severity, score_result["crisis_flag"])

        return {
            "patient_name": patient_name or "Patient",
            "assessment_name": data["name"],
            "assessment_type": key,
            "condition": data["condition"],
            "scored_at": score_result.get("scored_at", datetime.utcnow().isoformat()),
            "total_score": total,
            "max_possible": data["max_score"],
            "score_percentage": score_result["score_percentage"],
            "severity": severity,
            "severity_color": score_result["severity_color"],
            "interpretation": score_result["interpretation"],
            "subscale_scores": subscales,
            "elevated_subscales": elevated,
            "crisis_flag": score_result["crisis_flag"],
            "crisis_details": score_result.get("crisis_details", []),
            "clinical_recommendations": recommendations,
            "next_steps": next_steps,
            "scoring_bands": [
                {"range": f"{low}–{high}", "label": label, "color": color}
                for low, high, label, _, color in data["scoring"]
            ],
            "disclaimer": (
                "This report is generated by an AI screening tool and does not constitute a clinical diagnosis. "
                "Please discuss these results with a qualified mental health professional."
            ),
        }

    def build_llm_context_block(self, assessment_result: Dict) -> str:
        """Build context block for LLM prompt injection post-assessment."""
        key = assessment_result.get("assessment_type", "")
        ctx = ASSESSMENT_CLINICAL_CONTEXT.get(key, {})
        severity = assessment_result.get("severity", "unknown")
        score = assessment_result.get("total_score", 0)
        crisis = assessment_result.get("crisis_flag", False)

        block = f"""
## Assessment Completed: {assessment_result.get('assessment_name', key)}
- Score: {score}/{assessment_result.get('max_possible', '?')}
- Severity: {severity}
- Condition: {ctx.get('condition', 'general mental health')}
- Crisis Flag: {'YES - immediate action required' if crisis else 'No'}

**Interpretation**: {assessment_result.get('interpretation', '')}

**How to respond**:
"""
        if crisis:
            block += "PRIORITY: Crisis indicators present. Address safety immediately before discussing score.\n"
        elif severity.lower() in ["severe", "moderately severe", "very severe"]:
            block += f"Score indicates {severity} symptoms. Validate difficulty. Express genuine concern. Discuss professional referral.\n"
        elif severity.lower() in ["moderate", "mild"]:
            block += f"Score indicates {severity} symptoms. Validate experience. Introduce coping strategies. Discuss treatment options.\n"
        else:
            block += "Minimal/low symptoms. Validate self-awareness. Discuss preventative strategies and wellbeing maintenance.\n"

        return block


# ─── Helper functions ──────────────────────────────────────────────────────────

def _get_recommendations(assessment_type: str, severity: str, elevated_subscales: List[str]) -> List[str]:
    sev_lower = severity.lower()
    recs = []

    base_recs = {
        "PHQ-9": {
            "none-minimal": ["Continue current healthy habits", "Maintain regular sleep schedule and physical activity"],
            "mild": ["Consider self-help resources for low mood", "Increase physical activity and social connection", "Monitor symptoms over next 4 weeks"],
            "moderate": ["Cognitive Behavioral Therapy (CBT) is recommended", "Discuss antidepressant options with a psychiatrist", "Schedule follow-up within 2 weeks"],
            "moderately severe": ["Immediate referral to mental health professional", "Consider combination of therapy and medication", "Weekly monitoring of symptoms"],
            "severe": ["Urgent psychiatric evaluation required", "Consider hospitalization if safety is a concern", "Crisis support resources should be provided"],
        },
        "GAD-7": {
            "minimal": ["No clinical intervention needed", "Continue current stress management practices"],
            "mild": ["Practice mindfulness and relaxation techniques", "Consider CBT workbooks for anxiety", "Monitor symptoms"],
            "moderate": ["CBT for anxiety is recommended", "Consider medication evaluation", "Stress management program"],
            "severe": ["Urgent psychiatric evaluation", "Combination therapy and medication recommended", "Regular clinical monitoring"],
        },
        "PCL-5": {
            "minimal": ["No PTSD-specific intervention needed"],
            "moderate": ["Trauma-focused therapy (EMDR or CPT) evaluation recommended", "Avoid trauma triggers where possible"],
            "moderately severe": ["Immediate referral to trauma-specialized therapist", "EMDR or Prolonged Exposure therapy", "Safety planning"],
            "severe": ["Urgent clinical evaluation", "Inpatient trauma program may be needed", "Safety planning and crisis support"],
        },
        "ISI": {
            "no insomnia": ["Maintain good sleep hygiene"],
            "subthreshold insomnia": ["Sleep hygiene education", "Reduce caffeine and screen time before bed", "Regular sleep schedule"],
            "moderate insomnia": ["CBT for Insomnia (CBT-I) is first-line treatment", "Avoid sleep medications long-term", "Sleep diary recommended"],
            "severe insomnia": ["Immediate CBT-I program", "Medical evaluation to rule out underlying conditions", "Short-term medication may be considered"],
        },
        "OCI-R": {
            "below cutoff": ["No OCD-specific intervention needed"],
            "mild-moderate ocd": ["ERP (Exposure and Response Prevention) therapy recommended", "OCD psychoeducation"],
            "moderate-severe ocd": ["Specialized ERP therapist referral", "Consider SSRI medication evaluation"],
            "severe ocd": ["Urgent specialist OCD program", "Combined ERP and pharmacotherapy"],
        },
        "SPIN": {
            "minimal": ["No intervention needed"],
            "mild": ["Self-help CBT resources for social anxiety", "Gradual social exposure practice"],
            "moderate": ["CBT with social anxiety focus", "Consider group therapy"],
            "severe": ["Specialized social anxiety treatment program", "Medication evaluation (SSRIs)", "CBT with exposure therapy"],
            "very severe": ["Urgent specialized treatment", "Combined CBT and medication", "Regular clinical monitoring"],
        },
        "PSS": {
            "low stress": ["Continue current stress management practices"],
            "moderate stress": ["Mindfulness-based stress reduction (MBSR)", "Work-life balance review", "Physical exercise program"],
            "high stress": ["Immediate stress management support", "Consider temporary reduction of stressors", "Therapy focused on coping skills"],
        },
        "WHO-5": {
            "likely depression": ["PHQ-9 depression screening is strongly recommended", "Clinical evaluation for depression needed"],
            "poor wellbeing": ["Mental health support recommended", "Review lifestyle factors: sleep, exercise, social connection"],
            "moderate wellbeing": ["Targeted wellbeing interventions", "Positive psychology approaches"],
            "good wellbeing": ["Maintain current positive practices", "Consider periodic wellbeing check-ins"],
        },
    }

    assessment_recs = base_recs.get(assessment_type, {})
    for band, rec_list in assessment_recs.items():
        if band in sev_lower:
            recs.extend(rec_list)
            break

    if not recs:
        recs = [f"Discuss {severity} {assessment_type} results with your clinician"]

    # Add subscale-specific recommendations
    if elevated_subscales:
        recs.append(f"Elevated domains requiring attention: {', '.join(elevated_subscales)}")

    return recs


def _get_next_steps(assessment_type: str, severity: str, crisis_flag: bool) -> List[str]:
    steps = []

    if crisis_flag:
        steps = [
            "URGENT: Crisis indicators detected — contact a mental health professional immediately",
            "If in immediate danger, call emergency services (112) or a crisis helpline",
            "Do not leave the person alone if crisis risk is high",
        ]
        return steps

    sev_lower = severity.lower()
    if any(s in sev_lower for s in ["severe", "very severe", "likely depression"]):
        steps = [
            "Book an urgent appointment with a mental health professional",
            "Share this report with your therapist or doctor",
            "Identify one trusted person to check in with daily",
        ]
    elif any(s in sev_lower for s in ["moderate", "moderately severe", "moderate-severe", "moderate insomnia"]):
        steps = [
            "Schedule an appointment with a mental health professional within 1-2 weeks",
            "Begin a self-monitoring symptom diary",
            "Explore evidence-based self-help resources",
        ]
    elif any(s in sev_lower for s in ["mild", "subthreshold", "mild-moderate", "poor wellbeing"]):
        steps = [
            "Consider speaking with a counselor",
            "Explore self-help resources and apps",
            "Reassess in 4 weeks with this same scale",
        ]
    else:
        steps = [
            "Continue current healthy practices",
            "Re-assess in 3 months or if symptoms change",
        ]

    return steps
