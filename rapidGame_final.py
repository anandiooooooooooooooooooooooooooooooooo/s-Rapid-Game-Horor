"""
Rumah yang Tahu Namamu - ULTIMATE Edition
Game horor 2D berbasis Pygame. Fitur lengkap:
  - 8 ruangan, diary/lore, halusinasi, hiding, event horor, sprint,
    jejak kaki, achievement, vignette, ambient drone, stalker AI lanjutan.

Kontrol:
  WASD / Arrow Keys  = Gerak
  SHIFT (tahan)      = Sprint
  F                  = Senter on/off
  H                  = Bantuan kontrol
  M                  = Suara on/off
  TAB                = Objektif
  J                  = Jurnal/diary
  C                  = Sembunyikan diri (hiding)
  F5                 = Simpan
  F9                 = Muat
  E                  = Keluar rumah (Ruang Depan, 5 item)
  ESC                = Jeda
  1-5                = Pilih item inventori
  Klik Kanan         = Gunakan item
  Klik Kiri          = Ambil item / Ambil diary
"""

import pygame, sys, random, time, math, json, os

try:
    import numpy as np
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False

# === INIT ===
pygame.init()
if SOUND_AVAILABLE:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rumah yang Tahu Namamu — ULTIMATE")
clock = pygame.time.Clock()

FT = pygame.font.SysFont("consolas", 52, bold=True)
FB = pygame.font.SysFont("consolas", 36, bold=True)
FM = pygame.font.SysFont("consolas", 24)
FS = pygame.font.SysFont("consolas", 18)
FX = pygame.font.SysFont("consolas", 14)

BLACK=(5,0,0); DARK_RED=(80,0,0); BLOOD=(155,0,0); WHITE=(255,255,255)
GRAY=(45,45,45); LGRAY=(90,90,90); YELLOW=(255,220,60); GREEN=(0,200,60)
DIM=(160,160,160); CYAN=(0,180,200); PURPLE=(140,0,180)
SAVE_FILE="rumah_save.json"; FPS=60

# === PARTICLES ===
class Dust:
    def __init__(self):
        self.x=random.uniform(0,WIDTH); self.y=random.uniform(0,HEIGHT)
        self.vx=random.uniform(-0.3,0.3); self.vy=random.uniform(-0.2,0.2)
        self.sz=random.uniform(1,3); self.a=random.randint(20,60)
        self.life=random.uniform(3,8); self.age=0
    def update(self,dt):
        self.x+=self.vx; self.y+=self.vy; self.age+=dt
        self.vx+=random.uniform(-0.02,0.02); self.vy+=random.uniform(-0.02,0.02)
    def alive(self): return self.age<self.life and 0<self.x<WIDTH and 0<self.y<HEIGHT
    def draw(self,s):
        a=int(self.a*(1-self.age/self.life))
        if a>0: pygame.draw.circle(s,(120,110,100),(int(self.x),int(self.y)),int(self.sz))

class BloodDrip:
    def __init__(self):
        self.x=random.randint(50,WIDTH-50); self.y=random.randint(-40,100)
        self.ln=random.randint(20,50); self.sp=random.uniform(2,4.8)
        self.w=random.randint(2,6); self.a=190
    def update(self,dt): self.y+=self.sp; self.a-=1.4
    def alive(self): return self.a>0 and self.y<HEIGHT
    def draw(self,s):
        if self.a>0: pygame.draw.line(s,(*BLOOD,int(self.a)),(self.x,self.y),(self.x,self.y+self.ln),self.w)

class Footprint:
    def __init__(self,x,y):
        self.x=int(x); self.y=int(y); self.a=120; self.sz=random.randint(3,5)
    def update(self,dt): self.a-=0.6
    def alive(self): return self.a>10
    def draw(self,s):
        pygame.draw.circle(s,(40,15,15),(self.x,self.y),self.sz)

# === PLAYER ===
class Player:
    def __init__(self):
        self.reset()
    def reset(self):
        self.x=200.0; self.y=200.0; self.size=20; self.speed=4.3
        self.sanity=75.0; self.battery=100.0; self.fl_on=True
        self.moving=False; self.sprinting=False; self.stamina=100.0
        self.hidden=False; self.hide_timer=0.0
    def move(self,dx,dy,dt):
        spd=self.speed*(1.7 if self.sprinting else 1.0)
        self.x+=dx*spd; self.y+=dy*spd
        self.x=max(70,min(WIDTH-70,self.x)); self.y=max(70,min(HEIGHT-70,self.y))
        self.moving=True
    def update(self,dt):
        if self.sprinting and self.moving:
            self.stamina=max(0,self.stamina-0.4)
            if self.stamina<=0: self.sprinting=False
        elif not self.sprinting:
            self.stamina=min(100,self.stamina+0.15)
        if self.hidden:
            self.hide_timer+=dt
            self.sanity-=0.02  # hiding costs sanity
        self.moving=False
    def draw(self,s):
        if self.hidden:
            a=int(80+math.sin(time.time()*6)*40)
            pygame.draw.circle(s,(25,25,25),(int(self.x),int(self.y)),self.size)
            return
        px,py=int(self.x),int(self.y)
        pygame.draw.circle(s,(25,25,25),(px,py),self.size)
        pygame.draw.circle(s,BLOOD,(px,py),self.size,4)
        sc=GREEN if self.sanity>60 else YELLOW if self.sanity>30 else BLOOD
        pygame.draw.circle(s,sc,(px,py),6)

