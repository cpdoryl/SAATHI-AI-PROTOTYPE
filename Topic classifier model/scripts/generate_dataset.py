"""
SAATHI AI -- Topic Classifier Dataset Generator
================================================
Generates topic_classifier_v1.csv with ~1,500 examples across 5 topic classes.
Approximately 30% of examples are multi-label (2 co-occurring topics).

Schema: id, utterance, topics, primary_topic, confidence, source, annotator_id, created_at

Classes (multi-label — a message can belong to multiple):
  0 workplace_stress    -- job pressure, boss issues, burnout, deadlines, career anxiety
  1 relationship_issues -- romantic, family, friendship, loneliness, divorce, conflict
  2 academic_stress     -- exams, grades, perfectionism, student loans, career uncertainty
  3 health_concerns     -- illness, chronic pain, health anxiety, somatic complaints
  4 financial_stress    -- debt, job loss, money anxiety, financial shame

Run from repo root:
    python "Topic classifier model/scripts/generate_dataset.py"
"""

import csv
import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

SCRIPT_DIR  = Path(__file__).resolve().parent
BASE_DIR    = SCRIPT_DIR.parent
OUTPUT_FILE = BASE_DIR / "topic_classifier_v1.csv"

TOPICS = [
    "workplace_stress",
    "relationship_issues",
    "academic_stress",
    "health_concerns",
    "financial_stress",
]

# ─── Single-label target counts ───────────────────────────────────────────────
SINGLE_LABEL_TARGETS = {
    "workplace_stress":    240,
    "relationship_issues": 210,
    "academic_stress":     210,
    "health_concerns":     175,
    "financial_stress":    175,
}  # Total ~1,010

# ─── Multi-label pair targets ──────────────────────────────────────────────────
MULTI_LABEL_PAIRS = [
    ("workplace_stress",    "relationship_issues",  90),
    ("workplace_stress",    "financial_stress",     70),
    ("academic_stress",     "relationship_issues",  65),
    ("academic_stress",     "health_concerns",      55),
    ("relationship_issues", "financial_stress",     60),
    ("health_concerns",     "financial_stress",     50),
]  # Total ~390

# Combined total: ~1,400 examples

# ─── Utterance pools ──────────────────────────────────────────────────────────

WORKPLACE_POOL = [
    "My manager keeps criticising everything I do and I can't take it anymore.",
    "I'm completely burned out from working 12-hour days.",
    "I'm scared I'm going to lose my job and I don't know what to do.",
    "My boss takes credit for all my work and never acknowledges my contributions.",
    "The workplace is toxic and I dread going in every morning.",
    "I've been passed over for promotion three times and I'm losing faith.",
    "I work so much that I have no time for anything else in my life.",
    "My colleagues bully me and HR isn't doing anything about it.",
    "I feel like a failure at work even though I try my hardest.",
    "I have too many deadlines and I'm drowning in work.",
    "I can't stop thinking about work even when I'm at home.",
    "My job is killing me slowly — the stress is unbearable.",
    "I was laid off last month and I feel completely lost.",
    "The office politics are exhausting and I'm thinking of quitting.",
    "I'm suffering from severe burnout and I don't know how to recover.",
    "My work environment is making me physically sick.",
    "I feel undervalued and disrespected at work every single day.",
    "I have been micromanaged to the point where I can't do anything right.",
    "I'm afraid of making mistakes at work and it's paralyzing me.",
    "My career feels completely stuck and I have no idea what to do next.",
    "I'm in a high-pressure sales job and the targets are impossible.",
    "My team is hostile toward me and it's affecting my mental health.",
    "I was recently fired and I feel ashamed and worthless.",
    "I can't separate my self-worth from my performance at work.",
    "The constant criticism from my supervisor is destroying my confidence.",
    "I feel trapped in a job I hate but I can't afford to leave.",
    "I've been working nights and weekends for months and I'm exhausted.",
    "I was humiliated in front of my colleagues by my manager.",
    "I'm dealing with a very difficult colleague who makes my work life hell.",
    "I keep having panic attacks before important meetings.",
    "My job requires me to be available 24/7 and I have no boundaries.",
    "I'm struggling with imposter syndrome at work.",
    "I'm a junior employee being asked to do a senior employee's job.",
    "The company I work for is downsizing and I'm terrified.",
    "I gave up everything for this job and it's not working out.",
    "I've been passed over again and I feel invisible at work.",
    "I work in a hostile environment with constant conflict.",
    "My mental health is suffering because of my work situation.",
    "I'm exhausted and I feel like I can never do enough at work.",
    "I'm considering leaving my career entirely because of the stress.",
    "I can't sleep because I keep worrying about work problems.",
    "I feel like a cog in a machine at my job — completely replaceable.",
    "My workload is unmanageable and nobody seems to care.",
    "I was bullied at work and it has left me shaken.",
    "I'm struggling to perform at work because of the pressure.",
    "Naukri pe bahut zyada pressure hai aur main thak gaya hun.",
    "Boss se bahut problems ho rahi hain.",
    "Kaam ki wajah se zindagi kharab ho rahi hai.",
    "Office mein sab kuch bahut stressful ho gaya hai.",
    "Job ja sakti hai meri aur main darr raha hun.",
    "Burnout feel ho raha hai, kuch karna nahi chahta.",
    "Appraisal mein phir se ignore kiya gaya mujhe.",
    "Workplace pe mera confidence bahut kam ho gaya hai.",
]

