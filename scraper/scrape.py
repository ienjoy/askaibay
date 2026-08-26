# -*- coding: utf-8 -*-
"""
湾区租房论坛抓取脚本
抓取 bay123.com 和 chineseinsfbay.com 的租房帖子，
按城市/邮编近似定位，合并进 docs/data.json 供地图页面使用。

在 GitHub Actions 中每日运行；也可本地运行：python scraper/scrape.py
"""
import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

# ---------------- 配置 ----------------
BAY123_PAGES = 8          # bay123 抓取的列表页数（每页约30帖）
CIS_PAGES = 12            # chineseinsfbay 抓取的列表页数（每页约15帖）
MAX_NEW_DETAILS = 250     # 每次运行最多抓取的"新帖"详情数（老帖直接复用缓存）
RETENTION_DAYS = 30       # 超过30天没在列表页出现过的房源从地图移除
MAX_POST_AGE_DAYS = 120   # 发帖时间超过这么久的帖子不上地图（滤掉置顶广告和陈年老帖）
DELAY = 0.6               # 每次请求间隔（秒），对论坛保持礼貌
TIMEOUT = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; rental-map-bot; personal noncommercial use)"
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "docs", "data.json")
# 已抓过但没上地图的帖子（重复发帖 / 太旧 / 定位不出来），记下来避免每天重抓详情
SEEN_PATH = os.path.join(ROOT, "state", "seen.json")

