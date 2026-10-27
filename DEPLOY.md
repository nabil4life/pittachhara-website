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

## Custom domain — LIVE as of 2026-10-27 (pittachhara.org)

The domain is registered at **Namecheap** (BasicDNS) and now points at the current
Vercel project `prj_MReLrOn97m3tHsvukYcmNkjIsc6O`. Both `pittachhara.org` and
`www.pittachhara.org` are verified on that project; `www` 308-redirects to the apex.

### DNS records as currently set at Namecheap (Advanced DNS → Host Records)

| Type  | Host               | Value                                                    | Note |
|-------|--------------------|----------------------------------------------------------|------|
| A     | @                  | `216.198.79.1`                                           | Vercel IP. Unchanged during cutover — was already pointing at Vercel. |
| CNAME | www                | `cname.vercel-dns.com.`                                 | **Changed** during cutover (see rollback). |
| TXT   | _vercel            | `vc-domain-verify=pittachhara.org,24cd4c076289bec4b669` | Added — apex ownership verification. |
| TXT   | _vercel            | `vc-domain-verify=www.pittachhara.org,5f02e5e04e9059f6cafd` | Added — www ownership verification. |
| TXT   | default._domainkey | `v=DKIM1;k=rsa;p=…` (DKIM)                               | **Private Email — do not touch.** |
| MX / mail | (Private Email)| Namecheap Private Email records                          | **Do not touch — breaks email.** |

Vercel recommends switching the apex A record to `76.76.21.21`, but `216.198.79.1`
is a valid Vercel IP and reads `misconfigured: false`, so it was left as-is. No action needed.

### Rollback — to revert the domain to the OLD host/project

Before the cutover the domain was attached to a **different/older Vercel project**, and
the `www` CNAME pointed at that project's edge. That old project still exists and its last
deployment is frozen, so it is the rollback target. Vercel only allows a domain on one
project at a time, so reverting means moving it back.

**Old `www` CNAME value (restore this to revert www):**

```
562f9d85ac276261.vercel-dns-017.com.
```

To revert fully:
1. In the OLD Vercel project → Settings → Domains → re-add `pittachhara.org` and `www`
   (it will show a TXT challenge; add it at Namecheap and verify).
2. At Namecheap → change the `www` CNAME back to `562f9d85ac276261.vercel-dns-017.com.`
   (the apex A record `216.198.79.1` can stay — it is generic Vercel and both projects use it).
3. The two `_vercel` TXT records above are harmless and can stay or be removed.

Nothing was deleted: the GitHub repo, the current Vercel project, and the old Vercel project
all remain intact, so you can switch either direction at any time.

---

## Before-launch checklist

- [ ] Optimise images — `images/` is ~315 MB of full-size phone photos. Resizing to
      ~2000px wide and re-compressing would cut this ~10x, speeding up the site and
      staying well inside Vercel's free bandwidth. (Ask Claude to run the optimisation pass.)
- [ ] Swap in the real site logo (currently a placeholder).
- [ ] Close the MISSING slots once Russel sends the final photos (see `../comms/asks_for_russel.md`).
- [ ] Verify the MDPI cover (slot 2.5) opens the PDF.
