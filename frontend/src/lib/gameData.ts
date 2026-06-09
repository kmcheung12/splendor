export const COL: Record<string, string> = {
  red: '#ff3434', yellow: '#f1c40f', blue: '#3498db',
  pink: '#ffa3da', black: '#9aa0a6', master: '#a569bd',
}

export const CARDBG: Record<string, string> = {
  red: '#6b2a2a', yellow: '#5c5020', blue: '#1e3d5c',
  pink: '#a04f78', black: '#2a2a2a', master: '#4a3060',
}

export const TIER_BAR: Record<string, string> = {
  common: '#b08d57', uncommon: '#c7ccd1', rare: '#e8b923',
  epic: '#a55fd0', legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
}

export const TIER_DECK_GRAD: Record<string, string> = {
  common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
  uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
  rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
  epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
  legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
}

export const GEM_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
export const LANE_ORDER = ['red', 'yellow', 'blue', 'pink', 'black'] as const
export const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']

export const TIER_ABS_OFFSET: Record<string, number> = {
  common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
}

export const DISCARD_ACTION: Record<string, number> = {
  red: 71, yellow: 72, blue: 73, pink: 74, black: 75, master: 76,
}

export const DEX: Record<string, number> = {
  abra:63, aerodactyl:142, alakazam:65, articuno:144, beedrill:15,
  bellsprout:69, blastoise:9, bulbasaur:1, butterfree:12, caterpie:10,
  charizard:6, charmander:4, charmeleon:5, ditto:132, dragonair:148,
  dragonite:149, dratini:147, eevee:133, gastly:92, gengar:94,
  geodude:74, gloom:44, golem:76, graveler:75, haunter:93,
  ivysaur:2, kadabra:64, kakuna:14, lapras:131, machamp:68,
  machoke:67, machop:66, metapod:11, mew:151, mewtwo:150,
  moltres:146, nidoqueen:31, nidoran:29, nidorina:30, oddish:43,
  pidgeot:18, pidgeotto:17, pidgey:16, poliwag:60, poliwhirl:61,
  poliwrath:62, snorlax:143, squirtle:7, venusaur:3, victreebel:71,
  vileplume:45, wartortle:8, weedle:13, weepinbell:70, zapdos:145,
}

export function spriteUrl(name: string): string {
  const id = DEX[name.toLowerCase()]
  return id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png` : ''
}

export function groupCost(gems: string[]): { c: string; n: number }[] {
  const counts: Record<string, number> = {}
  for (const g of gems) counts[g] = (counts[g] ?? 0) + 1
  return GEM_ORDER.filter(c => counts[c]).map(c => ({ c, n: counts[c] }))
}
