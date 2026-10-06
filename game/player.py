import pygame
from game.maze import CELL

SPEED = 3


class Player:
    def __init__(self, r, c):
        self.r = r
        self.c = c
        x = c * CELL + CELL // 2
        y = r * CELL + CELL // 2
        self.rect = pygame.Rect(x - 10, y - 10, 20, 20)
        self.color = (60, 120, 220)

    def move(self, keys, walls, rows, cols):
        dx, dy = 0, 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = SPEED

        # Move horizontally only if there is no wall collision.
        new_rect = self.rect.move(dx, 0)
        if not self._hits_wall(new_rect, walls, rows, cols):
            self.rect = new_rect

        # Move vertically only if there is no wall collision.
        new_rect = self.rect.move(0, dy)
        if not self._hits_wall(new_rect, walls, rows, cols):
            self.rect = new_rect

    def _hits_wall(self, rect, walls, rows, cols):
        # Check whether any part of the player's rectangle
        # is outside the maze.
        if rect.left < 0 or rect.right > cols * CELL:
            return True

        if rect.top < 0 or rect.bottom > rows * CELL:
            return True

        # Determine the range of cells occupied by the player.
        left_col = rect.left // CELL
        right_col = (rect.right - 1) // CELL
        top_row = rect.top // CELL
        bottom_row = (rect.bottom - 1) // CELL

        # Check the maze walls around every cell touched by the player.
        for row in range(top_row, bottom_row + 1):
            for col in range(left_col, right_col + 1):
                cell_x = col * CELL
                cell_y = row * CELL

                north, south, east, west = walls[row][col]

                # Player is crossing the north wall.
                if north and rect.top < cell_y:
                    return True

                # Player is crossing the south wall.
                if south and rect.bottom > cell_y + CELL:
                    return True

                # Player is crossing the west wall.
                if west and rect.left < cell_x:
                    return True

                # Player is crossing the east wall.
                if east and rect.right > cell_x + CELL:
                    return True

        return False

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)