"""Interpreter - AST Execution Engine.

Main interpreter class that executes bash AST nodes.
Delegates to specialized modules for:
- Word expansion (expansion.py)
- Arithmetic evaluation (arithmetic.py)
- Conditional evaluation (conditionals.py)
- Built-in commands (builtins/)
- Redirections (redirections.py)
"""

import time
from typing import Optional

from ..ast.types import (
    CommandNode,
    PipelineNode,
    ScriptNode,
    SimpleCommandNode,
    StatementNode,
    IfNode,
    ForNode,
    CStyleForNode,
    WhileNode,
    UntilNode,
    CaseNode,
    SubshellNode,
    GroupNode,
    FunctionDefNode,
    ConditionalCommandNode,
    ArithmeticCommandNode,
)
from ..types import Command, ExecResult, ExecutionLimits, IFileSystem
from .errors import (
    BadSubstitutionError,
    BreakError,
    ContinueError,
    ErrexitError,
    ExecutionLimitError,
    ExitError,
    NounsetError,
    ReturnError,
)
from .types import InterpreterContext, InterpreterState, ShellOptions
from .expansion import expand_word_async, expand_word_with_glob, get_variable, evaluate_arithmetic
from .conditionals import evaluate_conditional
from .control_flow import (
    execute_if,
    execute_for,
    execute_c_style_for,
    execute_while,
    execute_until,
    execute_case,
)
from .builtins import BUILTINS
from .builtins.alias import get_aliases
from .builtins.shopt import DEFAULT_SHOPTS


def _ok() -> ExecResult:
    """Return a successful result."""
    return ExecResult(stdout="", stderr="", exit_code=0)


def _result(stdout: str, stderr: str, exit_code: int) -> ExecResult:
    """Create an ExecResult."""
    return ExecResult(stdout=stdout, stderr=stderr, exit_code=exit_code)


def _failure(stderr: str) -> ExecResult:
    """Create a failed result with stderr."""
    return ExecResult(stdout="", stderr=stderr, exit_code=1)


def _is_shopt_set(env: dict[str, str], name: str) -> bool:
    """Check if a shopt option is set."""
    key = f"__shopt_{name}__"
    if key in env:
        return env[key] == "1"
    return DEFAULT_SHOPTS.get(name, False)


