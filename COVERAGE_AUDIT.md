# Command Coverage Audit: just-bash TypeScript vs Python Port

## Overview

Systematic comparison of the original TypeScript `just-bash` implementation against the Python port to identify missing functionality that silently fails.

---

## Completely Missing Commands in Python

These commands exist in TypeScript but have NO implementation in Python:

- **alias** - shell alias management
- **clear** - clear terminal screen
- **history** - command history
- **html-to-markdown** - HTML to Markdown conversion
- **search-engine** - search functionality
- **test** - conditional test command (`[`, `test`)

---

## Recently Implemented

### File/Directory Utilities Parity (ls, stat, file)
- Status: **COMPLETED**
- Changes:
  - **ls**: Added `-A` (almost-all), `-S` (sort by size), `-t` (sort by time)
  - **stat**: Added `%u` (UID), `%U` (username), `%g` (GID), `%G` (groupname) format specifiers
  - **file**: Comprehensive magic byte detection (ELF, Mach-O, SQLite, etc.), expanded extension map, enhanced shebang detection
  - **touch**: Fixed to actually update mtime for existing files
- Tests: 28 new tests added

### query-engine (Internal Module)
- Status: **FULLY IMPLEMENTED**
- Location: `src/just_bash/query_engine/`
- Features:
  - Full jq expression parser with proper operator precedence
  - Multi-value evaluation semantics (pipe, comma, iterators)
  - 100+ builtin functions across 6 categories:
    - Core: `keys`, `values`, `length`, `type`, `empty`, `first`, `last`, `nth`, `range`
    - Array: `sort`, `sort_by`, `unique`, `unique_by`, `flatten`, `add`, `select`, `map`, `group_by`, `min`, `max`
    - String: `split`, `join`, `test`, `match`, `sub`, `gsub`, `trim`, `startswith`, `endswith`
    - Math: `floor`, `ceil`, `sqrt`, `log`, `exp`, `sin`, `cos`, `tonumber`, `tostring`
    - Path: `getpath`, `setpath`, `del`, `paths`, `has`, `contains`, `to_entries`, `from_entries`
    - Format: `@base64`, `@uri`, `@csv`, `@json`, `@html`, `@sh`
  - Advanced features: variable binding, conditionals, try-catch, reduce, foreach, update operators
- Used by: jq, yq commands
- Tests: 120+ unit tests + 26 integration tests

---

## File/Directory Utilities

### ls
- Status: **AT PARITY** with TypeScript
- Supports: `-a`, `-A`, `-l`, `-1`, `-R`, `-h`, `-d`, `-F`, `-r`, `-S`, `-t`

### stat
- Status: **AT PARITY** with TypeScript
- Supports format specifiers: `%n`, `%s`, `%F`, `%a`, `%A`, `%u`, `%U`, `%g`, `%G`

### file
- Status: **AT PARITY** with TypeScript
- Supports: Magic byte detection (PNG, GIF, JPEG, PDF, ZIP, gzip, bzip2, ELF, Mach-O, SQLite, RAR, 7z, MP3, FLAC, Ogg, HTML, XML)
- Supports: Extension-based detection for 30+ file types
- Supports: Shebang detection with `/usr/bin/env` handling
- Supports: Empty file detection, MIME type output (`-i`)

### ln
- Missing flags: `-n` (--no-dereference)
- Notes: Flag accepted but not implemented in TypeScript either

### pwd
- Missing flags: `-L` (logical), `-P` (physical)
- Notes: Ignored in both implementations (appropriate for virtual FS)

### cat, cp, mv, rm, mkdir, touch, chmod, head, tail, tee, diff, du, tree, basename, dirname, readlink
- Status: Functionally equivalent or Python has MORE features

---

## Text Processing Commands

### grep
- Missing flags: `-P` (--perl-regexp)
- Notes: Perl regex patterns are parsed but not functional

### sed
- Missing commands:
  - `c\` (change) - incomplete multi-line handling
  - `l` (list with escapes) - not implemented
  - `F` (print filename) - not implemented
  - `=` (print line number) - not implemented
  - `b [label]` branch - incomplete
  - `t [label]` branch on substitute - incomplete
  - `T [label]` branch on no substitute - incomplete
  - `:` label definitions - not fully supported
  - `r` and `w` file I/O commands - not fully working
  - `R` (read one line from file) - not implemented

### sort
- Missing flags:
  - `-c` (--check) - check if sorted
  - `-h` (--human-numeric-sort) - compare 2K, 1G, etc.
  - `-M` (--month-sort) - month sorting
  - `-V` (--version-sort) - natural version sorting
  - `-d` (--dictionary-order) - blanks and alphanumeric only

### uniq
- Missing flags:
  - `-D` - print all duplicate lines
  - `-s N` (--skip-chars) - skip first N characters
  - `-w N` (--check-chars) - compare only N characters
  - `-f N` (--skip-fields) - skip first N fields

### wc
- Missing flags: `-L` (--max-line-length)

### join
- Missing flags:
  - `-i` (ignore case)
  - `-e STRING` (replace missing fields)

### printf
- Missing flags: `-v var` (assign to variable)

### split
- Missing flags: `-n CHUNKS` (split into N equal chunks)

### strings
- Missing flags: `-e ENCODING` (encoding selection)

### tac
- Notes: Python ignores options silently

### cut, tr, fold, nl, paste, expand, column, comm, rev, od, echo, expr, seq
- Status: Functionally equivalent or minor differences

---

## Complex/Special Commands

### jq
- Status: **SIGNIFICANTLY IMPROVED** - Now uses shared query-engine module
- Implemented features:
  - Full recursive descent parser with proper precedence
  - 100+ builtin functions (keys, values, select, map, sort_by, group_by, etc.)
  - Variable binding (`as $var`)
  - Conditionals (`if-then-elif-else-end`)
  - Try-catch error handling
  - Reduce and foreach expressions
  - Update operators (`|=`, `+=`, `-=`, etc.)
  - Alternative operator (`//`)
  - Recursive descent (`..`)
  - String interpolation
  - Format functions (`@base64`, `@uri`, `@csv`, `@json`, etc.)
