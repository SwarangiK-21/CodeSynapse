import asyncio
import httpx
from codesynapse import config

def unavailable(platform, reason):
    """Result for a platform with no real data. score_norm None keeps it off the chart."""
    return {"platform": platform, "stats": {"Status": reason}, "score_norm": None}

# --- 1. LEETCODE (Standard GraphQL) ---
async def get_leetcode_stats(username):
    url = "https://leetcode.com/graphql"
    query = """
    query userProblemsSolved($username: String!) {
        matchedUser(username: $username) {
            submitStats: submitStatsGlobal {
                acSubmissionNum { difficulty count }
            }
            profile { ranking }
        }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json={'query': query, 'variables': {'username': username}})

        if resp.status_code != 200:
            return unavailable("LeetCode", f"Unavailable (HTTP {resp.status_code})")

        user_data = (resp.json().get("data") or {}).get("matchedUser")
        if not user_data:
            return unavailable("LeetCode", "User not found")

        stats = user_data["submitStats"]["acSubmissionNum"]
        total = next((item['count'] for item in stats if item['difficulty'] == 'All'), 0)
        hard = next((item['count'] for item in stats if item['difficulty'] == 'Hard'), 0)
        ranking = user_data["profile"]["ranking"]

        return {
            "platform": "LeetCode",
            "stats": {
                "Total Solved": total,
                "Ranking": ranking,
                "Hard Solved": hard,
                "Status": "Verified Live"
            },
            # Normalized score for the chart (0-100)
            "score_norm": min(total / 5, 100)
        }
    except Exception as e:
        print(f"LeetCode Error: {e}")
        return unavailable("LeetCode", "Unavailable (request failed)")

# --- 2. GITHUB ---
async def get_github_stats(username):
    url = f"https://api.github.com/users/{username}"
    headers = {"Authorization": f"Bearer {config.GITHUB_TOKEN}"} if config.GITHUB_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 404:
            return unavailable("GitHub", "User not found")
        if resp.status_code != 200:
            return unavailable("GitHub", f"Unavailable (HTTP {resp.status_code})")

        data = resp.json()
        repos = data.get("public_repos", 0)
        return {
            "platform": "GitHub",
            "stats": {
                "Public Repos": repos,
                "Followers": data.get("followers", 0),
                "Status": "Verified Live"
            },
            "score_norm": min(repos * 2, 100)
        }
    except Exception as e:
        print(f"GitHub Error: {e}")
        return unavailable("GitHub", "Unavailable (request failed)")

async def get_all_stats(usernames: dict):
    tasks = []

    if usernames.get('leetcode'):
        tasks.append(get_leetcode_stats(usernames['leetcode']))
    if usernames.get('github'):
        tasks.append(get_github_stats(usernames['github']))

    return await asyncio.gather(*tasks)
