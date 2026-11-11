# -*- coding: utf-8 -*-
"""提示词生成：WAI / Pony / MOSS + 负向（纯本地，不用旧后端）"""
import re

QUALITY = "masterpiece, best quality, amazing quality"
PONY_Q = "score_9, score_8_up, score_7_up, source_anime, rating_explicit"
ANIMA_Q = "masterpiece, best quality, very aesthetic, absurdres"

NEG_WAI = ('extra hands, multiple hands, mutated hands, malformed hands, deformed hands, worst quality, low quality, normal quality, lowres, jpeg artifacts, blurry, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, fused fingers, deformed, disfigured, malformed limbs, extra limbs, missing limbs, long neck, watermark, signature, username, artist name, text, logo, cropped, out of frame, border, censored, mosaic censoring, bar censor')
NEG_PONY = ("score_4, score_5, score_6, worst quality, low quality, lowres, bad anatomy, bad hands, "
            "missing fingers, extra digits, watermark, signature, text, username, artist name, jpeg artifacts, "
            "ugly, blurry, deformed")
NEG_MOSS = ("最差画质，低画质，普通画质，低分辨率，压缩噪点，模糊，错误的人体结构，畸形的手，多余的手指，"
            "缺失的手指，融合的手指，多出的肢体，缺失的肢体，长脖子，水印，签名，用户名，画师名，文字，标志，"
            "被裁切，出框，边框，马赛克，打码，遮挡")

# 负向「精简」档：只留质量 + 畸形类，去掉冗长列举
NEG_WAI_SIMPLE = "worst quality, low quality, bad anatomy, bad hands, extra fingers, watermark, text"
NEG_PONY_SIMPLE = ("score_4, score_5, score_6, worst quality, low quality, bad anatomy, bad hands, "
                   "extra digits, watermark, text")
NEG_MOSS_SIMPLE = "最差画质，低画质，错误的人体结构，畸形的手，多余的手指，水印，文字"

_NEG_FULL = {"wai": NEG_WAI, "pony": NEG_PONY, "moss": NEG_MOSS}
_NEG_SIMPLE = {"wai": NEG_WAI_SIMPLE, "pony": NEG_PONY_SIMPLE, "moss": NEG_MOSS_SIMPLE}
_LV_OFF = {"off", "none", "no", "0", "false", "关", "关闭", "关掉"}
_LV_SIMPLE = {"simple", "lite", "light", "short", "精简", "简"}

# 负向自适应：正向出现触发词 → 从负向里剔除对应冲突词
_NEG_DROP = {
    "censor": {
        "wai": ("censored", "mosaic censoring", "bar censor"),
        "pony": ("censored", "mosaic censoring", "bar censor"),
        "moss": ("马赛克", "打码", "遮挡"),
    },
    "nude": {
        "wai": ("nude", "nipples", "topless", "naked"),
        "pony": ("nude", "nipples", "topless", "naked"),
        "moss": ("裸体", "裸露", "乳头"),
    },
    "chibi": {
        "wai": ("chibi",),
        "pony": ("chibi",),
        "moss": ("Q版", "q版"),
    },
    "mono": {
        "wai": ("colorful", "color", "bad color", "saturated", "oversaturated"),
        "pony": ("colorful", "color", "bad color", "saturated", "oversaturated"),
        "moss": ("彩色", "鲜艳", "单色", "灰度"),
    },
}
_TRIGGERS = {
    "censor": ("uncensored", "no mosaic", "no_mosaic", "no censorship", "no_censorship", "无码", "无修正"),
    "nude": ("nude", "naked", "topless", "nipples visible", "nipples_visible", "nipples",
             "areola", "pussy", "裸体", "裸露", "乳头"),
    "chibi": ("chibi", "q版", "q 版"),
    "mono": ("monochrome", "greyscale", "grayscale", "单色", "灰度"),
}
# NSFW 关闭时追加的负向（防止关掉开关还出裸露）
_NEG_NSFW_ADD = {
    "wai": ("nude", "naked", "topless", "nipples", "areola", "pussy", "sex"),
    "pony": ("nude", "naked", "topless", "nipples", "areola", "pussy", "sex"),
    "moss": ("裸体", "裸露", "上半身裸露", "乳头", "乳晕", "小穴", "性交"),
}

