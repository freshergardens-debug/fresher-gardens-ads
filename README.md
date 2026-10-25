# Fresher Gardens ad creatives

This repo holds the image ads for the Fresher Gardens Meta campaign. It must be **public**, because Meta pulls each image from its raw GitHub link when an ad is created.

- `assets/photos/` holds real job and team photos (resized). `library.json` says what each one shows and what it suits.
- `assets/brand/` holds the logo files.
- `specs/` holds one JSON file per batch of ads. A spec is a layout plus short text, never free design.
- `tools/make_ads.py` turns a spec into PNGs.
- `out/` holds the rendered ads. Meta reads these via `https://raw.githubusercontent.com/<owner>/fresher-gardens-ads/main/out/<id>_feed.png`.

## Make a batch

```bash
pip install playwright pillow   # Chromium must be available to Playwright
python3 tools/make_ads.py specs/2026-10-25-launch.json
```

Each ad gives `out/<id>_feed.png` (1080×1350) and `out/<id>_story.png` (1080×1920), plus `out/_sheet_<batch>.jpg` to check by eye.

## Layouts

| layout | what it is | fields |
|---|---|---|
| `text_thread` | iMessage thread to an unreliable mowing guy | contact, messages[{ts?, text}], read, band |
| `callout_photo` | headline over a real job photo | photo, kicker, headline, sub |
| `before_after` | stacked before/after | headline, before, after |
| `face_guarantee` | team photo with guarantee and reviews | photo, headline, reviews |
| `price_shock` | big price on a photo | photo, chip, from_label, amount, what, then, cta |
| `text_colour` | bold text on brand colour | theme (lime/forest/cream), headline, chip, cta, small |

Put `[square brackets]` around the words you want in the accent colour.

## Rules for every ad

- Use real photos only, from `assets/photos`. No AI images.
- Every claim must match freshergardenslawns.com.
- Keep it to about 15 words on the image. Call out the person, name the pain, show the fix.
- Ad ids are lowercase with hyphens and never reused.
