"""Main Bash class - the primary API for just-bash.

Example usage:
    from just_bash import Bash

    # Synchronous usage (for REPL, scripts)
    bash = Bash()
    result = bash.run("echo hello world")
    print(result.stdout)  # "hello world\n"

    # Async usage (for async applications)
    bash = Bash()
    result = await bash.exec("echo hello world")
    print(result.stdout)  # "hello world\n"

    # With initial files
    bash = Bash(files={"/data.txt": "hello\\n"})
    result = bash.run("cat /data.txt")

    # With execution limits
    bash = Bash(limits=ExecutionLimits(max_command_count=1000))
"""

import asyncio
from typing import Optional

from .commands import create_command_registry
from .fs import InMemoryFs
from .interpreter import Interpreter, InterpreterState, ShellOptions
from .parser import parse
from .types import (
    Command,
    ExecResult,
    ExecutionLimits,
    IFileSystem,
    NetworkConfig,
)


class Bash:
    """Main Bash interpreter class.

    Provides a high-level API for executing bash scripts in a sandboxed
    environment with an in-memory virtual filesystem.
    """

    def __init__(
        self,
        *,
        fs: Optional[IFileSystem] = None,
        files: Optional[dict[str, str | bytes]] = None,
        cwd: str = "/home/user",
        env: Optional[dict[str, str]] = None,
        limits: Optional[ExecutionLimits] = None,
        network: Optional[NetworkConfig] = None,
        commands: Optional[dict[str, Command]] = None,
        errexit: bool = False,
        pipefail: bool = False,
        nounset: bool = False,
    ):
        """Initialize the Bash interpreter.

        Args:
            fs: Filesystem to use. If not provided, creates an InMemoryFs.
            files: Initial files to create (requires default InMemoryFs).
            cwd: Initial working directory.
            env: Additional environment variables.
            limits: Execution limits for security.
            network: Network configuration (for curl command).
            commands: Custom command registry. If not provided, uses built-in commands.
            errexit: Enable errexit (set -e) mode.
            pipefail: Enable pipefail mode.
            nounset: Enable nounset (set -u) mode.
        """
        # Set up filesystem
        if fs is not None:
            self._fs = fs
        else:
            self._fs = InMemoryFs(initial_files=files or {})

        # Set up limits
        self._limits = limits or ExecutionLimits()

        # Set up commands
        self._commands = commands or create_command_registry()

        # Set up network config
        self._network = network

        # Set up initial state
        default_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/home/user",
            "USER": "user",
            "SHELL": "/bin/bash",
            "PWD": cwd,
            "?": "0",
        }
        if env:
            default_env.update(env)

        self._initial_state = InterpreterState(
            env=default_env,
            cwd=cwd,
            previous_dir=cwd,
            options=ShellOptions(
                errexit=errexit,
                pipefail=pipefail,
                nounset=nounset,
            ),
        )

        # Create interpreter
        self._interpreter = Interpreter(
            fs=self._fs,
            commands=self._commands,
            limits=self._limits,
            state=self._initial_state,
        )

    @property
    def fs(self) -> IFileSystem:
        """Get the filesystem."""
        return self._fs

    @property
    def cwd(self) -> str:
        """Get the current working directory."""
        return self._interpreter.state.cwd

    @property
    def env(self) -> dict[str, str]:
        """Get the environment variables."""
        return self._interpreter.state.env

    async def exec(
        self,
        script: str,
        *,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> ExecResult:
        """Execute a bash script.

        Args:
            script: The bash script to execute.
            env: Additional environment variables for this execution.
            cwd: Working directory for this execution.

        Returns:
            ExecResult with stdout, stderr, exit_code, and final env.
        """
        # Parse the script
        ast = parse(script)

        # Update state if env/cwd provided
        if env:
            self._interpreter.state.env.update(env)
        if cwd:
            self._interpreter.state.cwd = cwd
            self._interpreter.state.env["PWD"] = cwd

        # Execute
        return await self._interpreter.execute_script(ast)

    def run(
        self,
        script: str,
        *,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> ExecResult:
        """Execute a bash script synchronously.

        This is a convenience wrapper around exec() for use in the REPL
        or other synchronous contexts.

        Args:
            script: The bash script to execute.
            env: Additional environment variables for this execution.
            cwd: Working directory for this execution.

        Returns:
            ExecResult with stdout, stderr, exit_code, and final env.

        Example:
            >>> bash = Bash()
            >>> result = bash.run('echo "Hello, World!"')
            >>> print(result.stdout)
            Hello, World!
        """
        return asyncio.run(self.exec(script, env=env, cwd=cwd))

    def reset(self) -> None:
        """Reset the interpreter state to initial values."""
        self._interpreter = Interpreter(
            fs=self._fs,
            commands=self._commands,
            limits=self._limits,
            state=InterpreterState(
                env=dict(self._initial_state.env),
                cwd=self._initial_state.cwd,
                previous_dir=self._initial_state.previous_dir,
                options=ShellOptions(
                    errexit=self._initial_state.options.errexit,
                    pipefail=self._initial_state.options.pipefail,
                    nounset=self._initial_state.options.nounset,
                ),
            ),
        )
