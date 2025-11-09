#!/usr/bin/env python3
import os
import time
import signal
from queuectl.storage import Storage
from queuectl.queue import QueueManager
from queuectl.worker import WorkerManager
from queuectl.models import Config, JobState

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def print_menu():
    queue_manager = get_queue_manager()
    worker_manager = get_worker_manager()
    status = queue_manager.get_status()
    worker_status = worker_manager.get_worker_status()
    processing_jobs = queue_manager.get_jobs_by_state(JobState.PROCESSING)

    print("\n" + "="*50)
    print("QUEUE CONTROL")
    print("="*50)
    print(f"Workers: {worker_status['workers']}" + (f" (PIDs: {', '.join(map(str, worker_status['pids']))})" if worker_status['pids'] else " [NONE]"))
    print(f"Jobs: {status['pending']} pending | {status['processing']} running | {status['completed']} done | {status['failed']} failed | {status['dead']} dead")

    if processing_jobs:
        print("\nRunning:")
        for job in processing_jobs[:2]:
            print(f"  → [{job.id}] {job.command[:45]}...")
        if len(processing_jobs) > 2:
            print(f"  (+{len(processing_jobs) - 2} more)")

    print("\n1. Add  2. Status  3. List  4. Start  5. Stop  6. Workers  7. DLQ  8. Config  9. Exit")
    print("-"*50)

def get_queue_manager():
    storage = Storage()
    config = storage.load_config()
    return QueueManager(storage, config)

def get_worker_manager():
    storage = Storage()
    config = storage.load_config()
    return WorkerManager(config)

def add_job():
    print("\n--- Add Job ---")
    command = input("Command: ").strip()
    if not command:
        print("Error: Command cannot be empty")
        return

    job_id = input("Job ID (auto-generate): ").strip() or None
    max_retries = input("Max retries (3): ").strip()
    max_retries = int(max_retries) if max_retries.isdigit() else None

    queue_manager = get_queue_manager()
    worker_manager = get_worker_manager()
    job = queue_manager.enqueue(command, job_id, max_retries)
    worker_status = worker_manager.get_worker_status()

    print(f"✓ Job {job.id} added")
    if worker_status['workers'] == 0:
        print("⚠ No workers running")

def view_status():
    print("\n--- Status ---")
    queue_manager = get_queue_manager()
    worker_manager = get_worker_manager()
    status = queue_manager.get_status()
    worker_status = worker_manager.get_worker_status()

    print(f"\nJobs: {status['pending']} pending | {status['processing']} running | {status['completed']} done | {status['failed']} failed | {status['dead']} dead")
    print(f"Workers: {worker_status['workers']} active" + (f" (PIDs: {', '.join(map(str, worker_status['pids']))})" if worker_status['pids'] else " ⚠ None running"))

    processing_jobs = queue_manager.get_jobs_by_state(JobState.PROCESSING)
    if processing_jobs:
        print(f"\nRunning ({len(processing_jobs)}):")
        for job in processing_jobs:
            print(f"  [{job.id}] {job.command[:50]} ({job.attempts}/{job.max_retries})")

    pending_jobs = queue_manager.get_jobs_by_state(JobState.PENDING)
    if pending_jobs:
        print(f"\nQueued ({len(pending_jobs)}):")
        for job in pending_jobs[:3]:
            print(f"  [{job.id}] {job.command[:50]}")

def list_jobs():
    print("\n--- List Jobs ---")
    print("1. All  2. Pending  3. Processing  4. Completed  5. Failed  6. Dead")
    choice = input("Option: ").strip()

    state_map = {
        '2': (JobState.PENDING, 'Pending'),
        '3': (JobState.PROCESSING, 'Currently Running'),
        '4': (JobState.COMPLETED, 'Completed'),
        '5': (JobState.FAILED, 'Failed (Will Retry)'),
        '6': (JobState.DEAD, 'Dead (Max Retries Exceeded)')
    }

    queue_manager = get_queue_manager()

    if choice == '1':
        jobs = queue_manager.storage.get_all_jobs()
        title = "All Jobs"
    elif choice in state_map:
        state, title = state_map[choice]
        jobs = queue_manager.get_jobs_by_state(state)
    else:
        print("Invalid option")
        return

    if not jobs:
        print(f"No {title.lower()} jobs")
        return

    print(f"\n{title} ({len(jobs)}):")
    for job in jobs:
        icon = "→" if job.state == JobState.PROCESSING else "•"
        print(f"{icon} [{job.id}] {job.command[:60]} | {job.attempts}/{job.max_retries} tries")
        if job.error_message:
            print(f"  Error: {job.error_message[:80]}")