RELATIONSHIP_POOL = [
    "My partner and I fight constantly and I'm not sure we can fix this.",
    "I feel so lonely even though I'm in a relationship.",
    "My family never understands me no matter how hard I try.",
    "I went through a painful breakup and I can't move on.",
    "My parents are getting divorced and it's tearing our family apart.",
    "I have trust issues after being cheated on and I can't let my guard down.",
    "I feel disconnected from my partner and I don't know how to reconnect.",
    "My closest friend betrayed me and I'm struggling to trust people again.",
    "I feel invisible in my relationship — like my needs don't matter.",
    "My relationship is emotionally abusive but I don't know how to leave.",
    "I'm dealing with a controlling partner and it's affecting my wellbeing.",
    "I feel deeply lonely and isolated and it's affecting my mental health.",
    "My parents put enormous pressure on me and it's damaging our relationship.",
    "I miss my family back home and the loneliness is crushing me.",
    "My spouse and I can't communicate without it turning into a fight.",
    "I'm going through a separation and the grief feels unbearable.",
    "I've been in a toxic relationship for years and I can't leave.",
    "My mother is very critical and it has impacted my self-esteem my whole life.",
    "I struggle to form close friendships and I often feel alone.",
    "My marriage is falling apart and I don't know how to save it.",
    "I keep attracting the wrong kind of people into my life.",
    "My partner doesn't seem to care about my emotional needs.",
    "I'm afraid of being abandoned and it's ruining my relationship.",
    "My sibling is going through something terrible and I feel helpless.",
    "I feel like I give so much in relationships and get nothing back.",
    "I've been divorced for two years and still feel like a failure.",
    "I'm struggling with jealousy in my relationship and it's driving me crazy.",
    "My partner and I have completely different values and it's causing conflict.",
    "I feel smothered in my relationship and I don't know what to do.",
    "The communication in my relationship has completely broken down.",
    "I'm going through grief after losing my best friend.",
    "I was in an abusive relationship and I'm still recovering from it.",
    "I feel like my family doesn't love me the way I need to be loved.",
    "My romantic relationship ended and I feel completely lost.",
    "I have codependency issues and I keep losing myself in relationships.",
    "My partner left me and I don't know how to cope with the loneliness.",
    "My relationships always fall apart and I don't understand why.",
    "I feel invisible in my family — like my voice doesn't matter.",
    "I'm struggling with a difficult divorce and custody battle.",
    "I feel deeply misunderstood by everyone around me.",
    "I have no close friends and the isolation is becoming unbearable.",
    "My in-laws create so much stress in my marriage.",
    "I don't know how to set boundaries with toxic family members.",
    "My children are struggling and I feel like a failure as a parent.",
    "Rishton mein bahut takleef ho rahi hai.",
    "Partner ke saath bahut jhagde ho rahe hain.",
    "Tanha feel hota hai bahut zyada.",
    "Breakup ke baad sambhalna mushkil ho raha hai.",
    "Ghar mein koi mujhe samajhta hi nahi.",
    "Maa-baap bahut pressure dete hain aur main thak gaya hun.",
    "Pyar mein dhoka mila aur ab trust nahi kar sakta.",
    "Pariwar ke saath tension bahut badh gayi hai.",
]

