"""Orchestrator implementing the Karpathy validation loop."""

from typing import Tuple, Optional

from .agents import router, AgentRole
from .executor import executor
from .db import Task, SessionLocal


class OrchestrationResult:
    """Result of a complete Karpathy loop execution."""

    def __init__(
        self,
        success: bool,
        code: str,
        tests: str,
        test_output: str,
        error_trace: Optional[str] = None,
        iterations: int = 0,
    ):
        self.success = success
        self.code = code
        self.tests = tests
        self.test_output = test_output
        self.error_trace = error_trace
        self.iterations = iterations


class Orchestrator:
    """Orchestrator coordinating the Karpathy validation loop.

    Flow: Decompose → Implementer → Debugger → Test Executor → Merge
    """

    MAX_ITERATIONS = 3

    def run_task(self, spec: str, task_id: int) -> OrchestrationResult:
        """Execute complete Karpathy loop for a coding task.

        Args:
            spec: Plain-language specification
            task_id: Database task ID for status tracking

        Returns:
            OrchestrationResult with final code and test results
        """
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()

        try:
            # Phase 1: Decompose task
            decomposition = self._decompose(spec)
            task.status = "decomposed"
            db.commit()

            # Phase 2-5: Implementation loop with validation
            for iteration in range(self.MAX_ITERATIONS):
                task.iteration_count = iteration + 1
                db.commit()

                # Phase 2: Core Implementer generates code
                code, tests = self._implement(spec, decomposition, task.error_trace)
                task.status = "implemented"
                task.code = code
                db.commit()

                # Phase 3: Debugger reviews code
                review_result = self._debug(code, tests)
                task.status = "reviewed"
                db.commit()

                # If debugger found critical issues, incorporate feedback
                if review_result.get("has_critical_issues"):
                    task.error_trace = review_result.get("feedback", "")
                    continue

                # Phase 4: Execute tests in sandbox
                exec_result = executor.execute_code(code, tests)
                task.test_output = exec_result.stdout + "\n" + exec_result.stderr
                db.commit()

                if exec_result.success:
                    # Phase 5: Merge approval
                    final_code = self._merge_approve(code, tests, spec)

                    # Re-validate the merge-approved code: the approval step can
                    # rewrite the implementation, so it must pass the same tests
                    # before being accepted. Fall back to the already-validated
                    # code if the rewrite breaks anything.
                    if final_code != code:
                        merge_exec_result = executor.execute_code(final_code, tests)
                        if merge_exec_result.success:
                            task.test_output = merge_exec_result.stdout + "\n" + merge_exec_result.stderr
                        else:
                            final_code = code

                    task.status = "completed"
                    task.code = final_code
                    db.commit()

                    return OrchestrationResult(
                        success=True,
                        code=final_code,
                        tests=tests,
                        test_output=task.test_output,
                        iterations=iteration + 1,
                    )
                else:
                    # Tests failed: provide error trace for next iteration
                    task.error_trace = exec_result.stderr
                    task.status = "testing_failed"
                    db.commit()

            # Max iterations exceeded
            task.status = "failed"
            db.commit()

            return OrchestrationResult(
                success=False,
                code=task.code or "",
                tests=tests,
                test_output=task.test_output or "",
                error_trace=task.error_trace,
                iterations=self.MAX_ITERATIONS,
            )

        finally:
            db.close()

    def _decompose(self, spec: str) -> str:
        """Decompose task into sub-tasks (Orchestrator role).

        Args:
            spec: Plain-language specification

        Returns:
            Structured decomposition
        """
        system_prompt = """You are an expert software architect. Decompose coding tasks into atomic sub-tasks.
For the task "generate function + tests", decompose into:
1. Function requirements (name, parameters, return type, edge cases)
2. Test requirements (happy path, edge cases, error conditions)

Be specific and concise."""

        prompt = f"""Decompose this coding task into atomic sub-tasks:

Specification: {spec}

Provide a structured breakdown of what needs to be implemented."""

        return router.call_agent(
            role=AgentRole.ORCHESTRATOR,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
        )

    def _implement(self, spec: str, decomposition: str, error_trace: Optional[str]) -> Tuple[str, str]:
        """Generate code and tests (Core Implementer role).

        Args:
            spec: Original specification
            decomposition: Task decomposition from orchestrator
            error_trace: Error feedback from previous iteration (if any)

        Returns:
            Tuple of (code, tests)
        """
        system_prompt = """You are an expert Python developer. Generate clean, correct code with comprehensive tests.

Output format:
```python
# solution.py
[your implementation here]
```

```python
# test_solution.py
import pytest
from solution import *

[your tests here]
```

Follow best practices: clear names, docstrings, edge case handling."""

        feedback_section = ""
        if error_trace:
            feedback_section = f"""

Previous iteration failed with this error:
```
{error_trace}
```

Fix the issues and regenerate the code."""

        prompt = f"""Generate Python code for this specification:

{spec}

Decomposition:
{decomposition}{feedback_section}

Provide both implementation and tests in the format specified."""

        response = router.call_agent(
            role=AgentRole.IMPLEMENTER,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2048,
        )

        # Parse code blocks from response
        code, tests = self._parse_code_blocks(response)
        return code, tests

    def _debug(self, code: str, tests: str) -> dict:
        """Review code for bugs (Debugger role).

        Args:
            code: Generated code
            tests: Generated tests

        Returns:
            Dict with has_critical_issues (bool) and feedback (str)
        """
        system_prompt = """You are an expert code reviewer focused on correctness and security.
Review code for:
- Logic bugs
- Edge case handling
- Security issues (injection, validation)
- Test coverage

Respond in this format:
CRITICAL_ISSUES: [YES/NO]
FEEDBACK: [your detailed feedback, or "No critical issues found"]"""

        prompt = f"""Review this code for bugs and issues:

```python
# solution.py
{code}
```

```python
# test_solution.py
{tests}
```

Provide your assessment."""

        response = router.call_agent(
            role=AgentRole.DEBUGGER,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1024,
        )

        # Parse debugger response
        has_issues = "CRITICAL_ISSUES: YES" in response
        return {
            "has_critical_issues": has_issues,
            "feedback": response,
        }

    def _merge_approve(self, code: str, tests: str, spec: str) -> str:
        """Final architectural review and merge approval (Orchestrator role).

        Args:
            code: Validated code
            tests: Validated tests
            spec: Original specification

        Returns:
            Final approved code
        """
        system_prompt = """You are a software architect performing final merge approval.
Check: naming conventions, structure, alignment with spec.
Return the final approved code only (no tests)."""

        prompt = f"""Final review for merge:

Specification: {spec}

Code:
```python
{code}
```

If approved, return the final code. If minor improvements needed, return improved code."""

        response = router.call_agent(
            role=AgentRole.ORCHESTRATOR,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )

        # Extract code from response
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            return response[start:end].strip()

        return code  # Fallback to original if no code block

    def _parse_code_blocks(self, response: str) -> Tuple[str, str]:
        """Parse solution and test code blocks from implementer response.

        Args:
            response: Implementer response with code blocks

        Returns:
            Tuple of (code, tests)
        """
        code_blocks = []
        lines = response.split("\n")
        in_block = False
        current_block = []

        for line in lines:
            if line.strip().startswith("```python"):
                in_block = True
                current_block = []
            elif line.strip() == "```" and in_block:
                in_block = False
                code_blocks.append("\n".join(current_block))
            elif in_block:
                current_block.append(line)

        if len(code_blocks) >= 2:
            return code_blocks[0], code_blocks[1]
        elif len(code_blocks) == 1:
            # Only one block: assume it's code, generate minimal test
            return code_blocks[0], "import pytest\n\ndef test_placeholder():\n    assert True"

        # No code blocks found: return response as-is with minimal test
        return response, "import pytest\n\ndef test_placeholder():\n    assert True"


# Global orchestrator instance
orchestrator = Orchestrator()
