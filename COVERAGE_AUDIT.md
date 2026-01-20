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

## Text Processing Commands

### printf
- Missing flags: `-v var` (assign to variable)

### strings
- Missing flags: `-e ENCODING` (encoding selection)

---

## Complex/Special Commands

### curl
- Missing functionality:
  - `--max-redirs NUM` - redirect limit
  - Full cookie handling (`-b`, `-c`, `--cookie-jar`)
  - Notes: Overall less complete than TypeScript

### find
- Status: **COMPREHENSIVE** - Core predicates and actions implemented
- Note: `-user` / `-group` intentionally not implemented (not applicable in virtual filesystem)

### rg (ripgrep)
- Status: **COMPREHENSIVE** - Most common flags implemented
- Missing flags:
  - `-z` (--search-zip) - search compressed files
  - `--include-zero` - show files with 0 matches in count mode

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

---

## Summary by Severity

### HIGH PRIORITY (commonly used, significant gaps)
1. **tar** - Very limited (only basic c/x/t/f/z/v/C)
2. **test command** - Entirely missing

### MEDIUM PRIORITY (useful features missing)
1. **curl** - Incomplete cookie/header handling
2. **gzip** - Missing list, test, recursive
3. **timeout** - Missing kill-after, signal
4. **env** - Can't execute commands with modified env

### LOW PRIORITY (nice to have)
1. **printf** - Variable assignment (`-v var`)
2. **strings** - Encoding selection (`-e`)

### RECENTLY COMPLETED (moved from missing)
1. **grep** - `-P` (Perl regex) now implemented
2. **sort** - `-c`, `-h`, `-M`, `-V`, `-d` all implemented
3. **uniq** - `-D`, `-s`, `-w`, `-f` all implemented
4. **wc** - `-L` (max line length) implemented
5. **join** - `-i`, `-e` implemented
6. **tac** - `-b`, `-r`, `-s` flags implemented
7. **sed** - `=`, `r`, `w`, `l`, `F`, `R` commands implemented
8. **split** - `-n CHUNKS` (split into N equal parts) implemented
9. **jq** - `-j`, `-S`, `--tab`, `-a` output formatting flags implemented

---

## Next Steps

1. Decide which gaps are most critical for your use case
2. Prioritize implementations based on actual usage patterns
3. Consider adding tests FIRST for desired functionality (TDD)
4. Implement missing features incrementally
