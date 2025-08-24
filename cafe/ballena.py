import os, sys, math, random
import pygame

ASSET_DIR = "assets"
IMG_BG = "background.png"
IMG_FLOOR = "seafloor.png"
IMG_WHALE = "whale.gif"     
WHALE_SIZE = (84, 60)       
WHALE_ANIM_FPS = 12        
IMG_TRASH = "trash.png"
SND_FLAP = "flap.wav"
SND_SCORE = "score.wav"
SND_HIT = "hit.wav"

# ----------------------------
# Parámetros del juego
# ----------------------------
ANCHO, ALTO = 480, 800
FPS = 60

GRAVEDAD = 2200      
IMPULSO = 620        
VEL_SCROLL_BG = 60   
VEL_SCROLL_SUELO = 180
VEL_OBSTACULOS = 220

ANCHO_COLUMNA = 90
GAP_INICIAL = 200
GAP_MIN = 140
SPAWN_MS = 1400

BORDE_SUPERIOR = 0
ALTURA_SUELO = 96

def ruta_asset(nombre):
    return os.path.join(ASSET_DIR, nombre)

def cargar_imagen(nombre, escala=None, flip_y=False):
    try:
        surf = pygame.image.load(ruta_asset(nombre)).convert_alpha()
        if escala:
            surf = pygame.transform.smoothscale(surf, escala)
        if flip_y:
            surf = pygame.transform.flip(surf, False, True)
        return surf
    except Exception:
        return None

def cargar_sonido(nombre, volumen=0.35):
    try:
        snd = pygame.mixer.Sound(ruta_asset(nombre))
        snd.set_volume(volumen)
        return snd
    except Exception:
        return None

def cargar_animacion_gif(nombre, escala=None):
    """
    Devuelve lista de frames (pygame.Surface) desde un GIF animado.
    Si no hay Pillow, intenta cargar un solo frame con pygame.
    """
    try:
        from PIL import Image
        im = Image.open(ruta_asset(nombre))
        frames = []
        for i in range(getattr(im, "n_frames", 1)):
            im.seek(i)
            fr = im.convert("RGBA")
            data = fr.tobytes()
            size = fr.size
            surf = pygame.image.fromstring(data, size, "RGBA").convert_alpha()
            if escala:
                surf = pygame.transform.smoothscale(surf, escala)
            frames.append(surf)
        return frames
    except Exception:
        s = cargar_imagen(nombre, escala=escala)
        return [s] if s is not None else []