ACADEMIC_POOL = [
    "I'm so stressed about my upcoming exams that I can't sleep.",
    "I'm failing my course and I feel like a complete failure.",
    "The pressure from my parents to get top grades is unbearable.",
    "I'm struggling with perfectionism and it's affecting my studies.",
    "I have exam anxiety so bad that I freeze during tests.",
    "I'm in a competitive programme and I feel like I don't belong.",
    "I'm behind on all my assignments and I don't know how to catch up.",
    "I dropped out of college and I feel ashamed and lost.",
    "I'm struggling with procrastination and my grades are suffering.",
    "I have no idea what career path to choose and it's terrifying.",
    "I'm in my final year and I'm terrified of graduating and entering the real world.",
    "My student loan debt is overwhelming and I'm not sure my degree was worth it.",
    "I'm dealing with imposter syndrome at university.",
    "I'm a first-generation student and I feel completely out of place.",
    "I can't focus on my studies because of everything going on in my life.",
    "I have been studying for years and I still haven't found success.",
    "I feel intense pressure to be the best in my class.",
    "I failed an important exam and I can't stop beating myself up.",
    "I'm in medical school and the workload is destroying my mental health.",
    "I feel like I'm not smart enough to be where I am academically.",
    "I'm constantly comparing myself to other students and feeling inferior.",
    "My academic career feels like a disaster and I don't know what to do.",
    "I'm doing a PhD and I'm deeply unhappy with my progress.",
    "I have multiple assignments due this week and I'm completely overwhelmed.",
    "I'm paralysed by the fear of failing and can't start my work.",
    "I have test anxiety that makes me forget everything I've studied.",
    "I took a gap year and now I feel behind all my peers.",
    "I'm in a course I hate but I don't know what else to do.",
    "My academic performance has been declining and I'm scared.",
    "I'm a student dealing with burnout from constant studying.",
    "I feel ashamed about my grades and hide them from my family.",
    "I'm in my third year and I'm having a massive crisis about my future.",
    "I chose the wrong field and now I'm stuck and don't know what to do.",
    "The competitive nature of my programme is making everyone miserable.",
    "I feel like I'm always just barely surviving academically.",
    "My thesis is due and I've barely started — I'm in panic mode.",
    "I'm worried I'll never get a job in my field after all this studying.",
    "I have ADHD and my academic performance suffers as a result.",
    "My professors don't support me and I feel completely on my own.",
    "Exams se pehle bahut ghabra jaata hun.",
    "Padhai mein focus nahi ho raha kuch bhi.",
    "Marks ache nahi aaye aur sab naraaz hain mujhse.",
    "Career ke baare mein kuch samajh nahi aa raha.",
    "College mein struggle ho raha hai bahut.",
    "Perfectionist hun aur khud pe bahut pressure deta hun.",
    "Exam fail kar liya aur ab samjh nahi aa raha kya karoon.",
    "Future ke baare mein dar lag raha hai.",
]

