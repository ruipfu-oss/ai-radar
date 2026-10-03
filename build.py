#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AI 前沿雷达：从 AI HOT 精选池采集最新 AI 资讯，生成网页。

产出两个页面：
  index.html        完整快照页，由 GitHub Actions 每日 06:00（北京时间）重建
  phone/index.html  手机端壳页：打开时自动拉取云端最新数据，拉不到就回退内置快照
                    （供 WorkBuddy「发布为应用」使用，发布一次后无需重复发布）

用法:
    python build.py            # 采集并重建两个页面
    python build.py --count 58 # 指定条数

数据源: AI HOT 公开只读 API (https://aihot.news/api/v1/items)
  注：2026-10-31 后旧域名 aihot.virxact.com 可能停用，故统一使用新域名 aihot.news
  - 优先取「精选池」(mode=selected) 近 7 天条目，按官方时间轴倒序
  - 精选池不足时用「全量池」(mode=all) 补足，并在页面上标注
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://aihot.news/api/v1/items"
UA = "aihot-skill/1.2.1 (+https://aihot.news/aihot-skill/)"
CST = timezone(timedelta(hours=8))  # 北京时间，中国无夏令时
TARGET = 58
BASE = os.path.dirname(os.path.abspath(__file__))

CATEGORY_CN = {
    "ai-models": "模型发布",
    "ai-products": "产品与应用",
    "industry": "行业动态",
    "paper": "论文研究",
    "tip": "技术实践",
}


def fetch(mode="selected", window="7d", limit=50, cursor=None):
    params = {"mode": mode, "window": window, "limit": str(limit)}
    if cursor:
        params["cursor"] = cursor
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def collect(target=TARGET):
    """按时间倒序采集，优先精选池；不足则用全量池补足。"""
    picked, seen = [], set()

    def add(items, pool):
        for it in items:
            if it["id"] in seen or len(picked) >= target:
                continue
            seen.add(it["id"])
            it["_pool"] = pool
            picked.append(it)

    # 1) 精选池，最多翻 3 页
    cursor = None
    for _ in range(3):
        if len(picked) >= target:
            break
        data = fetch(mode="selected", window="7d", limit=50, cursor=cursor)
        add(data.get("items", []), "selected")
        page = data.get("page") or {}
        if not page.get("hasMore") or not page.get("nextCursor"):
            break
        cursor = page["nextCursor"]

    # 2) 精选池不足，用全量池补足（页面会标注）
    if len(picked) < target:
        add(fetch(mode="all", window="7d", limit=50).get("items", []), "all")

    return picked[:target]


def parse_time(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize(raw):
    out = []
    for idx, it in enumerate(raw, 1):
        pub = parse_time(it.get("publishedAt"))
        disc = parse_time(it.get("discoveredAt"))
        show = pub or disc
        out.append({
            "no": idx,
            "id": it.get("id", ""),
            "title": it.get("title", "").strip(),
            "originalTitle": (it.get("originalTitle") or "").strip(),
            "summary": (it.get("summary") or "").strip(),
            "source": (it.get("source") or {}).get("name", "未标注来源"),
            "category": it.get("category") or "other",
            "categoryCn": CATEGORY_CN.get(it.get("category"), "其他"),
            "score": it.get("score"),
            "reason": (it.get("reason") or "").strip(),
            "publishedAt": pub.astimezone(CST).strftime("%Y-%m-%d %H:%M") if pub else "",
            "discoveredAt": disc.astimezone(CST).strftime("%Y-%m-%d %H:%M") if disc else "",
            "timeNote": "原文发布时间" if pub else "AI HOT 收录时间（原文未提供发布时间）",
            "sortKey": show.timestamp() if show else 0,
            "urlOriginal": (it.get("links") or {}).get("original", ""),
            "urlDetail": (it.get("links") or {}).get("aihot", ""),
            "pool": it.get("_pool", "selected"),
        })
    out.sort(key=lambda x: x["sortKey"], reverse=True)
    for i, it in enumerate(out, 1):
        it["no"] = i
    return out


TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 前沿雷达 · 最新 AI 发展动态 $count 条</title>
<style>
  :root{
    --bg:#f5f6f8; --card:#ffffff; --line:#e3e6ea; --text:#16191d;
    --muted:#5f6772; --accent:#1f5eff; --accent-soft:#eef3ff;
    --tag:#f0f2f5; --shadow:0 1px 2px rgba(16,24,40,.06),0 4px 12px rgba(16,24,40,.04);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font-family:"PingFang SC","Microsoft YaHei","Hiragino Sans GB",system-ui,-apple-system,"Segoe UI",sans-serif;
    font-size:15px;line-height:1.65;}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
  header.top{background:linear-gradient(135deg,#ffffff,#f2f6ff);border:1px solid var(--line);
    border-radius:16px;padding:26px 28px;box-shadow:var(--shadow);margin-bottom:20px}
  h1{margin:0 0 8px;font-size:26px;letter-spacing:-.3px}
  .sub{color:var(--muted);font-size:14px}
  .stats{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
  .stat{background:#fff;border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:13px;color:var(--muted)}
  .stat b{color:var(--text);font-size:16px;margin-right:4px}
  .syncbar{display:none;margin-top:14px;padding:9px 14px;border-radius:10px;font-size:13px;
    background:#eefaf1;border:1px solid #c9ecd4;color:#256f43}
  .syncbar b{color:#14532d}
  .syncbar.off{background:#fff7ed;border-color:#fcd9b6;color:#9a5b12}
  .syncbar.off b{color:#7c3d05}
  .toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 18px}
  .toolbar input[type=search]{flex:1;min-width:220px;padding:9px 14px;border:1px solid var(--line);
    border-radius:10px;background:#fff;font-size:14px;color:var(--text)}
  .chips{display:flex;flex-wrap:wrap;gap:8px}
  .chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 14px;
    font-size:13px;cursor:pointer;color:var(--muted);user-select:none}
  .chip.active{background:var(--accent-soft);border-color:#c3d5ff;color:var(--accent);font-weight:600}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 18px 14px;
    box-shadow:var(--shadow);display:flex;flex-direction:column}
  .card:hover{border-color:#cfd8e6}
  .meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);margin-bottom:8px;flex-wrap:wrap}
  .no{font-variant-numeric:tabular-nums;background:var(--tag);border-radius:6px;padding:1px 7px;color:var(--muted)}
  .tag{background:var(--accent-soft);color:var(--accent);border-radius:6px;padding:1px 8px;font-size:12px}
  .tag.alt{background:#f3f0ff;color:#6a48d6}
  h3{margin:0 0 8px;font-size:16.5px;line-height:1.45}
  .sum{margin:0 0 12px;font-size:14px;color:#33383f}
  .foot{margin-top:auto;display:flex;align-items:center;justify-content:space-between;gap:8px;
    padding-top:10px;border-top:1px dashed var(--line);font-size:12.5px;color:var(--muted)}
  .btns{display:flex;gap:8px;margin-top:10px}
  .btn{border:1px solid var(--line);background:#fff;border-radius:8px;padding:6px 12px;font-size:13px;
    cursor:pointer;color:var(--accent)}
  .btn:hover{background:var(--accent-soft)}
  .btn.solid{background:var(--accent);border-color:var(--accent);color:#fff}
  .btn.solid:hover{background:#1a4fd8}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .detail{display:none;margin-top:12px;padding:12px 14px;background:#fafbfc;border:1px solid var(--line);
    border-radius:10px;font-size:13.5px;color:#33383f}
  .detail.open{display:block}
  .detail dl{margin:0;display:grid;grid-template-columns:78px 1fr;gap:6px 10px}
  .detail dt{color:var(--muted);font-size:12.5px}
  .detail dd{margin:0;word-break:break-all}
  .empty{padding:48px;text-align:center;color:var(--muted)}
  footer{margin-top:32px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
  @media(max-width:640px){.wrap{padding:16px 12px 48px}h1{font-size:21px}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <h1>AI 前沿雷达 · 最新 AI 发展动态</h1>
    <div class="sub">从 AI HOT 权威信源池自动采集，每条含摘要、来源、日期，可查看源头原文与详细说明。每日 06:00（北京时间）自动更新。</div>
    <div class="stats">
      <div class="stat"><b id="cnt">$count</b>条动态</div>
      <div class="stat"><b id="srcn">$sources</b>个信源</div>
      <div class="stat">时间窗 <b>近 7 天</b></div>
      <div class="stat">更新于 <b id="upd">$updated</b></div>
    </div>
    <div class="syncbar" id="sync">正在同步云端最新数据…</div>
  </header>

  <div class="toolbar">
    <input type="search" id="q" placeholder="搜索标题、摘要、来源…">
    <div class="chips" id="chips"></div>
  </div>

  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" style="display:none">没有匹配的条目，试试其它关键词。</div>

  <footer>
    数据来源：AI HOT（aihot.virxact.com）公开只读 API 精选池与全量池，条目均附带第三方原文链接；
    标题与摘要由 AI HOT 编辑整理，引用具体数字、政策或原话前请回原文核对。<br>
    本页由本地脚本 build.py 自动生成：$updated · 下次自动更新：次日 06:00。
  </footer>
</div>

<script id="payload" type="application/json">$payload</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const chips = document.getElementById('chips');
let activeCat = 'all', keyword = '';

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}

function renderChips(){
  const cats = [['all','全部']].concat([...new Set(DATA.map(d=>d.category))]
    .map(c=>[c, (DATA.find(d=>d.category===c)||{}).categoryCn || '其他']));
  chips.innerHTML = cats.map(([c,n])=>
    `<span class="chip${c===activeCat?' active':''}" data-c="${esc(c)}">${esc(n)}</span>`).join('');
  chips.querySelectorAll('.chip').forEach(el=>el.onclick=()=>{activeCat=el.dataset.c;renderChips();render();});
}

function card(d){
  const hasOrig = !!d.urlOriginal;
  return `<article class="card" data-cat="${esc(d.category)}">
    <div class="meta">
      <span class="no">#${String(d.no).padStart(2,'0')}</span>
      <span class="tag${d.category==='paper'||d.category==='tip'?' alt':''}">${esc(d.categoryCn)}</span>
      ${d.pool==='all'?'<span class="no">全量池</span>':''}
    </div>
    <h3>${esc(d.title)}</h3>
    <p class="sum">${esc(d.summary)}</p>
    <div class="btns">
      <button class="btn${hasOrig?' solid':''}" ${hasOrig?'':'disabled'} onclick="window.open('${esc(d.urlOriginal)}','_blank')">查看原文</button>
      <button class="btn" onclick="toggle(this)">详细说明</button>
    </div>
    <div class="detail">
      <dl>
        <dt>来源</dt><dd>${esc(d.source)}</dd>
        <dt>日期</dt><dd>${esc(d.publishedAt||d.discoveredAt)} <span style="color:#5f6772">（${esc(d.timeNote)}）</span></dd>
        ${d.originalTitle?`<dt>原标题</dt><dd>${esc(d.originalTitle)}</dd>`:''}
        ${d.reason?`<dt>入选理由</dt><dd>${esc(d.reason)}</dd>`:''}
        ${d.score!=null?`<dt>热度分</dt><dd>${esc(d.score)}</dd>`:''}
        <dt>原文链接</dt><dd>${hasOrig?`<a href="${esc(d.urlOriginal)}" target="_blank" rel="noopener">${esc(d.urlOriginal)}</a>`:'暂未提供'}</dd>
        <dt>详情归档</dt><dd>${d.urlDetail?`<a href="${esc(d.urlDetail)}" target="_blank" rel="noopener">${esc(d.urlDetail)}</a>`:'暂未提供'}</dd>
      </dl>
    </div>
    <div class="foot"><span>${esc(d.source)}</span><span>${esc(d.publishedAt||d.discoveredAt)}</span></div>
  </article>`;
}

function render(){
  const kw = keyword.trim().toLowerCase();
  const list = DATA.filter(d=>{
    if(activeCat!=='all' && d.category!==activeCat) return false;
    if(!kw) return true;
    return (d.title+' '+d.summary+' '+d.source+' '+(d.originalTitle||'')).toLowerCase().includes(kw);
  });
  grid.innerHTML = list.map(card).join('');
  empty.style.display = list.length? 'none':'block';
}

function toggle(btn){
  const box = btn.closest('.card').querySelector('.detail');
  box.classList.toggle('open');
  btn.textContent = box.classList.contains('open') ? '收起说明' : '详细说明';
}

document.getElementById('q').addEventListener('input', e=>{keyword=e.target.value;render();});
renderChips(); render();
$syncjs
</script>
</body>
</html>
"""


SYNC_JS = r"""
/* 手机端壳页：优先拉取云端最新数据，失败则回退内置快照 */
(function(){
  var bar = document.getElementById('sync');
  if(bar){ bar.style.display='block'; bar.innerHTML='正在同步云端最新数据…'; }
  var SNAPSHOT = "$updated";
  var SOURCES = [
    "https://ruipfu-oss.github.io/ai-radar/data/latest.json",
    "https://cdn.jsdelivr.net/gh/ruipfu-oss/ai-radar@main/data/latest.json"
  ];
  function fail(){
    if(!bar) return;
    bar.className = 'syncbar off';
    bar.innerHTML = '云端暂不可达，当前显示 <b>' + SNAPSHOT + '</b> 的内置快照';
  }
  (async function(){
    for(var i=0;i<SOURCES.length;i++){
      try{
        var r = await fetch(SOURCES[i] + '?t=' + Date.now(), {cache:'no-store'});
        if(!r.ok) continue;
        var j = await r.json();
        if(j && j.items && j.items.length){
          DATA.length = 0;
          j.items.forEach(function(x){ DATA.push(x); });
          document.getElementById('upd').textContent = j.updatedAt || '—';
          document.getElementById('cnt').textContent = j.items.length;
          document.getElementById('srcn').textContent =
            new Set(j.items.map(function(x){ return x.source; })).size;
          renderChips(); render();
          if(bar){
            bar.className = 'syncbar';
            bar.innerHTML = '已同步云端最新数据 · 云端更新于 <b>' + (j.updatedAt || '—') + '</b>';
          }
          return;
        }
      }catch(e){}
    }
    fail();
  })();
})();
"""


def render_html(items, updated, mode="web"):
    payload = json.dumps(items, ensure_ascii=False).replace("<", "\\u003c")
    return (TPL.replace("$payload", payload)
               .replace("$count", str(len(items)))
               .replace("$sources", str(len({i["source"] for i in items})))
               .replace("$syncjs", SYNC_JS if mode == "phone" else "")
               .replace("$updated", updated))


def main():
    count = TARGET
    if "--count" in sys.argv:
        count = int(sys.argv[sys.argv.index("--count") + 1])

    raw = collect(count)
    items = normalize(raw)
    if len(items) < count:
        print(f"警告：仅采集到 {len(items)} 条，目标 {count} 条")

    updated = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
    out_json = os.path.join(BASE, "data", "latest.json")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    # 1) 云端 Pages 主页面（完整快照）
    with open(os.path.join(BASE, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_html(items, updated, "web"))

    # 2) 手机端壳页（发布一次即可长期自动同步云端）
    phone_dir = os.path.join(BASE, "phone")
    os.makedirs(phone_dir, exist_ok=True)
    with open(os.path.join(phone_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_html(items, updated, "phone"))

    # 3) 原始数据快照，供手机端拉取与次日对比
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"updatedAt": updated, "count": len(items), "items": items},
                  f, ensure_ascii=False, indent=2)

    print(f"已生成 index.html / phone/index.html：{len(items)} 条，"
          f"{len({i['source'] for i in items})} 个信源，更新时间 {updated}")


if __name__ == "__main__":
    main()
