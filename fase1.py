# fase1.py
# Plataforma 2D simples (inspirado em nível clássico)
# Requisitos: Python 3.8+ and pygame (pip install pygame)

import pygame, sys
from pygame.locals import *
pygame.init()

# --- CONFIG ---
FPS = 60
SCREEN_W, SCREEN_H = 800, 448  # proporção clássica
TILE = 32
GRAVITY = 0.9
JUMP_VEL = -15
PLAYER_SPEED = 4.5
FONT = pygame.font.SysFont("Arial", 18)

# --- CORES ---
BG_COLOR = (106, 150, 252)  # céu
GROUND_COLOR = (100, 60, 20)
PLAYER_COLOR = (255, 50, 50)
BLOCK_COLOR = (170, 120, 70)
COIN_COLOR = (255, 215, 0)
ENEMY_COLOR = (80, 80, 80)
FLAG_COLOR = (0, 180, 0)

# --- TELA ---
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()
pygame.display.set_caption("Fase 1 — Plataforma (inspirado)")

# --- TILEMAP (0=vazio, 1=bloco chão, 2=moeda, 3=inimigo, 4=plataforma chão alto, 9=bandeira) ---
# cada linha tem SCREEN_W / TILE colunas
cols = SCREEN_W // TILE
rows = SCREEN_H // TILE

# Mapa simples: list de strings para facilitar edição
map_data = [
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000002000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000200000000000000000002000000",
"00011100000000111000000011100000",
"00000000000000000000000000000000",
"00000000000300000000000000000000",
"00000000000000000000000000000000",
"00000111110000011111000000111110",
"00000000000000000000000000000000",
"00000000000000000000000000000000",
"00000000000000000000000000000009",
"11111111111111111111111111111111",
"11111111111111111111111111111111",
"11111111111111111111111111111111",
"11111111111111111111111111111111",
"11111111111111111111111111111111",
]

# Converte chars -> ints e ajusta altura
tilemap = []
for rline in map_data:
    row = [int(ch) for ch in rline]
    tilemap.append(row)

# --- ENTIDADES ---
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, TILE-4, TILE-4)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.lives = 3
        self.score = 0

    def update(self, tiles, coins, enemies, flag_rect):
        keys = pygame.key.get_pressed()
        self.vx = 0
        if keys[K_LEFT] or keys[K_a]:
            self.vx = -PLAYER_SPEED
        if keys[K_RIGHT] or keys[K_d]:
            self.vx = PLAYER_SPEED
        if (keys[K_SPACE] or keys[K_w] or keys[K_UP]) and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

        # aplicar gravidade
        self.vy += GRAVITY
        if self.vy > 20: self.vy = 20

        # movimento horizontal + colisão
        self.rect.x += int(self.vx)
        self.collide(self.vx, 0, tiles)

        # movimento vertical + colisão
        self.rect.y += int(self.vy)
        self.on_ground = False
        self.collide(0, self.vy, tiles)

        # coleta de moedas
        for coin in coins[:]:
            if self.rect.colliderect(coin):
                coins.remove(coin)
                self.score += 100

        # colisão com inimigos
        for e in enemies:
            if self.rect.colliderect(e.rect):
                # se estiver caindo e colidir por cima -> inimigo morre
                if self.vy > 0 and (self.rect.bottom - e.rect.top) < 12:
                    e.alive = False
                    self.vy = JUMP_VEL/2
                    self.score += 200
                else:
                    # perde vida e respawna no inicio
                    self.lives -= 1
                    self.respawn()
                    break

        # checa bandeira (fim de fase)
        if flag_rect and self.rect.colliderect(flag_rect):
            return "WIN"
        if self.lives <= 0:
            return "DEAD"
        return None

    def collide(self, vx, vy, tiles):
        # verifica colisões com blocos sólidos (1 e 4)
        for row_i, row in enumerate(tiles):
            for col_i, v in enumerate(row):
                if v in (1,4):
                    block = pygame.Rect(col_i*TILE, row_i*TILE, TILE, TILE)
                    if self.rect.colliderect(block):
                        if vx > 0:
                            self.rect.right = block.left
                        if vx < 0:
                            self.rect.left = block.right
                        if vy > 0:
                            self.rect.bottom = block.top
                            self.vy = 0
                            self.on_ground = True
                        if vy < 0:
                            self.rect.top = block.bottom
                            self.vy = 0

    def respawn(self):
        self.rect.topleft = (TILE, SCREEN_H - 5*TILE)
        self.vx = self.vy = 0

class Enemy:
    def __init__(self, x, y, patrol_w=2):
        self.rect = pygame.Rect(x, y, TILE-4, TILE-4)
        self.vx = 1
        self.patrol = patrol_w * TILE
        self.start_x = x
        self.alive = True

    def update(self, tiles):
        if not self.alive: return
        self.rect.x += self.vx
        if abs(self.rect.x - self.start_x) > self.patrol:
            self.vx *= -1
        # colisão básica com chão
        self.rect.y += 2
        on_ground = False
        for row_i,row in enumerate(tiles):
            for col_i,v in enumerate(row):
                if v in (1,4):
                    block = pygame.Rect(col_i*TILE, row_i*TILE, TILE, TILE)
                    if self.rect.colliderect(block):
                        on_ground = True
                        self.rect.bottom = block.top
        self.rect.y -= 2
        # se cair no vazio, inverte
        if not on_ground:
            self.vx *= -1

