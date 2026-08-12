#!/usr/bin/env python3
"""Analyze pull-left-torch experiment: decode screen buffer and find 'PULL LEFT TORCH'."""

import sys
sys.path.insert(0, "..")

from shared import load_frames, decode_text_row


def main():
    frames = load_frames("log.txt")
    print(f"Loaded {len(frames)} frames", file=sys.stderr)

    target = "PULL LEFT TORCH"
    best_score = 0
    best_frame = None
    best_text = ""

    for meta, sls in frames:
        screen_hex = "".join(sls)
        if len(screen_hex) < 10:
            continue

        if meta["pm"] != 255:
            continue

        screen_bytes = bytes.fromhex(screen_hex)
        for text_row in range(4):
            text = decode_text_row(screen_bytes, text_row, meta["color"], 32)

            score = 0
            for i, expected in enumerate(target):
                if i < len(text) and text[i] == expected:
                    score += 1

            if score > best_score:
                best_score = score
                best_frame = meta["frame"]
                best_text = text

            if score >= len(target) - 3:
                print(f"  Near match at frame {meta['frame']} row {text_row}: '{text[:40]}'",
                      file=sys.stderr)

    print(f"\nBest: frame {best_frame}, score {best_score}/{len(target)}", file=sys.stderr)
    print(f"  '{best_text[:40]}'", file=sys.stderr)

    if best_frame:
        print(f"\n=== Frames around frame {best_frame} ===", file=sys.stderr)
        for meta, sls in frames:
            if abs(meta["frame"] - best_frame) <= 3:
                screen_hex = "".join(sls)
                if len(screen_hex) < 10:
                    continue
                screen_bytes = bytes.fromhex(screen_hex)
                for text_row in range(4):
                    text = decode_text_row(screen_bytes, text_row, meta["color"], 32)
                    if any(c != " " for c in text):
                        print(f"  Frame {meta['frame']} row {text_row}: '{text[:40]}'",
                              file=sys.stderr)


if __name__ == "__main__":
    main()