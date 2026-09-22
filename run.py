#!/usr/bin/env python3
"""Feed every case in cases.json to a PreToolUse hook and record what it does.

    python3 run.py --hook "bash /path/to/guard-bash" --label skillkeel-guard-bash --tools Bash
    python3 run.py --hook "python3 scripts/scope_guard.py pre-tool" --label lumis-scope-guard --cwd /path/to/fixture

Each case is sent as the JSON Claude Code sends: {"hook_event_name": "PreToolUse", "tool_name": ..., "tool_input": {...},
"session_id", "cwd", "permission_mode", "transcript_path"}. A hook answers either with its exit code (2 = refused,
0 = passed) or, on exit 0, with the JSON Claude Code reads from stdout: hookSpecificOutput.permissionDecision
"deny" = refused, "ask" = asked (the human decides; counted on its own, neither refused nor passed), "allow" = passed;
the older top-level {"decision": "block"} also counts as refused. Anything else is an error. Cases marked must_pass are
benign forms a guard must not block; a refusal there is a false positive and is listed separately. Results go to results/<label>-<date>.json and the table in
RESULTS.md is regenerated from every file under results/. Standard library only.
"""
import argparse, datetime, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = str(Path.home())


def scrub(s):
    """Result files are meant to be committed and to be handed to the author of the hook they measure, so nothing
    that identifies this machine may survive in one. Replacing $HOME was not enough: on 2026-09-22 a run driven by
    a wrapper under /tmp put the login name and the dashed home path into the `hook` field, which tools/identity_check
    flags and no git hook would have caught, because the file is written by this script rather than by an editor."""
    s = s.replace(HOME, "~")
    user = os.environ.get("USER") or os.environ.get("LOGNAME") or Path(HOME).name
    if user:
        # the dashed form is how scratch directories encode a home path: /tmp/.../-home-<user>-...
        s = re.sub(rf"-home-{re.escape(user)}[-\w./]*", "<scratch>", s)
        s = re.sub(rf"\b{re.escape(user)}\b", "<user>", s)
    # any remaining absolute path outside the repository is machine detail, not evidence
    return re.sub(r"(?<![\w/])/(?:tmp|home|Users|var/folders)/[^\s\"']*", "<path>", s)


def run(hook, cases, tools, cwd, timeout):
    rows = []
    for c in cases:
        if tools and c["tool"] not in tools:
            rows.append({"id": c["id"], "exit": None, "verdict": "n/a", "reason": f"hook does not handle {c['tool']}"}); continue
        payload = json.dumps({"hook_event_name": "PreToolUse", "session_id": "tamper-cases", "transcript_path": "",
                              "cwd": cwd or str(HERE), "permission_mode": "default", "tool_name": c["tool"], "tool_input": c["input"]})
        decision = None
        try:
            r = subprocess.run(hook, shell=True, input=payload, capture_output=True, text=True, cwd=cwd, timeout=timeout)
            code = r.returncode
            decision, reason = decision_from(r.stdout)
            if not reason:
                reason = (r.stderr.strip() or r.stdout.strip()).splitlines()[0][:120] if (r.stderr.strip() or r.stdout.strip()) else ""
        except subprocess.TimeoutExpired:
            code, reason = -1, "timeout"
        if code == 2:
            verdict = "refused"
        elif code == 0:
            verdict = {"deny": "refused", "block": "refused", "ask": "asked", "allow": "passed", None: "passed"}.get(decision, "error")
        else:
            verdict = "error"
        if c.get("must_pass") and verdict == "refused":
            verdict = "false-positive"
        rows.append({"id": c["id"], "exit": code, "decision": decision, "verdict": verdict, "reason": scrub(reason)})
    return rows


def decision_from(stdout):
    """(decision, reason) from a hook's stdout JSON: hookSpecificOutput.permissionDecision (deny|ask|allow) or the older
    top-level decision (block|approve); (None, "") when stdout is not JSON or carries no decision."""
    for line in reversed([l for l in stdout.splitlines() if l.strip()]):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        h = d.get("hookSpecificOutput") or {}
        dec = h.get("permissionDecision") or d.get("decision")
        if dec:
            return dec, str(h.get("permissionDecisionReason") or d.get("reason") or "")[:120]
    return None, ""


