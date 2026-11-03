"""Checks every label against the repository's real files at its pinned commit. Uses no AI."""
import json
import re
import sys
from pathlib import Path
from codesynapse.services import repos

SUITES = {
    "core": Path(__file__).parent / "cases.json",
    # Traps: skills described in other words, mentioned but unused, or closely related but absent
    "hard": Path(__file__).parent / "cases_hard.json",
}

def load_cases(suite="core"):
    return json.loads(SUITES[suite].read_text(encoding="utf-8"))

def load_files(repo, commit):
    _, archive = repos.download_archive(repo, commit)
    return dict(repos.read_source_files(archive))

def label_problem(skill, files):
    """Returns why a label disagrees with the files, or None if it holds."""
    # READMEs only describe a project, so they prove nothing either way
    hits = [p for p, text in files.items()
            if not p.endswith(".md") and re.search(skill["proof"], text, re.MULTILINE)]
    if skill["present"] and not hits:
        return "labelled present, but the proof pattern matches nothing"
    if not skill["present"] and hits:
        return f"labelled absent, but found in {hits[:3]}"
    # A mentioned-only trap must really be mentioned somewhere, or it tests nothing
    if "mention" in skill and not any(re.search(skill["mention"], text) for text in files.values()):
        return "a trap whose mention appears nowhere in the repository"
    return None

def main():
    problems = checked = 0
    for suite in SUITES:
        for case in load_cases(suite):
            files = load_files(case["repo"], case["commit"])
            for skill in case["skills"]:
                checked += 1
                problem = label_problem(skill, files)
                if problem:
                    problems += 1
                    print(f"PROBLEM {suite} {case['repo']} / {skill['name']}: {problem}")
    print(f"{checked} labels checked, {problems} problems")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
