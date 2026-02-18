import pygame
import sys
import random
import time
import math
import json
import os
try:
    import numpy as np
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

pygame.init()
if SOUND_AVAILABLE:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu - FINAL FIXED 5.1")

clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 26)
FONT_SMALL = pygame.font.SysFont("consolas", 19)
FONT_TINY = pygame.font.SysFont("consolas", 15)
FONT_BIG = pygame.font.SysFont("consolas", 42, bold=True)

BLACK = (5, 0, 0)
DARK_RED = (80, 0, 0)
BLOOD_RED = (155, 0, 0)
WHITE = (255, 255, 255)
GRAY = (45, 45, 45)
LIGHT_GRAY = (90, 90, 90)
YELLOW_GLOW = (255, 220, 60)

PLAYER_NAME = "Lzroars23"
loop_count = 0
sound_enabled = SOUND_AVAILABLE
show_objective = True
save_file = "rumah_save.json"

objectives = {"collected": 0}
objective_text = "Kumpulkan 3 item: Old Key (Ruang Tamu), Candle (Dapur), Photo Fragment (Kamar Tidur). Kembali ke Ruang Depan & tekan E untuk keluar!"

class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 200
        self.y = 200
        self.size = 20
        self.speed = 4.3
        self.sanity = 75.0
        self.flashlight_battery = 100.0
        self.flashlight_on = True

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(70, min(WIDTH - 70, self.x))
        self.y = max(70, min(HEIGHT - 70, self.y))

    def draw(self, surface):
        pygame.draw.circle(surface, (25, 25, 25), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x), int(self.y)), self.size, 4)

class TheStalker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 1100
        self.y = 600
        self.size = 27
        self.speed = 2.7
        self.active = False
        self.spawn_cooldown = 50
        self.pulse = 0.0

    def update(self, player, current_room, sanity, cone_points):
        if sanity >= 65:
            self.active = False
            return
        self.active = True
        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= 1
            return
        try:
            dx = player.x - self.x
            dy = player.y - self.y
            dist = math.hypot(dx, dy)
            if dist < 24:
                player.sanity -= 21
                self.spawn_cooldown = 120
                return
            speed_mod = 1.0
            if cone_points and len(cone_points) == 3:
                try:
                    if point_in_polygon((self.x, self.y), cone_points):
                        speed_mod = 0.58
                except:
                    pass
            if dist < 260 and current_room in ["basement", "bedroom", "kitchen"]:
                boost = 1.0 + (100 - sanity) / 72
                self.x += (dx / dist) * self.speed * boost * speed_mod
                self.y += (dy / dist) * self.speed * boost * speed_mod
        except:
            self.active = False

    def draw(self, surface):
        if not self.active: return
        self.pulse = (self.pulse + 0.19) % (math.pi * 2)
        eye_size = 7.5 + math.sin(self.pulse) * 2.8
        pygame.draw.circle(surface, (8, 8, 8), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x - 9), int(self.y - 7)), int(eye_size))
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x + 9), int(self.y - 7)), int(eye_size))

    def check_collision(self, player):
        return math.hypot(self.x - player.x, self.y - player.y) < self.size + player.size + 5

class BloodDrip:
    def __init__(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-40, 100)
        self.length = random.randint(20, 50)
        self.speed = random.uniform(2.0, 4.8)
        self.width = random.randint(2, 6)
        self.alpha = 190

    def update(self):
        self.y += self.speed
        self.alpha -= 1.4

    def draw(self, surface):
        if self.alpha > 0:
            color = (*BLOOD_RED, int(self.alpha))
            pygame.draw.line(surface, color, (self.x, self.y), (self.x, self.y + self.length), self.width)

class Room:
    def __init__(self, name, desc, color, whispers, items=None):
        self.name = name
        self.desc = desc
        self.color = color
        self.whispers = whispers
        self.items = items or []

rooms = {
    "entrance": Room("Ruang Depan", "Pintu depan tertutup...", (25, 13, 13), ["Kamu ingat saat kecil..."]),
    "living": Room("Ruang Tamu", "Foto keluarga...", (18, 8, 8), ["Nama Anda tertulis..."], ["Old Key"]),
    "kitchen": Room("Dapur", "Pisau masih berdarah...", (36, 13, 3), ["Kakek Anda mati di sini..."], ["Candle"]),
    "bedroom": Room("Kamar Tidur", "Tempat tidur disiapkan...", (13, 3, 13), [f"{PLAYER_NAME}... tidurlah."], ["Photo Fragment"]),
    "basement": Room("Ruang Bawah Tanah", "Tangga menurun...", (8, 3, 8), ["Turunlah..."])
}

