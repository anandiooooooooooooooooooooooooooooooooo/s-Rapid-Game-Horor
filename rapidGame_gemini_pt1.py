import pygame
import math
import random
import array
import sys

# --- KONFIGURASI ENGINE ---
VIRTUAL_WIDTH = 320
VIRTUAL_HEIGHT = 240
FPS = 10
TILE_SIZE = 20  # Lebih kecil agar map terasa lebih luas

# Palet Warna
COLOR_BG = (10, 10, 10)
COLOR_SCAN_WALL = (0, 255, 100)   # Hijau
COLOR_SCAN_ENEMY = (255, 50, 50)  # Merah
COLOR_SCAN_EXIT = (50, 100, 255)  # Biru
COLOR_TEXT = (200, 200, 200)

# --- MODUL 1: AUDIO SYNTHESIZER ---
class SoundEngine:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.mixer.init()
        self.sounds = {}
        self._generate_library()

    def _generate_wave(self, func, duration, volume=0.5, freq=440):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = func(t, freq)
            buf[i] = int(val * volume * 32767)
        return pygame.mixer.Sound(buffer=buf)

    def _generate_library(self):
        # 1. Scanner Ping (Sonar style)
        self.sounds['ping'] = self._generate_wave(lambda t, f: math.sin(2 * math.pi * f * t) * math.exp(-6 * t), 0.6, 0.4, 800)
        # 2. Step (Noise burst pendek)
        self.sounds['step'] = self._generate_wave(lambda t, f: random.uniform(-1, 1) * math.exp(-20 * t), 0.1, 0.15)
        # 3. Scream (Sawtooth glitch)
        def screech(t, f):
            mod = f + random.uniform(-50, 50)
            return (2 * (t * mod % 1) - 1) * 0.8
        self.sounds['scream'] = self._generate_wave(screech, 0.8, 0.6, 150)
        # 4. Win (Harmonic)
        self.sounds['win'] = self._generate_wave(lambda t, f: (math.sin(2*math.pi*f*t) + math.sin(2*math.pi*(f*1.5)*t)) * 0.5, 1.5, 0.4, 440)

    def play(self, name):
        if name in self.sounds: self.sounds[name].play()

