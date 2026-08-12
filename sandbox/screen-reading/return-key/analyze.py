#!/usr/bin/env python3
"""Analyze return-key experiment: trace cursor movement and character changes."""

import sys
sys.path.insert(0, "..")

from shared import load_frames, FONT_PATTERNS


def match_pattern(candidate):
    """Match a 7-row candidate against font patterns, return (char, distance)."""
    best_char = "?"
    best_dist = 999
    for ch, pattern in FONT_PATTERNS:
        dist = 0
        for r in range(7):
            diff = candidate[r] ^ pattern[r]
            dist += diff.bit_count()
        if dist < best_dist:
            best_dist = dist
            best_char = ch
    return best_char, best_dist


def main():
    frames = load_frames("log.txt")
    print(f"Loaded {len(frames)} frames", file=sys.stderr)

    # Trace cursor movement
    print("\n=== Cursor Movement ===", file=sys.stderr)
    prev_cursor = None
    cursor_changes = []
    for meta, _sls in frames:
        if meta["cursor"] != prev_cursor:
            cursor_changes.append((meta["frame"], meta["cursor"]))
            print(f"  Frame {meta['frame']}: cursor {prev_cursor} -> {meta['cursor']}",
                  file=sys.stderr)
            prev_cursor = meta["cursor"]

    # Decode what appears at each new cursor position
    print("\n=== Characters at Cursor ===", file=sys.stderr)
    for frame_num, cursor in cursor_changes:
        # Look a few frames after each change for settled pixel data
        for meta, sls in frames:
            if meta["frame"] >= frame_num + 5 and meta["cursor"] == cursor:
                # Determine which text row the cursor is in
                text_row = cursor // 32
                char_pos = cursor % 32

                # Read 7 scanlines for this text row at the cursor position
                candidate = []
                for row in range(7):
                    sl_idx = text_row * 8 + row
                    if sl_idx < len(sls):
                        col_data = bytes.fromhex(sls[sl_idx])
                        if char_pos < len(col_data):
                            byte = col_data[char_pos]
                            val = (byte ^ meta["color"]) >> 2 & 0x1F
                            candidate.append(val)
                        else:
                            candidate.append(0)
                    else:
                        candidate.append(0)

                if all(v == 0 for v in candidate):
                    print(f"  Frame {meta['frame']}: cursor={cursor} -> [blank]",
                          file=sys.stderr)
                else:
                    ch, dist = match_pattern(candidate)
                    print(f"  Frame {meta['frame']}: cursor={cursor} -> '{ch}' (dist={dist})",
                          file=sys.stderr)
                break


if __name__ == "__main__":
    main()