def start_workers():
    print("\n--- Start Workers ---")
    worker_manager = get_worker_manager()
    count = input("Workers to start (1): ").strip()
    count = int(count) if count.isdigit() and int(count) > 0 else 1
    worker_manager.start_workers(count)
    print(f"✓ Started {count} worker(s)")

def stop_workers():
    print("\n--- Stop Workers ---")
    worker_manager = get_worker_manager()
    current_workers = worker_manager.get_worker_status()

    if current_workers['workers'] == 0:
        print("No workers running")
        return

    confirm = input(f"Stop {current_workers['workers']} worker(s)? (y/n): ").strip().lower()
    if confirm == 'y':
        worker_manager.stop_workers()
        print("✓ Workers stopping")

def worker_status():
    print("\n--- Worker Status ---")
    queue_manager = get_queue_manager()
    worker_manager = get_worker_manager()
    ws = worker_manager.get_worker_status()
    qs = queue_manager.get_status()

    print(f"Workers: {ws['workers']}" + (f" (PIDs: {', '.join(map(str, ws['pids']))})" if ws['pids'] else " - None running"))
    print(f"Queue: {qs['pending']} pending | {qs['processing']} running | {qs['completed']} done | {qs['failed']} failed")

def dlq_menu():
    print("\n--- Dead Letter Queue ---")
    print("1. List  2. Retry")
    choice = input("Option: ").strip()

    queue_manager = get_queue_manager()

    if choice == '1':
        jobs = queue_manager.get_jobs_by_state(JobState.DEAD)
        if not jobs:
            print("No dead jobs")
            return

        print(f"\nDead jobs ({len(jobs)}):")
        for job in jobs:
            print(f"✗ [{job.id}] {job.command[:60]}")
            print(f"  Failed: {job.attempts} tries | {job.error_message[:80]}")

    elif choice == '2':
        jobs = queue_manager.get_jobs_by_state(JobState.DEAD)
        if not jobs:
            print("No dead jobs")
            return

        for job in jobs:
            print(f"  {job.id}: {job.command[:50]}")
        job_id = input("\nJob ID to retry: ").strip()

        if queue_manager.retry_dlq_job(job_id):
            print(f"✓ Job {job_id} re-queued")
        else:
            print(f"✗ Job {job_id} not found")

    else:
        print("Invalid option")

def config_menu():
    print("\n--- Config ---")
    print("1. Show  2. Max Retries  3. Backoff Base")
    choice = input("Option: ").strip()

    storage = Storage()
    config = storage.load_config()

    if choice == '1':
        print(f"\nMax Retries: {config.max_retries}")
        print(f"Backoff Base: {config.backoff_base} (delays: {config.backoff_base}s, {config.backoff_base**2}s, {config.backoff_base**3}s...)")
        print(f"DB Path: {config.db_path}")

    elif choice == '2':
        value = input(f"Max retries ({config.max_retries}): ").strip()
        if value.isdigit() and int(value) > 0:
            config.max_retries = int(value)
            storage.save_full_config(config)
            print(f"✓ Max retries: {value}")
        else:
            print("✗ Invalid value")

    elif choice == '3':
        value = input(f"Backoff base ({config.backoff_base}): ").strip()
        if value.isdigit() and int(value) > 0:
            config.backoff_base = int(value)
            storage.save_full_config(config)
            print(f"✓ Backoff: {value}s, {value**2}s, {value**3}s...")
        else:
            print("✗ Invalid value")

    else:
        print("Invalid option")

def main():
    actions = {
        '1': add_job, '2': view_status, '3': list_jobs,
        '4': start_workers, '5': stop_workers, '6': worker_status,
        '7': dlq_menu, '8': config_menu
    }

    while True:
        try:
            print_menu()
            choice = input("\nOption: ").strip()

            if choice == '9':
                print("Exiting...")
                break
            elif choice in actions:
                actions[choice]()
            else:
                print("Invalid option")

            input("\n[Press Enter]")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            input("\n[Press Enter]")

if __name__ == '__main__':
    main()
