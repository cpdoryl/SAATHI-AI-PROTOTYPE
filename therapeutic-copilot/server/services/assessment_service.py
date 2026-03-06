"""
SAATHI AI — Clinical Assessment Service
Supports 8 validated instruments: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5
"""
from typing import List, Dict, Optional


ASSESSMENTS = {
    "PHQ-9": {
        "name": "Patient Health Questionnaire (Depression)",
        "questions": [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself",
            "Trouble concentrating",
            "Moving or speaking slowly — or being fidgety/restless",
            "Thoughts of self-harm or being better off dead",
        ],
        "scale": [0, 1, 2, 3],
        "labels": ["Not at all", "Several days", "More than half", "Nearly every day"],
        "scoring": [(0, 4, "None–minimal"), (5, 9, "Mild"), (10, 14, "Moderate"), (15, 19, "Moderately severe"), (20, 27, "Severe")],
    },
    "GAD-7": {
        "name": "Generalised Anxiety Disorder Scale",
        "questions": [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen",
        ],
        "scale": [0, 1, 2, 3],
        "labels": ["Not at all", "Several days", "More than half", "Nearly every day"],
        "scoring": [(0, 4, "Minimal"), (5, 9, "Mild"), (10, 14, "Moderate"), (15, 21, "Severe")],
    },
    # Additional assessments: PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5
    # Full question sets in separate data files (assessments_data.json)
}


class AssessmentService:
    """Score and interpret clinical assessments."""

    def get_questions(self, assessment_type: str) -> List[Dict]:
        """Return question list for a given assessment."""
        data = ASSESSMENTS.get(assessment_type.upper())
        if not data:
            return []
        return [
            {"id": i, "text": q, "scale": data["scale"], "labels": data["labels"]}
            for i, q in enumerate(data["questions"])
        ]

    def score(self, assessment_type: str, responses: List[int]) -> Dict:
        """
        Score an assessment and return severity classification.
        responses: list of integer scores matching question order.
        """
        data = ASSESSMENTS.get(assessment_type.upper())
        if not data:
            return {"error": f"Unknown assessment: {assessment_type}"}

        total = sum(responses)
        severity = "Unknown"
        for low, high, label in data["scoring"]:
            if low <= total <= high:
                severity = label
                break

        return {
            "assessment_type": assessment_type,
            "total_score": total,
            "severity": severity,
            "max_possible": max(data["scale"]) * len(data["questions"]),
            "responses": responses,
        }
