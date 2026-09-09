import re
import os
import random
from pathlib import Path
import base64
import numpy as np
import config
from animation_engine import compute_traveller_routes, generate_fluid_keyframes
from io import BytesIO
from PIL import Image
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
BANNER_OUT = OUTPUT_DIR / "banner.svg"

def get_base64_image(path):
    img = Image.open(path).convert('RGB')
    img = img.resize((400, 490), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c + c for c in hex_color)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))

def extract_logo_palette(svg_path, num_tones=5):
    """
    Auto-discovers the dominant color of an SVG and generates a 5-tone palette.
    """
    try:
        content = svg_path.read_text(encoding='utf-8')
        # Find all hex colors
        matches = re.findall(r'#[0-9a-fA-F]{3,6}', content)
        if not matches:
            return config.PORTRAIT_COLORS
            
        # Normalize to 6 chars
        hex_colors = []
        for m in matches:
            if len(m) == 4:
                m = '#' + m[1]*2 + m[2]*2 + m[3]*2
            hex_colors.append(m.upper())
            
        counter = Counter(hex_colors)
        # Exclude black and white if possible, unless it's the only color
        valid = [c for c in counter.most_common() if c[0] not in ('#000000', '#FFFFFF', '#FFF', '#000')]
        if valid:
            dominant = valid[0][0]
        else:
            dominant = counter.most_common(1)[0][0]
            
        # Generate 5 tones based on dominant
        r, g, b = hex_to_rgb(dominant)
        palette = []
        for i in range(num_tones):
            # Vary brightness by -40% to +40%
            factor = 0.6 + (i / (max(1, num_tones - 1))) * 0.8
            nr = min(255, r * factor)
            ng = min(255, g * factor)
            nb = min(255, b * factor)
            palette.append(rgb_to_hex(nr, ng, nb))
        return palette
    except Exception as e:
        print(f"Warning: color extraction failed for {svg_path}: {e}")
        return config.PORTRAIT_COLORS

def build_d_string(pts):
    parts = []
    for x, y in pts:
        parts.append(f"M{int(x)} {int(y)}h2v2h-2z")
    return "".join(parts)

