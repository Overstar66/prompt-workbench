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
               "表情", "身体", "画风", "风格", "光线", "时间", "氛围",
               # 题材 / 服装品类，不是角色名
               "百合", "内裤", "内衣", "情趣内衣", "制服", "道具", "姿势", "题材",
               "剧情", "情节", "设定", "背景", "镜位", "构图", "色调", "镜头")
    HEAD_RE = re.compile(r"^(\d+|[一二三四五六七八九十两])\s*个?\s*(角色|女生|女孩|女人|男孩|男生|男人|人|位)\s*(.+)$")

    header, blocks, sections = [], [], []
    _had_label = False
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = HEAD_RE.match(line)
        if m:
            cand = [x for x in re.split(r"[\s、,，]+", m.group(3)) if x]
            # 粘连写法：「两个角色角色a角色b」→ 拆成 角色a / 角色b
            if len(cand) == 1 and len(cand[0]) > 3:
                _rest = cand[0]
                _tk = re.findall(r"角色\s*[A-Za-z0-9甲乙丙丁一二三四]", _rest)
                if len(_tk) >= 2:
                    cand = _tk
                else:
                    _known = sorted({e["zh"] for e in lib if e.get("cat") == "角色"
                                     and e.get("zh") and e["zh"] in _rest}, key=len, reverse=True)
                    if len(_known) >= 2 and "".join(_known) == _rest:
                        cand = _known
            # 声明了几个就取几个
            _n = m.group(1)
            try:
                _n = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5}.get(_n) or int(_n)
            except Exception:
                _n = len(cand)
            if _n and len(cand) > _n:
                cand = cand[:_n]
            # 「一个女孩，粉发，微笑，海边」不是表头：名字里不该出现外形/服装词
            _bad = False
            for x in cand:
                # 表头是用户显式声明的名字：白名单不再否决（百合/内裤 也能当角色名）
                if (HAIR_RE.search(x) or EYE_RE.search(x) or OUT_RE.search(x)
                        or BODY_RE.search(x) or CHEST_RE.search(x)):
                    _bad = True
                    break
            if cand and not _bad:
                header = cand
                continue
            blocks.append(line)
            continue
        ms = re.match(r"^([^：:]{1,12})[：:]\s*(.+)$", line)
        if ms:
            _had_label = True
            if ms.group(1).strip() not in EXCLUDE:
                sections.append((ms.group(1).strip(), ms.group(2).strip()))
            continue
        blocks.append(line)

    def _mk(name, body):
        feats = _match(body, idx)
        zh_list = [f["zh"] for f in feats]
        en_list = [f["en"] for f in feats]
        # 角色自带外观：正文没写到的类别直接补成词条，拆出来就一目了然
        try:
            import gen_mod as _gm
            _app = app_map.get(name) or {}
            if _app:
                _extra = _gm._app_en({"zh": name, "name": name, "app": _app,
                                      "tags": [{"tag": e} for e in en_list]}, lib, [])
                for _en in _extra:
                    if _en and _en not in en_list:
                        _zh = next((e["zh"] for e in lib if e.get("en") == _en), _en)
                        en_list.append(_en)
                        zh_list.append(_zh)
        except Exception:
            pass
        return {"zh": name, "name": name, "tag": name,
                "features": zh_list,
                "features_en": en_list,
                "desc": fill_app(name, body, app_map.get(name)),
                "app": app_map.get(name)}

    chars = []
    if header:
        # 表头优先：只认表头里的名字；冒号段按「名字匹配 → 按顺序」对应过去
        named = {n: b for n, b in sections}
        if all(n in named for n in header):
            bodies = [named[n] for n in header]
        elif len(sections) == len(header):
            bodies = [b for _, b in sections]
        elif sections:
            bodies = ["，".join(b for _, b in sections)] * len(header)
        else:
            bodies = ["，".join(blocks)] * len(header)
        for name, body in zip(header, bodies):
            chars.append(_mk(name, body))
    elif sections:
        for name, body in sections:
            chars.append(_mk(name, body))
    elif _had_label:
        # 只有「场景/服装/百合/内裤」这类标签行，没有真实角色 → 不硬凑角色
        chars = []
    else:
        names = [(e["zh"], e) for e in lib if e.get("cat") == "角色" and e["zh"] in text]
        names.sort(key=lambda x: -len(x[0]))
        for nm, e in names:
            segs = [s for s in re.split(r"[。\n]", text) if nm in s]
            body = "，".join(segs)
            chars.append(_mk(nm, body))

    scene_src = "\n".join([l for l in text.split("\n")
                           if re.match(r"^(场景|其他|环境|画面|地点)", l.strip())]) or text
    feats = _match(scene_src, idx)
    glob = [{"zh": f["zh"], "en": f["en"]} for f in feats][:12]
    return {"chars": chars, "tags": glob, "expanded": ""}