# ---------------- 地理定位表（近似坐标） ----------------
CITY = {
 'San Francisco': (37.7599, -122.4148), '三藩市': (37.7599, -122.4148), '旧金山': (37.7599, -122.4148), '舊金山': (37.7599, -122.4148),
 'Sunset': (37.7500, -122.4870), '日落区': (37.7500, -122.4870), '列治文区': (37.7800, -122.4650), 'Excelsior': (37.7244, -122.4260),
 '唐人街': (37.7941, -122.4078), '中国城': (37.7941, -122.4078), 'SFSU': (37.7219, -122.4782),
 'Daly City': (37.6879, -122.4702), 'South San Francisco': (37.6547, -122.4077), 'San Bruno': (37.6305, -122.4111),
 'Millbrae': (37.5985, -122.3872), 'Burlingame': (37.5779, -122.3480), 'San Mateo': (37.5630, -122.3255), '聖馬刁': (37.5630, -122.3255), '圣马刁': (37.5630, -122.3255),
 'Foster City': (37.5585, -122.2711), 'Redwood City': (37.4852, -122.2364), 'Menlo Park': (37.4530, -122.1817), 'Belmont': (37.5202, -122.2758),
 'Palo Alto': (37.4419, -122.1430), 'East Palo Alto': (37.4688, -122.1411), 'Stanford': (37.4275, -122.1697), 'Los Altos': (37.3852, -122.1141),
 'Mountain View': (37.3861, -122.0839), 'MTV': (37.3861, -122.0839), 'Sunnyvale': (37.3688, -122.0363), 'Cupertino': (37.3230, -122.0322),
 'Santa Clara': (37.3541, -121.9552), 'San Jose': (37.3382, -121.8863), '圣何塞': (37.3382, -121.8863), '圣荷西': (37.3382, -121.8863),
 '聖荷西': (37.3382, -121.8863), '圣荷塞': (37.3382, -121.8863), '聖何塞': (37.3382, -121.8863), '圣活塞': (37.3382, -121.8863),
 'NSJ': (37.4100, -121.9300), 'SJSU': (37.3352, -121.8811), 'Milpitas': (37.4323, -121.8996), 'Campbell': (37.2872, -121.9500),
 'Saratoga': (37.2638, -122.0230), 'Los Gatos': (37.2358, -121.9624),
 'Fremont': (37.5485, -121.9886), '弗里蒙特': (37.5485, -121.9886), '弗蒙': (37.5485, -121.9886), 'Newark': (37.5297, -122.0402),
 'Union City': (37.5934, -122.0439), 'Hayward': (37.6688, -122.0808), 'San Leandro': (37.7249, -122.1561), 'San Lorenzo': (37.6810, -122.1244),
 'Castro Valley': (37.6941, -122.0864), 'Oakland': (37.8044, -122.2712), '奥克兰': (37.8044, -122.2712), '屋仑': (37.8044, -122.2712), '屋伦': (37.8044, -122.2712),
 'Alameda': (37.7652, -122.2416), 'Berkeley': (37.8715, -122.2730), '伯克利': (37.8715, -122.2730), '柏克利': (37.8715, -122.2730), 'Albany': (37.8869, -122.2977),
 'El Cerrito': (37.9161, -122.3108), 'Richmond': (37.9358, -122.3477), 'San Pablo': (37.9621, -122.3455), 'Concord': (37.9780, -122.0311),
 'Walnut Creek': (37.9101, -122.0652), 'Dublin': (37.7022, -121.9358), 'Pleasanton': (37.6624, -121.8747), 'Livermore': (37.6819, -121.7680),
 'San Ramon': (37.7799, -121.9780), 'Emeryville': (37.8313, -122.2852), 'Sacramento': (38.5816, -121.4944),
 'Morgan Hill': (37.1305, -121.6544), 'Gilroy': (37.0058, -121.5683), 'Vallejo': (38.1041, -122.2566), 'Santa Cruz': (36.9741, -122.0308),
}
ZIP = {
 '94112': (37.7200, -122.4430), '94108': (37.7920, -122.4080), '94133': (37.8010, -122.4100), '94118': (37.7810, -122.4620),
 '94124': (37.7280, -122.3880), '94127': (37.7350, -122.4590), '94134': (37.7190, -122.4130),
 '94303': (37.4550, -122.1290), '94306': (37.4190, -122.1310), '94061': (37.4610, -122.2360), '94402': (37.5380, -122.3320),
 '94523': (37.9530, -122.0740), '94513': (37.9320, -121.6960), '94565': (38.0170, -121.8890), '94022': (37.4020, -122.1370),
 '94040': (37.3800, -122.0870), '94043': (37.4060, -122.0770),
 '94085': (37.3890, -122.0180), '94086': (37.3720, -122.0230), '94087': (37.3520, -122.0360), '94089': (37.4060, -122.0110),
 '95002': (37.4270, -121.9750), '95014': (37.3180, -122.0450), '95050': (37.3520, -121.9530), '95051': (37.3480, -121.9830),
 '95054': (37.3930, -121.9640), '95035': (37.4360, -121.8920),
 '95110': (37.3420, -121.9000), '95111': (37.2830, -121.8270), '95112': (37.3440, -121.8830), '95116': (37.3500, -121.8530),
 '95117': (37.3110, -121.9620), '95121': (37.3050, -121.8100), '95122': (37.3290, -121.8340), '95124': (37.2570, -121.9230),
 '95127': (37.3690, -121.8210), '95128': (37.3160, -121.9360), '95129': (37.3060, -121.9990), '95131': (37.3870, -121.8980),
 '95132': (37.4020, -121.8580), '95133': (37.3720, -121.8600), '95134': (37.4130, -121.9450), '95135': (37.2970, -121.7570),
 '95136': (37.2700, -121.8500), '95148': (37.3300, -121.7920), '95832': (38.4680, -121.4930), '95377': (37.6600, -121.4520),
 '94536': (37.5620, -122.0080), '94538': (37.5270, -121.9640), '94539': (37.5100, -121.9200), '94555': (37.5730, -122.0470),
 '94560': (37.5300, -122.0330), '94587': (37.5930, -122.0500),
 '94541': (37.6740, -122.0870), '94542': (37.6570, -122.0410), '94544': (37.6350, -122.0570), '94545': (37.6350, -122.1030),
 '94577': (37.7220, -122.1620), '94579': (37.6930, -122.1520), '94580': (37.6790, -122.1300), '94606': (37.7930, -122.2440),
 '94703': (37.8640, -122.2760), '94597': (37.9290, -122.0710), '94598': (37.9130, -122.0270), '94588': (37.6930, -121.9000),
}
CITIES = list(CITY.keys())