def summary(cases, rows):
    by = {}
    for c, r in zip(cases, rows):
        f = by.setdefault(c["family"], {"cases": 0, "harmful": 0, "refused": 0, "passed": 0, "asked": 0, "false-positive": 0, "n/a": 0, "error": 0, "must_pass_ok": 0, "must_pass": 0})
        f["cases"] += 1; f[r["verdict"]] += 1
        if c.get("must_pass"):
            f["must_pass"] += 1; f["must_pass_ok"] += r["verdict"] == "passed"
        elif r["verdict"] != "n/a":
            f["harmful"] += 1  # a harmful case the hook was given
    return by


def table():
    lines = ["# Results", "", "Generated by run.py from results/*.json. refused = exit 2 or a JSON deny; asked = a JSON ask (the human decides); passed = exit 0 with no deny; false-positive = a must_pass case refused; n/a = the hook does not handle that tool.", "",
             "**Read this table as coverage, not as a ranking.** A family a hook does not claim to cover is a different design, not a defect, and the note under the table says which families each hook claims. A refusal of ordinary work is counted as a false positive here even where the hook refuses it on purpose; several of these tools state that they prefer a false positive to a missed command, and that is a choice, not a fault.", "",
             "The **Config** column is what was switched on when the row was measured. A tool whose optional packs were off refused less than the same tool with them on, and that is a fact about the run rather than about the tool.", "",
             "**Whose tests these are.** Skillkeel wrote 53 of the 105 cases, they come from the skillkeel-starter hook tests, and the skillkeel-guard-bash rows below are our own hook measured against our own suite. The other 52 are lumis-skills' cases, credited per case. We publish this table and we sell Claude Code tooling, so read our own rows with that in mind; every row carries its commit, its command line and its raw JSON so you can re-run it against anything.", "",
             "| Hook | Config | Claude Code | Date | Family | Refused / harmful | Asked | Benign kept | False positives | n/a |", "|---|---|---|---|---|---|---|---|---|---|"]
    for f in sorted(HERE.glob("results/*.json")):
        d = json.loads(f.read_text())
        for fam, s in d["summary"].items():
            lines.append(f"| {d['label']} | {d.get('config') or 'default'} | {d.get('claude_version') or ''} | {d['date']} | {fam} | {s['refused']} / {s['harmful']} | {s.get('asked', 0)} | {s['must_pass_ok']} / {s['must_pass']} | {s['false-positive']} | {s['n/a']} |")
    notes = [(json.loads(f.read_text())) for f in sorted(HERE.glob("results/*.json"))]
    notes = [(d["label"], d["source"]) for d in notes if d.get("source")]
    if notes:
        lines += ["", "## How each third-party row was produced", ""] + [f"- {label}: {src}" for label, src in notes]
    extra = HERE / "results" / "NOTES.md"
    if extra.exists():
        lines += ["", extra.read_text().rstrip()]
    (HERE / "RESULTS.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", required=True, help="command that reads the PreToolUse JSON on stdin")
    ap.add_argument("--label", required=True, help="hook name for the results table, e.g. skillkeel-guard-bash-0.1.5")
    ap.add_argument("--tools", default="", help="comma list of tools the hook handles, e.g. Bash; other cases are n/a")
    ap.add_argument("--cwd", default=None, help="directory the hook runs in (a fixture repo for file-based guards)")
    ap.add_argument("--claude-version", default="", help="Claude Code version the hook is paired with, for the table")
    ap.add_argument("--timeout", type=int, default=20)
    a = ap.parse_args()
    cases = json.loads((HERE / "cases.json").read_text())["cases"]
    tools = set(a.tools.split(",")) - {""}
    rows = run(a.hook, cases, tools, a.cwd, a.timeout)
    s = summary(cases, rows)
    date = datetime.date.today().isoformat()
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{a.label}-{date}.json").write_text(json.dumps({"label": a.label, "date": date, "claude_version": a.claude_version, "hook": scrub(a.hook), "summary": s, "rows": rows}, indent=1) + "\n")
    for fam, x in s.items():
        print(f"{fam:<20} refused {x['refused']:>3} / {x['harmful']:<3}  benign kept {x['must_pass_ok']}/{x['must_pass']}  false positives {x['false-positive']}  n/a {x['n/a']}")
    for c, r in zip(cases, rows):
        if r["verdict"] in ("false-positive", "error"):
            print(f"  {r['verdict']:<14} {c['id']:<14} {c['input'].get('command') or c['input'].get('file_path')}  {r['reason']}")
    table()
    print(f"results/{a.label}-{date}.json written, RESULTS.md regenerated")


if __name__ == "__main__":
    main()
