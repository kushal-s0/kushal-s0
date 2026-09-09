# Setup — making the profile README work

Everything here is a **one-time** setup. After step 4 the stats cards and the
contribution snake regenerate automatically every day.

---

## Why the images are broken right now

| Image | Source | Works without setup? |
|:---|:---|:---|
| Banner | `./output/banner.svg` (committed to this repo) | ✅ yes |
| Streak stats | `streak-stats.demolab.com` (live API) | ✅ yes |
| Stats card | `output` branch, built by GitHub Actions | ❌ needs setup |
| Top languages | `output` branch, built by GitHub Actions | ❌ needs setup |
| Contribution snake | `output` branch, built by GitHub Actions | ❌ needs setup |

The three broken ones all point at
`raw.githubusercontent.com/kushal-s0/kushal-s0/output/…`.
That `output` branch does not exist until the workflow runs. Nothing is wrong
with the URLs — the branch just isn't there yet.

> **Why not use the public `github-readme-stats.vercel.app` API instead?**
> Because it's a shared instance that is heavily rate-limited — it returns
> errors most of the time, which is exactly what you saw. Generating the SVGs
> in your own Actions runner avoids the rate limit completely.

---

## Step 1 — Create the profile repository

The README only shows on your GitHub profile if the repo is named **exactly**
the same as your username:

```
kushal-s0/kushal-s0
```

It must be **public**, and initialised **without** a README (this repo has one).

## Step 2 — Push this folder to it

```bash
cd "college folder/readme"
git init
git add .
git commit -m "Add profile README and banner generator"
git branch -M main
git remote add origin https://github.com/kushal-s0/kushal-s0.git
git push -u origin main
```

> ⚠️ This folder is currently **not** its own git repository — `git status` here
> resolves to an unrelated parent repo. Run `git init` as shown above so you
> don't accidentally commit unrelated files.

## Step 3 — Add the `STATS_TOKEN` secret

The stats card needs a token to read your contribution counts.

1. Go to **https://github.com/settings/tokens** → *Generate new token (classic)*
2. Give it a name, an expiry, and tick **only** these scopes:
   - `repo`
   - `read:user`
3. Copy the token (you only see it once).
4. In your `kushal-s0/kushal-s0` repo, go to
   **Settings → Secrets and variables → Actions → New repository secret**
5. Name it exactly `STATS_TOKEN`, paste the token, save.

## Step 4 — Run the workflow

1. Open the **Actions** tab on the repo.
2. If prompted, click **"I understand my workflows, enable them"**.
3. Pick **"Generate Profile Assets (Stats & Snake)"** in the left sidebar.
4. Click **Run workflow → Run workflow**.

It takes 2–3 minutes. When it finishes it creates an `output` branch containing
`stats.svg`, `top-langs.svg`, `github-snake.svg` and `github-snake-dark.svg`.
Refresh your profile — all three images now render.

After this it re-runs automatically every day at midnight UTC (the `schedule`
trigger in the workflow).

### If the workflow fails

- **"github-readme-stats generated an error SVG"** → `STATS_TOKEN` is missing,
  expired, or lacks the `read:user` scope. Regenerate it and update the secret.
- **Snake step fails** → make sure the repo is public; the snake action reads
  your public contribution graph.
- **Push to `output` fails** → check
  **Settings → Actions → General → Workflow permissions** is set to
  **Read and write permissions**.

---

## Rebuilding the banner

The banner is a pre-rendered SVG committed at `output/banner.svg`. Editing
`generator/config.py` does **not** change it until you rebuild:

```bash
cd generator
npm install
pip install -r requirements.txt
pip install opensimplex        # not listed in requirements.txt
python build_hero.py
```

Output goes to `output/banner.svg`. Commit it.

### Face-free mode

`generator/config.py` has:

```python
SHOW_PORTRAIT = False
```

With this off, no photo and no face silhouette is rendered at all — the 1,500
particles just morph between the tech logos in `assets/logos/`. The generated
SVG contains no embedded image data whatsoever.

Set it to `True` only if you later want a portrait, in which case you must also
supply `assets/portrait_final.png` and `assets/portrait_svg.svg`.

### Changing which logos appear

The animation auto-discovers every `.svg` in `assets/logos/` and cycles them in
alphabetical order. To change the lineup, add or delete files there and rebuild.

Currently included: AWS, Docker, Express, Java, MongoDB, MySQL, Node.js,
**Oracle**, React, JavaScript.

Oracle isn't part of your stack — remove it if you'd rather it didn't appear:

```bash
rm assets/logos/Oracle_logo.svg
cd generator && python build_hero.py
```

---

## Remaining placeholders

Four project links in `README.md` still need real URLs — search for `«REPLACE-`:

| Line | Project |
|:---|:---|
| ~226 | CommUnity |
| ~245 | GeoSwipe |
| ~265 | Atomix |
| ~281 | AI-Based Internship Recommendation System |
