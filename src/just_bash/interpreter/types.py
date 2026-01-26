"""Interpreter types for just-bash."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional, Awaitable

if TYPE_CHECKING:
    import random
    from ..ast.types import FunctionDefNode, ScriptNode, StatementNode, CommandNode
    from ..types import ExecResult, IFileSystem, Command, ExecutionLimits


@dataclass
class ShellOptions:
    """Shell options (set -e, etc.)."""

    errexit: bool = False
    """set -e: Exit immediately if a command exits with non-zero status."""

    pipefail: bool = False
    """set -o pipefail: Return exit status of last failing command in pipeline."""

    nounset: bool = False
    """set -u: Treat unset variables as an error when substituting."""

    xtrace: bool = False
    """set -x: Print commands and their arguments as they are executed."""

    verbose: bool = False
    """set -v: Print shell input lines as they are read."""


@dataclass
class InterpreterState:
    """Mutable state maintained by the interpreter."""

    env: dict[str, str] = field(default_factory=dict)
    """Environment variables."""

    cwd: str = "/home/user"
    """Current working directory."""

    previous_dir: str = "/home/user"
    """Previous directory (for cd -)."""

    functions: dict[str, "FunctionDefNode"] = field(default_factory=dict)
    """Defined functions."""

    local_scopes: list[dict[str, Optional[str]]] = field(default_factory=list)
    """Stack of local variable scopes for function calls."""

    call_depth: int = 0
    """Current function call depth."""

    source_depth: int = 0
    """Current source script nesting depth."""

    command_count: int = 0
    """Total commands executed (for limits)."""

    last_exit_code: int = 0
    """Exit code of last command."""

    last_arg: str = ""
    """Last argument of previous command (for $_)."""

    start_time: float = 0.0
    """Time when shell started (for $SECONDS)."""

    seconds_reset_time: Optional[float] = None
    """Time when SECONDS was reset (for SECONDS=n assignment)."""

    last_background_pid: int = 0
    """PID of last background job (for $!)."""

    current_line: int = 0
    """Current line number being executed (for $LINENO)."""

    options: ShellOptions = field(default_factory=ShellOptions)
    """Shell options."""

    in_condition: bool = False
    """True when executing condition for if/while/until."""

    loop_depth: int = 0
    """Current loop nesting depth (for break/continue)."""

    parent_has_loop_context: bool = False
    """True if spawned from within a loop context."""

    group_stdin: Optional[str] = None
    """Stdin for commands in compound commands."""

    readonly_vars: set[str] = field(default_factory=set)
    """Set of readonly variable names."""

    expansion_exit_code: Optional[int] = None
    """Exit code from expansion errors."""

    expansion_stderr: str = ""
    """Stderr from expansion errors."""

    associative_arrays: set[str] = field(default_factory=set)
    """Set of associative array variable names."""

    random_generator: Optional["random.Random"] = field(default=None, repr=False)
    """Random number generator for $RANDOM (seeded when RANDOM=n is assigned)."""


@dataclass
class InterpreterContext:
    """Context provided to interpreter methods."""

    state: InterpreterState
    """Mutable interpreter state."""

    fs: "IFileSystem"
    """Filesystem interface."""

    commands: dict[str, "Command"]
    """Command registry."""

    limits: "ExecutionLimits"
    """Execution limits."""

    exec_fn: Callable[[str, Optional[dict[str, str]], Optional[str]], Awaitable["ExecResult"]]
    """Function to execute a script string."""

    execute_script: Callable[["ScriptNode"], Awaitable["ExecResult"]]
    """Function to execute a script AST."""

    execute_statement: Callable[["StatementNode"], Awaitable["ExecResult"]]
    """Function to execute a statement AST."""

    execute_command: Callable[["CommandNode", str], Awaitable["ExecResult"]]
    """Function to execute a command AST."""

    fetch: Optional[Callable[[str], Awaitable[bytes]]] = None
    """Optional secure fetch function for network commands."""

    sleep: Optional[Callable[[float], Awaitable[None]]] = None
    """Optional sleep function for testing with mock clocks."""
