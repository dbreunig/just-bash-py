"""Pytest runner for Oils spec tests.

This runs the imported spec tests from the Oils project against just-bash.
"""

from pathlib import Path

import pytest

from .parser import parse_spec_file
from .runner import format_error, run_test_case

CASES_DIR = Path(__file__).parent / "cases"

# Tests to skip entirely (interactive, requires real shell, etc.)
SKIP_FILES = {
    # Interactive shell tests - require TTY
    "interactive.test.sh",
    "interactive-parse.test.sh",
    "prompt.test.sh",
    "builtin-history.test.sh",
    "builtin-fc.test.sh",
    "builtin-bind.test.sh",
    "builtin-completion.test.sh",
    # Process/job control - requires real processes
    "background.test.sh",
    "builtin-process.test.sh",
    "builtin-kill.test.sh",
    "builtin-trap.test.sh",
    "builtin-trap-bash.test.sh",
    "builtin-trap-err.test.sh",
    "builtin-times.test.sh",
    "process-sub.test.sh",
    # Shell-specific features not implemented
    "alias.test.sh",
    "xtrace.test.sh",
    "builtin-dirs.test.sh",
    "sh-usage.test.sh",
    # ZSH-specific tests
    "zsh-assoc.test.sh",
    "zsh-idioms.test.sh",
    # BLE (bash line editor) specific
    "ble-features.test.sh",
    "ble-idioms.test.sh",
    "ble-unset.test.sh",
    # Tests that require external commands or real filesystem
    "nul-bytes.test.sh",
    "unicode.test.sh",
    # Meta/introspection tests
    "introspect.test.sh",
    "print-source-code.test.sh",
    "serialize.test.sh",
    "spec-harness-bug.test.sh",
    # Known differences / divergence docs (not real tests)
    "known-differences.test.sh",
    "divergence.test.sh",
    # Toysh-specific
    "toysh.test.sh",
    "toysh-posix.test.sh",
    # Blog/exploration tests (not spec tests)
    "blog1.test.sh",
    "blog2.test.sh",
    "blog-other1.test.sh",
    "explore-parsing.test.sh",
    # Extended globbing - not implemented
    "extglob-match.test.sh",
    "extglob-files.test.sh",
    "globstar.test.sh",
    "globignore.test.sh",
    "nocasematch-match.test.sh",
    # Advanced features not implemented
    "builtin-getopts.test.sh",  # getopts builtin
    "nameref.test.sh",  # nameref/declare -n
    "var-ref.test.sh",  # ${!var} indirect references
    "regex.test.sh",  # =~ regex matching
    "sh-options.test.sh",  # shopt options
    "sh-options-bash.test.sh",
    # Bash-specific builtins not implemented
    "builtin-bash.test.sh",
    "builtin-type-bash.test.sh",
    "builtin-vars.test.sh",
    "builtin-meta.test.sh",
    "builtin-meta-assign.test.sh",
    # Advanced array features
    "array-assoc.test.sh",  # associative arrays
    "array-sparse.test.sh",  # sparse arrays
    "array-compat.test.sh",
    "array-literal.test.sh",
    "array-assign.test.sh",
    # Complex assignment features
    "assign-extended.test.sh",
    "assign-deferred.test.sh",
    "assign-dialects.test.sh",
    # Advanced arithmetic
    "arith-dynamic.test.sh",
    # Complex redirect features
    "redirect-multi.test.sh",
    "redirect-command.test.sh",
    "redir-order.test.sh",
    # Other advanced features
    "command-sub-ksh.test.sh",
    "vars-bash.test.sh",
    "var-op-bash.test.sh",
    "type-compat.test.sh",
    "shell-grammar.test.sh",
    "shell-bugs.test.sh",
    "nix-idioms.test.sh",
    "paren-ambiguity.test.sh",
    "fatal-errors.test.sh",
    "for-expr.test.sh",
    "glob-bash.test.sh",
    "bool-parse.test.sh",
    "arg-parse.test.sh",
    "append.test.sh",
    "bugs.test.sh",
}


def get_test_files() -> list[str]:
    """Get list of test files to run."""
    all_files = sorted(f.name for f in CASES_DIR.glob("*.test.sh"))
    return [f for f in all_files if f not in SKIP_FILES]


def truncate_script(script: str, max_len: int = 60) -> str:
    """Truncate script for test name display."""
    # Normalize whitespace and get first meaningful line(s)
    lines = script.split("\n")
    meaningful = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    normalized = " | ".join(meaningful)

    if len(normalized) <= max_len:
        return normalized
    return f"{normalized[:max_len - 3]}..."


# Collect test cases
def pytest_generate_tests(metafunc):
    """Generate test parameters for each test case."""
    if "test_file" in metafunc.fixturenames and "test_case" in metafunc.fixturenames:
        test_params = []
        for file_name in get_test_files():
            file_path = CASES_DIR / file_name
            spec_file = parse_spec_file(file_path)
            for test_case in spec_file.test_cases:
                script_preview = truncate_script(test_case.script)
                test_id = f"{file_name}::{test_case.name}[L{test_case.line_number}]"
                test_params.append(pytest.param(file_name, test_case, id=test_id))
        metafunc.parametrize("test_file,test_case", test_params)


class TestSpecTests:
    """Run Oils spec tests against just-bash."""

    @pytest.mark.asyncio
    async def test_spec_case(self, test_file, test_case):
        """Run a single spec test case."""
        result = await run_test_case(test_case)

        if result.skipped:
            pytest.skip(result.skip_reason or "Skipped")

        if not result.passed:
            pytest.fail(format_error(result))


# Alternative simpler approach: run all tests in a file together
@pytest.mark.asyncio
@pytest.mark.parametrize("test_file", get_test_files())
async def test_spec_file(test_file: str):
    """Run all tests in a spec file."""
    file_path = CASES_DIR / test_file
    spec_file = parse_spec_file(file_path)

    passed = 0
    failed = 0
    skipped = 0
    failures = []

    for test_case in spec_file.test_cases:
        result = await run_test_case(test_case)

        if result.skipped:
            skipped += 1
        elif result.passed:
            passed += 1
        else:
            failed += 1
            failures.append(format_error(result))

    if failures:
        summary = f"\n\n{'='*60}\nSummary: {passed} passed, {failed} failed, {skipped} skipped\n{'='*60}\n\n"
        # Show first 3 failures only
        failure_text = "\n\n---\n\n".join(failures[:3])
        if len(failures) > 3:
            failure_text += f"\n\n... and {len(failures) - 3} more failures"
        pytest.fail(summary + failure_text)
