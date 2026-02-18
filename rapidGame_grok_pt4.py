import pygame
import sys
import random
import time
import math
try:
    import numpy as np
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

pygame.init()
if SOUND_AVAILABLE:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

# Variabel resolusi dinamis
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu - Prompt 4 Fixed (4.1)")

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

PLAYER_NAME = "Lzroars23"
loop_count = 0
sound_enabled = SOUND_AVAILABLE
show_objective = True

# === OBJECTIVE SYSTEM ===
objectives = {
    "collected": 0,      # max 3
    "escaped": False
}
objective_text = "Tujuan: Kumpulkan 3 item lalu kembali ke Ruang Depan & tekan E untuk keluar!"

class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 150
        self.y = 150
        self.size = 20
        self.speed = 4.2
        self.sanity = 72.0
        self.flashlight_battery = 100.0
        self.flashlight_on = True

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(60, min(WIDTH - 60, self.x))
        self.y = max(60, min(HEIGHT - 60, self.y))

    def draw(self, surface):
        pygame.draw.circle(surface, (25, 25, 25), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x), int(self.y)), self.size, 4)

class TheStalker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = 680
        self.y = 480
        self.size = 27
        self.speed = 2.65
        self.active = False
        self.spawn_cooldown = 45
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
            if dist < 22:
                player.sanity -= 20
                self.spawn_cooldown = 110
                return
            speed_mod = 0.62 if (cone_points and point_in_polygon((self.x, self.y), cone_points)) else 1.0
            if dist < 255 and current_room in ["basement", "bedroom", "kitchen"]:
                boost = 1.0 + (100 - sanity) / 75
                self.x += (dx / dist) * self.speed * boost * speed_mod
                self.y += (dy / dist) * self.speed * boost * speed_mod
        except:
            pass  # safety net anti-crash

    def draw(self, surface):
        if not self.active: return
        self.pulse = (self.pulse + 0.18) % (math.pi * 2)
        eye_size = 7 + math.sin(self.pulse) * 2.5
        pygame.draw.circle(surface, (8, 8, 8), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x - 9), int(self.y - 7)), int(eye_size))
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x + 9), int(self.y - 7)), int(eye_size))

    def check_collision(self, player):
        return math.hypot(self.x - player.x, self.y - player.y) < self.size + player.size

class BloodDrip:
    def __init__(self):
        self.x = random.randint(50, WIDTH - 50)
        self.y = random.randint(-30, 80)
        self.length = random.randint(18, 45)
        self.speed = random.uniform(1.8, 4.2)
        self.width = random.randint(2, 5)
        self.alpha = 180

    def update(self):
        self.y += self.speed
        self.alpha -= 1.2

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
    "entrance": Room("Ruang Depan", "Pintu depan tertutup rapat...", (23, 12, 12), ["Kamu ingat saat kecil..."]),
    "living": Room("Ruang Tamu", "Foto keluarga...", (17, 7, 7), ["Nama Anda tertulis..."], ["Old Key"]),
    "kitchen": Room("Dapur", "Pisau masih berdarah...", (34, 12, 2), ["Kakek Anda mati di sini..."], ["Candle"]),
    "bedroom": Room("Kamar Tidur", "Tempat tidur disiapkan...", (12, 2, 12), [f"{PLAYER_NAME}... tidurlah."], ["Photo Fragment"]),
    "basement": Room("Ruang Bawah Tanah", "Tangga menurun...", (7, 2, 7), ["Turunlah..."])
}

current_room = "entrance"
room_rects = {  # enlarged for easier navigation
    "entrance": pygame.Rect(40, 40, 340, 220),
    "living": pygame.Rect(410, 40, 360, 220),
    "kitchen": pygame.Rect(40, 310, 270, 260),
    "bedroom": pygame.Rect(360, 310, 220, 260),
    "basement": pygame.Rect(620, 420, 160, 160)
}

player = Player()
stalker = TheStalker()
blood_drips = []
inventory = []
selected_item = None
game_state = "menu"  # menu / playing / game_over
last_whisper_time = time.time()
whisper_text = ""
whisper_alpha = 0
sanity_drain_rate = 0.0092
shake = 0
flicker = 1.0
last_flicker_time = time.time()

resolution_options = [
    ("1 - 800x600 (Default)", 800, 600),
    ("2 - 1024x768", 1024, 768),
    ("3 - 1280x720 (Rekomendasi)", 1280, 720),
    ("4 - Fullscreen", 0, 0)
]

def play_procedural_sound(freq, duration, volume=0.25, type="sine"):
    if not sound_enabled or not SOUND_AVAILABLE: return
    try:
        # Check mixer settings to match channels
        mixer_settings = pygame.mixer.get_init()
        if not mixer_settings: return
        sample_rate, size, channels = mixer_settings

        frames = int(duration * sample_rate)
        t = np.linspace(0, duration, frames)
        if type == "sine": wave = np.sin(2 * np.pi * t * freq)
        else: wave = 2 * (t * freq - np.floor(t * freq)) - 1

        arr = (wave * 32767 * volume).astype(np.int16)

        # If mixer is stereo (2 channels), duplicate mono array to 2 columns
        if channels == 2:
            arr = np.column_stack((arr, arr))

        sound = pygame.sndarray.make_sound(arr)
        sound.play()
    except Exception as e:
        print(f"Sound Error: {e}")

