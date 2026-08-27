# 湾区租房地图（自动更新）

把 [bay123.com 湾区租房版](http://www.bay123.com/forum-40-1.html) 和
[chineseinsfbay.com 房屋出租版](https://www.chineseinsfbay.com/f/page_viewforum/f_5.html)
的租房帖子抓取下来，标在交互地图上。

**网站已上线：https://askaibay.com**

数据来自两条途径：GitHub Actions 每天自动抓 bay123；chineseinsfbay 被 Cloudflare 挡在
机房 IP 之外，需要你在自己电脑上跑一次 [`./update.sh`](#手动更新数据)（见下文）。

## 仓库结构

```
├── update.sh                    # 手动更新：抓取 → 更新数据 → 推送（平时用这个）
├── scraper/scrape.py            # 抓取脚本：抓两个论坛 → 定位 → 合并进 docs/data.json
├── scraper/reparse.py           # 一次性工具：提取规则变好后回填老点位（平时不用跑）
├── docs/index.html              # 地图页面（GitHub Pages 发布这个目录）
├── docs/data.json               # 房源数据（脚本自动维护，含 457 条已验证数据）
├── docs/CNAME                   # 自定义域名 askaibay.com
├── state/seen.json              # 抓过但没上地图的帖子清单，避免每天重抓
├── state/last_run.json          # 每次运行的健康状况，CI 用它判断要不要报警
├── .github/workflows/update.yml # 每日定时任务
└── requirements.txt
```

## 部署现状

已经部署好了，这一节只是记录当前配置，平时不用管。

| 项目 | 配置 |
|---|---|
| 仓库 | [ienjoy/bayarea-rental-map](https://github.com/ienjoy/bayarea-rental-map)（Public） |
| 网站 | https://askaibay.com |
| GitHub Pages | Settings → Pages：`main` 分支 `/docs` 目录 |
| 域名 | Namecheap，4 条 A 记录指向 GitHub Pages；`www` CNAME 指向主域名 |
| 定时任务 | 每天 UTC 14:30（加州早上 6:30/7:30）自动跑，只有 bay123 能抓到 |
| 访问统计 | Google Analytics 4，在 `docs/index.html` 顶部配置 |

> 域名的 MX 记录和 SPF TXT 记录是 Namecheap 的邮箱转发，跟网站无关，**不要删**。

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

## 手动更新数据

### 操作步骤

**1. 打开"终端"**

按 `Command + 空格`，输入 `终端` 或 `Terminal`，回车。

**2. 复制粘贴这两行，回车**

```bash
cd ~/github/bayarea-rental-map
./update.sh
```

（以后再更新只要按方向键 `↑` 就能翻出上次的命令，不用重新打字。）

**3. 等 1–3 分钟，看到这样的输出就是成功了**

```
同步远端…

开始抓取（1–3 分钟，请稍候）…
[bay123] 240 threads on list pages
[cis] 180 threads on list pages
done: 457 points on map | fetched 3 new, reused 255, failed 0, ...

推送到 GitHub…

完成：房源 456 → 457 条，约 1 分钟后 https://askaibay.com 生效。
```

**4. 一分钟后打开 https://askaibay.com 确认**

看右下角"数据更新于"那行的时间变成刚才的时间，就说明新数据上线了。
如果时间没变，多半是浏览器缓存，按 `Command + Shift + R` 强制刷新。

### 多久跑一次

想起来就跑，**没有硬性要求**。不跑也不会出问题：已有房源不会因为没更新而消失，
云端每天还会自动更新 bay123 的部分。如果你自己正在找房，隔一两天跑一次比较合适；
只是挂着给别人用，一周跑一两次也够。

### 可能遇到的情况

| 屏幕上出现 | 什么意思 | 怎么办 |
|---|---|---|
| `数据没有变化，无需推送。` | 论坛这段时间没有新帖 | 正常，不用管 |
| `cis 这次一条都没抓到` | 论坛那边暂时不通 | 过几小时再跑一次；已有房源不会被删 |
| `zsh: permission denied: ./update.sh` | 脚本丢了执行权限 | 跑一次 `chmod +x update.sh` |
| `同步失败` / `推送失败` | 网络不通或 GitHub 出问题 | 过一会儿重跑；实在不行跑 `git status` 看看 |
| 抓取脚本报错退出 | 论坛可能改版了 | 把屏幕上的报错信息发给 Claude |

脚本**只会提交房源数据文件**，你在这个目录里改的任何其它东西都不会被它带上去。
抓取失败时不会提交，所以不用担心把坏数据推上线。

### 为什么需要手动跑

chineseinsfbay 用 Cloudflare 挡掉了 GitHub Actions 所在的机房 IP（返回 200 但 body
为空，换 UA、加 header、带 cookie 全都没用），只有住宅网络能正常访问。云端的每日任务
照常跑，负责 bay123；cis 的新帖要靠你在自己电脑上跑 `update.sh` 才能进来。
某个论坛整个抓挂时，脚本不会淘汰它的房源，所以数据不会被悄悄删光。

## 本地预览

```bash
python -m http.server -d docs   # 打开 http://localhost:8000 看地图
```

在 localhost 打开时不会向 Google Analytics 上报，方便自己测试。

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
