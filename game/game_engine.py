import json
import time
from collections import deque
from pathlib import Path

import pygame

from game.maze import CELL, generate_maze
from game.player import Player

FPS = 60
BG = (240, 235, 220)
WALL_COLOR = (40, 40, 60)
EXIT_COLOR = (80, 200, 80)

DIFFICULTIES = {
    "Easy": (10, 8),
    "Medium": (15, 13),
    "Hard": (20, 18),
}

MAX_COLS = max(cols for cols, rows in DIFFICULTIES.values())
MAX_ROWS = max(rows for cols, rows in DIFFICULTIES.values())
WIDTH = MAX_COLS * CELL
HEIGHT = MAX_ROWS * CELL + 60
LEADERBOARD_FILE = Path(__file__).resolve().parent.parent / "leaderboard.json"


class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Maze Runner")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 22)
        self.big_font = pygame.font.SysFont("monospace", 36, bold=True)
        self.small_font = pygame.font.SysFont("monospace", 18)

        self.leaderboard = self.load_leaderboard()
        self.difficulty = None
        self.cols = 0
        self.rows = 0
        self.state = "difficulty"
        self.walls = None
        self.player = None
        self.exit_rect = None
        self.start_time = 0
        self.elapsed = 0
        self.won = False
        self.time_recorded = False
        self.show_solution = False
        self.solution_path = []
        self.fog_radius_cells = 3

    def load_leaderboard(self):
        """Load the best five completion times from leaderboard.json safely."""
        try:
            with LEADERBOARD_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, list):
                return []
            times = []
            for value in data:
                try:
                    value = float(value)
                    if value >= 0:
                        times.append(value)
                except (TypeError, ValueError):
                    continue
            return sorted(times)[:5]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

    def save_leaderboard(self):
        try:
            with LEADERBOARD_FILE.open("w", encoding="utf-8") as file:
                json.dump(self.leaderboard[:5], file, indent=2)
        except OSError:
            pass

    def add_completion_time(self, completion_time):
        self.leaderboard.append(float(completion_time))
        self.leaderboard.sort()
        self.leaderboard = self.leaderboard[:5]
        self.save_leaderboard()

    def start_difficulty(self, difficulty):
        self.difficulty = difficulty
        self.cols, self.rows = DIFFICULTIES[difficulty]
        self.state = "playing"
        self.reset()

    def reset(self):
        self.walls = generate_maze(self.cols, self.rows)
        self.player = Player(0, 0)
        self.exit_rect = pygame.Rect(
            (self.cols - 1) * CELL + 5,
            (self.rows - 1) * CELL + 5,
            CELL - 10,
            CELL - 10,
        )
        self.start_time = time.time()
        self.elapsed = 0
        self.won = False
        self.time_recorded = False
        self.show_solution = False
        self.solution_path = []

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if self.state == "difficulty":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.start_difficulty("Easy")
                    elif event.key == pygame.K_2:
                        self.start_difficulty("Medium")
                    elif event.key == pygame.K_3:
                        self.start_difficulty("Hard")

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for name, rect in self.get_difficulty_buttons():
                        if rect.collidepoint(event.pos):
                            self.start_difficulty(name)
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_h:
                    self.show_solution = not self.show_solution
                    if self.show_solution:
                        self.solution_path = self.find_shortest_path()
                    else:
                        self.solution_path = []

        return True

    def get_difficulty_buttons(self):
        button_width = 260
        button_height = 60
        gap = 20
        total_height = len(DIFFICULTIES) * button_height + (len(DIFFICULTIES) - 1) * gap
        start_y = (HEIGHT - total_height) // 2
        rects = []

        for index, (name, (cols, rows)) in enumerate(DIFFICULTIES.items()):
            y = start_y + index * (button_height + gap)
            rect = pygame.Rect(WIDTH // 2 - button_width // 2, y, button_width, button_height)
            rects.append((name, rect))
        return rects

    def find_shortest_path(self):
        """Return the shortest wall-respecting path from the player to the exit."""
        start = (
            self.player.rect.centery // CELL,
            self.player.rect.centerx // CELL,
        )
        goal = (self.rows - 1, self.cols - 1)

        queue = deque([start])
        previous = {start: None}
        directions = [
            (-1, 0, 0),
            (1, 0, 1),
            (0, 1, 2),
            (0, -1, 3),
        ]

        while queue:
            r, c = queue.popleft()
            if (r, c) == goal:
                break

            for dr, dc, wall_index in directions:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                    continue
                if self.walls[r][c][wall_index]:
                    continue
                if (nr, nc) in previous:
                    continue
                previous[(nr, nc)] = (r, c)
                queue.append((nr, nc))

        if goal not in previous:
            return []

        path = []
        current = goal
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        return path

    def update(self):
        if self.state != "playing" or self.won:
            return

        keys = pygame.key.get_pressed()
        self.player.move(keys, self.walls, self.rows, self.cols)
        self.elapsed = time.time() - self.start_time

        if self.player.rect.colliderect(self.exit_rect):
            self.elapsed = time.time() - self.start_time
            self.won = True
            if not self.time_recorded:
                self.add_completion_time(self.elapsed)
                self.time_recorded = True

    def draw_maze(self):
        wall_w = 3
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c * CELL, r * CELL
                w = self.walls[r][c]
                if w[0]:
                    pygame.draw.line(self.screen, WALL_COLOR, (x, y), (x + CELL, y), wall_w)
                if w[1]:
                    pygame.draw.line(self.screen, WALL_COLOR, (x, y + CELL), (x + CELL, y + CELL), wall_w)
                if w[2]:
                    pygame.draw.line(self.screen, WALL_COLOR, (x + CELL, y), (x + CELL, y + CELL), wall_w)
                if w[3]:
                    pygame.draw.line(self.screen, WALL_COLOR, (x, y), (x, y + CELL), wall_w)

    def draw_difficulty_screen(self):
        self.screen.fill(BG)
        title = self.big_font.render("MAZE RUNNER", True, (30, 30, 50))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        subtitle = self.font.render("SELECT DIFFICULTY", True, (50, 50, 70))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 135))

        for index, (name, rect) in enumerate(self.get_difficulty_buttons(), start=1):
            pygame.draw.rect(self.screen, (30, 30, 50), rect, border_radius=8)
            label = self.font.render(
                f"{index}. {name}  ({DIFFICULTIES[name][0]}x{DIFFICULTIES[name][1]})",
                True,
                (240, 240, 240),
            )
            self.screen.blit(
                label,
                (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2),
            )

        hint = self.small_font.render("Click a button or press 1, 2, or 3", True, (70, 70, 80))
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 70))

    def draw(self):
        if self.state == "difficulty":
            self.draw_difficulty_screen()
            pygame.display.flip()
            return

        self.screen.fill(BG)
        self.draw_maze()

        if self.show_solution:
            for r, c in self.solution_path:
                x, y = c * CELL, r * CELL
                pygame.draw.rect(
                    self.screen,
                    (255, 215, 70),
                    (x + 7, y + 7, CELL - 14, CELL - 14),
                    border_radius=5,
                )

        pygame.draw.rect(self.screen, EXIT_COLOR, self.exit_rect, border_radius=4)
        ex_label = self.font.render("EXIT", True, (20, 80, 20))
        self.screen.blit(ex_label, (self.exit_rect.x + 2, self.exit_rect.y + 4))

        if not self.won:
            fog = pygame.Surface((self.cols * CELL, self.rows * CELL), pygame.SRCALPHA)
            fog.fill((0, 0, 0, 235))
            center = self.player.rect.center
            reveal_radius = self.fog_radius_cells * CELL
            pygame.draw.circle(fog, (0, 0, 0, 0), center, reveal_radius)
            self.screen.blit(fog, (0, 0))

        self.player.draw(self.screen)

        hud = pygame.Rect(0, self.rows * CELL, self.cols * CELL, 60)
        pygame.draw.rect(self.screen, (30, 30, 50), hud)
        time_surf = self.font.render(
            f"{self.difficulty}  Time: {self.elapsed:.1f}s   H = Hint   R = New Maze",
            True,
            (200, 200, 200),
        )
        self.screen.blit(time_surf, (10, self.rows * CELL + 18))

        if self.won:
            overlay = pygame.Surface((self.cols * CELL, self.rows * CELL), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))

            msg = self.big_font.render(f"Solved in {self.elapsed:.1f}s!", True, (80, 240, 80))
            self.screen.blit(msg, (self.cols * CELL // 2 - msg.get_width() // 2, 35))

            title = self.font.render("BEST 5 TIMES", True, (255, 215, 70))
            self.screen.blit(title, (self.cols * CELL // 2 - title.get_width() // 2, 95))

            for index, completion_time in enumerate(self.leaderboard, start=1):
                entry = self.font.render(
                    f"{index}. {completion_time:.1f}s",
                    True,
                    (230, 230, 230),
                )
                self.screen.blit(
                    entry,
                    (self.cols * CELL // 2 - entry.get_width() // 2, 130 + (index - 1) * 28),
                )

            sub = self.font.render("Press R for a new maze", True, (200, 200, 200))
            self.screen.blit(sub, (self.cols * CELL // 2 - sub.get_width() // 2, self.rows * CELL - 35))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
