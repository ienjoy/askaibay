# 湾区租房地图（自动更新）

把 [bay123.com 湾区租房版](http://www.bay123.com/forum-40-1.html) 和
[chineseinsfbay.com 房屋出租版](https://www.chineseinsfbay.com/f/page_viewforum/f_5.html)
的租房帖子抓取下来，标在交互地图上。GitHub Actions 每天自动抓取新帖并更新地图。

## 仓库结构

```
├── scraper/scrape.py            # 抓取脚本：抓两个论坛 → 定位 → 合并进 docs/data.json
├── scraper/reparse.py           # 一次性工具：提取规则变好后回填老点位（平时不用跑）
├── docs/index.html              # 地图页面（GitHub Pages 发布这个目录）
├── docs/data.json               # 房源数据（脚本自动维护，含 457 条已验证数据）
├── state/seen.json              # 抓过但没上地图的帖子清单，避免每天重抓
├── .github/workflows/update.yml # 每日定时任务
└── requirements.txt
```

## 部署步骤（一次性，约 5 分钟）

1. **创建仓库**：GitHub 上新建一个 **Public** 仓库（Pages 免费版需要 Public），
   比如叫 `bayarea-rental-map`。

2. **上传代码**：在本地这个文件夹里执行：
   ```bash
   git init
   git add .
   git commit -m "初始提交"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/bayarea-rental-map.git
   git push -u origin main
   ```
   （或者直接在 GitHub 网页上 "uploading an existing file" 把文件拖上去，
   注意 `.github` 是隐藏文件夹，网页上传容易漏掉，推荐用命令行。）

3. **开启 GitHub Pages**：仓库 Settings → Pages →
   Source 选 "Deploy from a branch" → Branch 选 `main`、目录选 `/docs` → Save。
   一两分钟后地图就在 `https://<你的用户名>.github.io/bayarea-rental-map/` 上线。

4. **验证定时任务**：仓库 Actions 标签页 → 左侧"每日抓取更新租房地图" →
   "Run workflow" 手动跑一次。绿色对勾 = 成功；之后每天加州早上 6:30–7:30 自动运行。
   > 注意：fork 的仓库或长期无活动的仓库，GitHub 可能自动暂停定时任务，
   > Actions 页面出现提示时点一下 "Enable" 即可。

## 工作原理

- 每次运行抓 bay123 前 8 页 + chineseinsfbay 前 12 页的帖子列表；
  两个论坛的**置顶帖都会跳过**（那些常年不动的广告和公告不是房源）；
- **只对没见过的新帖**抓详情页（已有的直接复用，对论坛压力很小）；
  抓过但判定不上地图的帖子记在 `state/seen.json`，第二天不会重抓；
- 从标题和正文提取租金、邮编、城市，按邮编/城市近似定位（帖子一般不写门牌号）；
- 这几类帖子不上地图：
  - 发帖超过 120 天的（多半是被顶起来的老帖）；
  - 标题里写了"已租/已出租/rented"的；
  - 同一内容反复发帖的（只留最新一帖——实测有房东同一条广告发了 23 次）；
  - 邮编和城市都认不出来、没法定位的；
- 超过 30 天没在列表页出现的房源自动从地图移除；
- 结果写入 `docs/data.json`，有变化才 commit，Pages 自动重新发布。

地图页面上可以按租金区间、来源论坛、发帖时间（最近 7/14/30 天）筛选。

## 常用调整

都在 `scraper/scrape.py` 顶部的配置区：

| 参数 | 默认 | 说明 |
|---|---|---|
| `BAY123_PAGES` / `CIS_PAGES` | 8 / 12 | 每次扫描的列表页数 |
| `RETENTION_DAYS` | 30 | 房源在列表页消失后还保留几天 |
| `MAX_POST_AGE_DAYS` | 120 | 发帖超过这么久就不上地图 |
| `MAX_NEW_DETAILS` | 250 | 单次运行最多抓的新帖数 |
| `PRICE_MIN` / `PRICE_MAX` | 200 / 9000 | 合理租金范围，用来排除电话号码、面积等误识别 |

更新频率改 `.github/workflows/update.yml` 里的 cron 表达式（UTC 时间）。

## 本地测试

```bash
pip install -r requirements.txt
python scraper/scrape.py        # 更新 docs/data.json
python -m http.server -d docs   # 打开 http://localhost:8000 看地图
```

## 已知限制

- 位置是**邮编/城市级近似**，不是确切地址；
- 约四成帖子识别不出租金（很多帖子本来就写"面议"），这些点显示为灰色"未标价"；
- 论坛改版后选择器可能失效，表现为 Actions 运行成功但新增数量一直是 0，
  此时需要更新 `scrape.py` 里的解析逻辑；
- 仅供个人找房参考，请勿商用或高频抓取。

## 提取规则改好之后

`scrape.py` 对见过的帖子直接复用缓存，所以改进了租金/城市识别规则之后，
老点位不会自动受益。本地跑一次回填即可（会重新请求这些帖子的详情页，注意别频繁跑）：

```bash
python scraper/reparse.py --missing-price   # 只重解析没识别出租金的点
python scraper/reparse.py --all             # 全部重解析
```
