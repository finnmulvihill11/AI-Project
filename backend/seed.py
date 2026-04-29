"""
Seed script — run once to populate the database with company profiles,
rounds, roles, and sample questions. Safe to re-run (uses INSERT OR IGNORE).

Usage:
    cd backend
    source venv/bin/activate
    python seed.py
"""

import json
import uuid
from database import get_connection, init_db

# ---------------------------------------------------------------------------
# IDs — fixed so everything can reference each other
# ---------------------------------------------------------------------------
GOOGLE_ID     = "google"
AMAZON_ID     = "amazon"
JANESTREET_ID = "jane_street"

ROLE_SWE_ID   = "software_engineer"
ROLE_QR_ID    = "quant_researcher"
ROLE_DS_ID    = "data_scientist"


def seed():
    init_db()
    conn = get_connection()
    c = conn.cursor()

    # ---------------------------------------------------------------------------
    # Roles
    # ---------------------------------------------------------------------------
    roles = [
        {
            "id":            ROLE_SWE_ID,
            "name":          "Software Engineer",
            "level":         None,
            "similar_roles": json.dumps([ROLE_DS_ID]),
            "tags":          json.dumps(["engineering", "backend", "frontend", "algorithms"]),
        },
        {
            "id":            ROLE_QR_ID,
            "name":          "Quantitative Researcher",
            "level":         None,
            "similar_roles": json.dumps([ROLE_DS_ID]),
            "tags":          json.dumps(["quant", "math", "probability", "trading"]),
        },
        {
            "id":            ROLE_DS_ID,
            "name":          "Data Scientist",
            "level":         None,
            "similar_roles": json.dumps([ROLE_SWE_ID, ROLE_QR_ID]),
            "tags":          json.dumps(["data", "ml", "statistics", "engineering"]),
        },
    ]

    for r in roles:
        c.execute("""
            INSERT OR IGNORE INTO roles (id, name, level, similar_roles, tags)
            VALUES (:id, :name, :level, :similar_roles, :tags)
        """, r)

    # ---------------------------------------------------------------------------
    # Companies
    # ---------------------------------------------------------------------------
    companies = [
        {
            "id":   GOOGLE_ID,
            "name": "Google",
            "interviewer_persona": (
                "Structured and neutral. Maintains a professional distance — does not indicate "
                "whether answers are correct or incorrect. Monitors candidate progress carefully "
                "and intervenes with hints once a wrong path is clearly visible, typically after "
                "2-3 minutes of unproductive work. Documents every hint given in the formal rubric."
            ),
            "hint_frequency":               "medium",
            "hint_style":                   json.dumps(["constraint_narrowing", "test_case_introduction", "single_word_prompt"]),
            "signals_wrong_answer_via":     json.dumps(["introduce_failing_test_case", "narrow_constraint", "structural_question"]),
            "says_answer_is_wrong_directly":0,
            "modifies_problem_mid_interview":0,
            "question_style":               "well_defined",
            "wrong_answer_response":        "Introduce a test case that breaks the current approach. Or narrow a constraint: 'Can you do this in constant space?'",
            "move_on_threshold":            "medium — hints exhausted, then move on",
            "known_focus_areas":            json.dumps(["data structures", "algorithms", "complexity analysis", "system design", "distributed systems"]),
            "interview_style_tags":         json.dumps(["algorithm_heavy", "system_design"]),
            "similar_companies":            json.dumps([AMAZON_ID]),
            "coding_in_standard_rounds":    1,
        },
        {
            "id":   AMAZON_ID,
            "name": "Amazon",
            "interviewer_persona": (
                "Direct and structured. Combines LeetCode-style technical questions with heavy "
                "behavioral emphasis on Leadership Principles. Gives hints reactively — only when "
                "candidate is visibly stuck. May introduce a new sample test case rather than verbal "
                "correction to signal an issue."
            ),
            "hint_frequency":               "medium_low",
            "hint_style":                   json.dumps(["test_case_introduction", "approach_redirect", "reframing"]),
            "signals_wrong_answer_via":     json.dumps(["introduce_failing_test_case", "reframe_approach"]),
            "says_answer_is_wrong_directly":0,
            "modifies_problem_mid_interview":0,
            "question_style":               "well_defined",
            "wrong_answer_response":        "Introduce a new sample test case that the candidate's solution fails. Or redirect: 'Think about it in terms of a sliding window.'",
            "move_on_threshold":            "medium — will pivot to a different question probing the same skill if stuck",
            "known_focus_areas":            json.dumps(["leadership principles", "data structures", "algorithms", "system design", "object-oriented design"]),
            "interview_style_tags":         json.dumps(["algorithm_heavy", "behavioral", "system_design"]),
            "similar_companies":            json.dumps([GOOGLE_ID]),
            "coding_in_standard_rounds":    1,
        },
        {
            "id":   JANESTREET_ID,
            "name": "Jane Street",
            "interviewer_persona": (
                "Collaborative and conversational. Treats the interview as a joint problem-solving "
                "session rather than a test. Gives hints freely and does not penalize for needing "
                "them. May modify the problem mid-interview by changing numbers or rules to test "
                "adaptability. Questions are deliberately underspecified — candidate is expected to "
                "identify missing information and ask about it."
            ),
            "hint_frequency":               "high",
            "hint_style":                   json.dumps(["conversational_nudge", "problem_modification", "rule_change"]),
            "signals_wrong_answer_via":     json.dumps(["modify_problem_variant", "follow_up_probe", "change_constraints"]),
            "says_answer_is_wrong_directly":0,
            "modifies_problem_mid_interview":1,
            "question_style":               "underspecified",
            "wrong_answer_response":        "Change a number or rule in the problem to force reconsideration. Ask why the candidate made a particular assumption.",
            "move_on_threshold":            "late — exhaust all probes before moving on",
            "known_focus_areas":            json.dumps(["probability", "expected value", "OCaml", "functional programming", "market-making", "mental math"]),
            "interview_style_tags":         json.dumps(["quant", "probability", "trading", "functional_programming"]),
            "similar_companies":            json.dumps([]),
            "coding_in_standard_rounds":    0,
        },
    ]

    for co in companies:
        c.execute("""
            INSERT OR IGNORE INTO companies (
                id, name, interviewer_persona, hint_frequency, hint_style,
                signals_wrong_answer_via, says_answer_is_wrong_directly,
                modifies_problem_mid_interview, question_style, wrong_answer_response,
                move_on_threshold, known_focus_areas, interview_style_tags,
                similar_companies, coding_in_standard_rounds
            ) VALUES (
                :id, :name, :interviewer_persona, :hint_frequency, :hint_style,
                :signals_wrong_answer_via, :says_answer_is_wrong_directly,
                :modifies_problem_mid_interview, :question_style, :wrong_answer_response,
                :move_on_threshold, :known_focus_areas, :interview_style_tags,
                :similar_companies, :coding_in_standard_rounds
            )
        """, co)

    # ---------------------------------------------------------------------------
    # Company Rounds
    # ---------------------------------------------------------------------------
    rounds = [
        # Google
        {
            "id": str(uuid.uuid4()), "company_id": GOOGLE_ID,
            "round_name": "phone_screen", "duration_minutes": 45,
            "question_count_range": json.dumps([1, 2]),
            "focus": "One coding problem, data structures",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.3, "coding": 0.7, "system_design": 0.0, "behavioral": 0.0}),
        },
        {
            "id": str(uuid.uuid4()), "company_id": GOOGLE_ID,
            "round_name": "onsite_coding", "duration_minutes": 45,
            "question_count_range": json.dumps([2, 3]),
            "focus": "Two coding problems, complexity analysis",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.2, "coding": 0.8, "system_design": 0.0, "behavioral": 0.0}),
        },
        {
            "id": str(uuid.uuid4()), "company_id": GOOGLE_ID,
            "round_name": "onsite_system_design", "duration_minutes": 45,
            "question_count_range": json.dumps([1, 2]),
            "focus": "Large-scale system design",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.1, "coding": 0.0, "system_design": 0.9, "behavioral": 0.0}),
        },
        # Amazon
        {
            "id": str(uuid.uuid4()), "company_id": AMAZON_ID,
            "round_name": "phone_screen", "duration_minutes": 1,
            "question_count_range": json.dumps([1, 1]),  # exactly 1 question for testing
            "focus": "One coding problem + one behavioral (Leadership Principles)",
            "is_technical_only": 0,
            "category_weights": json.dumps({"technical": 0.2, "coding": 0.5, "system_design": 0.0, "behavioral": 0.3}),
        },
        {
            "id": str(uuid.uuid4()), "company_id": AMAZON_ID,
            "round_name": "loop_technical", "duration_minutes": 60,
            "question_count_range": json.dumps([2, 3]),
            "focus": "Coding and system design",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.2, "coding": 0.5, "system_design": 0.3, "behavioral": 0.0}),
        },
        # Jane Street
        {
            "id": str(uuid.uuid4()), "company_id": JANESTREET_ID,
            "round_name": "first_round", "duration_minutes": 60,
            "question_count_range": json.dumps([3, 5]),
            "focus": "Math, probability, logic puzzles, market-making",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.9, "coding": 0.0, "system_design": 0.1, "behavioral": 0.0}),
        },
        {
            "id": str(uuid.uuid4()), "company_id": JANESTREET_ID,
            "round_name": "superday", "duration_minutes": 45,
            "question_count_range": json.dumps([2, 4]),
            "focus": "Technical depth, adaptability, trading intuition",
            "is_technical_only": 1,
            "category_weights": json.dumps({"technical": 0.9, "coding": 0.0, "system_design": 0.1, "behavioral": 0.0}),
        },
    ]

    for r in rounds:
        c.execute("""
            INSERT OR IGNORE INTO company_rounds (
                id, company_id, round_name, duration_minutes,
                question_count_range, focus, is_technical_only, category_weights
            ) VALUES (
                :id, :company_id, :round_name, :duration_minutes,
                :question_count_range, :focus, :is_technical_only, :category_weights
            )
        """, r)

    # ---------------------------------------------------------------------------
    # Questions (hardcoded for MVP testing — replace with Finn's pipeline later)
    # ---------------------------------------------------------------------------
    questions = [

        # --- Google — coding ---
        {
            "id": "q_google_lru_cache",
            "question_text": "Design and implement an LRU (Least Recently Used) cache that supports get and put operations in O(1) time.",
            "answer_text": "Use a hashmap + doubly linked list. The hashmap gives O(1) access; the linked list tracks recency. On get, move node to head. On put, insert at head and evict tail if over capacity.",
            "company_id": GOOGLE_ID,
            "role_id": ROLE_SWE_ID,
            "round": "phone_screen",
            "category": "coding",
            "quality_score": 0.95,
            "difficulty_score": 0.65,
            "tags": json.dumps(["linked_list", "hashmap", "design", "O(1)"]),
            "briefing": json.dumps({
                "question": "Design and implement an LRU cache that supports get and put in O(1) time.",
                "category": "coding",
                "triggers_coding_tab": True,
                "ideal_answer_summary": "Combines a hashmap for O(1) lookup with a doubly linked list for O(1) eviction. Head = most recent, tail = LRU. On get, move node to head. On put, insert at head; if over capacity evict tail and remove from map.",
                "key_concepts": ["doubly linked list", "hashmap", "O(1) get and put", "eviction policy"],
                "common_wrong_paths": [
                    {
                        "path": "Using an array or single list with linear scan",
                        "signal": "Candidate mentions iterating through elements to find least recently used",
                        "response": "What's the time complexity of finding the LRU element that way?"
                    },
                    {
                        "path": "Using OrderedDict without understanding internals",
                        "signal": "Candidate jumps to Python OrderedDict without explaining why",
                        "response": "Can you walk me through what OrderedDict is doing under the hood?"
                    }
                ],
                "good_signals": [
                    "Immediately identifies hashmap + linked list combo",
                    "Draws out the data structure before coding",
                    "Handles edge cases: capacity=1, duplicate put, get on missing key"
                ],
                "hint_if_stuck": "Think about two data structures that together give you both fast lookup and fast ordering updates."
            }),
            "is_active": 1,
        },
        {
            "id": "q_google_two_sum",
            "question_text": "Given an array of integers and a target sum, return the indices of the two numbers that add up to the target. Assume exactly one solution exists.",
            "answer_text": "Single-pass hashmap: for each element, check if complement (target - num) is in the map. If yes, return both indices. If no, store current value → index. O(n) time, O(n) space.",
            "company_id": GOOGLE_ID,
            "role_id": ROLE_SWE_ID,
            "round": "phone_screen",
            "category": "coding",
            "quality_score": 0.80,
            "difficulty_score": 0.25,
            "tags": json.dumps(["hashmap", "array", "complement"]),
            "briefing": json.dumps({
                "question": "Given an array and a target, return indices of two numbers that add to target.",
                "category": "coding",
                "triggers_coding_tab": True,
                "ideal_answer_summary": "Single-pass hashmap storing value-to-index. For each number, check if complement exists in map before inserting. O(n) time and space. Strong candidates handle edge cases and explain why brute force is O(n²).",
                "key_concepts": ["hashmap", "complement lookup", "O(n) vs O(n²)"],
                "common_wrong_paths": [
                    {
                        "path": "Nested loop brute force O(n²)",
                        "signal": "Candidate writes two for loops",
                        "response": "That works — can you do it in linear time?"
                    }
                ],
                "good_signals": [
                    "Starts with brute force and explicitly improves it",
                    "Explains the complement insight clearly",
                    "Asks about duplicates or negative numbers"
                ],
                "hint_if_stuck": "For each number, what value are you looking for? Can you store something that lets you check that in O(1)?"
            }),
            "is_active": 1,
        },
        {
            "id": "q_google_merge_intervals",
            "question_text": "Given an array of intervals, merge all overlapping intervals and return the result.",
            "answer_text": "Sort intervals by start time. Iterate: if current interval overlaps with last merged (current.start <= last.end), extend last.end = max(last.end, current.end). Otherwise append. O(n log n).",
            "company_id": GOOGLE_ID,
            "role_id": ROLE_SWE_ID,
            "round": "onsite_coding",
            "category": "coding",
            "quality_score": 0.88,
            "difficulty_score": 0.45,
            "tags": json.dumps(["sorting", "intervals", "greedy"]),
            "briefing": json.dumps({
                "question": "Given an array of intervals, merge all overlapping intervals.",
                "category": "coding",
                "triggers_coding_tab": True,
                "ideal_answer_summary": "Sort by start time, then single pass merging. Key insight: after sorting, only need to compare current interval with the last merged one. Handle the max() on end times to cover containment cases.",
                "key_concepts": ["sorting", "greedy merge", "interval containment"],
                "common_wrong_paths": [
                    {
                        "path": "Not sorting first and trying to compare all pairs",
                        "signal": "Candidate mentions O(n²) pairwise comparison",
                        "response": "Is there a way to simplify which intervals you need to compare?"
                    },
                    {
                        "path": "Forgetting the containment case (e.g. [1,10] and [2,3])",
                        "signal": "Candidate sets end = current.end instead of max",
                        "response": "What if one interval completely contains another?"
                    }
                ],
                "good_signals": [
                    "Immediately recognizes sorting as the key step",
                    "Uses max() for end boundary",
                    "Tests with [[1,3],[2,6],[8,10],[15,18]] mentally"
                ],
                "hint_if_stuck": "If the intervals were sorted by start time, which ones could possibly overlap with a given interval?"
            }),
            "is_active": 1,
        },

        # --- Google — system design ---
        {
            "id": "q_google_design_url_shortener",
            "question_text": "Design a URL shortening service like bit.ly. Walk me through your architecture.",
            "answer_text": "Key components: hash generation (base62 encode a counter or hash), storage (key-value store like DynamoDB or Redis for fast lookup), redirect service (301 vs 302 tradeoffs), analytics tracking. Handle collisions, scale to ~100M URLs.",
            "company_id": GOOGLE_ID,
            "role_id": ROLE_SWE_ID,
            "round": "onsite_system_design",
            "category": "system_design",
            "quality_score": 0.90,
            "difficulty_score": 0.55,
            "tags": json.dumps(["system_design", "hashing", "key-value", "scalability"]),
            "briefing": json.dumps({
                "question": "Design a URL shortening service like bit.ly.",
                "category": "system_design",
                "triggers_coding_tab": False,
                "ideal_answer_summary": "Strong answer covers: requirements clarification (read-heavy, scale, analytics?), short code generation (base62 counter vs hashing, collision handling), storage layer (key-value store), redirect logic (301 vs 302 for caching tradeoffs), and CDN/cache for hot URLs.",
                "key_concepts": ["base62 encoding", "key-value store", "301 vs 302 redirect", "consistent hashing", "CDN caching"],
                "common_wrong_paths": [
                    {
                        "path": "Using a relational DB as primary store without caching",
                        "signal": "Candidate proposes MySQL with no cache layer",
                        "response": "This is read-heavy — how does this scale to millions of redirects per second?"
                    },
                    {
                        "path": "MD5 hash without handling collisions",
                        "signal": "Candidate hashes URL and truncates without collision strategy",
                        "response": "What happens if two different URLs hash to the same short code?"
                    }
                ],
                "good_signals": [
                    "Asks clarifying questions before designing",
                    "Calls out 301 vs 302 tradeoff explicitly",
                    "Mentions analytics as a separate async write path"
                ],
                "hint_if_stuck": "Start with the core operation: given a long URL, how do you generate a short unique code and store the mapping?"
            }),
            "is_active": 1,
        },

        # --- Amazon — coding ---
        {
            "id": "q_amazon_valid_parentheses",
            "question_text": "Given a string of brackets — '(', ')', '{', '}', '[', ']' — determine if it is valid. A string is valid if every open bracket is closed in the correct order.",
            "answer_text": "Use a stack. Push open brackets. On close bracket, check if stack top matches. If mismatch or stack empty, return False. At end, return True only if stack is empty. O(n) time and space.",
            "company_id": AMAZON_ID,
            "role_id": ROLE_SWE_ID,
            "round": "phone_screen",
            "category": "coding",
            "quality_score": 0.82,
            "difficulty_score": 0.20,
            "tags": json.dumps(["stack", "string", "matching"]),
            "briefing": json.dumps({
                "question": "Determine if a string of brackets is valid.",
                "category": "coding",
                "triggers_coding_tab": True,
                "ideal_answer_summary": "Stack-based solution: push on open, pop and verify on close. Strong candidates handle all three bracket types, empty stack edge case on close, and non-empty stack at end.",
                "key_concepts": ["stack LIFO", "bracket matching", "edge cases"],
                "common_wrong_paths": [
                    {
                        "path": "Counting opens and closes without tracking order",
                        "signal": "Candidate counts '(' and ')' separately",
                        "response": "Does '([)]' pass your check? Should it?"
                    }
                ],
                "good_signals": [
                    "Immediately reaches for stack",
                    "Uses a hashmap for bracket pairs",
                    "Tests ')(' and '([)]' edge cases unprompted"
                ],
                "hint_if_stuck": "What data structure gives you access to the most recently seen open bracket?"
            }),
            "is_active": 1,
        },
        {
            "id": "q_amazon_behavioral_conflict",
            "question_text": "Tell me about a time you had a conflict with a teammate. How did you handle it?",
            "answer_text": "STAR format. Strong answers show: proactive communication, addressing the issue directly (not around it), focusing on the problem not the person, reaching a resolution, and reflecting on what you'd do differently.",
            "company_id": AMAZON_ID,
            "role_id": ROLE_SWE_ID,
            "round": "phone_screen",
            "category": "behavioral",
            "quality_score": 0.85,
            "difficulty_score": 0.40,
            "tags": json.dumps(["behavioral", "leadership_principles", "earn_trust", "conflict"]),
            "briefing": json.dumps({
                "question": "Tell me about a time you had a conflict with a teammate.",
                "category": "behavioral",
                "triggers_coding_tab": False,
                "ideal_answer_summary": "Maps to 'Earn Trust' LP. Strong answer: specific conflict (not vague), candidate addresses it directly rather than escalating immediately, outcome is constructive for both parties, reflection shows growth.",
                "key_concepts": ["Earn Trust LP", "STAR format", "direct communication", "ownership"],
                "common_wrong_paths": [
                    {
                        "path": "Vague answer with no specific situation",
                        "signal": "Candidate says 'we had a disagreement' without details",
                        "response": "Can you give me a specific example — what was the actual disagreement about?"
                    },
                    {
                        "path": "Candidate blames the other person entirely",
                        "signal": "No acknowledgment of own role in the conflict",
                        "response": "What would you do differently on your end if this happened again?"
                    }
                ],
                "good_signals": [
                    "Has a concrete, specific situation ready",
                    "Shows they addressed it directly and early",
                    "Outcome improved the working relationship"
                ],
                "hint_if_stuck": "Walk me through a specific situation — who was involved, what was the disagreement about?"
            }),
            "is_active": 1,
        },
        {
            "id": "q_amazon_product_of_array",
            "question_text": "Given an integer array, return an array where each element is the product of all other elements. You may not use division.",
            "answer_text": "Two-pass prefix/suffix product. First pass: left[i] = product of all elements to the left. Second pass: multiply in right products from the right. O(n) time, O(1) extra space (output array doesn't count).",
            "company_id": AMAZON_ID,
            "role_id": ROLE_SWE_ID,
            "round": "loop_technical",
            "category": "coding",
            "quality_score": 0.87,
            "difficulty_score": 0.55,
            "tags": json.dumps(["array", "prefix_product", "no_division"]),
            "briefing": json.dumps({
                "question": "Return product of all other elements without division.",
                "category": "coding",
                "triggers_coding_tab": True,
                "ideal_answer_summary": "Prefix product left pass then suffix product right pass. Key insight: output[i] = (product of all left of i) × (product of all right of i). Can be done in O(1) extra space by using the output array for left pass then a running right variable.",
                "key_concepts": ["prefix product", "suffix product", "O(1) space optimization"],
                "common_wrong_paths": [
                    {
                        "path": "Total product divided by element (uses division)",
                        "signal": "Candidate mentions dividing total product",
                        "response": "The problem says no division — can you solve it without that?"
                    },
                    {
                        "path": "Two separate arrays for left and right products",
                        "signal": "Candidate allocates left[] and right[] both at O(n)",
                        "response": "Can you reduce the extra space to O(1)?"
                    }
                ],
                "good_signals": [
                    "Correctly identifies prefix × suffix structure",
                    "Optimizes to O(1) space with running variable",
                    "Handles zeros in the array"
                ],
                "hint_if_stuck": "For each position, can you separately compute the product of everything to its left and everything to its right?"
            }),
            "is_active": 1,
        },

        # --- Jane Street — technical/probability ---
        {
            "id": "q_js_fair_coin_unfair",
            "question_text": "You have a biased coin that comes up heads with probability p (unknown). How do you use it to simulate a fair coin flip?",
            "answer_text": "Von Neumann trick: flip twice. HT → heads, TH → tails, HH/TT → repeat. P(HT) = p(1-p) = P(TH), so the two outcomes are equally likely. Expected flips = 2/[2p(1-p)].",
            "company_id": JANESTREET_ID,
            "role_id": ROLE_QR_ID,
            "round": "first_round",
            "category": "technical",
            "quality_score": 0.92,
            "difficulty_score": 0.50,
            "tags": json.dumps(["probability", "coin", "symmetry", "expected_value"]),
            "briefing": json.dumps({
                "question": "Use a biased coin with unknown probability p to simulate a fair coin flip.",
                "category": "technical",
                "triggers_coding_tab": False,
                "ideal_answer_summary": "Von Neumann extractor: flip two coins, map HT→H and TH→T, discard HH and TT and repeat. Correctness follows from P(HT) = P(TH) = p(1-p). Strong candidates also compute expected number of flips needed.",
                "key_concepts": ["Von Neumann extractor", "symmetry argument", "expected value", "geometric series"],
                "common_wrong_paths": [
                    {
                        "path": "Trying to compute p first then adjust",
                        "signal": "Candidate asks how to estimate p",
                        "response": "What if you couldn't estimate p at all — could you still do it?"
                    },
                    {
                        "path": "Flipping once and mapping by threshold",
                        "signal": "Candidate says 'flip and call heads if < 0.5'",
                        "response": "How would you know the threshold without knowing p?"
                    }
                ],
                "good_signals": [
                    "Immediately goes to pairs of flips",
                    "Correctly argues P(HT) = P(TH) without needing to know p",
                    "Computes expected number of flip pairs needed"
                ],
                "hint_if_stuck": "What if you flipped the coin twice? Are any pair of outcomes guaranteed to be equally likely regardless of p?"
            }),
            "is_active": 1,
        },
        {
            "id": "q_js_expected_dice",
            "question_text": "You roll a fair six-sided die repeatedly until you roll a 6. What is the expected number of rolls?",
            "answer_text": "Geometric distribution with p=1/6. E[rolls] = 1/p = 6. Can also derive via E = 1 + (5/6)E, solve to get E=6.",
            "company_id": JANESTREET_ID,
            "role_id": ROLE_QR_ID,
            "round": "first_round",
            "category": "technical",
            "quality_score": 0.88,
            "difficulty_score": 0.30,
            "tags": json.dumps(["probability", "expected_value", "geometric_distribution"]),
            "briefing": json.dumps({
                "question": "Roll a fair die until you get a 6. Expected number of rolls?",
                "category": "technical",
                "triggers_coding_tab": False,
                "ideal_answer_summary": "Answer is 6 (geometric distribution, E=1/p). Strong candidates either cite geometric distribution directly OR derive via the recursion E = 1 + (5/6)E. Excellent candidates verify with the recursion and then generalize to arbitrary p.",
                "key_concepts": ["geometric distribution", "expected value", "recursive expectation"],
                "common_wrong_paths": [
                    {
                        "path": "Saying 3 or 3.5 (confusing with median or midpoint)",
                        "signal": "Candidate says 'around 3 since there are 6 sides'",
                        "response": "Walk me through how you got to 3 — can you set up the calculation formally?"
                    }
                ],
                "good_signals": [
                    "States geometric distribution formula immediately",
                    "Derives via recursion E = 1 + (5/6)E",
                    "Generalizes: what if you needed to roll a 6 twice?"
                ],
                "hint_if_stuck": "Let E be the expected number of rolls. After the first roll, what are the two possible situations you're in?"
            }),
            "is_active": 1,
        },
        {
            "id": "q_js_market_making",
            "question_text": "I want to buy or sell a stock. Make me a market. The stock's true value is somewhere between 0 and 100 — you don't know where.",
            "answer_text": "Quote a wide spread initially (e.g. 40-60) representing max uncertainty. Narrow based on any information revealed. Key concepts: spread = uncertainty, midpoint = expected value estimate, manage inventory risk if they trade on one side repeatedly.",
            "company_id": JANESTREET_ID,
            "role_id": ROLE_QR_ID,
            "round": "superday",
            "category": "technical",
            "quality_score": 0.95,
            "difficulty_score": 0.75,
            "tags": json.dumps(["market_making", "trading", "probability", "expected_value", "spread"]),
            "briefing": json.dumps({
                "question": "Make a market on a stock with unknown value between 0 and 100.",
                "category": "technical",
                "triggers_coding_tab": False,
                "ideal_answer_summary": "Start with wide spread (e.g. 40-60) reflecting uniform prior. Midpoint = 50 = E[value]. Narrow spread as information arrives. Strong candidates discuss: what widening spread means (more uncertainty), inventory risk if client keeps hitting one side, and updating beliefs via Bayesian reasoning when trades occur.",
                "key_concepts": ["bid-ask spread", "expected value as midpoint", "inventory risk", "information asymmetry", "Bayesian updating"],
                "common_wrong_paths": [
                    {
                        "path": "Quoting a very tight spread immediately",
                        "signal": "Candidate says '49-51' without justification",
                        "response": "You don't know the true value at all — why is your spread so tight?"
                    },
                    {
                        "path": "Refusing to quote without more information",
                        "signal": "Candidate asks many questions before quoting",
                        "response": "You have to make a market now — what's your quote?"
                    }
                ],
                "good_signals": [
                    "Immediately quotes a wide spread and justifies it",
                    "Updates spread when interviewer trades or reveals info",
                    "Mentions inventory risk if they keep buying one side"
                ],
                "hint_if_stuck": "If you knew nothing about the true value, what would your best guess for the midpoint be? And how wide would your spread need to be to protect yourself?"
            }),
            "is_active": 1,
        },
    ]

    for q in questions:
        c.execute("""
            INSERT OR IGNORE INTO questions (
                id, question_text, answer_text, company_id, role_id,
                round, category, quality_score, difficulty_score,
                tags, briefing, is_active
            ) VALUES (
                :id, :question_text, :answer_text, :company_id, :role_id,
                :round, :category, :quality_score, :difficulty_score,
                :tags, :briefing, :is_active
            )
        """, q)

    conn.commit()
    conn.close()
    print(f"Seeded: 3 companies, 7 rounds, 3 roles, {len(questions)} questions.")


if __name__ == "__main__":
    seed()
