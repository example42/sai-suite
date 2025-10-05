# Computer Games Lists for Saidata Generation

This directory contains comprehensive lists of computer games organized by genre. Each file contains hundreds of game titles that can be used to generate saidata metadata for gaming software.

## File Structure by Genre

### Core Gaming Categories
- **`action_fps.txt`** - First-person shooters, battle royale, hero shooters, tactical FPS
- **`rpg_adventure.txt`** - RPGs, JRPGs, MMORPGs, adventure games, point-and-click
- **`strategy_simulation.txt`** - RTS, turn-based strategy, 4X, city builders, economic sims
- **`racing_sports.txt`** - Racing games, sports simulations, arcade racing, kart racing
- **`puzzle_platformer.txt`** - Puzzle games, 2D/3D platformers, Metroidvania games
- **`horror_survival.txt`** - Horror games, survival horror, psychological horror, zombie games
- **`fighting_arcade.txt`** - Fighting games, beat 'em ups, classic arcade, shoot 'em ups
- **`indie_experimental.txt`** - Indie games, art games, experimental gameplay, narrative games

## Usage with saidata-gen

### Generate for entire genres:
```bash
# Generate saidata for all FPS games
saidata-gen generate --batch --input-file software_lists/games/action_fps.txt

# Generate for multiple genres
saidata-gen generate --batch --input-file software_lists/games/rpg_adventure.txt
saidata-gen generate --batch --input-file software_lists/games/strategy_simulation.txt
```

### Generate for specific subgenres:
```bash
# Extract specific sections and generate
grep -A 30 "## Classic FPS" software_lists/games/action_fps.txt | saidata-gen generate --batch --stdin

# Generate for specific franchises
grep -E "(call-of-duty|battlefield|counter-strike)" software_lists/games/action_fps.txt | saidata-gen generate --batch --stdin
```

### Platform-specific generation:
```bash
# Generate for Steam games
saidata-gen generate --provider steam --batch --input-file software_lists/games/indie_experimental.txt

# Generate for multiple platforms
parallel -j 4 saidata-gen generate --provider {} --batch --input-file software_lists/games/action_fps.txt ::: steam gog epic
```

## File Format and Organization

Each file follows this structure:
- Comments start with `#` and provide genre/subgenre organization
- Game titles are listed one per line using common identifiers
- Sections are organized by `##` headers for easy parsing
- Related games and franchises are grouped together logically
- Both classic and modern titles are included

### Naming Conventions
- Game titles use lowercase with hyphens (e.g., `call-of-duty-modern-warfare`)
- Sequels include numbers or subtitles (e.g., `street-fighter-6`, `elder-scrolls-skyrim`)
- Series entries are grouped together chronologically
- DLC and expansions may be included for major releases

## Statistics

Total estimated games across all genres: **~2,500+ game titles**

### Breakdown by genre:
- Action/FPS: ~400 games
- RPG/Adventure: ~450 games  
- Strategy/Simulation: ~350 games
- Racing/Sports: ~300 games
- Puzzle/Platformer: ~350 games
- Horror/Survival: ~250 games
- Fighting/Arcade: ~300 games
- Indie/Experimental: ~300 games

## Platform Coverage

These lists include games available across multiple platforms and stores:
- **Steam** (PC gaming platform)
- **Epic Games Store** (PC gaming platform)
- **GOG** (DRM-free PC games)
- **Origin/EA App** (EA games)
- **Uplay/Ubisoft Connect** (Ubisoft games)
- **Battle.net** (Blizzard games)
- **Microsoft Store/Xbox** (Microsoft games)
- **PlayStation Store** (Sony games)
- **Nintendo eShop** (Nintendo games)
- **itch.io** (Indie games)

## Game Categories Explained

### Action/FPS
- Classic shooters (Doom, Quake, Wolfenstein)
- Modern military shooters (Call of Duty, Battlefield)
- Tactical shooters (Counter-Strike, Rainbow Six)
- Battle royale games (PUBG, Fortnite, Apex Legends)
- Hero shooters (Overwatch, Valorant)

### RPG/Adventure
- Western RPGs (Baldur's Gate, The Witcher, Fallout)
- JRPGs (Final Fantasy, Persona, Dragon Quest)
- Action RPGs (Diablo, Path of Exile, Mass Effect)
- MMORPGs (World of Warcraft, Final Fantasy XIV)
- Adventure games (Monkey Island, Life is Strange)

### Strategy/Simulation
- Real-time strategy (StarCraft, Age of Empires, Command & Conquer)
- Turn-based strategy (Civilization, Total War, XCOM)
- 4X games (Stellaris, Master of Orion)
- City builders (SimCity, Cities: Skylines, Anno)
- Economic simulations (Transport Tycoon, RollerCoaster Tycoon)

### Racing/Sports
- Arcade racing (Need for Speed, Burnout)
- Simulation racing (Gran Turismo, Forza, Assetto Corsa)
- Sports games (FIFA, Madden, NBA 2K)
- Kart racing (Mario Kart, Crash Team Racing)

### Puzzle/Platformer
- Classic puzzles (Tetris, Portal, The Witness)
- 2D platformers (Super Mario, Sonic, Hollow Knight)
- 3D platformers (Super Mario 64, Banjo-Kazooie)
- Metroidvania games (Metroid, Castlevania, Ori)

### Horror/Survival
- Classic horror (Resident Evil, Silent Hill, Fatal Frame)
- Psychological horror (Amnesia, SOMA, Layers of Fear)
- Survival horror (The Forest, Subnautica, The Long Dark)
- Multiplayer horror (Dead by Daylight, Phasmophobia)

### Fighting/Arcade
- 2D fighters (Street Fighter, King of Fighters, Guilty Gear)
- 3D fighters (Tekken, Soul Calibur, Mortal Kombat)
- Platform fighters (Super Smash Bros, Rivals of Aether)
- Beat 'em ups (Streets of Rage, Final Fight)
- Classic arcade (Pac-Man, Galaga, Centipede)

### Indie/Experimental
- Narrative games (Disco Elysium, Kentucky Route Zero)
- Art games (Journey, Gris, Monument Valley)
- Roguelikes (Hades, Dead Cells, Slay the Spire)
- Experimental gameplay (Baba Is You, The Stanley Parable)
- Cozy games (Stardew Valley, Animal Crossing)

## Quality Considerations

When generating saidata for these games:
1. Game availability varies by platform and region
2. Some games may have multiple editions or versions
3. Consider using platform-specific overrides for accuracy
4. Validate metadata for popular/critical games
5. Handle franchise naming conventions consistently
6. Account for remasters, remakes, and definitive editions

## Developer and Publisher Information

Many files include developer/publisher names for context:
- Major publishers (EA, Ubisoft, Activision, Sony, Microsoft, Nintendo)
- Indie publishers (Devolver Digital, Annapurna Interactive, Team17)
- Notable developers (id Software, Valve, Blizzard, FromSoftware)
- Indie developers (Team Cherry, Supergiant Games, ConcernedApe)

## Contributing

To add new games or categories:
1. Follow the existing naming conventions
2. Group games logically by subgenre
3. Include both popular and niche titles
4. Consider cross-platform availability
5. Add developer/publisher context where helpful
6. Maintain chronological order for series

## Usage Tips

- Use genre-specific lists for targeted metadata generation
- Combine multiple genres for comprehensive gaming libraries
- Filter by specific franchises or developers as needed
- Consider platform-specific generation for store optimization
- Validate generated metadata against actual game store listings