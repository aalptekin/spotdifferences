import pygame
import json
import os
import time
import math
import datetime
import sys
import random

pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
pygame.display.set_caption("Find the Differences")
font = pygame.font.SysFont(None, 36)
large_font = pygame.font.SysFont(None, 72)

# Background colours — change these to restyle all screens at once
BG_DARK = (0, 0, 0)        # menus, name entry, hall of fame
BG_GAME = (176, 214, 185)  # gameplay screen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CATEGORY_IMAGES = {
    "Doğa": os.path.join(BASE_DIR, "categorynature.jpg"),
    "Film": os.path.join(BASE_DIR, "categorymovies.jpg")
    # "Puzzle": os.path.join(BASE_DIR, "categorypuzzle.jpg")
}
CATEGORY_JSONS = {
    "Doğa": os.path.join(BASE_DIR, "gameData_nature.json"),
    "Film": os.path.join(BASE_DIR, "gameData_movies.json")
    # "Puzzle": os.path.join(BASE_DIR, "gameData_puzzle.json")
}
CATEGORY_PATHS = {
    "Doğa": os.path.join(BASE_DIR, "pictures/nature/"),
    "Film": os.path.join(BASE_DIR, "pictures/movies/")
    # "Puzzle": os.path.join(BASE_DIR, "pictures/puzzle/")
}

CORPORATE_IMAGE  = os.path.join(BASE_DIR, "corporateintro.jpg")
CORPORATE_PATH   = os.path.join(BASE_DIR, "pictures/corporate/")
CORPORATE_COLS   = 3    # thumbnail grid columns
CORPORATE_ROWS   = 5    # thumbnail grid rows per page
SWIPE_THRESHOLD  = 60   # pixels finger must travel to count as a swipe

