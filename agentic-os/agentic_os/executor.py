"""Sandboxed code execution in Docker containers."""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Tuple


class ExecutionResult:
    """Result of a sandboxed code execution."""

    def __init__(self, success: bool, stdout: str, stderr: str, exit_code: int):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def __repr__(self) -> str:
        return f"<ExecutionResult(success={self.success}, exit_code={self.exit_code})>"


class SandboxedExecutor:
    """Executes generated code in throwaway Docker containers."""

    DOCKER_IMAGE = "python:3.11-slim"
    TIMEOUT_SECONDS = 30

    def execute_code(self, code: str, tests: str) -> ExecutionResult:
        """Execute code + tests in a sandboxed Docker container.

        Args:
            code: The generated Python code
            tests: The generated test code

        Returns:
            ExecutionResult with success status and output
        """
        # Create temp directory for this execution
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write code and tests to temp files
            code_file = tmpdir_path / "solution.py"
            test_file = tmpdir_path / "test_solution.py"

            code_file.write_text(code)
            test_file.write_text(tests)

            # Step 1: Create container with pytest installed (needs network)
            install_cmd = [
                "docker",
                "run",
                "--name", f"pytest-install-{tmpdir_path.name}",
                "--network=bridge",  # Network for pip install
                self.DOCKER_IMAGE,
                "pip", "install", "-q", "pytest",
            ]

            # Step 2: Commit the container with pytest installed
            commit_cmd = [
                "docker",
                "commit",
                f"pytest-install-{tmpdir_path.name}",
                f"pytest-ready-{tmpdir_path.name}",
            ]

            # Step 3: Run tests in isolated container (no network)
            test_cmd = [
                "docker",
                "run",
                "--rm",  # Auto-remove container after execution
                "--network=none",  # No network access during test execution
                "--memory=512m",  # Memory limit
                "--cpus=1",  # CPU limit
                f"--volume={tmpdir_path}:/workspace:ro",  # Read-only bind mount
                "--workdir=/workspace",
                f"pytest-ready-{tmpdir_path.name}",
                "pytest", "-v", "test_solution.py",
            ]

            try:
                # Install pytest
                subprocess.run(install_cmd, check=True, capture_output=True, timeout=20)

                # Commit the image
                subprocess.run(commit_cmd, check=True, capture_output=True, timeout=10)

                # Remove install container
                subprocess.run(
                    ["docker", "rm", "-f", f"pytest-install-{tmpdir_path.name}"],
                    capture_output=True,
                )

                # Run tests in isolated container
                result = subprocess.run(
                    test_cmd,
                    timeout=self.TIMEOUT_SECONDS,
                    capture_output=True,
                    text=True,
                )

                # Cleanup: remove committed image
                subprocess.run(
                    ["docker", "rmi", "-f", f"pytest-ready-{tmpdir_path.name}"],
                    capture_output=True,
                )

                return ExecutionResult(
                    success=(result.returncode == 0),
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                )

            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution timed out after {self.TIMEOUT_SECONDS} seconds",
                    exit_code=-1,
                )

            except Exception as e:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Execution failed: {str(e)}",
                    exit_code=-1,
                )

    def verify_docker_available(self) -> bool:
        """Check if Docker is available and running.

        Returns:
            True if Docker is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False


# Global executor instance
executor = SandboxedExecutor()
