import pygame
import sys
import random
import time
import math

# ==================== KONSTANTA GAME ====================
pygame.init()
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu - Prompt 1/5")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 24)
FONT_SMALL = pygame.font.SysFont("consolas", 18)
FONT_TINY = pygame.font.SysFont("consolas", 14)

# Warna horor
BLACK = (5, 0, 0)
DARK_RED = (80, 0, 0)
BLOOD_RED = (150, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

PLAYER_NAME = "Lzroars23"  # Ganti dengan nama Anda sendiri untuk fourth-wall horror!

# ==================== PLAYER ====================
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
        # Batas layar
        self.x = max(50, min(WIDTH - 50, self.x))
        self.y = max(50, min(HEIGHT - 50, self.y))

    def draw(self, surface):
        # Player sebagai silhouette gelap dengan outline merah
        pygame.draw.circle(surface, (20, 20, 20), (int(self.x), int(self.y)), self.size)
        pygame.draw.circle(surface, BLOOD_RED, (int(self.x), int(self.y)), self.size, 3)

# ==================== RUANGAN ====================
rooms = {
    "entrance": {
        "name": "Ruang Depan",
        "desc": "Pintu depan tertutup rapat. Ada bau tanah basah dan sesuatu yang busuk.",
        "color": (20, 10, 10),
        "whispers": ["Kamu ingat saat kecil... pintu ini pernah mengunci ibumu di dalam?"]
    },
    "living": {
        "name": "Ruang Tamu",
        "desc": "Foto keluarga di dinding. Wajah Anda di foto itu tersenyum... tapi mata tidak.",
        "color": (15, 5, 5),
        "whispers": ["Nama Anda tertulis di belakang foto... tapi Anda tidak pernah tinggal di sini."]
    },
    "kitchen": {
        "name": "Dapur",
        "desc": "Pisau di meja masih berdarah. Jam dinding berhenti di pukul 03:33.",
        "color": (30, 10, 0),
        "whispers": ["Mereka bilang kakek Anda mati di sini... tapi kenapa ada suara langkah Anda di belakang?"]
    },
    "bedroom": {
        "name": "Kamar Tidur",
        "desc": "Tempat tidur sudah disiapkan. Seprei putih... ada bekas tangan di atasnya.",
        "color": (10, 0, 10),
        "whispers": [f"{PLAYER_NAME}... tidurlah. Rumah ini akan menjaga mimpi Anda selamanya."]
    },
    "basement": {
        "name": "Ruang Bawah Tanah",
        "desc": "Tangga menurun. Udara semakin dingin. Anda merasa sedang ditonton.",
        "color": (5, 0, 5),
        "whispers": ["Turunlah. Kami sudah menunggu sejak 1997."]
    }
}

current_room = "entrance"
room_rects = {  # Area trigger sederhana
    "entrance": pygame.Rect(50, 50, 300, 200),
    "living": pygame.Rect(400, 50, 350, 200),
    "kitchen": pygame.Rect(50, 300, 250, 250),
    "bedroom": pygame.Rect(350, 300, 200, 250),
    "basement": pygame.Rect(600, 400, 150, 150)
}

# ==================== VARIABEL GAME ====================
player = Player()
running = True
last_whisper_time = time.time()
whisper_text = ""
whisper_alpha = 0
sanity_drain_rate = 0.008  # per frame

# ==================== FUNGSI HELPER ====================
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
    # Vignette merah berdasarkan sanity
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    intensity = int((100 - player.sanity) * 1.8)
    overlay.fill((intensity, 0, 0, intensity // 2))
    surface.blit(overlay, (0, 0))

    # Sanity bar
    bar_width = 300
    bar_height = 20
    fill = int((player.sanity / 100) * bar_width)
    pygame.draw.rect(surface, GRAY, (WIDTH//2 - bar_width//2, 30, bar_width, bar_height))
    pygame.draw.rect(surface, BLOOD_RED, (WIDTH//2 - bar_width//2, 30, fill, bar_height))
    draw_text(surface, f"Sanity: {int(player.sanity)}%", FONT_SMALL, WHITE, (WIDTH//2 - 60, 5))

# ==================== MAIN LOOP ====================
while running:
    dt = clock.tick(60) / 1000.0  # untuk future timing
    screen.fill(BLACK)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

    # Movement
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

    # Update current room
    new_room = get_room_at_pos(player.x, player.y)
    if new_room != current_room:
        current_room = new_room
        whisper_text = rooms[current_room]["desc"]
        whisper_alpha = 255
        # Sanity drain lebih cepat di ruangan tertentu
        if current_room == "basement":
            player.sanity -= 8

    # Sanity drain
    player.sanity -= sanity_drain_rate
    if random.random() < 0.008:  # random extra drain
        player.sanity -= 0.5

    player.sanity = max(0, min(100, player.sanity))

    # Random whispers
    if time.time() - last_whisper_time > random.uniform(8, 18):
        if player.sanity < 60:
            whisper_text = random.choice(rooms[current_room]["whispers"])
            whisper_alpha = 255
        last_whisper_time = time.time()

    # Draw room background
    room_color = rooms[current_room]["color"]
    pygame.draw.rect(screen, room_color, (0, 0, WIDTH, HEIGHT))

    # Draw player
    player.draw(screen)

    # Draw sanity overlay
    draw_sanity_overlay(screen)

    # Draw room name
    draw_text(screen, rooms[current_room]["name"], FONT, WHITE, (20, 20))

    # Draw whisper text (fade out)
    if whisper_alpha > 0:
        alpha_speed = 2
        whisper_alpha = max(0, whisper_alpha - alpha_speed)
        txt_color = BLOOD_RED if player.sanity < 50 else WHITE
        draw_text(screen, whisper_text, FONT, txt_color, (WIDTH//2 - 200, HEIGHT - 80), whisper_alpha)

    # Sanity warning
    if player.sanity < 30:
        warning = FONT.render("RUMAH SEDANG MENDENGARKAN...", True, BLOOD_RED)
        warning.set_alpha(int(100 + math.sin(time.time() * 8) * 80))
        screen.blit(warning, (WIDTH//2 - warning.get_width()//2, HEIGHT - 120))

    # Game Over
    if player.sanity <= 0:
        gameover = FONT.render("RUMAH TELAH MENGAMBIL ANDA.", True, BLOOD_RED)
        screen.blit(gameover, (WIDTH//2 - gameover.get_width()//2, HEIGHT//2))
        pygame.display.flip()
        time.sleep(4)
        running = False

    pygame.display.flip()

pygame.quit()
sys.exit()
