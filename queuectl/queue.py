import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from .models import Job, JobState, Config
from .storage import Storage
from .executor import JobExecutor

class QueueManager:
    def __init__(self, storage: Storage, config: Config):
        self.storage = storage
        self.config = config
        self.executor = JobExecutor()

    def enqueue(self, command: str, job_id: Optional[str] = None, max_retries: Optional[int] = None) -> Job:
        if not job_id:
            job_id = self._generate_job_id()

        if max_retries is None:
            max_retries = self.config.max_retries

        job = Job(
            id=job_id,
            command=command,
            state=JobState.PENDING,
            max_retries=max_retries,
        )

        self.storage.save_job(job)
        return job

    def process_job(self, job: Job) -> bool:
        success, message = self.executor.execute(job.command)

        if success:
            job.state = JobState.COMPLETED
            job.error_message = None
            job.update_timestamp()
            self.storage.save_job(job)
            return True
        else:
            job.attempts += 1
            job.error_message = message
            job.update_timestamp()

            if job.attempts >= job.max_retries:
                job.state = JobState.DEAD
                job.next_retry_at = None
            else:
                job.state = JobState.FAILED
                delay_seconds = self._calculate_backoff(job.attempts)
                job.next_retry_at = self._calculate_next_retry(delay_seconds)

            self.storage.save_job(job)
            return False

    def get_next_job(self) -> Optional[Job]:
        current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        retryable_jobs = self.storage.get_retryable_jobs(current_time)

        if retryable_jobs:
            job = retryable_jobs[0]
            job.state = JobState.PENDING
            job.next_retry_at = None
            job.update_timestamp()
            self.storage.save_job(job)

        return self.storage.get_pending_job()

    def retry_dlq_job(self, job_id: str) -> bool:
        job = self.storage.get_job(job_id)

        if not job or job.state != JobState.DEAD:
            return False

        job.state = JobState.PENDING
        job.attempts = 0
        job.error_message = None
        job.next_retry_at = None
        job.update_timestamp()

        self.storage.save_job(job)
        return True

    def get_jobs_by_state(self, state: str) -> List[Job]:
        return self.storage.get_jobs_by_state(state)

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.storage.get_job(job_id)

    def get_status(self) -> dict:
        counts = self.storage.get_job_counts()
        return {
            "pending": counts.get(JobState.PENDING, 0),
            "processing": counts.get(JobState.PROCESSING, 0),
            "completed": counts.get(JobState.COMPLETED, 0),
            "failed": counts.get(JobState.FAILED, 0),
            "dead": counts.get(JobState.DEAD, 0),
            "total": sum(counts.values()),
        }

    def _generate_job_id(self) -> str:
        return f"job-{uuid.uuid4().hex[:12]}"

    def _calculate_backoff(self, attempts: int) -> int:
        return self.config.backoff_base ** attempts

    def _calculate_next_retry(self, delay_seconds: int) -> str:
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        return next_retry.isoformat().replace('+00:00', 'Z')