HAIR_RE = re.compile(r"(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)发|长发|短发|双马尾|马尾|丸子头|麻花辫|卷发|直发|刘海")
EYE_RE = re.compile(r"(黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿)(色)?(的)?(眼|瞳)")

# app 里的中文外观 → 词库整词：词库只有「银发 / 中长发 / 紫眼」，描述常写「银色中长发 / 紫色眼睛」
_COLOR_CH = "黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿|青|栗|褐"
_HAIR_BITS = "超长|中长|长|短|卷|直|散|蓬"
_HAIR_PAT = re.compile(r"(%s)(白|黑|金|银|红|蓝|绿|紫)?色?(%s)?(%s)?(?:头发|发型|发)"
                       % (_COLOR_CH, _HAIR_BITS, _HAIR_BITS))
_EYE_PAT = re.compile(r"(%s)(白|黑|金|银|红|蓝|绿|紫)?色?(?:眼睛|眼眸|眼|瞳)" % _COLOR_CH)


def zh_of(tags, en):
    for t in tags:
        if t.get("en") == en:
            return t.get("zh") or en
    return en


def build_neg(kind="wai", level="full"):
    """三档负向：full 完整 / simple(lite) 精简 / off 关闭（返回空串）"""
    kind = kind if kind in _NEG_FULL else "wai"
    lv = str(level or "full").strip().lower()
    if lv in _LV_OFF:
        return ""
    if lv in _LV_SIMPLE:
        return _NEG_SIMPLE[kind]
    return _NEG_FULL[kind]


def _pos_blob(req):
    """把正向内容拼成一整串小写文本，用于冲突检测"""
    parts = []
    for t in (req.get("tags") or []):
        if isinstance(t, dict):
            parts.append(str(t.get("tag") or ""))
        else:
            parts.append(str(t or ""))
    for c in (req.get("chars") or []):
        if not isinstance(c, dict):
            continue
        for k in ("en", "tag_en", "name", "zh"):
            if c.get(k):
                parts.append(str(c[k]))
        for t in (c.get("tags") or []):
            if isinstance(t, dict):
                parts.append(str(t.get("tag") or ""))
            else:
                parts.append(str(t or ""))
    return " ".join(parts).lower().replace("_", " ")


def adapt_neg(text, kind="wai", pos_blob="", nsfw_on=False):
    """负向自适应：剔除与正向冲突的词 + NSFW 关闭时追加裸露负向。

    - 冲突剔除：正向含 uncensored/no_mosaic → 去 censored 类；含裸露类 → 去裸体类；
      含 chibi → 去 chibi；含 monochrome/greyscale → 去彩色类（负向里有才去）。
    - NSFW 关闭 → 追加 nude/naked/... ；NSFW 开启 → 不追加。
    - 去重（不区分大小写）、保持原顺序，英文用 ", "、中文用 "，" 拼接。
    """
    if not text:
        return ""
    sep = "，" if kind == "moss" else ", "
    toks = [x.strip() for x in re.split(r"[,，]", text) if x.strip()]
    low = (pos_blob or "").lower().replace("_", " ")
    drop = set()
    for key, triggers in _TRIGGERS.items():
        if any(t in low for t in triggers):
            drop.update(w.lower() for w in _NEG_DROP[key][kind])
    out, seen = [], set()
    for t in toks:
        k = t.lower()
        if k in seen or k in drop:
            continue
        seen.add(k)
        out.append(t)
    if not nsfw_on and kind != "moss":
        for t in _NEG_NSFW_ADD[kind]:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(t)
    return sep.join(out)


def _char_line(c, taglist):
    name = c.get("name") or c.get("zh") or "角色"
    desc = (c.get("desc") or "").strip()
    feats = [t["tag"] for t in (c.get("tags") or []) if t.get("tag")]
    zh = [zh_of(taglist, f) for f in feats]
    if desc:
        return f"{name}：{desc}。"
    if c.get("_borrow"):
        return f"{name}：" + "，".join(c["_borrow"]) + "。"
    body = "，".join(zh[:12])
    return f"{name}：{body}。" if body else f"{name}：一个女孩。"