# === STALKER ===
class TheStalker:
    def __init__(self): self.reset()
    def reset(self):
        self.x=1100.0; self.y=600.0; self.size=27; self.base_speed=2.7
        self.speed=self.base_speed; self.active=False; self.cooldown=50
        self.pulse=0.0; self.phase="hunt"  # hunt / patrol / ambush
        self.patrol_target=None; self.ambush_room=None
    def scale(self,loop): self.speed=self.base_speed*(1+loop*0.08)
    def update(self,player,room,cone,dt):
        if player.hidden:
            # Stalker mencari tapi tidak menemukan
            if self.patrol_target is None:
                rects=list(ROOM_RECTS.values())
                self.patrol_target=random.choice(rects).center
            tx,ty=self.patrol_target
            dx,dy=tx-self.x,ty-self.y
            d=math.hypot(dx,dy)
            if d>5:
                self.x+=(dx/d)*self.speed*0.5; self.y+=(dy/d)*self.speed*0.5
            else:
                self.patrol_target=None
            return
        if player.sanity>=65: self.active=False; return
        self.active=True
        if self.cooldown>0: self.cooldown-=1; return
        dx=player.x-self.x; dy=player.y-self.y; dist=math.hypot(dx,dy)
        if dist<1: return
        if dist<24: player.sanity-=21; self.cooldown=120; return
        sm=1.0
        if cone and len(cone)==3:
            if _pip((self.x,self.y),cone): sm=0.58
        if dist<280:
            boost=1.0+(100-player.sanity)/72
            self.x+=(dx/dist)*self.speed*boost*sm
            self.y+=(dy/dist)*self.speed*boost*sm
    def draw(self,s):
        if not self.active: return
        self.pulse=(self.pulse+0.19)%(math.pi*2)
        es=7.5+math.sin(self.pulse)*2.8
        sx,sy=int(self.x),int(self.y)
        pygame.draw.circle(s,(8,8,8),(sx,sy),self.size)
        pygame.draw.circle(s,BLOOD,(sx-9,sy-7),int(es))
        pygame.draw.circle(s,BLOOD,(sx+9,sy-7),int(es))
        # Tendrils
        for i in range(4):
            ang=self.pulse+i*math.pi/2
            tx=sx+math.cos(ang)*self.size*1.3
            ty=sy+math.sin(ang)*self.size*1.3
            pygame.draw.line(s,(30,0,0),(sx,sy),(int(tx),int(ty)),2)
    def collision(self,p): return math.hypot(self.x-p.x,self.y-p.y)<self.size+p.size+5
    def dist_to(self,p): return math.hypot(self.x-p.x,self.y-p.y)

# === ROOM ===
class Room:
    def __init__(self,name,desc,color,whispers,items=None,diary=None):
        self.name=name; self.desc=desc; self.color=color
        self.whispers=whispers; self.orig_items=list(items or [])
        self.items=list(items or []); self.diary=diary; self.diary_found=False
    def reset(self):
        self.items=list(self.orig_items); self.diary_found=False

# === HORROR EVENTS ===
class HorrorEvent:
    """Event horor acak yang terjadi saat sanity rendah."""
    EVENTS = [
        {"name":"door_slam","msg":"BRAK! Pintu di belakangmu membanting!","shake":12,"san":-3},
        {"name":"blood_write","msg":"Tulisan darah muncul: 'JANGAN PERGI'","shake":5,"san":-5},
        {"name":"whisper_burst","msg":"Bisikan-bisikan memenuhi kepalamu...","shake":3,"san":-8},
        {"name":"lights_out","msg":"Semua cahaya padam sedetik...","shake":8,"san":-4},
        {"name":"mirror","msg":"Kamu melihat wajahmu... tapi tersenyum sendiri.","shake":6,"san":-7},
        {"name":"child_laugh","msg":"Suara tawa anak kecil terdengar dari dinding.","shake":4,"san":-3},
        {"name":"footsteps","msg":"Langkah kaki berlari di atasmu!","shake":7,"san":-4},
        {"name":"clock","msg":"Jam dinding berhenti. Lalu bergerak mundur.","shake":2,"san":-6},
    ]

# === ACHIEVEMENT ===
ACHIEVEMENTS = {
    "pertama_mati":{"title":"Kematian Pertama","desc":"Mati untuk pertama kali","icon":"💀"},
    "semua_ruangan":{"title":"Penjelajah","desc":"Kunjungi semua 8 ruangan","icon":"🗺️"},
    "semua_diary":{"title":"Sejarawan","desc":"Temukan semua halaman diary","icon":"📖"},
    "loop3":{"title":"Terjebak","desc":"Mencapai loop ke-3","icon":"🔄"},
    "sprint_master":{"title":"Pelari","desc":"Sprint selama 30 detik total","icon":"🏃"},
    "hiding":{"title":"Bersembunyi","desc":"Bersembunyi dari stalker","icon":"🫣"},
    "survivor":{"title":"Penyintas","desc":"Bertahan 5 menit","icon":"⏱️"},
    "escape":{"title":"Bebas?","desc":"Berhasil keluar dari rumah","icon":"🚪"},
}

# === UTILITY ===
def _snd(freq,dur,vol=0.25,typ="sine"):
    if not SOUND_AVAILABLE: return
    try:
        mi=pygame.mixer.get_init()
        if not mi: return
        sr,_,ch=mi; fr=int(dur*sr); t=np.linspace(0,dur,fr)
        w=np.sin(2*np.pi*t*freq) if typ=="sine" else 2*(t*freq-np.floor(t*freq))-1
        a=(w*32767*vol).astype(np.int16)
        if ch==2: a=np.column_stack((a,a))
        pygame.sndarray.make_sound(a).play()
    except Exception: pass

