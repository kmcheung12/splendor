# UI Test Specification

Tests apply to both **desktop** and **mobile** layouts unless marked otherwise.

---

## Fixture data

Use a stable card and player fixture throughout all tests.

```ts
const CHARMANDER: PokemonCard = {
  name: 'charmander',
  tier: 'common',
  bonus: ['red'],
  cost: ['red', 'red', 'blue', 'blue', 'blue'],   // 2 red, 3 blue
  point: 1,
  evolve_into: 'charmeleon',
  evolve: ['red', 'red', 'red'],                   // 3 red to evolve
}

const DRAGONITE: PokemonCard = {
  name: 'dragonite',
  tier: 'legendary',
  bonus: ['master', 'master'],                     // 2 bonus balls
  cost: ['red', 'yellow', 'blue', 'pink', 'black', 'master'],  // 6 types (overflow row)
  point: 7,
  evolve_into: null,
  evolve: [],
}

const MEWTWO: PokemonCard = {
  name: 'mewtwo',
  tier: 'legendary',
  bonus: ['master'],
  cost: ['master', 'master', 'master', 'master'],
  point: 10,
  evolve_into: null,
  evolve: [],
}

const PLAYER: PlayerState = {
  name: 'player1',
  points: 14,
  tokens:  { red: 2, yellow: 0, blue: 3, pink: 1, black: 0, master: 1 },
  cards:   [
    { ...CHARMANDER, evolved: false },
    { name: 'bulbasaur', tier: 'common', bonus: ['blue', 'blue'], cost: ['green','green'], point: 0, evolve_into: null, evolve: [], evolved: false },
  ],
  reserved_cards: [DRAGONITE],
}
```

---

## 1. BoardCard — `BoardCard.svelte` (size="sm" and size="lg")

Components under test: `BoardCard.svelte` rendered via `MobileBoard` (sm) and `CardDetailModal` (lg).

### 1.1 Catch cost tokens

- Each distinct gem type in `card.cost` renders exactly one ringed token circle.
- The token circle border color matches `COL[gemType]`.
- The number inside the circle equals the count of that gem in `card.cost`.
- A mini pokéball image is positioned at the bottom-right corner of the circle.
- **Overflow (4+ types):** when `card.cost` contains 4 or more distinct types, tokens split into two rows: the overflow types on top, the heaviest 3 on the bottom.

Given CHARMANDER (2 red, 3 blue):
- Two token circles rendered: red circle showing `2`, blue circle showing `3`.
- No overflow row (only 2 types).

Given DRAGONITE (6 distinct types):
- Six token circles rendered.
- Top row: first 3 overflow types; bottom row: last 3 types.

### 1.2 Bonus marker (upper-right mini card)

- Renders one pokéball image per entry in `card.bonus`.
- For single-bonus cards: one ball centered in the mini card shape.
- For multi-bonus cards (e.g. DRAGONITE `bonus: ['master','master']`): two balls stacked with slight overlap.
- The mini card background color matches `CARDBG[card.bonus[0]]`.
- The accent bar at the top of the mini card matches `COL[card.bonus[0]]`.

### 1.3 Points badge

- Bottom-right badge displays `card.point`.
- Badge border color matches `COL[card.bonus[0]]`.

### 1.4 Evolution line

- Shown only when `card.evolve_into` is set.
- Format: `{name} ‹ {evolve cost tokens}`.
- The pokemon name appears first (truncates with ellipsis if needed).
- Evolve cost tokens use the same ringed-circle pattern but are **2px smaller** than catch cost tokens (sm: 16px vs 18px; lg: 24px vs 30px).
- One token per distinct gem type in `card.evolve`.

Given CHARMANDER (`evolve: ['red','red','red']`):
- Evolution line reads: `charmeleon ‹ [red×3 token]`.
- One token showing `3` with red border and red pokéball badge.

### 1.5 Card name

- `card.name` is displayed in the header.
- Truncates with ellipsis if the name overflows available width.

### 1.6 Tier bar

- A thin bar at the very top of the card.
- Color matches `TIER_BAR[card.tier]`.

### 1.7 Highlight state

- When `highlighted=true`: card has a yellow (`#ffd23f`) outline.
- When `highlighted=false`: no outline.

### 1.8 Jump animation

- When `jumping=true`: the sprite image plays the jump keyframe animation.
- Animation clears after ~480 ms.

### 1.9 Catch-reveal animation

- When `catchReveal=true`: card plays the slide-up fade-in animation.

---

## 2. ReservedCard — `ReservedCard.svelte` (size="sm" and size="lg")

### 2.1 Color strip

- A 2px vertical bar on the left edge of the row.
- Color matches `COL[card.bonus[0]]` (bonus color, **not** tier color).

Given DRAGONITE (`bonus: ['master','master']`):
- Strip color is `COL['master']` = `#a569bd`.

### 2.2 Name

- `card.name` is displayed.
- Truncates with ellipsis (`text-overflow: ellipsis`) when catch cost tokens leave insufficient space.

### 2.3 Catch cost tokens

