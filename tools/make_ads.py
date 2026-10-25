"""Fresher Gardens ad generator.

Renders ads from small JSON specs into feed (1080x1350) and Stories/Reels
(1080x1920) PNGs, using real photos from assets/photos and the six proven layouts.

  python3 tools/make_ads.py specs/2026-11-09.json      # one batch file
  -> out/<id>_feed.png, out/<id>_story.png, out/_sheet_<batch>.jpg (contact sheet to check)

A batch file is {"batch": "2026-11-09", "ads": [ {spec}, ... ]}. Every spec has
"id" (lowercase-hyphens, unique forever), "layout", and that layout's fields:

  text_thread    contact, messages [{ts?, text}], read, band
  callout_photo  photo, kicker, headline, sub, pos_feed?, pos_story?
  before_after   headline, before, after
  face_guarantee photo, headline, reviews (true/false), pos_feed?, pos_story?
  price_shock    photo, chip, from_label, amount, what, then, cta, pos_feed?, pos_story?
  text_colour    theme ("lime"|"forest"|"cream"), headline, chip, cta, small

Wrap words in [square brackets] to colour them as the accent.
Keep on-image text short: headline 3-8 words, at most ~15 words on the whole image.
Requires: pip install playwright pillow; playwright install chromium (if not present).
"""
import html, json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "assets" / "photos"
BRAND = ROOT / "assets" / "brand"
OUT = ROOT / "out"

FORMATS = {
    "feed": dict(w=1080, h=1350, top=72, bottom=72, side=72),
    "story": dict(w=1080, h=1920, top=290, bottom=420, side=72),
}

BASE = """
:root{--forest:#0F2818;--lime:#8CCB45;--cream:#F4EFE2;--ink:#11201A}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:var(--w);height:var(--h);overflow:hidden;background:#000}
.ad{position:relative;width:var(--w);height:var(--h);overflow:hidden;font-family:Inter,sans-serif;color:#fff;-webkit-font-smoothing:antialiased}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.layer{position:absolute;inset:0}
.hd{font-family:'Inter Display',Inter,sans-serif;font-weight:900;line-height:.98;letter-spacing:-2px;text-wrap:balance}
.hd em{font-style:normal;color:var(--lime)}
.kick{font-weight:800;letter-spacing:3px;text-transform:uppercase}
.pill{display:inline-flex;align-items:center;gap:16px;border-radius:999px;font-weight:800}
.disc{width:96px;height:96px;border-radius:50%;background:var(--forest);display:flex;align-items:center;justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.35)}
.disc img{height:72px}
"""

STAR = "<svg viewBox='0 0 24 24' width='46' height='46'><path fill='#F4B400' d='M12 2.6l2.9 6 6.6.8-4.9 4.6 1.3 6.5L12 17.3l-5.9 3.2 1.3-6.5L2.5 9.4l6.6-.8z'/></svg>"


def t(s):
    """Escape text and turn [words] into the accent colour."""
    return re.sub(r"\[(.+?)\]", r"<em>\1</em>", html.escape(str(s or "")))


def photo(name):
    p = PHOTOS / name
    if not p.exists():
        raise SystemExit(f"Photo not found: {name} (see assets/photos/library.json)")
    return p.as_uri()


ICON = (BRAND / "logo_icon.png").as_uri()


def page(fmt, body, css):
    f = FORMATS[fmt]
    root = f":root{{--w:{f['w']}px;--h:{f['h']}px;--top:{f['top']}px;--bottom:{f['bottom']}px;--side:{f['side']}px}}"
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{root}{BASE}{css}</style></head><body>{body}</body></html>"