def point_in_polygon(point, poly):
    if poly is None or len(poly) < 3:
        return False
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

def get_room_at_pos(x, y):
    for rname, rect in room_rects.items():
        if rect.collidepoint(x, y):
            return rname
    return current_room

def draw_text(surface, text, font, color, pos, alpha=255):
    txt = font.render(text, True, color)
    txt.set_alpha(alpha)
    surface.blit(txt, pos)

def respawn():
    global game_state, loop_count, current_room
    player.reset()
    stalker.reset()
    current_room = "entrance"
    blood_drips.clear()
    game_state = "playing"
    loop_count += 1
    whisper_text = f"Kamu sudah mati {loop_count} kali, {PLAYER_NAME}..."
    whisper_alpha = 255

def apply_resolution(idx):
    global WIDTH, HEIGHT, screen
    name, w, h = resolution_options[idx]
    if w == 0:  # fullscreen
        info = pygame.display.Info()
        w, h = info.current_w, info.current_h
        screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
    WIDTH, HEIGHT = w, h
    pygame.display.set_caption(f"Rumah yang Tahu Namamu - {name}")

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
                    apply_resolution(idx)
                    game_state = "playing"
                    whisper_text = objective_text
                    whisper_alpha = 180
            elif game_state == "playing":
                if event.key == pygame.K_f:
                    player.flashlight_on = not player.flashlight_on
                if event.key == pygame.K_m:
                    global sound_enableded
                    sound_enabled = not sound_enabled
                if event.key == pygame.K_TAB:
                    show_objective = not show_objective
                if event.key == pygame.K_e and current_room == "entrance" and objectives["collected"] >= 3:
                    objectives["escaped"] = True
                    game_state = "game_over"  # win condition
                if event.key == pygame.K_1 and len(inventory) > 0: selected_item = 0
                if event.key == pygame.K_2 and len(inventory) > 1: selected_item = 1
                if event.key == pygame.K_3 and len(inventory) > 2: selected_item = 2
            elif game_state == "game_over":
                if event.key == pygame.K_r:
                    respawn()
                if event.key == pygame.K_q:
                    running = False

    if game_state == "menu":
        draw_text(screen, "PILIH RESOLUSI", FONT_BIG, WHITE, (WIDTH//2 - 220, 120))
        for i, (txt, _, _) in enumerate(resolution_options):
            col = BLOOD_RED if i == 0 else WHITE
            draw_text(screen, txt, FONT, col, (WIDTH//2 - 200, 220 + i*60))
        if not SOUND_AVAILABLE:
            draw_text(screen, "Sound: DISABLED → pip install numpy", FONT_SMALL, BLOOD_RED, (WIDTH//2 - 260, HEIGHT - 80))
        pygame.display.flip()
        continue

    if game_state == "playing":
        # === MOVEMENT & UPDATE (sama seperti sebelumnya tapi dengan objective) ===
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

        # Flashlight battery
        if player.flashlight_on:
            player.flashlight_battery -= 0.078
            if player.flashlight_battery <= 0:
                player.flashlight_on = False
        else:
            player.flashlight_battery = min(100, player.flashlight_battery + 0.035)

        player.sanity -= sanity_drain_rate
        if random.random() < 0.011: player.sanity -= 0.65
        player.sanity = max(0, min(100, player.sanity))

        # Item pick
        mx, my = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0]:
            for rname, rect in room_rects.items():
                if rect.collidepoint(mx, my) and rname == current_room:
                    for item in rooms[current_room].items[:]:
                        if random.random() < 0.7:
                            inventory.append(item)
                            rooms[current_room].items.remove(item)
                            objectives["collected"] += 1
                            break

        # Cone
        cone_points = None
        if player.flashlight_on and player.flashlight_battery > 4:
            angle = math.atan2(my - player.y, mx - player.x)
            length = 355
            half = math.radians(27)
            p1 = (player.x + math.cos(angle - half) * length, player.y + math.sin(angle - half) * length)
            p2 = (player.x + math.cos(angle + half) * length, player.y + math.sin(angle + half) * length)
            cone_points = [(player.x, player.y), p1, p2]

        stalker.update(player, current_room, player.sanity, cone_points)

        if stalker.active and stalker.check_collision(player):
            player.sanity -= 19
            whisper_text = f"{PLAYER_NAME}... aku sudah dekat sekali."
            whisper_alpha = 255
            stalker.spawn_cooldown = 120
            if sound_enabled: play_procedural_sound(115, 0.55, 0.38, "saw")

        if stalker.active:
            dist = math.hypot(stalker.x - player.x, stalker.y - player.y)
            if dist < 135: shake = 8.5
            elif dist < 215: shake = 3.5

        # Whisper & blood
        if time.time() - last_whisper_time > random.uniform(6.5, 14):
            if player.sanity < 50 or stalker.active:
                whisper_text = random.choice(rooms[current_room].whispers)
                whisper_alpha = 255
            last_whisper_time = time.time()

        if len(blood_drips) < 14 and player.sanity < 55 and random.random() < 0.17:
            blood_drips.append(BloodDrip())
        for drip in blood_drips[:]:
            drip.update()
            if drip.alpha <= 0 or drip.y > HEIGHT:
                blood_drips.remove(drip)

        if time.time() - last_flicker_time > random.uniform(0.09, 0.32):
            flicker = random.uniform(0.72, 1.0)
            last_flicker_time = time.time()

        if player.sanity <= 0:
            game_state = "game_over"

    # === DRAWING ===
    room_color = tuple(int(c * flicker * 1.12) for c in rooms[current_room].color)
    pygame.draw.rect(screen, room_color, (0, 0, WIDTH, HEIGHT))

    for rect in room_rects.values():
        pygame.draw.rect(screen, (30, 10, 10), rect, 6)

    player.draw(screen)
    stalker.draw(screen)

    ambient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(ambient, (35, 25, 15, 42), (int(player.x), int(player.y)), 195)
    screen.blit(ambient, (0, 0))

    dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark.fill((0, 0, 0, 138))
    if cone_points and player.flashlight_on:
        pygame.draw.polygon(dark, (0, 0, 0, 0), cone_points)
        pygame.draw.polygon(dark, (55, 40, 25, 55), cone_points, 22)
    screen.blit(dark, (0, 0))

    for drip in blood_drips:
        drip.draw(screen)

    draw_text(screen, rooms[current_room].name, FONT, WHITE, (22, 18))

    if whisper_alpha > 0:
        whisper_alpha = max(0, whisper_alpha - 3.8)
        txt_color = BLOOD_RED if player.sanity < 40 else WHITE
        draw_text(screen, whisper_text, FONT, txt_color, (WIDTH//2 - 240, HEIGHT - 92), whisper_alpha)

    # Sanity & battery bar
    bar_w = 320
    fill_s = int((player.sanity / 100) * bar_w)
    pygame.draw.rect(screen, GRAY, (WIDTH//2 - bar_w//2, 28, bar_w, 18))
    pygame.draw.rect(screen, BLOOD_RED, (WIDTH//2 - bar_w//2, 28, fill_s, 18))
    draw_text(screen, f"Sanity: {int(player.sanity)}%", FONT_SMALL, WHITE, (WIDTH//2 - 70, 4))

    bat_fill = int(player.flashlight_battery)
    pygame.draw.rect(screen, LIGHT_GRAY, (WIDTH - 180, 28, 150, 12))
    pygame.draw.rect(screen, (200, 180, 60), (WIDTH - 180, 28, bat_fill * 1.5, 12))
    draw_text(screen, "FLASHLIGHT", FONT_TINY, WHITE, (WIDTH - 175, 8))

    # Inventory
    pygame.draw.rect(screen, (18, 18, 18), (40, HEIGHT - 68, WIDTH - 80, 54))
    for i, item in enumerate(inventory):
        col = BLOOD_RED if i == selected_item else WHITE
        pygame.draw.rect(screen, col, (70 + i * 125, HEIGHT - 55, 95, 36), 3)
        draw_text(screen, item, FONT_TINY, col, (78 + i * 125, HEIGHT - 48))

    # OBJECTIVE DISPLAY
    if show_objective:
        prog = f"Item: {objectives['collected']}/3"
        draw_text(screen, objective_text, FONT_SMALL, WHITE, (20, 65))
        draw_text(screen, prog, FONT, WHITE, (20, 95))

    if game_state == "game_over":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 195))
        screen.blit(overlay, (0, 0))
        if objectives["escaped"]:
            draw_text(screen, "ANDA BERHASIL KELUAR!", FONT_BIG, (0, 255, 0), (WIDTH//2 - 260, HEIGHT//2 - 90))
            draw_text(screen, "Rumah tidak lagi tahu namamu...", FONT, WHITE, (WIDTH//2 - 240, HEIGHT//2))
        else:
            draw_text(screen, "RUMAH TELAH MENGAMBIL ANDA", FONT_BIG, BLOOD_RED, (WIDTH//2 - 310, HEIGHT//2 - 90))
            draw_text(screen, f"Anda sudah mati {loop_count} kali...", FONT, WHITE, (WIDTH//2 - 220, HEIGHT//2 - 20))
            draw_text(screen, "Tekan R untuk Respawn", FONT, WHITE, (WIDTH//2 - 180, HEIGHT//2 + 40))
            draw_text(screen, "Tekan Q untuk Quit", FONT_SMALL, WHITE, (WIDTH//2 - 110, HEIGHT//2 + 85))

    if shake > 0:
        sx = random.randint(-int(shake), int(shake))
        sy = random.randint(-int(shake), int(shake))
        screen.blit(screen, (sx, sy))
        shake -= 0.65

    pygame.display.flip()

pygame.quit()
sys.exit()
