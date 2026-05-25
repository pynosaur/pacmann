#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pacmann -- Terminal Pac-Man."""

import curses
import random
import sys
import time
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    __package__ = "app"

from app import __version__

# Original 28x31 Pac-Man maze
ORIGINAL_MAZE = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#o####.#####.##.#####.####o#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##          ##.#     ",
    "     #.## ###--### ##.#     ",
    "######.## #      # ##.######",
    "T     .   #      #   .     T",
    "######.## #      # ##.######",
    "     #.## ######## ##.#     ",
    "     #.##          ##.#     ",
    "     #.## ######## ##.#     ",
    "######.## ######## ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#o..##.......S .......##..o#",
    "###.##.##.########.##.##.###",
    "###.##.##.########.##.##.###",
    "#......##....##....##......#",
    "#.##########.##.##########.#",
    "#.##########.##.##########.#",
    "#..........................#",
    "############################",
]

MW = 28
MH = 31
TILE_W = 2
RENDER_W = MW * TILE_W
MIN_COLS = RENDER_W + 4
MIN_ROWS = MH + 4

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRS = [UP, DOWN, LEFT, RIGHT]

# Speed system: accumulator-based.
# Each tick: acc += speed. If acc >= 16, move and acc -= 16.
# Pac-Man MUST be faster than ghosts in open corridors.
SPD_PAC = 14           # ~87% -- clearly faster than ghosts
SPD_GHOST_NORMAL = 11  # ~69% -- noticeably slower than pac
SPD_GHOST_FRIGHT = 7   # ~44% -- very slow when blue
SPD_GHOST_TUNNEL = 5   # ~31% -- crawling in tunnels
SPD_GHOST_EATEN = 20   # ~125% -- fast return
SPD_THRESHOLD = 16

# Scatter/chase timing in ticks (80ms/tick -> 12.5 tps)
# Level 1: 7s, 20s, 7s, 20s, 5s, 20s, 5s, forever
SCATTER_CHASE = [88, 250, 88, 250, 63, 250, 63, 99999]

# Dots eaten before ghost release
RELEASE_DOTS = [0, 0, 30, 60]

# Frightened duration in ticks (~6 seconds at 80ms/tick)
FRIGHT_TIME = 75

# Ghosts cannot turn up at these tiles
NO_UP_TILES = {(12, 14), (15, 14), (12, 26), (15, 26)}

# Ghost scatter corners
SCATTER_TARGETS = [(25, 0), (2, 0), (27, 30), (0, 30)]

# Tunnel zones (ghosts slow down here)
TUNNEL_ZONES = set()
for _tx in range(6):
    TUNNEL_ZONES.add((_tx, 14))
    TUNNEL_ZONES.add((MW - 1 - _tx, 14))

# Fruit: spawns at (14, 17) after 70 and 170 dots eaten
FRUIT_POS = (14, 17)
FRUIT_DOTS = [70, 170]
# (char, points, color_pair) per level
FRUIT_TABLE = [
    ('%', 100, 4),    # cherry (red)
    ('&', 300, 5),    # strawberry (pink)
    ('@', 500, 7),    # orange (green display)
    ('@', 700, 7),    # another orange
    ('$', 1000, 5),   # apple (pink)
    ('$', 2000, 7),   # melon (green)
    ('*', 3000, 6),   # galaxian (cyan)
    ('?', 5000, 3),   # key (yellow)
]
FRUIT_DURATION = 120  # ticks fruit stays visible (~9.6s at 80ms)


def print_help():
    print("pacmann - Terminal Pac-Man with authentic arcade mechanics")
    print()
    print("Based on the original PAC-MAN (1980) by Toru Iwatani, Namco.")
    print("Game mechanics from The Pac-Man Dossier by Jamey Pittman.")
    print()
    print("USAGE:")
    print("    pacmann                      Start the game")
    print("    pacmann --help               Show this help")
    print("    pacmann --version            Show version")
    print()
    print("CONTROLS:")
    print("    Arrow keys / WASD            Move")
    print("    Space                        Pause")
    print("    Q / Esc                      Quit")
    print("    R                            Restart")
    print()
    print("GHOSTS:")
    print("    B = Blinky (red)    chases you directly")
    print("    P = Pinky (pink)    targets 4 tiles ahead of you")
    print("    I = Inky (cyan)     flanks using Blinky's position")
    print("    K = Clyde (orange)  chases when far, retreats when close")
    print()
    print("PAC-MAN is a trademark of Bandai Namco Entertainment Inc.")
    print("This is an independent fan tribute for educational purposes.")


