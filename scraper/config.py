import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Database ---
STAGING_DB = "scraper/db/staging.db"
QUESTIONS_DB = "scraper/db/questions.db"

# --- Deduplication ---
SIMILARITY_THRESHOLD = 0.85      # cosine similarity — questions above this are linked as variants
BORDERLINE_LOWER = 0.80          # similarity range flagged for manual review in validation
BORDERLINE_UPPER = SIMILARITY_THRESHOLD

# --- Scraping ---
MAX_REPOS_PER_SOURCE = 100       # safety cap on repos crawled per source search
GITHUB_MIN_STARS = 50            # minimum stars for a GitHub repo to be crawled
RATE_LIMIT_DEFAULT = 1.0         # req/sec default when site publishes no rate limit headers

# GitHub query templates — {company} is substituted automatically per source.
# Multiple queries are deduplicated by repo full_name, so the same repo is never crawled twice.
GITHUB_QUERY_TEMPLATES = [
    "{company} interview questions",
    "{company} interview preparation",
    "{company} coding interview",
    "{company} system design interview",
    "{company} software engineer interview",
    "{company} SWE interview",
    "{company} technical interview",
    "{company} interview prep",
]

# --- Extraction ---
CHUNK_SIZE_TOKENS = 2000         # max tokens per chunk sent to Haiku

# --- Scrapable domains (link following allowlist) ---
SCRAPABLE_DOMAINS = [
    "github.com",
    "raw.githubusercontent.com",
    "reddit.com",
    "medium.com",
    "geeksforgeeks.org",
    "dev.to",
    "hackernoon.com",
]

# --- Company name normalization ---
# Alias map: known variant → canonical name
# Add new entries here as you discover inconsistencies across sources
COMPANY_ALIASES = {
    "[24]7 Innovation Labs": "24/7 Innovation Labs",
    "24*7 Innovation Labs": "24/7 Innovation Labs",
    "247 Innovation Labs": "24/7 Innovation Labs",
    "athenahealth": "AthenaHealth",
    "Athena Health": "AthenaHealth",
    "Athena-Health": "AthenaHealth",
    "Google LLC": "Google",
    "Google Inc": "Google",
    "Google Inc.": "Google",
    "Amazon.com": "Amazon",
    "Amazon Web Services": "AWS",
    "Microsoft Corporation": "Microsoft",
    "Meta Platforms": "Meta",
    "Facebook": "Meta",
    "Accolite India": "Accolite",
    "ADP India": "ADP",
}

# Legal suffixes to strip automatically if no alias matches
COMPANY_LEGAL_SUFFIXES = [
    ", Inc.", ", Inc", " Inc.", " Inc",
    ", LLC", " LLC",
    ", Ltd.", ", Ltd", " Ltd.", " Ltd",
    ", Corp.", ", Corp", " Corp.", " Corp",
    " Corporation", " Limited", " Group",
]

# --- Auto-abandon ---
# If a repo has >= ABANDON_MIN_FILES processed and >= ABANDON_EMPTY_PCT are empty, skip the rest
ABANDON_MIN_FILES = 10
ABANDON_EMPTY_PCT = 0.50

# --- Reddit ---
REDDIT_POST_MAX_AGE_DAYS = 3 * 365   # ~3 years; change here to adjust cutoff globally
REDDIT_USER_AGENT = "python:interview-questions-scraper:v1.0 (educational project)"

# Query templates — {company} is substituted automatically per source.
# Covers all major role types. Add new templates here to broaden coverage globally.
REDDIT_QUERY_TEMPLATES = [
    "{company} interview experience",
    "{company} interview questions",
    "{company} software engineer interview",
    "{company} machine learning interview",
    "{company} data engineer interview",
    "{company} data scientist interview",
    "{company} system design interview",
    "{company} SRE interview",
    "{company} product manager interview",
    "{company} program manager interview",
]

# --- Sources ---
# To add a new source, add an entry here — no pipeline code changes needed.
# Supported types:
#   "github_search"  — searches GitHub for repos matching a query
#   "url_list"       — scrapes a fixed list of URLs directly (no crawling)
#   "reddit_search"  — searches Reddit subreddits for posts matching a query
SOURCES = [
    # Adding a company requires only its name — queries are auto-generated from templates above.
    # To override queries for a specific company, add a "queries" key with a custom list.
    {
        "type": "github_search",
        "company": "Google",
        "filters": {"min_stars": GITHUB_MIN_STARS, "max_repos": MAX_REPOS_PER_SOURCE}
    },
    {"type": "reddit_search", "company": "Google"},
]

# --- Company Profiles ---
PROFILES_DB = "scraper/db/profiles.db"

# Max Reddit posts to analyze per company when building a profile.
# More posts = richer profile but more Haiku calls.
MAX_PROFILE_POSTS = 30

# Query templates for profile scraping — focused on process/experience, not just questions.
# {company} is substituted automatically per source.
PROFILE_REDDIT_QUERY_TEMPLATES = [
    "{company} interview experience",
    "{company} interview process",
    "{company} onsite interview",
    "{company} phone screen experience",
    "{company} hiring process",
]

# Companies to build profiles for.
# Add a company here to include it in the next profile scrape run.
PROFILE_SOURCES = [
    {
        "type": "reddit_search",
        "company": "Google",
        "queries": [t.format(company="Google") for t in PROFILE_REDDIT_QUERY_TEMPLATES],
    },
    # Add Amazon and Jane Street once Google profile is validated
    # {"type": "reddit_search", "company": "Amazon", "queries": [t.format(company="Amazon") for t in PROFILE_REDDIT_QUERY_TEMPLATES]},
    # {"type": "reddit_search", "company": "Jane Street", "queries": [t.format(company="Jane Street") for t in PROFILE_REDDIT_QUERY_TEMPLATES]},
]
