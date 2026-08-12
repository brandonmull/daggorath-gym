"""Screen reading — decode command-area pixels back into text.

The game draws each character with its PrintRegChar routine: it decompresses
a 5-bit font pattern into seven rows, shifts each left by 2 bits, XORs with
comColor, and writes the seven bytes at a 32-byte scanline stride. This
module reverses that arithmetic to recover the characters.

Pure Python — the font table is a constant, no MAME dependency.
"""

# Command-area geometry. The area holds 4 text rows, each 32 characters
# wide and 8 scanlines tall; a scanline is 32 bytes (one byte per character).
TEXT_ROWS = 4
CHARS_PER_ROW = 32
SCANLINES_PER_ROW = 8
PIXEL_BYTES = TEXT_ROWS * SCANLINES_PER_ROW * CHARS_PER_ROW

# Font patterns from the disassembly (docs/references/game/code.md).
# Each character has 7 rows of 5 bits; the leftmost pixel is the high bit.
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


def decode_character(pixel_block, char_offset, com_color):
    """Decode one character from a flat pixel block.

    Reads seven bytes at a 32-byte stride (one per scanline), un-XORs with
    com_color, shifts right 2, masks to 5 bits, and matches against the font.

    Args:
        pixel_block: Flat command-area pixel bytes (scanline-major order).
        char_offset: Byte offset of the character's top-left pixel.
        com_color: The command area's color XOR byte.

    Returns:
        The best-matching character, or "?" when no font entry is close.
    """
    candidate = []
    for row in range(7):
        addr = char_offset + row * CHARS_PER_ROW
        if addr >= len(pixel_block):
            return "?"
        byte = pixel_block[addr]
        candidate.append((byte ^ com_color) >> 2 & 0x1F)

    best_char = "?"
    best_distance = 999
    for char, pattern in FONT_PATTERNS:
        distance = 0
        for row in range(7):
            distance += (candidate[row] ^ pattern[row]).bit_count()
        if distance < best_distance:
            best_distance = distance
            best_char = char

    if best_distance > 8:
        return "?"
    return best_char


def decode_text_row(pixel_block, text_row, com_color, characters_per_row=CHARS_PER_ROW):
    """Decode one of the four command-area text rows.

    Args:
        pixel_block: Flat command-area pixel bytes (scanline-major order).
        text_row: Zero-based row index (0 is the first line of text).
        com_color: The command area's color XOR byte.

    Returns:
        The decoded row as a string of `characters_per_row` characters.
    """
    start_byte = text_row * SCANLINES_PER_ROW * characters_per_row
    result = []
    for col in range(characters_per_row):
        result.append(decode_character(pixel_block, start_byte + col, com_color))
    return "".join(result)


def decode_command_area(pixel_block, com_color):
    """Decode all four text rows of the command area.

    Args:
        pixel_block: Flat command-area pixel bytes (scanline-major order).
        com_color: The command area's color XOR byte.

    Returns:
        The decoded text with the four rows joined by newlines.
    """
    rows = [
        decode_text_row(pixel_block, text_row, com_color)
        for text_row in range(TEXT_ROWS)
    ]
    return "\n".join(rows)
