# just-bash-py (pre-release)

[![PyPI version](https://badge.fury.io/py/just-bash.svg)](https://pypi.org/project/just-bash/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A pure Python bash interpreter with an in-memory virtual filesystem, designed for AI agents needing a secure, sandboxed bash environment.

This is a Python port of [just-bash](https://github.com/vercel-labs/just-bash), the emulated bash interpreter for TypeScript, from Vercel.

**This is a pre-release.** This as much a demonstration of coding agents' ability to implement software given a tight spec and high test coverage, as [discussed here](https://www.dbreunig.com/2026/01/08/a-software-library-with-no-code.html) and [here](https://github.com/dbreunig/whenwords).

## Features

- **Pure Python** - No external binaries, no WASM dependencies
- **In-memory filesystem** - Sandboxed virtual filesystem for safe execution
- **70+ commands** - grep, sed, awk, jq, curl, and more
- **Full bash syntax** - Pipes, redirections, variables, arrays, functions, control flow
- **32 shell builtins** - cd, export, declare, test, and more
- **Async execution** - Built on asyncio for non-blocking operation
- **Security limits** - Prevent infinite loops, excessive recursion, runaway execution

## Installation

```bash
pip install just-bash
```

## Quick Start

```python
from just_bash import Bash

bash = Bash()

# Simple command
result = bash.run('echo "Hello, World!"')
print(result.stdout)  # Hello, World!

# Pipes and text processing
result = bash.run('echo "banana apple cherry" | tr " " "\\n" | sort')
print(result.stdout)  # apple\nbanana\ncherry\n

# Variables and arithmetic
result = bash.run('x=5; echo $((x * 2))')
print(result.stdout)  # 10

# Arrays
result = bash.run('arr=(a b c); echo "${arr[@]}"')
print(result.stdout)  # a b c

# In-memory files
result = bash.run('echo "test" > /tmp/file.txt; cat /tmp/file.txt')
print(result.stdout)  # test
```

For async contexts, use `await bash.exec()` instead of `bash.run()`.

## Demo

Run the interactive demo to see all features in action:

```bash
python examples/demo.py
```

This demonstrates variables, arrays, control flow, pipes, text processing, JSON handling with jq, functions, and more.

## API

### Bash Class

```python
from just_bash import Bash

# Create with optional initial files
bash = Bash(files={
    "/data/input.txt": "line1\nline2\nline3\n",
    "/config.json": '{"key": "value"}'
})

# Execute commands
result = await bash.exec("cat /data/input.txt | wc -l")

# Result object
print(result.stdout)     # Standard output
print(result.stderr)     # Standard error
print(result.exit_code)  # Exit code (0 = success)
```

### Configuration Options

```python
bash = Bash(
    files={...},           # Initial filesystem contents
    env={...},             # Environment variables
    cwd="/home/user",      # Working directory
    network_enabled=False, # Enable/disable network (curl)
)
```

## Security

- **No native execution** - All commands are pure Python implementations
- **Network disabled by default** - curl requires explicit enablement
- **Execution limits** - Prevents infinite loops and excessive resource usage
- **Filesystem isolation** - Virtual filesystem keeps host system safe
- **SQLite sandboxed** - Only in-memory databases allowed

## Supported Features

### Shell Syntax
- Variables: `$VAR`, `${VAR}`, `${VAR:-default}`, `${VAR:+alt}`, `${#VAR}`
- Arrays: `arr=(a b c)`, `${arr[0]}`, `${arr[@]}`, `${#arr[@]}`
- Arithmetic: `$((expr))`, `((expr))`, increment/decrement, ternary
- Quoting: Single quotes, double quotes, `$'...'`, escapes
- Expansion: Brace `{a,b}`, tilde `~`, glob `*.txt`, command `$(cmd)`
- Control flow: `if/then/else/fi`, `for/do/done`, `while`, `until`, `case`
- Functions: `func() { ... }`, local variables, return values
- Pipes: `cmd1 | cmd2 | cmd3`
- Redirections: `>`, `>>`, `<`, `2>&1`, here-docs

### Parameter Expansion
- Default values: `${var:-default}`, `${var:=default}`
- Substring: `${var:offset:length}`
- Pattern removal: `${var#pattern}`, `${var##pattern}`, `${var%pattern}`, `${var%%pattern}`
- Replacement: `${var/pattern/string}`, `${var//pattern/string}`
- Case modification: `${var^^}`, `${var,,}`, `${var^}`, `${var,}`
- Length: `${#var}`, `${#arr[@]}`
- Indirection: `${!var}`, `${!prefix*}`, `${!arr[@]}`
- Transforms: `${var@Q}`, `${var@a}`, `${var@A}`

### Conditionals
- Test command: `[ -f file ]`, `[ "$a" = "$b" ]`
- Extended test: `[[ $var == pattern ]]`, `[[ $var =~ regex ]]`
- Arithmetic test: `(( x > 5 ))`
- File tests: `-e`, `-f`, `-d`, `-r`, `-w`, `-x`, `-s`, `-L`
- String tests: `-z`, `-n`, `=`, `!=`, `<`, `>`
- Numeric tests: `-eq`, `-ne`, `-lt`, `-le`, `-gt`, `-ge`

## Shell Builtins

```
:         .         [         alias     break     builtin   cd        command
continue  declare   eval      exec      exit      export    false     let
local     mapfile   readarray readonly  return    set       shift     shopt
source    test      true      type      typeset   unalias   unset     wait
```

## Available Commands

### File Operations
```
cat       chmod     cp        find      ln        ls        mkdir     mv
rm        stat      touch     tree
```

### Text Processing
```
awk       column    comm      cut       diff      expand    fold      grep
egrep     fgrep     head      join      nl        od        paste     rev
rg        sed       sort      split     strings   tac       tail      tee
tr        unexpand  uniq      wc
```

### Data Processing
```
jq        yq        xan       sqlite3
```

### Path Utilities
```
basename  dirname   pwd       readlink  which
```

### Compression & Encoding
```
base64    gzip      gunzip    zcat      md5sum    sha1sum   sha256sum tar
```

### System & Environment
```
alias     clear     date      du        echo      env       expr      false
file      help      history   hostname  printenv  printf    read      seq
sleep     timeout   true      unalias   xargs
```

### Network
```
curl      (disabled by default)
```

### Shell
```
bash      sh
```

## License

Apache 2.0

## Acknowledgments

This project is a Python port of [just-bash](https://github.com/vercel-labs/just-bash) by Vercel. The TypeScript implementation provided the design patterns, test cases, and feature specifications that guided this Python implementation.
