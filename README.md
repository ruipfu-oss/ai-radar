# AI 前沿雷达

每天自动采集 **58 条** AI 领域最新动态，生成可直接在手机上查看的网页。

## 查看地址

| 入口 | 地址 | 说明 |
|---|---|---|
| 网页版（推荐手机浏览器收藏） | https://ruipfu-oss.github.io/ai-radar/ | 云端每日 06:00 自动重建 |
| 原始数据 | https://ruipfu-oss.github.io/ai-radar/data/latest.json | JSON，供二次使用 |

手机端另有一个通过 WorkBuddy 发布的应用入口，打开时自动拉取上面的最新 JSON，
云端更新后无需重新发布即可看到新内容（网络不通时回退到发布时内置的那份快照）。

## 运行方式

- **自动**：GitHub Actions 每日 UTC 22:00（北京时间次日 06:00）执行 `.github/workflows/daily.yml`
- **手动**：仓库页面 → Actions → AI Radar Daily → Run workflow

采集或校验失败时不会提交，线上页面保持上一版内容不变。

## 数据来源与规则

- 数据源：AI HOT 公开只读 API `https://aihot.news/api/v1/items`
- 采集顺序：优先「精选池」近 7 天条目（按官方时间轴倒序），不足时用「全量池」补足，
  全量池条目在页面上标有「全量池」字样以作区分
- 每条包含：标题、摘要、来源名称、日期、原文链接、详细说明（原标题 / 入选理由 / 热度分 / 归档链接）
- 日期口径：原文发布时间；原文未提供时回退为 AI HOT 收录时间，并在页面上注明

## 本地运行

```bash
python build.py            # 采集并重建 index.html、phone/index.html、data/latest.json
python build.py --count 58 # 指定条数
```

## 文件说明

| 文件 | 作用 |
|---|---|
| `build.py` | 采集 + 渲染，唯一的可执行入口，无任何第三方依赖 |
| `index.html` | 云端 Pages 主页面（完整快照） |
| `phone/index.html` | 手机端壳页，打开时自动同步云端最新数据 |
| `data/latest.json` | 数据快照，含 `updatedAt`，供手机端与次日对比使用 |
| `.github/workflows/daily.yml` | 每日定时任务 |

## 注意

标题与摘要由 AI HOT 编辑整理，引用具体数字、价格、评测分数或政策原话前，
请点击「查看原文」回到出处核对。