# --- Cria listas de objetos a partir do tilemap ---
coins = []
enemies = []
tiles = tilemap
flag_rect = None

for r, row in enumerate(tilemap):
    for c, val in enumerate(row):
        x, y = c*TILE, r*TILE
        if val == 2:
            coins.append(pygame.Rect(x+8, y+8, TILE-16, TILE-16))
        elif val == 3:
            enemies.append(Enemy(x+2, y+2))
        elif val == 9:
            flag_rect = pygame.Rect(x+8, y, TILE, TILE*3)

# jogador spawn
player = Player(TILE, SCREEN_H - 5*TILE)

# --- funções utilitárias ---
def draw_map():
    for r, row in enumerate(tilemap):
        for c, val in enumerate(row):
            x, y = c*TILE, r*TILE
            if val == 1:
                pygame.draw.rect(screen, BLOCK_COLOR, (x, y, TILE, TILE))
            if val == 4:
                pygame.draw.rect(screen, BLOCK_COLOR, (x, y, TILE, TILE))
            if val == 2:
                pygame.draw.circle(screen, COIN_COLOR, (x+TILE//2, y+TILE//2), 8)
            if val == 3:
                pygame.draw.rect(screen, ENEMY_COLOR, (x+4, y+4, TILE-8, TILE-8))
            if val == 9:
                pygame.draw.rect(screen, FLAG_COLOR, (x+TILE//4, y, TILE//2, TILE*3))
    # chão visual: desenhar faixa no fim
    pygame.draw.rect(screen, GROUND_COLOR, (0, SCREEN_H - TILE, SCREEN_W, TILE))

def draw_ui():
    text = FONT.render(f"Pontuação: {player.score}   Vidas: {player.lives}", True, (0,0,0))
    screen.blit(text, (8,8))

def reset_level():
    global player, coins, enemies, tilemap, flag_rect
    # recria o mapa original para reiniciar moedas e inimigos
    tilemap_local = [list(map(int, list(row))) for row in map_data]
    tilemap[:] = tilemap_local
    coins[:] = []
    enemies[:] = []
    flag_rect = None
    for r, row in enumerate(tilemap):
        for c, val in enumerate(row):
            x,y = c*TILE, r*TILE
            if val == 2:
                coins.append(pygame.Rect(x+8, y+8, TILE-16, TILE-16))
            elif val == 3:
                enemies.append(Enemy(x+2, y+2))
            elif val == 9:
                flag_rect = pygame.Rect(x+8, y, TILE, TILE*3)
    player.respawn()
    player.lives = 3
    player.score = 0

# --- LOOP PRINCIPAL ---
running = True
game_state = "PLAY"  # PLAY, WIN, LOSE

while running:
    dt = clock.tick(FPS)
    for ev in pygame.event.get():
        if ev.type == QUIT:
            running = False
        if ev.type == KEYDOWN:
            if ev.key == K_r:
                reset_level()
                game_state = "PLAY"
            if ev.key == K_ESCAPE:
                running = False

    if game_state == "PLAY":
        # update entidades
        res = player.update(tilemap, coins, enemies, flag_rect)
        for e in enemies[:]:
            e.update(tilemap)
            if not e.alive:
                # remove visual do inimigo do mapa (crash-safe)
                enemies.remove(e)
        if res == "WIN":
            game_state = "WIN"
        if res == "DEAD":
            game_state = "LOSE"

    # --- RENDER ---
    screen.fill(BG_COLOR)
    draw_map()

    # desenha moedas restantes (caso foram criadas separadamente)
    for coin in coins:
        pygame.draw.circle(screen, COIN_COLOR, coin.center, 8)

    # desenha inimigos vivos
    for e in enemies:
        pygame.draw.rect(screen, ENEMY_COLOR, e.rect)

    # bandeira
    if flag_rect:
        pygame.draw.rect(screen, FLAG_COLOR, flag_rect)

    # jogador
    pygame.draw.rect(screen, PLAYER_COLOR, player.rect)

    # UI
    draw_ui()

    if game_state == "WIN":
        txt = FONT.render("Você completou a fase! Pressione R para reiniciar.", True, (0,0,0))
        screen.blit(txt, (SCREEN_W//2 - 200, SCREEN_H//2))
    elif game_state == "LOSE":
        txt = FONT.render("Você perdeu todas as vidas. Pressione R para tentar de novo.", True, (0,0,0))
        screen.blit(txt, (SCREEN_W//2 - 220, SCREEN_H//2))

    pygame.display.flip()

pygame.quit()
sys.exit()
