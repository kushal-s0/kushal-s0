from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import random
import config
import animation_engine

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "assets" / config.PORTRAIT_FILE
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_OUTPUT = DATA_DIR / "portrait_processed.png"
MASK_OUTPUT = DATA_DIR / "portrait_mask.png"
DITHER_OUTPUT = DATA_DIR / "portrait_dither.png"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Settings
OUTPUT_SIZE = (420, 520)
DOT_RADIUS = 0.9
DOT_SPACING = 2

def load_image():
    if not INPUT.exists():
        raise FileNotFoundError(f"Portrait not found: {INPUT}")
    image = cv2.imread(str(INPUT), cv2.IMREAD_COLOR)
    return image

def crop_portrait(image):
    height, width = image.shape[:2]
    top = max(0, int(height * 0.015))
    return image[top:height, :]

def create_subject_mask(image):
    import mediapipe as mp
    mp_selfie_segmentation = mp.solutions.selfie_segmentation
    with mp_selfie_segmentation.SelfieSegmentation(model_selection=0) as selfie_segmentation:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = selfie_segmentation.process(image_rgb)
        subject_mask = (results.segmentation_mask > 0.4).astype(np.uint8) * 255
    subject_mask = cv2.GaussianBlur(subject_mask, (5, 5), 0)
    return subject_mask

def process_and_dither(image, mask):
    target_width, target_height = OUTPUT_SIZE
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    resized_image = cv2.resize(image_rgb, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)
    resized_mask = cv2.resize(mask, (target_width, target_height), interpolation=cv2.INTER_AREA)

    pil_img = Image.fromarray(resized_image)
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(1.4)
    enhancer = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer.enhance(1.1)

    gray_pil = pil_img.convert('L')
    gray = np.array(gray_pil)

    gray_masked = np.full_like(gray, 255)
    foreground = resized_mask > 20
    gray_masked[foreground] = gray[foreground]

    # Quick dithering logic
    img_d = gray_masked.astype(np.float32).copy()
    h, w = img_d.shape
    DITHER_THRESHOLD = 110

    for y in range(h):
        for x in range(w):
            old_pixel = img_d[y, x]
            new_pixel = 0.0 if old_pixel < DITHER_THRESHOLD else 255.0
            img_d[y, x] = new_pixel
            error = old_pixel - new_pixel
            
            if x + 1 < w: img_d[y, x + 1] += error * 7 / 16
            if y + 1 < h and x > 0: img_d[y + 1, x - 1] += error * 3 / 16
            if y + 1 < h: img_d[y + 1, x] += error * 5 / 16
            if y + 1 < h and x + 1 < w: img_d[y + 1, x + 1] += error * 1 / 16

    dither_res = np.where(img_d < 128, 0, 255).astype(np.uint8)
    return dither_res, resized_mask

def generate_dots(dither, mask):
    height, width = dither.shape
    pts = []
    for y in range(0, height, DOT_SPACING):
        for x in range(0, width, DOT_SPACING):
            if mask[y, x] < 80: continue
            if dither[y, x] >= 128: continue
            pts.append([x, y])
    return np.array(pts, dtype=np.float32), width, height