def build_moss(chars, taglist, sel_tags=None, style="动漫风格，柔和光线，高细节"):
    """chars=角色；taglist=词库；sel_tags=已选标签[{tag,weight}]"""
    sel = [t.get("tag") for t in (sel_tags or []) if t.get("tag")]

    def cat_of(en):
        for e in taglist:
            if e.get("en") == en:
                return e.get("cat") or ""
        return ""

    def zh_of2(en):
        return zh_of(taglist, en)

    # 分类：身体/服装/动作/道具 → 角色词；场景 → 场景词
    body_words, scene_words = [], []
    for en in sel:
        c = cat_of(en)
        z = zh_of2(en)
        if not z or z == en:
            continue
        if c == "场景":
            if z not in scene_words:
                scene_words.append(z)
        else:
            if z not in body_words:
                body_words.append(z)

    KEY = ("小穴", "插入", "精液", "乳", "乳环", "肛门", "阴蒂", "无码", "跳蛋", "淫纹", "爱液", "乳头", "屁股", "裸")
    body_words.sort(key=lambda w: 0 if any(k in w for k in KEY) else 1)
    names = [(c.get("name") or c.get("zh") or "") for c in (chars or [])][:4]
    names = [n for n in names if n]
    head = ("一个女孩：" if len(names) == 1 else "两个女孩：" if len(names) == 2
            else "三个女孩：" if len(names) == 3 else "女孩们：")
    head += "、".join(names) + "。"
    if scene_words:
        head += "，".join(scene_words[:4]) + "，"
    head += style + "。"

    lines = [head, ""]
    if chars:
        for idx, c in enumerate(chars[:4]):
            nm = (c.get("name") or c.get("zh") or "").strip()
            desc = (c.get("desc") or "").strip()
            if desc:
                lines.append("%s：%s。" % (nm, desc))
            else:
                take = body_words[:25] if idx == 0 else body_words[25:50]
                if take:
                    lines.append("%s：%s。" % (nm, "，".join(take)))
                else:
                    lines.append("%s：%s。" % (nm, "女孩"))
            lines.append("")
    elif body_words:
        lines.append("一个女孩：" + "，".join(body_words[:25]) + "。")
        lines.append("")

    if scene_words:
        lines.append("场景是" + "，".join(scene_words[:5]) + "。")
    return "\n".join(lines).strip()



# 用户手加的标签优先：角色已有某类外观时，app 的自动补全不再补同类
_HAIR_WORDS = ("twintails", "ponytail", "bangs", "braid", "braids", "ahoge", "hime_cut",
               "bob_cut", "hair_bun", "drill_hair", "messy_hair", "wavy_hair",
               "curly_hair", "straight_hair", "very_long_hair")
_EYES_WORDS = ("heterochromia", "closed_eyes", "half_closed_eyes", "slit_pupils")
_OUTFIT_WORDS = ("dress", "skirt", "shirt", "uniform", "sailor", "blouse", "blazer",
                 "jumpsuit", "qipao", "cheongsam", "kimono", "gown", "leotard", "bodysuit")


def _app_kind(en, info):
    """英文标签属于哪类外观：hair / eyes / outfit / ''（body、chest 不归类，不参与跳过）"""
    e = (en or "").lower()
    cat, sub = info.get(en, ("", ""))
    if cat == "外形" and sub in ("发色", "发型", "头发"):
        return "hair"
    if cat == "外形" and sub == "眼睛":
        return "eyes"
    if cat == "服装":
        return "outfit"
    if e.endswith("_hair") or e in _HAIR_WORDS:
        return "hair"
    if e.endswith("_eyes") or e.endswith("_eye") or e in _EYES_WORDS:
        return "eyes"
    if any(k in e for k in _OUTFIT_WORDS):
        return "outfit"
    return ""


