# rashichakra

Daily Instagram bot that posts a 13-slide carousel: a date cover slide + 12
zodiac slides, each with the day's horoscope text overlaid on your hand-made
zodiac art.

Horoscopes are scraped from `ganeshaspeaks.com`. If any sign fails to scrape,
the bot **skips that day's post entirely** rather than posting a partial
carousel — so on rare site outages or layout changes, you'll see the workflow
log "SKIPPING today's post" and no Instagram post will appear that day.

Runs on GitHub Actions every morning (default 8:00 AM IST). No server needed.

## How it works

1. `src/main.py render` fetches all 12 horoscopes (scrape → LLM fallback), renders 13 JPGs into `posts/YYYY-MM-DD/`, and writes `state/_pending.json`.
2. The workflow commits the new images so they're served at `raw.githubusercontent.com/<repo>/<branch>/posts/...`.
3. `src/main.py publish` uploads **two** carousels of **7** slides each: date cover + six signs (Aries→Virgo), then the **same cover** again + six signs (Libra→Pisces); part 2 uses a short “part 2” caption.
4. The post is logged to `state/posted.json` for that date.

## One-time setup

### 1. Create a new Instagram account

Set up a fresh Instagram account for the astrology page (separate from @gyaankhand). Switch it to **Business** or **Creator** in Settings → Account type.

### 2. Add it to your existing Meta Developer app

Same Meta app you used for gyaankhand, second product instance:

1. <https://developers.facebook.com/apps> → click your app
2. Sidebar: **Instagram** → **API setup with Instagram Business Login**
3. **Add an Instagram account** → log in with the new astrology account → approve.
4. Accept the tester invite from <https://www.instagram.com/accounts/manage_access/>.
5. Generate a token from Graph API Explorer (selecting the new account this time) — make sure scopes include `instagram_business_content_publish`.
6. The token issued here is already long-lived (~60 days). Save it.
7. Get the new account's `IG_USER_ID`:
   ```bash
   curl -G "https://graph.instagram.com/v22.0/me" \
     --data-urlencode "fields=user_id,username,account_type" \
     --data-urlencode "access_token=YOUR_TOKEN"
   ```
   The numeric `user_id` from the response is what you want.

### 3. Drop your zodiac images in `data/zodiac_images/`

13 files, exact names (templates with empty space in the **lower half** for horoscope text):

```
cover.jpg
aries.jpg
taurus.jpg
gemini.jpg
cancer.jpg
leo.jpg
virgo.jpg
libra.jpg
scorpio.jpg
sagittarius.jpg
capricorn.jpg
aquarius.jpg
pisces.jpg
```

Each should be **1080×1350** portrait or larger (will be center-cropped). The renderer overlays text starting around 55% down the canvas — design the upper half with the zodiac art, leave the lower half empty (or with subtle background only) for text.

The cover slide gets a date stamp around 78% down — leave that area uncluttered.

### 4. GitHub repo

```bash
cd ~/rashichakra
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:<you>/rashichakra.git
git push -u origin main
```

In the repo on GitHub:

- **Settings → Secrets and variables → Actions → New repository secret**:
  - `IG_LONG_LIVED_TOKEN` — token from step 2
  - `IG_USER_ID` — numeric user_id from step 2
  - `IG_APP_ID` — Instagram App ID (from Instagram product page in your Meta app)
  - `IG_APP_SECRET` — Instagram App Secret
- **Variables** tab: `IG_HANDLE` = `@your_astro_handle`
- **Settings → Actions → General → Workflow permissions** → *Read and write permissions*
- **Settings → General → Danger Zone** → set repo to **Public** so raw.githubusercontent.com can serve images to Instagram.

### 5. First test run

**Actions** tab → *Daily Horoscope Carousel* → *Run workflow* → leave branch on `main` → green button.

If anything fails, the most likely first-run problems are: workflow write perms off, repo still private, or one of the secret names typo'd.

## Adjusting the schedule

`.github/workflows/post.yml` → `cron`. Times are UTC. For IST add 5h30:

| Local (IST) | Cron        |
| ----------- | ----------- |
| 7:00 AM     | `30 1 * * *` |
| 8:00 AM     | `30 2 * * *` (current) |
| 9:00 AM     | `30 3 * * *` |
| 12:00 PM    | `30 6 * * *` |

## Adjusting horoscope behavior

- **Change scrape source**: edit `src/scraper.py` — the `BASE_URL` and the `candidates` list of CSS selectors.
- **Add an LLM fallback later**: see the stub at `src/llm_fallback.py` for the steps to wire one up if you change your mind.
- **Skip behavior**: by default, if any of the 12 signs fails to scrape, the entire post is skipped (no partial carousel). To change this, edit `horoscope_all()` in `src/horoscope_loader.py` to swallow individual failures.

## Carousel size

The [Instagram Content Publishing API](https://developers.facebook.com/docs/instagram-platform/content-publishing/) allows **up to 10 images per carousel**. This project renders **13** JPGs on disk (cover + 12 signs) but publishes **14** carousel slots across two posts by **reusing the cover image URL** in part 2: **7 + 7** slides (cover+Aries…Virgo, then cover+Libra…Pisces).

## Troubleshooting

- **Workflow logs "SKIPPING today's post"** — scraper failed for at least one sign. Check the log to see which one, then visit `ganeshaspeaks.com/horoscopes/daily-horoscope/<that-sign>/` in a browser. If the page works for you but not the bot, the site likely changed its HTML structure — update `scraper.py`'s `candidates` list of CSS selectors. If the page itself is broken, just wait — usually self-resolves the next day.
- **Carousel publish fails with "Invalid image dimensions"** — Instagram requires a consistent aspect ratio across all carousel children. All zodiac templates and cover should be the same dimensions (the renderer normalizes them, but very different source ratios can leave artifacts).
- **`(#10) Application does not have permission for this action`** — token scope issue. Re-check that `instagram_business_content_publish` is granted.

## Token rotation

Long-lived tokens last ~60 days. Refresh:

```
GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=CURRENT_TOKEN
```

Then update `IG_LONG_LIVED_TOKEN` in GitHub Secrets. (Auto-refresh is on the to-do list.)