def run():
    print("Parsing portrait_svg.svg to extract initial particles and colors...")
    with open(config.PORTRAIT_SVG, "r") as f:
        svg_content = f.read()

    paths = re.findall(r'<path fill=\"([^\"]+)\" d=\"([^\"]+)\"', svg_content)
    
    all_dots = []
    for fill, d in paths:
        for cmd in d.split('z'):
            if not cmd: continue
            m = re.search(r'M(\d+)\s*(\d+)', cmd)
            if m:
                all_dots.append({'x': int(m.group(1)), 'y': int(m.group(2)), 'fill': fill})
                
    num_hero = config.PARTICLES["count"]
    if len(all_dots) < num_hero:
        indices = np.random.choice(len(all_dots), num_hero, replace=True)
    else:
        indices = np.random.choice(len(all_dots), num_hero, replace=False)
        
    hero_indices_set = set(indices)
    hero_dots = [all_dots[i] for i in indices]
    static_dots = [all_dots[i] for i in range(len(all_dots)) if i not in hero_indices_set]
    
    scale = 490 / 283
    tx = 40 + (400 - (231 * scale)) / 2
    ty = 85
    
    static_paths_str = ""
    color_map = {}
    for d in static_dots:
        c = d['fill']
        if c not in color_map: color_map[c] = []
        color_map[c].append(d)
    for c, dots in color_map.items():
        d_str = "".join([f"M{int(d['x'] * scale + tx)} {int(d['y'] * scale + ty)}h1v1h-1z" for d in dots])
        static_paths_str += f'<path fill="{c}" d="{d_str}" />\n'
        
    hero_pts = []
    for d in hero_dots:
        hx = d['x'] * scale + tx
        hy = d['y'] * scale + ty
        hero_pts.append([hx, hy])
    hero_pts = np.array(hero_pts, dtype=np.float32)
    
    def color_brightness(hex_c):
        r, g, b = hex_to_rgb(hex_c)
        return 0.299*r + 0.587*g + 0.114*b
        
    for d in hero_dots:
        d['brightness'] = color_brightness(d['fill'])
        
    sorted_pairs = sorted(zip(hero_dots, hero_pts), key=lambda x: x[0]['brightness'])
    hero_dots = [p[0] for p in sorted_pairs]
    hero_pts = np.array([p[1] for p in sorted_pairs])
    
    buckets = 5
    bucket_size = num_hero // buckets
    
    print("Auto-discovering logos...")
    valid_logos = []
    palettes = [config.PORTRAIT_COLORS] # index 0 is portrait
    
    for ext in ['*.svg']:
        for logo_path in sorted(config.LOGOS_DIR.glob(ext)):
            print(f"Found {logo_path.name}")
            valid_logos.append(logo_path)
            palettes.append(extract_logo_palette(logo_path, buckets))
            
    if not valid_logos:
        print("No valid logos found in assets/logos/. Exiting.")
        return
        
    print(f"Discovered {len(valid_logos)} logos.")
    
    target_box = config.PARTICLES["target_width"]
    cx = 40 + 400 / 2
    cy = 85 + 490 / 2
    
    routes = compute_traveller_routes(hero_pts, valid_logos, target_box, target_box, num_hero)
    
    if not routes:
        print("Failed to compute routes. Exiting.")
        return
        
    for r in routes[1:-1]:
        r[:, 0] += cx - target_box/2
        r[:, 1] += cy - target_box/2
        
    print("Generating strict timeline...")
    
    dur = config.TIMING
    
    timeline_d = []          # (time, points, color_palette_index)
    timeline_photo = []      # (time, opacity)
    timeline_static = []     # (time, opacity)
    timeline_hero_op = []    # (time, opacity)
    
    t = 0.0
    # A. CLEAN PORTRAIT HOLD
    timeline_d.append((t, routes[0], 0))
    timeline_photo.append((t, 1))
    timeline_static.append((t, 0))
    timeline_hero_op.append((t, 0))
    
    t += dur["clean_portrait_hold"]
    timeline_d.append((t, routes[0], 0))
    timeline_photo.append((t, 1))
    timeline_static.append((t, 0))
    timeline_hero_op.append((t, 0))
    
    # A -> B: PHOTO DISSOLVE
    t += dur["photo_dissolve"]
    timeline_d.append((t, routes[0], 0))
    timeline_photo.append((t, 0))
    timeline_static.append((t, 1))
    timeline_hero_op.append((t, 1))
    
    # B: PARTICLE PORTRAIT HOLD
    t += dur["particle_portrait_hold"]
    timeline_d.append((t, routes[0], 0))
    timeline_photo.append((t, 0))
    timeline_static.append((t, 1))
    timeline_hero_op.append((t, 1))
    
    # Logos Iteration
    for i in range(len(valid_logos)):
        # Transition to Logo i
        start_t = t
        end_t = t + dur["logo_transition"]
        frames = generate_fluid_keyframes(routes[i], routes[i+1], steps=6, turbulence=25.0)
        
        for j in range(1, len(frames)):
            frame_t = start_t + (end_t - start_t) * (j / (len(frames)-1))
            # The palette index smoothly transitions to i+1
            timeline_d.append((frame_t, frames[j], i+1))
            
        timeline_photo.append((end_t, 0))
        timeline_static.append((start_t + 0.1, 0)) # Disappear as soon as particles leave
        timeline_static.append((end_t, 0))
        timeline_hero_op.append((end_t, 1))
        
        t = end_t
        
        # Logo Hold
        t += dur["logo_hold"]
        timeline_d.append((t, routes[i+1], i+1))
        timeline_photo.append((t, 0))
        timeline_static.append((t, 0))
        timeline_hero_op.append((t, 1))
        
    # N -> B: FINAL LOGO TO PORTRAIT
    start_t = t
    end_t = t + dur["logo_transition"]
    frames = generate_fluid_keyframes(routes[-2], routes[-1], steps=6, turbulence=25.0)
    for j in range(1, len(frames)):
        frame_t = start_t + (end_t - start_t) * (j / (len(frames)-1))
        timeline_d.append((frame_t, frames[j], 0)) # transition back to portrait colors
        
    timeline_photo.append((end_t, 0))
    timeline_static.append((start_t, 0))
    timeline_static.append((end_t, 1)) # Reappear when particles arrive
    timeline_hero_op.append((end_t, 1))
    t = end_t
    
    # B: PARTICLE PORTRAIT HOLD (Closing)
    t += dur["particle_portrait_hold"]
    timeline_d.append((t, routes[-1], 0))
    timeline_photo.append((t, 0))
    timeline_static.append((t, 1))
    timeline_hero_op.append((t, 1))
    
    # B -> A: RECONSTRUCT
    t += dur["reconstruct"]
    timeline_d.append((t, routes[-1], 0))
    timeline_photo.append((t, 1))
    timeline_static.append((t, 0))
    timeline_hero_op.append((t, 0))
    
    total_dur = t
    print(f"Total animation loop: {total_dur}s")
    
    path_elements = ""
    for b in range(buckets):
        start_idx = b * bucket_size
        end_idx = (b+1) * bucket_size if b < buckets-1 else num_hero
        
        d_values = []
        fill_values = []
        kt_d = []
        
        for frame_t, frame_pts, pal_idx in timeline_d:
            sub_pts = frame_pts[start_idx:end_idx]
            d_values.append(build_d_string(sub_pts))
            fill_values.append(palettes[pal_idx][b])
            kt_d.append(f"{frame_t / total_dur:.3f}")
            
        kt_str = ";".join(kt_d)
        
        path_elements += f'''
        <path fill="{palettes[0][b]}">
            <animate attributeName="d" values="{";".join(d_values)}" keyTimes="{kt_str}" dur="{total_dur}s" repeatCount="indefinite" />
            <animate attributeName="fill" values="{";".join(fill_values)}" keyTimes="{kt_str}" dur="{total_dur}s" repeatCount="indefinite" />
        </path>
        '''
        
    def format_op(timeline):
        kt = ";".join([f"{time/total_dur:.3f}" for time, op in timeline])
        val = ";".join([str(op) for time, op in timeline])
        return kt, val
        
    photo_kt, photo_val = format_op(timeline_photo)
    static_kt, static_val = format_op(timeline_static)
    hero_kt, hero_val = format_op(timeline_hero_op)
    
    print("Writing SVG...")
    photo_b64 = get_base64_image(config.PORTRAIT_PHOTO)
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1180 610" width="1180" height="610">
    <defs>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&amp;family=Inter:wght@400;500;700&amp;display=swap');
            text {{ font-family: 'JetBrains Mono', monospace; }}
            .label {{ fill: #94A3B8; font-size: 14px; }}
            .val {{ fill: #F8FAFC; font-weight: 700; font-size: 14px; }}
            .title {{ fill: #22D3EE; font-size: 12px; letter-spacing: 2px; }}
        </style>
        <filter id="photoBlur">
            <feGaussianBlur stdDeviation="0">
                <!-- We map opacity inversion to blur: when opacity is 0, blur is 8 -->
                <animate attributeName="stdDeviation" values="{';'.join(['0' if op==1 else '8' for _, op in timeline_photo])}" keyTimes="{photo_kt}" dur="{total_dur}s" repeatCount="indefinite" />
            </feGaussianBlur>
        </filter>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
    </defs>

    <!-- Background -->
    <rect width="1180" height="610" fill="{config.BACKGROUND}" />
    
    <!-- Outer Window Frame -->
    <rect x="2" y="2" width="1176" height="606" rx="14" fill="none" stroke="#22D3EE" stroke-width="2" opacity="0.4" filter="url(#glow)" />
    <rect x="2" y="2" width="1176" height="606" rx="14" fill="none" stroke="#22D3EE" stroke-width="1" />
    <rect x="2" y="2" width="1176" height="42" rx="14" fill="#070B16" />
    <line x1="2" y1="44" x2="1178" y2="44" stroke="rgba(255,255,255,0.1)" />

    <!-- Window controls -->
    <circle cx="24" cy="23" r="6" fill="#FF5F56" />
    <circle cx="44" cy="23" r="6" fill="#FFBD2E" />
    <circle cx="64" cy="23" r="6" fill="#27C93F" />
    <text x="590" y="27" fill="#64748B" font-size="12" text-anchor="middle">{config.EMAIL} - ./profile.sh --hero</text>

    <!-- Left Box (Portrait area) -->
    <text x="40" y="72" class="title" fill="#64748B">VISUAL.MAP</text>
    <rect x="40" y="85" width="400" height="490" rx="8" fill="#070B16" stroke="rgba(34,211,238,0.2)" />

    <!-- Photo Layer -->
    <image x="40" y="85" width="400" height="490" href="data:image/png;base64,{photo_b64}" preserveAspectRatio="xMidYMid slice" filter="url(#photoBlur)">
        <animate attributeName="opacity" values="{photo_val}" keyTimes="{photo_kt}" dur="{total_dur}s" repeatCount="indefinite" />
    </image>

    <!-- Static Background Dots -->
    <g opacity="0">
        <animate attributeName="opacity" values="{static_val}" keyTimes="{static_kt}" dur="{total_dur}s" repeatCount="indefinite" />
        {static_paths_str}
    </g>
    
    <!-- Dynamic Path Morphing Particles -->
    <g filter="url(#glow)" opacity="0">
        <animate attributeName="opacity" values="{hero_val}" keyTimes="{hero_kt}" dur="{total_dur}s" repeatCount="indefinite" />
        {path_elements}
    </g>

    <!-- Right Box (Info area) -->
    <text x="500" y="100" class="title">SYSTEM.INFO</text>
    <line x1="590" y1="96" x2="1140" y2="96" stroke="rgba(255,255,255,0.1)" />
    
    <text x="500" y="140" class="label">Name ........... <tspan class="val">{config.NAME}</tspan></text>
    <text x="500" y="170" class="label">Role ........... <tspan class="val">{config.ROLE}</tspan></text>
    <text x="500" y="200" class="label">Location ....... <tspan class="val">{config.LOCATION}</tspan></text>
    <text x="500" y="230" class="label">Education ...... <tspan class="val">{config.EDUCATION}</tspan></text>
    
    <text x="500" y="280" class="title">STACK.INFO</text>
    <line x1="590" y1="276" x2="1140" y2="276" stroke="rgba(255,255,255,0.1)" />
    
    <text x="500" y="320" class="label">Core.Lang ...... <tspan class="val">{config.LANGUAGES}</tspan></text>
    <text x="500" y="350" class="label">Core.Front ..... <tspan class="val">{config.FRONTEND}</tspan></text>
    <text x="500" y="380" class="label">Core.Back ...... <tspan class="val">{config.BACKEND}</tspan></text>
    <text x="500" y="410" class="label">Core.Data ...... <tspan class="val">{config.DATABASE}</tspan></text>
    <text x="500" y="440" class="label">Core.Infra ..... <tspan class="val">{config.INFRA}</tspan></text>
    
    <text x="500" y="490" class="title">NETWORK.INFO</text>
    <line x1="600" y1="486" x2="1140" y2="486" stroke="rgba(255,255,255,0.1)" />
    
    <text x="500" y="530" class="label">Email .......... <tspan class="val">{config.EMAIL}</tspan></text>
    <text x="500" y="560" class="label">Portfolio ...... <tspan class="val">{config.PORTFOLIO.replace("https://", "")}</tspan></text>
</svg>
'''

    BANNER_OUT.write_text(svg, encoding="utf-8")
    print(f"Saved optimized banner to {BANNER_OUT}")

if __name__ == "__main__":
    run()
