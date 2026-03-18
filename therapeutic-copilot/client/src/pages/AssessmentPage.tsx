/**
 * SAATHI AI — Psychological Assessment Page
 * Supports: PHQ-9, GAD-7, PCL-5, ISI, OCI-R, SPIN, PSS, WHO-5
 *
 * Views:
 *   1. Dashboard  — cards for all 8 assessments
 *   2. Assessment — question-by-question form
 *   3. Results    — score, severity, subscale radar + bar charts
 *   4. Report     — printable clinical summary
 */

import React, { useState, useCallback } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AssessmentMeta {
  id: string;
  name: string;
  short_name: string;
  condition: string;
  description: string;
  question_count: number;
  max_score: number;
}

interface Question {
  id: number;
  text: string;
  scale: number[];
  labels: string[];
  is_crisis_question: boolean;
  is_reversed: boolean;
}

interface SubScale {
  score: number;
  max: number;
  percentage: number;
  normal_min: number;
  normal_max: number;
}

interface ScoreResult {
  assessment_type: string;
  assessment_name: string;
  condition: string;
  total_score: number;
  max_possible: number;
  score_percentage: number;
  severity: string;
  severity_color: string;
  interpretation: string;
  subscale_scores: Record<string, SubScale>;
  crisis_flag: boolean;
  crisis_details: Array<{ question: number; text: string; response: number; label: string }>;
  responses: number[];
  scored_at: string;
}

interface Report {
  patient_name: string;
  assessment_name: string;
  assessment_type: string;
  condition: string;
  scored_at: string;
  total_score: number;
  max_possible: number;
  score_percentage: number;
  severity: string;
  severity_color: string;
  interpretation: string;
  subscale_scores: Record<string, SubScale>;
  elevated_subscales: string[];
  crisis_flag: boolean;
  clinical_recommendations: string[];
  next_steps: string[];
  scoring_bands: Array<{ range: string; label: string; color: string }>;
  disclaimer: string;
}

type View = 'dashboard' | 'taking' | 'results' | 'report';

// ─── Assessment metadata (static, matches backend) ────────────────────────────

const ASSESSMENT_META: AssessmentMeta[] = [
  {
    id: 'PHQ-9', name: 'Patient Health Questionnaire-9', short_name: 'PHQ-9',
    condition: 'Depression', description: 'Screens for depressive symptoms over the past 2 weeks.',
    question_count: 9, max_score: 27,
  },
  {
    id: 'GAD-7', name: 'Generalized Anxiety Disorder-7', short_name: 'GAD-7',
    condition: 'Anxiety', description: 'Screens for generalized anxiety disorder over the past 2 weeks.',
    question_count: 7, max_score: 21,
  },
  {
    id: 'PCL-5', name: 'PTSD Checklist for DSM-5', short_name: 'PCL-5',
    condition: 'PTSD', description: 'Screens for post-traumatic stress symptoms over the past month.',
    question_count: 20, max_score: 80,
  },
  {
    id: 'ISI', name: 'Insomnia Severity Index', short_name: 'ISI',
    condition: 'Insomnia', description: 'Assesses the severity and impact of insomnia.',
    question_count: 7, max_score: 28,
  },
  {
    id: 'OCI-R', name: 'Obsessive Compulsive Inventory—Revised', short_name: 'OCI-R',
    condition: 'OCD', description: 'Measures obsessive-compulsive symptoms across 6 domains.',
    question_count: 18, max_score: 72,
  },
  {
    id: 'SPIN', name: 'Social Phobia Inventory', short_name: 'SPIN',
    condition: 'Social Anxiety', description: 'Screens for social anxiety across fear, avoidance, and physiological domains.',
    question_count: 17, max_score: 68,
  },
  {
    id: 'PSS', name: 'Perceived Stress Scale', short_name: 'PSS-10',
    condition: 'Stress', description: 'Measures the degree to which life situations are perceived as stressful.',
    question_count: 10, max_score: 40,
  },
  {
    id: 'WHO-5', name: 'WHO Well-Being Index', short_name: 'WHO-5',
    condition: 'Wellbeing', description: 'Measures current mental wellbeing across 5 dimensions.',
    question_count: 5, max_score: 100,
  },
];

// ─── Condition icons (emoji fallback — no icon lib needed) ───────────────────

const CONDITION_ICON: Record<string, string> = {
  Depression: '🧠', Anxiety: '🌀', PTSD: '💥', Insomnia: '🌙',
  OCD: '🔄', 'Social Anxiety': '👥', Stress: '⚡', Wellbeing: '🌱',
};

const CONDITION_COLOR: Record<string, string> = {
  Depression: 'from-indigo-500 to-purple-600',
  Anxiety: 'from-orange-400 to-amber-500',
  PTSD: 'from-red-500 to-rose-600',
  Insomnia: 'from-blue-400 to-cyan-500',
  OCD: 'from-teal-400 to-emerald-500',
  'Social Anxiety': 'from-pink-400 to-fuchsia-500',
  Stress: 'from-yellow-400 to-orange-500',
  Wellbeing: 'from-green-400 to-teal-500',
};

// ─── Inline question data (fallback — backend can override) ──────────────────

