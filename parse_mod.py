# -*- coding: utf-8 -*-
"""拆标签（重写版）：支持「N个角色 A B」表头 + 外形/服装/动作 分类行 + 散文兜底"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
_cache = {}

def load_lib():
    if "lib" in _cache:
        return _cache["lib"]
    tags = json.load(open(os.path.join(HERE, "tags_cn.json"), encoding="utf-8"))["tags"]
    for fn in ("chars_extra.json",):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            try:
                tags = tags + json.load(open(p, encoding="utf-8"))
            except Exception:
                pass
    app = {}
    p = os.path.join(HERE, "chars_app.json")
    if os.path.exists(p):
        try:
            app = json.load(open(p, encoding="utf-8"))
        except Exception:
            app = {}
    for e in tags:
        if e.get("cat") == "角色" and not e.get("app"):
            a = app.get(e.get("en")) or {}
            if a:
                e["app"] = {k: a.get(k, "") for k in ("hair", "eyes", "outfit", "body", "chest")}
    idx = [(e["zh"], e) for e in tags if len(e.get("zh") or "") >= 2 and e.get("cat") != "角色"]
    idx.sort(key=lambda x: -len(x[0]))
    _cache["lib"] = tags
    _cache["idx"] = idx
    return tags

HAIR_RE = re.compile(r"(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)发|长发|短发|双马尾|马尾|丸子头|麻花辫|卷发|直发|刘海")
EYE_RE = re.compile(r"(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)(色)?(的)?(眼|瞳)")
OUT_RE = re.compile(r"裸|全裸|没穿|不穿|内衣|围裙|校服|水手服|女仆|巫女|浴衣|和服|旗袍|泳装|比基尼|制服|连衣裙|衬衫|T恤|外套|睡衣|运动服|裙子|短裤")
BODY_RE = re.compile(r"娇小|纤细|高挑|丰满|匀称")
CHEST_RE = re.compile(r"贫乳|巨乳|爆乳|平胸|小胸|大胸")

def fill_app(name, desc, app):
    if not app:
        return desc
    miss = []
    if not HAIR_RE.search(desc):
        miss.append(app.get("hair"))
    if not EYE_RE.search(desc):
        miss.append(app.get("eyes"))
    if not OUT_RE.search(desc):
        miss.append(app.get("outfit"))
    if not BODY_RE.search(desc):
        miss.append(app.get("body"))
    if not CHEST_RE.search(desc):
        miss.append(app.get("chest"))
    miss = [m for m in miss if m]
    return ("，".join(miss) + "，" + desc) if miss else desc

def _match(body, idx):
    feats, used = [], [False] * len(body)
    for z, e in idx:
        i = body.find(z)
        if i < 0:
            continue
        if any(used[i:i + len(z)]):
            continue
        for k in range(i, i + len(z)):
            used[k] = True
        feats.append({"zh": z, "en": e["en"]})
        if len(feats) >= 16:
            break
    return feats

def parse_text(text):
    lib = load_lib()
    idx = _cache["idx"]
    app_map = {e["zh"]: e.get("app") for e in lib if e.get("cat") == "角色" and e.get("app")}

    EXCLUDE = ("场景", "其他", "环境", "画面", "地点", "外形", "服装", "动作",
               "表情", "身体", "画风", "风格", "光线", "时间", "氛围")

    header, blocks, sections = [], [], []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+|[一二三])个角色\s+(.+)$", line)
        if m:
            header = [x for x in re.split(r"[\s、,，]+", m.group(2)) if x]
            continue
        ms = re.match(r"^([^：:]{1,12})[：:]\s*(.+)$", line)
        if ms and ms.group(1).strip() not in EXCLUDE:
            sections.append((ms.group(1).strip(), ms.group(2).strip()))
        else:
            blocks.append(line)

    chars = []
    if sections:
        for name, body in sections:
            feats = _match(body, idx)
            chars.append({"zh": name, "name": name, "tag": name,
                          "features": [f["zh"] for f in feats],
                          "features_en": [f["en"] for f in feats],
                          "desc": fill_app(name, body, app_map.get(name)),
                          "app": app_map.get(name)})
    elif header:
        body = "，".join(blocks)
        body = re.sub(r"(外形|服装|动作|其他|表情|身体|画风)\s*[：:]", "", body)
        feats = _match(body, idx)
        for name in header:
            chars.append({"zh": name, "name": name, "tag": name,
                          "features": [f["zh"] for f in feats],
                          "features_en": [f["en"] for f in feats],
                          "desc": fill_app(name, body, app_map.get(name)),
                          "app": app_map.get(name)})
    else:
        names = [(e["zh"], e) for e in lib if e.get("cat") == "角色" and e["zh"] in text]
        names.sort(key=lambda x: -len(x[0]))
        for nm, e in names:
            segs = [s for s in re.split(r"[。\n]", text) if nm in s]
            body = "，".join(segs)
            feats = _match(body, idx)
            chars.append({"zh": nm, "name": nm, "tag": nm,
                          "features": [f["zh"] for f in feats],
                          "features_en": [f["en"] for f in feats],
                          "desc": fill_app(nm, body, app_map.get(nm)),
                          "app": app_map.get(nm)})

    scene_src = "\n".join([l for l in text.split("\n")
                           if re.match(r"^(场景|其他|环境|画面|地点)", l.strip())]) or text
    feats = _match(scene_src, idx)
    glob = [{"zh": f["zh"], "en": f["en"]} for f in feats][:12]
    return {"chars": chars, "tags": glob, "expanded": ""}
