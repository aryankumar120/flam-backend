# Queue Control System (QueueCTL)

A lightweight, reliable job queue system with background workers and real-time monitoring capabilities, built entirely with Python's standard library.

[![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 🚀 Overview

QueueCTL is a zero-dependency job queue system that provides robust background job processing with built-in monitoring, automatic retries, and a dead letter queue for failed jobs. Perfect for managing background tasks, processing queues, and handling asynchronous operations in Python applications.

## ✨ Key Features

- **Zero External Dependencies**: Built entirely with Python's standard library
- **Real-time Monitoring**: Live dashboard showing queue status and job progress
- **Background Processing**: Efficient multi-worker job execution
- **Robust Error Handling**:
  - Automatic retry mechanism with exponential backoff
  - Dead Letter Queue (DLQ) for failed jobs
  - Configurable retry policies
- **Persistent Storage**: SQLite-based job storage for reliability
- **User-friendly CLI**: Interactive command-line interface for queue management

## 🛠 Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd queuectl
   ```

2. Run the application:
   ```bash
   python3 main.py
   ```

## 📖 Usage Guide

### Basic Operations

1. **Starting Workers**
   - Select `Option 4` from the main menu
   - Workers will start processing jobs in the background

2. **Adding Jobs**
   - Select `Option 1` from the main menu
   - Enter the command to be executed
   - Jobs are automatically queued for processing

3. **Monitoring**
   - Select `Option 2` for detailed status
   - The dashboard auto-updates with real-time information

### Advanced Features

- **Worker Management** (`Option 6`):
  - View active workers
  - Monitor worker health
  - Scale workers up/down

- **Dead Letter Queue** (`Option 7`):
  - View failed jobs
  - Retry or delete failed jobs
  - Analyze failure patterns

- **Configuration** (`Option 8`):
  - Adjust retry policies
  - Configure worker settings
  - Customize queue behavior

## 💫 Job Lifecycle

```
PENDING ─→ PROCESSING ─→ COMPLETED
            │
            └─→ FAILED ─→ [Retry] ─→ DEAD
                            ↑_____|
```

- **PENDING**: Jobs waiting to be processed
- **PROCESSING**: Currently being executed by a worker
- **COMPLETED**: Successfully processed jobs
- **FAILED**: Failed jobs (will be retried based on policy)
- **DEAD**: Jobs that exceeded maximum retry attempts

## 🗃 Technical Details

### Storage
- Jobs are persistently stored in `.queuectl.db` (SQLite database)
- Ensures data durability across system restarts
- Automatic database management and cleanup

### System Requirements
- Python 3.6 or higher
- No additional dependencies required
- Works on Linux, macOS, and Windows

## 📝 Contributing

Contributions are welcome! Please feel free to submit pull requests, create issues, or suggest improvements.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
