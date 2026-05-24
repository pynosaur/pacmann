# pacmann

Terminal Pac-Man with authentic arcade mechanics, rendered entirely in curses.

Based on the original PAC-MAN (1980) by Toru Iwatani, published by Namco.
Game mechanics derived from "The Pac-Man Dossier" by Jamey Pittman.

## Install

```
pget install pacmann
```

## Usage

```
pacmann          # start the game
pacmann --help   # show help
```

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| Space | Pause |
| R | Restart |
| Q / Esc | Quit |

## Ghosts

| Char | Name | Behavior |
|------|------|----------|
| B | Blinky (red) | Chases you directly |
| P | Pinky (pink) | Targets 4 tiles ahead |
| I | Inky (cyan) | Flanks using Blinky |
| K | Clyde (orange) | Chases far, retreats close |

## Fruits

Appear below the ghost pen after 70 and 170 dots eaten.

| Char | Fruit | Points | Level |
|------|-------|--------|-------|
| % | Cherry | 100 | 1 |
| & | Strawberry | 300 | 2 |
| @ | Orange | 500-700 | 3-4 |
| $ | Apple/Melon | 1000-2000 | 5-6 |
| * | Galaxian | 3000 | 7 |
| ? | Key | 5000 | 8+ |

## Credits

PAC-MAN is a registered trademark of Bandai Namco Entertainment Inc.
This is an independent fan tribute for educational purposes and is not
affiliated with or endorsed by Bandai Namco.