def build_banner(portrait_pts, portrait_width, portrait_height, theme="dark"):
    w = config.BANNER_WIDTH
    h = config.BANNER_HEIGHT
    
    # Theme configuration
    if theme == "dark":
        bg_color = "#070B16"
        frame_color = "#0A101F"
        frame_stroke = "rgba(34,211,238,0.35)"
        ui_light = "#22D3EE"
        text_primary = "#F8FAFC"
        text_secondary = "#CBD5E1"
        text_muted = "#94A3B8"
        portrait_grad_1 = "#22D3EE"
        portrait_grad_2 = "#A78BFA"
    else:
        bg_color = "#F8FAFC"
        frame_color = "#F1F5F9"
        frame_stroke = "rgba(15,23,42,0.15)"
        ui_light = "#0F172A"
        text_primary = "#0F172A"
        text_secondary = "#334155"
        text_muted = "#64748B"
        portrait_grad_1 = "#0F172A"
        portrait_grad_2 = "#334155"

    intro_groups = []
    shuffled_pts = portrait_pts.copy()
    np.random.shuffle(shuffled_pts)
    group_size = len(shuffled_pts) // 60
    for i in range(60):
        intro_groups.append(shuffled_pts[i*group_size:(i+1)*group_size])

    intro_svg = ""
    for i, grp in enumerate(intro_groups):
        delay = random.uniform(0, 2.0)
        dots = "".join([f'<circle cx="{x}" cy="{y}" r="{DOT_RADIUS:.2f}"/>' for x, y in grp])
        intro_svg += f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.5;0.99;1" dur="3.2s" begin="{delay}s" fill="freeze" />{dots}</g>'
        
    logo_center = (portrait_width / 2, portrait_height / 2)
    bands = animation_engine.compute_drift_bands(portrait_pts, logo_center, 94)
    loop_svg = ""
    for b in bands:
        dx, dy = b['dx'], b['dy']
        dots = "".join([f'<circle cx="{x}" cy="{y}" r="{DOT_RADIUS:.2f}"/>' for x, y in b['pts']])
        loop_svg += f'''
        <g opacity="0">
            <animate attributeName="opacity" values="1;1;0;0;0;0;0;0;1" keyTimes="0.000;0.194;0.288;0.432;0.525;0.669;0.763;0.906;1.000" dur="13.9s" begin="3.2s" repeatCount="indefinite"/>
            <animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f};0 0" keyTimes="0.000;0.194;0.288;0.432;0.525;0.669;0.763;0.906;1.000" dur="13.9s" begin="3.2s" repeatCount="indefinite"/>
            {dots}
        </g>'''

    def format_row(label, value, y_offset):
        dots = "." * max(2, (18 - len(label)))
        return f'''
        <text x="500" y="{y_offset}" class="mono label">{label} {dots}</text>
        <text x="680" y="{y_offset}" class="mono value" fill="{text_primary}">{value}</text>
        '''

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
    <defs>
        <linearGradient id="portraitGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{portrait_grad_1}" />
            <stop offset="100%" stop-color="{portrait_grad_2}" />
        </linearGradient>
        <filter id="glow8" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="txtGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&amp;family=Inter:wght@400;700&amp;display=swap');
            text {{ font-family: 'JetBrains Mono', monospace; }}
            .mono {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; }}
            .label {{ fill: {text_muted}; }}
            .value {{ font-weight: 700; }}
            .title {{ font-size: 13px; fill: {ui_light}; letter-spacing: 2px; filter: url(#txtGlow); }}
            .top-bar-text {{ font-size: 12px; fill: {text_muted}; }}
        </style>
    </defs>

    <rect x="0" y="0" width="{w}" height="{h}" fill="{bg_color}" />
    
    <!-- Outer Window Frame -->
    <rect x="2" y="2" width="{w-4}" height="{h-4}" rx="18" fill="none" stroke="{ui_light}" stroke-width="1.6" />
    <rect x="2" y="2" width="{w-4}" height="{h-4}" rx="18" fill="none" stroke="{ui_light}" stroke-width="3" opacity="0.3" filter="url(#glow8)" />
    
    <rect x="2" y="2" width="{w-4}" height="46" rx="18" fill="{frame_color}" />
    <line x1="2" y1="48" x2="{w-2}" y2="48" stroke="rgba(255,255,255,0.1)" />

    <circle cx="30" cy="25" r="5.5" fill="#FF5F56" />
    <circle cx="50" cy="25" r="5.5" fill="#FFBD2E" />
    <circle cx="70" cy="25" r="5.5" fill="#27C93F" />
    <text x="{w/2}" y="29" class="top-bar-text" text-anchor="middle">{config.EMAIL} - % ./profile.sh --live</text>

    <!-- Visual Map Portrait -->
    <text x="38" y="74" class="title" style="fill:#475569; filter:none; font-size:10px; letter-spacing:3px;">VISUAL.MAP</text>
    
    <rect x="36" y="84" width="{portrait_width + 10}" height="{portrait_height + 10}" rx="10" fill="none" stroke="{ui_light}" stroke-width="2" opacity="0.45" filter="url(#glow8)" />
    <rect x="36" y="84" width="{portrait_width + 10}" height="{portrait_height + 10}" rx="10" fill="{frame_color}" stroke="{frame_stroke}" />
    
    <path d="M 50 84 L 36 84 L 36 98" fill="none" stroke="{ui_light}" stroke-width="2" />
    <path d="M {36 + portrait_width - 4} 84 L {36 + portrait_width + 10} 84 L {36 + portrait_width + 10} 98" fill="none" stroke="{ui_light}" stroke-width="2" />
    <path d="M 50 {84 + portrait_height + 10} L 36 {84 + portrait_height + 10} L 36 {84 + portrait_height - 4}" fill="none" stroke="{ui_light}" stroke-width="2" />
    <path d="M {36 + portrait_width - 4} {84 + portrait_height + 10} L {36 + portrait_width + 10} {84 + portrait_height + 10} L {36 + portrait_width + 10} {84 + portrait_height - 4}" fill="none" stroke="{ui_light}" stroke-width="2" />

    <!-- Info Right Side -->
    <text x="500" y="106" class="title">SYSTEM.INFO</text>
    <line x1="596" y1="102" x2="1061" y2="102" stroke="rgba(255,255,255,0.1)" />
    <text x="1125" y="106" class="title" text-anchor="end" fill="#F87171">• LIVE</text>
    
    <g opacity="0">
        <animate attributeName="opacity" values="0;1" dur="1s" begin="0.5s" fill="freeze" />
        {format_row("Subject", config.NAME, 170)}
        {format_row("Role", config.ROLE, 195)}
        {format_row("Origin", config.LOCATION, 220)}
        {format_row("Education", config.EDUCATION, 245)}
        {format_row("Status", "Building + Learning + Shipping", 270)}
        {format_row("ToolChain", config.TOOLCHAIN, 295)}
    </g>

    <g opacity="0">
        <animate attributeName="opacity" values="0;1" dur="1s" begin="1.5s" fill="freeze" />
        <text x="500" y="335" class="title" style="fill: {ui_light}; filter:none;">-----------</text>
        {format_row("Core.Lang", config.LANGUAGES, 360)}
        {format_row("Core.Frontend", config.FRONTEND, 385)}
        {format_row("Core.Backend", config.BACKEND, 410)}
        {format_row("Core.Database", config.DATABASE, 435)}
        {format_row("Core.Infra", config.INFRA, 460)}
    </g>

    <g opacity="0">
        <animate attributeName="opacity" values="0;1" dur="1s" begin="2.5s" fill="freeze" />
        <text x="500" y="500" class="mono" style="fill: {text_muted}; font-size: 13px;">- Contact -</text>
        {format_row("Grid.Mail", config.EMAIL, 530)}
        {format_row("Grid.Portfolio", config.PORTFOLIO.replace("https://", ""), 555)}
        {format_row("Grid.LinkedIn", config.LINKEDIN.split("in/")[1].strip("/"), 580)}
    </g>

    <!-- Portrait Animation Layer -->
    <g transform="translate(41, 89)" fill="url(#portraitGrad)" shape-rendering="crispEdges">
        {intro_svg}
        {loop_svg}
    </g>
</svg>
'''
    out_file = OUTPUT_DIR / f"banner-{theme}.svg"
    out_file.write_text(svg, encoding="utf-8")
    print(f"Saved {theme} banner: {out_file}")

def process_portrait():
    print("PORTRAIT PROCESSOR")
    image = load_image()
    image = crop_portrait(image)
    mask = create_subject_mask(image)
    
    dither, resized_mask = process_and_dither(image, mask)
    
    Image.fromarray(dither, mode="L").save(DITHER_OUTPUT, optimize=True)
    
    pts, p_width, p_height = generate_dots(dither, resized_mask)
    
    build_banner(pts, p_width, p_height, "dark")
    build_banner(pts, p_width, p_height, "light")
    print("DONE")

if __name__ == "__main__":
    process_portrait()