def show_text_centered(text, font, color, surface, y):
    render = font.render(text, True, color)
    rect = render.get_rect(center=(surface.get_width() // 2, y))
    surface.blit(render, rect)

def scale_image_to_fit(img, max_width, max_height):
    img_width, img_height = img.get_size()
    scale = min(max_width / img_width, max_height / img_height)
    new_size = (int(img_width * scale), int(img_height * scale))
    return pygame.transform.scale(img, new_size), scale

CLUE_PENALTY = 0          # seconds deducted from timer per clue
CLUE_HIGHLIGHT_DURATION = 2.0  # seconds the clue circle stays visible

def draw_clue_button(surface, rect, clues_left):
    """Draw a styled lightbulb clue button using only pygame primitives."""
    active   = clues_left > 0
    cx, cy   = rect.centerx, rect.centery

    # ---- drop shadow ----
    shadow_rect = rect.move(3, 3)
    pygame.draw.rect(surface, (40, 40, 40), shadow_rect, border_radius=14)

    # ---- button body gradient simulation (two-tone) ----
    top_color = (250, 229, 67) if active else (160, 160, 160)
    bot_color = (87, 78, 60)  if active else (100, 100, 100)
    top_half  = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 2)
    bot_half  = pygame.Rect(rect.x, rect.centery, rect.width, rect.height - rect.height // 2)
    pygame.draw.rect(surface, top_color, top_half, border_radius=14)
    pygame.draw.rect(surface, bot_color, bot_half, border_radius=14)
    pygame.draw.rect(surface, top_color, rect, border_radius=14)
    # Draw dark overlay on a full-button surface so the rounded mask clips it correctly
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(overlay, (0, 0, 0, 0), pygame.Rect(0, 0, rect.width, rect.height), border_radius=14)
    pygame.draw.rect(overlay, (0, 0, 0, 55),
                     pygame.Rect(0, rect.height // 2, rect.width, rect.height - rect.height // 2),
                     border_radius=14)
    # Clip the overlay to the rounded button shape
    mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, rect.width, rect.height), border_radius=14)
    overlay.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(overlay, (rect.x, rect.y))

    # ---- outer border ----
    border_col = (180, 100, 0) if active else (70, 70, 70)
    pygame.draw.rect(surface, border_col, rect, 2, border_radius=14)

    # ---- draw lightbulb icon (pure shapes) ----
    bx = rect.x + int(rect.width * 0.28)
    by = cy
    br = int(rect.height * 0.30)
    bulb_col  = (255, 255, 180) if active else (210, 210, 210)
    shine_col = (255, 255, 255) if active else (230, 230, 230)
    base_col  = (160, 100, 0)   if active else (90, 90, 90)

    # main bulb circle
    pygame.draw.circle(surface, bulb_col, (bx, by), br)
    # shine highlight
    pygame.draw.circle(surface, shine_col, (bx - br//3, by - br//3), max(2, br//3))
    # bulb base stripes
    base_w = int(br * 1.0)
    base_h = max(3, int(br * 0.35))
    base_rect = pygame.Rect(bx - base_w//2, by + br - 1, base_w, base_h)
    pygame.draw.rect(surface, base_col, base_rect)
    cap_rect = pygame.Rect(bx - base_w//2 + 2, by + br + base_h - 1, base_w - 4, base_h)
    pygame.draw.rect(surface, base_col, cap_rect)
    # bulb outline
    pygame.draw.circle(surface, border_col, (bx, by), br, 1)

    # ---- count label ----
    count_font = pygame.font.SysFont(None, int(rect.height * 0.62))
    txt_col    = (80, 40, 0) if active else (60, 60, 60)
    label      = count_font.render(str(clues_left), True, txt_col)
    label_rect = label.get_rect(center=(rect.x + int(rect.width * 0.72), cy))
    surface.blit(label, label_rect)

def load_valid_ads():
    # Load ad entries from ads/ads.json, skipping any with missing image files.
    ads_json = os.path.join(BASE_DIR, "ads", "ads.json")
    if not os.path.exists(ads_json):
        return []
    try:
        with open(ads_json, "r") as f:
            entries = json.load(f)
    except Exception:
        return []
    valid = []
    for ad in entries:
        img_path = os.path.join(BASE_DIR, "ads", ad.get("image", ""))
        if os.path.exists(img_path) and ad.get("duration", 0) > 0:
            valid.append(ad)
    return valid

def run_ad_loop():
    ads = load_valid_ads()
    if not ads:
        return

    # Flush any pending input before ads start
    pygame.event.clear()

    # HARD LOCK: only allow QUIT events during ads
    pygame.event.set_allowed([pygame.QUIT])

    # Optional: grab input focus (helps on some kiosk/touch setups)
    pygame.event.set_grab(True)

    try:
        clock = pygame.time.Clock()

        for ad in ads:
            try:
                img_path = os.path.join(BASE_DIR, "ads", ad["image"])
                ad_image = pygame.image.load(img_path)
                ad_image = pygame.transform.scale(ad_image, screen.get_size())
                duration = max(1, int(ad["duration"]))
            except Exception:
                continue

            start_time = time.time()
            while time.time() - start_time < duration:
                # Keep internal event system alive without delivering input events
                pygame.event.pump()

                # Only QUIT is allowed, handle it
                for event in pygame.event.get([pygame.QUIT]):
                    pygame.quit()
                    sys.exit()

                screen.blit(ad_image, (0, 0))
                pygame.display.flip()
                clock.tick(60)

    finally:
        # Restore event handling after ads
        pygame.event.set_grab(False)
        pygame.event.set_allowed(None)   # allow all events again
        pygame.event.clear()             # clear any queued touch/click that happened during ads

def show_corporate_gallery():
    """
    Two-mode corporate viewer:
      - Thumbnail grid  : CORPORATE_COLS x CORPORATE_ROWS, with margins, paginated.
      - Full-screen view: swipe left/right to browse; tap image to return to grid.
    """
    sw, sh = screen.get_size()

    # ── collect image files ───────────────────────────────────────────────────
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
    if not os.path.isdir(CORPORATE_PATH):
        return
    files = sorted([
        os.path.join(CORPORATE_PATH, f)
        for f in os.listdir(CORPORATE_PATH)
        if os.path.splitext(f)[1].lower() in exts
    ])
    if not files:
        return

    per_page   = CORPORATE_COLS * CORPORATE_ROWS
    thumb_cache = {}   # path -> thumbnail Surface
    full_cache  = {}   # path -> full-size Surface

    def load_thumb(path):
        if path not in thumb_cache:
            try:
                img = pygame.image.load(path).convert()
                img, _ = scale_image_to_fit(img, thumb_w, thumb_h)
                thumb_cache[path] = img
            except Exception:
                s = pygame.Surface((thumb_w, thumb_h))
                s.fill((60, 60, 60))
                thumb_cache[path] = s
        return thumb_cache[path]

    def load_full(path):
        if path not in full_cache:
            try:
                img = pygame.image.load(path).convert()
                img, _ = scale_image_to_fit(img, sw, sh)
                full_cache[path] = img
            except Exception:
                s = pygame.Surface((sw, sh))
                s.fill((30, 30, 30))
                full_cache[path] = s
        return full_cache[path]

    # ── layout calculations ───────────────────────────────────────────────────
    margin     = 20
    thumb_w    = (sw - margin * (CORPORATE_COLS + 1)) // CORPORATE_COLS
    thumb_h    = (sh - margin * (CORPORATE_ROWS + 1)) // CORPORATE_ROWS

    def thumb_rect(idx_in_page):
        col = idx_in_page % CORPORATE_COLS
        row = idx_in_page // CORPORATE_COLS
        x   = margin + col * (thumb_w + margin)
        y   = margin + row * (thumb_h + margin)
        return pygame.Rect(x, y, thumb_w, thumb_h)

    # Close button geometry (top-right corner)
    close_size = 44
    close_btn  = pygame.Rect(sw - close_size - 12, 12, close_size, close_size)

    def draw_close_btn():
        """Draw a red circular X button."""
        pygame.draw.circle(screen, (200, 40, 40), close_btn.center, close_size // 2)
        pygame.draw.circle(screen, (255, 80, 80), close_btn.center, close_size // 2, 2)
        x_font = pygame.font.SysFont(None, int(close_size * 1.1), bold=True)
        x_lbl  = x_font.render("X", True, (255, 255, 255))
        screen.blit(x_lbl, x_lbl.get_rect(center=close_btn.center))

    def draw_grid(page):
        screen.fill(BG_DARK)
        start = page * per_page
        rects = []
        for i in range(per_page):
            fi = start + i
            if fi >= len(files):
                break
            r = thumb_rect(i)
            thumb = load_thumb(files[fi])
            # centre thumbnail inside its cell
            tx = r.x + (thumb_w - thumb.get_width())  // 2
            ty = r.y + (thumb_h - thumb.get_height()) // 2
            pygame.draw.rect(screen, (40, 40, 40), r, border_radius=6)
            screen.blit(thumb, (tx, ty))
            pygame.draw.rect(screen, (100, 100, 100), r, 1, border_radius=6)
            rects.append((r, fi))
        # page indicator
        total_pages = max(1, (len(files) + per_page - 1) // per_page)
        pager = font.render(f"{page + 1} / {total_pages}", True, (180, 180, 180))
        screen.blit(pager, pager.get_rect(bottomright=(sw - margin, sh - 8)))
        draw_close_btn()
        pygame.display.flip()
        return rects

    def draw_fullscreen(idx):
        screen.fill((0, 0, 0))
        img = load_full(files[idx])
        screen.blit(img, img.get_rect(center=(sw // 2, sh // 2)))
        # subtle counter
        counter = font.render(f"{idx + 1} / {len(files)}", True, (200, 200, 200))
        screen.blit(counter, (12, 10))
        pygame.display.flip()

    # ── state machine ─────────────────────────────────────────────────────────
    mode       = "grid"   # "grid" | "full"
    page       = 0
    full_idx   = 0
    rects      = draw_grid(page)

    swipe_start_x = None   # track finger/mouse start for swipe detection

    while True:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ── KEYBOARD shortcuts ────────────────────────────────────────────
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return                          # back to start screen
                if mode == "full":
                    if event.key == pygame.K_LEFT and full_idx > 0:
                        full_idx -= 1; draw_fullscreen(full_idx)
                    elif event.key == pygame.K_RIGHT and full_idx < len(files) - 1:
                        full_idx += 1; draw_fullscreen(full_idx)
                    elif event.key == pygame.K_RETURN:
                        mode = "grid"; rects = draw_grid(page)

            # ── MOUSE / TOUCH: button-down records swipe origin ───────────────
            elif event.type == pygame.MOUSEBUTTONDOWN:
                swipe_start_x = event.pos[0]

            elif event.type == pygame.MOUSEBUTTONUP:
                if swipe_start_x is None:
                    continue
                dx = event.pos[0] - swipe_start_x
                swipe_start_x = None

                if mode == "grid":
                    if abs(dx) >= SWIPE_THRESHOLD:
                        # swipe in grid = page flip
                        total_pages = (len(files) + per_page - 1) // per_page
                        if dx < 0 and page < total_pages - 1:
                            page += 1; rects = draw_grid(page)
                        elif dx > 0 and page > 0:
                            page -= 1; rects = draw_grid(page)
                    else:
                        # tap close button = back to home
                        mx, my = event.pos
                        if close_btn.collidepoint(mx, my):
                            return
                        # tap = open thumbnail
                        for r, fi in rects:
                            if r.collidepoint(mx, my):
                                full_idx = fi
                                mode     = "full"
                                draw_fullscreen(full_idx)
                                break

                elif mode == "full":
                    if abs(dx) >= SWIPE_THRESHOLD:
                        # swipe in full = previous / next image
                        if dx < 0 and full_idx < len(files) - 1:
                            full_idx += 1
                        elif dx > 0 and full_idx > 0:
                            full_idx -= 1
                        draw_fullscreen(full_idx)
                    else:
                        # tap image = back to grid
                        # make sure we show the right page
                        page  = full_idx // per_page
                        mode  = "grid"
                        rects = draw_grid(page)

            # ── FINGER events (touch screens) ─────────────────────────────────
            elif hasattr(pygame, "FINGERDOWN") and event.type == pygame.FINGERDOWN:
                swipe_start_x = int(event.x * sw)

            elif hasattr(pygame, "FINGERUP") and event.type == pygame.FINGERUP:
                if swipe_start_x is None:
                    continue
                finger_x = int(event.x * sw)
                finger_y = int(event.y * sh)
                dx = finger_x - swipe_start_x
                swipe_start_x = None

                if mode == "grid":
                    if abs(dx) >= SWIPE_THRESHOLD:
                        total_pages = (len(files) + per_page - 1) // per_page
                        if dx < 0 and page < total_pages - 1:
                            page += 1; rects = draw_grid(page)
                        elif dx > 0 and page > 0:
                            page -= 1; rects = draw_grid(page)
                    else:
                        if close_btn.collidepoint(finger_x, finger_y):
                            return
                        for r, fi in rects:
                            if r.collidepoint(finger_x, finger_y):
                                full_idx = fi
                                mode     = "full"
                                draw_fullscreen(full_idx)
                                break
                elif mode == "full":
                    if abs(dx) >= SWIPE_THRESHOLD:
                        if dx < 0 and full_idx < len(files) - 1:
                            full_idx += 1
                        elif dx > 0 and full_idx > 0:
                            full_idx -= 1
                        draw_fullscreen(full_idx)
                    else:
                        page  = full_idx // per_page
                        mode  = "grid"
                        rects = draw_grid(page)


def show_start_screen():
    categories  = list(CATEGORY_IMAGES.keys())
    sw, sh      = screen.get_size()
    spacing     = 50

    # ── layout: category images fill the top ~72% of the screen ──────────────
    cat_area_h  = int(sh * 0.72)
    img_width   = (sw - (len(categories) + 1) * spacing) // len(categories)
    img_height  = int(img_width * 9 / 16)
    cat_y       = (cat_area_h - img_height) // 2   # vertically centred in top area

    # ── corporate banner: bottom strip ───────────────────────────────────────
    corp_margin = spacing
    corp_h      = sh - cat_area_h - corp_margin * 2
    corp_w      = sw - corp_margin * 2
    corp_rect   = pygame.Rect(corp_margin, cat_area_h + corp_margin, corp_w, corp_h)

    def draw_categories():
        screen.fill(BG_DARK)
        rects_local = []

        # category boxes
        for i, cat in enumerate(categories):
            x = spacing + i * (img_width + spacing)
            img = pygame.image.load(CATEGORY_IMAGES[cat])
            img = pygame.transform.scale(img, (img_width, img_height))
            screen.blit(img, (x, cat_y))
            txt = font.render(cat, True, (255, 255, 255))
            txt_rect = txt.get_rect(center=(x + img_width // 2, cat_y + img_height + 22))
            screen.blit(txt, txt_rect)
            rects_local.append((pygame.Rect(x, cat_y, img_width, img_height), cat))

        # corporate banner
        if os.path.exists(CORPORATE_IMAGE):
            corp_img = pygame.image.load(CORPORATE_IMAGE)
            corp_img = pygame.transform.scale(corp_img, (corp_w, corp_h))
            screen.blit(corp_img, corp_rect.topleft)
        else:
            pygame.draw.rect(screen, (40, 40, 40), corp_rect, border_radius=10)
            show_text_centered("Corporate", font, (200, 200, 200), screen, corp_rect.centery)
        pygame.draw.rect(screen, (120, 120, 120), corp_rect, 2, border_radius=10)

        pygame.display.flip()
        return rects_local

    rects      = draw_categories()
    idle_start = time.time()

    while True:
        if time.time() - idle_start > 30:
            run_ad_loop()
            rects = draw_categories()
            idle_start = time.time()
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                # corporate banner tapped?
                if corp_rect.collidepoint(mx, my):
                    show_corporate_gallery()
                    rects = draw_categories()   # redraw on return
                    idle_start = time.time()
                    continue

                for rect, cat in rects:
                    if rect.collidepoint(mx, my):
                        return cat

            elif event.type in [pygame.KEYDOWN, pygame.MOUSEMOTION]:
                idle_start = time.time()

            # Touch events support
            if hasattr(pygame, "FINGERDOWN") and event.type == pygame.FINGERDOWN:
                mx = int(event.x * sw)
                my = int(event.y * sh)

                if corp_rect.collidepoint(mx, my):
                    show_corporate_gallery()
                    rects = draw_categories()
                    idle_start = time.time()
                    continue

                for rect, cat in rects:
                    if rect.collidepoint(mx, my):
                        return cat


def get_player_name():
    name = ""
    active = True
    input_font = pygame.font.SysFont(None, 48)
    prompt = "Adınızı yazın:"
    key_font = pygame.font.SysFont(None, 36)

    # Extended keyboard layout including numbers
    keys = [
        list("1234567890"),
        list("QWERTYUIOP"),
        list("ASDFGHJKL"),
        list("ZXCVBNM"),
        ["__", "Sil", "Giriş"]
    ]

    key_rects = []

    def draw_keyboard():
        key_rects.clear()
        key_width = 80
        key_height = 60
        spacing = 10
        start_y = screen.get_height() // 2 + 20

        for row_idx, row in enumerate(keys):
            row_width = sum([key_width + spacing for _ in row]) - spacing
            start_x = (screen.get_width() - row_width) // 2
            for col_idx, key in enumerate(row):
                rect = pygame.Rect(start_x + col_idx * (key_width + spacing),
                                   start_y + row_idx * (key_height + spacing),
                                   key_width, key_height)
                key_rects.append((rect, key))
                pygame.draw.rect(screen, (100, 100, 100), rect, border_radius=6)
                label = key_font.render(" " if key == "__" else key, True, (255, 255, 255))
                label_rect = label.get_rect(center=rect.center)
                screen.blit(label, label_rect)

    while active:
        screen.fill(BG_DARK)
        show_text_centered(prompt, font, (255, 255, 255), screen, 80)
        show_text_centered(name + "_", input_font, (0, 255, 0), screen, 150)
        draw_keyboard()
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip() != "":
                    active = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode.isprintable() and len(name) < 20:
                    name += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for rect, key in key_rects:
                    if rect.collidepoint(mx, my):
                        if key == "__":
                            name += " "
                        elif key == "Sil":
                            name = name[:-1]
                        elif key == "Giriş":
                            if name.strip():
                                active = False
                        else:
                            if len(name) < 20:
                                name += key

    return name.strip()


def save_to_hall_of_fame(name, score):
    entry = {
        "name": name,
        "score": score
    }

    try:
        if os.path.exists("hall_of_fame.json"):
            with open("hall_of_fame.json", "r") as f:
                hall = json.load(f)
        else:
            hall = []
    except:
        hall = []

    hall.append(entry)
    hall = sorted(hall, key=lambda x: x["score"], reverse=True)[:10]  # keep top 10

    with open("hall_of_fame.json", "w") as f:
        json.dump(hall, f, indent=2)

def display_hall_of_fame():
    try:
        with open("hall_of_fame.json", "r") as f:
            hall = json.load(f)
    except:
        hall = []

    screen.fill(BG_DARK)
    show_text_centered("En İyiler", large_font, (255, 215, 0), screen, 80)
    if not hall:
        show_text_centered("Henüz puan yok.", font, (255, 255, 255), screen, 160)
    else:
        for i, entry in enumerate(hall):
            text = f"{i + 1}. {entry['name']} - {entry['score']} pts"
            show_text_centered(text, font, (255, 255, 255), screen, 160 + i * 40)

    show_text_centered("Bir tuşa basın", font, (180, 180, 180), screen, screen.get_height() - 60)
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.QUIT]:
                return

def run_game(game_data, asset_path):
    level = 0
    score = 0
    total_levels = len(game_data)

    while level < total_levels:
        data = game_data[level]
        original = pygame.image.load(os.path.join(asset_path, data["original"]))
        modified = pygame.image.load(os.path.join(asset_path, data["modified"]))
        diffs = data["differences"]
        found = []
        max_width = screen.get_width() // 2 - 60
        max_height = screen.get_height() - 100
        orig_img, scale = scale_image_to_fit(original, max_width, max_height)
        mod_img, _ = scale_image_to_fit(modified, max_width, max_height)

        time_limit = max(10, 60 - (level // 5) * 10)
        time_left = time_limit
        start_time = time.time()
        score += 10
        running = True

        # Clue state
        clues_left = 3
        # Wrong-click flash state
        wrong_flash_until = 0.0   # timestamp; shows X overlay while time.time() < this
        clue_highlight_idx = None   # index of diff currently being highlighted
        clue_highlight_until = 0.0  # timestamp when highlight expires
        CLUE_BTN_W, CLUE_BTN_H = 90, 46
        clue_btn_rect = pygame.Rect(
            screen.get_width() - CLUE_BTN_W - 20, 8,
            CLUE_BTN_W, CLUE_BTN_H
        )

        while running:
            elapsed = time.time() - start_time
            remaining = max(0, int(time_left - elapsed))
            screen.fill(BG_GAME)
            margin = 30
            top = 80
            screen.blit(orig_img, (margin, top))
            screen.blit(mod_img, (screen.get_width() // 2 + margin, top))

            for i in found:
                cx = diffs[i]["x"] * scale
                cy = diffs[i]["y"] * scale + top
                r = int(diffs[i]["radius"] * scale)
                pygame.draw.circle(screen, (255, 0, 0), (int(cx + margin), int(cy)), r, 2)
                pygame.draw.circle(screen, (255, 0, 0), (int(cx + screen.get_width() // 2 + margin), int(cy)), r, 2)

            timer_color = (255, 0, 0) if remaining < 10 and int(time.time() * 2) % 2 == 0 else (0, 0, 0)
            remaining_diffs = max(0, 7 - len(found))
            status_text = f"Level {level + 1} - Süre: {remaining}s -  fark: {remaining_diffs} "
            show_text_centered(status_text, font, timer_color, screen, 30)
            show_text_centered(f"Puan: {score}", font, (0, 0, 0), screen, 60)

            # Draw clue button
            draw_clue_button(screen, clue_btn_rect, clues_left)

            # Draw active clue highlight (flashing yellow ring)
            if clue_highlight_idx is not None and time.time() < clue_highlight_until:
                d = diffs[clue_highlight_idx]
                cx = d["x"] * scale
                cy = d["y"] * scale + top
                r = int(d["radius"] * scale) + 8
                if int(time.time() * 4) % 2 == 0:  # flash at 4Hz
                    pygame.draw.circle(screen, (255, 220, 0), (int(cx + margin), int(cy)), r, 4)
                    pygame.draw.circle(screen, (255, 220, 0),
                                       (int(cx + screen.get_width() // 2 + margin), int(cy)), r, 4)
            elif clue_highlight_idx is not None and time.time() >= clue_highlight_until:
                clue_highlight_idx = None  # expire highlight
            if remaining <= 0:
                show_text_centered("Süre Bitti", large_font, (255, 0, 0), screen, screen.get_height() // 2)
                pygame.display.flip()
                pygame.time.wait(3000)
                player_name = get_player_name()
                save_to_hall_of_fame(player_name, score)
                display_hall_of_fame()
                return

            if len(found) == 7:
                # Redraw the full scene with ALL 7 circles (including the last one just found)
                # so the player can see it before the level ends.
                seconds_taken = int(time.time() - start_time)
                screen.fill(BG_GAME)
                screen.blit(orig_img, (margin, top))
                screen.blit(mod_img, (screen.get_width() // 2 + margin, top))
                for i in found:
                    cx = diffs[i]["x"] * scale
                    cy = diffs[i]["y"] * scale + top
                    r = int(diffs[i]["radius"] * scale)
                    pygame.draw.circle(screen, (255, 0, 0), (int(cx + margin), int(cy)), r, 2)
                    pygame.draw.circle(screen, (255, 0, 0), (int(cx + screen.get_width() // 2 + margin), int(cy)), r, 2)
                show_text_centered("Tebrikler! Hepsini buldunuz!", font, (30, 144, 255), screen, 30)
                show_text_centered(f"Puan: {score}", font, (0, 0, 0), screen, 60)
                # Display elapsed time in top-left corner
                time_font = pygame.font.SysFont(None, 42, bold=True)
                time_label = time_font.render(f" {seconds_taken} sn.", True, (30, 144, 255))
                screen.blit(time_label, (12, 10))
                pygame.display.flip()

                # Play success sound
                success_path = os.path.join(BASE_DIR, "nextlevel.mp3")
                if os.path.exists(success_path):
                    pygame.mixer.Sound(success_path).play()

                score += remaining * 5
                level += 1
                pygame.time.wait(1500)  # Pause so player sees all circles

                # Display level-specific ad before next level
                ad_filename = f"ad{level}.png"  # ad1.png, ad2.png, ...
                ad_path = os.path.join(BASE_DIR, "ads", ad_filename)
                if os.path.exists(ad_path):
                    try:
                        ad_img = pygame.image.load(ad_path)
                        ad_img = pygame.transform.scale(ad_img, screen.get_size())

                        # Block all input during ad except QUIT
                        pygame.event.clear()
                        pygame.event.set_allowed([pygame.QUIT])
                        pygame.event.set_grab(True)

                        start_time_ad = time.time()
                        while time.time() - start_time_ad < 5:
                            pygame.event.pump()
                            for event in pygame.event.get([pygame.QUIT]):
                                pygame.quit()
                                sys.exit()
                            screen.blit(ad_img, (0, 0))
                            pygame.display.flip()
                            pygame.time.Clock().tick(60)

                    except:
                        pass
                    finally:
                        # Always restore normal input after ad
                        pygame.event.set_grab(False)
                        pygame.event.set_allowed(None)
                        pygame.event.clear()

                break  # proceed to next level

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()

                    # --- Clue button ---
                    if clue_btn_rect.collidepoint(mx, my):
                        if clues_left > 0:
                            unfound = [i for i in range(len(diffs)) if i not in found]
                            if unfound:
                                clues_left -= 1
                                clue_highlight_idx = random.choice(unfound)
                                clue_highlight_until = time.time() + CLUE_HIGHLIGHT_DURATION
                                start_time -= CLUE_PENALTY  # time penalty
                        continue  # don't process as a diff click
                    rel_x = rel_y = -1
                    if margin <= mx <= margin + orig_img.get_width():
                        rel_x = mx - margin
                    elif screen.get_width() // 2 + margin <= mx <= screen.get_width():
                        rel_x = mx - (screen.get_width() // 2 + margin)
                    rel_y = my - top
                    if rel_x < 0 or rel_y < 0:
                        continue
                    click_x = rel_x / scale
                    click_y = rel_y / scale
                    correct = False
                    for i, d in enumerate(diffs):
                        dx, dy = click_x - d["x"], click_y - d["y"]
                        if math.sqrt(dx * dx + dy * dy) <= d["radius"]:
                            if i not in found:
                                found.append(i)
                                correct = True
                    if not correct:
                        # Play wrong click sound
                        wrong_path = os.path.join(BASE_DIR, "wrong.mp3")
                        if os.path.exists(wrong_path):
                            pygame.mixer.Sound(wrong_path).play()
                        start_time -= 10
                        wrong_flash_until = time.time() + 0.5  # show X for 0.5 seconds
            # ── Wrong-click X flash overlay ──────────────────────────────────
            if time.time() < wrong_flash_until:
                x_size  = screen.get_height() // 3
                x_font  = pygame.font.SysFont(None, x_size, bold=False)
                x_surf  = x_font.render("-10 sn.", True, (220, 0, 0))
                x_rect  = x_surf.get_rect(center=(screen.get_width() // 2,
                                                   screen.get_height() // 2))
                # semi-transparent dark background behind the X
                bg_surf = pygame.Surface(x_surf.get_size(), pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 90))
                screen.blit(bg_surf, x_rect)
                screen.blit(x_surf, x_rect)

            pygame.display.flip()
            pygame.time.Clock().tick(60)

    show_text_centered("TEBRiKLER. OYUNU BiTiRDiNiZ.", large_font, (255, 0, 0), screen, screen.get_height() // 2)
    pygame.display.flip()
    pygame.time.wait(3000)
    player_name = get_player_name()
    save_to_hall_of_fame(player_name, score)
    display_hall_of_fame()



def main_loop():
    while True:
        selected_cat = show_start_screen()
        json_file = CATEGORY_JSONS[selected_cat]
        asset_folder = CATEGORY_PATHS[selected_cat]
        with open(json_file) as f:
            game_data = json.load(f)["games"]
            random.shuffle(game_data)  # Shuffle levels per session
        run_game(game_data, asset_folder)

# --- Entry Point ---
if __name__ == "__main__":
    main_loop()
    pygame.quit()