def text_thread(s, fmt):
    story = fmt == "story"
    css = f"""
    .ad{{background:#fff;color:#000}}
    .status{{position:absolute;top:{40 if story else 26}px;left:64px;right:64px;display:flex;justify-content:space-between;font-weight:600;font-size:34px}}
    .nav{{position:absolute;top:{300 if story else 96}px;left:0;right:0;text-align:center;border-bottom:1px solid #E5E5EA;padding-bottom:26px}}
    .back{{position:absolute;left:40px;top:34px;color:#0A84FF;font-size:64px;font-weight:300;line-height:1}}
    .av{{width:108px;height:108px;border-radius:50%;background:linear-gradient(#A6ABB7,#858A96);margin:0 auto;color:#fff;font-size:46px;font-weight:600;display:flex;align-items:center;justify-content:center}}
    .name{{font-size:28px;margin-top:10px;color:#000}}
    .thread{{position:absolute;top:{520 if story else 320}px;left:44px;right:44px;display:flex;flex-direction:column;align-items:flex-end;gap:12px}}
    .ts{{align-self:center;color:#8E8E93;font-size:26px;font-weight:500;margin:22px 0 8px}}
    .b{{background:#0A84FF;color:#fff;font-size:42px;line-height:1.22;padding:22px 32px;border-radius:44px 44px 12px 44px;max-width:760px}}
    .read{{color:#8E8E93;font-size:26px;font-weight:600;margin-right:12px}}
    .band{{position:absolute;left:0;right:0;bottom:0;height:{700 if story else 300}px;background:var(--forest);padding:{58 if story else 52}px var(--side) 0;display:flex;align-items:flex-start;justify-content:space-between;gap:30px}}
    .band .hd{{font-size:70px;color:#fff;letter-spacing:-1px}}
    .band img{{height:96px;flex:none;margin-top:8px}}
    """
    contact = s.get("contact", "Mowing guy")
    initials = "".join(w[0] for w in contact.split()[:2]).upper()
    msgs = ""
    for m in s["messages"]:
        if m.get("ts"):
            msgs += f"<div class='ts'>{t(m['ts'])}</div>"
        msgs += f"<div class='b'>{t(m['text'])}</div>"
    body = f"""<div class='ad'>
      <div class='status'><span>9:41</span><span>&#9679;&#9679;&#9679;&#9679; &nbsp;&#9646;</span></div>
      <div class='nav'><div class='back'>&#8249;</div><div class='av'>{t(initials)}</div><div class='name'>{t(contact)} &rsaquo;</div></div>
      <div class='thread'>{msgs}<div class='read'>{t(s.get('read', 'Read'))}</div></div>
      <div class='band'><p class='hd'>{t(s['band'])}</p><img src='{ICON}'></div></div>"""
    return page(fmt, body, css)


def callout_photo(s, fmt):
    pos = s.get("pos_story" if fmt == "story" else "pos_feed", "50% 45%")
    css = """
    .shade{background:linear-gradient(to bottom,rgba(8,22,13,.92) 0%,rgba(8,22,13,.78) 38%,rgba(8,22,13,0) 62%)}
    .top{position:absolute;top:var(--top);left:var(--side);right:var(--side)}
    .kick{font-size:32px;color:var(--lime)}
    .top .hd{font-size:128px;margin-top:22px}
    .sub{font-size:52px;font-weight:800;margin-top:26px;color:#fff}
    .logo{position:absolute;left:var(--side);bottom:var(--bottom)}
    """
    body = f"""<div class='ad'><img class='bg' src='{photo(s['photo'])}' style='object-position:{pos}'>
      <div class='layer shade'></div>
      <div class='top'><p class='kick'>{t(s.get('kicker'))}</p><h1 class='hd'>{t(s['headline'])}</h1><p class='sub'>{t(s.get('sub'))}</p></div>
      <div class='logo disc'><img src='{ICON}'></div></div>"""
    return page(fmt, body, css)


