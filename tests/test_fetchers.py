import asyncio
import httpx
import pytest
import respx
from codesynapse.services import fetchers

GITHUB = "https://api.github.com/users/octocat"
LEETCODE = "https://leetcode.com/graphql"

def run(coro):
    return asyncio.run(coro)

@pytest.fixture
def mocked():
    with respx.mock(assert_all_called=False) as m:
        yield m

def test_github_success(mocked):
    mocked.get(GITHUB).respond(json={"public_repos": 8, "followers": 3})
    result = run(fetchers.get_github_stats("octocat"))
    assert result["stats"] == {"Public Repos": 8, "Followers": 3, "Status": "Verified Live"}
    assert result["score_norm"] == 16

def test_github_score_is_capped(mocked):
    mocked.get(GITHUB).respond(json={"public_repos": 500})
    assert run(fetchers.get_github_stats("octocat"))["score_norm"] == 100

def test_github_unknown_user_gets_no_stats(mocked):
    mocked.get(GITHUB).respond(404)
    assert run(fetchers.get_github_stats("octocat")) == fetchers.unavailable("GitHub", "User not found")

def test_github_rate_limit_gets_no_stats(mocked):
    mocked.get(GITHUB).respond(403)
    assert run(fetchers.get_github_stats("octocat"))["score_norm"] is None

def test_github_network_failure_gets_no_stats(mocked):
    mocked.get(GITHUB).mock(side_effect=httpx.ConnectTimeout("slow"))
    assert run(fetchers.get_github_stats("octocat"))["score_norm"] is None

def leetcode_payload():
    return {"data": {"matchedUser": {
        "submitStats": {"acSubmissionNum": [{"difficulty": "All", "count": 100}, {"difficulty": "Hard", "count": 5}]},
        "profile": {"ranking": 42},
    }}}

def test_leetcode_success(mocked):
    mocked.post(LEETCODE).respond(json=leetcode_payload())
    result = run(fetchers.get_leetcode_stats("octocat"))
    assert result["stats"] == {"Total Solved": 100, "Ranking": 42, "Hard Solved": 5, "Status": "Verified Live"}
    assert result["score_norm"] == 20

def test_leetcode_unknown_user_gets_no_stats(mocked):
    mocked.post(LEETCODE).respond(json={"errors": [{"message": "no user"}], "data": {"matchedUser": None}})
    assert run(fetchers.get_leetcode_stats("octocat")) == fetchers.unavailable("LeetCode", "User not found")

def test_leetcode_server_error_gets_no_stats(mocked):
    mocked.post(LEETCODE).respond(500)
    assert run(fetchers.get_leetcode_stats("octocat"))["score_norm"] is None

def test_blank_usernames_are_skipped():
    assert run(fetchers.get_all_stats({"github": "", "leetcode": ""})) == []