def _own_kinds(c, info, sel_tags=None):
    """用户已选的标签覆盖了哪几类外观（角色自己的 + 全局标签都算）"""
    own = set()
    for t in (c.get("tags") or []):
        en = (t.get("tag") or "").strip()
        if en:
            k = _app_kind(en, info)
            if k:
                own.add(k)
    # 全局标签里出现某类外观 = 用户已全局指定，任何角色都不再自动补该类。
    # 角色自己带同类不同值（全局 blue_eyes、角色 red_eyes）时 own 已含该类，
    # 角色标签照常输出，只是 app 不再补。
    for t in (sel_tags or []):
        en = (t.get("tag") or "").strip() if isinstance(t, dict) else str(t or "").strip()
        if en:
            k = _app_kind(en, info)
            if k:
                own.add(k)
    return own


def _app_en(c, taglist, sel_tags=None):
    """把角色 app 里的中文外观转成英文标签"""
    info = {e.get("en"): (e.get("cat") or "", e.get("sub") or "") for e in taglist if e.get("en")}
    own = _own_kinds(c, info, sel_tags)
    app = c.get("app") or {}
    fixed = []
    for k in ("hair_en", "eyes_en", "outfit_en"):
        for x in (app.get(k) or []):
            if x and x not in fixed:
                fixed.append(x)
    if fixed:
        for k in ("hair_en", "eyes_en", "outfit_en"):
            for x in (app.get(k) or []):
                if x and x not in fixed:
                    fixed.append(x)
    if fixed:
        return [x for x in fixed if _app_kind(x, info) not in own]
    text = "，".join([app.get(k) or "" for k in ("hair", "eyes", "outfit", "body", "chest")])
    if not text.strip():
        return []
    out = []
    zh2en = [(e.get("zh") or "", e.get("en") or "") for e in taglist if e.get("zh") and e.get("en")]
    zh2en.sort(key=lambda x: -len(x[0]))
    zh_map = dict(zh2en)
    used = [False] * len(text)
    for zh, en in zh2en:
        if len(zh) < 2:
            continue
        i = text.find(zh)
        if i < 0:
            continue
        if any(used[i:i + len(zh)]):
            continue
        for k in range(i, i + len(zh)):
            used[k] = True
        if en not in out:
            out.append(en)
        if len(out) >= 12:
            break

    def pick(*cands):
        """按候选中文词优先命中词库里的整词，落成英文标签"""
        for z in cands:
            if z and z in zh_map and zh_map[z] not in out:
                out.append(zh_map[z])
                return True
        return False

    # 第二遍：词库只有整词（银发 / 中长发 / 紫眼），描述常写成「银色中长发」「紫色眼睛」，按颜色词拆分
    for m in _HAIR_PAT.finditer(text):
        if len(out) >= 16:
            break
        c1, c2, m1, m2 = m.group(1), m.group(2), m.group(3), m.group(4)
        col = c1 + (c2 or "")
        pick(col + "发", (c2 or "") + c1 + "发", col + "色发", c1 + "发")
        for ln in (m1, m2):
            if ln:
                pick(ln + "发", ln + "长发")
    for m in _EYE_PAT.finditer(text):
        if len(out) >= 16:
            break
        c1, c2 = m.group(1), m.group(2)
        col = c1 + (c2 or "")
        pick(col + "眼", (c2 or "") + c1 + "眼", col + "色眼睛", col + "眼睛", c1 + "眼")
    # 第三遍：颜色词 + 服装（「黑色紧身连衣裙」里词库有「黑色连衣裙」这个组合词）
    for seg in re.split(r"[，、；。/]", text):
        seg = seg.strip()
        m = re.match(r"(%s)(白|黑|金|银|红|蓝|绿|紫)?色?(.+)$" % _COLOR_CH, seg)
        if not m or len(out) >= 16:
            continue
        col, rest = m.group(1) + (m.group(2) or ""), m.group(3)
        for zh, en in zh2en:
            if len(zh) >= 2 and zh in rest:
                if pick(col + zh, col + "色" + zh):
                    break
    return [x for x in out if _app_kind(x, info) not in own]