def before_after(s, fmt):
    story = fmt == "story"
    head_h = 660 if story else 300
    rest = (1920 - 420 - head_h) if story else (1350 - head_h)
    ph = rest // 2
    after_h = rest - ph + (420 if story else 0)
    css = f"""
    .ad{{background:var(--forest)}}
    .head{{position:absolute;left:0;right:0;top:0;height:{head_h}px;padding:0 var(--side) 34px;display:flex;align-items:flex-end;justify-content:space-between;gap:24px}}
    .head .hd{{font-size:{100 if story else 96}px}}
    .head img{{height:84px;flex:none;margin-bottom:6px}}
    .ph{{position:absolute;left:0;right:0;overflow:hidden}}
    .ph img{{width:100%;height:100%;object-fit:cover}}
    .tag{{position:absolute;left:var(--side);top:28px;font-size:30px;font-weight:900;letter-spacing:3px;padding:12px 22px;border-radius:10px}}
    """
    body = f"""<div class='ad'>
      <div class='head'><h1 class='hd'>{t(s['headline'])}</h1><img src='{ICON}'></div>
      <div class='ph' style='top:{head_h}px;height:{ph - 4}px'><img src='{photo(s['before'])}' style='object-position:50% 70%'><span class='tag' style='background:#111;color:#fff'>BEFORE</span></div>
      <div class='ph' style='top:{head_h + ph}px;height:{after_h}px'><img src='{photo(s['after'])}' style='object-position:50% {"55%" if story else "62%"}'><span class='tag' style='background:var(--lime);color:var(--forest)'>AFTER</span></div></div>"""
    return page(fmt, body, css)


def face_guarantee(s, fmt):
    pos = s.get("pos_story" if fmt == "story" else "pos_feed", "50% 30%")
    rev = f"<div class='rev'><span class='st'>{STAR * 5}</span>4.9 from 75 Google reviews</div>" if s.get("reviews", True) else ""
    css = """
    .shade{background:linear-gradient(to top,rgba(8,22,13,.95) 0%,rgba(8,22,13,.85) 30%,rgba(8,22,13,0) 58%)}
    .bottom{position:absolute;left:var(--side);right:var(--side);bottom:var(--bottom)}
    .bottom .hd{font-size:118px}
    .rev{display:flex;align-items:center;gap:16px;margin-top:30px;font-size:36px;font-weight:700}
    .rev .st{display:flex;gap:2px}
    """
    body = f"""<div class='ad'><img class='bg' src='{photo(s['photo'])}' style='object-position:{pos}'>
      <div class='layer shade'></div>
      <div class='bottom'><h1 class='hd'>{t(s['headline'])}</h1>{rev}</div></div>"""
    return page(fmt, body, css)


def price_shock(s, fmt):
    pos = s.get("pos_story" if fmt == "story" else "pos_feed", "50% 60%")
    css = """
    .shade{background:linear-gradient(to top,rgba(8,22,13,.97) 0%,rgba(8,22,13,.9) 42%,rgba(8,22,13,.2) 70%,rgba(8,22,13,.1) 100%)}
    .logo{position:absolute;top:var(--top);left:var(--side)}
    .bottom{position:absolute;left:var(--side);right:var(--side);bottom:var(--bottom)}
    .chip{display:inline-block;font-size:30px;font-weight:900;letter-spacing:3px;background:var(--lime);color:var(--forest);padding:12px 22px;border-radius:10px}
    .price{display:flex;align-items:flex-start;gap:14px;margin-top:22px}
    .from{font-size:54px;font-weight:800;margin-top:44px}
    .amt{font-family:'Inter Display',Inter,sans-serif;font-weight:900;font-size:330px;line-height:.82;letter-spacing:-12px;color:var(--lime)}
    .what{font-family:'Inter Display',Inter,sans-serif;font-weight:900;font-size:76px;margin-top:18px;letter-spacing:-1px}
    .then{font-size:36px;font-weight:600;margin-top:14px;color:rgba(255,255,255,.88)}
    .cta{background:#fff;color:var(--forest);font-size:44px;padding:28px 48px;margin-top:40px}
    """
    body = f"""<div class='ad'><img class='bg' src='{photo(s['photo'])}' style='object-position:{pos}'>
      <div class='layer shade'></div><div class='logo disc'><img src='{ICON}'></div>
      <div class='bottom'><span class='chip'>{t(s.get('chip', 'NEW CLIENTS'))}</span>
        <div class='price'><span class='from'>{t(s.get('from_label', 'from'))}</span><span class='amt'>{t(s['amount'])}</span></div>
        <p class='what'>{t(s['what'])}</p><p class='then'>{t(s.get('then'))}</p>
        <div class='pill cta'>{t(s.get('cta', 'Get my price'))} <span>&rarr;</span></div></div></div>"""
    return page(fmt, body, css)


