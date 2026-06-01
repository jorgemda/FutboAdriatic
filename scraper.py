import requests
import json
import re

URL = "https://eadriaticleague2.leaguerepublic.com/index.html"
PAIRS_FILE = "data.json"

def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "text/html,application/xhtml+xml",
    }
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_matches(html):
    matches = []
    current_time = None
    current_section = None

    for line in html.split("\n"):
        line = line.strip()

        # Detect section
        if re.match(r"FC26 R\d+", line):
            current_section = "skip" if ("LA LIGA" in line or "FRIENDLY" in line) else line
        elif "FC26 SEASON 7" in line:
            current_section = "skip"

        # Detect time
        t = re.search(r"\|\s*(\d{2}:\d{2})\s*\|", line)
        if t:
            current_time = t.group(1)

        # Detect match row
        if current_time and current_section != "skip":
            players = re.findall(r"\[([^(]+)\(([^)]+)\)\]", line)
            if len(players) >= 2:
                p1 = players[0][1].strip()
                p2 = players[1][1].strip()
                pending = "vs" in line.lower()
                matches.append({
                    "time": current_time,
                    "p1": p1,
                    "p2": p2,
                    "pending": pending
                })

    return matches

def build_schedule(matches, pairs_data):
    def pk(a, b):
        return "|".join(sorted([a, b]))

    PAIRS = pairs_data.get("P", {})
    schedule = []
    seen = set()

    for m in matches:
        p1, p2 = m["p1"], m["p2"]
        key = f"{m['time']}_{min(p1,p2)}_{max(p1,p2)}"
        if key in seen:
            continue
        seen.add(key)

        k = pk(p1, p2)
        d = PAIRS.get(k)

        if d:
            dp1 = d.get("p1")
            u1_2 = d.get("u1_2") if dp1 == p1 else d.get("u2_2")
            u2_2 = d.get("u2_2") if dp1 == p1 else d.get("u1_2")
            o45 = d.get("o45", 0) or 0
            o55 = d.get("o55", 0) or 0
            vals = [x for x in [u1_2, u2_2] if x is not None]
            best = max(vals) if vals else 0
            best_dir = p1 if u1_2 == best else p2
        else:
            u1_2 = u2_2 = None
            o45 = o55 = best = 0
            best_dir = p1

        schedule.append({
            "time": m["time"], "p1": p1, "p2": p2,
            "pending": m["pending"],
            "o45": o45, "o55": o55,
            "u_p1_2": u1_2, "u_p2_2": u2_2,
            "best_u2": best, "best_dir": best_dir,
            "dnb2_ok": bool(best and best >= 88),
            "o45_ok": bool(o45 and o45 >= 78),
            "interesting": bool((best and best >= 88) or (o45 and o45 >= 78))
        })

    return sorted(schedule, key=lambda x: x["time"])

def main():
    print(f"Fetching {URL}...")
    html = fetch_page()
    print(f"Got {len(html)} chars")

    matches = parse_matches(html)
    print(f"Parsed {len(matches)} matches")

    with open(PAIRS_FILE) as f:
        data = json.load(f)

    schedule = build_schedule(matches, data)
    pending = sum(1 for m in schedule if m["pending"])
    print(f"Schedule: {len(schedule)} entries, {pending} pending")

    data["S"] = schedule

    with open(PAIRS_FILE, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    print("Updated data.json successfully")

if __name__ == "__main__":
    main()
