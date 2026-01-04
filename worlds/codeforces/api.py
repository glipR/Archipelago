import asyncio
import base64
import cloudscraper
import re
import requests
import time
import random
import logging
import string
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlencode
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import CodeforcesWorld

@dataclass
class Problem:
    name: str
    rating: int | None
    tags: list[str]

    # CF related info
    contest_id: str
    problem_index: str

    favour_score: float = 0

    time_limit: int = 0

    @classmethod
    def from_json(cls, obj):
        name, contest_id, problem_index, rating, tags = (
            obj.get("name"), obj.get("contestId"), obj.get("index"), obj.get("rating"), obj.get("tags")
        )
        if name is None or contest_id is None or problem_index is None:
            return None
        return Problem(
            name,
            rating,
            tags or [],
            contest_id,
            problem_index
        )

    @property
    def url(self):
        return f"https://codeforces.com/problemset/problem/{self.contest_id}/{self.problem_index}"

    @property
    def id(self):
        return f"{self.contest_id}/{self.problem_index}"

    def generate_score(self, score_mapping: dict[str, (float, int)]):
        rating = 0
        for tag in self.tags:
            contribution = score_mapping.get(tag, 1)
            if not isinstance(contribution, (float, int)):
                # Invalid options
                self.favour_score = 1
                return self.favour_score
            if contribution == 0:
                self.favour_score = 0
                return self.favour_score
            rating += contribution
        self.favour_score = 1 if len(self.tags) == 0 else rating / len(self.tags)
        return self.favour_score

lookback_days = 7

cf_username = ""
cf_api_key = ""
cf_api_secret = ""

def default_last_checked_ts():
    return int(time.time()) - lookback_days * 24 * 60 * 60

last_checked_submission = default_last_checked_ts()

def set_user_info(username, api_key, api_secret):
    global cf_username, cf_api_key, cf_api_secret
    cf_username = username
    cf_api_key = api_key
    cf_api_secret = api_secret

def set_last_checked_submission(seconds: int):
    global last_checked_submission
    last_checked_submission = seconds

def get_last_checked_ts():
    return last_checked_submission

class CFAPIError(Exception):
    pass

def makeApiSig(endpoint, kwargs: dict[str, Any]):
    rand = "".join(random.choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits
    ) for _ in range(6))
    # Query params need to be sorted for signature
    s = {}
    for k in sorted(kwargs.keys()):
        s[k] = kwargs[k]
    queries = urlencode(s)
    to_hash = f"{rand}/{endpoint}?{queries}#{cf_api_secret}"
    h = hashlib.sha512(to_hash.encode("utf-8"))
    return rand + h.hexdigest()

def make_request(endpoint: str, **kwargs):
    try:
        if not cf_username and ("{user}" in endpoint or any("{user}" in v for v in kwargs.values())):
            raise CFAPIError("User not configured.")
        endpoint = endpoint.format(user=cf_username)
        for k in kwargs.keys():
            kwargs[k] = kwargs[k].format(user=cf_username)
        # Two different methods depending on if we are using the token
        if cf_api_key and cf_api_secret:
            kwargs["apiKey"] = cf_api_key
            kwargs["time"] = int(time.time())
            kwargs["apiSig"] = makeApiSig(endpoint, kwargs)
        resp = requests.get(f"https://codeforces.com/api/{endpoint}?{urlencode(kwargs)}")
        return resp
    except Exception as e:
        from CommonClient import logger
        import traceback
        logger.exception(traceback.format_exc())
        raise e

@lru_cache()
def get_all_problems() -> list[Problem]:
    resp = make_request("problemset.problems")
    try:
        obj = resp.json()
    except:
        raise ValueError(f"The request to codeforces failed, status code: {resp.status_code}")

    problems = obj.get("result", {}).get("problems", [])
    if len(problems) == 0:
        raise ValueError(f"The request to codeforces failed, status code: {resp.status_code} and response: {str(resp.obj)}")
    return [pr for pr in [Problem.from_json(p) for p in problems] if pr is not None]

