"""Checks the AI's claims against real code. This is plain code on purpose: a model
that was misled by a repository cannot talk its way past it."""
import re
from codesynapse.services.jobs import normalize

MIN_QUOTE_CHARS = 8
IMPORT_LINE = re.compile(
    r"^\s*(import\s|from\s+\S+\s+import\s|#\s*include\s|using\s+\S+;|(const|let|var)\s+.*require\(|require\()"
)

def is_import_only(quote):
    """An import shows a dependency was added, not that the skill was used."""
    lines = [line for line in quote.split("\n") if line.strip()]
    return all(IMPORT_LINE.match(line) for line in lines)

def find_lines(content, quote):
    """Returns the (first, last) line of the quote within content, 0-based, or None."""
    lines = content.split("\n")
    wanted = normalize(quote)
    if len(wanted) < MIN_QUOTE_CHARS or wanted not in normalize(content):
        return None

    # The first line where the quote is complete, then back up to where it starts
    last = next((i for i in range(len(lines)) if wanted in normalize(" ".join(lines[:i + 1]))), None)
    if last is None:
        return None
    first = next(i for i in range(last, -1, -1) if wanted in normalize(" ".join(lines[i:last + 1])))
    return first, last

def permalink(evidence, first_line, last_line):
    return (f"https://github.com/{evidence['repo']}/blob/{evidence['commit_sha']}/{evidence['path']}"
            f"#L{first_line}-L{last_line}")

def verify_claim(claim, evidence_by_id):
    """Returns the citation with real line numbers, or None if the claim can't be proved."""
    evidence = evidence_by_id.get(claim.evidence_id)
    if not evidence or is_import_only(claim.quote):
        return None
    position = find_lines(evidence["content"], claim.quote)
    if position is None:
        return None

    first_line = evidence["start_line"] + position[0]
    last_line = evidence["start_line"] + position[1]
    return {
        "claim": claim.claim,
        "quote": claim.quote,
        "repo": evidence["repo"],
        "path": evidence["path"],
        "symbol": evidence["symbol"],
        "start_line": first_line,
        "end_line": last_line,
        "url": permalink(evidence, first_line, last_line),
    }

def verify_assessment(assessment, evidence_by_id):
    """Splits an assessment's claims into proved citations and a count of rejected ones."""
    citations = [c for c in (verify_claim(claim, evidence_by_id) for claim in assessment.claims) if c]
    return citations, len(assessment.claims) - len(citations)
