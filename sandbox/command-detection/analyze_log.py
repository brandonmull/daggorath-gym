#!/usr/bin/env python3
"""Analyze log.txt from the command-detection sandbox."""

import sys

lines = open("log.txt").readlines()

# Find the first line with 16 fields (post-boot data)
data_start = None
for i, l in enumerate(lines):
    if l.startswith("CMD"):
        continue
    if l.startswith("RESET"):
        continue
    parts = l.strip().split(",")
    if len(parts) == 16:
        data_start = i
        break

if data_start is None:
    print("ERROR: No 16-field data lines found")
    sys.exit(1)

# Find CMD events
cmd_events = []
for i, l in enumerate(lines):
    if l.startswith("CMD"):
        parts = l.strip().split(",")
        cmd_events.append({
            "line": i,
            "frame": int(parts[1]),
            "index": int(parts[2]),
            "text": parts[3],
        })

print("=== Command Events ===")
for cmd in cmd_events:
    print(f"  Frame {cmd['frame']}: CMD#{cmd['index']} = \"{cmd['text']}\" (log line {cmd['line']})")

# Parse a 16-field data line
def parse_line(l):
    parts = l.strip().split(",")
    if len(parts) != 16:
        return None
    return {
        "frame": int(parts[0]),
        "gameMode": int(parts[1]),
        "perfectMatch": int(parts[2]),
        "foundMatch": int(parts[3]),
        "numWords": int(parts[4]),
        "inputHead": int(parts[5]),
        "inputTail": int(parts[6]),
        "displayFnLo": int(parts[7]),
        "displayFnHi": int(parts[8]),
        "whereToPrint": int(parts[9]),
        "nextToParse": int(parts[10]),
        "comStart": int(parts[11]),
        "comSize": int(parts[12]),
        "comTextCursor": int(parts[13]),
        "ringBufHex": parts[14],
        "comAreaText": parts[15],
    }

# Show context around each command
for cmd in cmd_events:
    print(f"\n=== Context around CMD#{cmd['index']} \"{cmd['text']}\" (frame {cmd['frame']}) ===")
    offsets = [-5, -3, -1, 0, 1, 3, 5, 10, 20, 40, 80, 160, 320]
    for off in offsets:
        idx = cmd["line"] + off
        if idx < 0 or idx >= len(lines):
            continue
        l = lines[idx]
        if l.startswith("CMD"):
            continue
        d = parse_line(l)
        if d is None:
            continue
        print(f"  frame {d['frame']:5d}: pf={d['perfectMatch']:3d} fm={d['foundMatch']} nw={d['numWords']} "
              f"head={d['inputHead']:2d} tail={d['inputTail']:2d} wtp={d['whereToPrint']:3d} "
              f"ntp={d['nextToParse']:5d} comStart={d['comStart']:5d} comSize={d['comSize']:3d} "
              f"cursor={d['comTextCursor']:5d}")

# Find perfectMatch 0->255 transitions
print("\n=== perfectMatch 0->255 Transitions ===")
prev_pf = None
for i in range(data_start, len(lines)):
    d = parse_line(lines[i])
    if d is None:
        continue
    if prev_pf is not None and prev_pf == 0 and d["perfectMatch"] == 255:
        # Show surrounding frames
        print(f"  Frame {d['frame']}: pf={d['perfectMatch']} fm={d['foundMatch']} "
              f"nw={d['numWords']} wtp={d['whereToPrint']} ntp={d['nextToParse']} "
              f"cursor={d['comTextCursor']} head={d['inputHead']} tail={d['inputTail']}")
        # Show the command area text
        print(f"    comAreaText: {d['comAreaText'][:200]}")
    prev_pf = d["perfectMatch"]

# Show comStart/comSize/commandAreaText at key frames
print("\n=== Command Area Summary ===")
# Show at frame ~300 (before prime), ~700 (live), ~1000 (post-CMD1), ~1400 (post-CMD2), ~2000 (post-CMD3)
key_frames = [300, 700, 1000, 1400, 2000, 3400]
for target_frame in key_frames:
    best = None
    for i in range(data_start, len(lines)):
        d = parse_line(lines[i])
        if d is None:
            continue
        if d["frame"] >= target_frame:
            best = d
            break
    if best:
        print(f"\n  Frame {best['frame']}:")
        print(f"    comStart={best['comStart']} comSize={best['comSize']} cursor={best['comTextCursor']}")
        text = best['comAreaText'][:300].replace('.', ' ')
        print(f"    text: {text}")

# Show command area text when it contains recognizable commands
print("\n=== Command Area Text When Commands Appear ===")
# After each CMD, find when the command area text first contains the command text
for cmd in cmd_events:
    search_text = cmd["text"].split()[0]  # e.g., "PULL", "USE", "MOVE"
    found = False
    for i in range(cmd["line"], min(cmd["line"] + 500, len(lines))):
        d = parse_line(lines[i])
        if d is None:
            continue
        if search_text in d["comAreaText"] and not found:
            print(f"\n  CMD#{cmd['index']} \"{search_text}\" first appears in comAreaText at frame {d['frame']}:")
            # Grab the clean text
            text = d['comAreaText'][:300]
            # Show only the readable parts (filter out hex bytes)
            import re
            readable = re.sub(r'\[[0-9A-F]{2}\]', '', text)
            print(f"    {readable}")
            found = True
            break
    if not found:
        print(f"\n  CMD#{cmd['index']} \"{search_text}\" NOT FOUND in comAreaText within 500 frames")