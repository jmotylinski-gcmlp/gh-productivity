"""Map GitHub usernames to JIRA email addresses using fuzzy matching"""

import csv
import json
import re
from pathlib import Path
from difflib import SequenceMatcher


GITHUB_CSV = Path("data/exports/github/user_commits.csv")
JIRA_CSV = Path("data/exports/jira/user_issues.csv")
CONFIG_PATH = Path("config.json")


def normalize_github_username(username: str) -> str:
    """
    Normalize GitHub username by removing common suffixes and cleaning up.

    Examples:
        echang-gcmlp -> echang
        sjensen-gcm -> sjensen
        jmotylinski-gcmlp -> jmotylinski
        HiltonGiesenow -> hiltongiesenow
    """
    # Convert to lowercase
    name = username.lower()

    # Remove common suffixes
    suffixes = ['-gcmlp', '-gcm', 'gcmlp', 'gcm']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break

    # Remove trailing hyphens or underscores
    name = name.rstrip('-_')

    return name


def normalize_jira_email(email: str) -> str:
    """
    Normalize JIRA email by extracting the username part.

    Examples:
        echang@gcmlp.com -> echang
        jmotylinski@gcmlp.com -> jmotylinski
    """
    if not email or '@' not in email:
        return email.lower() if email else ''

    return email.split('@')[0].lower()


def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity between two strings using SequenceMatcher."""
    return SequenceMatcher(None, s1, s2).ratio()


def get_unique_github_usernames() -> set:
    """Read unique GitHub usernames from CSV."""
    usernames = set()

    if not GITHUB_CSV.exists():
        print(f"Warning: {GITHUB_CSV} not found")
        return usernames

    with open(GITHUB_CSV, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get('username', '').strip()
            if username:
                usernames.add(username)

    return usernames


def get_unique_jira_emails() -> set:
    """Read unique JIRA emails from CSV."""
    emails = set()

    if not JIRA_CSV.exists():
        print(f"Warning: {JIRA_CSV} not found")
        return emails

    with open(JIRA_CSV, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('assignee_email', '').strip()
            if email:
                emails.add(email)

    return emails


def find_best_jira_match(github_username: str, jira_emails: set, threshold: float = 0.7) -> tuple:
    """
    Find the best matching JIRA email for a GitHub username.

    Returns:
        Tuple of (jira_email, score) or (None, 0) if no match found
    """
    normalized_github = normalize_github_username(github_username)

    if not normalized_github:
        return None, 0

    best_match = None
    best_score = 0

    for email in jira_emails:
        normalized_jira = normalize_jira_email(email)

        if not normalized_jira:
            continue

        # Exact match after normalization
        if normalized_github == normalized_jira:
            return email, 1.0

        # Fuzzy match
        score = similarity_score(normalized_github, normalized_jira)

        # Also check if one contains the other
        if normalized_github in normalized_jira or normalized_jira in normalized_github:
            score = max(score, 0.85)

        if score > best_score:
            best_score = score
            best_match = email

    if best_score >= threshold:
        return best_match, best_score

    return None, 0


def build_user_mappings(threshold: float = 0.7) -> list:
    """
    Build mappings from GitHub usernames to JIRA emails.

    Returns:
        List of dicts with 'github' and 'jira' keys
    """
    github_users = get_unique_github_usernames()
    jira_emails = get_unique_jira_emails()

    print(f"Found {len(github_users)} GitHub usernames")
    print(f"Found {len(jira_emails)} JIRA emails")

    mappings = []
    matched = 0
    unmatched = []

    # Skip bot/system accounts
    skip_patterns = ['[bot]', 'copilot', 'dependabot', 'devops-']

    for github_user in sorted(github_users):
        # Skip bots and system accounts
        if any(pattern in github_user.lower() for pattern in skip_patterns):
            continue

        jira_email, score = find_best_jira_match(github_user, jira_emails, threshold)

        if jira_email:
            mappings.append({
                "github": github_user,
                "jira": jira_email
            })
            matched += 1
            print(f"  Matched: {github_user} -> {jira_email} (score: {score:.2f})")
        else:
            unmatched.append(github_user)

    print(f"\nMatched {matched} users")
    print(f"Unmatched {len(unmatched)} users:")
    for user in unmatched[:20]:  # Show first 20
        print(f"  - {user}")
    if len(unmatched) > 20:
        print(f"  ... and {len(unmatched) - 20} more")

    return mappings


def save_mappings_to_config(mappings: list):
    """Save user mappings to config.json."""
    # Load existing config
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)

    # Update with user_mappings at root level
    config['user_mappings'] = mappings

    # Write back
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved {len(mappings)} mappings to {CONFIG_PATH}")


def main():
    print("Building GitHub to JIRA user mappings...\n")

    mappings = build_user_mappings(threshold=0.7)
    save_mappings_to_config(mappings)


if __name__ == "__main__":
    main()
