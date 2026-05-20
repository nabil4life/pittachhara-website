# Deploying the Pittachhara site (GitHub + Vercel)

This folder (`website/development/`) is the deploy repo. It already has a git
commit, a `.gitignore` (keeps the raw video masters out), a `.vercelignore`
(keeps `_tools/` etc. out of the live site), and a `vercel.json`.

The site is a single static `index.html` plus an `images/` folder. No build step.

---

## One-time setup

### 1. Create the GitHub repo

On github.com → **New repository**:
- Name: `pittachhara-website` (or anything)
- Private is fine (Vercel can still read it after you connect)
- Do **not** add a README/.gitignore/licence (the folder already has commits)

### 2. Push this folder to it

In Terminal:

```bash
cd "/Users/nabil/Projects/pittachhara/website/development"
git remote add origin https://github.com/<YOUR-USERNAME>/pittachhara-website.git
git branch -M main
git push -u origin main
```

The first push moves ~324 MB, so give it a few minutes. (If git asks you to sign
in, use a GitHub Personal Access Token as the password, or the GitHub CLI `gh auth login`.)

### 3. Connect Vercel

On vercel.com → **Add New… → Project** → **Import** the `pittachhara-website` repo.
- Framework Preset: **Other**
- Build & Output settings: leave everything default / empty (it is a static site)
- Root Directory: leave as `./`
- Click **Deploy**

After ~1 minute you get a review URL like `https://pittachhara-website.vercel.app`.
Send that to Russel.

---

## Updating the site later

Every time the site changes, from this folder:

```bash
cd "/Users/nabil/Projects/pittachhara/website/development"
git add -A
git commit -m "describe the change"
git push
```

Vercel auto-rebuilds and the live URL updates in under a minute.

---

## Custom domain at launch (pittachhara.org)

When ready to go live:
1. Vercel project → **Settings → Domains** → add `pittachhara.org` (and `www`).
2. Vercel shows you DNS records (an A record / CNAME).
3. **Russel** updates those records at wherever pittachhara.org's DNS is managed.
   DNS is his to control, not ours.
4. Once DNS propagates (minutes to a few hours), the site is live on the real domain.

---

## Before-launch checklist

- [ ] Optimise images — `images/` is ~315 MB of full-size phone photos. Resizing to
      ~2000px wide and re-compressing would cut this ~10x, speeding up the site and
      staying well inside Vercel's free bandwidth. (Ask Claude to run the optimisation pass.)
- [ ] Swap in the real site logo (currently a placeholder).
- [ ] Close the MISSING slots once Russel sends the final photos (see `../comms/asks_for_russel.md`).
- [ ] Verify the MDPI cover (slot 2.5) opens the PDF.