HEALTH_POOL = [
    "I was recently diagnosed with a serious illness and I'm terrified.",
    "I have chronic pain that never goes away and it's affecting everything.",
    "I'm convinced something is very wrong with me but doctors can't find it.",
    "I've been suffering from severe migraines for months.",
    "I have health anxiety and I constantly fear the worst.",
    "I was diagnosed with a chronic condition and I'm struggling to accept it.",
    "I'm dealing with long COVID and I feel like I'll never recover.",
    "My doctor found something worrying on my scan and I'm waiting for results.",
    "I have somatic symptoms — physical pain with no clear medical cause.",
    "I'm terrified of dying and it's consuming my every thought.",
    "I have an autoimmune disease that is unpredictable and frightening.",
    "I can't stop googling my symptoms and it's making my anxiety worse.",
    "I had a heart scare last week and I haven't recovered mentally.",
    "I'm dealing with a family member's terminal illness.",
    "I've been battling cancer and the emotional toll is enormous.",
    "I'm scared to get medical tests because I'm afraid of what they'll find.",
    "I have chronic fatigue syndrome and I've lost my former life.",
    "I've been diagnosed with diabetes and I'm struggling to adjust.",
    "I have persistent back pain that has ended my ability to do things I love.",
    "I'm afraid my illness will get worse and I'll be unable to work.",
    "I have a sleep disorder and the exhaustion is destroying my quality of life.",
    "I was recently hospitalised and I'm still processing the trauma.",
    "I live in constant fear of having another panic attack.",
    "I have fibromyalgia and some days I can barely get out of bed.",
    "I have a phobia of hospitals and medical procedures.",
    "My mental health is making my physical symptoms worse.",
    "I was told I might need surgery and I'm absolutely terrified.",
    "I have reproductive health issues that have devastated me.",
    "I am dealing with the physical effects of long-term stress.",
    "I've had recurring infections that won't resolve and I'm exhausted.",
    "My chronic condition has isolated me from friends and family.",
    "I was diagnosed with a neurological condition and I'm in shock.",
    "I have severe IBS that controls my life and makes me anxious.",
    "Health anxiety is stopping me from living normally.",
    "I feel like my body is betraying me and I don't know how to cope.",
    "Tabiyat theek nahi rehti aur main darr gaya hun.",
    "Koi bimari hai jo theek hi nahi ho rahi.",
    "Doctors ke paas jaana mujhe bahut dara deta hai.",
    "Chronic pain ki wajah se zindagi bahut mushkil ho gayi hai.",
    "Health ki wajah se sab kuch rok diya hai mujhne.",
]

FINANCIAL_POOL = [
    "I'm drowning in debt and I can't see a way out.",
    "I lost my job last month and I can't pay my bills.",
    "I feel deep shame about my financial situation.",
    "I have borrowed money from family and I'm too embarrassed to face them.",
    "I can't afford basic necessities and it's terrifying.",
    "I'm worried I'll never be financially stable.",
    "I've made terrible financial decisions and I can't forgive myself.",
    "My debt is mounting every month and I don't know how to stop it.",
    "I have no savings and an unexpected expense has wiped me out.",
    "I'm supporting my family alone and the financial pressure is crushing.",
    "I was scammed and lost my entire savings.",
    "I'm terrified of bankruptcy and what it means for my future.",
    "I feel like a financial failure compared to everyone around me.",
    "I can't sleep because I keep worrying about money.",
    "I've been unemployed for six months and my confidence is shattered.",
    "I'm using credit cards to survive and the interest is piling up.",
    "My business failed and I've lost everything I worked for.",
    "I feel completely ashamed of how much debt I'm in.",
    "I can't provide for my children the way I want to.",
    "I grew up in poverty and I'm terrified of going back there.",
    "I've been living paycheck to paycheck for years and I'm exhausted.",
    "I'm in a low-paying job and I can't make ends meet.",
    "My partner and I fight constantly about money.",
    "I feel embarrassed about not being able to afford things my peers can.",
    "I have medical bills that I cannot pay and I'm overwhelmed.",
    "I spent years building my business and it collapsed — I've lost everything.",
    "Financial stress is affecting my health and my relationships.",
    "I've never been good with money and I feel hopeless about it.",
    "I'm afraid to open my bank statements.",
    "I owe money to people I love and I feel terrible about it.",
    "I had to sell my home because of financial difficulties.",
    "I'm on the verge of eviction and I'm completely panicking.",
    "Paise ki bahut taqleef hai aur samajh nahi aa raha kya karoon.",
    "Karza bahut ho gaya hai aur main thak gaya hun.",
    "Naukri chali gayi aur bills nahi bhar sakta.",
    "Paise ki kami ki wajah se sab se sharmaata hun.",
    "Financially bahut stress mein hun aur neend nahi aa rahi.",
]

