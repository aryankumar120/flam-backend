import subprocess
from typing import Tuple

class JobExecutor:
    @staticmethod
    def execute(command: str, timeout: int = 300) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout else "Command completed successfully"
                return True, output
            else:
                error = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                return False, error

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except FileNotFoundError as e:
            return False, f"Command not found: {str(e)}"
        except Exception as e:
            return False, f"Execution error: {str(e)}"
