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

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu - Prompt 3/5")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 24)
FONT_SMALL = pygame.font.SysFont("consolas", 18)
FONT_TINY = pygame.font.SysFont("consolas", 14)

BLACK = (5, 0, 0)
DARK_RED = (80, 0, 0)
BLOOD_RED = (150, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

PLAYER_NAME = "Lzroars23"

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.size = 20
        self.speed = 4
        self.sanity = 100.0
        self.flashlight_battery = 100.0
        self.flashlight_on = True

    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(50, min(WIDTH - 50, self.x))
        self.y = max(50, min(HEIGHT - 50, self.y))

    def draw(self, surface):
        pygame.draw.circle(surface, (20, 20, 20), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x), int(self.y)), self.size, 3)

class TheStalker:
    def __init__(self):
        self.x = 650
        self.y = 450
        self.size = 28
        self.speed = 2.8
        self.active = False
        self.spawn_cooldown = 0
        self.pulse = 0.0

    def update(self, player, current_room, sanity, flashlight_cone_points):
        if sanity >= 68:
            self.active = False
            return
        self.active = True
        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= 1
            return
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 20:
            player.sanity -= 22
            self.spawn_cooldown = 90
            return
        speed_mod = 1.0
        if flashlight_cone_points and point_in_polygon((self.x, self.y), flashlight_cone_points):
            speed_mod = 0.58
        if dist < 250 and current_room in ["basement", "bedroom", "kitchen"]:
            speed_boost = 1.0 + (100 - sanity) / 60
            self.x += (dx / dist) * self.speed * speed_boost * speed_mod
            self.y += (dy / dist) * self.speed * speed_boost * speed_mod

    def draw(self, surface, sanity):
        if not self.active:
            return
        self.pulse = (self.pulse + 0.15) % (math.pi * 2)
        eye_size = 6 + math.sin(self.pulse) * 2
        pygame.draw.circle(surface, (10, 10, 10), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x - 8), int(self.y - 6)), int(eye_size))
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x + 8), int(self.y - 6)), int(eye_size))

    def check_collision(self, player):
        dist = math.hypot(self.x - player.x, self.y - player.y)
        return dist < self.size + player.size

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
    "entrance": Room("Ruang Depan", "Pintu depan tertutup rapat...", (100, 60, 60), ["Kamu ingat saat kecil..."]),
    "living": Room("Ruang Tamu", "Foto keluarga di dinding...", (60, 100, 60), ["Nama Anda tertulis di belakang foto..."], ["Old Key"]),
    "kitchen": Room("Dapur", "Pisau di meja masih berdarah...", (60, 60, 140), ["Mereka bilang kakek Anda mati di sini..."], ["Candle"]),
    "bedroom": Room("Kamar Tidur", "Tempat tidur sudah disiapkan...", (120, 120, 60), [f"{PLAYER_NAME}... tidurlah."], ["Photo Fragment"]),
    "basement": Room("Ruang Bawah Tanah", "Tangga menurun. Udara semakin dingin...", (100, 40, 100), ["Turunlah. Kami sudah menunggu sejak 1997."])
}

current_room = "entrance"
room_rects = {
    "entrance": pygame.Rect(50, 50, 300, 200),
    "living": pygame.Rect(400, 50, 350, 200),
    "kitchen": pygame.Rect(50, 300, 250, 250),
    "bedroom": pygame.Rect(350, 300, 200, 250),
    "basement": pygame.Rect(600, 400, 150, 150)
}

player = Player()
stalker = TheStalker()
blood_drips = []
inventory = []
selected_item = None
running = True
last_whisper_time = time.time()
whisper_text = ""
whisper_alpha = 0
sanity_drain_rate = 0.011
shake = 0
debug_hunter = False
flicker = 1.0
last_flicker_time = time.time()
ambient_playing = False