def norm_date(raw):
    """把 '2026-8-21' / '2026/08/10' / '2026-8-21 15:20' 统一成 ISO 'YYYY-MM-DD'，
    解析不出来就返回空串。"""
    if not raw:
        return ""
    m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", raw)
    if not m:
        return ""
    y, mo, dd = (int(x) for x in m.groups())
    try:
        return datetime(y, mo, dd).date().isoformat()
    except ValueError:
        return ""


def too_old(iso_date, today):
    """发帖日期过老 → True。日期解析不出来时按"不过滤"处理。"""
    if not iso_date:
        return False
    try:
        return (today - datetime.fromisoformat(iso_date).date()).days > MAX_POST_AGE_DAYS
    except ValueError:
        return False


def http_get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def extract_city(hay):
    hay_low = hay.lower()
    best_pos, best_city = 10 ** 9, ""
    for c in CITIES:
        i = hay_low.find(c.lower())
        if 0 <= i < best_pos:
            best_pos, best_city = i, c
    return best_city


# 租金写法五花八门：$850 / ＄850 / $1,200 / 850元 / 租金1200 / 1200一个月
PRICE_PATTERNS = [
    r"[$＄﹩]\s?(?<!\d)(\d{1,2},\d{3}|\d{3,4})(?!\d)",
    r"(?<!\d)(\d{3,4})(?!\d)\s*(?:元|刀|美金|美元|块)",
    r"(?:租金|月租|房租|价格|价钱|rent)\s*[:：是为]?\s*[$＄]?\s*(?<!\d)(\d{3,4})(?!\d)",
    r"(?<!\d)(\d{3,4})(?!\d)\s*(?:/|每|一)\s*(?:月|mo\b|month)",
]
PRICE_MIN, PRICE_MAX = 200, 9000   # 越界的多半是邮编、电话、面积、年份


def extract_price(full):
    """返回 (原文片段, 数值)；识别不出来返回 ("", None)。"""
    for pat in PRICE_PATTERNS:
        for m in re.finditer(pat, full, re.I):
            v = int(m.group(1).replace(",", ""))
            if PRICE_MIN <= v <= PRICE_MAX:
                return m.group(0).strip(), v
    return "", None


def extract_common(title, text):
    full = title + " " + text
    price, pv = extract_price(full)
    m = re.search(r"\b9[45]\d{3}\b", full)
    zc = m.group(0) if m else ""
    city = extract_city(title + " | " + text[:600])
    return price, pv, zc, city


# 标题里出现这些字样说明房子已经租掉了，没必要占地图
RENTED_RE = re.compile(r"已\s*(?:租|出租|租出|租掉)|租\s*出\s*了|已\s*停\s*租|rented", re.I)


def dedup_key(p):
    """同一房源被反复发帖（不同帖子 ID、内容一模一样）时的归并键。
    标点/空格差异（半角逗号 vs 全角逗号之类）不应该算不同房源。"""
    title = re.sub(r"[^\w\u4e00-\u9fff]+", "", (p.get("t") or "")).lower()
    return (title, p.get("pv"), p.get("z", ""), p.get("c", ""))


def dedup(points):
    """同一内容被反复发帖时只保留最新的一条。"""
    best = {}
    for p in points:
        k = dedup_key(p)
        cur = best.get(k)
        if cur is None or (p.get("d") or "", p["id"]) > (cur.get("d") or "", cur["id"]):
            best[k] = p
    return list(best.values())


def jitter(uid, scale):
    h = hashlib.md5(uid.encode()).digest()
    return (h[0] / 255 - 0.5) * scale, (h[1] / 255 - 0.5) * scale


