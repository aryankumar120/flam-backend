import time
import signal
import os
import json
from multiprocessing import Process
from typing import List
from .storage import Storage
from .queue import QueueManager
from .models import Config

class WorkerManager:
    WORKER_PID_FILE = ".queuectl_workers.json"

    def __init__(self, config: Config):
        self.config = config

    def start_workers(self, count: int = 1):
        existing_pids = self._load_worker_pids()

        if existing_pids:
            running_count = sum(1 for pid in existing_pids if self._is_process_running(pid))
            if running_count > 0:
                print(f"Warning: {running_count} worker(s) already running")
                print(f"PIDs: {existing_pids}")
                print("Stop existing workers first")
                return

        worker_pids = []
        for i in range(count):
            process = Process(target=self._worker_loop, args=(i + 1,))
            process.start()
            worker_pids.append(process.pid)
            print(f"Started worker {i + 1} (PID: {process.pid})")

        self._save_worker_pids(worker_pids)
        print(f"\nStarted {count} worker(s) successfully")

    def stop_workers(self):
        worker_pids = self._load_worker_pids()

        if not worker_pids:
            print("No workers found")
            return

        stopped_count = 0
        for pid in worker_pids:
            if self._is_process_running(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent SIGTERM to worker PID {pid}")
                    stopped_count += 1
                except ProcessLookupError:
                    print(f"Worker PID {pid} not found (already stopped)")
                except PermissionError:
                    print(f"Permission denied to stop worker PID {pid}")
            else:
                print(f"Worker PID {pid} not running")

        if os.path.exists(self.WORKER_PID_FILE):
            os.remove(self.WORKER_PID_FILE)

        if stopped_count > 0:
            print(f"\nSent stop signal to {stopped_count} worker(s)")
            print("Workers will finish their current jobs before stopping")

    def get_worker_status(self) -> dict:
        worker_pids = self._load_worker_pids()

        if not worker_pids:
            return {"workers": 0, "pids": []}

        running_pids = [pid for pid in worker_pids if self._is_process_running(pid)]

        return {
            "workers": len(running_pids),
            "pids": running_pids,
        }

    def _worker_loop(self, worker_id: int):
        shutdown_flag = {"should_stop": False}

        def signal_handler(signum, frame):
            print(f"\nWorker {worker_id} (PID {os.getpid()}): Received shutdown signal")
            shutdown_flag["should_stop"] = True

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        storage = Storage(self.config.db_path)
        queue_manager = QueueManager(storage, self.config)

        print(f"Worker {worker_id} (PID {os.getpid()}): Started")

        try:
            while not shutdown_flag["should_stop"]:
                job = queue_manager.get_next_job()

                if job:
                    print(f"Worker {worker_id} (PID {os.getpid()}): Processing job {job.id}")
                    success = queue_manager.process_job(job)

                    if success:
                        print(f"Worker {worker_id} (PID {os.getpid()}): Job {job.id} completed")
                    else:
                        if job.state == "dead":
                            print(f"Worker {worker_id} (PID {os.getpid()}): Job {job.id} failed permanently")
                        else:
                            print(f"Worker {worker_id} (PID {os.getpid()}): Job {job.id} failed (attempt {job.attempts}/{job.max_retries})")
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            print(f"\nWorker {worker_id} (PID {os.getpid()}): Interrupted")
        finally:
            print(f"Worker {worker_id} (PID {os.getpid()}): Stopped")

    def _save_worker_pids(self, pids: List[int]):
        with open(self.WORKER_PID_FILE, "w") as f:
            json.dump(pids, f)

    def _load_worker_pids(self) -> List[int]:
        if not os.path.exists(self.WORKER_PID_FILE):
            return []

        try:
            with open(self.WORKER_PID_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _is_process_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
