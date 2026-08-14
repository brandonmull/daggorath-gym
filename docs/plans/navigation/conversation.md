## Navigation

### "Cell," not "room"

**From the conversation:**

> *Antecedent — I had described the maze as "one byte per room," carrying ram.md's word:*
>
> **Cline:** "The maze is a 32×32 cell table, one byte per room (32×32 bytes)."
>
> **You:** "the problem was how you conflated the word 'room' with 'cell'. a room is a large space spanning many cells in both directions. a hall is a narrow space spanning many cells in only one direction."

> ### The Crux
>
> **Cline:** "The maze is a uniform 32×32 grid of cells. The game has no rooms — only halls."

**Resolution:** use "cell" for a grid position; never "room."


### The maze in a byte

**From the conversation:**

> *Antecedent — my "one byte per room" phrasing from ram.md:*
>
> **Cline:** "The maze is a 32×32 cell table, one byte per room (32×32 bytes)."
>
> **You:** "what do you mean one byte per room? 32 x 32 = 1024. not all rooms are the same shape and size. a maze is made of hallways as well. for every cell, you need to know if it's a wall, an open space, a door, etc. you can't just use a zero or one to represent the information per cell."

> ### The Crux
>
> **Cline:** "One byte per cell — not one bit — packing four 2-bit direction fields: open, normal door, magic door, or solid wall. And the dungeon has no rooms at all, only halls."

**Resolution:** navigation reads the 1024-byte maze (four 2-bit fields per cell) plus the holes/ladders table, and computes line-of-sight for sight-gating.

### How far does sight reach?

**From the conversation:**

> **Cline:** "Sight in Daggorath is light-bounded — the 3D view draws dots down the corridor, and dotFrequency is 'based on light-level, FF means no-draw.' The exact reach is a function of ambient_light plus torch light, and it's not traced. The principle is settled; only the threshold is unknown."
>
> **You:** "yepp"

> ### The Crux
>
> **Cline:** "Defer sight reach to a sandbox/trace, coupled with the corridor gate — both define what the player perceives at a distance."

**Resolution:** sight reach deferred to a sandbox/trace, coupled with the sound module's corridor gate.

### Magic doors

**From the conversation:**

> **Cline:** "The maze byte distinguishes normal doors (01) from magic doors (10), but how they differ in play — whether the 3D view renders them differently, what opens one — isn't traced. If they look distinct, the agent should see the distinction; if not, just 'door.'"

> ### The Crux
>
> **Cline:** "Defer magic-door exposure to the same research, with player-parity as the guide: expose what the player sees."

**Resolution:** magic-door exposure deferred pending research on how they appear and behave; player-parity guides the eventual answer.

### Whole map or explored cells?

**From the conversation:**

> **You:** "explored-with-memory map, obviously. it's a shame that these kinds of things have to be the responsibility of the environment. conceptually, they are the responsibilities of the player, therefore the agent, and thus should be delegated to the model under training, not the engine itself."

> ### The Crux
>
> **Cline:** "Explored-with-memory — but the memory is scaffolding. Map-building is conceptually the agent's job; the environment provides it now and the curriculum removes it later."

**Resolution:** explored-with-memory; the map memory is a curriculum item (environment scaffolding, removed when the agent learns to maintain its own map).
