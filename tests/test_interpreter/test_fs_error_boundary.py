"""Tests that a filesystem backend's errors stay inside the interpreter.

A custom backend can fail in ways the built-in ones never do -- a network
timeout, an I/O error, a permission model of its own. Those arrive as OSError
subclasses, and the command-execution boundary turns them into a failed
command rather than an exception escaping bash.exec().
"""

import errno

import pytest

from just_bash import Bash
from just_bash.fs import InMemoryFs


class FlakyFs:
    """InMemoryFs with chosen paths rigged to fail on read."""

    def __init__(self, initial_files=None, failures=None):
        self._inner = InMemoryFs(initial_files=initial_files or {})
        self._failures = failures or {}

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def _check(self, path):
        error = self._failures.get(path)
        if error is not None:
            raise error

    async def read_file(self, path: str, encoding: str = "utf-8") -> str:
        self._check(path)
        return await self._inner.read_file(path, encoding)

    async def read_file_bytes(self, path: str) -> bytes:
        self._check(path)
        return await self._inner.read_file_bytes(path)

    def resolve_path(self, base: str, path: str) -> str:
        return self._inner.resolve_path(base, path)


class TestBackendErrorsAreContained:
    """Test that an OSError from the backend becomes a failed command."""

    @pytest.mark.asyncio
    async def test_oserror_with_filename(self):
        """An errno-bearing failure should report path and strerror, exit 1."""
        fs = FlakyFs(
            initial_files={"/ok.txt": "fine\n"},
            failures={"/flaky.txt": OSError(errno.EIO, "Input/output error", "/flaky.txt")},
        )
        bash = Bash(fs=fs, cwd="/")

        result = await bash.exec("cat /flaky.txt")

        assert result.exit_code == 1
        assert result.stderr == "cat: /flaky.txt: Input/output error\n"
        assert result.stdout == ""

    @pytest.mark.asyncio
    async def test_timeout_error_without_filename(self):
        """TimeoutError is an OSError, so a slow backend is contained too."""
        fs = FlakyFs(
            initial_files={"/ok.txt": "fine\n"},
            failures={"/slow.txt": TimeoutError("backend timed out")},
        )
        bash = Bash(fs=fs, cwd="/")

        result = await bash.exec("cat /slow.txt")

        assert result.exit_code == 1
        assert result.stderr == "cat: backend timed out\n"

    @pytest.mark.asyncio
    async def test_shell_keeps_running_afterwards(self):
        """A contained failure should behave like any other nonzero command."""
        fs = FlakyFs(
            initial_files={"/ok.txt": "fine\n"},
            failures={"/flaky.txt": OSError(errno.EIO, "Input/output error", "/flaky.txt")},
        )
        bash = Bash(fs=fs, cwd="/")

        result = await bash.exec("cat /flaky.txt; echo continued; cat /ok.txt")

        assert result.exit_code == 0
        assert result.stdout == "continued\nfine\n"

    @pytest.mark.asyncio
    async def test_composes_with_errexit(self):
        """set -e should stop on the contained failure."""
        fs = FlakyFs(
            failures={"/flaky.txt": OSError(errno.EIO, "Input/output error", "/flaky.txt")},
        )
        bash = Bash(fs=fs, cwd="/", errexit=True)

        result = await bash.exec("cat /flaky.txt\necho unreachable")

        assert result.exit_code == 1
        assert "unreachable" not in result.stdout


class TestExistingBehaviorUnchanged:
    """Test that the errors commands already handle keep their own messages."""

    @pytest.mark.asyncio
    async def test_missing_file_message(self):
        """ENOENT should still come from cat, not from the boundary."""
        bash = Bash(files={"/ok.txt": "fine\n"}, cwd="/")

        result = await bash.exec("cat /nope.txt")

        assert result.exit_code == 1
        assert result.stderr == "cat: /nope.txt: No such file or directory\n"

    @pytest.mark.asyncio
    async def test_directory_message(self):
        """EISDIR should still come from cat."""
        bash = Bash(files={"/dir/file.txt": "x\n"}, cwd="/")

        result = await bash.exec("cat /dir")

        assert result.exit_code == 1
        assert result.stderr == "cat: /dir: Is a directory\n"

    @pytest.mark.asyncio
    async def test_permission_message(self):
        """EACCES should still come from cat."""
        fs = FlakyFs(
            initial_files={"/secret.txt": "x\n"},
            failures={"/secret.txt": PermissionError("EACCES: permission denied")},
        )
        bash = Bash(fs=fs, cwd="/")

        result = await bash.exec("cat /secret.txt")

        assert result.exit_code == 1
        assert result.stderr == "cat: /secret.txt: Permission denied\n"


class TestControlFlowStillPropagates:
    """Test that the boundary does not interfere with interpreter control flow."""

    @pytest.mark.asyncio
    async def test_exit_code_propagates(self):
        """exit 3 should still terminate the script with 3."""
        bash = Bash(files={"/ok.txt": "fine\n"}, cwd="/")

        result = await bash.exec("echo before\nexit 3\necho after")

        assert result.exit_code == 3
        assert result.stdout == "before\n"

    @pytest.mark.asyncio
    async def test_break_propagates(self):
        """break should still leave the loop rather than be caught."""
        bash = Bash(cwd="/")

        result = await bash.exec("for i in 1 2 3; do echo $i; break; done; echo done")

        assert result.exit_code == 0
        assert result.stdout == "1\ndone\n"

    @pytest.mark.asyncio
    async def test_return_propagates(self):
        """return should still leave the function with its code."""
        bash = Bash(cwd="/")

        result = await bash.exec("f() { return 4; }\nf\necho $?")

        assert result.exit_code == 0
        assert result.stdout == "4\n"