def _pip(pt,poly):
    if not poly or len(poly)<3: return False
    x,y=pt; n=len(poly); inside=False; p1x,p1y=poly[0]
    for i in range(n+1):
        p2x,p2y=poly[i%n]
        if y>min(p1y,p2y) and y<=max(p1y,p2y) and x<=max(p1x,p2x):
            if p1y!=p2y:
                xi=(y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
            if p1x==p2x or x<=xi: inside=not inside
        p1x,p1y=p2x,p2y
    return inside

def _room_at(x,y,cur):
    for n,r in ROOM_RECTS.items():
        if r.collidepoint(x,y): return n
    return cur

def _txt(s,t,f,c,p,a=255):
    r=f.render(t,True,c)
    if a<255: r.set_alpha(a)
    s.blit(r,p)

# === ROOMS DATA ===
def make_rooms(pn):
    return {
        "entrance":Room("Ruang Depan","Pintu depan tertutup rapat. Udara berat.",(25,13,13),
            [f"{pn}, seharusnya kamu tidak kembali.","Kamu ingat bermain di sini saat kecil..."],
            diary="1987 — Rumah ini dibangun oleh kakekmu. Dia bilang rumah ini 'hidup'."),
        "living":Room("Ruang Tamu","Foto keluarga memenuhi dinding. Semua wajah dicoret.",(18,8,8),
            ["Nama Anda tertulis di belakang foto...","Sofa itu... dulu tempat kakekmu duduk."],
            ["Kunci Tua"],
            diary="1993 — Foto-foto mulai berubah. Wajah-wajah baru muncul yang tidak kami kenal."),
        "kitchen":Room("Dapur","Pisau masih berdarah. Bau besi memenuhi ruangan.",(36,13,3),
            ["Mereka bilang kakek Anda mati di sini...","Air keran menetes. Tik. Tik. Tik."],
            ["Lilin"],
            diary="1995 — Pisau itu bergerak sendiri tadi malam. Ibu sudah tidak mau masak lagi."),
        "bedroom":Room("Kamar Tidur","Tempat tidur sudah disiapkan untuk seseorang.",(13,3,13),
            [f"{pn}... tidurlah. Selamanya.","Bantal itu basah. Bukan oleh air."],
            ["Fragmen Foto"],
            diary="1996 — Aku mendengar suara dari bawah kasur setiap malam. Suara itu tahu namaku."),
        "basement":Room("Ruang Bawah Tanah","Tangga menurun ke kegelapan absolut.",(8,3,8),
            ["Turunlah. Kami sudah menunggu sejak 1997.","Langkah di bawah... bukan langkahmu."],
            ["Jimat Kuno"],
            diary="1997 — Ada sesuatu di bawah tanah. Kakek turun dan tidak pernah kembali."),
        "hallway":Room("Lorong","Lorong panjang dan gelap. Cermin retak di dinding.",(15,10,10),
            ["Bayanganmu berjalan lebih lambat...","Cermin itu memantulkan seseorang lain."],
            diary="1998 — Lorong ini semakin panjang setiap hari. Aku yakin itu."),
        "bathroom":Room("Kamar Mandi","Keran menetes. Air berwarna kemerahan.",(12,12,18),
            ["Jangan lihat ke cermin...","Air itu bukan air."],
            ["Obat Penenang"],
            diary="1999 — Air keran berubah merah. Kami tidak lagi menggunakannya."),
        "attic":Room("Loteng","Debu tebal. Kotak-kotak tua dan boneka tanpa mata.",(20,15,8),
            ["Boneka itu... dulu punyamu.","Ada yang bergerak di antara kotak-kotak."],
            ["Kunci Rahasia"],
            diary="2000 — Surat terakhir kakek ditemukan di loteng: 'Rumah ini tahu namamu. Larilah.'"),
    }

ROOM_CONNS=[("entrance","living"),("entrance","kitchen"),("living","bedroom"),
    ("kitchen","bedroom"),("bedroom","basement"),("entrance","hallway"),
    ("hallway","bathroom"),("hallway","attic"),("bedroom","hallway")]

ROOM_RECTS={
    "entrance":pygame.Rect(50,50,300,200),
    "living":pygame.Rect(420,50,300,200),
    "kitchen":pygame.Rect(50,310,250,220),
    "bedroom":pygame.Rect(370,310,250,220),
    "basement":pygame.Rect(690,420,200,160),
    "hallway":pygame.Rect(790,50,250,200),
    "bathroom":pygame.Rect(790,310,200,160),
    "attic":pygame.Rect(1050,50,180,200),
}

# === GAME CLASS ===
class Game:
    def __init__(self):
        self.state="menu"; self.running=True; self.pname=""
        self.cursor_blink=0.0
        self.player=Player(); self.stalker=TheStalker()
        self.rooms=make_rooms("???"); self.cur_room="entrance"
        self.blood=[]; self.dust=[]; self.foots=[]; self.inv=[]
        self.sel_item=None; self.loop=0; self.obj=0; self.tplay=0.0
        self.visited={"entrance"}; self.snd_on=SOUND_AVAILABLE
        self.lwhisper=time.time(); self.wtxt=""; self.walpha=0
        self.san_rate=0.0088; self.shake=0.0; self.flicker=1.0
        self.lflicker=time.time(); self.flash=0; self.lfootstep=0.0
        self.lheartbeat=0.0; self.show_obj=True; self.show_ctrl=False
        self.show_journal=False; self.cone=None; self.sprint_total=0.0
        # Hallucination
        self.halluc_timer=0.0; self.halluc_active=False
        self.halluc_type=None; self.reverse_controls=False
        self.fake_stalkers=[]
        # Horror event
        self.last_event=time.time(); self.event_msg=""; self.event_alpha=0
        # Diary
        self.diaries_found=[]
        # Achievement
        self.achievements=set(); self.ach_display=""; self.ach_timer=0.0
        # Typewriter
        self.tw_text=""; self.tw_idx=0; self.tw_time=0.0
        # Surfaces
        self.s_dark=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        self.s_amb=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        self.s_part=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        self.s_vig=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        self._build_vignette()
        self.cw=WIDTH; self.ch=HEIGHT
        for _ in range(25): self.dust.append(Dust())

    def _build_vignette(self):
        """Buat overlay vignette (gelap di tepi layar)."""
        self.s_vig.fill((0,0,0,0))
        cx,cy=WIDTH//2,HEIGHT//2
        max_r=math.hypot(cx,cy)
        for r in range(int(max_r),0,-8):
            a=max(0,int(180*(1-r/max_r)**2))
            pygame.draw.circle(self.s_vig,(0,0,0,a),(cx,cy),r)

    def _ensure_surf(self):
        global WIDTH, HEIGHT
        if self.cw!=WIDTH or self.ch!=HEIGHT:
            self.s_dark=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            self.s_amb=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            self.s_part=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            self.s_vig=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            self._build_vignette()
            self.cw=WIDTH; self.ch=HEIGHT

    def _ach(self,key):
        if key not in self.achievements:
            self.achievements.add(key)
            a=ACHIEVEMENTS.get(key)
            if a:
                self.ach_display=f"{a['icon']} {a['title']}: {a['desc']}"
                self.ach_timer=4.0

    # --- SAVE / LOAD ---
    def save(self):
        d={"loop":self.loop,"inv":self.inv,"san":self.player.sanity,
           "bat":self.player.battery,"room":self.cur_room,"obj":self.obj,
           "tp":self.tplay,"vis":list(self.visited),"pn":self.pname,
           "ri":{k:v.items for k,v in self.rooms.items()},
           "diaries":self.diaries_found,"achs":list(self.achievements)}
        try:
            with open(SAVE_FILE,"w") as f: json.dump(d,f,indent=2)
            self.wtxt="Game tersimpan."; self.walpha=200
        except Exception: self.wtxt="Gagal menyimpan!"; self.walpha=200

    def load(self):
        if not os.path.exists(SAVE_FILE):
            self.wtxt="Tidak ada save file."; self.walpha=200; return
        try:
            with open(SAVE_FILE,"r") as f: d=json.load(f)
            self.loop=d["loop"]; self.inv=d["inv"]
            self.player.sanity=d["san"]; self.player.battery=d.get("bat",100)
            self.cur_room=d["room"]; self.obj=d.get("obj",0)
            self.tplay=d.get("tp",0); self.visited=set(d.get("vis",["entrance"]))
            self.pname=d.get("pn","???")
            for k,v in d.get("ri",{}).items():
                if k in self.rooms: self.rooms[k].items=v
            self.diaries_found=d.get("diaries",[])
            self.achievements=set(d.get("achs",[]))
            self.wtxt="Game dimuat."; self.walpha=200
        except Exception: self.wtxt="Gagal memuat!"; self.walpha=200

    def respawn(self):
        self.player.reset(); self.stalker.reset()
        self.cur_room="entrance"; self.blood.clear(); self.foots.clear()
        self.loop+=1; self.obj=0; self.inv.clear(); self.visited={"entrance"}
        self.halluc_active=False; self.reverse_controls=False
        self.fake_stalkers.clear()
        for r in self.rooms.values(): r.reset()
        self.stalker.scale(self.loop)
        self.san_rate=0.0088*(1+self.loop*0.12)
        self.player.sanity=max(40,75-self.loop*5)
        self.state="playing"
        self.wtxt=f"Loop ke-{self.loop}. Rumah semakin mengenalmu, {self.pname}..."
        self.walpha=255
        if self.loop>=3: self._ach("loop3")

    # --- EVENTS ---
    def handle_events(self,dt):
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: self.running=False
            if ev.type==pygame.KEYDOWN:
                if self.state=="menu":
                    if ev.key==pygame.K_RETURN and self.pname.strip():
                        self.rooms=make_rooms(self.pname); self.state="playing"
                        self.wtxt="Kumpulkan 5 item, kembali ke Ruang Depan. Tekan E."
                        self.walpha=255
                    elif ev.key==pygame.K_BACKSPACE: self.pname=self.pname[:-1]
                    elif ev.key==pygame.K_ESCAPE: self.running=False
                    elif ev.unicode.isprintable() and len(self.pname)<20:
                        self.pname+=ev.unicode
                elif self.state=="playing":
                    if ev.key==pygame.K_ESCAPE: self.state="paused"
                    elif ev.key==pygame.K_f: self.player.fl_on=not self.player.fl_on
                    elif ev.key==pygame.K_m: self.snd_on=not self.snd_on
                    elif ev.key==pygame.K_TAB: self.show_obj=not self.show_obj
                    elif ev.key==pygame.K_h: self.show_ctrl=not self.show_ctrl
                    elif ev.key==pygame.K_j: self.show_journal=not self.show_journal
                    elif ev.key==pygame.K_c:
                        self.player.hidden=not self.player.hidden
                        if self.player.hidden:
                            self.wtxt="Kamu bersembunyi..."; self.walpha=200
                            self._ach("hiding")
                        else: self.wtxt="Kamu keluar dari persembunyian."; self.walpha=200
                    elif ev.key==pygame.K_F5: self.save()
                    elif ev.key==pygame.K_F9: self.load()
                    elif ev.key==pygame.K_e:
                        if self.cur_room=="entrance" and self.obj>=5:
                            self.state="ending"; self._ach("escape")
                            self.tw_text=(f"ANDA BERHASIL KELUAR DARI RUMAH...\n"
                                f"Rumah tidak lagi tahu nama {self.pname}.\n"
                                f"Atau mungkin... rumah hanya membiarkanmu pergi.\n"
                                f"Untuk sementara.")
                            self.tw_idx=0; self.tw_time=time.time()
                    elif ev.key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4,pygame.K_5):
                        idx=ev.key-pygame.K_1
                        if idx<len(self.inv): self.sel_item=idx
                elif self.state=="paused":
                    if ev.key in (pygame.K_ESCAPE,pygame.K_p): self.state="playing"
                    elif ev.key==pygame.K_q: self.running=False
                elif self.state in ("game_over","ending"):
                    if ev.key==pygame.K_r: self.respawn()
                    elif ev.key==pygame.K_q: self.running=False

            if ev.type==pygame.MOUSEBUTTONDOWN and self.state=="playing":
                if ev.button==3 and self.sel_item is not None:
                    if self.sel_item<len(self.inv):
                        it=self.inv[self.sel_item]
                        if it=="Lilin": self.player.sanity=min(100,self.player.sanity+12); self.inv.pop(self.sel_item)
                        elif it=="Fragmen Foto": self.player.sanity=min(100,self.player.sanity+18); self.inv.pop(self.sel_item)
                        elif it=="Obat Penenang": self.player.sanity=min(100,self.player.sanity+25); self.inv.pop(self.sel_item)
                        elif it=="Jimat Kuno": self.player.sanity=min(100,self.player.sanity+15); self.stalker.cooldown=200; self.inv.pop(self.sel_item)
                    self.sel_item=None
                elif ev.button==1:
                    mx,my=ev.pos
                    # Pick diary
                    rm=self.rooms[self.cur_room]
                    if rm.diary and not rm.diary_found:
                        r=ROOM_RECTS[self.cur_room]
                        if r.collidepoint(mx,my):
                            rm.diary_found=True; self.diaries_found.append(rm.diary)
                            self.wtxt="Halaman diary ditemukan!"; self.walpha=255
                            if self.snd_on: _snd(600,0.1,0.15)
                            if len(self.diaries_found)>=8: self._ach("semua_diary")
                    # Pick item
                    for rn,rect in ROOM_RECTS.items():
                        if rect.collidepoint(mx,my) and rn==self.cur_room:
                            for it in self.rooms[self.cur_room].items[:]:
                                if len(self.inv)<5:
                                    self.inv.append(it)
                                    self.rooms[self.cur_room].items.remove(it)
                                    self.obj+=1
                                    self.wtxt=f"Mengambil: {it}"; self.walpha=200
                                    if self.snd_on: _snd(440,0.1,0.15)
                                break

    # --- UPDATE ---
    def update(self,dt):
        if self.state!="playing": return
        self.tplay+=dt

        # Achievement: survivor
        if self.tplay>=300: self._ach("survivor")

        # Movement
        keys=pygame.key.get_pressed()
        self.player.sprinting=keys[pygame.K_LSHIFT] and self.player.stamina>0
        if self.player.sprinting and self.player.moving:
            self.sprint_total+=dt
            if self.sprint_total>=30: self._ach("sprint_master")
        dx=dy=0
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy-=1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy+=1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx-=1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx+=1
        # Reversed controls hallucination
        if self.reverse_controls: dx,dy=-dx,-dy
        if dx or dy:
            ln=math.hypot(dx,dy); dx/=ln; dy/=ln
            if not self.player.hidden: self.player.move(dx,dy,dt)
        self.player.update(dt)

        # Footsteps
        if self.player.moving and not self.player.hidden:
            if self.snd_on and time.time()-self.lfootstep>0.35:
                _snd(random.randint(60,100),0.05,0.12,"saw"); self.lfootstep=time.time()
            if random.random()<0.15: self.foots.append(Footprint(self.player.x,self.player.y))
        self.foots=[f for f in self.foots if f.alive()]
        for f in self.foots: f.update(dt)

        # Room detection
        nr=_room_at(self.player.x,self.player.y,self.cur_room)
        if nr!=self.cur_room:
            self.cur_room=nr; self.visited.add(nr)
            self.wtxt=self.rooms[nr].desc; self.walpha=255; self.flash=12
            if len(self.visited)>=8: self._ach("semua_ruangan")

        # Flashlight
        if self.player.fl_on:
            self.player.battery-=0.075
            if self.player.battery<=0: self.player.fl_on=False; self.player.battery=0
        else: self.player.battery=min(100,self.player.battery+0.04)

        # Sanity drain
        self.player.sanity-=self.san_rate
        if random.random()<0.012: self.player.sanity-=0.7
        self.player.sanity=max(0,min(100,self.player.sanity))

        # Flashlight cone
        mx,my=pygame.mouse.get_pos(); self.cone=None
        if self.player.fl_on and self.player.battery>5:
            ang=math.atan2(my-self.player.y,mx-self.player.x)
            fl=370; h=math.radians(27)
            p1=(self.player.x+math.cos(ang-h)*fl,self.player.y+math.sin(ang-h)*fl)
            p2=(self.player.x+math.cos(ang+h)*fl,self.player.y+math.sin(ang+h)*fl)
            self.cone=[(self.player.x,self.player.y),p1,p2]

        # Stalker
        self.stalker.update(self.player,self.cur_room,self.cone,dt)
        if self.stalker.active and self.stalker.collision(self.player) and not self.player.hidden:
            self.player.sanity-=21
            self.wtxt=f"{self.pname}... aku sudah di sini."; self.walpha=255
            self.stalker.cooldown=130
            if self.snd_on: _snd(110,0.6,0.45,"saw")
            if self.loop==0: self._ach("pertama_mati")

        if self.stalker.active:
            d=self.stalker.dist_to(self.player)
            if d<140: self.shake=9.0; self.player.sanity-=0.04
            elif d<220: self.shake=4.0
            if d<250 and self.snd_on and time.time()-self.lheartbeat>0.8:
                _snd(45,0.15,max(0.1,0.5-d/500)); self.lheartbeat=time.time()

        # Whispers
        if time.time()-self.lwhisper>random.uniform(6,13):
            if self.player.sanity<48 or self.stalker.active:
                self.wtxt=random.choice(self.rooms[self.cur_room].whispers)
                self.walpha=255
                if self.snd_on: _snd(random.randint(700,1300),0.4,0.22)
            self.lwhisper=time.time()

        # Horror events
        if (self.player.sanity<40 and time.time()-self.last_event>random.uniform(8,18)):
            ev=random.choice(HorrorEvent.EVENTS)
            self.event_msg=ev["msg"]; self.event_alpha=255
            self.shake=max(self.shake,ev["shake"])
            self.player.sanity+=ev["san"]
            if self.snd_on: _snd(random.randint(80,200),0.4,0.35,"saw")
            self.last_event=time.time()

        # Hallucinations
        if self.player.sanity<25:
            self.halluc_timer+=dt
            if not self.halluc_active and self.halluc_timer>random.uniform(5,12):
                self.halluc_active=True; self.halluc_timer=0
                self.halluc_type=random.choice(["reverse","fake_stalker","screen_warp"])
                if self.halluc_type=="reverse":
                    self.reverse_controls=True; self.wtxt="Kontrol terbalik!?"; self.walpha=200
                elif self.halluc_type=="fake_stalker":
                    for _ in range(random.randint(2,4)):
                        self.fake_stalkers.append([random.uniform(100,WIDTH-100),
                                                   random.uniform(100,HEIGHT-100),3.0])
                    self.wtxt="Mereka ada di mana-mana..."; self.walpha=200
            if self.halluc_active:
                if self.halluc_type=="reverse":
                    self.halluc_timer+=dt
                    if self.halluc_timer>4: self.reverse_controls=False; self.halluc_active=False; self.halluc_timer=0
                elif self.halluc_type=="fake_stalker":
                    self.fake_stalkers=[[x,y,t-dt] for x,y,t in self.fake_stalkers if t>0]
                    if not self.fake_stalkers: self.halluc_active=False; self.halluc_timer=0
                elif self.halluc_type=="screen_warp":
                    self.halluc_timer+=dt
                    if self.halluc_timer>3: self.halluc_active=False; self.halluc_timer=0
        else:
            self.halluc_active=False; self.reverse_controls=False
            self.fake_stalkers.clear(); self.halluc_timer=0

        # Particles
        if len(self.blood)<16 and self.player.sanity<52 and random.random()<0.19:
            self.blood.append(BloodDrip())
        self.blood=[d for d in self.blood if d.alive()]
        for d in self.blood: d.update(dt)

        mx_dust=45 if self.cur_room in ("basement","attic") else 25
        if len(self.dust)<mx_dust and random.random()<0.3: self.dust.append(Dust())
        self.dust=[p for p in self.dust if p.alive()]
        for p in self.dust: p.update(dt)

        # Flicker
        if time.time()-self.lflicker>random.uniform(0.08,0.3):
            self.flicker=random.uniform(0.74,1.0); self.lflicker=time.time()

        # Achievement timer
        if self.ach_timer>0: self.ach_timer-=dt

        # Game over
        if self.player.sanity<=0:
            self.state="game_over"
            if self.loop==0: self._ach("pertama_mati")

    # --- DRAW ---
    def draw(self,dt):
        self._ensure_surf()
        if self.state=="menu": self._draw_menu(dt); return

        # BG
        rc=tuple(min(255,int(c*self.flicker*1.13)) for c in self.rooms[self.cur_room].color)
        screen.fill(rc)

        # Transition flash
        if self.flash>0:
            fs=pygame.Surface((WIDTH,HEIGHT)); fs.fill(WHITE); fs.set_alpha(min(255,self.flash*15))
            screen.blit(fs,(0,0)); self.flash-=1

        # Room outlines + doors
        self._draw_rooms()

        # Footprints
        for f in self.foots: f.draw(screen)

        # Player & stalker
        self.player.draw(screen)
        self.stalker.draw(screen)

        # Fake stalkers (hallucination)
        for fx,fy,ft in self.fake_stalkers:
            a=int(max(0,min(255,ft*85)))
            pygame.draw.circle(screen,(8,8,8),(int(fx),int(fy)),25)
            pygame.draw.circle(screen,(*BLOOD,a),(int(fx)-8,int(fy)-6),6)
            pygame.draw.circle(screen,(*BLOOD,a),(int(fx)+8,int(fy)-6),6)

        # Particles
        self.s_part.fill((0,0,0,0))
        for p in self.dust: p.draw(self.s_part)
        screen.blit(self.s_part,(0,0))

        # Ambient
        self.s_amb.fill((0,0,0,0))
        pygame.draw.circle(self.s_amb,(38,28,18,48),(int(self.player.x),int(self.player.y)),210)
        screen.blit(self.s_amb,(0,0))

        # Darkness
        dark_a=132+int(max(0,(40-self.player.sanity))*1.5) if self.player.sanity<40 else 132
        self.s_dark.fill((0,0,0,min(220,dark_a)))
        if self.cone and self.player.fl_on:
            pygame.draw.polygon(self.s_dark,(0,0,0,0),self.cone)
            pygame.draw.polygon(self.s_dark,(58,42,28,60),self.cone,24)
        screen.blit(self.s_dark,(0,0))

        # Vignette
        vig_a=min(255,int(180+(100-self.player.sanity)*0.75))
        self.s_vig.set_alpha(vig_a)
        screen.blit(self.s_vig,(0,0))

        # Screen warp halluc
        if self.halluc_active and self.halluc_type=="screen_warp":
            warp=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            warp.fill((BLOOD[0],0,0,25))
            screen.blit(warp,(random.randint(-3,3),random.randint(-3,3)))

        # Blood drips
        for d in self.blood: d.draw(screen)

        # HUD
        self._draw_hud()
        self._draw_minimap()

        # Item & diary indicators
        rm=self.rooms[self.cur_room]
        if rm.items and self.state=="playing": self._draw_item_ind()
        if rm.diary and not rm.diary_found and self.state=="playing":
            _txt(screen,"📖 Halaman diary terdeteksi! Klik untuk ambil.",FX,CYAN,(WIDTH//2-180,HEIGHT//2+110))

        # Whisper
        if self.walpha>0:
            self.walpha=max(0,self.walpha-4)
            tc=BLOOD if self.player.sanity<38 else WHITE
            _txt(screen,self.wtxt,FM,tc,(WIDTH//2-260,HEIGHT-95),int(self.walpha))

        # Event message
        if self.event_alpha>0:
            self.event_alpha=max(0,self.event_alpha-3)
            _txt(screen,self.event_msg,FB,BLOOD,(WIDTH//2-300,HEIGHT//2-170),int(self.event_alpha))

        # Achievement popup
        if self.ach_timer>0:
            ab=pygame.Surface((500,50),pygame.SRCALPHA); ab.fill((0,0,0,180))
            screen.blit(ab,(WIDTH//2-250,100))
            _txt(screen,self.ach_display,FS,YELLOW,(WIDTH//2-230,112))

        # Overlays
        if self.show_ctrl: self._draw_ctrl()
        if self.show_journal: self._draw_journal()
        if self.state=="paused": self._draw_pause()
        if self.state=="game_over": self._draw_go()
        if self.state=="ending": self._draw_end()

        # Shake
        if self.shake>0:
            sa=int(self.shake)
            if sa>0: screen.blit(screen,(random.randint(-sa,sa),random.randint(-sa,sa)))
            self.shake-=0.7
            if self.shake<0.5: self.shake=0

        if not self.snd_on and SOUND_AVAILABLE:
            _txt(screen,"SUARA MATI (M)",FX,(255,180,0),(WIDTH-180,HEIGHT-30))
        pygame.display.flip()

    # --- DRAW HELPERS ---
    def _draw_menu(self,dt):
        screen.fill(BLACK)
        ta=int(180+math.sin(time.time()*2)*75)
        t=FT.render("RUMAH YANG TAHU NAMAMU",True,BLOOD); t.set_alpha(ta)
        screen.blit(t,(WIDTH//2-t.get_width()//2,80))
        _txt(screen,"— ULTIMATE EDITION —",FS,DARK_RED,(WIDTH//2-110,145))
        _txt(screen,"Sebuah game horor oleh Lzroars23",FS,DIM,(WIDTH//2-160,175))
        pygame.draw.line(screen,DARK_RED,(WIDTH//2-200,210),(WIDTH//2+200,210),2)
        _txt(screen,"Masukkan nama Anda:",FM,WHITE,(WIDTH//2-130,260))
        bw=400; bx=WIDTH//2-bw//2; by=310
        pygame.draw.rect(screen,GRAY,(bx,by,bw,50))
        pygame.draw.rect(screen,BLOOD,(bx,by,bw,50),3)
        self.cursor_blink+=dt
        dn=self.pname+("|" if (self.cursor_blink%1)<0.5 else "")
        _txt(screen,dn,FM,WHITE,(bx+15,by+12))
        if self.pname.strip():
            ea=int(150+math.sin(time.time()*4)*100)
            _txt(screen,"Tekan ENTER untuk memulai",FM,BLOOD,(WIDTH//2-170,400),ea)
        else: _txt(screen,"Ketik nama lalu tekan ENTER",FS,DIM,(WIDTH//2-150,400))
        tips=["WASD = Gerak | SHIFT = Sprint | F = Senter | C = Sembunyi",
              "J = Jurnal | H = Bantuan | F5 = Simpan | F9 = Muat"]
        for i,tp in enumerate(tips): _txt(screen,tp,FX,LGRAY,(WIDTH//2-250,HEIGHT-80+i*22))
        if random.random()<0.08: self.blood.append(BloodDrip())
        self.blood=[d for d in self.blood if d.alive()]
        for d in self.blood: d.update(dt); d.draw(screen)

        # Gambar ruangan kecil sebagai preview
        _txt(screen,"8 Ruangan untuk Dijelajahi",FX,DARK_RED,(WIDTH//2-100,HEIGHT-130))
        pygame.display.flip()

    def _draw_rooms(self):
        for rn,rect in ROOM_RECTS.items():
            c=(60,20,20) if rn==self.cur_room else (32,12,12)
            w=8 if rn==self.cur_room else 5
            pygame.draw.rect(screen,c,rect,w)
            # Room label
            _txt(screen,self.rooms[rn].name,FX,(80,60,60),(rect.x+5,rect.y+5))
        for r1,r2 in ROOM_CONNS:
            rc1,rc2=ROOM_RECTS[r1],ROOM_RECTS[r2]
            c1,c2=rc1.center,rc2.center
            col=(80,40,40) if r1==self.cur_room or r2==self.cur_room else (40,20,20)
            dx,dy=c2[0]-c1[0],c2[1]-c1[1]; d=math.hypot(dx,dy)
            if d==0: continue
            st=int(d/12)
            for i in range(0,st,2):
                t1,t2=i/st,min((i+1)/st,1)
                pygame.draw.line(screen,col,
                    (int(c1[0]+dx*t1),int(c1[1]+dy*t1)),
                    (int(c1[0]+dx*t2),int(c1[1]+dy*t2)),2)
            mx,my=(c1[0]+c2[0])//2,(c1[1]+c2[1])//2
            dp=int(60+math.sin(time.time()*3)*30)
            pygame.draw.circle(screen,(dp,dp//3,dp//3),(mx,my),5)

    def _draw_hud(self):
        _txt(screen,self.rooms[self.cur_room].name,FM,WHITE,(30,25))
        # Sanity
        bw=320; fs=int((self.player.sanity/100)*bw)
        sc=GREEN if self.player.sanity>60 else YELLOW if self.player.sanity>30 else BLOOD
        pygame.draw.rect(screen,GRAY,(WIDTH//2-bw//2,35,bw,18))
        pygame.draw.rect(screen,sc,(WIDTH//2-bw//2,35,fs,18))
        pygame.draw.rect(screen,WHITE,(WIDTH//2-bw//2,35,bw,18),1)
        _txt(screen,f"Kewarasan: {int(self.player.sanity)}%",FS,WHITE,(WIDTH//2-80,10))
        # Battery
        bf=max(0,int(self.player.battery*1.6))
        bc=(210,190,70) if self.player.battery>20 else BLOOD
        pygame.draw.rect(screen,LGRAY,(WIDTH-200,35,160,12))
        pygame.draw.rect(screen,bc,(WIDTH-200,35,bf,12))
        pygame.draw.rect(screen,WHITE,(WIDTH-200,35,160,12),1)
        fs2="ON" if self.player.fl_on else "OFF"
        _txt(screen,f"Senter: {fs2}",FX,WHITE,(WIDTH-200,15))
        # Stamina
        stf=int(self.player.stamina*1.6)
        pygame.draw.rect(screen,GRAY,(WIDTH-200,52,160,8))
        pygame.draw.rect(screen,CYAN,(WIDTH-200,52,stf,8))
        _txt(screen,"Sprint",FX,CYAN,(WIDTH-200,60)) if self.player.sprinting else None
        # Loop
        if self.loop>0: _txt(screen,f"Loop: {self.loop}",FX,BLOOD,(WIDTH-90,72))
        # Inventory
        ib=pygame.Surface((WIDTH-100,55),pygame.SRCALPHA); ib.fill((15,15,15,180))
        screen.blit(ib,(50,HEIGHT-70))
        _txt(screen,"Inventori:",FX,DIM,(55,HEIGHT-68))
        for i,it in enumerate(self.inv):
            c=BLOOD if i==self.sel_item else WHITE
            sx=70+i*130
            pygame.draw.rect(screen,c,(sx,HEIGHT-55,110,35),3)
            _txt(screen,f"[{i+1}] {it}",FX,c,(sx+4,HEIGHT-47))
        # Hiding indicator
        if self.player.hidden:
            ha=int(180+math.sin(time.time()*8)*75)
            _txt(screen,"🫣 BERSEMBUNYI",FS,PURPLE,(WIDTH//2-80,60),ha)
        # Objective
        if self.show_obj and self.state=="playing":
            ot=f"Item: {self.obj}/5"
            if self.obj>=5: ot+=" — Ruang Depan, tekan E!"
            _txt(screen,ot,FS,YELLOW,(30,80))
            # Diary counter
            _txt(screen,f"Diary: {len(self.diaries_found)}/8",FX,CYAN,(30,100))

    def _draw_minimap(self):
        mx,my,mw,mh=WIDTH-190,80,170,130
        mb=pygame.Surface((mw,mh),pygame.SRCALPHA); mb.fill((10,10,10,160))
        screen.blit(mb,(mx,my)); pygame.draw.rect(screen,DARK_RED,(mx,my,mw,mh),2)
        sx,sy=mw/WIDTH,mh/HEIGHT
        for rn,rect in ROOM_RECTS.items():
            mr=pygame.Rect(mx+int(rect.x*sx),my+int(rect.y*sy),
                max(6,int(rect.width*sx)),max(4,int(rect.height*sy)))
            c=(120,40,40) if rn==self.cur_room else (50,20,20) if rn in self.visited else (25,10,10)
            pygame.draw.rect(screen,c,mr); pygame.draw.rect(screen,(80,30,30),mr,1)
        px,py=mx+int(self.player.x*sx),my+int(self.player.y*sy)
        pygame.draw.circle(screen,GREEN,(px,py),3)
        if self.stalker.active:
            stx,sty=mx+int(self.stalker.x*sx),my+int(self.stalker.y*sy)
            if (time.time()*4)%1<0.5: pygame.draw.circle(screen,BLOOD,(stx,sty),3)
        _txt(screen,"PETA",FX,DIM,(mx+5,my+3))

    def _draw_item_ind(self):
        p=math.sin(time.time()*5)*12+38; cx,cy=WIDTH//2,HEIGHT//2-30
        pygame.draw.circle(screen,YELLOW,(cx,cy),int(p),5)
        h=FS.render("ADA ITEM DI SINI!",True,YELLOW)
        h.set_alpha(int(180+math.sin(time.time()*6)*75))
        screen.blit(h,(cx-h.get_width()//2,cy+50))

    def _draw_ctrl(self):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,210))
        screen.blit(ov,(0,0))
        _txt(screen,"BANTUAN KONTROL",FB,WHITE,(WIDTH//2-180,60))
        ctrls=[("WASD/Panah","Gerak"),("SHIFT","Sprint"),("F","Senter"),
            ("C","Sembunyi"),("M","Suara"),("H","Bantuan ini"),("J","Jurnal/Diary"),
            ("TAB","Objektif"),("ESC","Jeda"),("F5","Simpan"),("F9","Muat"),
            ("E","Keluar (5 item)"),("1-5","Pilih item"),("Klik Kiri","Ambil item/diary"),
            ("Klik Kanan","Gunakan item")]
        for i,(k,d) in enumerate(ctrls):
            y=120+i*32
            _txt(screen,f"[{k}]",FM,BLOOD,(WIDTH//2-200,y))
            _txt(screen,d,FS,WHITE,(WIDTH//2+20,y+3))
        _txt(screen,"Tekan H untuk menutup",FS,DIM,(WIDTH//2-120,HEIGHT-50))

    def _draw_journal(self):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,220))
        screen.blit(ov,(0,0))
        _txt(screen,"📖 JURNAL — Halaman Diary",FB,CYAN,(WIDTH//2-220,60))
        if not self.diaries_found:
            _txt(screen,"Belum ada halaman ditemukan.",FS,DIM,(WIDTH//2-140,150))
            _txt(screen,"Klik kiri di ruangan untuk mencari halaman diary.",FX,DIM,(WIDTH//2-200,180))
        else:
            for i,d in enumerate(self.diaries_found):
                y=120+i*40
                _txt(screen,f"• {d}",FS,WHITE,(100,y))
        _txt(screen,"Tekan J untuk menutup",FS,DIM,(WIDTH//2-120,HEIGHT-50))

    def _draw_pause(self):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,180))
        screen.blit(ov,(0,0))
        _txt(screen,"JEDA",FT,BLOOD,(WIDTH//2-80,HEIGHT//2-80))
        _txt(screen,"ESC / P = Lanjut  |  Q = Keluar",FM,WHITE,(WIDTH//2-230,HEIGHT//2+20))
        # Stats in pause
        m=int(self.tplay//60); s=int(self.tplay%60)
        _txt(screen,f"Waktu: {m}m {s}d  |  Loop: {self.loop}  |  Ruangan: {len(self.visited)}/8",
             FX,DIM,(WIDTH//2-200,HEIGHT//2+65))
        _txt(screen,f"Achievement: {len(self.achievements)}/{len(ACHIEVEMENTS)}",
             FX,YELLOW,(WIDTH//2-100,HEIGHT//2+85))

    def _draw_go(self):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,210))
        screen.blit(ov,(0,0))
        _txt(screen,"RUMAH TELAH MENGAMBIL ANDA",FB,BLOOD,(WIDTH//2-290,HEIGHT//2-150))
        m=int(self.tplay//60); s=int(self.tplay%60)
        stats=[f"Nama: {self.pname}",f"Waktu: {m}m {s}d",
            f"Ruangan: {len(self.visited)}/8",f"Item: {self.obj}/5",
            f"Diary: {len(self.diaries_found)}/8",
            f"Kematian: {self.loop}",f"Achievement: {len(self.achievements)}/{len(ACHIEVEMENTS)}"]
        for i,st in enumerate(stats):
            _txt(screen,st,FS,WHITE,(WIDTH//2-120,HEIGHT//2-70+i*28))
        _txt(screen,"R = Respawn (Time Loop)  |  Q = Keluar",FM,WHITE,(WIDTH//2-260,HEIGHT//2+140))

    def _draw_end(self):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,220))
        screen.blit(ov,(0,0))
        if time.time()-self.tw_time>0.05 and self.tw_idx<len(self.tw_text):
            self.tw_idx+=1; self.tw_time=time.time()
            if self.snd_on and random.random()<0.3: _snd(random.randint(300,500),0.02,0.08)
        disp=self.tw_text[:self.tw_idx]
        for i,ln in enumerate(disp.split("\n")):
            _txt(screen,ln,FB,(0,255,80),(WIDTH//2-350,HEIGHT//2-100+i*50))
        if self.tw_idx>=len(self.tw_text):
            if (time.time()*2)%1<0.5:
                _txt(screen,"R = Main lagi  |  Q = Keluar",FS,WHITE,(WIDTH//2-170,HEIGHT//2+120))

    def run(self):
        while self.running:
            dt=clock.tick(FPS)/1000.0
            self.handle_events(dt); self.update(dt); self.draw(dt)
        pygame.quit(); sys.exit()

if __name__=="__main__":
    Game().run()