- Same ringed-circle pattern as BoardCard but smaller (sm: 12px circles, lg: 14px circles).
- One circle per distinct gem type in `card.cost`.
- Number and border color correct per gem type.
- Mini pokéball badge at bottom-right.
- Name shrinks to accommodate tokens — it does **not** overflow the row's fixed width.

Given DRAGONITE (6 gem types):
- Six 12px (sm) / 14px (lg) circles rendered.
- Name truncates to fit.

### 2.4 Points badge

- `card.point` displayed in a dark pill on the right.

### 2.5 Sprite (lg only)

- `size="lg"` renders an 18×18 px sprite image from the PokeAPI URL.
- `size="sm"` renders no sprite.

### 2.6 Catchable state (lg only)

- When `catchable=true`: yellow outline pulse animation on the row, cursor is `pointer`.
- A "Catch" tag is visible inside the row.
- When `catchable=false`: no outline, no tag, cursor is `default`.

---

## 3. Player panel — desktop `PlayerPanel.svelte`

### 3.1 Total points

- Displays the sum of `player.points` prominently.
- Given PLAYER (points: 14): shows `14`.

### 3.2 Bonus by type

- One column per gem color in `LANE_ORDER` (`red yellow blue pink black master`).
- Each column shows the total bonus count for that color across all non-evolved cards.
- Given PLAYER cards (charmander: `bonus:['red']`, bulbasaur: `bonus:['blue','blue']`):
  - Red column: `1`
  - Blue column: `2`
  - All other columns: `0`

### 3.3 Pokéballs by type

- One count per gem color in `TOKEN_ORDER`.
- Value equals `player.tokens[color]`.
- Given PLAYER tokens `{ red:2, yellow:0, blue:3, pink:1, black:0, master:1 }`:
  - Red: `2`, Yellow: `0`, Blue: `3`, Pink: `1`, Black: `0`, Master: `1`.

### 3.4 Reserved pokémon

- Shows up to 3 `ReservedCard size="lg"` rows.
- Each row passes all checks in section 2.
- Given PLAYER (1 reserved card — DRAGONITE): one row rendered.
- Given a player with 0 reserved cards: section is empty or hidden.

---

## 4. Mobile player rail — `MobilePlayerRail.svelte`

### 4.1 Total points

- LCD-style badge displays `player.points`.

### 4.2 Bonus / Pokéball stacks

- 6 columns (red, yellow, blue, pink, black, master).
- Each column has two stacked elements:
  - **Top (cs-card):** bonus count for that color. Zero count renders at reduced opacity (`.csz`).
  - **Bottom (cs-gem):** token count for that color. Zero count renders at reduced opacity.
- Background colors and accent bars match `CARDBG` / `COL` for each color.
- Master column always rendered; uses star icon instead of number in top card.

Given PLAYER:
- Red cs-card: `1`, Red cs-gem: `2`.
- Blue cs-card: `2`, Blue cs-gem: `3`.
- Yellow cs-card: `0` (dim), Yellow cs-gem: `0` (dim).

### 4.3 Reserved pokémon

- Shows `ReservedCard size="sm"` rows.
- Each row passes all checks in section 2 (sm variant).
- Row width does not exceed rail width (110px); name truncates if needed.

### 4.4 Active player indicator

- When `isActive=true`: rail has a gold glow border, avatar badge is yellow.
- When `isActive=false`: no glow, avatar is grey.

### 4.5 Action required badge

- When `needsAction=true` (own player, own turn, discard or evolve phase): a red `!` badge pulses on the rail.
- Otherwise: no badge.

---

## 5. Mobile player hand modal — `PlayerHandModal.svelte`

### 5.1 Reserved pokémon section

- Heading shows `Reserved · {n}/3` where `n` is the count.
- Each reserved card renders as `ReservedCard size="lg"`.
- All checks from section 2 (lg) apply.

### 5.2 Discard mode

- When `discardMode=true`: pokéball buttons for valid discard types are highlighted; clicking sends the discard action.
- When `discardMode=false`: no discard buttons shown.

### 5.3 Catchable reserved card

- When the player can catch a reserved card: `ReservedCard` receives `catchable=true`; passes checks 2.6.

---

## 6. Cross-cutting

### 6.1 Bonus color vs tier color

- In **every** component, the left-edge color strip on a reserved card row uses `COL[card.bonus[0]]`, never `TIER_BAR[card.tier]`.

### 6.2 Master ball cost shown

- Cards with `master` in their `cost` (e.g. MEWTWO) render a purple (`COL['master']`) token circle.
- This applies to BoardCard catch cost, BoardCard evolve cost, and ReservedCard cost tokens.

### 6.3 Sprite URLs

- All sprite images use `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png`.
- `spriteUrl('charmander')` → id `4`.
- `spriteUrl('unknown')` → empty string (no broken img rendered).

### 6.4 groupCost ordering

- Tokens always appear in `GEM_ORDER` sequence: red → yellow → blue → pink → black → master.
- Input order in `card.cost` does not affect rendered order.
