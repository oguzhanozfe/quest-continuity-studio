"""Check reachability of quest objectives with explicit, reversible boolean flags."""

from collections import deque
import json

TITLE = "Quest Continuity Studio"
DESCRIPTION = "Explore quest flags and prerequisites, then export approved shortest playthrough proofs."
PROMPT = "Explain which goals are reachable, citing actual transitions and the initial state. For unreachable goals distinguish a missing flag from mutually incompatible prerequisites. Do not invent new transitions."


def rows(data, key, limit=250, empty=False):
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, list) or len(value) > limit or (not value and not empty):
        raise ValueError(
            f"{key} must be a list with {'0' if empty else '1'} to {limit} entries"
        )
    if any(not isinstance(entry, dict) for entry in value):
        raise ValueError(f"Every {key} entry must be an object")
    return value


def text(value, name, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonblank text, at most {limit} characters")
    return value.strip()


def selected(evidence, approved):
    by_id = {c["id"]: c for c in evidence["candidates"]}
    result = []
    seen = set()
    for item in approved:
        key = item.get("id") if isinstance(item, dict) else None
        if not isinstance(key, str) or key not in by_id or key in seen:
            raise ValueError("Unknown or duplicate approval")
        seen.add(key)
        result.append(by_id[key])
    return result


def prepare(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Expected an object")
    flags = data.get("flags")
    if not isinstance(flags, list) or not 1 <= len(flags) <= 12:
        raise ValueError("Declare 1 to 12 flags")
    flags = [text(f, "flag", 60) for f in flags]
    if len(set(flags)) != len(flags):
        raise ValueError("Flag names must be unique")
    bit = {flag: 1 << i for i, flag in enumerate(flags)}

    def mask(values):
        if not isinstance(values, list) or any(
            not isinstance(v, str) or v not in bit for v in values
        ):
            raise ValueError("Flag list contains an undeclared flag")
        return sum(bit[v] for v in set(values))

    def names(state):
        return [f for f in flags if state & bit[f]]

    def cond(entry):
        yes, no = mask(entry.get("requires", [])), mask(entry.get("forbids", []))
        if yes & no:
            raise ValueError("Cannot both require and forbid the same flag")
        return yes, no

    start = mask(data.get("initial", []))
    actions = []
    records = []
    ids = set()
    for a in rows(data, "actions", 80, empty=True):
        key = text(a.get("id"), "action id", 80)
        yes, no = cond(a)
        add, remove = mask(a.get("set", [])), mask(a.get("clear", []))
        if key in ids or add & remove:
            raise ValueError("Duplicate action or conflicting effects")
        ids.add(key)
        actions.append((key, yes, no, add, remove))
        records.append(
            {
                "id": "action:" + key,
                "requires": names(yes),
                "forbids": names(no),
                "set": names(add),
                "clear": names(remove),
            }
        )
    parent = {start: None}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for key, yes, no, add, remove in actions:
            if state & yes != yes or state & no:
                continue
            nxt = (state | add) & ~remove
            if nxt not in parent:
                parent[nxt] = (state, key)
                queue.append(nxt)
    records.append(
        {"id": "initial", "state": names(start), "reachable_states": len(parent)}
    )
    candidates = []
    goal_ids = set()
    for g in rows(data, "goals", 80):
        gid = text(g.get("id"), "goal id", 80)
        if gid in goal_ids:
            raise ValueError("Goal IDs must be unique")
        goal_ids.add(gid)
        yes, no = cond(g)
        match = next((s for s in parent if s & yes == yes and not s & no), None)
        rec = {
            "id": "goal:" + gid,
            "goal": gid,
            "requires": names(yes),
            "forbids": names(no),
            "reachable": match is not None,
        }
        records.append(rec)
        if match is None:
            nearest = min(parent, key=lambda s: ((yes & ~s) | (no & s)).bit_count())
            rec.update(
                nearest_state=names(nearest),
                missing=names(yes & ~nearest),
                forbidden_present=names(no & nearest),
            )
            continue
        steps = []
        state = match
        while parent[state] is not None:
            before, act = parent[state]
            steps.append(
                {"action": act, "before": names(before), "after": names(state)}
            )
            state = before
        steps.reverse()
        rec["steps"] = len(steps)
        refs = list(
            dict.fromkeys(
                ["initial", rec["id"]] + ["action:" + step["action"] for step in steps]
            )
        )
        candidates.append(
            {
                "id": "proof:" + gid,
                "action": "Export playthrough for " + gid,
                "evidence_ids": refs,
                "goal": gid,
                "initial": names(start),
                "final": names(match),
                "steps": steps,
            }
        )
    return {
        "summary": f"{len(candidates)} of {len(goal_ids)} goals are reachable across {len(parent)} distinct states.",
        "metrics": {
            "Reachable states": len(parent),
            "Goals": len(goal_ids),
            "Reachable goals": len(candidates),
        },
        "records": records,
        "candidates": candidates,
    }


def export(data, evidence, approved):
    proofs = [
        {k: c[k] for k in ("goal", "initial", "final", "steps")}
        for c in selected(evidence, approved)
    ]
    graph = ["digraph playthroughs {", "  rankdir=LR;"]
    for n, p in enumerate(proofs):
        graph.append(f"  subgraph cluster_{n} {{")
        graph.append("    label=" + json.dumps(p["goal"]) + ";")
        states = [p["initial"]] + [s["after"] for s in p["steps"]]
        for i, state in enumerate(states):
            graph.append(
                f"    g{n}s{i} [label="
                + json.dumps(", ".join(state) or "(empty)")
                + "];"
            )
        for i, step in enumerate(p["steps"]):
            graph.append(
                f"    g{n}s{i} -> g{n}s{i + 1} [label="
                + json.dumps(step["action"])
                + "];"
            )
        graph.append("  }")
    graph.append("}")
    return {
        "playthrough-proofs.json": json.dumps({"goals": proofs}, indent=2) + "\n",
        "playthroughs.dot": "\n".join(graph) + "\n",
    }
