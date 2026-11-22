"""Background generation jobs with cooperative cancellation and bounded history."""
from threading import Event, Lock, Thread
from time import monotonic
from uuid import uuid4
from .core import Budget
from .service import dispatch


class GenerationJobs:
    def __init__(self):
        self._lock = Lock()
        self._jobs = {}

    def start(self, data):
        with self._lock:
            # Keep only recent completed results; never discard active jobs.
            self._jobs = {k: v for k, v in self._jobs.items()
                          if v['result'] is None or monotonic() - v['finished'] < 60}
            if sum(j['result'] is None for j in self._jobs.values()) >= 2:
                raise ValueError('Two generation jobs are already running. Stop one first.')
            key = uuid4().hex
            job = dict(event=Event(), started=monotonic(), result=None, finished=None)
            self._jobs[key] = job
        Thread(target=self._run, args=(job, dict(data)), daemon=True).start()
        return dict(job_id=key)

    def _run(self, job, data):
        try:
            budget = Budget(max_nodes=None, cancel_event=job['event'],
                            solution_limit=2, max_attempts=None)
            result = dispatch('generate', data, budget=budget)
        except (ValueError, TypeError) as error:
            result = dict(status='error', message=str(error))
        except Exception:
            import traceback
            traceback.print_exc()
            result = dict(status='error', message='Generation failed. See server console.')
        with self._lock:
            # A cancellation accepted before completion wins the race.
            if job['event'].is_set():
                result = dict(status='cancelled')
            result['elapsed_ms'] = (monotonic() - job['started']) * 1000
            job['result'], job['finished'] = result, monotonic()

    def status(self, key):
        with self._lock:
            job = self._get(key)
            return job['result'] or dict(status='running',
                                        elapsed_ms=(monotonic() - job['started']) * 1000)

    def cancel(self, key):
        with self._lock:
            job = self._get(key)
            if job['result'] is None:
                job['event'].set()
                return dict(status='stopping')
            return job['result']

    def _get(self, key):
        if not isinstance(key, str) or key not in self._jobs:
            raise ValueError('Unknown generation job.')
        return self._jobs[key]
