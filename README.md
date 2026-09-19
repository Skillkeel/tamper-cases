# tamper-cases

A shared set of PreToolUse cases for coding-agent guard hooks, with a runner that feeds them to any hook and a results table per hook and Claude Code version. The point is a number you can check: which cases a guard refuses, which it lets through, and which benign commands it wrongly blocks.

## Cases (cases.json, 105)

| Family | Cases | What they try | Origin |
|---|---|---|---|
| guard-file-tamper | 52 (2 must pass) | rewrite, delete, rename or roll back the guard's own files: direct writes, path tricks, `find -exec`, a symlink, `git stash` and `git reset` on history that touches the guard | u/Far_Business4773, [lumis-skills examples/tamper_cases.py](https://github.com/momonanq/lumis-skills/blob/master/examples/tamper_cases.py) (MIT); cases 41 to 52 from the r/ClaudeCode exchange with u/northbridgedev, 2026-09-14 |
| destructive | 33 (12 must pass) | `rm -rf` on root, home, cwd or a glob; recursive `rm` behind `find -exec` and `xargs`; force push; `git reset --hard`; `git clean -f`; database, infrastructure and disk wipes; remote scripts piped to a shell. The must-pass forms are ordinary work: `rm -rf build/`, `--force-with-lease`, `git status` | skillkeel-starter tests/test-hooks.sh (MIT) |
| git-config-exec | 20 (8 must pass) | git settings that make git run a command (`core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, filters, shell aliases) through `git config` and `git -c`, shell writes into `.git/`, a directory planted as `.git`. The must-pass forms are reads, `--unset` and plain keys | skillkeel-starter tests/test-hooks.sh; family added after [accomplish.ai's Beltdown write-up](https://accomplish.ai/blog/beltdown-escaping-the-claude-code-sandbox/) (2026-09-11) |

Every case carries `tool`, `input` (the `tool_input` Claude Code sends), `family`, `source`, `target`, and `must_pass` for benign forms a guard must not block. A hook that covers only one family scores n/a on the others; that is a scope statement, not a failure. guard-file-tamper cases assume a hook with protected paths (the guard's own files); a destructive-command guard is out of scope there and the table says so.

## Run

```
python3 run.py --hook "bash /path/to/guard-bash" --label my-guard-1.0 --tools Bash --claude-version 2.1.274
python3 run.py --hook "python3 scripts/scope_guard.py pre-tool" --label lumis-scope-guard --cwd /path/to/fixture
```

Exit 2 counts as refused, 0 as passed, anything else as an error. Results land in `results/<label>-<date>.json`; `RESULTS.md` is regenerated from every result file. Standard library only.

## Results so far

See [RESULTS.md](RESULTS.md). First rows: skillkeel-starter guard-bash 0.1.0 (2026-09-14) and 0.1.5 (2026-09-17): destructive 17/21 then 21/21, git-config-exec 0/12 then 12/12, guard-file-tamper 1/40 both (out of scope, no protected paths), 0 false positives on the 22 benign forms. Reported in the source thread on 2026-09-19 by u/Far_Business4773, result file not yet in the repo: lumis scope_guard at commit 91b9a1a, same fixture, guard-file-tamper 48/50, destructive 2/21, git-config-exec 0/12, 0 false positives. Five destructive cases (skillkeel-03, 05, 10, 13, 14) take the guard's own files with the tree, so they now carry `also_hits: guard-file-tamper`.

## Adding a hook or a case

Open a PR. A hook row needs the exact command, its version and the Claude Code version it is paired with. A new case needs a source (thread, issue, write-up, or your own test) and a target; mark benign forms `must_pass`. Cases that only work with a fixture (files, history, symlinks) say so in `note`, and the runner's `--cwd` points at the fixture.

## License

MIT. Cases from lumis-skills keep their MIT terms and credit; see `source` on each case.