def locate(uid, zc, city):
    if zc and zc in ZIP:
        base, level, scale = ZIP[zc], "zip", 0.008
    elif city and city in CITY:
        base, level, scale = CITY[city], "city", 0.018
    else:
        return None
    dx, dy = jitter(uid, scale)
    return round(base[0] + dx, 5), round(base[1] + dy, 5), level


# ---------------- bay123.com (Discuz) ----------------
def bay123_list_ids():
    ids = []
    seen = set()
    for p in range(1, BAY123_PAGES + 1):
        try:
            html = http_get(f"http://www.bay123.com/forum-40-{p}.html")
        except Exception as e:
            print(f"[bay123] list page {p} failed: {e}", file=sys.stderr)
            continue
        # 只取 normalthread_*，跳过 stickthread_*（置顶广告/公告常年不动）
        for m in re.finditer(r'id="normalthread_(\d+)"', html):
            tid = m.group(1)
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
        time.sleep(DELAY)
    return ids


def bay123_detail(tid):
    url = f"http://www.bay123.com/thread-{tid}-1-1.html"
    soup = BeautifulSoup(http_get(url), "html.parser")
    t = soup.select_one("#thread_subject")
    title = t.get_text(strip=True) if t else ""
    em = soup.select_one("em[id^=authorposton]")
    pub = ""
    if em:
        span = em.find("span")
        pub = (span.get("title") if span and span.get("title") else em.get_text()).replace("发表于", "").strip()
        pub = norm_date(pub)
    body = soup.select_one("td[id^=postmessage_], div[id^=postmessage_]")
    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)) if body else ""
    price, pv, zc, city = extract_common(title, text)
    return {"t": title[:60], "p": price, "pv": pv, "z": zc, "c": city, "d": pub, "u": url}


# ---------------- chineseinsfbay.com ----------------
def cis_list_ids():
    ids = []
    seen = set()
    for p in range(CIS_PAGES):
        url = ("https://www.chineseinsfbay.com/f/page_viewforum/f_5.html" if p == 0
               else f"https://www.chineseinsfbay.com/f/page_viewforum/f_5/start_{p * 15}.html")
        try:
            html = http_get(url)
        except Exception as e:
            print(f"[cis] list page {p} failed: {e}", file=sys.stderr)
            continue
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select(".topic_list_detail"):
            if row.select_one(".topic_list_11 span.sticky"):
                continue          # 置顶广告
            a = row.select_one(".topic_list_12 a[href*=page_viewtopic]")
            if not a:
                continue          # 分页等非帖子行
            m = re.search(r"t_(\d+)\.html", a.get("href", ""))
            if not m:
                continue
            tid = m.group(1)
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
        time.sleep(DELAY)
    return ids


def cis_detail(tid):
    url = f"https://www.chineseinsfbay.com/f/page_viewtopic/t_{tid}.html"
    html = http_get(url)
    soup = BeautifulSoup(html, "html.parser")
    t = soup.select_one(".topic_line_title")
    title = re.sub(r"回复|新帖", "", t.get_text(strip=True)).strip() if t else ""
    m = re.search(r"发布于[:：]\s*([\d/]+)", html)
    pub = norm_date(m.group(1) if m else "")
    body = soup.select_one(".post_body .real-content, p.real-content")
    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)) if body else ""
    price, pv, zc, city = extract_common(title, text)
    return {"t": title[:60], "p": price, "pv": pv, "z": zc, "c": city, "d": pub, "u": url}


