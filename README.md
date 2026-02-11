# just-bash-py (pre-release)

[![PyPI version](https://badge.fury.io/py/just-bash.svg)](https://pypi.org/project/just-bash/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

A pure Python bash interpreter with an in-memory virtual filesystem, designed for AI agents needing a secure, sandboxed bash environment.

This is a Python port of [just-bash](https://github.com/vercel-labs/just-bash), the emulated bash interpreter for TypeScript, from Vercel.

**This is a pre-release.** This as much a demonstration of coding agents' ability to implement software given a tight spec and high test coverage, as [discussed here](https://www.dbreunig.com/2026/01/08/a-software-library-with-no-code.html) and [here](https://github.com/dbreunig/whenwords).

## Features

- **Pure Python** - No external binaries, no WASM dependencies
- **Flexible filesystems** - In-memory, real filesystem access, copy-on-write overlays, or mount multiple sources
- **70+ commands** - grep, sed, awk, jq, curl, and more
- **Full bash syntax** - Pipes, redirections, variables, arrays, functions, control flow
- **36 shell builtins** - cd, export, declare, test, pushd, popd, and more
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
result = await bash.exec('echo "Hello, World!"')
print(result.stdout)  # Hello, World!

# Pipes and text processing
result = await bash.exec('echo "banana apple cherry" | tr " " "\\n" | sort')
print(result.stdout)  # apple\nbanana\ncherry\n

# Variables and arithmetic
result = await bash.exec('x=5; echo $((x * 2))')
print(result.stdout)  # 10

# Arrays
result = await bash.exec('arr=(a b c); echo "${arr[@]}"')
print(result.stdout)  # a b c

# In-memory files
result = await bash.exec('echo "test" > /tmp/file.txt; cat /tmp/file.txt')
print(result.stdout)  # test
```

A synchronous `bash.run()` wrapper is also available and works in any context, including Jupyter notebooks.

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
    network=NetworkConfig(...),  # Network configuration (for curl)
    unescape_html=True,    # Auto-fix HTML entities in LLM output (default: True)
)
```

### Filesystem Options

just-bash provides four filesystem implementations for different use cases:

#### InMemoryFs (Default)

Pure in-memory filesystem - completely sandboxed with no disk access.

```python
from just_bash import Bash

# Default: in-memory filesystem with optional initial files
bash = Bash(files={
    "/data/input.txt": "hello world\n",
    "/config.json": '{"key": "value"}'
})

result = await bash.exec("cat /data/input.txt")
print(result.stdout)  # hello world
```

#### ReadWriteFs

Direct access to the real filesystem, rooted at a specific directory. All paths are translated relative to the root.

```python
from just_bash import Bash
from just_bash.fs import ReadWriteFs, ReadWriteFsOptions

# Access real files under /path/to/project
fs = ReadWriteFs(ReadWriteFsOptions(root="/path/to/project"))
bash = Bash(fs=fs, cwd="/")

# /src/main.py in bash maps to /path/to/project/src/main.py on disk
result = await bash.exec("cat /src/main.py")
```

**Warning**: ReadWriteFs provides direct disk access. Use with caution.

#### OverlayFs

Copy-on-write overlay - reads from the real filesystem, but all writes go to an in-memory layer. The real filesystem is never modified.

```python
from just_bash import Bash
from just_bash.fs import OverlayFs, OverlayFsOptions

# Overlay real files at /home/user/project, changes stay in memory
fs = OverlayFs(OverlayFsOptions(
    root="/path/to/real/project",
    mount_point="/home/user/project"
))
bash = Bash(fs=fs)

# Read real files
result = await bash.exec("cat /home/user/project/README.md")

# Writes only affect the in-memory layer
await bash.exec("echo 'modified' > /home/user/project/README.md")
# Real file on disk is unchanged!
```

Use cases:
- Safe experimentation with real project files
- Testing scripts without modifying actual files
- AI agents that need to read real code but not write to disk

#### MountableFs

Mount multiple filesystems at different paths, similar to Unix mount points.

```python
from just_bash import Bash
from just_bash.fs import (
    MountableFs, MountableFsOptions, MountConfig,
    InMemoryFs, ReadWriteFs, ReadWriteFsOptions, OverlayFs, OverlayFsOptions
)

# Create a mountable filesystem with multiple sources
fs = MountableFs(MountableFsOptions(
    base=InMemoryFs(),  # Default for paths outside mounts
    mounts=[
        # Mount real project at /project (read-write)
        MountConfig(
            mount_point="/project",
            filesystem=ReadWriteFs(ReadWriteFsOptions(root="/path/to/project"))
        ),
        # Mount another project as overlay (read-only to disk)
        MountConfig(
            mount_point="/reference",
            filesystem=OverlayFs(OverlayFsOptions(
                root="/path/to/other/project",
                mount_point="/"
            ))
        ),
    ]
))

bash = Bash(fs=fs)

# Access different filesystems through unified paths
await bash.exec("ls /project")      # Real filesystem
await bash.exec("ls /reference")    # Overlay filesystem
await bash.exec("ls /tmp")          # In-memory (base)
```

#### Direct Filesystem Access

You can also access the filesystem directly through the `bash.fs` property:

```python
import asyncio
from just_bash import Bash

bash = Bash(files={"/data.txt": "initial content"})

# Async filesystem operations
async def main():
    # Read
    content = await bash.fs.read_file("/data.txt")

    # Write
    await bash.fs.write_file("/output.txt", "new content")

    # Check existence
    exists = await bash.fs.exists("/data.txt")

    # List directory
    files = await bash.fs.readdir("/")

    # Get file stats
    stat = await bash.fs.stat("/data.txt")
    print(f"Size: {stat.size}, Mode: {oct(stat.mode)}")

asyncio.run(main())
```

### HTML Escaping Compatibility

When LLMs generate bash commands, they sometimes output HTML-escaped operators:

```bash
wc -l &lt; file.txt      # LLM outputs this instead of: wc -l < file.txt
echo "done" &amp;&amp; exit  # Instead of: echo "done" && exit
```

By default, just-bash automatically unescapes these HTML entities (`&lt;` → `<`, `&gt;` → `>`, `&amp;` → `&`, `&quot;` → `"`, `&apos;` → `'`) in operator positions, so LLM-generated commands work correctly.

Entities inside quotes and heredocs are preserved:

```python
# These work as expected
await bash.exec('echo "&lt;"')  # Outputs: &lt;
await bash.exec("cat << 'EOF'\n&lt;tag&gt;\nEOF")  # Outputs: &lt;tag&gt;
```

To disable this behavior for strict bash compatibility:

```python
bash = Bash(unescape_html=False)
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
continue  declare   dirs      eval      exec      exit      export    false
hash      let       local     mapfile   popd      pushd     readarray readonly
return    set       shift     shopt     source    test      true      type
typeset   unalias   unset     wait
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

#### xan - CSV Toolkit

The `xan` command provides CSV manipulation capabilities. Most commands are implemented:

**Implemented:**
```
headers     count       head        tail        slice       select
drop        rename      filter      search      sort        reverse
behead      enum        shuffle     sample      dedup       top
cat         transpose   fixlengths  flatten     explode     implode
split       view        stats       frequency   to json     from json
```

**Not Yet Implemented** (require expression evaluation):
```
join        agg         groupby     map         transform   pivot
```

Example usage:
```python
# Show column names
await bash.exec("xan headers data.csv")

# Filter and select
await bash.exec("xan filter 'age > 30' data.csv | xan select name,age")

# Convert to JSON
await bash.exec("xan to json data.csv")

# Sample random rows
await bash.exec("xan sample 10 --seed 42 data.csv")
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

## Test Results

Test suite history per commit (spec_tests excluded). Each `█` ≈ 55 tests.

```
Commit   Date         Passed  Failed  Skipped  Graph
c816182  2026-01-25     2641       3        2  ████████████████████████████████████████████████▒░
e91d4d8  2026-01-26     2643       2        2  ████████████████████████████████████████████████▒░
ca69ff0  2026-02-04     2757       0        2  █████████████████████████████████████████████████░
6bd4810  2026-02-04     2769       0        2  █████████████████████████████████████████████████░
6c9ab28  2026-02-05     2780       0        2  ██████████████████████████████████████████████████░
aa16896  2026-02-05     2794       0        2  ██████████████████████████████████████████████████░
b6a96dd  2026-02-09     2814       0        2  ██████████████████████████████████████████████████░
a7e64a4  2026-02-11     2825       0        2  ███████████████████████████████████████████████████░
```

`█` passed · `▒` failed · `░` skipped

## License

Apache 2.0

## Backlog

Future improvements under consideration:

- **Separate sync/async implementations**: Replace the current `nest_asyncio`-based `run()` wrapper with a truly synchronous implementation. This would follow the pattern used by libraries like httpx (`Client` vs `AsyncClient`) and the OpenAI SDK, providing cleaner separation without event loop patching.

## Acknowledgments

This project is a Python port of [just-bash](https://github.com/vercel-labs/just-bash) by Vercel. The TypeScript implementation provided the design patterns, test cases, and feature specifications that guided this Python implementation.