def text_colour(s, fmt):
    theme = s.get("theme", "lime")
    bg, fg, chip_bg, chip_fg, cta_bg, cta_fg = {
        "lime": ("var(--lime)", "var(--forest)", "var(--forest)", "var(--lime)", "var(--forest)", "#fff"),
        "forest": ("var(--forest)", "#fff", "var(--lime)", "var(--forest)", "var(--lime)", "var(--forest)"),
        "cream": ("var(--cream)", "var(--forest)", "var(--forest)", "var(--lime)", "var(--forest)", "#fff"),
    }[theme]
    css = f"""
    .ad{{background:{bg};color:{fg}}}
    .wrap{{position:absolute;top:var(--top);left:var(--side);right:var(--side);bottom:var(--bottom);display:flex;flex-direction:column;justify-content:space-between}}
    .brand{{display:flex;align-items:center;gap:18px;font-weight:900;font-size:34px;letter-spacing:4px;text-transform:uppercase}}
    .brand .dot{{width:72px;height:72px;border-radius:50%;background:var(--forest);display:flex;align-items:center;justify-content:center}}
    .brand .dot img{{height:56px}}
    .hd{{font-size:150px;letter-spacing:-4px}}
    .hd em{{color:{"var(--forest)" if theme == "lime" else "var(--lime)"};text-decoration:{"underline" if theme == "lime" else "none"}}}
    .chip{{display:inline-block;background:{chip_bg};color:{chip_fg};font-size:38px;font-weight:800;padding:18px 30px;border-radius:14px;margin-top:40px}}
    .cta{{background:{cta_bg};color:{cta_fg};font-size:46px;padding:30px 52px}}
    .small{{font-size:32px;font-weight:700;margin-top:22px}}
    """
    chip = f"<span class='chip'>{t(s['chip'])}</span>" if s.get("chip") else ""
    body = f"""<div class='ad'><div class='wrap'>
      <div class='brand'><span class='dot'><img src='{ICON}'></span>Fresher Gardens</div>
      <div><h1 class='hd'>{t(s['headline'])}</h1>{chip}</div>
      <div><div class='pill cta'>{t(s.get('cta', 'Show me my price'))} <span>&rarr;</span></div><p class='small'>{t(s.get('small'))}</p></div>
    </div></div>"""
    return page(fmt, body, css)


LAYOUTS = {f.__name__: f for f in (text_thread, callout_photo, before_after, face_guarantee, price_shock, text_colour)}


def main(batch_file):
    batch = json.loads(Path(batch_file).read_text())
    OUT.mkdir(exist_ok=True)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fmt, f in FORMATS.items():
            pg = b.new_page(viewport={"width": f["w"], "height": f["h"]})
            for s in batch["ads"]:
                if not re.fullmatch(r"[a-z0-9-]{3,60}", s["id"]):
                    raise SystemExit(f"Bad id {s['id']!r}: use lowercase letters, digits and hyphens")
                tmp = OUT / f"_{s['id']}_{fmt}.html"
                tmp.write_text(LAYOUTS[s["layout"]](s, fmt))
                pg.goto(tmp.as_uri()); pg.wait_for_load_state("networkidle"); pg.evaluate("document.fonts.ready")
                png = OUT / f"{s['id']}_{fmt}.png"
                pg.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": f["w"], "height": f["h"]})
                tmp.unlink()
                made.append(png)
            pg.close()
        b.close()
    # contact sheet to eyeball: feed row on top, stories below
    from PIL import Image
    ids = [s["id"] for s in batch["ads"]]
    W = 360
    sheet = Image.new("RGB", (len(ids) * (W + 12), 450 + 640 + 20), "white")
    for i, a in enumerate(ids):
        sheet.paste(Image.open(OUT / f"{a}_feed.png").convert("RGB").resize((W, 450)), (i * (W + 12), 0))
        sheet.paste(Image.open(OUT / f"{a}_story.png").convert("RGB").resize((W, 640)), (i * (W + 12), 470))
    sheet_path = OUT / f"_sheet_{batch.get('batch', 'batch')}.jpg"
    sheet.save(sheet_path, quality=85)
    for m in made:
        print("wrote", m.relative_to(ROOT))
    print("sheet", sheet_path.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1])