class Interpreter:
    """AST interpreter for bash scripts."""

    def __init__(
        self,
        fs: IFileSystem,
        commands: dict[str, Command],
        limits: ExecutionLimits,
        state: Optional[InterpreterState] = None,
    ):
        """Initialize the interpreter.

        Args:
            fs: Filesystem interface
            commands: Command registry
            limits: Execution limits
            state: Optional initial state (creates default if not provided)
        """
        self._fs = fs
        self._commands = commands
        self._limits = limits
        self._state = state or InterpreterState(
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/home/user",
                "USER": "user",
                "SHELL": "/bin/bash",
                "PWD": "/home/user",
                "?": "0",
            },
            cwd="/home/user",
            previous_dir="/home/user",
            start_time=time.time(),
        )

        # Build the context
        self._ctx = InterpreterContext(
            state=self._state,
            fs=fs,
            commands=commands,
            limits=limits,
            exec_fn=self._exec_fn,
            execute_script=self.execute_script,
            execute_statement=self.execute_statement,
            execute_command=self.execute_command,
        )

    @property
    def state(self) -> InterpreterState:
        """Get the interpreter state."""
        return self._state

    async def _exec_fn(
        self,
        script: str,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[str] = None,
    ) -> ExecResult:
        """Execute a script string (for subcommands)."""
        # Import here to avoid circular imports
        from ..parser import parse

        # Parse the script
        ast = parse(script)

        # Create a new state for the subshell if env/cwd are provided
        if env or cwd:
            new_env = {**self._state.env, **(env or {})}
            new_state = InterpreterState(
                env=new_env,
                cwd=cwd or self._state.cwd,
                previous_dir=self._state.previous_dir,
                functions=dict(self._state.functions),
                start_time=self._state.start_time,
                options=ShellOptions(
                    errexit=self._state.options.errexit,
                    pipefail=self._state.options.pipefail,
                    nounset=self._state.options.nounset,
                    xtrace=self._state.options.xtrace,
                    verbose=self._state.options.verbose,
                ),
            )
            sub_interpreter = Interpreter(
                fs=self._fs,
                commands=self._commands,
                limits=self._limits,
                state=new_state,
            )
            return await sub_interpreter.execute_script(ast)

        return await self.execute_script(ast)

    async def execute_script(self, node: ScriptNode) -> ExecResult:
        """Execute a script AST node."""
        stdout = ""
        stderr = ""
        exit_code = 0

        for statement in node.statements:
            try:
                result = await self.execute_statement(statement)
                stdout += result.stdout
                stderr += result.stderr
                exit_code = result.exit_code
                self._state.last_exit_code = exit_code
                self._state.env["?"] = str(exit_code)
            except ExitError as error:
                # ExitError always propagates up to terminate the script
                error.prepend_output(stdout, stderr)
                raise
            except ExecutionLimitError:
                # ExecutionLimitError must always propagate
                raise
            except ErrexitError as error:
                stdout += error.stdout
                stderr += error.stderr
                exit_code = error.exit_code
                self._state.last_exit_code = exit_code
                self._state.env["?"] = str(exit_code)
                return ExecResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    env=dict(self._state.env),
                )
            except NounsetError as error:
                stdout += error.stdout
                stderr += error.stderr
                exit_code = 1
                self._state.last_exit_code = exit_code
                self._state.env["?"] = str(exit_code)
                return ExecResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    env=dict(self._state.env),
                )
            except BadSubstitutionError as error:
                stdout += error.stdout
                stderr += error.stderr
                exit_code = 1
                self._state.last_exit_code = exit_code
                self._state.env["?"] = str(exit_code)
                return ExecResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    env=dict(self._state.env),
                )
            except (BreakError, ContinueError) as error:
                # Handle break/continue errors
                if self._state.loop_depth > 0:
                    # Inside a loop, propagate the error
                    error.prepend_output(stdout, stderr)
                    raise
                # Outside loops, silently continue
                stdout += error.stdout
                stderr += error.stderr
                continue
            except ReturnError as error:
                # Handle return - prepend accumulated output before propagating
                error.prepend_output(stdout, stderr)
                raise

        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            env=dict(self._state.env),
        )

    async def execute_statement(self, node: StatementNode) -> ExecResult:
        """Execute a statement AST node."""
        self._state.command_count += 1
        if self._state.command_count > self._limits.max_command_count:
            raise ExecutionLimitError(
                f"too many commands executed (>{self._limits.max_command_count}), "
                "increase execution_limits.max_command_count",
                "commands",
            )

        stdout = ""
        stderr = ""
        exit_code = 0
        last_executed_index = -1
        last_pipeline_negated = False

        for i, pipeline in enumerate(node.pipelines):
            operator = node.operators[i - 1] if i > 0 else None

            if operator == "&&" and exit_code != 0:
                continue
            if operator == "||" and exit_code == 0:
                continue

            result = await self.execute_pipeline(pipeline)
            stdout += result.stdout
            stderr += result.stderr
            exit_code = result.exit_code
            last_executed_index = i
            last_pipeline_negated = pipeline.negated

            # Update $? after each pipeline
            self._state.last_exit_code = exit_code
            self._state.env["?"] = str(exit_code)

        # Check errexit (set -e)
        if (
            self._state.options.errexit
            and exit_code != 0
            and last_executed_index == len(node.pipelines) - 1
            and not last_pipeline_negated
            and not self._state.in_condition
        ):
            raise ErrexitError(exit_code, stdout, stderr)

        return _result(stdout, stderr, exit_code)

    async def execute_pipeline(self, node: PipelineNode) -> ExecResult:
        """Execute a pipeline AST node."""
        # Use group_stdin for the first command if we're inside a group
        stdin = self._state.group_stdin or ""
        # Clear group_stdin after first use so it's not reused
        self._state.group_stdin = ""
        last_result = _ok()
        pipefail_exit_code = 0
        pipestatus_exit_codes: list[int] = []

        for i, command in enumerate(node.commands):
            is_last = i == len(node.commands) - 1

            try:
                result = await self.execute_command(command, stdin)
            except BadSubstitutionError as error:
                result = ExecResult(
                    stdout=error.stdout,
                    stderr=error.stderr,
                    exit_code=1,
                )
            except ExitError as error:
                # In a multi-command pipeline, each command runs in subshell context
                if len(node.commands) > 1:
                    result = ExecResult(
                        stdout=error.stdout,
                        stderr=error.stderr,
                        exit_code=error.exit_code,
                    )
                else:
                    raise

            # Track exit code for PIPESTATUS
            pipestatus_exit_codes.append(result.exit_code)

            # Track failing exit code for pipefail
            if result.exit_code != 0:
                pipefail_exit_code = result.exit_code

            if not is_last:
                stdin = result.stdout
                last_result = ExecResult(
                    stdout="",
                    stderr=result.stderr,
                    exit_code=result.exit_code,
                )
            else:
                last_result = result

        # Set PIPESTATUS array
        for key in list(self._state.env.keys()):
            if key.startswith("PIPESTATUS_"):
                del self._state.env[key]
        for i, code in enumerate(pipestatus_exit_codes):
            self._state.env[f"PIPESTATUS_{i}"] = str(code)
        self._state.env["PIPESTATUS__length"] = str(len(pipestatus_exit_codes))

        # Apply pipefail
        if self._state.options.pipefail and pipefail_exit_code != 0:
            last_result = ExecResult(
                stdout=last_result.stdout,
                stderr=last_result.stderr,
                exit_code=pipefail_exit_code,
            )

        # Apply negation
        if node.negated:
            last_result = ExecResult(
                stdout=last_result.stdout,
                stderr=last_result.stderr,
                exit_code=1 if last_result.exit_code == 0 else 0,
            )

        return last_result

    async def execute_command(self, node: CommandNode, stdin: str) -> ExecResult:
        """Execute a command AST node."""
        if isinstance(node, SimpleCommandNode) or node.type == "SimpleCommand":
            return await self._execute_simple_command(node, stdin)
        elif isinstance(node, IfNode) or node.type == "If":
            return await execute_if(self._ctx, node)
        elif isinstance(node, ForNode) or node.type == "For":
            return await execute_for(self._ctx, node)
        elif isinstance(node, CStyleForNode) or node.type == "CStyleFor":
            return await execute_c_style_for(self._ctx, node)
        elif isinstance(node, WhileNode) or node.type == "While":
            return await execute_while(self._ctx, node, stdin)
        elif isinstance(node, UntilNode) or node.type == "Until":
            return await execute_until(self._ctx, node)
        elif isinstance(node, CaseNode) or node.type == "Case":
            return await execute_case(self._ctx, node)
        elif isinstance(node, SubshellNode) or node.type == "Subshell":
            return await self._execute_subshell(node, stdin)
        elif isinstance(node, GroupNode) or node.type == "Group":
            return await self._execute_group(node, stdin)
        elif isinstance(node, FunctionDefNode) or node.type == "FunctionDef":
            return await self._execute_function_def(node)
        elif isinstance(node, ConditionalCommandNode) or node.type == "ConditionalCommand":
            return await self._execute_conditional(node)
        elif isinstance(node, ArithmeticCommandNode) or node.type == "ArithmeticCommand":
            return await self._execute_arithmetic(node)
        else:
            return _ok()

    async def _execute_subshell(self, node: SubshellNode, stdin: str) -> ExecResult:
        """Execute a subshell command."""
        # Create a new interpreter with a copy of the state
        new_state = InterpreterState(
            env=dict(self._state.env),
            cwd=self._state.cwd,
            previous_dir=self._state.previous_dir,
            functions=dict(self._state.functions),
            start_time=self._state.start_time,
            options=ShellOptions(
                errexit=self._state.options.errexit,
                pipefail=self._state.options.pipefail,
                nounset=self._state.options.nounset,
                xtrace=self._state.options.xtrace,
                verbose=self._state.options.verbose,
            ),
        )
        sub_interpreter = Interpreter(
            fs=self._fs,
            commands=self._commands,
            limits=self._limits,
            state=new_state,
        )

        # Execute statements in subshell
        stdout = ""
        stderr = ""
        exit_code = 0
        try:
            for stmt in node.body:
                result = await sub_interpreter.execute_statement(stmt)
                stdout += result.stdout
                stderr += result.stderr
                exit_code = result.exit_code
        except ExitError as e:
            # exit inside a subshell only exits the subshell
            stdout += e.stdout
            stderr += e.stderr
            exit_code = e.exit_code

        result = _result(stdout, stderr, exit_code)

        # Process output redirections on the subshell
        if node.redirections:
            result = await self._process_output_redirections(node.redirections, result)

        return result

    async def _execute_group(self, node: GroupNode, stdin: str) -> ExecResult:
        """Execute a command group { ... }."""
        # Groups execute in the current shell context
        stdout = ""
        stderr = ""
        exit_code = 0

        # Save and set group stdin
        saved_group_stdin = self._state.group_stdin
        if stdin:
            self._state.group_stdin = stdin

        try:
            for stmt in node.body:
                result = await self.execute_statement(stmt)
                stdout += result.stdout
                stderr += result.stderr
                exit_code = result.exit_code
        finally:
            self._state.group_stdin = saved_group_stdin

        result = _result(stdout, stderr, exit_code)

        # Process output redirections on the group
        if node.redirections:
            result = await self._process_output_redirections(node.redirections, result)

        return result

    async def _execute_function_def(self, node: FunctionDefNode) -> ExecResult:
        """Execute a function definition."""
        # Store the function in state
        self._state.functions[node.name] = node
        return _ok()

    async def _execute_conditional(self, node: ConditionalCommandNode) -> ExecResult:
        """Execute a conditional command [[ ... ]]."""
        if node.expression is None:
            return _result("", "", 0)

        try:
            result = await evaluate_conditional(self._ctx, node.expression)
            return _result("", "", 0 if result else 1)
        except ValueError as e:
            return _result("", f"bash: conditional: {e}\n", 2)

    async def _execute_arithmetic(self, node: ArithmeticCommandNode) -> ExecResult:
        """Execute an arithmetic command (( ... ))."""
        if node.expression is None:
            return _result("", "", 0)

        try:
            result = await evaluate_arithmetic(self._ctx, node.expression.expression)
            # (( expr )) returns 0 if result is non-zero, 1 if result is zero
            return _result("", "", 0 if result != 0 else 1)
        except Exception as e:
            return _result("", f"bash: arithmetic: {e}\n", 1)

    async def _execute_simple_command(
        self, node: SimpleCommandNode, stdin: str
    ) -> ExecResult:
        """Execute a simple command."""
        # Update currentLine for $LINENO
        if node.line is not None:
            self._state.current_line = node.line

        # Clear expansion state
        self._state.expansion_stderr = ""
        self._state.expansion_exit_code = None

        # Temporary assignments for command environment
        temp_assignments: dict[str, str | None] = {}

        # Handle assignments
        for assignment in node.assignments:
            name = assignment.name

            # Check for array subscript in name: a[idx]=value
            import re as _re
            _array_lhs = _re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\[(.+)\]$', name)

            # Check for array assignment
            if assignment.array:
                if assignment.append:
                    # a+=(2 3) - append to existing array
                    # Find next available index
                    from .expansion import get_array_elements as _get_elems
                    existing_elems = _get_elems(self._ctx, name)
                    next_idx = (max(i for i, _ in existing_elems) + 1) if existing_elems else 0

                    # Mark as array if not already
                    if f"{name}__is_array" not in self._state.env:
                        self._state.env[f"{name}__is_array"] = "indexed"

                    # Expand and store each new element
                    for i, elem in enumerate(assignment.array):
                        elem_value = await expand_word_async(self._ctx, elem)
                        self._state.env[f"{name}_{next_idx + i}"] = elem_value
                else:
                    # a=(1 2 3) - replace array
                    # Clear existing array elements
                    prefix = f"{name}_"
                    to_remove = [k for k in self._state.env if k.startswith(prefix) and not k.startswith(f"{name}__")]
                    for k in to_remove:
                        del self._state.env[k]

                    # Mark as array
                    self._state.env[f"{name}__is_array"] = "indexed"

                    # Expand and store each element, handling [idx]=value syntax
                    auto_idx = 0
                    for elem in assignment.array:
                        elem_value = await expand_word_async(self._ctx, elem)
                        # Check for [idx]=value syntax (from GlobPart + LiteralPart)
                        bracket_match = _re.match(r'^\[([^\]]+)\]=(.*)$', elem_value)
                        if bracket_match:
                            key = bracket_match.group(1)
                            val = bracket_match.group(2)
                            self._state.env[f"{name}_{key}"] = val
                            try:
                                auto_idx = int(key) + 1
                            except ValueError:
                                pass  # assoc array key
                        else:
                            self._state.env[f"{name}_{auto_idx}"] = elem_value
                            auto_idx += 1
                continue

            # Expand assignment value
            value = ""
            if assignment.value:
                value = await expand_word_async(self._ctx, assignment.value)

            if node.name is None:
                # Assignment-only command - set in environment
                if _array_lhs:
                    # a[idx]=value or a[idx]+=value
                    arr_name = _array_lhs.group(1)
                    subscript = _array_lhs.group(2)
                    # Mark as array if not already
                    if f"{arr_name}__is_array" not in self._state.env:
                        self._state.env[f"{arr_name}__is_array"] = "indexed"
                    if assignment.append:
                        existing = self._state.env.get(f"{arr_name}_{subscript}", "")
                        self._state.env[f"{arr_name}_{subscript}"] = existing + value
                    else:
                        self._state.env[f"{arr_name}_{subscript}"] = value
                elif assignment.append:
                    existing = self._state.env.get(name, "")
                    self._state.env[name] = existing + value
                else:
                    # Special handling for SECONDS - reset timer
                    if name == "SECONDS":
                        import time
                        try:
                            offset = int(value)
                            self._state.seconds_reset_time = time.time() - offset
                        except (ValueError, TypeError):
                            self._state.seconds_reset_time = time.time()
                    self._state.env[name] = value
            else:
                # Temporary assignment for command
                temp_assignments[name] = self._state.env.get(name)
                self._state.env[name] = value

        # If no command name, it's an assignment-only statement
        if node.name is None:
            return _ok()

        # Process redirections for heredocs and input redirections
        from ..ast.types import WordNode

        for redir in node.redirections:
            if redir.operator in ("<<", "<<-"):
                # Here-document: the target should be a HereDocNode
                target = redir.target
                if hasattr(target, 'content'):
                    # Expand content - parser handles quoted vs unquoted delimiter
                    # (quoted delimiter parses content as literal SingleQuotedPart)
                    heredoc_content = await expand_word_async(self._ctx, target.content)
                    # Strip leading tabs if <<-
                    if redir.operator == "<<-":
                        lines = heredoc_content.split("\n")
                        heredoc_content = "\n".join(line.lstrip("\t") for line in lines)
                    stdin = heredoc_content
            elif redir.operator == "<<<":
                # Here-string: expand the word and use as stdin with trailing newline
                if redir.target is not None and isinstance(redir.target, WordNode):
                    herestring_content = await expand_word_async(self._ctx, redir.target)
                    stdin = herestring_content + "\n"
            elif redir.operator == "<":
                # Input redirection: read file content into stdin
                if redir.target is not None and isinstance(redir.target, WordNode):
                    target_path = await expand_word_async(self._ctx, redir.target)
                    target_path = self._fs.resolve_path(self._state.cwd, target_path)
                    try:
                        stdin = await self._fs.read_file(target_path)
                    except FileNotFoundError:
                        return _failure(f"bash: {target_path}: No such file or directory\n")
                    except IsADirectoryError:
                        return _failure(f"bash: {target_path}: Is a directory\n")

        try:
            # Expand command name
            cmd_name = await expand_word_async(self._ctx, node.name)

            # Alias expansion (before checking functions/builtins)
            alias_args: list[str] = []
            if _is_shopt_set(self._state.env, "expand_aliases"):
                aliases = get_aliases(self._ctx)
                if cmd_name in aliases:
                    alias_value = aliases[cmd_name]
                    # Simple word splitting for alias value
                    import shlex
                    try:
                        alias_parts = shlex.split(alias_value)
                    except ValueError:
                        # Fall back to simple split if shlex fails
                        alias_parts = alias_value.split()
                    if alias_parts:
                        cmd_name = alias_parts[0]
                        alias_args = alias_parts[1:]

            # Check for function call first (functions override builtins)
            if cmd_name in self._state.functions:
                return await self._call_function(cmd_name, node.args, stdin, alias_args)

            # Check for builtins (which need InterpreterContext access)
            if cmd_name in BUILTINS:
                return await self._execute_builtin(cmd_name, node, stdin, alias_args)

            # Expand arguments with glob support
            args: list[str] = list(alias_args)  # Start with alias args
            for arg in node.args:
                expanded = await expand_word_with_glob(self._ctx, arg)
                args.extend(expanded["values"])

            # Check for expansion errors (e.g., failglob)
            if self._state.expansion_exit_code is not None:
                exit_code = self._state.expansion_exit_code
                stderr = self._state.expansion_stderr
                self._state.expansion_exit_code = None
                self._state.expansion_stderr = ""
                return _result("", stderr, exit_code)

            # Update last arg for $_
            if args:
                self._state.last_arg = args[-1]

            # Look up command
            if cmd_name in self._commands:
                cmd = self._commands[cmd_name]
                # Create command context
                from ..types import CommandContext

                ctx = CommandContext(
                    fs=self._fs,
                    cwd=self._state.cwd,
                    env=self._state.env,
                    stdin=stdin,
                    limits=self._limits,
                    exec=lambda script, opts: self._exec_fn(
                        script, opts.get("env"), opts["cwd"]
                    ),
                    get_registered_commands=lambda: list(self._commands.keys()),
                )
                result = await cmd.execute(args, ctx)
            else:
                # Command not found
                result = _failure(f"bash: {cmd_name}: command not found\n")

            # Process output redirections
            result = await self._process_output_redirections(node.redirections, result)
            return result
        finally:
            # Restore temporary assignments
            for name, old_value in temp_assignments.items():
                if old_value is None:
                    del self._state.env[name]
                else:
                    self._state.env[name] = old_value

    async def _process_output_redirections(
        self, redirections: list, result: ExecResult
    ) -> ExecResult:
        """Process output redirections after command execution."""
        from ..ast.types import RedirectionNode, WordNode

        stdout = result.stdout
        stderr = result.stderr

        # Pre-process: find the last file redirect index per fd for "last wins" semantics
        # For > or >>, last redirect per fd gets the content; earlier ones just create/truncate
        last_file_redir_for_fd: dict[int, int] = {}
        for idx, redir in enumerate(redirections):
            if not isinstance(redir, RedirectionNode):
                continue
            if redir.operator in (">", ">>"):
                fd = redir.fd if redir.fd is not None else 1
                last_file_redir_for_fd[fd] = idx
            elif redir.operator == "&>":
                last_file_redir_for_fd[1] = idx
                last_file_redir_for_fd[2] = idx

        for idx, redir in enumerate(redirections):
            if not isinstance(redir, RedirectionNode):
                continue

            # Skip heredocs and input redirections - already handled
            if redir.operator in ("<<", "<<-", "<<<", "<"):
                continue

            # Get the target path
            if redir.target is None:
                continue

            # Expand the target if it's a WordNode
            if isinstance(redir.target, WordNode):
                target_path = await expand_word_async(self._ctx, redir.target)
            else:
                continue

            try:
                fd = redir.fd if redir.fd is not None else 1  # Default to stdout

                # Check for FD duplication operators - don't resolve as path
                is_fd_dup = redir.operator in (">&", "<&")
                is_fd_target = is_fd_dup and target_path in ("0", "1", "2", "-")

                # Handle /dev/null and special device files
                if target_path in ("/dev/null", "/dev/zero"):
                    if redir.operator in (">", ">>"):
                        if fd == 1:
                            stdout = ""
                        elif fd == 2:
                            stderr = ""
                    elif redir.operator == "&>":
                        stdout = ""
                        stderr = ""
                    continue
                elif target_path in ("/dev/stdout", "/dev/stderr", "/dev/stdin"):
                    continue

                # Resolve to absolute path for file operations
                if not is_fd_target:
                    target_path = self._fs.resolve_path(self._state.cwd, target_path)

                if redir.operator == ">":
                    is_last_for_fd = last_file_redir_for_fd.get(fd) == idx
                    if is_last_for_fd:
                        # Last redirect for this fd - write content
                        if fd == 1:
                            await self._fs.write_file(target_path, stdout)
                            stdout = ""
                        elif fd == 2:
                            await self._fs.write_file(target_path, stderr)
                            stderr = ""
                    else:
                        # Not the last redirect - just create/truncate the file
                        await self._fs.write_file(target_path, "")

                elif redir.operator == ">>":
                    # Append to file
                    try:
                        existing = await self._fs.read_file(target_path)
                    except FileNotFoundError:
                        existing = ""
                    is_last_for_fd = last_file_redir_for_fd.get(fd) == idx
                    if is_last_for_fd:
                        if fd == 1:
                            await self._fs.write_file(target_path, existing + stdout)
                            stdout = ""
                        elif fd == 2:
                            await self._fs.write_file(target_path, existing + stderr)
                            stderr = ""
                    else:
                        # Not last - ensure file exists but don't write content
                        if not existing:
                            await self._fs.write_file(target_path, "")

                elif redir.operator == "&>":
                    # Redirect both stdout and stderr to file
                    await self._fs.write_file(target_path, stdout + stderr)
                    stdout = ""
                    stderr = ""

                elif redir.operator == ">&":
                    # FD duplication
                    if target_path == "2":
                        # stdout to stderr: e.g., echo foo >&2
                        if fd == 1:
                            stderr = stderr + stdout
                            stdout = ""
                    elif target_path == "1":
                        # stderr to stdout: e.g., cmd 2>&1
                        if fd == 2:
                            stdout = stdout + stderr
                            stderr = ""
                        else:
                            # fd>&1 - redirect fd to stdout
                            pass
                    elif target_path == "-":
                        # Close FD - just discard
                        pass
                    else:
                        # >&file is same as &> for fd 1
                        if fd == 1:
                            await self._fs.write_file(target_path, stdout + stderr)
                            stdout = ""
                            stderr = ""

                elif redir.operator == "2>&1":
                    # Redirect stderr to stdout
                    stdout = stdout + stderr
                    stderr = ""

            except Exception as e:
                return ExecResult(
                    stdout=stdout,
                    stderr=stderr + f"bash: {target_path}: {e}\n",
                    exit_code=1,
                )

        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=result.exit_code,
        )

    async def _call_function(
        self, name: str, args: list, stdin: str, alias_args: list[str] | None = None
    ) -> ExecResult:
        """Call a user-defined function."""
        func_def = self._state.functions[name]

        # Check call depth
        self._state.call_depth += 1
        if self._state.call_depth > self._limits.max_call_depth:
            self._state.call_depth -= 1
            raise ExecutionLimitError(
                f"function call depth exceeded ({self._limits.max_call_depth})",
                "call_depth",
            )

        # Save positional parameters
        saved_params = {}
        i = 1
        while str(i) in self._state.env:
            saved_params[str(i)] = self._state.env[str(i)]
            del self._state.env[str(i)]
            i += 1
        saved_count = self._state.env.get("#", "0")

        # Set new positional parameters (alias args first, then expanded args)
        expanded_args: list[str] = list(alias_args) if alias_args else []
        for arg in args:
            expanded = await expand_word_with_glob(self._ctx, arg)
            expanded_args.extend(expanded["values"])

        for i, arg in enumerate(expanded_args):
            self._state.env[str(i + 1)] = arg
        self._state.env["#"] = str(len(expanded_args))

        # Save and set FUNCNAME
        saved_funcname = self._state.env.get("FUNCNAME")
        self._state.env["FUNCNAME"] = name

        # Create local scope
        self._state.local_scopes.append({})

        try:
            # Execute function body (which is a CompoundCommandNode)
            try:
                result = await self.execute_command(func_def.body, stdin)
                return result
            except ReturnError as e:
                return _result(e.stdout, e.stderr, e.exit_code)
        finally:
            # Pop local scope and restore saved variables
            scope = self._state.local_scopes.pop()
            # First pass: identify arrays that need element cleanup
            # If __is_array is restored to None, the array didn't exist before
            # and we need to clean up all element keys created inside the function
            arrays_to_clean = []
            for var_name, original_value in scope.items():
                if var_name.endswith("__is_array") and original_value is None:
                    arr_name = var_name[:-len("__is_array")]
                    arrays_to_clean.append(arr_name)

            # Clean up array element keys created inside the function
            for arr_name in arrays_to_clean:
                prefix = f"{arr_name}_"
                to_remove = [
                    k for k in self._state.env
                    if k.startswith(prefix) and not k.startswith(f"{arr_name}__")
                ]
                for k in to_remove:
                    del self._state.env[k]

            # Second pass: restore all saved variables
            for var_name, original_value in scope.items():
                if original_value is None:
                    self._state.env.pop(var_name, None)
                else:
                    self._state.env[var_name] = original_value

            # Restore positional parameters
            i = 1
            while str(i) in self._state.env:
                del self._state.env[str(i)]
                i += 1
            for k, v in saved_params.items():
                self._state.env[k] = v
            self._state.env["#"] = saved_count

            # Restore FUNCNAME
            if saved_funcname is None:
                self._state.env.pop("FUNCNAME", None)
            else:
                self._state.env["FUNCNAME"] = saved_funcname

            self._state.call_depth -= 1

    async def _execute_builtin(
        self, cmd_name: str, node: SimpleCommandNode, stdin: str,
        alias_args: list[str] | None = None
    ) -> ExecResult:
        """Execute a shell builtin command.

        Builtins get direct access to InterpreterContext so they can
        modify interpreter state (env, cwd, options, etc.).
        """
        # Expand arguments with glob support (alias args first)
        args: list[str] = list(alias_args) if alias_args else []
        for arg in node.args:
            expanded = await expand_word_with_glob(self._ctx, arg)
            args.extend(expanded["values"])

        # Update last arg for $_
        if args:
            self._state.last_arg = args[-1]

        # Get the builtin handler and execute
        handler = BUILTINS[cmd_name]
        # Some builtins (like mapfile) need stdin - check signature
        import inspect
        sig = inspect.signature(handler)
        if len(sig.parameters) >= 3:
            result = await handler(self._ctx, args, stdin)
        else:
            result = await handler(self._ctx, args)

        # Process output redirections
        result = await self._process_output_redirections(node.redirections, result)
        return result
