# Queue Control System

Simple job queue with background workers and real-time monitoring.

## Quick Start

```bash
python3 main.py
```

No dependencies - uses Python 3 standard library only.

## Features

- Real-time status dashboard
- Background job processing
- Auto-retry with exponential backoff
- Dead letter queue for failed jobs
- Configurable retry policies

## Usage

1. Start workers: `Option 4`
2. Add jobs: `Option 1`
3. Monitor: Dashboard auto-updates

## Job States

- **Pending** → **Processing** → **Completed**
- **Failed** → Auto-retry → **Dead** (max retries exceeded)

## Storage

Jobs stored in `.queuectl.db` (SQLite)