def _wtag(t):
    tag = (t.get("tag") or t.get("en") or "").strip()
    if not tag:
        return ""
    try:
        w = float(t.get("weight") or 1)
    except Exception:
        w = 1.0
    if abs(w - 1.0) < 0.01:
        return tag
    return "(%s:%.1f)" % (tag, w)


# 密度三档：(每个角色最多拼几个标签, 全局最多拼几个标签)
# 只裁剪标签数量，角色名 / quality 前缀 / (2girls:1.45) 计数一律不动，顺序按「已选」保留。
# 标准/复杂 = 不截断（与原 v1.7 行为一致），只有精简档做限制
DENSITY_LIMITS = {
    "compact": (8, 6),
    "normal": (999, 999),
    "complex": (999, 999),
}


def density_limits(name):
    return DENSITY_LIMITS.get(str(name or "").strip().lower(), DENSITY_LIMITS["normal"])


def build_positive(chars, tags, quality=QUALITY, prefix="", density="normal"):
    per_max, glob_max = density_limits(density)
    words = []
    if prefix:
        words.append(prefix)
    words.append(quality)
    cnt = len(chars) or 1
    if cnt > 1:
        words.append(f"({cnt}girls:1.45)")
    for c in chars:
        nm = c.get("en") or c.get("tag_en") or c.get("name") or c.get("zh")
        if nm:
            words.append(f"({nm})")
        kept = 0
        for t in (c.get("tags") or []):
            x = _wtag(t)
            if x and x not in words:
                words.append(x)
                kept += 1
                if kept >= per_max:
                    break
    kept = 0
    for t in (tags or []):
        x = _wtag(t)
        if x and x not in words:
            words.append(x)
            kept += 1
            if kept >= glob_max:
                break
    out, seen = [], set()
    for w in words:
        if w.lower() not in seen:
            seen.add(w.lower()); out.append(w)
    return ", ".join(out)


def generate(req):
    chars = req.get("chars") or []
    tags = req.get("tags") or []
    taglist = req.get("libTags") or []
    # 前端传的是 neg（full/lite/off），旧调用方传 negLevel；两者都认
    neg_lvl = req.get("negLevel") or req.get("neg") or "full"
    nsfw_on = bool(req.get("nsfw"))
    scene_tags = [t for t in tags]
    moss = build_moss(chars, taglist, tags)
    _zh2en = {(e.get("zh") or ""): (e.get("en") or "") for e in taglist if e.get("cat") == "角色"}
    chars2 = []
    for c in chars:
        if not c.get("en"):
            nm = c.get("name") or c.get("zh") or ""
            c = dict(c)
            c["en"] = c.get("tag_en") or _zh2en.get(nm) or ""
        extra = _app_en(c, taglist, tags)
        have = {(t.get("tag") or "") for t in (c.get("tags") or [])}
        add = [{"tag": e, "weight": 1} for e in extra if e not in have]
        c2 = dict(c)
        c2["tags"] = list(c.get("tags") or []) + add
        chars2.append(c2)
    # 密度：compact / normal / complex → 控制每个角色与全局拼进去的标签数量
    density = str(req.get("density") or "normal").strip().lower()
    wai = build_positive(chars2, tags, density=density)
    pony = build_positive(chars2, tags, PONY_Q, density=density)
    pos_blob = " ".join([_pos_blob(req), wai.lower(), pony.lower()])
    # Q版(chibi)容易画成多角色/角色表 → 单角色时补 solo
    if "chibi" in pos_blob and (len(chars) or 1) == 1:
        if "solo" not in wai.lower():
            wai = wai + ", solo"
        if "solo" not in pony.lower():
            pony = pony + ", solo"
        pos_blob = pos_blob + " solo"
    anima = build_positive(chars2, tags, ANIMA_Q, density=density)
    neg_wai = adapt_neg(build_neg("wai", neg_lvl), "wai", pos_blob, nsfw_on)
    neg_pony = adapt_neg(build_neg("pony", neg_lvl), "pony", pos_blob, nsfw_on)
    neg_moss = adapt_neg(build_neg("moss", neg_lvl), "moss", pos_blob, nsfw_on)
    # 单角色：负向加入多角色/克隆词，避免画成一群
    if (len(chars) or 1) == 1:
        _anti = "2girls, multiple_girls, split_screen, character_sheet, duplicate, multiple views"
        if neg_wai:
            neg_wai = neg_wai + ", " + _anti
        if neg_pony:
            neg_pony = neg_pony + ", " + _anti
    return {
        "moss": moss,
        "neg_moss": neg_moss,
        "neg_zh": neg_moss,
        "wai": wai,
        "neg": neg_wai,
        "pony": pony,
        "neg_pony": neg_pony,
        "anima": anima,
        "neg_anima": (neg_wai + ", " + _anti) if ((len(chars) or 1) == 1 and neg_wai) else neg_wai,
        "negLevel": str(neg_lvl).strip().lower(),
        "note": "本地生成",
    }


