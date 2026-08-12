"""Shared utilities for screen-reading experiments.

Font patterns extracted from docs/references/game/code.md, TextCharacters section.
Each character has 7 rows of 5 bits. The leftmost pixel is the most significant bit.
"""

# Reference patterns extracted from code.md (32 characters: space, A-Z, !, _, ?, .)
FONT_PATTERNS = [
    (" ", [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
    ("A", [0x04, 0x0A, 0x11, 0x11, 0x1F, 0x11, 0x11]),
    ("B", [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E]),
    ("C", [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E]),
    ("D", [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E]),
    ("E", [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F]),
    ("F", [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10]),
    ("G", [0x0F, 0x11, 0x10, 0x10, 0x13, 0x11, 0x0F]),
    ("H", [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11]),
    ("I", [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E]),
    ("J", [0x01, 0x01, 0x01, 0x01, 0x01, 0x11, 0x0E]),
    ("K", [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11]),
    ("L", [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F]),
    ("M", [0x11, 0x1B, 0x15, 0x15, 0x15, 0x11, 0x11]),
    ("N", [0x11, 0x11, 0x19, 0x15, 0x13, 0x11, 0x11]),
    ("O", [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E]),
    ("P", [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10]),
    ("Q", [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D]),
    ("R", [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11]),
    ("S", [0x0E, 0x11, 0x10, 0x0E, 0x01, 0x11, 0x0E]),
    ("T", [0x1F, 0x15, 0x04, 0x04, 0x04, 0x04, 0x04]),
    ("U", [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E]),
    ("V", [0x11, 0x11, 0x11, 0x0A, 0x0A, 0x04, 0x04]),
    ("W", [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11]),
    ("X", [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11]),
    ("Y", [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04]),
    ("Z", [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F]),
    ("!", [0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04]),
    ("_", [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F]),
    ("?", [0x0E, 0x11, 0x01, 0x06, 0x04, 0x00, 0x04]),
    (".", [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04]),
]


def load_frames(path):
    """Parse log.txt into list of (metadata, scanlines) tuples."""
    with open(path) as f:
        lines = [l.strip() for l in f]

    frames = []
    scanlines = []
    meta = None
    for line in lines:
        if line.startswith("FRAME,"):
            if meta and len(scanlines) == 32:
                frames.append((meta, list(scanlines)))
            parts = line.split(",")
            meta = {
                "frame": int(parts[1]),
                "area_start": int(parts[2]),
                "area_size": int(parts[3]),
                "cursor": int(parts[4]),
                "color": int(parts[5]),
                "display_fn": int(parts[6]),
                "pm": int(parts[7]),
            }
            scanlines = []
        elif line.startswith("DATA,"):
            parts = line.split(",", 2)
            if len(parts) >= 3:
                scanlines.append(parts[2])
    if meta and len(scanlines) == 32:
        frames.append((meta, scanlines))
    return frames


def decode_character(screen_bytes, char_offset, com_color):
    """Read 7 bytes at 32-byte intervals (one per scanline) and match against font."""
    candidate = []
    for row in range(7):
        addr = char_offset + row * 32
        if addr >= len(screen_bytes):
            return "?"
        byte = screen_bytes[addr]
        row_val = (byte ^ com_color) >> 2 & 0x1F
        candidate.append(row_val)

    best_char = "?"
    best_dist = 999

    for char, pattern in FONT_PATTERNS:
        dist = 0
        for r in range(7):
            diff = candidate[r] ^ pattern[r]
            dist += diff.bit_count()
        if dist < best_dist:
            best_dist = dist
            best_char = char

    if best_dist > 8:
        return "?"
    return best_char


def decode_text_row(screen_bytes, text_row, com_color, characters_per_row=32):
    """Decode one text row. text_row 0 = first row in the command area."""
    start_byte = text_row * 8 * characters_per_row
    result = []
    for col in range(characters_per_row):
        ch = decode_character(screen_bytes, start_byte + col, com_color)
        result.append(ch)
    return "".join(result)


def decode_frame(screen_bytes, com_size, com_color):
    """Decode all 32 character positions in the first text row. Legacy wrapper."""
    return decode_text_row(screen_bytes, 0, com_color, min(com_size, 32))