# ---------------- 主流程 ----------------
def main():
    today = datetime.now(timezone.utc).date()
    # 读取已有数据（增量合并）
    existing = {}
    if os.path.exists(DATA_PATH):
        try:
            old = json.load(open(DATA_PATH, encoding="utf-8"))
            for pt in old.get("points", []):
                pt["d"] = norm_date(pt.get("d"))
                if too_old(pt["d"], today) or RENTED_RE.search(pt.get("t", "")):
                    continue      # 历史数据里的置顶广告/陈年老帖/已租帖，清理掉
                existing[pt["id"]] = pt
        except Exception as e:
            print(f"warn: cannot read existing data.json: {e}", file=sys.stderr)

    seen_ledger = {}
    if os.path.exists(SEEN_PATH):
        try:
            seen_ledger = json.load(open(SEEN_PATH, encoding="utf-8"))
        except Exception as e:
            print(f"warn: cannot read seen.json: {e}", file=sys.stderr)

    sources = [
        ("bay123", bay123_list_ids, bay123_detail),
        ("cis", cis_list_ids, cis_detail),
    ]
    new_fetched, reused, failed = 0, 0, 0
    skipped_old, skipped_noloc, skipped_known, skipped_rented = 0, 0, 0, 0

    for src, list_fn, detail_fn in sources:
        try:
            ids = list_fn()
        except Exception as e:
            print(f"[{src}] listing failed entirely: {e}", file=sys.stderr)
            continue
        print(f"[{src}] {len(ids)} threads on list pages")
        for tid in ids:
            uid = f"{src}:{tid}"
            if uid in existing:
                existing[uid]["seen"] = str(today)   # 仍在列表上，刷新最后出现时间
                reused += 1
                continue
            if uid in seen_ledger:
                seen_ledger[uid] = str(today)        # 抓过且已判定不上地图，不再重抓
                skipped_known += 1
                continue
            if new_fetched >= MAX_NEW_DETAILS:
                continue
            try:
                d = detail_fn(tid)
            except Exception as e:
                failed += 1
                print(f"[{src}] {tid} failed: {e}", file=sys.stderr)
                time.sleep(DELAY)
                continue
            loc = locate(uid, d["z"], d["c"])
            new_fetched += 1
            time.sleep(DELAY)
            if RENTED_RE.search(d["t"]):
                skipped_rented += 1
                seen_ledger[uid] = str(today)
                continue  # 标题里写了"已租"
            if too_old(d["d"], today):
                skipped_old += 1
                seen_ledger[uid] = str(today)
                continue  # 发帖太久（置顶广告、被顶起来的老帖）不上地图
            if not loc:
                skipped_noloc += 1
                seen_ledger[uid] = str(today)
                continue  # 无法定位的帖子不上地图
            lat, lng, level = loc
            existing[uid] = {
                "id": uid, "s": src, "t": d["t"], "p": d["p"],
                "pv": d["pv"],
                "z": d["z"], "c": d["c"], "d": d["d"], "u": d["u"],
                "lat": lat, "lng": lng, "lv": level,
                "seen": str(today),
            }

    # 淘汰长期没出现的旧房源
    cutoff = today - timedelta(days=RETENTION_DAYS)
    points = [p for p in existing.values()
              if datetime.fromisoformat(p.get("seen", "2000-01-01")).date() >= cutoff]
    candidates = points
    points = dedup(candidates)
    kept_ids = {p["id"] for p in points}
    for p in candidates:                       # 去重落选的帖子进账本，别再重抓
        if p["id"] not in kept_ids:
            seen_ledger[p["id"]] = str(today)

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "points": sorted(points, key=lambda p: (p.get("d") or "", p["id"]), reverse=True),
    }
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    json.dump(out, open(DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False)

    seen_ledger = {k: v for k, v in seen_ledger.items()
                   if datetime.fromisoformat(v).date() >= cutoff}
    os.makedirs(os.path.dirname(SEEN_PATH), exist_ok=True)
    json.dump(seen_ledger, open(SEEN_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, sort_keys=True)
    print(f"done: {len(points)} points on map | "
          f"fetched {new_fetched} new, reused {reused}, failed {failed}, "
          f"skipped {skipped_known} already-known | "
          f"dropped: {skipped_old} too old, {skipped_rented} rented, "
          f"{skipped_noloc} no location, {len(candidates) - len(points)} repeat posts")


if __name__ == "__main__":
    main()
