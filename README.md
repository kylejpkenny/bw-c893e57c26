# Bowen's Birthday World

A one-tap retro auto-runner, made as a birthday present for Bowen from his Uncle Kyle.

Everything lives in **`index.html`** — art, audio, level and game loop. No build step, no
dependencies, no external assets. Open the file and it runs.

## Playing it

Tap anywhere to jump. Bowen runs right on his own. Jumping on a dinosaur squashes it;
running into one just puts him back on solid ground a moment earlier. There is no game
over and no way to lose — the level always ends at the castle.

Best held **sideways** (landscape). In portrait it shows a "turn your phone" prompt.

## How it's put together

| Piece | Where |
|---|---|
| Pixel font (5×7 glyphs) | `FONT` |
| Bowen's sprites | `BOWEN_HEAD` / `BOWEN_BODY` / `BOWEN_RUN_*` / `BOWEN_JUMP` |
| Uncle Kyle's head | `KYLE_HEAD` + `KYLE_PAL` |
| Dinosaur | `dinoMap()` — plotted with geometry, not a hand-typed grid |
| Level layout | `buildLevel()` — a readable script of `flat` / `dino` / `pipe` / `pit` / `coinArc` calls |
| Sound | `SFX` — synthesised with the Web Audio API |

Sprites are written as arrays of strings, one character per pixel, and baked once into
offscreen canvases by `makeSprite()`. A character with no entry in the palette is
transparent.

### Swapping in the real photo of Uncle Kyle

The head on the dinosaurs is currently a **placeholder**. To replace it:

1. Edit `KYLE_HEAD` (a 12×12 string map) and `KYLE_PAL` (its palette) near the top of
   `index.html`.
2. Nothing else needs to change. The head is positioned by `drawKyleOn()`, which centres
   whatever size you give it over the dinosaur's neck, so a different width or height
   still lands correctly.
3. `sprites.html` renders every sprite at 13× against the game's own code — open it to
   check the new head before shipping.

### Tuning the difficulty

The forgiveness dials are all constants at the top of the file: `RUN_SPEED`, `GRAVITY`,
`JUMP_V`, `JUMP2_V` (the mid-air save jump), `COYOTE` (grace frames after leaving a
ledge) and `BUFFER` (how long an early tap stays queued).

## Local preview

Any static server works, e.g.

```bash
npx serve .
```