const QUESTIONS: Record<string, Question[]> = {
  'PHQ-9': [
    { id: 0, text: 'Little interest or pleasure in doing things', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 1, text: 'Feeling down, depressed, or hopeless', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 2, text: 'Trouble falling or staying asleep, or sleeping too much', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 3, text: 'Feeling tired or having little energy', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 4, text: 'Poor appetite or overeating', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 5, text: 'Feeling bad about yourself — or that you are a failure', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 6, text: 'Trouble concentrating on things', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 7, text: 'Moving or speaking slowly / being fidgety or restless', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 8, text: 'Thoughts that you would be better off dead, or of hurting yourself', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: true, is_reversed: false },
  ],
  'GAD-7': [
    { id: 0, text: 'Feeling nervous, anxious, or on edge', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 1, text: 'Not being able to stop or control worrying', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 2, text: 'Worrying too much about different things', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 3, text: 'Trouble relaxing', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 4, text: 'Being so restless that it is hard to sit still', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 5, text: 'Becoming easily annoyed or irritable', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
    { id: 6, text: 'Feeling afraid as if something awful might happen', scale: [0,1,2,3], labels: ['Not at all','Several days','More than half the days','Nearly every day'], is_crisis_question: false, is_reversed: false },
  ],
  'ISI': [
    { id: 0, text: 'Difficulty falling asleep', scale: [0,1,2,3,4], labels: ['None','Mild','Moderate','Severe','Very Severe'], is_crisis_question: false, is_reversed: false },
    { id: 1, text: 'Difficulty staying asleep (waking up at night)', scale: [0,1,2,3,4], labels: ['None','Mild','Moderate','Severe','Very Severe'], is_crisis_question: false, is_reversed: false },
    { id: 2, text: 'Problems waking up too early in the morning', scale: [0,1,2,3,4], labels: ['None','Mild','Moderate','Severe','Very Severe'], is_crisis_question: false, is_reversed: false },
    { id: 3, text: 'How satisfied/dissatisfied are you with your current sleep pattern?', scale: [0,1,2,3,4], labels: ['Very satisfied','Satisfied','Neutral','Dissatisfied','Very dissatisfied'], is_crisis_question: false, is_reversed: false },
    { id: 4, text: 'How noticeable to others is your sleep problem?', scale: [0,1,2,3,4], labels: ['Not noticeable','Barely','Somewhat','Much','Very much'], is_crisis_question: false, is_reversed: false },
    { id: 5, text: 'How worried/distressed are you about your sleep problem?', scale: [0,1,2,3,4], labels: ['Not worried','A little','Somewhat','Much','Very much worried'], is_crisis_question: false, is_reversed: false },
    { id: 6, text: 'To what extent does sleep interfere with your daily functioning?', scale: [0,1,2,3,4], labels: ['Not at all','A little','Somewhat','Much','Very much'], is_crisis_question: false, is_reversed: false },
  ],
  'PSS': [
    { id: 0, text: 'How often have you been upset because of something that happened unexpectedly?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
    { id: 1, text: 'How often have you felt that you were unable to control important things in your life?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
    { id: 2, text: 'How often have you felt nervous and stressed?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
    { id: 3, text: 'How often have you felt confident about your ability to handle personal problems?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: true },
    { id: 4, text: 'How often have you felt that things were going your way?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: true },
    { id: 5, text: 'How often have you found that you could not cope with all the things you had to do?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
    { id: 6, text: 'How often have you been able to control irritations in your life?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: true },
    { id: 7, text: 'How often have you felt that you were on top of things?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: true },
    { id: 8, text: 'How often have you been angered because of things outside of your control?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
    { id: 9, text: 'How often have you felt difficulties were piling up so high you could not overcome them?', scale: [0,1,2,3,4], labels: ['Never','Almost never','Sometimes','Fairly often','Very often'], is_crisis_question: false, is_reversed: false },
  ],
  'WHO-5': [
    { id: 0, text: 'I have felt cheerful and in good spirits', scale: [0,1,2,3,4,5], labels: ['At no time','Some of the time','Less than half the time','More than half the time','Most of the time','All of the time'], is_crisis_question: false, is_reversed: false },
    { id: 1, text: 'I have felt calm and relaxed', scale: [0,1,2,3,4,5], labels: ['At no time','Some of the time','Less than half the time','More than half the time','Most of the time','All of the time'], is_crisis_question: false, is_reversed: false },
    { id: 2, text: 'I have felt active and vigorous', scale: [0,1,2,3,4,5], labels: ['At no time','Some of the time','Less than half the time','More than half the time','Most of the time','All of the time'], is_crisis_question: false, is_reversed: false },
    { id: 3, text: 'I woke up feeling fresh and rested', scale: [0,1,2,3,4,5], labels: ['At no time','Some of the time','Less than half the time','More than half the time','Most of the time','All of the time'], is_crisis_question: false, is_reversed: false },
    { id: 4, text: 'My daily life has been filled with things that interest me', scale: [0,1,2,3,4,5], labels: ['At no time','Some of the time','Less than half the time','More than half the time','Most of the time','All of the time'], is_crisis_question: false, is_reversed: false },
  ],
};

// For brevity, generate placeholder questions for PCL-5, OCI-R, SPIN
// The full questions are served from the backend API
const PCL5_TEXTS = [
  'Repeated, disturbing memories of the stressful experience',
  'Repeated, disturbing dreams of the stressful experience',
  'Suddenly feeling as if the stressful experience were actually happening again',
  'Feeling very upset when something reminded you of the stressful experience',
  'Strong physical reactions when something reminded you of the experience',
  'Avoiding memories, thoughts, or feelings related to the experience',
  'Avoiding external reminders of the stressful experience',
  'Trouble remembering important parts of the stressful experience',
  'Strong negative beliefs about yourself, other people, or the world',
  'Blaming yourself or someone else for the stressful experience',
  'Strong negative feelings such as fear, horror, anger, guilt, or shame',
  'Loss of interest in activities that you used to enjoy',
  'Feeling distant or cut off from other people',
  'Trouble experiencing positive feelings',
  'Irritable behavior or angry outbursts',
  'Taking too many risks or doing things that could cause harm',
  'Being superalert, watchful, or on guard',
  'Feeling jumpy or easily startled',
  'Having difficulty concentrating',
  'Trouble falling or staying asleep',
];

QUESTIONS['PCL-5'] = PCL5_TEXTS.map((text, id) => ({
  id, text, scale: [0,1,2,3,4],
  labels: ['Not at all','A little bit','Moderately','Quite a bit','Extremely'],
  is_crisis_question: false, is_reversed: false,
}));

const OCIR_TEXTS = [
  'I have saved up so many things that they get in the way',
  'I check things more often than necessary',
  'I get upset if objects are not arranged properly',
  'I feel compelled to count while I am doing things',
  'I find it difficult to touch objects touched by strangers',
  'I find it difficult to control my own thoughts',
  'I collect things I don\'t need',
  'I repeatedly check doors, windows, drawers, etc.',
  'I get upset if others change the way I have arranged things',
  'I feel I have to repeat certain numbers',
  'I sometimes have to wash or clean myself simply because I feel contaminated',
  'I am upset by unpleasant thoughts that come into my mind against my will',
  'I avoid throwing things away because I am afraid I might need them later',
  'I repeatedly check gas and water taps and light switches after turning them off',
  'I need things to be arranged in a particular order',
  'I feel that there are good and bad numbers',
  'I wash my hands more often and longer than necessary',
  'I frequently get nasty thoughts and have difficulty in getting rid of them',
];

QUESTIONS['OCI-R'] = OCIR_TEXTS.map((text, id) => ({
  id, text, scale: [0,1,2,3,4],
  labels: ['Not at all','A little','Moderately','A lot','Extremely'],
  is_crisis_question: false, is_reversed: false,
}));

const SPIN_TEXTS = [
  'I am afraid of people in authority',
  'I am bothered by blushing in front of people',
  'Parties and social events scare me',
  'I avoid talking to people I don\'t know',
  'Being criticized scares me a lot',
  'Fear of embarrassment causes me to avoid things',
  'Sweating in front of people causes me distress',
  'I avoid going to parties',
  'I avoid activities where I am the center of attention',
  'Talking to strangers scares me',
  'I avoid having to give speeches',
  'I would do anything to avoid being criticized',
  'Heart palpitations bother me when I am around people',
  'I am afraid of doing things when people might be watching',
  'Being embarrassed or looking stupid are among my worst fears',
  'I avoid speaking to anyone in authority',
  'Trembling or shaking in front of others is distressing to me',
];

QUESTIONS['SPIN'] = SPIN_TEXTS.map((text, id) => ({
  id, text, scale: [0,1,2,3,4],
  labels: ['Not at all','A little bit','Somewhat','Very much','Extremely'],
  is_crisis_question: false, is_reversed: false,
}));

// ─── Local scoring logic (no network required for demo) ──────────────────────

function scoreLocally(type: string, responses: number[]): ScoreResult {
  const meta = ASSESSMENT_META.find(a => a.id === type)!;

  const reversedItems: Record<string, number[]> = { PSS: [3, 4, 6, 7] };
  const reversed = reversedItems[type] || [];
  const maxVal = Math.max(...(QUESTIONS[type]?.[0]?.scale || [3]));

  const scored = responses.map((r, i) =>
    reversed.includes(i) ? maxVal - r : r
  );

  let total = scored.reduce((a, b) => a + b, 0);
  if (type === 'WHO-5') total = total * 4;

  // Severity bands
  const bands: Record<string, Array<[number, number, string, string, string]>> = {
    'PHQ-9': [[0,4,'None-Minimal','No significant depressive symptoms.','#22c55e'],[5,9,'Mild','Mild depressive symptoms.','#86efac'],[10,14,'Moderate','Moderate depression. Treatment recommended.','#facc15'],[15,19,'Moderately Severe','Active treatment strongly recommended.','#f97316'],[20,27,'Severe','Severe depression. Immediate intervention required.','#ef4444']],
    'GAD-7': [[0,4,'Minimal','Minimal anxiety.','#22c55e'],[5,9,'Mild','Mild anxiety.','#86efac'],[10,14,'Moderate','Moderate anxiety. Therapy recommended.','#facc15'],[15,21,'Severe','Severe anxiety. Urgent evaluation needed.','#ef4444']],
    'PCL-5': [[0,31,'Minimal','Minimal PTSD symptoms.','#22c55e'],[32,44,'Moderate','Moderate PTSD. Clinical evaluation recommended.','#facc15'],[45,59,'Moderately Severe','Trauma-focused therapy strongly recommended.','#f97316'],[60,80,'Severe','Severe PTSD. Immediate intervention required.','#ef4444']],
    'ISI': [[0,7,'No Insomnia','No clinically significant insomnia.','#22c55e'],[8,14,'Subthreshold Insomnia','Sleep hygiene education recommended.','#86efac'],[15,21,'Moderate Insomnia','CBT-I recommended.','#facc15'],[22,28,'Severe Insomnia','Medical evaluation and CBT-I urgently needed.','#ef4444']],
    'OCI-R': [[0,20,'Below Cutoff','OCD symptoms below clinical threshold.','#22c55e'],[21,40,'Mild-Moderate OCD','Symptoms above OCD cutoff. Assessment recommended.','#facc15'],[41,60,'Moderate-Severe OCD','Significant OCD symptoms. ERP therapy needed.','#f97316'],[61,72,'Severe OCD','Severe OCD. Urgent specialist evaluation required.','#ef4444']],
    'SPIN': [[0,20,'Minimal','Minimal social anxiety.','#22c55e'],[21,30,'Mild','Mild social anxiety.','#86efac'],[31,40,'Moderate','Moderate social anxiety. CBT recommended.','#facc15'],[41,50,'Severe','Severe social anxiety. Clinical treatment required.','#f97316'],[51,68,'Very Severe','Very severe. Urgent clinical intervention.','#ef4444']],
    'PSS': [[0,13,'Low Stress','Low perceived stress.','#22c55e'],[14,26,'Moderate Stress','Moderate stress.','#facc15'],[27,40,'High Stress','High perceived stress. Clinical support recommended.','#ef4444']],
    'WHO-5': [[0,28,'Likely Depression','Score suggests possible depression. PHQ-9 recommended.','#ef4444'],[29,50,'Poor Wellbeing','Low wellbeing.','#f97316'],[51,72,'Moderate Wellbeing','Moderate wellbeing.','#facc15'],[73,100,'Good Wellbeing','Good mental wellbeing.','#22c55e']],
  };

  const band = (bands[type] || []).find(([lo, hi]) => total >= lo && total <= hi);
  const [,, severity, interpretation, severity_color] = band || [0, 0, 'Unknown', '', '#94a3b8'];

  // Subscales
  const subscaleDefs: Record<string, Record<string, { indices: number[]; max: number; normalMin: number; normalMax: number }>> = {
    'PHQ-9': { Mood: { indices:[0,1], max:6, normalMin:0, normalMax:1 }, 'Sleep & Energy': { indices:[2,3], max:6, normalMin:0, normalMax:1 }, Appetite: { indices:[4], max:3, normalMin:0, normalMax:0 }, 'Self-Worth': { indices:[5], max:3, normalMin:0, normalMax:0 }, Concentration: { indices:[6], max:3, normalMin:0, normalMax:0 }, Psychomotor: { indices:[7], max:3, normalMin:0, normalMax:0 }, 'Suicidal Ideation': { indices:[8], max:3, normalMin:0, normalMax:0 } },
    'GAD-7': { Worry: { indices:[0,1,2], max:9, normalMin:0, normalMax:2 }, Restlessness: { indices:[3,4], max:6, normalMin:0, normalMax:1 }, Irritability: { indices:[5], max:3, normalMin:0, normalMax:0 }, Fear: { indices:[6], max:3, normalMin:0, normalMax:0 } },
    'PCL-5': { Intrusion: { indices:[0,1,2,3,4], max:20, normalMin:0, normalMax:4 }, Avoidance: { indices:[5,6], max:8, normalMin:0, normalMax:2 }, 'Negative Cognitions': { indices:[7,8,9,10,11,12,13], max:28, normalMin:0, normalMax:5 }, Hyperarousal: { indices:[14,15,16,17,18,19], max:24, normalMin:0, normalMax:5 } },
    'ISI': { 'Sleep Onset': { indices:[0], max:4, normalMin:0, normalMax:1 }, 'Sleep Maintenance': { indices:[1,2], max:8, normalMin:0, normalMax:2 }, 'Sleep Satisfaction': { indices:[3], max:4, normalMin:0, normalMax:1 }, 'Daytime Impact': { indices:[4,5,6], max:12, normalMin:0, normalMax:2 } },
    'OCI-R': { Hoarding: { indices:[0,6,12], max:12, normalMin:0, normalMax:2 }, Checking: { indices:[1,7,13], max:12, normalMin:0, normalMax:2 }, Ordering: { indices:[2,8,14], max:12, normalMin:0, normalMax:2 }, Counting: { indices:[3,9,15], max:12, normalMin:0, normalMax:2 }, Contamination: { indices:[4,10,16], max:12, normalMin:0, normalMax:2 }, Obsessing: { indices:[5,11,17], max:12, normalMin:0, normalMax:2 } },
    'SPIN': { Fear: { indices:[0,4,5,7,10,14], max:24, normalMin:0, normalMax:5 }, Avoidance: { indices:[2,3,8,9,13,15], max:24, normalMin:0, normalMax:5 }, Physiological: { indices:[1,6,12,16,11], max:20, normalMin:0, normalMax:4 } },
    'PSS': { 'Perceived Stress': { indices:[0,1,2,5,8,9], max:24, normalMin:0, normalMax:8 }, 'Perceived Coping': { indices:[3,4,6,7], max:16, normalMin:8, normalMax:16 } },
    'WHO-5': { 'Positive Mood': { indices:[0,1], max:40, normalMin:24, normalMax:40 }, Vitality: { indices:[2,3], max:40, normalMin:24, normalMax:40 }, 'General Interest': { indices:[4], max:20, normalMin:12, normalMax:20 } },
  };

  const subs = subscaleDefs[type] || {};
  const subscale_scores: Record<string, SubScale> = {};
  for (const [name, { indices, max, normalMin, normalMax }] of Object.entries(subs)) {
    let subScore = indices.reduce((acc, i) => acc + (scored[i] ?? 0), 0);
    if (type === 'WHO-5') subScore = subScore * 4;
    subscale_scores[name] = {
      score: subScore,
      max,
      percentage: max > 0 ? Math.round(subScore / max * 100) : 0,
      normal_min: normalMin,
      normal_max: normalMax,
    };
  }

  const crisis_flag = type === 'PHQ-9' && responses[8] >= 1;
  const crisis_details = crisis_flag ? [{
    question: 8,
    text: 'Thoughts that you would be better off dead, or of hurting yourself',
    response: responses[8],
    label: ['Not at all','Several days','More than half the days','Nearly every day'][responses[8]],
  }] : [];

  return {
    assessment_type: type,
    assessment_name: meta.name,
    condition: meta.condition,
    total_score: total,
    max_possible: meta.max_score,
    score_percentage: Math.round(total / meta.max_score * 100),
    severity,
    severity_color,
    interpretation,
    subscale_scores,
    crisis_flag,
    crisis_details,
    responses,
    scored_at: new Date().toISOString(),
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

// Score gauge / progress ring
function ScoreGauge({ score, max, color }: { score: number; max: number; color: string }) {
  const pct = Math.min(100, Math.round(score / max * 100));
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="relative inline-flex items-center justify-center w-36 h-36">
      <svg className="w-36 h-36 -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none"
          stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
      </svg>
      <div className="absolute text-center">
        <span className="text-2xl font-bold text-slate-800">{score}</span>
        <span className="block text-xs text-slate-500">/ {max}</span>
      </div>
    </div>
  );
}

// Subscale bar chart with normal range reference lines
function SubscaleBarChart({ subscales }: { subscales: Record<string, SubScale> }) {
  const data = Object.entries(subscales).map(([name, sub]) => ({
    name,
    Score: sub.score,
    Max: sub.max,
    'Normal Max': sub.normal_max,
    normalMax: sub.normal_max,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: '#64748b' }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
        <Tooltip
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            const sub = subscales[label as string];
            return (
              <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-sm">
                <p className="font-semibold text-slate-800 mb-1">{label}</p>
                <p className="text-slate-700">Score: <strong>{sub.score}</strong> / {sub.max}</p>
                <p className="text-green-600">Normal range: 0 – {sub.normal_max}</p>
                {sub.score > sub.normal_max && (
                  <p className="text-orange-600 font-medium mt-1">Above normal range</p>
                )}
              </div>
            );
          }}
        />
        <Legend wrapperStyle={{ paddingTop: 16 }} />
        <Bar dataKey="Score" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={entry.Score > entry.normalMax ? '#f97316' : '#6366f1'}
            />
          ))}
        </Bar>
        <Bar dataKey="Normal Max" fill="#86efac" opacity={0.5} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Radar chart for subscale profile
function SubscaleRadar({ subscales }: { subscales: Record<string, SubScale> }) {
  const data = Object.entries(subscales).map(([name, sub]) => ({
    subject: name,
    Score: sub.max > 0 ? Math.round(sub.score / sub.max * 100) : 0,
    'Normal Max': sub.max > 0 ? Math.round(sub.normal_max / sub.max * 100) : 0,
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data}>
        <PolarGrid stroke="#e2e8f0" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#475569' }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
        <Radar name="Your Score" dataKey="Score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
        <Radar name="Normal Range" dataKey="Normal Max" stroke="#22c55e" fill="#22c55e" fillOpacity={0.15} strokeDasharray="5 5" />
        <Legend />
        <Tooltip formatter={(val) => `${val}%`} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// Severity band legend
function SeverityScale({ type }: { type: string }) {
  const bands: Record<string, Array<{ label: string; color: string; range?: string }>> = {
    'PHQ-9': [{ label:'None-Minimal', color:'#22c55e', range:'0–4' },{ label:'Mild', color:'#86efac', range:'5–9' },{ label:'Moderate', color:'#facc15', range:'10–14' },{ label:'Mod. Severe', color:'#f97316', range:'15–19' },{ label:'Severe', color:'#ef4444', range:'20–27' }],
    'GAD-7': [{ label:'Minimal', color:'#22c55e', range:'0–4' },{ label:'Mild', color:'#86efac', range:'5–9' },{ label:'Moderate', color:'#facc15', range:'10–14' },{ label:'Severe', color:'#ef4444', range:'15–21' }],
    'PCL-5': [{ label:'Minimal', color:'#22c55e', range:'0–31' },{ label:'Moderate', color:'#facc15', range:'32–44' },{ label:'Mod. Severe', color:'#f97316', range:'45–59' },{ label:'Severe', color:'#ef4444', range:'60–80' }],
    'ISI': [{ label:'None', color:'#22c55e', range:'0–7' },{ label:'Subthreshold', color:'#86efac', range:'8–14' },{ label:'Moderate', color:'#facc15', range:'15–21' },{ label:'Severe', color:'#ef4444', range:'22–28' }],
    'OCI-R': [{ label:'Below Cutoff', color:'#22c55e', range:'0–20' },{ label:'Mild-Mod', color:'#facc15', range:'21–40' },{ label:'Mod-Severe', color:'#f97316', range:'41–60' },{ label:'Severe', color:'#ef4444', range:'61–72' }],
    'SPIN': [{ label:'Minimal', color:'#22c55e', range:'0–20' },{ label:'Mild', color:'#86efac', range:'21–30' },{ label:'Moderate', color:'#facc15', range:'31–40' },{ label:'Severe', color:'#f97316', range:'41–50' },{ label:'Very Severe', color:'#ef4444', range:'51–68' }],
    'PSS': [{ label:'Low', color:'#22c55e', range:'0–13' },{ label:'Moderate', color:'#facc15', range:'14–26' },{ label:'High', color:'#ef4444', range:'27–40' }],
    'WHO-5': [{ label:'Likely Dep.', color:'#ef4444', range:'0–28' },{ label:'Poor', color:'#f97316', range:'29–50' },{ label:'Moderate', color:'#facc15', range:'51–72' },{ label:'Good', color:'#22c55e', range:'73–100' }],
  };

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {(bands[type] || []).map(b => (
        <span key={b.label} className="flex items-center gap-1.5 text-xs bg-slate-50 rounded-full px-3 py-1 border border-slate-200">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: b.color }} />
          <span className="text-slate-600">{b.label}</span>
          {b.range && <span className="text-slate-400">({b.range})</span>}
        </span>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const AssessmentPage: React.FC = () => {
  const [view, setView] = useState<View>('dashboard');
  const [selectedAssessment, setSelectedAssessment] = useState<AssessmentMeta | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [responses, setResponses] = useState<(number | null)[]>([]);
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [patientName] = useState('Patient');

  const questions = selectedAssessment ? (QUESTIONS[selectedAssessment.id] || []) : [];

  const startAssessment = useCallback((meta: AssessmentMeta) => {
    setSelectedAssessment(meta);
    setCurrentQuestion(0);
    setResponses(new Array(meta.question_count).fill(null));
    setScoreResult(null);
    setReport(null);
    setView('taking');
  }, []);

  const handleAnswer = useCallback((questionIdx: number, value: number) => {
    setResponses(prev => {
      const next = [...prev];
      next[questionIdx] = value;
      return next;
    });
  }, []);

  const handleNext = useCallback(() => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(q => q + 1);
    }
  }, [currentQuestion, questions.length]);

  const handlePrev = useCallback(() => {
    if (currentQuestion > 0) setCurrentQuestion(q => q - 1);
  }, [currentQuestion]);

  const handleSubmit = useCallback(() => {
    if (!selectedAssessment) return;
    const filledResponses = responses.map(r => r ?? 0);
    const result = scoreLocally(selectedAssessment.id, filledResponses);
    setScoreResult(result);

    // Build basic report
    const elevated = Object.entries(result.subscale_scores)
      .filter(([, s]) => s.score > s.normal_max)
      .map(([name]) => name);

    setReport({
      patient_name: patientName,
      assessment_name: result.assessment_name,
      assessment_type: result.assessment_type,
      condition: result.condition,
      scored_at: result.scored_at,
      total_score: result.total_score,
      max_possible: result.max_possible,
      score_percentage: result.score_percentage,
      severity: result.severity,
      severity_color: result.severity_color,
      interpretation: result.interpretation,
      subscale_scores: result.subscale_scores,
      elevated_subscales: elevated,
      crisis_flag: result.crisis_flag,
      clinical_recommendations: [],
      next_steps: [],
      scoring_bands: [],
      disclaimer: 'This is a screening tool, not a clinical diagnosis. Please discuss results with a qualified mental health professional.',
    });

    setView('results');
  }, [selectedAssessment, responses, patientName]);

  const progress = questions.length > 0
    ? Math.round(responses.filter(r => r !== null).length / questions.length * 100)
    : 0;

  const canSubmit = responses.every(r => r !== null);

  // ── Dashboard ──────────────────────────────────────────────────────────────
  if (view === 'dashboard') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 p-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-800">Mental Health Assessments</h1>
            <p className="text-slate-500 mt-1">
              Validated clinical screening tools to understand your mental wellbeing.
              Each assessment takes 1–7 minutes.
            </p>
          </div>

          {/* Assessment Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {ASSESSMENT_META.map(meta => (
              <div
                key={meta.id}
                className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer"
                onClick={() => startAssessment(meta)}
              >
                {/* Gradient header */}
                <div className={`bg-gradient-to-r ${CONDITION_COLOR[meta.condition] || 'from-slate-400 to-slate-500'} p-4 text-white`}>
                  <div className="text-3xl mb-1">{CONDITION_ICON[meta.condition]}</div>
                  <div className="font-bold text-lg">{meta.short_name}</div>
                  <div className="text-white/80 text-xs">{meta.condition}</div>
                </div>

                {/* Body */}
                <div className="p-4">
                  <p className="text-slate-600 text-sm leading-relaxed mb-3">{meta.description}</p>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>{meta.question_count} questions</span>
                    <span>Max score: {meta.max_score}</span>
                  </div>
                  <button
                    className="mt-3 w-full py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
                    onClick={e => { e.stopPropagation(); startAssessment(meta); }}
                  >
                    Start Assessment
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Info banner */}
          <div className="mt-8 bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-3">
            <span className="text-blue-400 text-xl">ℹ️</span>
            <p className="text-blue-700 text-sm">
              These are standardized screening tools used globally by clinicians. Results are for informational
              purposes only and should be discussed with a qualified mental health professional.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ── Taking Assessment ──────────────────────────────────────────────────────
  if (view === 'taking' && selectedAssessment) {
    const q = questions[currentQuestion];
    const currentAnswer = responses[currentQuestion];
    const isCrisis = q?.is_crisis_question;

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 flex items-start justify-center p-6">
        <div className="w-full max-w-2xl">
          {/* Top bar */}
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => setView('dashboard')}
              className="text-slate-500 hover:text-slate-700 flex items-center gap-1 text-sm"
            >
              ← Back
            </button>
            <span className={`px-3 py-1 rounded-full text-xs font-medium text-white bg-gradient-to-r ${CONDITION_COLOR[selectedAssessment.condition]}`}>
              {CONDITION_ICON[selectedAssessment.condition]} {selectedAssessment.condition}
            </span>
          </div>

          {/* Card */}
          <div className="bg-white rounded-2xl shadow-md border border-slate-100 p-8">
            {/* Assessment title + progress */}
            <div className="mb-6">
              <h2 className="text-xl font-bold text-slate-800">{selectedAssessment.short_name}</h2>
              <div className="flex items-center gap-3 mt-2">
                <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <span className="text-xs text-slate-500 whitespace-nowrap">
                  {currentQuestion + 1} / {questions.length}
                </span>
              </div>
            </div>

            {/* Crisis alert */}
            {isCrisis && (
              <div className="mb-4 bg-red-50 border border-red-200 rounded-xl p-3 flex gap-2">
                <span>⚠️</span>
                <p className="text-red-700 text-sm">
                  This question asks about difficult thoughts. If you are in crisis, please reach out to a
                  mental health helpline immediately.
                </p>
              </div>
            )}

            {/* Question */}
            <div className="mb-8">
              <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">Question {currentQuestion + 1}</p>
              <p className="text-slate-800 text-lg font-medium leading-relaxed">{q?.text}</p>
            </div>

            {/* Answer options */}
            <div className="space-y-3">
              {(q?.labels || []).map((label, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAnswer(currentQuestion, idx)}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl border text-left transition-all ${
                    currentAnswer === idx
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-800'
                      : 'border-slate-200 hover:border-indigo-300 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <span className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                    currentAnswer === idx ? 'border-indigo-500 bg-indigo-500' : 'border-slate-300'
                  }`}>
                    {currentAnswer === idx && <span className="w-2 h-2 rounded-full bg-white" />}
                  </span>
                  <span className="text-sm font-medium">{idx} — {label}</span>
                </button>
              ))}
            </div>

            {/* Navigation */}
            <div className="flex justify-between mt-8 gap-3">
              <button
                onClick={handlePrev}
                disabled={currentQuestion === 0}
                className="px-5 py-2.5 rounded-xl border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous
              </button>

              {currentQuestion < questions.length - 1 ? (
                <button
                  onClick={handleNext}
                  disabled={currentAnswer === null}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next →
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="px-6 py-2.5 rounded-xl bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  View Results ✓
                </button>
              )}
            </div>
          </div>

          {/* Question dots */}
          <div className="flex flex-wrap justify-center gap-1.5 mt-5">
            {questions.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentQuestion(i)}
                className={`w-5 h-5 rounded-full text-[10px] font-bold transition-all ${
                  i === currentQuestion
                    ? 'bg-indigo-600 text-white'
                    : responses[i] !== null
                    ? 'bg-indigo-200 text-indigo-700'
                    : 'bg-slate-200 text-slate-400'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Results ────────────────────────────────────────────────────────────────
  if (view === 'results' && scoreResult && selectedAssessment) {
    const subscaleEntries = Object.entries(scoreResult.subscale_scores);

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 p-6">
        <div className="max-w-4xl mx-auto">
          {/* Top nav */}
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => setView('dashboard')}
              className="text-slate-500 hover:text-slate-700 flex items-center gap-1 text-sm"
            >
              ← All Assessments
            </button>
            <div className="flex gap-2">
              <button
                onClick={() => setView('report')}
                className="px-4 py-2 rounded-lg border border-indigo-300 text-indigo-700 text-sm font-medium hover:bg-indigo-50"
              >
                📄 Full Report
              </button>
              <button
                onClick={() => startAssessment(selectedAssessment)}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
              >
                Retake
              </button>
            </div>
          </div>

          {/* Crisis alert */}
          {scoreResult.crisis_flag && (
            <div className="mb-5 bg-red-50 border-l-4 border-red-500 rounded-xl p-4 flex gap-3">
              <span className="text-red-500 text-xl">⚠️</span>
              <div>
                <p className="font-semibold text-red-800">Crisis Indicators Detected</p>
                <p className="text-red-700 text-sm mt-1">
                  Your response suggests you may be having difficult thoughts. Please reach out to a
                  mental health professional or crisis helpline immediately.
                </p>
                {scoreResult.crisis_details.map((d, i) => (
                  <p key={i} className="text-red-600 text-xs mt-1">
                    Q{d.question + 1}: "{d.text}" — Response: {d.label}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Score summary card */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-5">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <ScoreGauge
                score={scoreResult.total_score}
                max={scoreResult.max_possible}
                color={scoreResult.severity_color}
              />
              <div className="flex-1 text-center sm:text-left">
                <div className="flex items-center gap-2 justify-center sm:justify-start mb-1">
                  <span className="text-2xl">{CONDITION_ICON[selectedAssessment.condition]}</span>
                  <h2 className="text-2xl font-bold text-slate-800">{selectedAssessment.short_name}</h2>
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold text-white mb-3"
                  style={{ background: scoreResult.severity_color }}>
                  {scoreResult.severity}
                </div>
                <p className="text-slate-600 text-sm leading-relaxed">{scoreResult.interpretation}</p>
                <SeverityScale type={selectedAssessment.id} />
              </div>
            </div>
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
            {/* Radar */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <h3 className="font-semibold text-slate-800 mb-1">Symptom Profile</h3>
              <p className="text-xs text-slate-500 mb-3">
                Your score (%) per domain vs. normal range (green shading)
              </p>
              <SubscaleRadar subscales={scoreResult.subscale_scores} />
            </div>

            {/* Bar chart */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
              <h3 className="font-semibold text-slate-800 mb-1">Domain Scores</h3>
              <p className="text-xs text-slate-500 mb-3">
                Orange bars = above normal range. Green bars = normal range ceiling.
              </p>
              <SubscaleBarChart subscales={scoreResult.subscale_scores} />
            </div>
          </div>

          {/* Subscale table */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden mb-5">
            <div className="px-5 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-800">Dimension Breakdown</h3>
            </div>
            <div className="divide-y divide-slate-50">
              {subscaleEntries.map(([name, sub]) => {
                const isElevated = sub.score > sub.normal_max;
                const pct = sub.max > 0 ? Math.round(sub.score / sub.max * 100) : 0;
                return (
                  <div key={name} className="px-5 py-3.5 flex items-center gap-4">
                    <div className="w-36 text-sm font-medium text-slate-700 flex-shrink-0">{name}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              background: isElevated ? '#f97316' : '#6366f1',
                            }}
                          />
                        </div>
                        <span className="text-xs text-slate-500 w-16 text-right">
                          {sub.score} / {sub.max}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>Normal: 0–{sub.normal_max}</span>
                        {isElevated && (
                          <span className="text-orange-600 font-medium">▲ Elevated</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="text-xs text-slate-400 text-center leading-relaxed">
            This screening tool does not constitute a clinical diagnosis. Please discuss your results with a qualified mental health professional.
          </div>
        </div>
      </div>
    );
  }

  // ── Full Report ────────────────────────────────────────────────────────────
  if (view === 'report' && scoreResult && selectedAssessment && report) {
    const date = new Date(report.scored_at).toLocaleDateString('en-IN', {
      year: 'numeric', month: 'long', day: 'numeric',
    });

    return (
      <div className="min-h-screen bg-slate-100 p-6 print:p-0 print:bg-white">
        <div className="max-w-3xl mx-auto">
          {/* Actions */}
          <div className="flex gap-2 mb-5 print:hidden">
            <button onClick={() => setView('results')} className="text-slate-500 hover:text-slate-700 text-sm flex items-center gap-1">
              ← Results
            </button>
            <div className="flex-1" />
            <button
              onClick={() => window.print()}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              🖨️ Print / Save PDF
            </button>
          </div>

          {/* Report card */}
          <div className="bg-white rounded-2xl shadow-md border border-slate-100 overflow-hidden print:shadow-none print:rounded-none">
            {/* Header */}
            <div className={`bg-gradient-to-r ${CONDITION_COLOR[selectedAssessment.condition]} p-6 text-white`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-white/70 text-sm mb-1">SAATHI AI — Clinical Assessment Report</p>
                  <h1 className="text-2xl font-bold">{report.assessment_name}</h1>
                  <p className="text-white/80 text-sm mt-1">{report.condition} Screening</p>
                </div>
                <div className="text-right">
                  <p className="text-white/70 text-xs">Date</p>
                  <p className="font-semibold">{date}</p>
                </div>
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Patient + score summary */}
              <div className="flex flex-wrap gap-4 pb-6 border-b border-slate-100">
                <div className="flex-1 min-w-[180px]">
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Patient</p>
                  <p className="font-semibold text-slate-800">{report.patient_name}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Total Score</p>
                  <p className="font-bold text-2xl text-slate-800">
                    {report.total_score} <span className="text-sm font-normal text-slate-400">/ {report.max_possible}</span>
                  </p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Severity</p>
                  <span
                    className="inline-block px-3 py-1 rounded-full text-white text-sm font-semibold"
                    style={{ background: report.severity_color }}
                  >
                    {report.severity}
                  </span>
                </div>
              </div>

              {/* Clinical interpretation */}
              <div>
                <h3 className="font-semibold text-slate-800 mb-2">Clinical Interpretation</h3>
                <p className="text-slate-600 text-sm leading-relaxed bg-slate-50 rounded-xl p-4">
                  {report.interpretation}
                </p>
              </div>

              {/* Crisis alert in report */}
              {report.crisis_flag && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <h3 className="font-semibold text-red-800 flex items-center gap-2">
                    ⚠️ Crisis Indicators Present
                  </h3>
                  <p className="text-red-700 text-sm mt-1">
                    Responses indicate possible risk. Immediate clinical follow-up is required.
                  </p>
                </div>
              )}

              {/* Subscale scores table */}
              <div>
                <h3 className="font-semibold text-slate-800 mb-3">Domain Scores</h3>
                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50">
                      <tr>
                        <th className="text-left px-4 py-2.5 text-slate-600 font-medium">Domain</th>
                        <th className="text-center px-4 py-2.5 text-slate-600 font-medium">Score</th>
                        <th className="text-center px-4 py-2.5 text-slate-600 font-medium">Max</th>
                        <th className="text-center px-4 py-2.5 text-slate-600 font-medium">Normal Range</th>
                        <th className="text-center px-4 py-2.5 text-slate-600 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {Object.entries(report.subscale_scores).map(([name, sub]) => {
                        const elevated = sub.score > sub.normal_max;
                        return (
                          <tr key={name} className={elevated ? 'bg-orange-50' : ''}>
                            <td className="px-4 py-2.5 font-medium text-slate-700">{name}</td>
                            <td className="px-4 py-2.5 text-center font-bold">{sub.score}</td>
                            <td className="px-4 py-2.5 text-center text-slate-500">{sub.max}</td>
                            <td className="px-4 py-2.5 text-center text-green-700">0 – {sub.normal_max}</td>
                            <td className="px-4 py-2.5 text-center">
                              {elevated
                                ? <span className="text-orange-600 font-medium text-xs">▲ Elevated</span>
                                : <span className="text-green-600 text-xs">✓ Normal</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Charts in report */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">Symptom Radar</h4>
                  <SubscaleRadar subscales={report.subscale_scores} />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-700 mb-2">Domain Bar Chart</h4>
                  <SubscaleBarChart subscales={report.subscale_scores} />
                </div>
              </div>

              {/* Elevated domains */}
              {report.elevated_subscales.length > 0 && (
                <div className="bg-orange-50 rounded-xl p-4">
                  <h3 className="font-semibold text-orange-800 mb-1">Elevated Domains</h3>
                  <p className="text-orange-700 text-sm">
                    The following domains scored above the normal range:{' '}
                    <strong>{report.elevated_subscales.join(', ')}</strong>
                  </p>
                </div>
              )}

              {/* Scoring reference */}
              <div>
                <h3 className="font-semibold text-slate-800 mb-2">Score Interpretation Guide</h3>
                <SeverityScale type={selectedAssessment.id} />
              </div>

              {/* Disclaimer */}
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
                <p className="text-xs text-slate-500 leading-relaxed">{report.disclaimer}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default AssessmentPage;
