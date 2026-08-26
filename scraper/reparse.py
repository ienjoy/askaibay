# -*- coding: utf-8 -*-
"""
重新解析 docs/data.json 里已有点位的详情页。

抓取脚本对已见过的帖子直接复用缓存、不再重新解析，所以当 scrape.py 的
提取规则（租金、邮编、城市）变好之后，老点位不会自动受益。这个脚本用来做
一次性回填，平时不需要跑，也不在 GitHub Actions 里运行。

    python scraper/reparse.py --missing-price   # 只重解析没识别出租金的点（默认）
    python scraper/reparse.py --all             # 全部重解析
"""
import json
import re
import sys
import time

import scrape


def main():
    mode = "--all" if "--all" in sys.argv else "--missing-price"
    data = json.load(open(scrape.DATA_PATH, encoding="utf-8"))
    points = data["points"]
    targets = points if mode == "--all" else [p for p in points if not p.get("pv")]
    print(f"{len(targets)} / {len(points)} 个点位待重解析（{mode}）")

    changed = failed = 0
    for i, p in enumerate(targets, 1):
        tid_m = re.search(r"(?:thread-|t_)(\d+)", p["u"])
        if not tid_m:
            continue
        try:
            d = (scrape.bay123_detail if p["s"] == "bay123" else scrape.cis_detail)(tid_m.group(1))
        except Exception as e:
            failed += 1
            print(f"  [{i}] {p['u']} 失败: {e}", file=sys.stderr)
            time.sleep(scrape.DELAY)
            continue

        before = (p.get("p"), p.get("pv"), p.get("z"), p.get("c"))
        p["t"], p["p"], p["pv"] = d["t"] or p["t"], d["p"], d["pv"]
        p["z"], p["c"] = d["z"] or p.get("z", ""), d["c"] or p.get("c", "")
        p["d"] = d["d"] or p.get("d", "")
        loc = scrape.locate(p["id"], p["z"], p["c"])
        if loc:
            p["lat"], p["lng"], p["lv"] = loc
        if (p.get("p"), p.get("pv"), p.get("z"), p.get("c")) != before:
            changed += 1
            if p.get("pv") and not before[1]:
                print(f"  [{i}] 补上租金 {p['p']} ← {p['t'][:30]}")
        time.sleep(scrape.DELAY)
        if i % 50 == 0:
            json.dump(data, open(scrape.DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  …已处理 {i}/{len(targets)}，中途存盘")

    json.dump(data, open(scrape.DATA_PATH, "w", encoding="utf-8"), ensure_ascii=False)
    priced = sum(1 for p in points if p.get("pv"))
    print(f"done: {changed} 个点位有更新，{failed} 个失败；"
          f"现在 {priced}/{len(points)} 个点位有租金")


if __name__ == "__main__":
    main()