# --- MODUL 2: DISPLAY & CAMERA ---
class DisplayManager:
    def __init__(self):
        pygame.init()
        self.info = pygame.display.Info()
        self.monitor_w = self.info.current_w
        self.monitor_h = self.info.current_h
        self.scale = 3
        self.window_w = VIRTUAL_WIDTH * self.scale
        self.window_h = VIRTUAL_HEIGHT * self.scale
        self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)
        self.virtual_surface = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        pygame.display.set_caption("LIDAR: The Silent Void")
        self.font = pygame.font.SysFont("monospace", 10)
        self.fullscreen = False

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((self.monitor_w, self.monitor_h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.window_w, self.window_h), pygame.RESIZABLE)

    def render(self):
        current_w, current_h = self.screen.get_size()
        scaled_surf = pygame.transform.scale(self.virtual_surface, (current_w, current_h))
        self.screen.blit(scaled_surf, (0, 0))
        pygame.display.flip()

    def draw_text_center(self, text, y_offset=0, color=COLOR_TEXT):
        surf = self.font.render(text, False, color)
        rect = surf.get_rect(center=(VIRTUAL_WIDTH // 2, VIRTUAL_HEIGHT // 2 + y_offset))
        self.virtual_surface.blit(surf, rect)

# --- MODUL 3: WORLD GENERATION ---
class Map:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cols = width // TILE_SIZE
        self.rows = height // TILE_SIZE
        self.grid = []
        self.exit_rect = None
        self.generate_caves()

    def generate_caves(self):
        # Cellular Automata
        self.grid = [[1 if random.random() < 0.40 else 0 for _ in range(self.cols)] for _ in range(self.rows)]
        for _ in range(4):
            new_grid = [row[:] for row in self.grid]
            for r in range(1, self.rows-1):
                for c in range(1, self.cols-1):
                    walls = self._count_walls(r, c)
                    if walls > 4: new_grid[r][c] = 1
                    elif walls < 4: new_grid[r][c] = 0
            self.grid = new_grid

        # Border Walls
        for r in range(self.rows):
            for c in range(self.cols):
                if r == 0 or c == 0 or r == self.rows-1 or c == self.cols-1:
                    self.grid[r][c] = 1

    def place_exit(self, player_x, player_y):
        # Cari lokasi exit jauh dari player
        while True:
            c = random.randint(1, self.cols-2)
            r = random.randint(1, self.rows-2)
            if self.grid[r][c] == 0:
                # Cek jarak
                dist = math.hypot(c*TILE_SIZE - player_x, r*TILE_SIZE - player_y)
                if dist > VIRTUAL_WIDTH * 0.8: # Minimal jarak tertentu
                    self.exit_rect = pygame.Rect(c*TILE_SIZE, r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    break

    def _count_walls(self, r, c):
        count = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                if self.grid[r+i][c+j] == 1: count += 1
        return count

    def is_wall(self, x, y):
        c = int(x // TILE_SIZE)
        r = int(y // TILE_SIZE)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c] == 1
        return True

    def is_exit(self, x, y):
        if self.exit_rect:
            return self.exit_rect.collidepoint(x, y)
        return False

# --- MODUL 4: ENTITIES & LOGIC ---
class Entity:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 35
        self.hunt_speed = 70
        self.radius = 12
        self.state = "IDLE"
        self.hunt_timer = 0

    def update(self, dt, player_x, player_y, is_scanning, game_map):
        dist = math.hypot(player_x - self.x, player_y - self.y)

        if is_scanning and dist < 300: # Hearing range
            self.state = "HUNT"
            self.hunt_timer = 3.0

        target_x, target_y = self.x, self.y
        current_speed = self.speed

        if self.state == "HUNT":
            current_speed = self.hunt_speed
            target_x, target_y = player_x, player_y
            self.hunt_timer -= dt
            if self.hunt_timer <= 0: self.state = "IDLE"
        else:
            # Jitter movement
            if random.random() < 0.05:
                target_x = self.x + random.uniform(-40, 40)
                target_y = self.y + random.uniform(-40, 40)

        # Move Logic
        angle = math.atan2(target_y - self.y, target_x - self.x)
        new_x = self.x + math.cos(angle) * current_speed * dt
        new_y = self.y + math.sin(angle) * current_speed * dt

        # Simple collision with walls for enemy
        if not game_map.is_wall(new_x, new_y):
            self.x, self.y = new_x, new_y

    def check_kill(self, px, py):
        return math.hypot(px - self.x, py - self.y) < self.radius

class LidarScanner:
    def __init__(self, game_map):
        self.game_map = game_map
        self.points = [] # [x, y, intensity, r, g, b]
        self.max_rays = 180 # Ray count (optimized)
        self.scan_radius = 200

    def pulse(self, px, py, angle_facing, entity):
        start_angle = 0
        step = (math.pi * 2) / self.max_rays

        for i in range(self.max_rays):
            angle = start_angle + (i * step)
            sin_a = math.sin(angle)
            cos_a = math.cos(angle)

            for depth in range(4, self.scan_radius, 4):
                tx = px + cos_a * depth
                ty = py + sin_a * depth

                # Cek Entity
                dist_ent = math.hypot(tx - entity.x, ty - entity.y)
                if dist_ent < entity.radius:
                    self._add_point(tx, ty, COLOR_SCAN_ENEMY)
                    break

                # Cek Exit
                if self.game_map.is_exit(tx, ty):
                    self._add_point(tx, ty, COLOR_SCAN_EXIT)
                    break

                # Cek Wall
                if self.game_map.is_wall(tx, ty):
                    self._add_point(tx, ty, COLOR_SCAN_WALL)
                    break

    def _add_point(self, x, y, color):
        # Add jitter
        nx = x + random.uniform(-1, 1)
        ny = y + random.uniform(-1, 1)
        self.points.append([nx, ny, 255, color])

    def update(self, dt):
        decay = 180 * dt
        # Filter points: keep only if intensity > 0
        new_points = []
        for p in self.points:
            p[2] -= decay
            if p[2] > 0:
                new_points.append(p)
        self.points = new_points

    def render(self, surface):
        for p in self.points:
            intensity = p[2] / 255.0
            col = p[3]
            r = int(col[0] * intensity)
            g = int(col[1] * intensity)
            b = int(col[2] * intensity)
            try:
                surface.set_at((int(p[0]), int(p[1])), (r, g, b))
            except: pass

class Game:
    def __init__(self):
        self.display = DisplayManager()
        self.audio = SoundEngine()
        self.clock = pygame.time.Clock()
        self.state = "MENU" # MENU, PLAY, GAMEOVER, WIN
        self.reset_game()

    def reset_game(self):
        self.map = Map(VIRTUAL_WIDTH, VIRTUAL_HEIGHT)

        # Spawn Player safe
        while True:
            self.px = random.randint(TILE_SIZE, VIRTUAL_WIDTH - TILE_SIZE)
            self.py = random.randint(TILE_SIZE, VIRTUAL_HEIGHT - TILE_SIZE)
            if not self.map.is_wall(self.px, self.py): break

        self.p_angle = 0
        self.map.place_exit(self.px, self.py)

        # Spawn Entity Far
        while True:
            self.ex = random.randint(TILE_SIZE, VIRTUAL_WIDTH - TILE_SIZE)
            self.ey = random.randint(TILE_SIZE, VIRTUAL_HEIGHT - TILE_SIZE)
            dist = math.hypot(self.ex - self.px, self.ey - self.py)
            if not self.map.is_wall(self.ex, self.ey) and dist > 100: break

        self.entity = Entity(self.ex, self.ey)
        self.scanner = LidarScanner(self.map)
        self.step_timer = 0

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()

            if self.state == "PLAY":
                self.update_play(dt)

            self.render()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f: self.display.toggle_fullscreen()

                if self.state == "MENU":
                    if event.key == pygame.K_SPACE:
                        self.state = "PLAY"
                        self.audio.play('ping')

                elif self.state == "PLAY":
                    if event.key == pygame.K_SPACE:
                        self.audio.play('ping')
                        self.scanner.pulse(self.px, self.py, self.p_angle, self.entity)
                        self.entity.update(0.016, self.px, self.py, True, self.map) # Instant reaction

                elif self.state in ["GAMEOVER", "WIN"]:
                    if event.key == pygame.K_r:
                        self.reset_game()
                        self.state = "PLAY"

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        speed = 50 * dt

        if keys[pygame.K_w]: dy = -speed
        if keys[pygame.K_s]: dy = speed
        if keys[pygame.K_a]: dx = -speed
        if keys[pygame.K_d]: dx = speed

        # Movement & Collision
        if dx != 0 or dy != 0:
            if not self.map.is_wall(self.px + dx, self.py): self.px += dx
            if not self.map.is_wall(self.px, self.py + dy): self.py += dy

            # Step sound
            self.step_timer -= dt
            if self.step_timer <= 0:
                self.audio.play('step')
                self.step_timer = 0.5

        # Check Win
        if self.map.is_exit(self.px, self.py):
            self.state = "WIN"
            self.audio.play('win')

        # Update Systems
        self.scanner.update(dt)
        self.entity.update(dt, self.px, self.py, False, self.map)

        # Check Die
        if self.entity.check_kill(self.px, self.py):
            self.state = "GAMEOVER"
            self.audio.play('scream')

    def render(self):
        self.display.virtual_surface.fill(COLOR_BG)

        if self.state == "MENU":
            self.display.draw_text_center("LIDAR: THE SILENT VOID", -20)
            self.display.draw_text_center("PRESS SPACE TO START", 10)
            self.display.draw_text_center("WASD: Move | SPACE: Scan", 30)
            self.display.draw_text_center("FIND THE BLUE SIGNAL. AVOID THE RED.", 50)

        elif self.state == "PLAY":
            self.scanner.render(self.display.virtual_surface)
            # Draw Player
            pygame.draw.circle(self.display.virtual_surface, (200, 200, 255), (int(self.px), int(self.py)), 2)

        elif self.state == "GAMEOVER":
            self.display.virtual_surface.fill((50, 0, 0)) # Red Flash
            self.display.draw_text_center("SIGNAL LOST", -10)
            self.display.draw_text_center("PRESS R TO RETRY", 10)

        elif self.state == "WIN":
            self.display.virtual_surface.fill((0, 50, 100)) # Blue Flash
            self.display.draw_text_center("EXIT FOUND", -10)
            self.display.draw_text_center("PRESS R TO PLAY AGAIN", 10)

        self.display.render()

if __name__ == "__main__":
    Game().run()