current_room = "entrance"
room_rects = {
    "entrance": pygame.Rect(50, 50, 400, 250),
    "living": pygame.Rect(550, 50, 400, 250),
    "kitchen": pygame.Rect(50, 380, 300, 300),
    "bedroom": pygame.Rect(450, 380, 250, 300),
    "basement": pygame.Rect(800, 520, 200, 180)
}

player = Player()
stalker = TheStalker()
blood_drips = []
inventory = []
selected_item = None
game_state = "menu"
last_whisper_time = time.time()
whisper_text = ""
whisper_alpha = 0
sanity_drain_rate = 0.0088
shake = 0.0
flicker = 1.0
last_flicker_time = time.time()
typewriter_text = ""
typewriter_index = 0
typewriter_timer = 0

resolution_options = [
    ("1 - 800x600", 800, 600),
    ("2 - 1024x768", 1024, 768),
    ("3 - 1280x720 (Rekomendasi)", 1280, 720),
    ("4 - Fullscreen", 0, 0)
]

def play_procedural_sound(freq, duration, volume=0.25, typ="sine"):
    if not sound_enabled or not SOUND_AVAILABLE: return
    try:
        sample_rate = 44100
        frames = int(duration * sample_rate)
        t = np.linspace(0, duration, frames)
        if typ == "sine": wave = np.sin(2 * np.pi * t * freq)
        else: wave = 2 * (t * freq - np.floor(t * freq)) - 1
        arr = (wave * 32767 * volume).astype(np.int16)
        sound = pygame.sndarray.make_sound(arr)
        sound.play()
    except:
        pass

def point_in_polygon(point, poly):
    if poly is None or len(poly) != 3:
        return False
    try:
        x, y = point
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    except:
        return False

def get_room_at_pos(x, y):
    for rname, rect in room_rects.items():
        if rect.collidepoint(x, y):
            return rname
    return current_room

def draw_text(surface, text, font, color, pos, alpha=255):
    txt = font.render(text, True, color)
    txt.set_alpha(alpha)
    surface.blit(txt, pos)

def save_game():
    data = {"loop_count": loop_count, "inventory": inventory, "sanity": player.sanity, "current_room": current_room}
    with open(save_file, "w") as f:
        json.dump(data, f)

def load_game():
    global loop_count, current_room, inventory
    if os.path.exists(save_file):
        with open(save_file, "r") as f:
            data = json.load(f)
        loop_count = data["loop_count"]
        inventory = data["inventory"]
        player.sanity = data["sanity"]
        current_room = data["current_room"]
        return True
    return False

def respawn():
    global game_state, loop_count
    player.reset()
    stalker.reset()
    current_room = "entrance"
    blood_drips.clear()
    game_state = "playing"
    loop_count += 1

