"""The simple approach the agent has to beat: one AI call over search results, with no verification."""
from typing import Literal
from pydantic import BaseModel
from codesynapse.agents.gap_analysis import EVIDENCE_CHARS
from codesynapse.services import llm, search

RESULTS_PER_SKILL = 5

class BaselineSkill(BaseModel):
    name: str
    level: Literal["strong", "partial", "none"]

class BaselineReply(BaseModel):
    skills: list[BaselineSkill]

def run(db, user, repo_id, skills):
    usage = llm.Usage()
    blocks = []
    for skill in skills:
        for hit in search.search_code(db, user, skill["name"], repo_id, RESULTS_PER_SKILL):
            blocks.append(f"--- {hit['path']} {hit['symbol']}\n{hit['content'][:EVIDENCE_CHARS]}")

    names = "\n".join(f"- {s['name']}" for s in skills)
    code = "\n\n".join(dict.fromkeys(blocks))
    prompt = f"""
    Rate how much this code shows each skill as strong, partial or none.
    Use each skill's name exactly as given.

    Skills:
    {names}

    Code:
    {code}
    """
    reply = llm.generate_json(prompt, BaselineReply, usage)
    levels = {s.name: s.level for s in reply.skills}
    return {s["name"]: levels.get(s["name"], "none") for s in skills}, usage
