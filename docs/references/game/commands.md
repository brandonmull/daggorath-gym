# Dungeons of Daggorath — Commands

_Extracted from the original 1982 Tandy Corporation game manual._

## Summary

The game recognizes 14 command words combined with 6 second words to form 28 valid command phrases. Commands fall into five categories:

| Category | Commands |
|----------|----------|
| Movement | MOVE, TURN, CLIMB |
| Inventory | EXAMINE, LOOK, GET, DROP, PULL, STOW |
| Combat | ATTACK, USE |
| Magic | REVEAL, INCANT |
| Cassette | ZLOAD, ZSAVE |

See [Appendix A](#appendix-a--summary-of-commands) for the full command reference and [Appendix C](#appendix-c--command-grammar) for the formal grammar.

---

## Commands

To enter commands in the Dungeon, type the desired command, with spaces between the words of multi-word commands, and press `ENTER`.

If you make a mistake in typing a command, press the ← key to erase one character at a time and continue typing the command. If you enter an illegal or impossible command, ??? appears after the command, and no action is taken.

You can enter commands in rapid succession. Simply continue typing. The computer stores the commands you type and then displays and carries them out as rapidly as possible.

Commands can be abbreviated to the shortest set of letters that cannot be confused with another command word. For example, ATTACK LEFT can be abbreviated A L, and PULL LEFT SWORD can be abbreviated P L SW. SWORD cannot be abbreviated with just an S, as this can be confused with SHIELD. You must still enter spaces between abbreviated words. If you try to enter an abbreviation that is too short, ??? appears after the command.

The appendices at the end of The Book contain a Summary of Commands (Appendix A), a Partial List of Allowable Abbreviations (Appendix B), and the commands you need to use to save and reload a game (Appendix C).

---

## Moving in the Dungeon

Enter the command MOVE to step one cell forward in the Dungeon. If you are facing a wall, you will "bump" into it. You may move past a creature that is directly in front of you by moving forward. The creature, however, will follow you and attempt to move fast enough to jump back in front of you.

To step back, type MOVE BACK. You can also turn in either direction by typing TURN LEFT or TURN RIGHT. Type TURN AROUND to turn completely around in the same cell. Use the commands MOVE LEFT or MOVE RIGHT to sidestep (move sideways without turning).

A TORCH will help you see which way to MOVE in the Dungeon. You can MOVE with no TORCH (in total darkness), but you will bump into walls. This is not a recommended method of traveling in the Dungeon, for you might bump into the dreaded creatures.

---

## Levels and Climbing in the Dungeon

The Dungeon is a multi-level maze. There are three known levels, but there are rumors that the real Wizard lives beyond in even deeper levels. If you want to explore the first three levels, you must find a hole or a ladder to move between the levels. Beyond that, you are on your own.

If you are standing next to a hole, type CLIMB DOWN. You are then on the level below and can see the hole you just climbed through directly above you. But be careful ... if you climb down a hole, you cannot go back up.

If you are standing next to a ladder, you can move up or down by using the commands CLIMB UP or CLIMB DOWN. Be especially wary of climbing up ... for it is said that if the Wizard senses you retreating up a level, he will punish your faintheartedness with the wrath of his most fearsome creatures.

---

## Creatures

The Dungeon is filled with terrible creatures, henchmen of the evil Wizard. You will encounter Vipers, Spiders, Evil Knights, the Smiling Blobs, massive Stone Giants, Scorpions, Wraiths, and the awesome Galdrogs. These demons of darkness will attempt to seek you out and destroy you. They grow more powerful and more deadly as you descend deeper into the Dungeon.

Each creature has a characteristic sound that it will sometimes make as it approaches from any direction. The sound grows louder as the creature approaches. Listen carefully in the Dungeon, for you can often tell which creature to expect from the sound you hear. If the creature is in the cell with you, the sound is very loud, and you will be attacked. You will hear the blow strike you if it finds its mark. This is extremely hazardous to your health.

If you have your wits about you, you can use the ATTACK command to fend off or destroy your attacker. Use an object (such as a SWORD) if you have one, but your empty hand is better than nothing.

One technique you might use to defeat creatures involves attacking several times in rapid succession and then moving several steps and turning around. This method lets your heart rate slow down while the creature approaches. Then you are ready to attack again as the creature enters your cell.

Creatures attack faster as they become more powerful. Time your attack to strike the creature just as it enters your cell and before it has a chance to strike you. Entering several ATTACKS followed by MOVES in rapid succession (don't wait for the command to be displayed) helps to get your blows in and gets you out of danger before the creature has a chance to destroy you.

The Blob might require ten or so successful sword hits to kill when you first encounter it. The Stone Giant might take six or seven hits to destroy. You might be able to kill Spiders with only one blow, but Vipers will take two or three.

Both the Blob and the Stone Giant can often kill you with one blow — so be quick and move before they strike!

In the Dungeon, the victor of a struggle draws strength from the defeated foe. Be cautious, but master many creatures as you move through the Dungeon so your strength may increase. The stronger you become, the fewer hits it will take to destroy a creature. If you go to a deeper level without mastering most of the creatures on the levels above, your strength will be no match for the creatures you encounter. Eventually, if you survive, you will face the evil Wizard. Defeating the Wizard will be the ultimate struggle, for his strength is greater than all his creatures.

BUT BE WARNED ... long before you face the real Wizard, he will send a demon in his image to test your worthiness and resolve. Only after defeating the Wizard's image will the true challenge begin.

BE PREPARED FOR ANYTHING!

---

## Objects

Within the Dungeon there will be a number of objects which must be used in your quest. The creatures will have collected most of the objects in the Dungeon by the time you arrive. There are six object classes:

**TORCH  SWORD  SHIELD  FLASK  SCROLL  RING**

There are several types within each of these object classes. For example, a TORCH can be a PINE TORCH or a LUNAR TORCH.

### Types of Objects

| TORCH | SWORD | SHIELD | FLASK | SCROLL |
|-------|-------|--------|-------|--------|
| PINE | WOODEN | LEATHER | HALE | VISION |
| LUNAR | IRON | BRONZE | ABYE | SEER |
| SOLAR | ELVISH | MITHRIL | THEWS | |

The types of RINGs, however, will not be listed in the chart. You must discover them yourself.

When you first enter the Dungeon, you will be given a backpack containing a PINE TORCH and a WOODEN SWORD. You can find other objects within the Dungeon and can get them when they are on the floor. At any time, you can see what objects are in your backpack and on the floor by typing EXAMINE.

You can look at the Dungeon by typing LOOK (but only after an EXAMINE command).

To grab something from your backpack, you must first have an empty hand. Then use the PULL command, as in PULL LEFT PINE TORCH. To place something you are holding into your backpack, type STOW LEFT (for left hand) or STOW RIGHT (for right hand). Your right or left hand is now empty and the object you are holding is in the backpack.

Creatures in the Dungeon are aware that objects are valuable and will gather objects they encounter as they move throughout the Dungeon. A creature will continue to carry the objects it has collected until it is destroyed. When a creature is destroyed, the objects (if any) will drop to the floor. The objects will remain where they fall, even if you leave the area, unless you pick them up or another creature comes by and picks them up. You can pick up an object from the floor using the GET command only if you have an empty hand (example: GET RIGHT SHIELD). You can drop an object to the floor from either hand by typing DROP LEFT or DROP RIGHT respectively. This leaves one hand empty, and the object you were holding now appears on the floor of the cell you occupy.

---

### Object Types

**TORCH**

No rays of light penetrate the Dungeon. You will need the TORCH to find your way. When you first enter the Dungeon, you will see only darkness. If you want to see you must PULL the TORCH into either hand and light it by typing USE LEFT or USE RIGHT. You will hear the match strike, and the TORCH will be mounted on your backpack. Your hand is now empty, and you can see. If you EXAMINE your backpack, the TORCH currently in use is highlighted. After an EXAMINE command you must LOOK to see the lit Dungeon.

In time, all TORCHes burn down and eventually die. As this happens, you can see less and less in the Dungeon. The PINE TORCH lasts fifteen minutes. The LUNAR TORCH holds some magic light and will last for thirty minutes. The SOLAR TORCH is the most powerful and lasts for sixty minutes.

It is vital that you find another TORCH before your light goes out, or you will be in pitch darkness and at the mercy of the Wizard.

**SWORD**

The Dungeon is very dangerous. Only a fool would enter without holding close his best and sharpest SWORD. When facing a creature, you can attempt to strike him with a SWORD you are holding by typing ATTACK LEFT or ATTACK RIGHT, depending on which hand your SWORD is in. If you miss, you hear the swish of your sword through the air. If you hit, you hear the blow strike and the command area shows !!! after the attack command to show that you have made contact.

Stronger creatures are naturally harder to hit. You will also find that you miss more often as the light from your torch grows dim. It becomes even more important to find other torches before your light burns too low.

As you grow stronger (if you survive), the force and effect of your blows increase. But do not expect the creatures of the Dungeon to fall from a single blow. And beware ... for even as you strike, they will strike back, often with fatal results.

**SHIELD**

When you hold a SHIELD in your hand, you are protected from some of the force of an attacking creature's blow. This may save your life! The effectiveness of a SHIELD depends somewhat on your strength and the strength of the creature you are facing.

You can also ATTACK with a SHIELD. The MITHRIL SHIELD is quite powerful and can be used effectively as a weapon. Attacking with a SHIELD is better than attacking with an empty hand and makes a great noise. But BE CAREFUL ... jokesters tend to have very short careers in the Dungeon!

**FLASK**

In the Dungeon you might also find various magical FLASKs, which may serve you in your quest. If you are holding a FLASK and type USE LEFT or USE RIGHT (depending on which hand it is in), you will pour the contents of the FLASK down your throat. Be careful ... flasks may harm you or greatly aid you. Their effects may be striking or subtle, short-lived or permanent.

You may get a clue to the nature of a FLASK from its name when you are able to REVEAL it. But the only way to really learn the true effect of a FLASK is by trying it in different situations.

**SCROLL**

It is said that in the Dungeon there are SCROLLs that may be of immeasurable value in conquering the Powers of Evil. To use a SCROLL you are holding, type USE LEFT or USE RIGHT.

**RING**

RINGs are extremely magical! They can serve as weapons of great power, and can strike down mighty enemies in a twinkling. But now that they are under a powerful magic spell that prevents their use by mere mortals.

Learn how to unleash the power of a RING in the "Magic" section.

---

## Magic

The Dungeon is a magic place. Creatures, torches, weapons and certain doors in the Dungeon have magical powers. Creatures that are very magical (like the Wizard) are best fought with magic weapons and can only be seen fully under a TORCH that throws magical light. You must learn from the Dungeon as you proceed.

There is both Physical and Magical light in the Dungeon. The PINE TORCH, for example, radiates Physical light, so certain magic passages cannot be seen. Even though you cannot see these magic passages, you can move through them. So it will appear that you can step through the walls in some places. If you have magic light the passages will appear as triangles. Other passages will appear as rectangles and can be seen in any light.

As you proceed in the Dungeon, you must find more powerful magic torches to reveal the magic doors and creatures.

### Reveal

Objects in the Dungeon often have hidden natures that are not immediately known. To discover the full power of an object, you should always attempt to REVEAL it. To REVEAL an object, you must be holding it in either hand and type REVEAL RIGHT or REVEAL LEFT, respectively. For example, you may be holding a TORCH that can be REVEALed as a more powerful LUNAR TORCH. The more powerful an object, the more strength it takes to REVEAL it. If you are unable to REVEAL an object you have found, you should save it in your backpack. After you have grown in wisdom and strength, try again to REVEAL it.

Like other objects, the full powers of a SCROLL or a RING cannot be used until you have REVEALed them.

### Incant

Only RINGs can be INCANTed. Attacking with a RING (even after you have REVEALed it) won't have much more effect than a bare-handed slap. The RING will make its magical sound, but will hold no power until it has been INCANTed. You must use your wisdom to determine the magic name of a RING. Then you must INCANT the magic name to release the RING's awesome power. The type of RING that you may REVEAL serves as a clue to the magic name of the RING. For example, if a RING is found and REVEALed to be an IRON RING, a possible incantation is to type INCANT STEEL, and press ENTER. If the incantation is correct, the RING transforms into a STEEL RING of great power. If the incantation is wrong (which it is!), nothing at all happens, and you are left to ponder the correct incantation.

After you have successfully INCANTed a RING, you can ATTACK using the RING as a magic weapon of great power. But use it wisely, for its power is not limitless, and use of a RING also puts a great strain on your heart. It is rumored that even the power of the evil Wizard is derived from a RING which he holds. If you manage to defeat the real Wizard, you must find the Wizard's RING, for it may hold the secret to your future. Remember ALL RINGs can be INCANTed.

---

## Your Heartbeat

Throughout your adventure in the Dungeon, you see and hear your heart beating as you continue the journey. Many things affect your heart rate. Moving fast or with a heavy load, swinging a SWORD or wielding a RING, being attacked and struck by a creature ... all these and more will make your heart beat more rapidly.

Time and rest, if you can find them, will bring your heart rate down. If you allow your heart rate to climb too high, you will faint. This stops you in your tracks, but alas, the creatures do not stop and will continue to track and attack you. If your heart rate climbs even further, your weary heart may simply burst, and you will have failed in your quest. The faster your heart is beating, the easier a creature's blow will kill you or cause you to faint. It is best to be rested before attempting to master a powerful creature. As you grow stronger, so will your heart, and activities which once would have killed you will become easy.

Go then, with caution, and grow in strength.

---

## Appendix A — Summary of Commands

The following summary of commands serves as a quick reference to help you remember and use the commands. Each command is presented in the following format:

> **NAME** (The name of this type of command)
>
> **Usage:** (This shows the various forms the command can take and briefly describes the effect of each form. For more detail, refer to The Book.)

Note: When the word "object" is used, you may type either an object class (like TORCH), or a specific object type (like PINE TORCH). For example, GET LEFT object refers to the whole class of commands like GET LEFT PINE TORCH, GET LEFT SWORD, and so on.

### MOVE

| Usage | Effect |
|-------|--------|
| `MOVE` | Step one cell forward |
| `MOVE BACK` | Step one cell back |
| `MOVE LEFT` | Step one cell left without turning |
| `MOVE RIGHT` | Step one cell right without turning |

### TURN

| Usage | Effect |
|-------|--------|
| `TURN LEFT` | Turn left in the current cell |
| `TURN RIGHT` | Turn right in the current cell |
| `TURN AROUND` | Turn around in the current cell |

### CLIMB

| Usage | Effect |
|-------|--------|
| `CLIMB UP` | Climb up a ladder |
| `CLIMB DOWN` | Climb down a ladder or a hole |

### EXAMINE

| Usage | Effect |
|-------|--------|
| `EXAMINE` | Show a list of objects on the floor of the cell you occupy plus a list of everything you are carrying in your backpack |

Note: Any lit TORCH is highlighted on the display.

### LOOK

| Usage | Effect |
|-------|--------|
| `LOOK` | Look at the Dungeon after an EXAMINE command |

### GET

| Usage | Effect |
|-------|--------|
| `GET LEFT object` | Get an object from the floor with your left hand |
| `GET RIGHT object` | Get an object from the floor with your right hand |

Note: The object you type must be on the floor of the cell you occupy, and the hand you choose must be empty.

### DROP

| Usage | Effect |
|-------|--------|
| `DROP LEFT` | Drop the object in your left hand (if any) to the floor |
| `DROP RIGHT` | Drop the object in your right hand (if any) to the floor |

### PULL

| Usage | Effect |
|-------|--------|
| `PULL LEFT object` | Pull an object from your backpack with your left hand |
| `PULL RIGHT object` | Pull an object from your backpack with your right hand |

Note: The object you type must be in your backpack, and the hand you choose must be empty.

### STOW

| Usage | Effect |
|-------|--------|
| `STOW LEFT` | Stow the object in your left hand (if any) into your backpack |
| `STOW RIGHT` | Stow the object in your right hand (if any) into your backpack |

### ATTACK

| Usage | Effect |
|-------|--------|
| `ATTACK LEFT` | Attack with the object in your left hand (or with your empty hand) |
| `ATTACK RIGHT` | Attack with the object in your right hand (or with your empty hand) |

### USE

| Usage | Effect |
|-------|--------|
| `USE LEFT` | Use the object in your left hand (effect depends on the object) |
| `USE RIGHT` | Use the object in your right hand (effect depends on the object) |

Note: The USE command can be used with three types of objects, and its effect varies depending on the object selected:

- **TORCH** — To USE a TORCH is to light it and mount it on your backpack
- **FLASK** — To USE a FLASK is to pour its contents down your throat
- **SCROLL** — To USE a SCROLL, the SCROLL must be REVEALed. Try it!

### REVEAL

| Usage | Effect |
|-------|--------|
| `REVEAL LEFT` | Attempt to "reveal" the type of object in your left hand |
| `REVEAL RIGHT` | Attempt to "reveal" the type of object in your right hand |

### INCANT

| Usage | Effect |
|-------|--------|
| `INCANT magic-word` | Attempt to conjure up the magic power of a RING by "incanting" its magical name |

Note: When you INCANT, type only the single word you are incanting, such as INCANT STEEL.

### Cassette Commands

| Usage | Effect |
|-------|--------|
| `ZSAVE filename` | Save the current state of the game on cassette with the filename that was typed in |
| `ZLOAD filename` | Load from cassette a game you saved earlier with the given filename |

---

## Appendix B — Partial List of Abbreviations

Commands can be abbreviated to the shortest set of letters that cannot be confused with another command. Remember that you must still enter the spaces between the abbreviated command words, and always press ENTER after typing the command. If you try an abbreviation that is too short, ??? appears after the command.

| Full Command | Shortest Abbreviation |
|-------------|----------------------|
| MOVE | M |
| MOVE BACK | M B |
| MOVE LEFT | M L |
| MOVE RIGHT | M R |
| TURN LEFT | T L |
| TURN RIGHT | T R |
| TURN AROUND | T A |
| CLIMB UP | C U |
| CLIMB DOWN | C D |
| EXAMINE | E |
| LOOK | L |
| GET LEFT TORCH | G L T |
| GET RIGHT WOODEN SWORD | G R W S W |
| DROP LEFT | D L |
| DROP RIGHT | D R |
| PULL LEFT SHIELD | P L S H |
| PULL RIGHT LEATHER SHIELD | P R L E S H |
| STOW LEFT | S L |
| STOW RIGHT | S R |
| ATTACK LEFT | A L |
| ATTACK RIGHT | A R |
| USE LEFT | U L |
| USE RIGHT | U R |
| REVEAL LEFT | R L |
| REVEAL RIGHT | R R |
| INCANT STEEL | I S T E E L |

---

## Appendix C — Command Grammar

Commands follow a fixed phrase structure. The game stores a table of **first words** and a table of **second words** in ROM. The parser decodes the first word typed, dispatches to a command handler, and the handler may parse additional words from the second-word table or proper-name table as needed.

### Formal Grammar

```
<command>      ::= <first-word> [<second-word> | <object-spec>] [<object-spec>]
                 | INCANT <proper-name>

<first-word>   ::= ATTACK | CLIMB | DROP | EXAMINE | GET | INCANT | LOOK
                 | MOVE | PULL | REVEAL | STOW | TURN | USE | ZLOAD | ZSAVE

<second-word>  ::= LEFT | RIGHT | BACK | AROUND | UP | DOWN

<object-spec>  ::= <proper-name> <class-name>
                 | <class-name>

<proper-name>  ::= any entry from the Proper Names table (Appendix D)

<class-name>   ::= FLASK | RING | SCROLL | SHIELD | SWORD | TORCH
```

### Second Words

Second words qualify the first word (which hand, which direction). The table at ROM `D8D9` defines six second words:

| Token | Word |
|-------|------|
| 00 | LEFT |
| 01 | RIGHT |
| 02 | BACK |
| 03 | AROUND |
| 04 | UP |
| 05 | DOWN |

Which second words are valid depends on the command:

| Command | Allowed Second Words |
|---------|---------------------|
| ATTACK | LEFT, RIGHT |
| CLIMB | UP, DOWN |
| DROP | LEFT, RIGHT |
| GET | LEFT, RIGHT |
| MOVE | _(none—or BACK, LEFT, RIGHT)_ |
| PULL | LEFT, RIGHT |
| REVEAL | LEFT, RIGHT |
| STOW | LEFT, RIGHT |
| TURN | LEFT, RIGHT, AROUND |
| USE | LEFT, RIGHT |

Commands that take no second word: EXAMINE, INCANT, LOOK, ZLOAD, ZSAVE.

### Command Templates

Each command expects a specific phrase structure. Object specifiers can be abbreviated (see Appendix B).

| Command | Template |
|---------|----------|
| ATTACK | `ATTACK LEFT` \| `ATTACK RIGHT` |
| CLIMB | `CLIMB UP` \| `CLIMB DOWN` |
| DROP | `DROP LEFT` \| `DROP RIGHT` |
| EXAMINE | `EXAMINE` |
| GET | `GET LEFT <object>` \| `GET RIGHT <object>` |
| INCANT | `INCANT <proper-name>` |
| LOOK | `LOOK` |
| MOVE | `MOVE` \| `MOVE BACK` \| `MOVE LEFT` \| `MOVE RIGHT` |
| PULL | `PULL LEFT <object>` \| `PULL RIGHT <object>` |
| REVEAL | `REVEAL LEFT` \| `REVEAL RIGHT` |
| STOW | `STOW LEFT` \| `STOW RIGHT` |
| TURN | `TURN LEFT` \| `TURN RIGHT` \| `TURN AROUND` |
| USE | `USE LEFT` \| `USE RIGHT` |
| ZLOAD | `ZLOAD "<filename>"` |
| ZSAVE | `ZSAVE "<filename>"` |

> **Note:** The MOVE command is a special case. `MOVE` alone steps forward. `MOVE BACK`, `MOVE LEFT`, and `MOVE RIGHT` use second words from the same table. The INCANT command parses a single proper-name word against the entire Proper Names table — any valid proper name can be typed, but only rings can be successfully incanted.

### Object Specifiers

When an object must be specified, you may type either:

- **Class name only** (e.g., `GET LEFT TORCH`) — matches any torch on the floor
- **Proper name + class name** (e.g., `GET LEFT PINE TORCH`) — matches a specific torch type

The game matches the words you type against the proper-name and class-name tables. If an abbreviation is too short to uniquely identify one entry (e.g., `S` could be SHIELD or SWORD), the game prints `???`.

---

## Appendix D — Object Names (ROM Reference)

The following tables are extracted directly from the Daggorath ROM disassembly. Each proper name has an internal token (its index in the Proper Names table at `D8F4`) and belongs to one of the six object classes from the Class Names table at `D96B`.

### Class Names

| Internal Token | Name |
|---------------|------|
| 00 | FLASK |
| 01 | RING |
| 02 | SCROLL |
| 03 | SHIELD |
| 04 | SWORD |
| 05 | TORCH |

### Proper Names

The internal token is stored in object structures at offset 9 (`proper name token`). Objects are created with a class, and the proper name is filled in when the object is placed in the dungeon or revealed. The index is purely an internal identifier — the player types the text name.

| Token | Name | Class |
|-------|------|-------|
| 00 | SUPREME | RING |
| 01 | JOULE | RING |
| 02 | ELVISH | SWORD |
| 03 | MITHRIL | SHIELD |
| 04 | SEER | SCROLL |
| 05 | THEWS | FLASK |
| 06 | RIME | RING |
| 07 | VISION | SCROLL |
| 08 | ABYE | FLASK |
| 09 | HALE | FLASK |
| 0A | SOLAR | TORCH |
| 0B | BRONZE | SHIELD |
| 0C | VULCAN | RING |
| 0D | IRON | SWORD |
| 0E | LUNAR | TORCH |
| 0F | PINE | TORCH |
| 10 | LEATHER | SHIELD |
| 11 | WOODEN | SWORD |
| 12 | FINAL | RING |
| 13 | ENERGY | RING |
| 14 | ICE | RING |
| 15 | FIRE | RING |
| 16 | GOLD | RING |
| 17 | EMPTY | FLASK |
| 18 | DEAD | TORCH |

### Incantation Words

Only rings can be successfully incanted. The INCANT command matches the typed word against the entire Proper Names table. Any of these 9 words are valid incantations:

> **SUPREME · JOULE · RIME · VULCAN · FINAL · ENERGY · ICE · FIRE · GOLD**

The manual deliberately obscures these names ("The types of RINGs, however, will not be listed in the chart. You must discover them yourself."). They are revealed here from the ROM data.

---

## Appendix E — Object Properties (ROM DA64 Table)

The table at ROM `DA64` defines properties for certain objects. Each entry is 4 bytes: proper-name token, and three property bytes whose meaning depends on the object class.

| Token | Name | Property 1 | Property 2 | Property 3 |
|-------|------|------------|------------|------------|
| 00 | SUPREME RING | strikes: 03 | ?? | ?? |
| 01 | JOULE RING | strikes: 03 | ?? | ?? |
| 03 | MITHRIL SHIELD | magic defense: 40 | physical defense: 40 | ?? |
| 06 | RIME RING | strikes: 03 | ?? | ?? |
| 0A | SOLAR TORCH | minutes: 3C (60) | physical light: 0D | magic light: 0B |
| 0B | BRONZE SHIELD | magic defense: 60 | physical defense: 80 | ?? |
| 0C | VULCAN RING | strikes: 03 | ?? | ?? |
| 0E | LUNAR TORCH | minutes: 1E (30) | physical light: 0A | magic light: 04 |
| 0F | PINE TORCH | minutes: 0F (15) | physical light: 07 | magic light: 00 |
| 10 | LEATHER SHIELD | magic defense: 6C | physical defense: 80 | ?? |
| 18 | DEAD TORCH | minutes: 00 | physical light: 00 | magic light: 00 |

**Torch durations** (in minutes):
- PINE: 15 · LUNAR: 30 · SOLAR: 60 · DEAD: 0

**Shield defense** (multiplier, where `80` = 1.0, `40` = 0.5):
- LEATHER: magic 0.85, physical 1.0
- BRONZE: magic 0.75, physical 1.0
- MITHRIL: magic 0.5, physical 0.5

> **Note:** There is a known bug where the physical and magic defense values for LEATHER and BRONZE shields are swapped in the ROM. These are purely physical shields — the magic defense should be 1.0 and the physical defense should be the lower value.

**Ring strikes:** All rings have a strike value of 03. This is the number of uses remaining when the ring is first found or created.

Not all objects have entries in this table — objects not listed use default values determined by their class.