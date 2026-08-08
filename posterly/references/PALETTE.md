### Palette derivation (when the user has no color preference)

A paper already carries brand signals — the default palette should be **derived from them, not house-styled**. Pick the seed color from whichever signal is strongest for *this* poster (judgment call, no fixed priority):

- **Affiliation brand color** — the official identity color of the dominant lab/university (your own knowledge or a quick web check: Tsinghua purple, MIT cardinal, ETH blue…). Strongest choice when one affiliation dominates the author list.
- **A provided logo** — extract its dominant saturated color (snippet below).
- **Venue identity** — if the conference has a recognizable brand color.
- **The paper's own figures** — dominant hue of the headline figure; the poster then echoes its figures.
- **Field/topic conventions** — weakest signal; use only when nothing above gives a usable color.

Whatever the source, the seed feeds one fixed recipe — the rebrand surface is the same eight tokens in every template (`--accent`, `--accent-deep`, `--accent-light`, `--accent-soft`, `--accent-ink`, `--emph`, `--emph-soft`, `--emph-ink`):

```python
from collections import Counter
from PIL import Image

def rel_lum(rgb):
    c = [v / 255 for v in rgb]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

def contrast(a, b):
    la, lb = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def mix(rgb, other, t):  # t=0 -> rgb, t=1 -> other
    return tuple(round(v + (o - v) * t) for v, o in zip(rgb, other))

# 1) Seed. From an IMAGE (logo / headline figure): dominant saturated
#    mid-tone, bucketed so JPEG noise doesn't split the vote. From a BRAND
#    GUIDELINE: just set `seed` to the official hex and skip this block.
im = Image.open("images/lab-logo.png").convert("RGBA")
im.thumbnail((128, 128))
px = [(r, g, b) for r, g, b, a in im.getdata() if a > 128]
cands = Counter((r // 32, g // 32, b // 32) for r, g, b in px
                if max(r, g, b) - min(r, g, b) > 40       # saturated enough
                and 60 < (r + g + b) / 3 < 200)           # mid-tone
seed = (tuple(v * 32 + 16 for v in cands.most_common(1)[0][0])
        if cands else None)  # None = this image has no usable seed --
                             # try the next signal source, neutral only last

# 2) Tokens. Darken the seed until white text clears WCAG AA on it (the
#    same 4.5:1 also covers accent-as-text on white -- symmetric pair).
accent = seed
while contrast(accent, (255, 255, 255)) < 4.5:
    accent = mix(accent, (0, 0, 0), 0.08)
fmt = lambda c: "#%02X%02X%02X" % c
print(f"--accent: {fmt(accent)};  --accent-deep: {fmt(mix(accent, (0, 0, 0), 0.30))};")
print(f"--accent-light: {fmt(mix(accent, (255, 255, 255), 0.90))};  "
      f"--accent-soft: {fmt(mix(accent, (255, 255, 255), 0.82))};")
print(f"white-on-accent contrast: {contrast(accent, (255, 255, 255)):.1f}:1")
# --accent-ink stays #FFFFFF -- the AA loop above just guaranteed it.
# 3) Emphasis register: pick --emph per the rule below, then derive
#    --emph-soft = mix(emph, white, 0.90) and check --emph-ink (the ink
#    used ON the emph fill; template default #14314A) still
#    clears 4.5:1 against the register you chose -- swap it if not.
```

Rules that hold regardless of seed source:

- **Print-safe accent**: muted-to-medium saturation, medium-dark value. The AA loop above enforces the dark end; if a brand color is neon-bright, mute it toward the template's tone rather than shipping fluorescent ink.
- **Emphasis register (`--emph`) is a per-poster choice, not a fixture**: it is the single "ours / best" cue (the `.ours` row, `★` callouts, `.keyword-emph`), and defaulting it to the same color on every poster is a recognizable fingerprint. Pick ONE register per poster from a shortlist that suits the accent — warm gold `#C9A24A` (classic against cool accents), deep cool slate `#3D4A5C` (safe on any accent), rust `#A2521C`, forest `#2D5F3E`, burgundy `#8F2437` (see `templates/THEMES.md` for the calibrated pool) — and vary the choice across posters. Constraints: (a) hue-distinct from the accent (rule 4 allows exactly these two hue families); (b) if the accent is warm (red/orange/yellow), the register must be cool; (c) re-derive `--emph-soft` as the register's ~90% white tint and keep `--emph-ink` at 4.5:1 on the register fill. (These constraints govern the default accent+emph role topology — a deliberately different Axis 3 choice made in Step 2.5, e.g. same-center tonal or categorical roles, follows `templates/DESIGN-AXES.md` instead.)
- **Backgrounds default to near-white** (`--bg-page`/`--bg-card` untouched, or at most a faint seed-hued tint) — this recipe derives the *accent* tokens, not the ground. A non-white canvas (cream / light tint / brand hue / near-black) is a legitimate **Axis 2** choice made in Step 2.5, with its own contrast obligations (`templates/DESIGN-AXES.md` clash rules 6 and 9) and, for dark grounds, the `"dark_ground": true` declaration in the `--tokens` JSON (Step 2.5 item 4).
- **Echo the choice**: state the seed source and final tokens to the user (they surface visually in the Step 2.5 thumbnails) and record them in the Step 2.5 `DESIGN DIRECTION` comment block — "accent #660874 from Tsinghua brand; register slate #3D4A5C" — so a later edit doesn't "correct" a deliberate derivation back to neutral.