def play_procedural_sound(freq, duration, volume=0.25, type="sine"):
    if not SOUND_AVAILABLE:
        return

    # Query mixer so we match the sample rate and channels exactly
    mixer_settings = pygame.mixer.get_init()
    if not mixer_settings:
        return
    sample_rate, size, channels = mixer_settings

    frames = int(duration * sample_rate)
    t = np.linspace(0, duration, frames)
    if type == "sine":
        wave = np.sin(2 * np.pi * t * freq)
    elif type == "saw":
        wave = 2 * (t * freq - np.floor(t * freq)) - 1

    arr = (wave * 32767 * volume).astype(np.int16)

    # Handle stereo output requirement
    if channels == 2:
        arr = np.colum_stack((arr, arr))

    sound = pygame.sndarray.make_sound(arr)
    sound.play()

def point_in_polygon(point, poly):
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

def draw_sanity_overlay(surface):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    intensity = int((100 - player.sanity) * 1.9)
    overlay.fill((intensity, 0, 0, intensity // 2))
    surface.blit(overlay, (0, 0))
    bar_width = 300
    fill = int((player.sanity / 100) * bar_width)
    pygame.draw.rect(surface, GRAY, (WIDTH//2 - bar_width//2, 30, bar_width, 20))
    pygame.draw.rect(surface, BLOOD_RED, (WIDTH//2 - bar_width//2, 30, fill, 20))
    draw_text(surface, f"Sanity: {int(player.sanity)}%", FONT_SMALL, WHITE, (WIDTH//2 - 60, 5))

def draw_inventory(surface):
    pygame.draw.rect(surface, (20, 20, 20), (50, HEIGHT - 70, WIDTH - 100, 60))
    for i, item in enumerate(inventory):
        color = BLOOD_RED if i == selected_item else WHITE
        pygame.draw.rect(surface, color, (80 + i * 110, HEIGHT - 55, 80, 40), 3)
        draw_text(surface, item, FONT_TINY, color, (85 + i * 110, HEIGHT - 48))

while running:
    dt = clock.tick(60) / 1000.0
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            if event.key == pygame.K_h:
                debug_hunter = not debug_hunter
            if event.key == pygame.K_f:
                player.flashlight_on = not player.flashlight_on
            if event.key == pygame.K_1 and len(inventory) > 0:
                selected_item = 0
            if event.key == pygame.K_2 and len(inventory) > 1:
                selected_item = 1
            if event.key == pygame.K_3 and len(inventory) > 2:
                selected_item = 2
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 3 and selected_item is not None:
                item = inventory[selected_item]
                if item == "Candle":
                    player.sanity += 8
                    inventory.pop(selected_item)
                elif item == "Photo Fragment":
                    player.sanity += 14
                    inventory.pop(selected_item)
                selected_item = None
            if event.button == 1:
                mx, my = pygame.mouse.get_pos()
                for rname, rect in room_rects.items():
                    if rect.collidepoint(mx, my) and rname == current_room:
                        for item in rooms[current_room].items[:]:
                            if random.random() < 0.6:
                                inventory.append(item)
                                rooms[current_room].items.remove(item)
                                break

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
        if current_room == "basement":
            player.sanity -= 9

    if player.flashlight_on:
        player.flashlight_battery -= 0.085
        if player.flashlight_battery <= 0:
            player.flashlight_on = False
    else:
        player.flashlight_battery = min(100, player.flashlight_battery + 0.032)

    player.sanity -= sanity_drain_rate
    if random.random() < 0.013:
        player.sanity -= 0.8
    player.sanity = max(0, min(100, player.sanity))

    mx, my = pygame.mouse.get_pos()
    cone_points = None
    if player.flashlight_on and player.flashlight_battery > 5:
        angle = math.atan2(my - player.y, mx - player.x)
        length = 340
        half_angle = math.radians(27.5)
        p1 = (player.x + math.cos(angle - half_angle) * length, player.y + math.sin(angle - half_angle) * length)
        p2 = (player.x + math.cos(angle + half_angle) * length, player.y + math.sin(angle + half_angle) * length)
        cone_points = [(player.x, player.y), p1, p2]

    stalker.update(player, current_room, player.sanity, cone_points)

    if stalker.active and stalker.check_collision(player):
        player.sanity -= 19
        whisper_text = f"{PLAYER_NAME}... aku sudah dekat sekali."
        whisper_alpha = 255
        stalker.spawn_cooldown = 120
        if SOUND_AVAILABLE:
            play_procedural_sound(120, 0.6, 0.4, "saw")

    if stalker.active:
        dist_to_stalker = math.hypot(stalker.x - player.x, stalker.y - player.y)
        if dist_to_stalker < 140:
            shake = 9
            player.sanity -= 0.038
        elif dist_to_stalker < 220:
            shake = 4

    if time.time() - last_whisper_time > random.uniform(6, 15):
        if player.sanity < 52 or stalker.active:
            whisper_text = random.choice(rooms[current_room].whispers)
            if stalker.active and dist_to_stalker < 170:
                whisper_text = f"{PLAYER_NAME}... cahaya tidak akan selamatkan kamu selamanya."
            whisper_alpha = 255
            if SOUND_AVAILABLE and random.random() < 0.4:
                play_procedural_sound(random.randint(800, 1400), 0.35, 0.2)
        last_whisper_time = time.time()

    if len(blood_drips) < 12 and player.sanity < 58 and random.random() < 0.15:
        blood_drips.append(BloodDrip())

    for drip in blood_drips[:]:
        drip.update()
        if drip.alpha <= 0 or drip.y > HEIGHT:
            blood_drips.remove(drip)

    if time.time() - last_flicker_time > random.uniform(0.08, 0.35):
        flicker = random.uniform(0.65, 1.0)
        last_flicker_time = time.time()

    # Draw all rooms to show layout
    for r_name, r_rect in room_rects.items():
        base_color = rooms[r_name].color
        draw_color = tuple(int(c * flicker) for c in base_color)
        pygame.draw.rect(screen, draw_color, r_rect)
        # Add a subtle border
        pygame.draw.rect(screen, (30, 30, 30), r_rect, 1)

    player.draw(screen)
    stalker.draw(screen, player.sanity)

    dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark.fill((0, 0, 0, 192))
    if cone_points and player.flashlight_on:
        pygame.draw.polygon(dark, (0, 0, 0, 0), cone_points)
        pygame.draw.polygon(dark, (40, 30, 20, 40), cone_points, 18)
    screen.blit(dark, (0, 0))

    for drip in blood_drips:
        drip.draw(screen)

    draw_sanity_overlay(screen)
    draw_text(screen, rooms[current_room].name, FONT, WHITE, (20, 20))

    if whisper_alpha > 0:
        whisper_alpha = max(0, whisper_alpha - 3.5)
        txt_color = BLOOD_RED if player.sanity < 42 else WHITE
        draw_text(screen, whisper_text, FONT, txt_color, (WIDTH//2 - 230, HEIGHT - 88), whisper_alpha)

    if player.sanity < 27:
        warning = FONT.render("RUMAH SEDANG MENGIRIM SESUATU UNTUK ANDA...", True, BLOOD_RED)
        warning.set_alpha(int(95 + math.sin(time.time() * 11) * 95))
        screen.blit(warning, (WIDTH//2 - warning.get_width()//2 + random.randint(-2, 2), HEIGHT - 130))

    if shake > 0:
        shake_offset_x = random.randint(-shake, shake)
        shake_offset_y = random.randint(-shake, shake)
        screen.blit(screen, (shake_offset_x, shake_offset_y))
        shake -= 0.7

    draw_inventory(screen)

    if player.sanity <= 0:
        gameover = FONT.render("RUMAH TELAH MENGAMBIL ANDA. THE STALKER MENANG.", True, BLOOD_RED)
        screen.blit(gameover, (WIDTH//2 - gameover.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        time.sleep(5.5)
        running = False

    if debug_hunter:
        draw_text(screen, "DEBUG HUNTER ACTIVE", FONT_TINY, (255, 255, 0), (10, HEIGHT - 30))

    pygame.display.flip()

pygame.quit()
sys.exit()
