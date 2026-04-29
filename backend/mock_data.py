"""
Mock data for MVP — used when the database has no seeded companies or questions.

All sessions use these hard-coded questions regardless of which company/role
the user selected. The company profile is stubbed generically so the interviewer
persona still feels real even without real company data.

TODO (Finn + Matthew): Replace this with real DB data once the enrichment
pipeline is running. Steps to switch:
  1. Seed companies table with real company rows (see database.py schema)
  2. Seed questions table with enriched questions + briefings
  3. Remove the MOCK_* usage from main.py and let the DB endpoints take over
  4. Delete this file
"""

import json

# ── Companies ─────────────────────────────────────────────────────────────────
# Shown in Finn's company selector dropdown.
# TODO: replace with SELECT id, name, interview_style_tags, known_focus_areas FROM companies

MOCK_COMPANIES = [
    {
        "id": "google",
        "name": "Google",
        "interview_style_tags": json.dumps(["algorithmic", "system design", "behavioral"]),
        "known_focus_areas": json.dumps(["data structures", "scalability", "coding"]),
    },
    {
        "id": "meta",
        "name": "Meta",
        "interview_style_tags": json.dumps(["coding", "system design", "product sense"]),
        "known_focus_areas": json.dumps(["graph problems", "dynamic programming", "coding"]),
    },
    {
        "id": "amazon",
        "name": "Amazon",
        "interview_style_tags": json.dumps(["leadership principles", "coding", "system design"]),
        "known_focus_areas": json.dumps(["behavioral", "scalable systems", "coding"]),
    },
    {
        "id": "jane_street",
        "name": "Jane Street",
        "interview_style_tags": json.dumps(["probability", "functional programming", "quantitative"]),
        "known_focus_areas": json.dumps(["OCaml", "probability", "logic puzzles"]),
    },
]

# ── Rounds ────────────────────────────────────────────────────────────────────
# TODO: replace with SELECT * FROM company_rounds WHERE company_id = ?

MOCK_ROUNDS = [
    {"id": "phone_screen",       "company_id": None, "round_name": "phone_screen",       "duration_minutes": 45, "focus": "Coding"},
    {"id": "onsite_technical",   "company_id": None, "round_name": "onsite_technical",   "duration_minutes": 60, "focus": "Coding + System Design"},
]

# ── Roles ─────────────────────────────────────────────────────────────────────
# TODO: replace with SELECT DISTINCT roles.* FROM roles JOIN questions ... WHERE company_id = ?

MOCK_ROLES = [
    {"id": "swe_new_grad",  "name": "Software Engineer (New Grad)", "level": "entry"},
    {"id": "swe_mid",       "name": "Software Engineer",            "level": "mid"},
    {"id": "swe_senior",    "name": "Senior Software Engineer",     "level": "senior"},
]

# ── Company profiles ──────────────────────────────────────────────────────────
# Full profile used by build_system_prompt. The real version comes from the
# companies table. This stub makes all companies use a neutral interviewer
# persona until real profiles are seeded.
# TODO: replace with SELECT * FROM companies WHERE id = ?

def get_mock_company_profile(company_id: str) -> dict:
    """Return a generic interviewer profile for any company ID."""
    name_map = {c["id"]: c["name"] for c in MOCK_COMPANIES}
    name = name_map.get(company_id, "the company")

    # TODO: once companies table has real rows, load from DB and return dict(row)
    return {
        "id":                           company_id,
        "name":                         name,
        "interviewer_persona":          (
            f"You are a professional {name} interviewer. "
            "You are direct, calm, and technical. You ask follow-up questions rather "
            "than volunteering information. You maintain a neutral tone throughout — "
            "you neither encourage nor discourage the candidate."
        ),
        "hint_frequency":               "low",
        "hint_style":                   json.dumps(["Socratic questions"]),
        "wrong_answer_response":        "probe with a clarifying question",
        "move_on_threshold":            "medium",
        "signals_wrong_answer_via":     json.dumps(["follow-up probing questions", "silence"]),
        "modifies_problem_mid_interview": False,
        "question_style":               "well_defined",
    }

# ── Questions ─────────────────────────────────────────────────────────────────
# Hard-coded questions with full Domain Expert briefings.
# These are returned for every session regardless of company/role selected.
# TODO: replace with select_questions(company_id, role_id, round) once DB is seeded

