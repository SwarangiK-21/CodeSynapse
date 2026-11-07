"""Runs slow work, like indexing and analysis, outside the web request.

Jobs run in this process, so a restart stops them. recover_interrupted() marks those
as failed on startup instead of leaving them stuck.
"""
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import update
from codesynapse import config
from codesynapse.db.models import Analysis, Repo, utcnow

INTERRUPTED = "Interrupted by a server restart. Please try again."

executor = ThreadPoolExecutor(max_workers=config.WORKERS, thread_name_prefix="codesynapse-job")

# Tests run jobs immediately so results can be checked straight away
RUN_INLINE = False

def report_failure(future):
    error = future.exception()
    if error:
        print(f"Background Job Error: {error!r}")

def submit(function, *args):
    if RUN_INLINE:
        function(*args)
        return
    executor.submit(function, *args).add_done_callback(report_failure)

def recover_interrupted(db):
    """Fails jobs that were running when the server last stopped."""
    db.execute(update(Repo).where(Repo.status == "indexing").values(status="failed", error=INTERRUPTED))
    db.execute(update(Analysis).where(Analysis.status == "running")
               .values(status="failed", error=INTERRUPTED, finished_at=utcnow()))
    db.commit()