# ----------------------------
# Clases
# ----------------------------
class Ballena:
    """Versión animada: recibe lista de frames."""
    def __init__(self, x, y, frames, anim_fps=10):
        self.x = x
        self.y = y
        self.vy = 0.0
        self.frames = [f for f in frames if f is not None]
        if not self.frames:
            # Placeholder si no hay frames válidos
            ph = pygame.Surface(WHALE_SIZE, pygame.SRCALPHA)
            pygame.draw.ellipse(ph, (90, 200, 255), ph.get_rect())
            pygame.draw.ellipse(ph, (255, 255, 255), (ph.get_width()-36, ph.get_height()//2-8, 14, 14))
            self.frames = [ph]
        self.frame_idx = 0
        self.anim_fps = max(1, anim_fps)
        self.anim_timer = 0.0
        self.img = self.frames[self.frame_idx]
        self.rect = self.img.get_rect(center=(self.x, self.y))
        self.rotada = self.img

    def flap(self):
        self.vy = -IMPULSO

    def update(self, dt):
        # Física
        self.vy += GRAVEDAD * dt
        self.y += self.vy * dt

        # Animación
        self.anim_timer += dt
        if self.anim_timer >= 1.0 / self.anim_fps:
            self.anim_timer = 0.0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        base = self.frames[self.frame_idx]

        # Rotación estética según velocidad
        ang = max(-30, min(60, self.vy * 0.06))
        self.rotada = pygame.transform.rotate(base, -ang)
        self.rect = self.rotada.get_rect(center=(self.x, self.y))

    def draw(self, screen):
        screen.blit(self.rotada, self.rect.topleft)

    def get_mask(self):
        return pygame.mask.from_surface(self.rotada)

class ColumnaBasura:
    """Par de columnas (superior e inferior) con un hueco (gap)."""
    def __init__(self, x, gap_y, gap_altura, textura):
        self.x = x
        self.gap_y = gap_y
        self.gap_altura = gap_altura
        self.textura_base = textura

        self.ancho = ANCHO_COLUMNA
        self.scored = False

        # Alturas desde el centro del gap
        top_altura = max(20, int(gap_y - gap_altura / 2))
        bottom_y = int(gap_y + gap_altura / 2)
        bottom_altura = max(20, ALTO - ALTURA_SUELO - bottom_y)

        # Superficies
        self.superior = self._crear_columna(top_altura, flip_y=True)
        self.inferior = self._crear_columna(bottom_altura, flip_y=False)

        # Rects
        self.rect_top = self.superior.get_rect(midbottom=(self.x, top_altura))
        self.rect_bottom = self.inferior.get_rect(midtop=(self.x, bottom_y))

    def _crear_columna(self, altura, flip_y=False):
        if self.textura_base is not None:
            tex = pygame.transform.smoothscale(self.textura_base, (self.ancho, max(10, altura)))
            if flip_y:
                tex = pygame.transform.flip(tex, False, True)
            return tex
        else:
            surf = pygame.Surface((self.ancho, max(10, altura)), pygame.SRCALPHA)
            color = (60, 120, 80, 255)
            pygame.draw.rect(surf, color, surf.get_rect(), border_radius=10)
            for i in range(0, surf.get_height(), 18):
                pygame.draw.line(surf, (80, 160, 110, 140), (8, i), (self.ancho - 8, i), 2)
            if flip_y:
                surf = pygame.transform.flip(surf, False, True)
            return surf

    def update(self, dt):
        dx = -VEL_OBSTACULOS * dt
        self.x += dx
        self.rect_top.x += dx
        self.rect_bottom.x += dx

    def draw(self, screen):
        screen.blit(self.superior, self.rect_top.topleft)
        screen.blit(self.inferior, self.rect_bottom.topleft)

    def fuera_de_pantalla(self):
        return self.rect_top.right < -10 and self.rect_bottom.right < -10


def dibujar_fondo(screen, bg_surf, offset):
    if bg_surf:
        w = bg_surf.get_width()
        x = - (offset % w)
        screen.blit(bg_surf, (x, 0))
        screen.blit(bg_surf, (x + w, 0))
    else:
        screen.fill((10, 28, 48))
        pygame.draw.rect(screen, (12, 70, 120), (0, 0, ANCHO, 220))

def dibujar_suelo(screen, floor_surf, offset):
    y = ALTO - ALTURA_SUELO
    if floor_surf:
        w = floor_surf.get_width()
        x = - (offset % w)
        screen.blit(floor_surf, (x, y))
        screen.blit(floor_surf, (x + w, y))
    else:
        pygame.draw.rect(screen, (20, 40, 60), (0, y, ANCHO, ALTURA_SUELO))

def texto(screen, msg, size, y, color=(255, 255, 255), bold=False, sombra=True):
    font = pygame.font.SysFont("arial", size, bold=bold)
    surf = font.render(msg, True, color)
    rect = surf.get_rect(center=(ANCHO // 2, y))
    if sombra:
        sh = font.render(msg, True, (0, 0, 0))
        screen.blit(sh, (rect.x + 2, rect.y + 2))
    screen.blit(surf, rect.topleft)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _collide_mask(ballena, mask_ballena, otro_surf, otro_rect):
    """Colisión pixel-perfect entre ballena rotada y columna (si hay alpha)."""
    if otro_surf is None:
        return ballena.rect.colliderect(otro_rect)
    mask_otro = pygame.mask.from_surface(otro_surf)
    offset = (otro_rect.x - ballena.rect.x, otro_rect.y - ballena.rect.y)
    return mask_ballena.overlap(mask_otro, offset) is not None

 
def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    screen = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Flappy Whale – Esquiva la basura")
    clock = pygame.time.Clock()

    bg_img = cargar_imagen(IMG_BG)
    floor_img = cargar_imagen(IMG_FLOOR, escala=(ANCHO, ALTURA_SUELO))
    whale_frames = cargar_animacion_gif(IMG_WHALE, escala=WHALE_SIZE)
    trash_tex = cargar_imagen(IMG_TRASH, escala=(ANCHO_COLUMNA, 400))  # base, luego se re-escala por altura

    snd_flap = cargar_sonido(SND_FLAP, volumen=0.4)
    snd_score = cargar_sonido(SND_SCORE, volumen=0.4)
    snd_hit = cargar_sonido(SND_HIT, volumen=0.45)


    JUGANDO, GAMEOVER, READY = 0, 1, 2
    estado = READY

    ballena = Ballena(ANCHO * 0.35, ALTO * 0.45, whale_frames, anim_fps=WHALE_ANIM_FPS)
    columnas = []
    tiempo_spawn = 0
    score = 0
    highscore = 0

    bg_off = 0
    floor_off = 0

    burbujas = []

    def reiniciar():
        nonlocal ballena, columnas, tiempo_spawn, score, estado
        ballena = Ballena(ANCHO * 0.35, ALTO * 0.45, whale_frames, anim_fps=WHALE_ANIM_FPS)
        columnas = []
        tiempo_spawn = 0
        estado = READY

    def crear_burbujas():
        for _ in range(random.randint(3, 5)):
            r = random.randint(3, 7)
            burbujas.append({
                "x": ballena.rect.left - random.randint(0, 8),
                "y": ballena.rect.centery + random.randint(-8, 8),
                "r": r,
                "vy": -random.uniform(20, 50),
                "vx": -random.uniform(10, 30),
                "a": 180
            })

    def actualizar_burbujas(dt):
        for b in burbujas:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["a"] -= 80 * dt
        burbujas[:] = [b for b in burbujas if b["a"] > 0 and b["y"] > -10]

    def dibujar_burbujas():
        for b in burbujas:
            s = pygame.Surface((b["r"]*2, b["r"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (230, 240, 255, int(b["a"])), (b["r"], b["r"]), b["r"], width=1)
            screen.blit(s, (b["x"]-b["r"], b["y"]-b["r"]))

    # Loop principal
    corriendo = True
    while corriendo:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                corriendo = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_UP):
                    if estado == READY:
                        score = 0
                        columnas.clear()
                        tiempo_spawn = SPAWN_MS
                        estado = JUGANDO
                        if snd_flap: snd_flap.play()
                        ballena.flap()
                        crear_burbujas()
                    elif estado == JUGANDO:
                        if snd_flap: snd_flap.play()
                        ballena.flap()
                        crear_burbujas()
                    elif estado == GAMEOVER:
                        reiniciar()
                if e.key == pygame.K_r and estado == GAMEOVER:
                    reiniciar()
                if e.key == pygame.K_ESCAPE:
                    corriendo = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if estado == READY:
                    score = 0
                    columnas.clear()
                    tiempo_spawn = SPAWN_MS
                    estado = JUGANDO
                    if snd_flap: snd_flap.play()
                    ballena.flap()
                    crear_burbujas()
                elif estado == JUGANDO:
                    if snd_flap: snd_flap.play()
                    ballena.flap()
                    crear_burbujas()
                elif estado == GAMEOVER:
                    reiniciar()

        bg_off += VEL_SCROLL_BG * dt
        floor_off += VEL_SCROLL_SUELO * dt

        if estado == READY:
            ballena.y += math.sin(pygame.time.get_ticks() * 0.005) * 0.4
            ballena.rect.center = (ballena.x, ballena.y)
            actualizar_burbujas(dt)

        if estado == JUGANDO:
            ballena.update(dt)
            ballena.y = clamp(ballena.y, BORDE_SUPERIOR + 10, ALTO - ALTURA_SUELO - 10)
            ballena.rect.center = (ballena.x, ballena.y)
            actualizar_burbujas(dt)

            
            tiempo_spawn += dt * 1000.0
            if tiempo_spawn >= SPAWN_MS:
                tiempo_spawn = 0.0
                gap = max(GAP_MIN, GAP_INICIAL - int(score * 2.5))
                min_y = 140
                max_y = ALTO - ALTURA_SUELO - 140
                gap_y = random.randint(min_y, max_y)
                columnas.append(ColumnaBasura(ANCHO + 40, gap_y, gap, trash_tex))

            for col in columnas:
                col.update(dt)
                if not col.scored and col.rect_top.centerx < ballena.rect.centerx:
                    col.scored = True
                    score += 1
                    if snd_score: snd_score.play()

            
            columnas[:] = [c for c in columnas if not c.fuera_de_pantalla()]

            
            if ballena.rect.bottom >= ALTO - ALTURA_SUELO or ballena.rect.top <= BORDE_SUPERIOR:
                if snd_hit: snd_hit.play()
                highscore = max(highscore, score)
                estado = GAMEOVER

            
            mask_ballena = ballena.get_mask()
            for col in columnas:
                if _collide_mask(ballena, mask_ballena, col.superior, col.rect_top) or \
                   _collide_mask(ballena, mask_ballena, col.inferior, col.rect_bottom):
                    if snd_hit: snd_hit.play()
                    highscore = max(highscore, score)
                    estado = GAMEOVER
                    break

         
        dibujar_fondo(screen, bg_img, bg_off)
        for c in columnas:
            c.draw(screen)
        dibujar_burbujas()
        dibujar_suelo(screen, floor_img, floor_off)
        ballena.draw(screen)

        # UI
        if estado == READY:
            texto(screen, "Flappy Whale", 44, ALTO//2 - 80, bold=True)
            texto(screen, "Pulsa ESPACIO o clic para nadar", 22, ALTO//2 - 28)
            texto(screen, "Esquiva la basura", 22, ALTO//2 + 2)
        elif estado == JUGANDO:
            texto(screen, f"{score}", 52, 80, bold=True)
        else:  # GAMEOVER
            texto(screen, "¡Game Over!", 46, ALTO//2 - 80, bold=True)
            texto(screen, f"Puntaje: {score}", 28, ALTO//2 - 20)
            texto(screen, f"Mejor: {highscore}", 22, ALTO//2 + 10)
            texto(screen, "R para reiniciar", 20, ALTO//2 + 50)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