# ─── Multi-label utterance pools (per pair) ───────────────────────────────────

WORK_RELATION_POOL = [
    "My job stress is bleeding into my marriage and we fight constantly about it.",
    "I work so much I have no time for my partner and they're fed up.",
    "My toxic work environment is making me take out my frustration on my family.",
    "I was laid off and now my relationship is under enormous strain.",
    "My boss is making my life hell and I'm taking it out on my partner.",
    "I can't balance work demands and my family keeps suffering for it.",
    "The pressure at work is making me emotionally unavailable to my partner.",
    "My career ambition and my relationship are in constant conflict.",
    "I travel too much for work and my family is falling apart.",
    "Work stress is making me irritable and hurting my closest relationships.",
    "My promotion means relocating and it's causing a crisis in my relationship.",
    "I feel like I'm failing as both a professional and as a partner.",
    "My boss's criticism is making me depressed and my partner doesn't know how to help.",
    "I've been working from home and my partner and I are constantly in conflict.",
    "The financial pressure from losing my job is affecting my marriage.",
    "My family feels I prioritise work over them and they're right.",
    "Work-life balance has collapsed and both my career and my relationship are suffering.",
    "I'm burned out and distant from my family because of constant work stress.",
    "Kaam ki wajah se ghar mein bhi tension rehti hai.",
    "Burnout ki wajah se partner ke saath relationship kharab ho gayi.",
]

WORK_FINANCE_POOL = [
    "I'm afraid I'll lose my job and I won't be able to pay my mortgage.",
    "I work in a toxic environment but I can't quit because I need the money.",
    "I was passed over for a raise and now I can barely afford my bills.",
    "I'm underpaid and overworked and the financial pressure is making me anxious.",
    "I've been laid off and I'm panicking about how to pay my debts.",
    "The stress of financial instability is making it hard to perform at work.",
    "I can't negotiate a better salary because I'm scared of losing my job.",
    "I'm working two jobs to make ends meet and I'm completely exhausted.",
    "My company is going under and I'm terrified about my financial future.",
    "I feel trapped in a bad job because of my financial obligations.",
    "I was demoted and my pay was cut — I don't know how I'll survive.",
    "I have credit card debt from a period of unemployment and it's overwhelming.",
    "I'm working in a terrible environment but the pay is keeping me there.",
    "Job ja sakti hai aur paise ki bhi bahut tension hai.",
    "Naukri ka pressure aur karza — dono saath mein sata rahe hain.",
]

ACAD_RELATION_POOL = [
    "My studies are suffering because my relationship is falling apart.",
    "I can't focus on my exams because of the fighting at home.",
    "My parents' high expectations and our constant conflicts are destroying my studies.",
    "My boyfriend and I broke up right before finals and I'm falling apart.",
    "I'm away at university and I'm desperately lonely without my family.",
    "The pressure from my parents about grades is damaging our relationship.",
    "I'm struggling to study because my family is going through a crisis.",
    "I'm in a long-distance relationship while doing my degree and it's unsustainable.",
    "I can't balance my academic commitments and my relationship — both are suffering.",
    "My parents don't support my choice of career and we've stopped speaking.",
    "I feel completely alone at university and my grades are reflecting that.",
    "My toxic relationship is preventing me from focusing on my studies.",
    "My partner doesn't understand the pressure I'm under academically.",
    "Breakup ki wajah se padhai bilkul nahi ho rahi.",
    "Ghar mein tension hai toh studies pe dhyan nahi rehta.",
]