MOCK_QUESTIONS = [
    {
        "id": "mock_lru_cache",
        "question_text": "Design and implement an LRU cache that supports get and put operations in O(1) time.",
        "category": "coding",
        "briefing": json.dumps({
            "question": (
                "Design an LRU cache with a fixed capacity. "
                "It should support two operations: get(key), which returns the value if the key exists "
                "and -1 otherwise, and put(key, value), which inserts or updates a key-value pair. "
                "When the cache reaches capacity, it should evict the least recently used item. "
                "Both operations must run in O(1) time."
            ),
            "ideal_answer_summary": (
                "A hash map for O(1) key lookup combined with a doubly linked list for O(1) "
                "insertion and removal. The head of the list is the most recently used item; "
                "the tail is the least recently used. On get: move the node to the head. "
                "On put: insert at head, evict tail if over capacity. Sentinel head/tail nodes "
                "simplify edge cases."
            ),
            "key_concepts": [
                "hash map + doubly linked list",
                "O(1) get and put",
                "eviction policy at tail",
                "sentinel/dummy head and tail nodes",
                "updating on get, not just on put",
            ],
            "common_wrong_paths": [
                {
                    "path": "Using an array or singly linked list",
                    "signal": "Mentions O(n) removal or linear scan",
                    "response": "What's the time complexity of removing a node from the middle of that structure?"
                },
                {
                    "path": "Forgetting to update recency on get (only on put)",
                    "signal": "Describes put correctly but omits moving node on get",
                    "response": "What should happen to a key's position when it's read, not just written?"
                },
            ],
            "good_signals": [
                "Immediately identifies hash map + doubly linked list",
                "Mentions sentinel nodes to avoid null checks",
                "Correctly handles the case where key already exists on put",
                "Considers capacity-zero edge case",
            ],
            "hint_if_stuck": "What data structure gives you O(1) lookup by key, and what gives you O(1) removal from an arbitrary position?",
            "category": "coding",
        }),
    },
    {
        "id": "mock_two_sum",
        "question_text": "Given an array of integers and a target sum, return the indices of the two numbers that add up to the target. You may assume exactly one solution exists.",
        "category": "coding",
        "briefing": json.dumps({
            "question": (
                "Given an array of integers called nums and an integer target, return the indices "
                "of the two numbers such that they add up to target. You may assume that each input "
                "has exactly one solution, and you may not use the same element twice."
            ),
            "ideal_answer_summary": (
                "Single pass with a hash map. For each element, check if target minus the current "
                "value exists in the map. If yes, return the stored index and current index. "
                "If no, store the current value and its index. O(n) time, O(n) space."
            ),
            "key_concepts": [
                "hash map for complement lookup",
                "O(n) single pass",
                "complement = target - current value",
                "storing index not just value",
            ],
            "common_wrong_paths": [
                {
                    "path": "Brute force O(n²) nested loops",
                    "signal": "Describes checking all pairs",
                    "response": "Can you get this below O(n squared)?"
                },
                {
                    "path": "Sorting first — loses original indices",
                    "signal": "Mentions sorting",
                    "response": "If you sort the array, what happens to the original indices you need to return?"
                },
            ],
            "good_signals": [
                "Immediately identifies hash map approach",
                "Stores the index, not just the value, in the map",
                "Recognizes single pass is possible",
                "Handles duplicate values correctly",
            ],
            "hint_if_stuck": "If you know the current number, what value are you looking for, and how could you check for it in constant time?",
            "category": "coding",
        }),
    },
    {
        "id": "mock_valid_parens",
        "question_text": "Given a string containing only the characters '(', ')', '{', '}', '[', and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type of brackets and in the correct order.",
        "category": "coding",
        "briefing": json.dumps({
            "question": (
                "Given a string containing only parentheses, curly braces, and square brackets, "
                "determine if it is valid. Valid means every opening bracket is closed by the "
                "corresponding closing bracket in the correct order, and no unmatched brackets remain."
            ),
            "ideal_answer_summary": (
                "Stack-based approach. Push opening brackets onto the stack. When a closing bracket "
                "is encountered, check that the top of the stack is the matching opener — if not, "
                "return false. After processing all characters, the stack must be empty."
            ),
            "key_concepts": [
                "stack for tracking unmatched openers",
                "matching closing bracket pops the stack",
                "stack must be empty at the end",
                "early return on mismatch",
            ],
            "common_wrong_paths": [
                {
                    "path": "Counting opens and closes without tracking order",
                    "signal": "Mentions just counting brackets",
                    "response": "Would that handle a string like '](' correctly?"
                },
                {
                    "path": "Not handling the empty stack case on closing bracket",
                    "signal": "Forgets to check if stack is empty before popping",
                    "response": "What happens if the very first character is a closing bracket?"
                },
            ],
            "good_signals": [
                "Immediately identifies stack",
                "Uses a hash map or explicit matching for bracket pairs",
                "Checks for empty stack at the end",
                "Handles edge case of empty string or single character",
            ],
            "hint_if_stuck": "If you're processing left to right, what do you need to remember about the opening brackets you've seen so far?",
            "category": "coding",
        }),
    },
]


def get_mock_questions(n: int = 2) -> list[dict]:
    """
    Return n questions for a session.
    TODO: replace with select_questions(company_id, role_id, round) once DB is seeded.
    Currently returns the first n mock questions regardless of company/role.
    """
    import random
    questions = list(MOCK_QUESTIONS)
    random.shuffle(questions)
    return questions[:min(n, len(questions))]