def print_version():
    print(__version__)


def _parse():
    walls = set()
    dots = set()
    energizers = set()
    doors = set()
    pac_start = (13, 23)

    for y, row in enumerate(ORIGINAL_MAZE):
        for x, ch in enumerate(row):
            if ch == '#':
                walls.add((x, y))
            elif ch == '.':
                dots.add((x, y))
            elif ch == 'o':
                dots.add((x, y))
                energizers.add((x, y))
            elif ch == '-':
                doors.add((x, y))
            elif ch == 'S':
                pac_start = (x, y)

    return walls, dots, energizers, doors, pac_start


def _dist_sq(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _opposite(d):
    return (-d[0], -d[1])


def _run(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(80)  # ~12.5 tps game feel

    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_GREEN, -1)
    curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(9, curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(10, curses.COLOR_RED, -1)
    curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLUE)

    walls, init_dots, init_energizers, doors, pac_start = _parse()
    gnames = ['B', 'P', 'I', 'K']
    gcolors = [4, 5, 6, 7]
    ghost_pen_exit = (14, 11)

    def can_move(x, y):
        if y < 0 or y >= MH:
            return False
        return (x % MW, y) not in walls and (x % MW, y) not in doors

    def can_move_ghost(x, y, eaten):
        if y < 0 or y >= MH:
            return False
        if (x % MW, y) in walls:
            return False
        if (x % MW, y) in doors and not eaten:
            return False
        return True

    def new_game():
        return {
            'score': 0, 'lives': 3, 'level': 1,
            'dots': set(init_dots), 'energizers': set(init_energizers),
            'dots_eaten': 0,
            'fruit_active': False, 'fruit_timer': 0,
            'fruit_spawned': 0,
        }

    def new_round():
        return {
            'px': pac_start[0], 'py': pac_start[1],
            'pdir': LEFT, 'pnext': LEFT,
            'pac_acc': 0,
            'ghosts': [
                # [x, y, dir, mode, fright_t, in_pen, speed_acc]
                [14, 11, LEFT, 'scatter', 0, False, 0],
                [14, 14, UP, 'scatter', 0, True, 0],
                [12, 14, UP, 'scatter', 0, True, 0],
                [16, 14, UP, 'scatter', 0, True, 0],
            ],
            'mode_idx': 0, 'mode_t': 0,
            'state': 'ready', 'ready_t': 25,
            'dead_t': 0, 'won_t': 0, 'combo': 0,
            'fright_active': False,
        }

    def ghost_target(gi, r, g):
        gh = r['ghosts'][gi]
        mode = gh[3]
        px, py, pdir = r['px'], r['py'], r['pdir']

        if mode == 'frightened':
            return (random.randint(0, MW - 1), random.randint(0, MH - 1))
        elif mode == 'eaten':
            return ghost_pen_exit
        elif mode == 'scatter':
            return SCATTER_TARGETS[gi]
        else:
            if gi == 0:
                return (px, py)
            elif gi == 1:
                tx = px + pdir[0] * 4
                ty = py + pdir[1] * 4
                if pdir == UP:
                    tx -= 4
                return (tx, ty)
            elif gi == 2:
                bx, by = r['ghosts'][0][0], r['ghosts'][0][1]
                ax = px + pdir[0] * 2
                ay = py + pdir[1] * 2
                if pdir == UP:
                    ax -= 2
                return (ax + (ax - bx), ay + (ay - by))
            else:
                if _dist_sq((gh[0], gh[1]), (px, py)) > 64:
                    return (px, py)
                return SCATTER_TARGETS[3]

    def move_ghost(gi, r, g):
        gh = r['ghosts'][gi]
        # [x, y, dir, mode, fright_t, in_pen, speed_acc]

        if gh[5]:  # in pen
            release = RELEASE_DOTS[gi] if gi < 4 else 60
            if g['dots_eaten'] >= release:
                gh[5] = False
                gh[0], gh[1] = 14, 11
                gh[2] = LEFT
            return

        # Speed accumulator
        in_tunnel = (gh[0], gh[1]) in TUNNEL_ZONES
        if gh[3] == 'eaten':
            spd = SPD_GHOST_EATEN
        elif gh[3] == 'frightened':
            spd = SPD_GHOST_FRIGHT
        elif in_tunnel:
            spd = SPD_GHOST_TUNNEL
        else:
            spd = SPD_GHOST_NORMAL

        gh[6] += spd
        if gh[6] < SPD_THRESHOLD:
            return
        gh[6] -= SPD_THRESHOLD

        if gh[3] == 'eaten' and (gh[0], gh[1]) == ghost_pen_exit:
            gh[3] = 'scatter' if r['mode_idx'] % 2 == 0 else 'chase'
            gh[5] = True
            gh[0], gh[1] = 14, 14
            return

        target = ghost_target(gi, r, g)
        cur_dir = gh[2]
        opp = _opposite(cur_dir)
        eaten = gh[3] == 'eaten'

        best_d = cur_dir
        best_dist = float('inf')
        choices = []

        for d in DIRS:
            if d == opp:
                continue
            nx = (gh[0] + d[0]) % MW
            ny = gh[1] + d[1]
            if not can_move_ghost(nx, ny, eaten):
                continue
            if d == UP and (gh[0], gh[1]) in NO_UP_TILES and not eaten:
                continue
            choices.append(d)
            dist = _dist_sq((nx, ny), target)
            if dist < best_dist:
                best_dist = dist
                best_d = d

        if gh[3] == 'frightened' and choices:
            chosen = random.choice(choices)
        elif choices:
            chosen = best_d
        else:
            nx = (gh[0] + opp[0]) % MW
            ny = gh[1] + opp[1]
            if can_move_ghost(nx, ny, eaten):
                chosen = opp
            else:
                return

        gh[0] = (gh[0] + chosen[0]) % MW
        gh[1] = gh[1] + chosen[1]
        gh[2] = chosen

    def check_collision(r, g):
        """Returns True if pac died (caller should return)."""
        for gh in r['ghosts']:
            if gh[5]:
                continue
            if (gh[0], gh[1]) == (r['px'], r['py']):
                if gh[3] == 'frightened':
                    gh[3] = 'eaten'
                    r['combo'] += 1
                    g['score'] += 200 * (2 ** (r['combo'] - 1))
                elif gh[3] != 'eaten':
                    g['lives'] -= 1
                    if g['lives'] <= 0:
                        r['state'] = 'gameover'
                    else:
                        r['state'] = 'dead'
                    return True
        return False

    def tick(r, g):
        if r['state'] == 'ready':
            r['ready_t'] -= 1
            if r['ready_t'] <= 0:
                r['state'] = 'playing'
            return
        if r['state'] != 'playing':
            return

        # Pac-Man speed accumulator -- always same speed
        r['pac_acc'] += SPD_PAC
        if r['pac_acc'] >= SPD_THRESHOLD:
            r['pac_acc'] -= SPD_THRESHOLD
            # Move Pac-Man
            pnext = r['pnext']
            pdir = r['pdir']
            nx = (r['px'] + pnext[0]) % MW
            ny = r['py'] + pnext[1]
            if can_move(nx, ny):
                r['pdir'] = pnext
                r['px'], r['py'] = nx, ny
            else:
                nx = (r['px'] + pdir[0]) % MW
                ny = r['py'] + pdir[1]
                if can_move(nx, ny):
                    r['px'], r['py'] = nx, ny

            pos = (r['px'], r['py'])
            if pos in g['dots']:
                g['dots'].discard(pos)
                g['dots_eaten'] += 1
                if pos in g['energizers']:
                    g['energizers'].discard(pos)
                    g['score'] += 50
                    r['combo'] = 0
                    r['fright_active'] = True
                    for gh in r['ghosts']:
                        if not gh[5] and gh[3] != 'eaten':
                            gh[3] = 'frightened'
                            gh[4] = FRIGHT_TIME
                            gh[2] = _opposite(gh[2])
                else:
                    g['score'] += 10

                # Spawn fruit at 70 and 170 dots
                if (g['fruit_spawned'] < len(FRUIT_DOTS) and
                        g['dots_eaten'] >= FRUIT_DOTS[g['fruit_spawned']]):
                    g['fruit_active'] = True
                    g['fruit_timer'] = FRUIT_DURATION
                    g['fruit_spawned'] += 1

            # Eat fruit
            if g['fruit_active'] and pos == FRUIT_POS:
                g['fruit_active'] = False
                fi = min(g['level'] - 1, len(FRUIT_TABLE) - 1)
                g['score'] += FRUIT_TABLE[fi][1]

            # Check collision right after pac moves (catches pac running into ghost)
            if check_collision(r, g):
                return

        if not g['dots']:
            r['state'] = 'won'
            return

        # Fruit timer
        if g['fruit_active']:
            g['fruit_timer'] -= 1
            if g['fruit_timer'] <= 0:
                g['fruit_active'] = False

        # Mode timer
        r['mode_t'] += 1
        if r['mode_idx'] < len(SCATTER_CHASE):
            if r['mode_t'] >= SCATTER_CHASE[r['mode_idx']]:
                r['mode_t'] = 0
                r['mode_idx'] += 1
                new_mode = 'scatter' if r['mode_idx'] % 2 == 0 else 'chase'
                for gh in r['ghosts']:
                    if gh[3] not in ('frightened', 'eaten') and not gh[5]:
                        gh[3] = new_mode
                        gh[2] = _opposite(gh[2])

        # Frightened countdown
        r['fright_active'] = False
        for gh in r['ghosts']:
            if gh[3] == 'frightened':
                r['fright_active'] = True
                gh[4] -= 1
                if gh[4] <= 0:
                    gh[3] = 'scatter' if r['mode_idx'] % 2 == 0 else 'chase'

        # Save ghost positions before movement (for swap detection)
        prev_pos = [(gh[0], gh[1]) for gh in r['ghosts']]

        # Move ghosts (with speed accumulator)
        for gi in range(4):
            move_ghost(gi, r, g)

        # Check collision after ghosts move (catches ghost running into pac)
        if check_collision(r, g):
            return

        # Check for swap: ghost was where pac is now, pac was where ghost is now
        pac_pos = (r['px'], r['py'])
        for gi, gh in enumerate(r['ghosts']):
            if gh[5]:
                continue
            ghost_now = (gh[0], gh[1])
            ghost_was = prev_pos[gi]
            if ghost_was == pac_pos and ghost_now != pac_pos:
                if gh[3] == 'frightened':
                    gh[3] = 'eaten'
                    r['combo'] += 1
                    g['score'] += 200 * (2 ** (r['combo'] - 1))
                elif gh[3] != 'eaten':
                    g['lives'] -= 1
                    if g['lives'] <= 0:
                        r['state'] = 'gameover'
                    else:
                        r['state'] = 'dead'
                    return

    g = new_game()
    r = new_round()

    while True:
        rows, cols = stdscr.getmaxyx()

        key = stdscr.getch()
        while key != -1:
            if key in (ord('q'), ord('Q'), 27):
                return
            elif key in (ord('r'), ord('R')):
                g = new_game()
                r = new_round()
            elif key == ord(' '):
                r['paused'] = not r.get('paused', False)
            elif key in (curses.KEY_UP, ord('w'), ord('W')):
                r['pnext'] = UP
            elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                r['pnext'] = DOWN
            elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
                r['pnext'] = LEFT
            elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
                r['pnext'] = RIGHT
            key = stdscr.getch()

        if not r.get('paused', False):
            if r['state'] == 'dead':
                r['dead_t'] += 1
                if r['dead_t'] > 25:
                    r = new_round()
            elif r['state'] == 'won':
                r['won_t'] += 1
                if r['won_t'] > 40:
                    g['level'] += 1
                    g['dots'] = set(init_dots)
                    g['energizers'] = set(init_energizers)
                    g['dots_eaten'] = 0
                    r = new_round()
            else:
                tick(r, g)

        # Render
        stdscr.erase()

        if rows < MIN_ROWS or cols < MIN_COLS:
            msg = f"Resize terminal to {MIN_COLS}x{MIN_ROWS}"
            cur = f"(now {cols}x{rows})"
            try:
                stdscr.addstr(rows // 2, max(0, (cols - len(msg)) // 2), msg)
                stdscr.addstr(
                    rows // 2 + 1,
                    max(0, (cols - len(cur)) // 2), cur,
                )
            except curses.error:
                pass
            stdscr.refresh()
            continue

        ox = max(0, (cols - RENDER_W) // 2)
        oy = max(0, (rows - MH - 2) // 2) + 1

        def _put(tx, ty, ch, attr=0):
            sx = ox + tx * TILE_W
            sy = oy + ty
            if 0 <= sy < rows and 0 <= sx < cols - 2:
                try:
                    stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass

        # Header
        lives_str = '> ' * g['lives']
        hdr = (
            f" PACMANN  Score:{g['score']}"
            f"  Lv:{g['level']}  {lives_str}"
        )
        hx = max(0, (cols - len(hdr)) // 2)
        try:
            attr = curses.color_pair(9) | curses.A_BOLD
            stdscr.addnstr(oy - 1, hx, hdr, cols - hx, attr)
        except curses.error:
            pass

        # Maze
        for y in range(MH):
            sy = oy + y
            if sy >= rows:
                break
            for x in range(MW):
                pos = (x, y)
                if pos in walls:
                    _put(x, y, '##', curses.color_pair(1))
                elif pos in doors:
                    _put(x, y, '--', curses.color_pair(1))
                elif pos in g['energizers']:
                    blink = curses.A_BOLD if int(time.time() * 3) % 2 else 0
                    _put(x, y, 'oo', curses.color_pair(2) | blink)
                elif pos in g['dots']:
                    _put(x, y, ' .', curses.color_pair(2))
                else:
                    _put(x, y, '  ')

        # Fruit
        if g['fruit_active']:
            fi = min(g['level'] - 1, len(FRUIT_TABLE) - 1)
            fch, _, fcol = FRUIT_TABLE[fi]
            attr = curses.color_pair(fcol) | curses.A_BOLD
            _put(FRUIT_POS[0], FRUIT_POS[1], fch + ' ', attr)

        # Ghosts
        for gi, gh in enumerate(r['ghosts']):
            if gh[5]:
                continue
            if gh[3] == 'eaten':
                _put(gh[0], gh[1], '""', curses.color_pair(2))
            elif gh[3] == 'frightened':
                flash = gh[4] < 10 and int(time.time() * 4) % 2
                if flash:
                    attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    attr = curses.color_pair(8)
                _put(gh[0], gh[1], 'WW', attr)
            else:
                attr = curses.color_pair(gcolors[gi]) | curses.A_BOLD
                n = gnames[gi]
                _put(gh[0], gh[1], n + n, attr)

        # Pac-Man
        pac_tiles = {
            LEFT: '<<', RIGHT: '>>', UP: '^^', DOWN: 'VV',
        }
        pac_ch = pac_tiles.get(r['pdir'], '>>')
        attr = curses.color_pair(3) | curses.A_BOLD
        _put(r['px'], r['py'], pac_ch, attr)

        # Messages
        msg = None
        mc = curses.color_pair(3) | curses.A_BOLD
        if r.get('paused', False):
            msg = "PAUSED"
        elif r['state'] == 'ready':
            msg = "READY!"
        elif r['state'] == 'dead':
            msg, mc = "OUCH!", curses.color_pair(10) | curses.A_BOLD
        elif r['state'] == 'gameover':
            mc = curses.color_pair(10) | curses.A_BOLD
            msg = "GAME OVER  (R)estart (Q)uit"
        elif r['state'] == 'won':
            msg = "LEVEL CLEAR!"

        if msg:
            my = oy + MH // 2
            mx = ox + max(0, (RENDER_W - len(msg)) // 2)
            if 0 <= my < rows:
                try:
                    stdscr.addnstr(my, mx, msg, cols - mx, mc)
                except curses.error:
                    pass

        if oy + MH + 1 < rows:
            hlp = "WASD/Arrows  Space=Pause  Q=Quit  R=Restart"
            hx = max(0, (cols - len(hlp)) // 2)
            try:
                stdscr.addnstr(
                    oy + MH, hx, hlp, cols - hx,
                    curses.color_pair(11),
                )
            except curses.error:
                pass

        stdscr.refresh()


def main():
    args = sys.argv[1:]

    if args and args[0] in ("-h", "--help", "help"):
        print_help()
        return 0

    if args and args[0] in ("-v", "--version"):
        print_version()
        return 0

    try:
        curses.wrapper(_run)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
