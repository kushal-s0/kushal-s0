# ============================================
# GitHub Profile Banner Configuration
# ============================================
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- Personal ----------
NAME = "Kushal D. Soni"
GITHUB_USERNAME = "kushal-s0"

BACKGROUND = "#0A101F"


# ---------- Assets ----------
# SHOW_PORTRAIT = False -> no photo and no face silhouette is rendered at all.
# The particles simply cycle through the tech logos in assets/logos/.
# Set it to True only if you want a portrait photo in the banner, in which case
# PORTRAIT_PHOTO and PORTRAIT_SVG below must point at your own images.
SHOW_PORTRAIT = False

PORTRAIT_PHOTO = ROOT / "assets" / "portrait_final.png"
PORTRAIT_SVG = ROOT / "assets" / "portrait_svg.svg"
LOGOS_DIR = ROOT / "assets" / "logos"

ROLE = "AI / Full-Stack Developer"
LOCATION = "Mumbai, India"
EDUCATION = "B.Tech Computer Engineering (Honors - AIML)"

# ---------- Tech Stack ----------
LANGUAGES = "Python · Java · JavaScript · C · SQL"
FRONTEND = "HTML5 · CSS3 · Bootstrap · Tailwind · React.js"
BACKEND = "Django · Flask · Node.js · Express.js"
DATABASE = "MySQL · PostgreSQL · MongoDB · SQLite"
INFRA = "AWS · Docker · Vercel · Render · Unity"

# ---------- Social ----------
LINKEDIN = "https://www.linkedin.com/in/kushaldsoni/"
EMAIL = "teamatomixkardhikush@gmail.com"
PORTFOLIO = "https://portfolio1-blue-zeta.vercel.app/"

# ---------- Animation Timeline (in seconds) ----------
TIMING = {
    "clean_portrait_hold": 2.5,
    "photo_dissolve": 1.0,         # photo -> particle portrait
    "particle_portrait_hold": 1.5,
    "logo_transition": 1.5,        # particles forming logo
    "logo_hold": 2.5,
    "reconstruct": 1.0             # particle portrait -> photo
}

# ---------- Particle Settings ----------
PARTICLES = {
    "count": 1500,
    "target_width": 300,  # Size of logo bounding box
    "target_height": 300
}

# ---------- Default Palette ----------
# The 5 base portrait colors (from light to dark)
PORTRAIT_COLORS = ["#22D3EE", "#38BDF8", "#A78BFA", "#8B5CF6", "#7C3AED"]
