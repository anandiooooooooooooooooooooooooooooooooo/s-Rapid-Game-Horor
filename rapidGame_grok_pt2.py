import pygame
import sys
import random
import time
import math

pygame.init()
WIDTH, HEIGHT = 1440, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu - Prompt 2/5")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 24)
FONT_SMALL = pygame.font.SysFont("consolas", 18)
FONT_TINY = pygame.font.SysFont("consolas", 14)

BLACK = (5, 0, 0)
DARK_RED = (80, 0, 0)
BLOOD_RED = (150, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

PLAYER_NAME = "Lzroars23"  # Ganti dengan nama Anda untuk fourth-wall effect maksimal

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.size = 20
        self.speed = 4
        self.sanity = 100.0
        self.flashlight_battery = 100.0

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

    def update(self, player, current_room, sanity):
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

        if dist < 250 and current_room in ["basement", "bedroom", "kitchen"]:
            speed_boost = 1.0 + (100 - sanity) / 60
            self.x += (dx / dist) * self.speed * speed_boost
            self.y += (dy / dist) * self.speed * speed_boost

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

class Room:
    def __init__(self, name, desc, color, whispers):
        self.name = name
        self.desc = desc
        self.color = color
        self.whispers = whispers

rooms = {
    "entrance": Room("Ruang Depan", "Pintu depan tertutup rapat...", (20, 10, 10), ["Kamu ingat saat kecil..."]),
    "living": Room("Ruang Tamu", "Foto keluarga di dinding...", (15, 5, 5), ["Nama Anda tertulis di belakang foto..."]),
    "kitchen": Room("Dapur", "Pisau di meja masih berdarah...", (30, 10, 0), ["Mereka bilang kakek Anda mati di sini..."]),
    "bedroom": Room("Kamar Tidur", "Tempat tidur sudah disiapkan...", (10, 0, 10), [f"{PLAYER_NAME}... tidurlah."]),
    "basement": Room("Ruang Bawah Tanah", "Tangga menurun. Udara semakin dingin...", (5, 0, 5), ["Turunlah. Kami sudah menunggu sejak 1997."])
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
running = True
last_whisper_time = time.time()
whisper_text = ""
whisper_alpha = 0
sanity_drain_rate = 0.009
shake = 0
debug_hunter = False

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
    intensity = int((100 - player.sanity) * 1.8)
    overlay.fill((intensity, 0, 0, intensity // 2))
    surface.blit(overlay, (0, 0))
    bar_width = 300
    fill = int((player.sanity / 100) * bar_width)
    pygame.draw.rect(surface, GRAY, (WIDTH//2 - bar_width//2, 30, bar_width, 20))
    pygame.draw.rect(surface, BLOOD_RED, (WIDTH//2 - bar_width//2, 30, fill, 20))
    draw_text(surface, f"Sanity: {int(player.sanity)}%", FONT_SMALL, WHITE, (WIDTH//2 - 60, 5))

def tint_color(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)

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

    player.sanity -= sanity_drain_rate
    if random.random() < 0.012:
        player.sanity -= 0.7
    player.sanity = max(0, min(100, player.sanity))

    stalker.update(player, current_room, player.sanity)

    if stalker.active and stalker.check_collision(player):
        player.sanity -= 19
        whisper_text = f"{PLAYER_NAME}... aku sudah dekat sekali."
        whisper_alpha = 255
        stalker.spawn_cooldown = 120

    if stalker.active:
        dist_to_stalker = math.hypot(stalker.x - player.x, stalker.y - player.y)
        if dist_to_stalker < 140:
            shake = 8
            player.sanity -= 0.035
        elif dist_to_stalker < 220:
            shake = 3

    if time.time() - last_whisper_time > random.uniform(7, 16):
        if player.sanity < 55 or stalker.active:
            whisper_text = random.choice(rooms[current_room].whispers)
            if stalker.active and dist_to_stalker < 180:
                whisper_text = f"{PLAYER_NAME}... jangan lari. Rumah sudah memilihmu."
            whisper_alpha = 255
        last_whisper_time = time.time()

    # draw background
    screen.fill(BLACK)

    # draw each room rectangle with its own color; brighten the current room
    for rname, rect in room_rects.items():
        base = rooms[rname].color
        if rname == current_room:
            col = tint_color(base, 2.2)
        else:
            col = tint_color(base, 0.9)
        pygame.draw.rect(screen, col, rect)

    player.draw(screen)
    stalker.draw(screen, player.sanity)

    draw_sanity_overlay(screen)
    draw_text(screen, rooms[current_room].name, FONT, WHITE, (20, 20))

    if whisper_alpha > 0:
        whisper_alpha = max(0, whisper_alpha - 3)
        txt_color = BLOOD_RED if player.sanity < 45 else WHITE
        draw_text(screen, whisper_text, FONT, txt_color, (WIDTH//2 - 220, HEIGHT - 85), whisper_alpha)

    if player.sanity < 28:
        warning = FONT.render("RUMAH SEDANG MENGIRIM SESUATU UNTUK ANDA...", True, BLOOD_RED)
        warning.set_alpha(int(90 + math.sin(time.time() * 10) * 90))
        screen.blit(warning, (WIDTH//2 - warning.get_width()//2 + random.randint(-1, 1), HEIGHT - 125))

    if shake > 0:
        shake_offset_x = random.randint(-shake, shake)
        shake_offset_y = random.randint(-shake, shake)
        screen.blit(screen, (shake_offset_x, shake_offset_y))
        shake -= 0.6

    if player.sanity <= 0:
        gameover = FONT.render("RUMAH TELAH MENGAMBIL ANDA. THE STALKER MENANG.", True, BLOOD_RED)
        screen.blit(gameover, (WIDTH//2 - gameover.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        time.sleep(5)
        running = False

    if debug_hunter:
        draw_text(screen, "DEBUG HUNTER ACTIVE", FONT_TINY, (255, 255, 0), (10, HEIGHT - 30))

    pygame.display.flip()

pygame.quit()
sys.exit()
