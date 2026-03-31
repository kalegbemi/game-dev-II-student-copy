import pygame
import random
import json
import math
from pathlib import Path

TILE = 32
DATA_FILE = "game_stats.json"
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "images"

# Background images are selected by index
BACKGROUND_FILES = [
    "background1.png",
    "background2.png",
    "background3.png",
]

# Spawnable object image files
SPRITE_FILES = {
    "captain": "captain.png",
    "knight": "knighta.png",
    "munchkin": "munchkin.png",
    "skeleton": "skeleton.png",
    "gold_coin": "gold_coin.png",
    "lightstone": "silver_coin.png",
    "potion-medium": "gold_coin2.png",
    "wall": "wall.png",
}

# Fallback colors if image is missing
FALLBACK_COLORS = {
    "captain": (40, 120, 255),
    "knight": (40, 120, 255),
    "munchkin": (200, 60, 60),
    "skeleton": (180, 180, 180),
    "gold_coin": (60, 220, 220),
    "lightstone": (255, 255, 120),
    "potion-medium": (170, 80, 220),
    "wall": (90, 70, 50),
}


def load_image(filename, size=None, fallback_color=(255, 0, 255)):
    path = IMAGE_DIR / filename
    print(f"loading file: {path}")
    print(f"exists: {path.exists()}")

    try:
        img = pygame.image.load(str(path)).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception as e:
        print(f"Failed to load image: {e}")
        surf = pygame.Surface(size if size else (TILE, TILE), pygame.SRCALPHA)
        surf.fill(fallback_color)
        return surf


class Entity(pygame.sprite.Sprite):
    def __init__(self, kind, x, y, size=(24, 24), speed=0):
        super().__init__()
        filename = SPRITE_FILES.get(kind, "")
        color = FALLBACK_COLORS.get(kind, (255, 0, 255))
        self.image = load_image(filename, size, color)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.kind = kind
        self.speed = speed


class Player(Entity):
    def __init__(self, kind, x, y):
        super().__init__(kind, x, y, size=(50, 50), speed=5)
        self.maxSpeed = 5
        self.maxHealth = 100
        self.attackDamage = 20
        self.health = self.maxHealth


class Enemy(Entity):
    def __init__(self, kind, x, y):
        super().__init__(kind, x, y, size=(45, 45), speed=2)
        self.chase_distance = 200

    def chase_player(self, player, walls):
        if not player:
            return

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)

        if distance == 0 or distance > self.chase_distance:
            return

        move_x = (dx / distance) * self.speed
        move_y = (dy / distance) * self.speed

        old_rect = self.rect.copy()

        self.rect.x += round(move_x)
        if pygame.sprite.spritecollideany(self, walls):
            self.rect.x = old_rect.x

        self.rect.y += round(move_y)
        if pygame.sprite.spritecollideany(self, walls):
            self.rect.y = old_rect.y