def build_moss_rule(chars, taglist, sel_tags=None, style="动漫风格，柔和光线，高细节"):
    """规则拼接：不经模型，保留全部标签，用固定句式连成句子"""
    def zh(en):
        return zh_of(taglist, en)
    def cat(en):
        for e in taglist:
            if e.get('en') == en:
                return e.get('cat') or ''
        return ''
    groups = {'外形': [], '服装': [], '道具': [], '动作': [], '场景': []}
    for t in (sel_tags or []):
        en = t.get('tag')
        if not en:
            continue
        z = zh(en)
        if not z or z == en:
            continue
        c = cat(en)
        if c in groups and z not in groups[c]:
            groups[c].append(z)
    names = [(c.get('name') or c.get('zh') or '').strip() for c in (chars or [])][:3]
    names = [n for n in names if n]
    head = ('女孩' if not names else '一个女孩' if len(names) == 1 else '两个女孩' if len(names) == 2 else '三个女孩')
    head += ('：' + '、'.join(names)) if names else ''
    head += '。'
    if groups['场景']:
        head += '，'.join(groups['场景'][:3]) + '，'
    head += style + '。'
    lines = [head, '']
    n = max(1, len(names))
    body = groups['外形'] + groups['服装'] + groups['道具'] + groups['动作']
    per = max(3, (len(body) + n - 1) // n)
    for i in range(n):
        nm = names[i] if i < len(names) else '女孩'
        # 角色自己的标签优先
        own = []
        if i < len(chars):
            for t in (chars[i].get('tags') or []):
                z2 = zh(t.get('tag') or t.get('en') or '')
                if z2 and z2 not in own:
                    own.append(z2)
        g = body[i * per:(i + 1) * per]
        chunk = list(dict.fromkeys(own + [x for x in g if x not in own]))
        if not chunk:
            chunk = body[:6]
        _desc = (chars[i].get('desc') or '').strip() if i < len(chars) else ''
        if own:
            _parts = ([_desc] if _desc else []) + chunk[:20]
            lines.append(nm + '：' + '、'.join(list(dict.fromkeys(_parts))) + '。')
            lines.append('')
            continue
        seg = []
        if groups['外形']:
            seg.append('、'.join([x for x in chunk if x in groups['外形']][:5]))
        if groups['服装']:
            seg.append('穿着' + '、'.join([x for x in chunk if x in groups['服装']][:5]))
        if groups['道具']:
            seg.append('身上带着' + '、'.join([x for x in chunk if x in groups['道具']][:5]))
        if groups['动作']:
            seg.append('正在' + '、'.join([x for x in chunk if x in groups['动作']][:5]))
        seg = [x for x in seg if x and not x.endswith('着')]
        if _desc:
            # 角色自带外观优先，后面再跟已选标签
            _tail = '；'.join(seg) if seg else ''
            lines.append(nm + '：' + _desc + ('；' + _tail if _tail else '') + '。')
        else:
            lines.append(nm + '：' + ('；'.join(seg) if seg else '、'.join(chunk[:8])) + '。')
        lines.append('')
    if groups['场景']:
        lines.append('场景：' + '、'.join(groups['场景'][:4]) + '。')
    return '\n'.join(lines).strip()
