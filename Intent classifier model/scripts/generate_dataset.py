"""
SAATHI AI -- Intent Classifier Dataset Generator
=================================================
Generates intent_classifier_v1.csv with ~1,500 examples across 7 intent classes.

Schema: id, utterance, primary_intent, secondary_intent, confidence, source, annotator_id, created_at

Classes:
  0 seek_support        -- user wants emotional support / mental health help
  1 book_appointment    -- user wants to schedule a session with a therapist
  2 crisis_emergency    -- user signals imminent danger to self or others
  3 information_request -- user wants factual/educational information
  4 feedback_complaint  -- user giving feedback or complaining
  5 general_chat        -- casual conversation, no specific goal
  6 assessment_request  -- user wants to take a clinical assessment

Run from repo root:
    python "Intent classifier model/scripts/generate_dataset.py"
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ─── Reproducibility ──────────────────────────────────────────────────────────
random.seed(42)

# ─── Output path ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent
OUTPUT_FILE = OUTPUT_DIR / "intent_classifier_v1.csv"

# ─── Intent class target counts ───────────────────────────────────────────────
TARGET_PER_CLASS = {
    "seek_support":       300,
    "book_appointment":   250,
    "crisis_emergency":   250,
    "information_request": 200,
    "feedback_complaint": 150,
    "general_chat":       150,
    "assessment_request": 200,
}

INTENT_CLASSES = list(TARGET_PER_CLASS.keys())

# ─── Secondary intent pairings (contextually plausible) ──────────────────────
SECONDARY_MAP = {
    "seek_support":        ["book_appointment", "general_chat", None, None, None],
    "book_appointment":    ["seek_support", None, None, None],
    "crisis_emergency":    ["seek_support", None, None],
    "information_request": ["assessment_request", "seek_support", None, None],
    "feedback_complaint":  ["general_chat", None, None],
    "general_chat":        ["seek_support", None, None],
    "assessment_request":  ["seek_support", "information_request", None, None],
}

# ─── Utterance pools ──────────────────────────────────────────────────────────

SEEK_SUPPORT_POOL = [
    "I've been feeling really low lately and don't know what to do.",
    "I'm struggling so much and need someone to talk to.",
    "I feel completely overwhelmed by everything.",
    "I think I need some support right now.",
    "Can we talk about what I've been going through?",
    "I've been having a really hard time lately.",
    "I'm not coping well at all.",
    "Everything feels too heavy right now.",
    "I need help dealing with my emotions.",
    "I feel like I'm falling apart.",
    "I'm exhausted from trying to hold everything together.",
    "I've been feeling anxious and sad all the time.",
    "I just need someone to listen to me.",
    "I feel so alone in all of this.",
    "I can't seem to get out of this dark place.",
    "My mental health has been really suffering.",
    "I've been crying a lot and can't understand why.",
    "I feel numb and disconnected from everything.",
    "I've been having panic attacks and don't know how to cope.",
    "I'm struggling with my anxiety more than ever.",
    "I feel like nobody understands what I'm going through.",
    "I need emotional support more than anything right now.",
    "Things have been really difficult at home and I'm not handling it well.",
    "I've been feeling hopeless and don't know what to do.",
    "I can't sleep because my mind won't stop racing.",
    "I feel like I'm losing control of my life.",
    "I've been isolating myself and I know it's not healthy.",
    "I'm scared of my own thoughts lately.",
    "I feel like I'm just going through the motions every day.",
    "I need help working through some really painful feelings.",
    "I've been under so much stress and I'm breaking down.",
    "I feel really vulnerable and could use some guidance.",
    "I think I'm going through depression but I'm not sure.",
    "I've been having a really tough week emotionally.",
    "My relationships are falling apart and I don't know how to cope.",
    "I feel disconnected from myself.",
    "I've been having a lot of dark thoughts.",
    "I need help understanding why I feel this way.",
    "I feel like I'm not good enough no matter what I do.",
    "I've been dealing with grief and it's really hard.",
    "Can you help me process what I'm feeling?",
    "I just want someone to understand me.",
    "I've been carrying so much pain for so long.",
    "I'm not okay and I need help.",
    "I feel like crying but I don't even know why.",
    "I've been having trouble getting out of bed in the mornings.",
    "Everything I try seems to fail and I feel defeated.",
    "I feel completely alone even when I'm around people.",
    "My anxiety is stopping me from living my life.",
    "I just want to feel better.",
    "I've been struggling with my self-worth lately.",
    "I feel like there is no point to anything.",
    "I need someone to help me figure out what I'm going through.",
    "I've been feeling angry and sad at the same time.",
    "I've been neglecting myself and I need help getting back on track.",
    "I feel lost and don't know which direction to go.",
    "My thoughts have been really negative and I can't stop them.",
    "I need emotional guidance through a difficult period.",
    "I feel overwhelmed by my responsibilities and I'm burning out.",
    "I'm struggling with trust issues after being hurt.",
    "I've been feeling like a burden to everyone around me.",
    "I need help managing my emotions better.",
    "I've been feeling really stuck in life.",
    "I'm struggling to find any joy in things I used to love.",
    "I feel like I need professional support but I'm not sure where to start.",
    "I've been really reactive lately and it's affecting my relationships.",
    "I need help dealing with my trauma.",
    "I feel like I'm not living, just surviving.",
    "I've been having a lot of self-doubt.",
    "I'm struggling with loneliness more than ever.",
    "I need help coping with a difficult life event.",
    "I've been feeling really fragile emotionally.",
    "I can't stop overthinking everything.",
    "I've been in a very dark headspace lately.",
    "I feel deeply unhappy and I don't know why.",
    "I need support to get through this difficult time.",
    "I've been really emotional and I need to talk.",
    "I feel like I have no energy for anything.",
    "I'm struggling to keep up with life right now.",
    "I've been feeling very stressed and anxious for weeks.",
    "I need help with my emotional wellbeing.",
    "I feel like my mind is working against me.",
    "I've been having trouble concentrating because of how I feel.",
    "I need to talk about some things that have been bothering me deeply.",
    "I'm exhausted emotionally and I need support.",
    "I've been feeling really down and unmotivated.",
    "I need help making sense of everything I'm feeling.",
    "I've been crying myself to sleep and need support.",
    "I feel broken and don't know how to fix myself.",
    "I've been struggling with my mental health for a while now.",
    "I need help with the anxiety that's been consuming my life.",
    "I feel like I'm always on edge.",
    "I've been having a very rough time and need someone to talk to.",
    "I feel like things will never get better.",
    "I've been feeling really hopeless about the future.",
    "I need to talk about my pain.",
    "I feel really scared and alone.",
    "I've been struggling a lot and I'm reaching out for help.",
    "I need support to deal with what I'm going through.",
    "I feel like I'm drowning in my own thoughts.",
    "I've been feeling really out of control lately.",
    "I need someone to help me find my way through this.",
    "I've been carrying a lot of emotional weight.",
    "I feel like I'm at my breaking point.",
    "I've been struggling with my mental health and I need help.",
    "I feel deeply sad and I don't know how to feel better.",
    "I need help getting through a very difficult period in my life.",
    "I've been feeling so much pain and need someone to talk to.",
    "I feel like there's a heavy fog over everything.",
    "I've been really struggling and I just need support.",
    "I need help processing some really hard emotions.",
    "I feel like I'm not myself anymore.",
    "I've been very overwhelmed and need guidance.",
    "I need someone to talk to about what I've been going through.",
    "I feel like everything is falling apart around me.",
    "I've been dealing with a lot of emotional turmoil.",
    "I need help with coping strategies.",
    "Yaar bahut bura lag raha hai aaj.",
    "Mujhe kisi se baat karni hai.",
    "Bahut mushkil ho raha hai sambhalna.",
    "Main thak gaya hun sab kuch se.",
]

BOOK_APPOINTMENT_POOL = [
    "I'd like to schedule a therapy session.",
    "Can I book an appointment with a therapist?",
    "I want to set up a meeting with a counselor.",
    "How do I schedule a session?",
    "I'd like to make an appointment.",
    "Is there an appointment available this week?",
    "Can I book a session for tomorrow?",
    "I want to book a session for Thursday.",
    "I need to schedule a follow-up appointment.",
    "Can I set up my first therapy session?",
    "I'd like to book a slot with a therapist.",
    "I'm ready to schedule my first appointment.",
    "How do I book a session on this platform?",
    "I want to see a therapist, how do I book?",
    "I need to make an appointment as soon as possible.",
    "Can I reschedule my appointment?",
    "I want to cancel and rebook my session.",
    "I'd like to schedule a weekly session.",
    "Can I get an appointment today?",
    "I want to set up a consultation.",
    "I need to book a therapy appointment.",
    "How do I schedule time with a counselor?",
    "I'd like to get an appointment booked.",
    "Is there a therapist available this weekend?",
    "I want to start regular sessions, how do I book?",
    "Can I schedule a session for next Monday?",
    "I need to set up an appointment with someone.",
    "I'd like to book a session for this afternoon if possible.",
    "Can I get an appointment for Friday?",
    "I want to book an initial consultation.",
    "I'd like to arrange a therapy session.",
    "I want to see someone about my mental health, how do I book?",
    "I'm interested in starting therapy, can I book a session?",
    "I need to set up a regular appointment.",
    "I want to schedule a 45-minute session.",
    "Can I book therapy for this week?",
    "I need to get an appointment booked urgently.",
    "Is it possible to book a session today?",
    "I'd like to set up fortnightly therapy sessions.",
    "I want to book a session with Dr. Sharma.",
    "I need to make an appointment for mental health support.",
    "Can you help me schedule a therapy session?",
    "I want to arrange a session with a counselor.",
    "How do I get started with booking a therapist?",
    "I need to schedule therapy as soon as possible.",
    "I'd like to set up an appointment for next week.",
    "Can I book a session for Monday morning?",
    "I want to schedule my next appointment.",
    "I need to see a therapist urgently, how do I book?",
    "I'd like to organize a regular slot each week.",
    "Can I book a therapy session online?",
    "I want to set up a video session.",
    "I'd like to schedule a phone consultation first.",
    "Can I make a booking for couples therapy?",
    "I want to schedule a family therapy session.",
    "I need to rebook my cancelled appointment.",
    "I'd like to get on the schedule this week.",
    "Can I see if there are any openings today?",
    "I want to book a session and need to know the available times.",
    "I'd like to arrange regular therapy appointments.",
    "Can you tell me how to book a session on here?",
    "I want to start therapy and need to book my first session.",
    "I'd like to get an appointment as soon as there's availability.",
    "I need to book an emergency session.",
    "Can I schedule a session for sometime next week?",
    "I want to make an appointment for this Thursday.",
    "I'd like to set up a consultation call first.",
    "I need to schedule a session to discuss my anxiety.",
    "Can I book a session in the evening?",
    "I want to book a morning appointment.",
    "Session book karna hai mujhe.",
    "Appointment kaise lun yahan se?",
    "Therapist se milna hai, kaise book karein?",
    "Mujhe ek session schedule karna hai.",
    "Main therapist se milna chahta hun, booking kaise hogi?",
]

CRISIS_EMERGENCY_POOL = [
    "I want to hurt myself.",
    "I'm thinking about ending my life.",
    "I don't want to be here anymore.",
    "I've been having thoughts of suicide.",
    "I feel like I can't go on.",
    "I want to kill myself.",
    "I've been thinking about harming myself.",
    "I don't see any reason to live.",
    "I've planned how I would end my life.",
    "I'm going to hurt myself tonight.",
    "I can't take this anymore and I'm thinking of a way out.",
    "I've been cutting myself to cope.",
    "I feel like disappearing forever.",
    "I don't want to wake up tomorrow.",
    "I've been having thoughts that it would be better if I wasn't here.",
    "I'm in danger right now.",
    "I have access to something I could hurt myself with.",
    "I don't think I can keep myself safe.",
    "I've already taken some pills.",
    "I feel like ending everything.",
    "I've been thinking about suicide every day.",
    "I have a plan to kill myself.",
    "I feel like death is the only way out.",
    "I don't want to live anymore.",
    "I've been thinking of ways to hurt myself.",
    "I want to disappear from this world.",
    "I feel completely worthless and like dying.",
    "I've been self-harming and I need help.",
    "I'm thinking about jumping off a bridge.",
    "I feel like the world would be better without me.",
    "I have overdosed before and I'm thinking of doing it again.",
    "I feel like hurting someone else too.",
    "I'm a danger to myself.",
    "I can't stop thinking about killing myself.",
    "I've written a goodbye letter.",
    "I don't think I'll make it through the night.",
    "I've been stockpiling medication to end it.",
    "I feel like I'm about to do something drastic.",
    "I'm at the edge and I don't know what will happen.",
    "I've been having violent thoughts about myself.",
    "I feel like there's no way out except death.",
    "I've been hurting myself regularly and can't stop.",
    "I'm scared of what I might do to myself.",
    "I feel completely hopeless and suicidal.",
    "I'm in a very dark place and I'm not safe.",
    "I feel like I want to end my suffering permanently.",
    "I've been thinking that everyone would be better off without me.",
    "I want to stop existing.",
    "I feel like I'm going to act on my thoughts soon.",
    "I've been thinking about this for a long time and I'm ready.",
    "I don't see any future for myself.",
    "I feel like there is no hope and I want to die.",
    "I've been struggling with suicidal thoughts for weeks.",
    "I'm having thoughts of self-harm right now.",
    "I feel like I need to escape permanently.",
    "I've been fantasizing about dying.",
    "I'm scared I will hurt myself tonight.",
    "I feel like the pain will only stop if I'm dead.",
    "I've been thinking about driving into traffic.",
    "I feel like I have nothing left to live for.",
    "I'm at a crisis point right now.",
    "I don't want to live but I'm scared.",
    "I've been thinking about ways to end my life for weeks.",
    "I feel worthless and like ending it all.",
    "I'm having a mental health crisis.",
    "I need immediate help -- I'm not safe.",
    "I'm in crisis and I don't know what to do.",
    "I've hurt myself badly.",
    "I'm thinking of ending things tonight.",
    "I feel completely trapped and want to die.",
    "I've been having urges to hurt myself that I can't control.",
    "I'm scared of myself right now.",
    "Khud ko hurt karna chahta hun.",
    "Main jeena nahi chahta.",
    "Mujhe nahi lagna apni zindagi mein koi matlab hai.",
    "Main bahut bura feeling kar raha hun, kuch kar lunga.",
]

INFORMATION_REQUEST_POOL = [
    "What is CBT?",
    "How does cognitive behavioral therapy work?",
    "What is the difference between anxiety and depression?",
    "Can you explain what mindfulness is?",
    "What are the symptoms of depression?",
    "What is DBT therapy?",
    "How does therapy actually help people?",
    "What is EMDR therapy?",
    "What are the types of anxiety disorders?",
    "What is the PHQ-9 test?",
    "How does meditation help with mental health?",
    "What are the signs of burnout?",
    "What is GAD-7?",
    "What is attachment theory?",
    "How does trauma affect the brain?",
    "What is psychotherapy?",
    "What is the difference between a psychologist and a psychiatrist?",
    "What medications are used for depression?",
    "What is exposure therapy?",
    "How long does therapy usually take?",
    "What is the DSM-5?",
    "What is schema therapy?",
    "Can anxiety be cured?",
    "What is the fight-or-flight response?",
    "What are coping strategies for panic attacks?",
    "What is the difference between stress and anxiety?",
    "What is interpersonal therapy?",
    "How do I know if I need therapy?",
    "What is a mental health crisis?",
    "What is the difference between sadness and depression?",
    "How does sleep affect mental health?",
    "What is acceptance and commitment therapy?",
    "What is PTSD?",
    "How do antidepressants work?",
    "What is the connection between exercise and mental health?",
    "What is borderline personality disorder?",
    "What is self-harm and why do people do it?",
    "What is the cycle of trauma?",
    "What are grounding techniques?",
    "What is solution-focused therapy?",
    "What is the difference between OCD and anxiety?",
    "How does journaling help mental health?",
    "What are the stages of grief?",
    "What is narrative therapy?",
    "What is the window of tolerance in trauma?",
    "How does this platform work?",
    "What services does Saathi AI offer?",
    "What are the pricing plans?",
    "What qualifications do your therapists have?",
    "What is the difference between coaching and therapy?",
    "What is the 5-4-3-2-1 grounding technique?",
    "What is somatic therapy?",
    "What causes panic attacks?",
    "What is bipolar disorder?",
    "What is the relationship between gut health and mental health?",
    "What does 'going to therapy' actually involve?",
    "What is complex PTSD?",
    "What is the difference between group therapy and individual therapy?",
    "How does breathing affect anxiety?",
    "What are the long-term effects of untreated depression?",
    "What is motivational interviewing?",
    "What is hypervigilance?",
    "What is dissociation?",
    "What are the early warning signs of a mental health problem?",
    "What is emotional regulation?",
    "What is the Socratic method in therapy?",
    "What are the benefits of therapy?",
    "What does a first therapy session look like?",
    "CBT kya hota hai?",
    "Therapy kaise kaam karti hai?",
    "Anxiety aur depression mein kya fark hai?",
    "Mindfulness ke baare mein batao.",
]

FEEDBACK_COMPLAINT_POOL = [
    "This app is not working properly.",
    "The chatbot doesn't understand me at all.",
    "I'm not happy with the service.",
    "Your responses are completely unhelpful.",
    "I've been waiting for a response for too long.",
    "The app keeps crashing.",
    "This is a terrible experience.",
    "I feel like I'm talking to a wall.",
    "Your AI responses are generic and unhelpful.",
    "I've had a very bad experience with this platform.",
    "The therapist I was matched with wasn't right for me.",
    "I'm disappointed with the quality of support.",
    "I can't log into my account.",
    "The payment didn't go through but I was charged.",
    "I can't access my previous sessions.",
    "This platform is too expensive for what it offers.",
    "I'm not getting the support I expected.",
    "The scheduling system is very confusing.",
    "I want to give feedback about my recent session.",
    "The therapist cancelled without notice.",
    "I've been billed incorrectly.",
    "My data doesn't seem to be saving properly.",
    "I want to make a formal complaint.",
    "The notifications are very annoying.",
    "I can't find the settings to change my preferences.",
    "The video call quality was terrible.",
    "I'm not satisfied with my recent session.",
    "The platform is hard to navigate.",
    "I feel like my privacy is not being respected.",
    "There was a technical error during my session.",
    "I want to delete my account.",
    "I've had issues every time I try to use this app.",
    "I'm frustrated with the lack of response.",
    "The waiting time is too long.",
    "I want a refund for my last session.",
    "This platform doesn't feel safe to use.",
    "I have a suggestion for improving the chatbot.",
    "I've been matched with the wrong type of therapist.",
    "Your onboarding process was very confusing.",
    "I think there's a bug in the assessment section.",
    "The app doesn't work on my phone.",
    "I'm not impressed with the service so far.",
    "I want to report an issue with the platform.",
    "The reminder emails are too frequent.",
    "I wish there were more therapist options available.",
    "I've tried contacting support but got no reply.",
    "The session ended abruptly and I lost my progress.",
    "I'm concerned about how my data is being used.",
    "The interface is very unintuitive.",
    "I think the AI responses need a lot of improvement.",
    "Ye app sahi se kaam nahi kar raha.",
    "Mujhe refund chahiye.",
    "Chatbot bilkul samajh nahi raha meri baat.",
]

GENERAL_CHAT_POOL = [
    "Hello, how are you today?",
    "Hi there!",
    "Hey, what can you help me with?",
    "Good morning!",
    "What's up?",
    "Just wanted to say hi.",
    "Tell me something interesting.",
    "What can you do?",
    "I'm just browsing.",
    "What kind of support do you offer?",
    "I was curious about this app.",
    "Can we just chat for a bit?",
    "I'm bored and wanted to talk.",
    "What's new?",
    "How does this all work?",
    "I've heard about this app and wanted to try it.",
    "Can you tell me more about yourself?",
    "What's the weather like where you are? Just kidding.",
    "I'm not sure why I'm here, just exploring.",
    "Can we talk about something light today?",
    "I just wanted to check in.",
    "I'm doing okay today, just wanted to say hello.",
    "What are your capabilities?",
    "I was just thinking and wanted to chat.",
    "What do you like to talk about?",
    "Just saying hi before I get into anything serious.",
    "Hi, I'm new here.",
    "I wanted to introduce myself.",
    "I'm not ready to talk about anything deep yet.",
    "Can we keep things light today?",
    "I'm just looking around at the moment.",
    "What would you recommend I try first?",
    "I was referred here by a friend.",
    "I'm just getting started.",
    "Can you give me an overview of what's available?",
    "I just wanted to test the app.",
    "Hi, I wanted to check out this platform.",
    "I'm not sure what I need yet.",
    "Just passing time and thought I'd chat.",
    "What can I do here?",
    "I don't have a specific question, just exploring.",
    "Tell me about yourself.",
    "I'm here for the first time.",
    "Is this thing working?",
    "Let's just talk.",
    "Nothing serious today, just wanted to connect.",
    "I'm fine right now, just exploring the app.",
    "Good evening! How are you?",
    "I wanted to see what this chatbot is like.",
    "Hello, testing testing!",
    "Kaise ho aap?",
    "Baat karte hain thodi der.",
    "Sirf explore kar raha hun.",
    "Kuch naya hai kya?",
    "Bas hello kehna tha.",
]

ASSESSMENT_REQUEST_POOL = [
    "I want to take the PHQ-9 test.",
    "Can I do a depression assessment?",
    "I'd like to check my anxiety levels.",
    "Can I complete the GAD-7 questionnaire?",
    "I want to take a mental health assessment.",
    "Can I do the stress test?",
    "I'd like to assess my current state of mind.",
    "Can you give me a questionnaire about my depression?",
    "I want to take the DASS-21.",
    "I'd like to do a wellbeing assessment.",
    "Can we do an evaluation of my mental health today?",
    "I want to check if I have anxiety.",
    "Can I take a test to see how I'm doing mentally?",
    "I'd like to complete an assessment form.",
    "Let's do the PHQ-9 assessment.",
    "Can I take the depression screening test?",
    "I want to assess my PTSD symptoms.",
    "Can I take a stress evaluation test?",
    "I'd like to do a clinical assessment.",
    "Can you assess my current mental health?",
    "I want to take the mood questionnaire.",
    "I'd like to evaluate my anxiety symptoms.",
    "Can we do the GAD-7 today?",
    "I want to take a self-assessment test.",
    "I want to do the depression test today.",
    "Can I take a questionnaire about my mental health?",
    "I'd like to complete the anxiety assessment.",
    "Can I evaluate my current wellbeing?",
    "I want to start with an assessment.",
    "Can I take the standard mental health screening?",
    "I want to see where I'm at with a proper evaluation.",
    "Can I complete the intake assessment?",
    "I'd like to take the clinical screening tests.",
    "Can we do an assessment of my depression?",
    "I want to take a mental wellness quiz.",
    "Can I do a formal evaluation of my symptoms?",
    "I'd like to complete a standardized test.",
    "Can you give me the PHQ-9 now?",
    "I want to measure my anxiety levels with a test.",
    "Can I take a mood assessment today?",
    "I'd like to track my mental health with assessments.",
    "Can I start the mental health evaluation?",
    "I want to complete the full assessment battery.",
    "Can we do the depression and anxiety tests?",
    "I'd like to take the PTSD screening.",
    "Can I do a baseline mental health check?",
    "I want to take an assessment for OCD symptoms.",
    "Can I evaluate my burnout levels?",
    "I'd like to do the PCL-5 screening.",
    "Can I take a formal mental health assessment?",
    "PHQ-9 test lena hai mujhe.",
    "Kya main apni anxiety test kar sakta hun?",
    "Depression ka assessment karna hai.",
    "Mujhe mental health evaluation chahiye.",
    "GAD-7 questionnaire dena hai.",
    "Apni condition check karni hai test se.",
    "Kya main yahan koi assessment le sakta hun?",
    "Stress test lena hai mujhe aaj.",
]

# ─── Pool registry ─────────────────────────────────────────────────────────────
POOLS = {
    "seek_support":        SEEK_SUPPORT_POOL,
    "book_appointment":    BOOK_APPOINTMENT_POOL,
    "crisis_emergency":    CRISIS_EMERGENCY_POOL,
    "information_request": INFORMATION_REQUEST_POOL,
    "feedback_complaint":  FEEDBACK_COMPLAINT_POOL,
    "general_chat":        GENERAL_CHAT_POOL,
    "assessment_request":  ASSESSMENT_REQUEST_POOL,
}

# ─── Confidence pools (class-specific) ────────────────────────────────────────
CONFIDENCE_POOLS = {
    "seek_support":        [0.85, 0.88, 0.90, 0.92, 0.95, 0.97],
    "book_appointment":    [0.90, 0.92, 0.94, 0.96, 0.98],
    "crisis_emergency":    [0.90, 0.93, 0.95, 0.97, 0.99],
    "information_request": [0.88, 0.90, 0.92, 0.95, 0.97],
    "feedback_complaint":  [0.85, 0.88, 0.90, 0.93, 0.95],
    "general_chat":        [0.85, 0.88, 0.90, 0.92, 0.95],
    "assessment_request":  [0.88, 0.90, 0.93, 0.95, 0.97],
}


def generate_timestamp() -> str:
    base = datetime(2024, 6, 1)
    offset = timedelta(seconds=random.randint(0, 60 * 60 * 24 * 300))
    return (base + offset).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_dataset():
    rows = []
    counter = 1

    for intent, target in TARGET_PER_CLASS.items():
        pool = POOLS[intent]
        # Sample up to target; if pool smaller, use all and allow repeats for remainder
        if len(pool) >= target:
            utterances = random.sample(pool, target)
        else:
            utterances = pool.copy()
            while len(utterances) < target:
                utterances.append(random.choice(pool))
            random.shuffle(utterances)

        for utt in utterances:
            secondary_pool = SECONDARY_MAP[intent]
            secondary = random.choice(secondary_pool)

            rows.append({
                "id":               f"intent_{counter:06d}",
                "utterance":        utt,
                "primary_intent":   intent,
                "secondary_intent": secondary if secondary else "",
                "confidence":       random.choice(CONFIDENCE_POOLS[intent]),
                "source":           "synthetic",
                "annotator_id":     f"ann_{random.randint(1, 5):03d}",
                "created_at":       generate_timestamp(),
            })
            counter += 1

    random.shuffle(rows)

    # Renumber after shuffle
    for i, row in enumerate(rows, 1):
        row["id"] = f"intent_{i:06d}"

    return rows


def evaluate_distribution(rows):
    from collections import Counter
    counts = Counter(r["primary_intent"] for r in rows)
    total = len(rows)
    print(f"\nDataset: {total} total examples")
    print(f"{'Class':<22} {'Count':>6}  {'%':>6}  {'Target':>7}")
    print("-" * 50)
    for intent in INTENT_CLASSES:
        n = counts[intent]
        pct = 100 * n / total
        target = TARGET_PER_CLASS[intent]
        print(f"  {intent:<20} {n:>6}  {pct:>5.1f}%  {target:>7}")

    # Check secondary distribution
    sec_counts = Counter(r["secondary_intent"] for r in rows if r["secondary_intent"])
    print(f"\nSecondary intent distribution (non-null):")
    for intent, n in sec_counts.most_common():
        print(f"  {intent:<22} : {n}")

    # Unique starts per class (phrasing diversity check)
    print(f"\nPhrasing diversity (unique first words per class):")
    from collections import defaultdict
    class_utts = defaultdict(list)
    for r in rows:
        class_utts[r["primary_intent"]].append(r["utterance"])
    for intent in INTENT_CLASSES:
        utts = class_utts[intent]
        starts = set(u.split()[0].lower() for u in utts if u)
        print(f"  {intent:<22}: {len(starts)} unique start words (target >10)")


if __name__ == "__main__":
    print("SAATHI AI -- Intent Classifier Dataset Generator")
    print("=" * 50)

    rows = generate_dataset()
    evaluate_distribution(rows)

    # Write CSV
    fieldnames = ["id", "utterance", "primary_intent", "secondary_intent",
                  "confidence", "source", "annotator_id", "created_at"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {OUTPUT_FILE}")
    print("Next step: python scripts/prepare_data_splits.py")