class Game:
    def __init__(self, width=25, height=18, title="Game Dev with Pygame"):
        pygame.init()
        self.width = width
        self.height = height
        self.screen_width = width * TILE
        self.screen_height = height * TILE
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.big_font = pygame.font.SysFont(None, 42)

        self.player = None
        self.background = None

        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.collectibles = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()

        self.stats = {"defeated": 0, "collected": 0, "wins": 0, "losses": 0}
        self.tracked = []
        self.goals = []
        self.running = True
        self.game_over = False
        self.win = False
        self.time_limit = None
        self.start_ticks = pygame.time.get_ticks()

    def grid_to_px(self, x, y):
        return x * TILE, y * TILE

    def spawnMaze(self, background_index=0, border=1):
        if 0 <= background_index < len(BACKGROUND_FILES):
            bg_name = BACKGROUND_FILES[background_index]
        else:
            bg_name = BACKGROUND_FILES[0]

        self.background = load_image(bg_name, (self.screen_width, self.screen_height), (60, 150, 80))

        for gx in range(self.width):
            for gy in range(self.height):
                if gx < border or gy < border or gx >= self.width - border or gy >= self.height - border:
                    px, py = self.grid_to_px(gx, gy)
                    wall = Entity("wall", px, py, size=(TILE, TILE))
                    self.walls.add(wall)
                    self.all_sprites.add(wall)

    def spawnPlayerXY(self, kind, x, y):
        px, py = self.grid_to_px(x, y)
        self.player = Player(kind, px + 4, py + 4)
        self.all_sprites.add(self.player)
        return self.player

    def spawnXY(self, kind, x, y):
        px, py = self.grid_to_px(x, y)

        if kind in ("munchkin", "skeleton"):
            obj = Enemy(kind, px + 5, py + 5)
            self.enemies.add(obj)
        elif kind in ("gold_coin", "lightstone", "potion-medium"):
            obj = Entity(kind, px + 8, py + 8, size=(18, 18))
            self.collectibles.add(obj)
        else:
            obj = Entity(kind, px + 8, py + 8)

        self.all_sprites.add(obj)
        return obj

    def spawnRandom(self, kind, count=1):
        for _ in range(count):
            x = random.randint(1, self.width - 2)
            y = random.randint(1, self.height - 2)
            self.spawnXY(kind, x, y)

    def addDefeatGoal(self, count=1):
        self.goals.append(("Defeat", lambda g: g.stats["defeated"] >= count, f"Defeat {count}"))

    def addCollectGoal(self, count=1):
        self.goals.append(("Collect", lambda g: g.stats["collected"] >= count, f"Collect {count}"))

    def addSurviveGoal(self, seconds=20):
        self.time_limit = seconds
        self.goals.append(("Survive", lambda g: g.time_left() <= 0, f"Survive {seconds}s"))

    def addCustomGoal(self, label, rule):
        self.goals.append(("Custom", rule, label))

    def time_left(self):
        if self.time_limit is None:
            return 0
        elapsed = (pygame.time.get_ticks() - self.start_ticks) // 1000
        return max(0, self.time_limit - elapsed)

    def save_stats(self):
        Path(DATA_FILE).write_text(json.dumps(self.stats, indent=2))

    def load_stats(self):
        path = Path(DATA_FILE)
        if path.exists():
            self.stats.update(json.loads(path.read_text()))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.save_stats()
                elif event.key == pygame.K_l:
                    self.load_stats()
                elif event.key == pygame.K_SPACE and self.player:
                    hits = pygame.sprite.spritecollide(self.player, self.enemies, dokill=True)
                    if hits:
                        self.stats["defeated"] += len(hits)

    def move_player(self):
        if not self.player:
            return

        keys = pygame.key.get_pressed()
        old_rect = self.player.rect.copy()
        speed = self.player.maxSpeed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.rect.x -= speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.rect.x += speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.player.rect.y -= speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.player.rect.y += speed

        if pygame.sprite.spritecollideany(self.player, self.walls):
            self.player.rect = old_rect

    def move_enemies(self):
        for enemy in self.enemies:
            enemy.chase_player(self.player, self.walls)

    def update(self):
        self.move_player()
        self.move_enemies()

        found = pygame.sprite.spritecollide(self.player, self.collectibles, dokill=True)
        if found:
            self.stats["collected"] += len(found)

        for enemy in self.enemies:
            if self.player and enemy.rect.colliderect(self.player.rect):
                self.player.health -= 1

        for _, rule, _ in self.goals:
            if rule(self):
                self.win = True

        if self.player and self.player.health <= 0:
            self.game_over = True
            self.stats["losses"] += 1

        if self.win:
            self.game_over = True
            self.stats["wins"] += 1

    def draw_background(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((50, 120, 70))

    def draw_ui(self):
        y = 6
        for name in self.tracked:
            value = self.stats.get(name, getattr(self, name, ""))
            txt = self.font.render(f"{name}: {value}", True, (255, 255, 255))
            self.screen.blit(txt, (8, y))
            y += 24

        if self.player:
            hp = self.font.render(f"health: {self.player.health}", True, (255, 255, 255))
            self.screen.blit(hp, (8, y))
            y += 24

        if self.time_limit is not None:
            txt = self.font.render(f"time_left: {self.time_left()}", True, (255, 255, 255))
            self.screen.blit(txt, (8, y))
            y += 24

        goals = " | ".join(label for _, _, label in self.goals)
        txt = self.font.render(goals, True, (255, 255, 0))
        self.screen.blit(txt, (8, self.screen_height - 28))

    def draw_end(self):
        msg = "YOU WIN!" if self.win else "GAME OVER"
        txt = self.big_font.render(msg, True, (255, 255, 255))
        rect = txt.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        self.screen.blit(txt, rect)

    def run(self):
        while self.running:
            self.handle_events()

            if not self.game_over:
                self.update()

            self.draw_background()
            self.all_sprites.draw(self.screen)
            self.draw_ui()

            if self.game_over:
                self.draw_end()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()


class UI:
    def track(self, game, name):
        if name not in game.tracked:
            game.tracked.append(name)