async def new_submissions():
    """
    Retrieves new submissions after the last_checked_submission timestamp,
    and updates the last_checked_submission to the latest problem found whose state is not transient.
    """
    global last_checked_submission

    page_count = 5
    from_point = 1
    found_submissions = []
    end_found = False
    while not end_found:
        kwargs = {"from": str(from_point), "count": str(page_count), "handle": "{user}"}
        if cf_api_key and cf_api_secret:
            kwargs["includeSources"] = "true"
        resp = make_request("user.status", **kwargs)
        obj = resp.json()
        if len(obj["result"]) == 0:
            end_found = True
            continue
        for submission in obj["result"]:
            if submission["creationTimeSeconds"] <= last_checked_submission:
                end_found = True
                break
            found_submissions.append(submission)
        from_point += page_count
        await asyncio.sleep(0.2)
    # found_submissions contains all submissions descending in submission time.
    # Reverse and stop as soon as we see a transient status
    found_submissions.reverse()
    for subm in found_submissions:
        status = subm.get("verdict", None)
        if status in [None, "SUBMITTED", "TESTING"]:
            # Transient, may be replaced later
            break
        last_checked_submission = subm["creationTimeSeconds"]
        # Also add some extra info on submissions
        if "sourceBase64" in subm:
            b64_data = subm["sourceBase64"]
            decoded = base64.b64decode(b64_data).decode("utf-8")
            subm["sourceCode"] = decoded
        yield subm

def get_problem_time_limit(problem: Problem):
    from CommonClient import logger
    logger.info(f"Retrieving Time Limit for Problem: {problem.id}")
    return 1
    scraper = cloudscraper.create_scraper()
    def test_html():
        html = scraper.get(problem.url).text
        match = re.search(
            r'time limit per test\s*</div>\s*(\d+)\s*second',
            html,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        easier_match = re.search(
            r'(\d+)\s*second',
            html,
            re.IGNORECASE,
        )
        if easier_match:
            return int(easier_match.group(1))

        raise ValueError(f"Unable to determine time limit for {problem.id}")

    try:
        return test_html()
    except ValueError:
        import time
        # Try one more time, a bit later.
        time.sleep(3)
        return test_html()

def generate_problems(world: "CodeforcesWorld") -> list[Problem]:
    """
    Generates the problems for a particular CodeforcesWorld.
    """

    problem_list = get_all_problems()

    floor = world.options.rating_floor
    ceiling = world.options.rating_ceiling

    # First, get rid of all problems not withing the rating scale
    problem_list = [p for p in problem_list if p.rating is not None and floor <= p.rating <= ceiling]

    # Now generate the score of all problems using the tag options:
    for problem in problem_list:
        problem.generate_score(world.options.tag_preference_mapping.value)
    total_score = sum(p.favour_score for p in problem_list)

    def random_problem():
        random_score = world.random.random() * total_score
        # Linear search for the first problem favour_score that reduces random_score to <= 0.
        for prob in problem_list:
            random_score -= prob.favour_score
            if random_score <= 0:
                return prob
        # Maybe with float shenanigans :/
        return problem_list[-1]

    if len(problem_list) < world.options.number_of_problems:
        raise ValueError(
            "Not enough problems available to generate problems. "
            "Try loosening constraints or reducing #problems"
        )

    accepted_failures = 20
    problem_id_set = set()
    final_problems = []
    while len(problem_id_set) < world.options.number_of_problems:
        next_problem = random_problem()
        if next_problem.id not in problem_id_set:
            problem_id_set.add(next_problem.id)
            final_problems.append(next_problem)
        else:
            accepted_failures -= 1
            if accepted_failures <= 0:
                raise ValueError(
                    "Failed to generate problems from available list. "
                    "Your options are likely too restrictive, or problem count too high."
                )

    # Finally - collect time limits for all problems
    for problem in final_problems:
        time_limit = get_problem_time_limit(problem)
        problem.time_limit = time_limit
    return final_problems