running = True
while running:
    dt = clock.tick(60) / 1000.0
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if game_state == "menu":
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    idx = int(event.unicode) - 1
                    name, w, h = resolution_options[idx]
                    if w == 0:
                        info = pygame.display.Info()
                        w, h = info.current_w, info.current_h
                        screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                    WIDTH, HEIGHT = w, h
                    game_state = "playing"
            elif game_state == "playing":
                if event.key == pygame.K_f: player.flashlight_on = not player.flashlight_on
                if event.key == pygame.K_m: sound_enabled = not sound_enabled
                if event.key == pygame.K_TAB: show_objective = not show_objective
                if event.key == pygame.K_s: save_game()
                if event.key == pygame.K_l: load_game()
                if event.key == pygame.K_e and current_room == "entrance" and objectives["collected"] >= 3:
                    game_state = "ending"
                    typewriter_text = "ANDA BERHASIL KELUAR DARI RUMAH YANG TAHU NAMAMU...\nRumah tidak lagi tahu namamu..."
                    typewriter_index = 0
                    typewriter_timer = time.time()
                if event.key == pygame.K_1 and len(inventory) > 0: selected_item = 0
                if event.key == pygame.K_2 and len(inventory) > 1: selected_item = 1
                if event.key == pygame.K_3 and len(inventory) > 2: selected_item = 2
            elif game_state in ("game_over", "ending"):
                if event.key == pygame.K_r:
                    respawn()
                if event.key == pygame.K_q:
                    running = False

    if game_state == "menu":
        draw_text(screen, "PILIH RESOLUSI", FONT_BIG, WHITE, (WIDTH//2 - 220, 140))
        for i, (txt, _, _) in enumerate(resolution_options):
            col = BLOOD_RED if i == 2 else WHITE
            draw_text(screen, txt, FONT, col, (WIDTH//2 - 180, 260 + i*65))
        if not SOUND_AVAILABLE:
            draw_text(screen, "Sound DISABLED - Jalankan: pip install numpy", FONT_SMALL, BLOOD_RED, (WIDTH//2 - 280, HEIGHT - 100))
        pygame.display.flip()
        continue

    if game_state == "playing":
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
            player.move(dx, dy)

        new_room = get_room_at_pos(player.x, player.y)
        if new_room != current_room:
            current_room = new_room
            whisper_text = rooms[current_room].desc
            whisper_alpha = 255

        if player.flashlight_on:
            player.flashlight_battery -= 0.075
            if player.flashlight_battery <= 0:
                player.flashlight_on = False
        else:
            player.flashlight_battery = min(100, player.flashlight_battery + 0.04)

        player.sanity -= sanity_drain_rate
        if random.random() < 0.012: player.sanity -= 0.7
        player.sanity = max(0, min(100, player.sanity))

        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            for rname, rect in room_rects.items():
                if rect.collidepoint(mx, my) and rname == current_room:
                    for item in rooms[current_room].items[:]:
                        if random.random() < 0.92:
                            inventory.append(item)
                            rooms[current_room].items.remove(item)
                            objectives["collected"] += 1
                            break

        cone_points = None
        if player.flashlight_on and player.flashlight_battery > 5:
            angle = math.atan2(my - player.y, mx - player.x)
            length = 370
            half = math.radians(27)
            p1 = (player.x + math.cos(angle - half) * length, player.y + math.sin(angle - half) * length)
            p2 = (player.x + math.cos(angle + half) * length, player.y + math.sin(angle + half) * length)
            cone_points = [(player.x, player.y), p1, p2]

        stalker.update(player, current_room, player.sanity, cone_points)

        if stalker.active and stalker.check_collision(player):
            player.sanity -= 21
            whisper_text = f"{PLAYER_NAME}... aku sudah di sini."
            whisper_alpha = 255
            stalker.spawn_cooldown = 130
            if sound_enabled: play_procedural_sound(110, 0.6, 0.45, "saw")

        if stalker.active:
            dist = math.hypot(stalker.x - player.x, stalker.y - player.y)
            if dist < 140: shake = 9.0
            elif dist < 220: shake = 4.0

        if time.time() - last_whisper_time > random.uniform(6, 13):
            if player.sanity < 48 or stalker.active:
                whisper_text = random.choice(rooms[current_room].whispers)
                whisper_alpha = 255
                if sound_enabled: play_procedural_sound(random.randint(700, 1300), 0.4, 0.22)
            last_whisper_time = time.time()

        if len(blood_drips) < 16 and player.sanity < 52 and random.random() < 0.19:
            blood_drips.append(BloodDrip())
        for drip in blood_drips[:]:
            drip.update()
            if drip.alpha <= 0 or drip.y > HEIGHT:
                blood_drips.remove(drip)

        if time.time() - last_flicker_time > random.uniform(0.08, 0.3):
            flicker = random.uniform(0.74, 1.0)
            last_flicker_time = time.time()

        if player.sanity <= 0:
            game_state = "game_over"

    # DRAWING
    room_color = tuple(int(c * flicker * 1.13) for c in rooms[current_room].color)
    pygame.draw.rect(screen, room_color, (0, 0, WIDTH, HEIGHT))

    for rect in room_rects.values():
        pygame.draw.rect(screen, (32, 12, 12), rect, 7)

    player.draw(screen)
    stalker.draw(screen)

    ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(ambient, (38, 28, 18, 48), (int(player.x), int(player.y)), 210)
    screen.blit(ambient, (0, 0))

    dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark.fill((0, 0, 0, 132))
    if cone_points and player.flashlight_on:
        pygame.draw.polygon(dark, (0, 0, 0, 0), cone_points)
        pygame.draw.polygon(dark, (58, 42, 28, 60), cone_points, 24)
    screen.blit(dark, (0, 0))

    for drip in blood_drips:
        drip.draw(screen)

    draw_text(screen, rooms[current_room].name, FONT, WHITE, (30, 25))

    if whisper_alpha > 0:
        whisper_alpha = max(0, whisper_alpha - 4)
        txt_color = BLOOD_RED if player.sanity < 38 else WHITE
        draw_text(screen, whisper_text, FONT, txt_color, (WIDTH//2 - 260, HEIGHT - 95), whisper_alpha)

    # Sanity & battery bar
    bar_w = 380
    fill_s = int((player.sanity / 100) * bar_w)
    pygame.draw.rect(screen, GRAY, (WIDTH//2 - bar_w//2, 35, bar_w, 20))
    pygame.draw.rect(screen, BLOOD_RED, (WIDTH//2 - bar_w//2, 35, fill_s, 20))
    draw_text(screen, f"Sanity: {int(player.sanity)}%", FONT_SMALL, WHITE, (WIDTH//2 - 85, 8))

    bat_fill = int(player.flashlight_battery)
    pygame.draw.rect(screen, LIGHT_GRAY, (WIDTH - 210, 35, 180, 14))
    pygame.draw.rect(screen, (210, 190, 70), (WIDTH - 210, 35, bat_fill * 1.8, 14))
    draw_text(screen, "FLASHLIGHT", FONT_TINY, WHITE, (WIDTH - 205, 13))

    # Inventory
    pygame.draw.rect(screen, (20, 20, 20), (50, HEIGHT - 75, WIDTH - 100, 60))
    for i, item in enumerate(inventory):
        col = BLOOD_RED if i == selected_item else WHITE
        pygame.draw.rect(screen, col, (80 + i * 140, HEIGHT - 62, 110, 42), 4)
        draw_text(screen, item, FONT_TINY, col, (88 + i * 140, HEIGHT - 53))

    # OBJECTIVE
    if show_objective:
        draw_text(screen, objective_text, FONT_SMALL, WHITE, (30, 80))
        draw_text(screen, f"Item terkumpul: {objectives['collected']}/3", FONT, WHITE, (30, 115))

    # VISUAL ITEM INDICATOR (FIX UTAMA)
    if rooms[current_room].items:
        pulse = math.sin(time.time() * 5) * 12 + 38
        pygame.draw.circle(screen, YELLOW_GLOW, (WIDTH//2, HEIGHT//2 - 30), int(pulse), 5)
        hint_text = FONT_SMALL.render("ADA ITEM DI RUANGAN INI", True, YELLOW_GLOW)
        hint_text.set_alpha(int(180 + math.sin(time.time() * 6) * 75))
        screen.blit(hint_text, (WIDTH//2 - hint_text.get_width()//2, HEIGHT//2 + 20))
        draw_text(screen, "Klik mouse di area ruangan untuk ambil!", FONT_TINY, YELLOW_GLOW, (WIDTH//2 - 180, HEIGHT//2 + 55))

    # GAME OVER / ENDING
    if game_state == "game_over":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        draw_text(screen, "RUMAH TELAH MENGAMBIL ANDA", FONT_BIG, BLOOD_RED, (WIDTH//2 - 340, HEIGHT//2 - 100))
        draw_text(screen, f"Anda sudah mati {loop_count} kali...", FONT, WHITE, (WIDTH//2 - 240, HEIGHT//2 - 30))
        draw_text(screen, "Tekan R untuk Respawn   Q untuk Quit", FONT_SMALL, WHITE, (WIDTH//2 - 220, HEIGHT//2 + 60))

    if game_state == "ending":
        if time.time() - typewriter_timer > 0.05 and typewriter_index < len(typewriter_text):
            typewriter_index += 1
            typewriter_timer = time.time()
        draw_text(screen, typewriter_text[:typewriter_index], FONT_BIG, (0, 255, 80), (WIDTH//2 - 380, HEIGHT//2 - 80))

    # SHAKE FIX (TIDAK ADA LAGI ERROR)
    if shake > 0:
        shake_amount = int(shake)
        sx = random.randint(-shake_amount, shake_amount)
        sy = random.randint(-shake_amount, shake_amount)
        screen.blit(screen, (sx, sy))
        shake -= 0.7
        if shake < 0.5:
            shake = 0

    if not sound_enabled and SOUND_AVAILABLE:
        draw_text(screen, "SOUND OFF (M to toggle)", FONT_TINY, (255, 180, 0), (WIDTH - 280, HEIGHT - 30))

    pygame.display.flip()

pygame.quit()
sys.exit()