ACAD_HEALTH_POOL = [
    "I have a chronic illness and it's making it impossible to keep up with my studies.",
    "I developed anxiety during exam season and now I'm physically sick too.",
    "My health problems have caused me to miss so much university that I might fail.",
    "I'm dealing with depression and it's derailing my academic performance.",
    "The stress of my studies is manifesting in physical symptoms.",
    "I was hospitalised during my exams and now I'm way behind.",
    "I have ADHD and a chronic illness and I'm struggling academically.",
    "I'm burning out from studying and my body is breaking down.",
    "I can't sleep because of exam stress and my health is deteriorating.",
    "My mental health crisis is affecting my ability to study.",
    "I'm struggling academically because my physical health has collapsed.",
    "Exams ka stress hai aur tabiyat bhi theek nahi reh rahi.",
]

RELATION_FINANCE_POOL = [
    "My partner and I fight constantly about money and it's breaking us apart.",
    "We can't afford to have the life we want and it's creating resentment.",
    "My partner controls all the money in the relationship and I feel trapped.",
    "I'm going through a divorce and the financial situation is devastating.",
    "Financial stress is the main cause of conflict in my relationship.",
    "I feel ashamed of my financial situation in front of my partner.",
    "My partner and I have completely different relationships with money.",
    "I'm supporting my partner financially and I'm beginning to resent it.",
    "Financial difficulties after having a baby are straining my relationship.",
    "We can't afford to buy a house and it's causing constant tension.",
    "Paise ki wajah se partner ke saath bahut jhagde ho rahe hain.",
    "Ghar mein financial stress aur rishton mein khichaav ek saath chal raha hai.",
]

HEALTH_FINANCE_POOL = [
    "My medical bills are overwhelming and I don't know how to cope.",
    "I can't work because of my illness and I'm in serious financial trouble.",
    "I have a chronic condition and the treatment costs are destroying me financially.",
    "I'm afraid to get the medical help I need because I can't afford it.",
    "My health problems have cost me my job and my savings.",
    "I can't afford my medication and it's making my condition worse.",
    "I've been sick for months and the financial pressure is adding to my stress.",
    "I lost my job because of illness and now I'm struggling financially.",
    "Bimari ki wajah se job bhi gayi aur paise bhi nahi hain.",
    "Medical bills ka bojh bahut zyada ho gaya hai.",
]

POOLS = {
    "workplace_stress":    WORKPLACE_POOL,
    "relationship_issues": RELATIONSHIP_POOL,
    "academic_stress":     ACADEMIC_POOL,
    "health_concerns":     HEALTH_POOL,
    "financial_stress":    FINANCIAL_POOL,
}

PAIR_POOLS = {
    ("workplace_stress",    "relationship_issues"): WORK_RELATION_POOL,
    ("workplace_stress",    "financial_stress"):    WORK_FINANCE_POOL,
    ("academic_stress",     "relationship_issues"): ACAD_RELATION_POOL,
    ("academic_stress",     "health_concerns"):     ACAD_HEALTH_POOL,
    ("relationship_issues", "financial_stress"):    RELATION_FINANCE_POOL,
    ("health_concerns",     "financial_stress"):    HEALTH_FINANCE_POOL,
}

CONFIDENCE_POOLS = {
    "workplace_stress":    [0.88, 0.90, 0.92, 0.95, 0.97],
    "relationship_issues": [0.87, 0.90, 0.92, 0.95],
    "academic_stress":     [0.88, 0.90, 0.93, 0.95],
    "health_concerns":     [0.87, 0.90, 0.92, 0.95],
    "financial_stress":    [0.87, 0.90, 0.92, 0.95],
}


def generate_timestamp() -> str:
    base   = datetime(2024, 6, 1)
    offset = timedelta(seconds=random.randint(0, 60 * 60 * 24 * 300))
    return (base + offset).strftime("%Y-%m-%dT%H:%M:%SZ")


