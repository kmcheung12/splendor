// Pokemon sprite URL helper. Mirrors frontend/src/lib/gameData.ts; kept
// separate so the article can render without importing the live-game store.

const DEX: Record<string, number> = {
  abra: 63, aerodactyl: 142, alakazam: 65, articuno: 144, beedrill: 15,
  bellsprout: 69, blastoise: 9, bulbasaur: 1, butterfree: 12, caterpie: 10,
  charizard: 6, charmander: 4, charmeleon: 5, ditto: 132, dragonair: 148,
  dragonite: 149, dratini: 147, eevee: 133, gastly: 92, gengar: 94,
  geodude: 74, gloom: 44, golem: 76, graveler: 75, haunter: 93,
  ivysaur: 2, kadabra: 64, kakuna: 14, lapras: 131, machamp: 68,
  machoke: 67, machop: 66, metapod: 11, mew: 151, mewtwo: 150,
  moltres: 146, nidoqueen: 31, nidoran: 29, nidorina: 30, oddish: 43,
  pidgeot: 18, pidgeotto: 17, pidgey: 16, poliwag: 60, poliwhirl: 61,
  poliwrath: 62, snorlax: 143, squirtle: 7, venusaur: 3, victreebel: 71,
  vileplume: 45, wartortle: 8, weedle: 13, weepinbell: 70, zapdos: 145,
};

export function spriteUrl(name: string): string {
  const id = DEX[name.toLowerCase()];
  return id
    ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png`
    : '';
}