- Missing flags:
  - `-j` (--join-output) - no newlines between outputs
  - `-S` (--sort-keys) - sort object keys
  - `-C` (--color) / `-M` (--monochrome) - color output
  - `--tab` - use tabs for indentation
  - `-a` (--ascii) - ASCII output

### curl
- Missing functionality:
  - `--max-redirs NUM` - redirect limit
  - Full cookie handling (`-b`, `-c`, `--cookie-jar`)
  - Notes: Overall less complete than TypeScript

### find
- Missing flags:
  - `-regex PATTERN` / `-iregex PATTERN` - regex matching
  - `-perm MODE` - permission matching
  - `-user NAME` / `-group NAME` - ownership matching
  - `-newer FILE` - partial implementation
  - `-exec CMD {} ;` - minimal handling
  - `-delete` - not fully implemented

### rg (ripgrep)
- Missing flags:
  - `-f FILE` (--file) - read patterns from file
  - `--count-matches` - count individual matches
  - `-b` (--byte-offset) - show byte offsets
  - `--vimgrep` - vimgrep format
  - `-U` (--multiline) - multiline matching
  - `-z` (--search-zip) - search compressed files
  - `--sort TYPE` - sort output
  - `--heading` - file path above matches
  - `--passthru` - print all lines
  - `--include-zero` - files with 0 matches

### tar
- Missing flags:
  - `-r` (--append) - append to archive
  - `-u` (--update) - update with newer files
  - `-a` (--auto-compress) - auto-detect compression
  - `-j` (--bzip2) / `-J` (--xz) / `--zstd` - other compressions
  - `-O` (--to-stdout) - extract to stdout
  - `-k` (--keep-old-files) - don't replace existing
  - `-m` (--touch) - don't extract modified time
  - `-p` (--preserve) - preserve permissions
  - `-T FILE` (--files-from) - read file list
  - `-X FILE` (--exclude-from) - read exclude patterns
  - `--strip=N` - strip path components
  - `--exclude=PATTERN` - exclude matching files
- Notes: Python only supports c/x/t/f/z/v/C

### gzip (in compression module)
- Missing flags:
  - `-l` (--list) - list compressed file info
  - `-n` / `-N` - (don't) save/restore filename
  - `-q` (--quiet) - suppress warnings
  - `-r` (--recursive) - recursive operation
  - `-S SUFFIX` (--suffix) - custom suffix
  - `-t` (--test) - test integrity

### yq
- Status: **IMPROVED** - Now uses shared query-engine module for jq-style filtering
- Implemented features:
  - Full jq expression support via query-engine
  - Format conversion: YAML, JSON, XML, INI, CSV, TOML
  - `-p` (--input-format) and `-o` (--output-format) supported
  - Auto-detection of format from file extension
- Missing functionality:
  - `--front-matter` - extract markdown front matter

### xan (CSV toolkit)
- Notes: Significantly reduced feature set vs TypeScript

### timeout
- Missing flags:
  - `-k DURATION` (--kill-after) - send KILL after timeout
  - `-s SIGNAL` (--signal) - specify signal
  - `--preserve-status` - preserve exit status

### xargs
- Missing flags:
  - `-P NUM` - parallel processing (silently ignored)
  - `-d` delimiter escape sequences not parsed
  - `-v` (--verbose) formatting less complete

### env
- Missing functionality:
  - Command execution with modified environment
  - Only prints environment, doesn't execute commands
  - Incomplete `-u NAME` (unset) handling

### sqlite3
- Status: EXISTS in Python (sqlite3_cmd.py)
- Notes: Needs detailed comparison for missing features

### base64, date, sleep, which, hostname, help
- Status: Functionally equivalent

---

## Summary by Severity

### HIGH PRIORITY (commonly used, significant gaps)
1. **sed** - Many commands incomplete/missing
2. **find** - Missing regex, perm, user/group, exec, delete
3. **sort** - Missing human/version/month sorting
4. **tar** - Very limited (only basic c/x/t/f/z/v/C)
5. **rg** - Missing many search options
6. **test command** - Entirely missing

### MEDIUM PRIORITY (useful features missing)
1. **grep** - No Perl regex
2. **uniq** - No field/char skipping
3. **curl** - Incomplete cookie/header handling
4. **gzip** - Missing list, test, recursive
5. **timeout** - Missing kill-after, signal
6. **env** - Can't execute commands with modified env
7. **jq** - Missing output formatting options (core functionality now complete)

### LOW PRIORITY (nice to have)
1. **wc** - Max line length
2. **join** - Ignore case
3. **printf** - Variable assignment
4. **split** - Chunk mode

---

## Next Steps

1. Decide which gaps are most critical for your use case
2. Prioritize implementations based on actual usage patterns
3. Consider adding tests FIRST for desired functionality (TDD)
4. Implement missing features incrementally