def sample_pool(pool, n):
    if len(pool) >= n:
        return random.sample(pool, n)
    result = pool.copy()
    while len(result) < n:
        result.append(random.choice(pool))
    random.shuffle(result)
    return result


def generate_dataset():
    rows    = []
    counter = 1

    # ── Single-label examples ──────────────────────────────────────────────
    for topic, target in SINGLE_LABEL_TARGETS.items():
        pool  = POOLS[topic]
        utts  = sample_pool(pool, target)
        for utt in utts:
            rows.append({
                "id":            f"topic_{counter:06d}",
                "utterance":     utt,
                "topics":        json.dumps([topic]),
                "primary_topic": topic,
                "confidence":    random.choice(CONFIDENCE_POOLS[topic]),
                "source":        "synthetic",
                "annotator_id":  f"ann_{random.randint(1, 5):03d}",
                "created_at":    generate_timestamp(),
            })
            counter += 1

    # ── Multi-label (2-topic) examples ─────────────────────────────────────
    for t1, t2, target in MULTI_LABEL_PAIRS:
        pair_key  = (t1, t2)
        pair_pool = PAIR_POOLS.get(pair_key) or PAIR_POOLS.get((t2, t1), [])
        utts      = sample_pool(pair_pool, target)
        for utt in utts:
            rows.append({
                "id":            f"topic_{counter:06d}",
                "utterance":     utt,
                "topics":        json.dumps([t1, t2]),
                "primary_topic": t1,
                "confidence":    random.choice([0.82, 0.85, 0.87, 0.90]),
                "source":        "synthetic",
                "annotator_id":  f"ann_{random.randint(1, 5):03d}",
                "created_at":    generate_timestamp(),
            })
            counter += 1

    random.shuffle(rows)
    for i, row in enumerate(rows, 1):
        row["id"] = f"topic_{i:06d}"

    return rows


def evaluate_distribution(rows):
    from collections import Counter, defaultdict

    total = len(rows)
    print(f"\nDataset: {total} total examples")

    # Primary topic distribution
    prim_counts = Counter(r["primary_topic"] for r in rows)
    print(f"\n{'Primary Topic':<24} {'Count':>6}  {'%':>6}")
    print("-" * 40)
    for topic in TOPICS:
        n   = prim_counts[topic]
        pct = 100 * n / total
        print(f"  {topic:<22} {n:>6}  {pct:>5.1f}%")

    # Multi-label count
    multi_count  = sum(1 for r in rows if len(json.loads(r["topics"])) > 1)
    single_count = total - multi_count
    print(f"\nSingle-label examples : {single_count} ({100*single_count/total:.1f}%)")
    print(f"Multi-label examples  : {multi_count}  ({100*multi_count/total:.1f}%)")

    # Label frequency (each class how many times it appears as a label)
    label_counts = defaultdict(int)
    for r in rows:
        for t in json.loads(r["topics"]):
            label_counts[t] += 1
    print(f"\nLabel frequency (including multi-label co-occurrence):")
    for topic in TOPICS:
        n   = label_counts[topic]
        pct = 100 * n / total
        print(f"  {topic:<24}: {n} ({pct:.1f}% of examples)")

    # Co-occurrence pairs
    pair_counts = Counter()
    for r in rows:
        ts = sorted(json.loads(r["topics"]))
        if len(ts) > 1:
            pair_counts[tuple(ts)] += 1
    print(f"\nTop co-occurrence pairs:")
    for pair, count in pair_counts.most_common(8):
        print(f"  {pair[0]} + {pair[1]}: {count}")


if __name__ == "__main__":
    print("SAATHI AI -- Topic Classifier Dataset Generator")
    print("=" * 50)

    rows = generate_dataset()
    evaluate_distribution(rows)

    fieldnames = ["id", "utterance", "topics", "primary_topic",
                  "confidence", "source", "annotator_id", "created_at"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {OUTPUT_FILE}")
    print("Next step: python scripts/prepare_data_splits.py")
