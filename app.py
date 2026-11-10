# -*- coding: utf-8 -*-
"""提示词工作台 v2 后端：静态页 + 词库接口 + 扩写/图反推（全部本地/自有数据）"""
import json, os, re
import threading
import urllib.request
from urllib.parse import unquote, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8901

_cache = {}
CHARS_PATH = os.path.join(HERE, "custom_chars.json")
_CHARS_LOCK = threading.Lock()


def load_custom_chars():
    try:
        d = json.load(open(CHARS_PATH, encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save_custom_char(rec):
    """追加/更新一个自定义角色（同 zh / 同 en / 同 from 视为同一条），返回总条数。"""
    with _CHARS_LOCK:
        arr = load_custom_chars()
        zh, en, frm = rec.get("zh"), rec.get("en"), rec.get("from")
        idx = -1
        for i, c in enumerate(arr):
            if not isinstance(c, dict):
                continue
            if ((zh and c.get("zh") == zh) or (en and c.get("en") == en)
                    or (frm and c.get("from") == frm)):
                idx = i
                break
        if idx >= 0:
            old = arr[idx]
            if not rec.get("sub") and isinstance(old, dict) and old.get("sub"):
                rec["sub"] = old["sub"]          # 没传作品时保留原 sub
            arr[idx] = rec
        else:
            arr.append(rec)
        tmp = CHARS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(arr, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CHARS_PATH)
        _cache.pop("lib", None)          # 下次 /api/tags 重新拼装
        return len(arr)


def delete_custom_char(en=None, zh=None):
    """按 en / zh 删除一个自定义角色，返回 (是否删到, 剩余条数)。"""
    with _CHARS_LOCK:
        arr = load_custom_chars()
        out, hit = [], False
        for c in arr:
            if isinstance(c, dict) and ((en and c.get("en") == en) or (zh and c.get("zh") == zh)):
                hit = True
                continue
            out.append(c)
        if not hit:
            return False, len(arr)
        tmp = CHARS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CHARS_PATH)
        _cache.pop("lib", None)          # 下次 /api/tags 重新拼装
        return True, len(out)


def load_lib():
    if "lib" in _cache:
        return _cache["lib"]
    tags = json.load(open(os.path.join(HERE, "tags_cn.json"), encoding="utf-8"))["tags"]
    # 合并额外的角色
    for fn in ("chars_extra.json",):
        p = os.path.join(HERE, fn)
        if os.path.exists(p):
            try:
                tags = tags + json.load(open(p, encoding="utf-8"))
            except Exception:
                pass
    # 合并前端「＋ 添加角色 / 编辑角色」写进 custom_chars.json 的自定义角色
    # 带 from 的记录是内置角色的覆盖层：按 from（原 en）替换内置条目，不改 tags_cn.json
    try:
        _custom = load_custom_chars()
    except Exception:
        _custom = []
    for c in (_custom or []):
        if not isinstance(c, dict):
            continue
        zh = str(c.get("zh") or "").strip()
        if not zh:
            continue
        en = str(c.get("en") or "").strip() or zh
        frm = str(c.get("from") or "").strip()
        a = c.get("app") or {}
        appd = {k: str(a.get(k) or "") for k in ("hair", "eyes", "outfit", "body", "chest")}
        tgt = None
        if frm:
            tgt = next((e for e in tags if e.get("cat") == "角色" and e.get("en") == frm), None)
        if tgt is None:
            tgt = next((e for e in tags if e.get("cat") == "角色" and e.get("en") == en), None)
        if tgt is None:
            tgt = next((e for e in tags if e.get("cat") == "角色"
                        and e.get("zh") == zh and not e.get("custom")), None)
        if tgt is not None:
            tgt["zh"], tgt["en"], tgt["app"], tgt["custom"] = zh, en, appd, True
            if c.get("sub"):
                tgt["sub"] = str(c.get("sub")).strip()   # 覆盖内置角色时同步作品
            if frm:
                tgt["from"] = frm
            continue
        if any(e.get("cat") == "角色" and e.get("en") == en for e in tags):
            continue
        tags.append({"zh": zh, "en": en, "cat": "角色", "sub": c.get("sub") or "自定义",
                     "nsfw": False, "custom": True, "app": appd})
    # 附加外貌
    app = {}
    p = os.path.join(HERE, "chars_app.json")
    if os.path.exists(p):
        try:
            app = json.load(open(p, encoding="utf-8"))
        except Exception:
            app = {}
    for e in tags:
        if e.get("cat") == "角色":
            a = app.get(e.get("en")) or {}
            if a and not e.get("app"):
                e["app"] = {k: a.get(k, "") for k in ("hair", "eyes", "outfit", "body", "chest")}
    _cache["lib"] = tags
    return tags


# ---------- 角色外观约束（扩写防篡改） ----------
# 用户反馈：描述里写「明日香：发色咖啡色」，扩写后变成「发色黑长直」——模型把角色设定改了。
# 做法：扩写前找出文本里出现过的角色，把外观拼成一段硬约束放在发给模型的内容最前面；
#       用户自己写过的字段（发色/瞳色/服装/体型/胸围）以用户为准，词库只在缺失时补。
_GUARD_NOTE = "（以用户描述为准，若用户已写则用用户的）"
_ASSET_FLAG = "（用户已写，禁止改）"
_LIB_FLAG = "（词库）"

# 字段 → (中文标签, 「用户已写」判定正则)
_APP_FIELDS = (
    ("hair", "发色", re.compile(
        r"发色|发型|头发|黑长直|长直发|双马尾|单马尾|马尾|丸子头|麻花辫|卷发|直发|"
        r"长发|短发|法式刘海|刘海|散发|发梢|"
        r"(?:黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿|咖啡|栗|酒红|亚麻|茶|巧克力)(?:色)?(?:的)?"
        r"(?:发|长发|短发|卷发|直发)")),
    ("eyes", "瞳色", re.compile(
        r"眼睛|眼瞳|瞳孔|眼珠|瞳色|异色瞳|"
        r"(?:黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿|琥珀|异色)(?:色)?(?:的)?(?:眼|瞳)")),
    ("outfit", "服装", re.compile(
        r"穿着|穿|裸|服装|衣服|外套|上衣|裙子|连衣裙|制服|校服|水手服|女仆|巫女|浴衣|和服|"
        r"旗袍|泳装|比基尼|睡衣|衬衫|T恤|短裤|短裙|长裙|丝袜|袜子|鞋子|内衣|围裙|驾驶服|战斗服")),
    ("body", "体型", re.compile(r"身材|体型|体态|娇小|纤细|高挑|丰满|匀称|苗条|微胖")),
    ("chest", "胸围", re.compile(r"贫乳|巨乳|爆乳|平胸|小胸|大胸|胸部|胸围|罩杯")),
)


def _alias_of(zh):
    """角色别名：中文名本身 + 「·」/「・」前的名字（明日香·兰格雷 → 明日香）。"""
    out = [zh]
    for sep in ("·", "・", "•", " "):
        if sep in zh:
            head = zh.split(sep)[0].strip()
            if len(head) >= 2:
                out.append(head)
    return out


# 英文露骨词词库里没有、单字兜底也管不到：做温和中性化（不参与删句判定）。
_SFW_PAIRS = (
    ("pussy", "body"), ("nipples", "chest"), ("cum", "water"),
)


def _sfw_repair(text):
    """英文露骨词的中性化；中文露骨词走下面的整句删除，不在这里替换。"""
    out = text
    for a, b in _SFW_PAIRS:
        out = out.replace(a, b)
    return out


def _sfw_sanitize(text):
    """NSFW 关闭时的输入中性化：只做英文兜底（中文露骨词在输出侧整句删）。"""
    return _sfw_repair(text)


# ---------- NSFW 三级判定：露骨整句删 / 擦边原样留 ----------
# 用户反馈：一刀切删掉「内裤外露 / 走光 / 内衣 / 长筒袜」这类擦边内容太狠。
# 现在把 tags_cn.json 里 nsfw==true 的词分两档（词库文件本身不动，规则全在这）：
#   露骨 = 性器官/性行为/体液词根、动作-亲密、明确的性玩具  → 命中整句删
#   擦边 = 服装、外形/表情/姿势、非玩具道具等               → 原样保留（不删句、不改写）
_EXPLICIT_ROOTS = (
    "小穴", "阴道", "阴茎", "肉棒", "龟头", "包皮", "阴唇", "阴蒂", "肛门",
    "乳首", "乳头", "乳晕", "奶头", "精液", "精子", "射精", "爱液", "淫水",
    "潮吹", "尿液", "口交", "性交", "插入", "抽插", "中出", "肛交", "自慰",
    "调教", "舔阴", "舔屌", "肉穴", "子宫", "孕肚",
)

# 词库的 sub 并不完全可靠：做爱/后入/手交/后穴 这些明确性行为落在「双人互动」
# 或「单人」下，只按 sub=="亲密" 会漏。补一小撮词根，它们同样属于露骨。
_EXPLICIT_ACTS = ("开裆裤袜", "开裆连裤袜", "开裆内裤", "开裆", 
    "做爱", "后入", "乳交", "手交", "足交", "抠穴", "扣穴", "后穴", "屁穴",
    "颜射", "深喉", "口爆", "吞精",
)

# 明确的性玩具（A 档）；词库里没收录或 flag 不稳的也硬编码兜住
_TOY_WORDS = (
    "跳蛋", "假阳具", "肛塞", "拉珠", "口球", "乳夹", "乳铃", "束缚绳", "手铐",
    "眼罩", "项圈", "触手", "尿道棒", "震动棒", "飞机杯", "避孕套", "按摩棒", "贞操",
)

_EXPLICIT_MARK_RX = re.compile("|".join(
    re.escape(w) for w in sorted(
        set(_EXPLICIT_ROOTS) | set(_EXPLICIT_ACTS) | set(_TOY_WORDS),
        key=len, reverse=True)))

_NSFW_LOCK = threading.Lock()
_NSFW_TIERS = None      # (explicit_set, soft_set)
_EXPLICIT_RX = None     # 露骨词正则（长词优先）
# 单字兜底：词库外的残留露骨字。命中也整句删，但先屏蔽正常词（逼真/逼近/尿尿…）
_RESIDUE_RX = re.compile(r"逼|淫|尿|屄|屌|肏")
_RESIDUE_OK = frozenset((
    "逼近", "逼真", "逼仄", "逼迫", "逼供", "逼问", "逼视", "逼婚", "逼债", "逼上",
    "紧逼", "直逼", "催逼", "逼不得已", "逼人", "逼走", "屌丝",
    "淫雨", "淫威", "淫祀", "淫辞",
    "尿尿", "撒尿", "排尿", "尿急", "尿频", "尿布", "尿床", "尿检", "尿常规", "尿壶",
))
# 全被滤掉时的中性兜底，保证接口永远回一段干净文本
_SFW_EMPTY = "场景：室内，柔和的光线，安静的氛围。"


def _tag_explicit(zh, recs):
    """单个词条是否露骨：含露骨词根/性玩具，或属于「动作-亲密」。"""
    if _EXPLICIT_MARK_RX.search(zh):
        return True
    return any(e.get("cat") == "动作" and e.get("sub") == "亲密" for e in recs)


def nsfw_words():
    """惰性加载并分级：返回 (explicit_set, soft_set)。

    只有 explicit_set 会触发整句删除；soft_set 是擦边词，原样保留。
    """
    global _NSFW_TIERS, _EXPLICIT_RX
    if _NSFW_TIERS is not None:
        return _NSFW_TIERS
    with _NSFW_LOCK:
        if _NSFW_TIERS is not None:
            return _NSFW_TIERS
        recs = {}
        try:
            with open(os.path.join(HERE, "tags_cn.json"), encoding="utf-8") as f:
                data = json.load(f)
            for e in (data.get("tags") or []):
                if not isinstance(e, dict):
                    continue
                zh = str(e.get("zh") or "").strip()
                # 「自定义/图反推」是用户自建条目、nsfw 缺省 False，不参与判定；
                # 否则同名的正式词会被一条自建重名条目整条放过。
                if (not zh or not re.search(r"[\u4e00-\u9fff]", zh)
                        or str(e.get("cat") or "") == "自定义"):
                    continue
                recs.setdefault(zh, []).append(e)
        except Exception:
            recs = {}
        # 同词多条记录：全部 nsfw=true 才算命中（半条 nsfw 的不动）
        words = {zh for zh, es in recs.items()
                 if len(zh) >= 2 and all(x.get("nsfw") is True for x in es)}
        words |= set(_EXPLICIT_ROOTS) | set(_EXPLICIT_ACTS) | set(_TOY_WORDS)
        explicit = {w for w in words if _tag_explicit(w, recs.get(w, ()))}
        _EXPLICIT_RX = (re.compile("|".join(
            re.escape(w) for w in sorted(explicit, key=len, reverse=True)))
            if explicit else None)
        _NSFW_TIERS = (frozenset(explicit), frozenset(words - explicit))
    return _NSFW_TIERS


def soft_words():
    """擦边词集合（只保留、不删句），给自检/报表用。"""
    return nsfw_words()[1]


def _residue_hits(sent):
    """单字兜底：先屏蔽正常词，剩下的 逼/淫/尿/屄/屌/肏 才算露骨。"""
    s = sent
    for w in _RESIDUE_OK:
        if w in s:
            s = s.replace(w, "〇")
    return _RESIDUE_RX.findall(s)


def _split_sentences(text):
    """按 。！？!? 和换行切句，保留标点。"""
    out, buf = [], ""
    for ch in text:
        buf += ch
        if ch in "。！？!?\n":
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def _tidy_filtered(text):
    """删句后的收尾：去空行 / 删只剩角色名的空壳行 / 按剩下的人改首行人数。"""
    lines = []
    for raw in (text or "").split("\n"):
        ln = raw.strip()
        if not ln:
            continue
        # 「明日香：」「明日香：，。」这种后面没内容的行，删掉
        if re.match(r"^[^：:]{1,16}[：:]\s*[，,。；;、！!·…\s]*$", ln):
            continue
        lines.append(ln)
    if not lines:
        return ""
    m = re.match(r"^(\d+)\s*个角色\s+(.+)$", lines[0])
    if m and len(lines) > 1:
        names = [x for x in m.group(2).split() if x]
        have = [n for n in names
                if any(ln.startswith(n + "：") or ln.startswith(n + ":") for ln in lines[1:])]
        if have and len(have) != len(names):
            lines[0] = "%d个角色 %s" % (len(have), " ".join(have))
        elif not have:
            lines.pop(0)
    return "\n".join(lines)


def sanitize_nsfw_text(text):
    """NSFW 关闭时的输出清洗：只删露骨句，擦边原样保留。

    返回 (清洗后文本, 命中数)；命中数 = 被删句子里命中的露骨词/单字个数。
    """
    src = str(text or "")
    if not src.strip():
        return src, 0
    nsfw_words()
    rx = _EXPLICIT_RX
    hits, kept = 0, []
    for sent in _split_sentences(src):
        found = rx.findall(sent) if rx is not None else []
        if not found:
            found = _residue_hits(sent)
        if found:
            hits += len(found)
            continue
        kept.append(_sfw_repair(sent))
    return _tidy_filtered("".join(kept)), hits


def _role_hits(text, lib):
    """找出文本里出现的角色：zh / 别名做包含匹配，最长匹配优先，区间不重叠。"""
    if not text:
        return []
    cands = []
    for e in lib:
        if e.get("cat") != "角色":
            continue
        zh = (e.get("zh") or "").strip()
        if len(zh) < 2:
            continue
        for a in _alias_of(zh):
            i = text.find(a)
            if i >= 0:
                cands.append((len(a), i, a, e))
    cands.sort(key=lambda x: (-x[0], x[1]))
    used = [False] * len(text)
    hits, seen = [], set()
    for ln, i, a, e in cands:
        if e.get("zh") in seen or any(used[i:i + ln]):
            continue
        for k in range(i, i + ln):
            used[k] = True
        seen.add(e.get("zh"))
        hits.append({"zh": a, "name": e.get("zh") or a, "app": e.get("app") or {},
                     "start": i, "end": i + ln})
    hits.sort(key=lambda h: h["start"])
    return hits


def _role_body(text, hit, hits):
    """取该角色在用户文本里的那段描述：优先「名字：描述」行，否则按名字位置切段。"""
    for line in text.splitlines():
        m = re.match(r"^([^：:]{1,16})[：:]\s*(.+)$", line.strip())
        if m and m.group(1).strip() in (hit["zh"], hit["name"]):
            return m.group(2)
    if len(hits) <= 1:
        return text
    i = hits.index(hit)
    end = hits[i + 1]["start"] if i + 1 < len(hits) else len(text)
    return text[hit["end"]:end]


def _phrase(body, m):
    """把命中的关键词扩成一句可读的外观短语（发色咖啡色 → 咖啡色）。"""
    i, j = m.start(), m.end()
    while i > 0 and body[i - 1] not in "，,。；;、\n 　":
        i -= 1
    while j < len(body) and body[j] not in "，,。；;、\n":
        j += 1
    seg = body[i:j].strip()
    for pre in ("发色", "发型", "头发", "眼睛", "眼瞳", "瞳孔", "瞳色", "服装", "穿着", "穿",
                "衣服", "身材", "体型", "胸围"):
        if seg.startswith(pre) and len(seg) > len(pre):
            seg = seg[len(pre):].strip("：: ")
            break
    return seg


def build_char_guard(text, lib=None):
    """扩写前拼在模型输入最前面的角色外观约束；文本里没有已知角色就返回空串。"""
    try:
        lib = lib if lib is not None else load_lib()
        hits = _role_hits(text, lib)
    except Exception:
        return ""
    rows = []
    for h in hits:
        appd = h.get("app") or {}
        body = _role_body(text, h, hits) or ""
        parts = []
        for key, label, rx in _APP_FIELDS:
            m = rx.search(body)
            if m:
                p = _phrase(body, m)
                if p:
                    parts.append("%s=%s%s" % (label, p, _ASSET_FLAG))
                    continue
            val = str(appd.get(key) or "").strip()
            if val:
                parts.append("%s=%s%s" % (label, val, _LIB_FLAG))
        if parts:
            short = []
            for one in parts:
                if one.startswith("发色="):
                    short.append(one.split("=", 1)[1].rstrip("（词库）"))
                elif one.startswith("瞳色="):
                    short.append(one.split("=", 1)[1].rstrip("（词库）"))
                elif one.startswith("服装="):
                    short.append(one.split("=", 1)[1].rstrip("（词库）"))
            if short:
                rows.append(h["zh"] + "=" + "/".join(short))
    if not rows:
        return ""
    return ("【外观锁定，不得更改或互换】" + "；".join(rows) + "\n")


CFG_PATH = os.path.join(HERE, "api_config.json")
DEFAULT_CFG = {"url": "https://api.deepseek.com", "model": "deepseek-chat",
               "key": ""}

def load_cfg():
    try:
        return json.load(open(CFG_PATH, encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_CFG)



OLLAMA = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5:7b"

SYS_EXPAND = ("你是成人向动漫插画提示词写手。把用户的一句话扩写成标准格式：\n"
              "第一行「2个角色 A B」或「1个角色 A」；\n"
              "每个人一行「名字：发色发型，眼睛，服装，动作，表情」；\n"
              "最后一行「场景：地点，光线，氛围」。\n"
              "全中文，不要英文标签，不要分镜，不要解释。")

def ollama_expand(text, model=None, nsfw=None):
    if nsfw is None:
        nsfw = False
    mname = model or ("goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest" if nsfw else OLLAMA_MODEL)
    sys_p = SYS_EXPAND if nsfw else ("你是动漫插画提示词写手。把用户描述扩写成标准格式：\n"
                                     "第一行「2个角色 A B」；每人一行「名字：发色发型，眼睛，服装，动作，表情」；\n"
                                     "最后一行「场景：地点，光线，氛围」。全中文，保持健康正常内容，不要成人内容。")
    body = json.dumps({
        "model": mname,
        "system": sys_p,
        "prompt": text,
        "stream": False,
        "keep_alive": "5s",
        "options": {"temperature": 0.8, "num_predict": 700, "repeat_penalty": 1.15},
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as f:
        d = json.load(f)
    return (d.get("response") or "").strip()


def local_expand(text):
    """不联网的本地扩写：按句子切分，整理成「名字：内容」结构"""
    import re as _re
    raw = _re.split(r"[\n。；]", text)
    lines = [x.strip() for x in raw if x.strip()]
    if not lines:
        return text
    out = []
    for ln in lines:
        if "：" in ln or ":" in ln:
            out.append(ln.replace(":", "："))
        else:
            out.append(ln)
    if not any(("场景" in x) for x in out) and len(out) > 1:
        out.append("场景：室内，柔和光线")
    return "\n".join(out)

def api_expand(text, nsfw=False):
    cfg = load_cfg()
    if not cfg.get("url") or not cfg.get("key"):
        return ""
    body = {
        "model": cfg.get("model") or "deepseek-chat",
        "messages": [
            {"role": "system", "content": ("你是" + ("成人向" if nsfw else "动漫") + "插画提示词写手。把用户描述扩写成标准格式：第一行「N个角色 A B」；每人一行「名字：发色发型，眼睛，服装，动作，表情」；最后一行「场景：地点，光线，氛围」。全中文，不要英文标签。" + ("允许成人内容。" if nsfw else "保持健康正常内容，不要成人内容。"))},
            {"role": "user", "content": text},
        ],
        "temperature": 0.7, "max_tokens": 900,
    }
    req = urllib.request.Request(cfg["url"].rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json",
                                          "authorization": "Bearer " + cfg["key"]})
    with urllib.request.urlopen(req, timeout=120) as f:
        d = json.load(f)
    return (d.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            f = os.path.join(HERE, "static", "index.html")
            try:
                self._send(200, open(f, "rb").read(), "text/html; charset=utf-8")
            except Exception as e:
                self._send(500, "index missing: %s" % e, "text/plain; charset=utf-8")
        elif p == "/api/config":
            _c = load_cfg(); _k = _c.get("key") or ""
            self._send(200, json.dumps({"url": _c.get("url") or "", "model": _c.get("model") or "",
                                        "key": (_k[:6] + "…" + _k[-4:]) if len(_k) > 12 else _k,
                                        "key_set": bool(_k)}, ensure_ascii=False))
        elif p == "/api/styles":
            try:
                sj = os.path.join(HERE, "styles.json")
                data = json.load(open(sj, encoding="utf-8"))
                items = data if isinstance(data, list) else data.get("styles", [])
                out = []
                for it in items:
                    if isinstance(it, str):
                        out.append({"name": it, "img": "/styles/" + it, "tag": it})
                    else:
                        tag = it.get("tag") or it.get("en") or ""
                        img = it.get("img") or it.get("file") or ""
                    if not img:
                        base = tag.replace(" ", "_").replace("(", "").replace(")", "").replace("__", "_")
                        cands = [base + ".jpg", base.split("_")[0] + ".jpg", tag.replace(" ", "_").split("(")[0].strip() + ".jpg"]
                        sdir = os.path.join(HERE, "styles")
                        for c in cands:
                            if os.path.isfile(os.path.join(sdir, c)):
                                img = c
                                break
                        if not img:
                            img = base + ".jpg"
                        out.append({"name": it.get("zh") or it.get("name") or tag,
                                    "desc": it.get("desc") or "",
                                    "img": "/styles/" + img if img else "",
                                    "tag": tag})
                self._send(200, json.dumps({"styles": out}, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"styles": [], "error": str(e)}, ensure_ascii=False))
        elif p == "/favicon.ico":
            fp = os.path.join(HERE, "static", "favicon.ico")
            if os.path.isfile(fp):
                data2 = open(fp, "rb").read()
                self.send_response(200)
                self.send_header("content-type", "image/x-icon")
                self.send_header("content-length", str(len(data2)))
                self.end_headers()
                self.wfile.write(data2)
            else:
                self._send(404, "{}")
        elif p.startswith("/styles/"):
            _sd = os.path.join(HERE, "styles")
            fp = os.path.join(_sd, os.path.basename(unquote(p)))
            if os.path.isfile(fp):
                self._send(200, open(fp, "rb").read(), "image/jpeg")
            else:
                self._send(404, b"", "text/plain")
        elif p == "/api/tags":
            self._send(200, json.dumps({"tags": load_lib()}, ensure_ascii=False))
        elif p == "/api/chars":
            self._send(200, json.dumps({"chars": load_custom_chars()}, ensure_ascii=False))
        elif p.startswith("/api/"):
            self._send(404, "{}")
        else:
            fp = os.path.join(HERE, "static", p.lstrip("/"))
            if os.path.isfile(fp):
                ct = ("text/javascript; charset=utf-8" if fp.endswith(".js")
                      else "text/css; charset=utf-8" if fp.endswith(".css")
                      else "application/octet-stream")
                self._send(200, open(fp, "rb").read(), ct)
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")

    def do_DELETE(self):
        u = urlparse(self.path)
        if u.path == "/api/chars":
            q = parse_qs(u.query)
            en = (q.get("en") or [""])[0].strip()
            zh = (q.get("zh") or [""])[0].strip()
            ok, cnt = delete_custom_char(en, zh)
            if ok:
                self._send(200, json.dumps({"ok": True, "count": cnt}, ensure_ascii=False))
            else:
                self._send(200, json.dumps({"ok": False, "error": "not found"}, ensure_ascii=False))
        else:
            self._send(404, "{}")

    def do_POST(self):
        p = self.path.split("?")[0]
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n) if n else b"{}"

        if p == "/api/reverse_upload":
            try:
                ctype = self.headers.get("content-type") or ""
                boundary = ctype.split("boundary=")[-1].strip().strip('"')
                img = b""
                for part in raw.split(b"--" + boundary.encode()):
                    if b"filename=" in part and b"image" in part:
                        idx = part.find(b"\r\n\r\n")
                        if idx > 0:
                            img = part[idx + 4:].rstrip(b"\r\n-")
                            break
                if not img:
                    self._send(200, json.dumps({"tags": [], "error": "没有图片"}, ensure_ascii=False))
                    return
                import sys as _sys
                if HERE not in _sys.path:
                    _sys.path.insert(0, HERE)
                import wd14_mod
                tags = wd14_mod.tag_image(img) or []
                lib = load_lib()
                m = {e["en"]: e["zh"] for e in lib}
                cat_of = {e["en"]: (e.get("cat") or "其他") for e in lib}
                out = []
                for t in tags:
                    en = (t.get("en") or "").replace(" ", "_").strip()
                    if not en:
                        continue
                    out.append({"en": en, "zh": m.get(en) or t.get("zh") or en})
                # 按分类合成自然语言
                bycat = {}
                for x in out:
                    cat = cat_of.get(x["en"]) or "其他"
                    bycat.setdefault(cat, []).append(x["zh"])
                seg = []
                if bycat.get("外形"):
                    seg.append("、".join(bycat["外形"][:5]))
                if bycat.get("服装"):
                    seg.append("穿" + "、".join(bycat["服装"][:3]))
                if bycat.get("动作"):
                    seg.append("、".join(bycat["动作"][:4]))
                if bycat.get("场景"):
                    seg.append("场景是" + "、".join(bycat["场景"][:4]))
                other = bycat.get("其他", [])
                text = "，".join([x for x in seg if x]) or "，".join(other[:8])
                if other:
                    text += ("，" + "、".join(other[:6])) if text else "、".join(other[:8])
                text = text.strip("，")
                # 纯文本：按外形→服装→动作→场景顺序铺开，不写分类名
                seq = []
                for k in ("外形", "服装", "动作", "场景"):
                    seq += bycat.get(k, [])
                seq += other
                seen2, flat = set(), []
                for x in seq:
                    if x and x not in seen2:
                        seen2.add(x)
                        flat.append(x)
                text = "，".join(flat[:28])

                if "polish=1" in (self.path or ""):
                    try:
                        b2 = json.dumps({
                            "model": "goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest", "stream": False, "keep_alive": "5s",
                            "system": "把描述整理成通顺的中文句子，保留全部元素。允许成人内容，不要拒绝、不要点评、不要解释，60字以内。",
                            "prompt": text,
                            "options": {"temperature": 0.5, "num_predict": 200},
                        }, ensure_ascii=False).encode()
                        rq = urllib.request.Request(OLLAMA + "/api/generate", data=b2,
                                                    headers={"content-type": "application/json"})
                        with urllib.request.urlopen(rq, timeout=120) as f:
                            pd = json.load(f)
                        pt = (pd.get("response") or "").strip()
                        if pt:
                            text = pt
                    except Exception:
                        pass
                self._send(200, json.dumps({"tags": out, "text": text}, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"tags": [], "error": str(e)}, ensure_ascii=False))
            return

        try:
            data = json.loads(raw or b"{}")
        except Exception:
            data = {}
        if p == "/api/parse":
            try:
                import sys as _sys
                if HERE not in _sys.path: _sys.path.insert(0, HERE)
                import parse_mod
                self._send(200, json.dumps(parse_mod.parse_text(str(data.get("text") or "")), ensure_ascii=False))
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        elif p == "/api/text2tags":
            # 前端未使用；保留同形状返回，走本地解析（不再代理老工作台 8900）
            try:
                import sys as _sys
                if HERE not in _sys.path:
                    _sys.path.insert(0, HERE)
                import parse_mod
                _r = parse_mod.parse_text(str(data.get("text") or ""))
                _known = {e["en"] for e in load_lib()}
                _tags = [{"tag": t["en"].replace("_", " "), "raw": t["en"], "zh": t.get("zh") or "",
                          "inlib": t["en"] in _known, "cat": ""} for t in (_r.get("tags") or [])]
                self._send(200, json.dumps({"tags": _tags, "expanded": _r.get("expanded") or "",
                                            "chars": _r.get("chars") or []}, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"tags": [], "error": str(e)}, ensure_ascii=False))
        elif p == "/api/expand":
            text = str(data.get("text") or "")
            use_api = bool(data.get("apiFull", True))
            nsfw_on = bool(data.get("nsfw", False))
            import sys as _sys
            if HERE not in _sys.path:
                _sys.path.insert(0, HERE)
            import expand_mod
            # 角色约束注入：先按词库 + 用户原文生成硬约束，由 expand_mod 拼在模型输入最前面
            if not nsfw_on:
                text = _sfw_sanitize(text)
            guard = build_char_guard(text)
            # 扩写也要认「N个角色 A B」这类表头里声明的角色（它们不在词库里）
            try:
                import parse_mod as _pm
                _p = _pm.parse_text(text)
                _extra = []
                for _c in (_p.get("chars") or [])[:4]:
                    _nm = (_c.get("name") or _c.get("zh") or "").strip()
                    if not _nm:
                        continue
                    _ap = _c.get("app") or {}
                    _vals = [_ap.get(k) for k in ("hair", "eyes", "outfit") if _ap.get(k)]
                    _txt = "，".join(_vals) or (_c.get("desc") or "").strip()[:60] or "保持原文设定"
                    _extra.append("%s=%s" % (_nm, _txt))
                if _extra:
                    guard = (guard + "\n" if guard else "") + "【外观锁定，不得改名或互换】" + "；".join(_extra)
            except Exception:
                pass
            # use_api=True 走 DeepSeek，失败自动退 Ollama；False 直接 Ollama，再退 fallback
            try:
                out, engine = expand_mod.expand(text, nsfw=nsfw_on, use_api=use_api, guard=guard)
            except Exception as e:
                out, engine = "", "error:" + str(e)[:80]
            # 输出侧：NSFW 关闭时必须干净——模型越界也按词库整句删掉
            filtered = 0
            if not nsfw_on:
                if out:
                    out, filtered = sanitize_nsfw_text(out)
                if not out:
                    out, _ = sanitize_nsfw_text(text)
                if not out:
                    out = _SFW_EMPTY
            self._send(200, json.dumps({"expanded": out or text, "engine": engine,
                                        "local": not use_api, "guard": guard,
                                        "filtered": filtered}, ensure_ascii=False))
        elif p == "/api/config":
            cfg = {"url": str(data.get("url") or ""), "model": str(data.get("model") or ""),
                   "key": str(data.get("key") or "")}
            json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
        elif p == "/api/chars":
            _a = data.get("app") or {}
            _zh = str(data.get("zh") or "").strip()
            _en = re.sub(r"[^a-z0-9]+", "_", str(data.get("en") or "").strip().lower()).strip("_")
            rec = {"zh": _zh, "en": _en or _zh,
                   "app": {k: str(_a.get(k) or "").strip() for k in ("hair", "eyes", "outfit", "body", "chest")}}
            _sub = str(data.get("sub") or "").strip()
            if _sub:
                rec["sub"] = _sub
            _from = re.sub(r"[^a-z0-9]+", "_", str(data.get("from") or "").strip().lower()).strip("_")
            if _from:
                rec["from"] = _from
            if not rec["zh"]:
                self._send(200, json.dumps({"ok": False, "error": "中文名必填"}, ensure_ascii=False))
            else:
                self._send(200, json.dumps({"ok": True, "count": save_custom_char(rec)}, ensure_ascii=False))
        elif p == "/api/generate":
            try:
                if HERE not in __import__("sys").path:
                    __import__("sys").path.insert(0, HERE)
                import gen_mod
                req = dict(data)
                # 兼容前端字段：neg（full/lite/off）→ negLevel（后端统一认这两个名）
                if not req.get("negLevel") and req.get("neg"):
                    req["negLevel"] = req["neg"]
                _lib = load_lib()
                req["libTags"] = _lib
                # 外观来源优先级：chars_app.json（旧词库）< 词库（tags_cn + custom_chars 覆盖层）
                # load_lib 已把「编辑角色」写进 custom_chars.json 的 app 覆盖到内置条目上，必须最后落，
                # 否则 chars_app.json 里的同名旧外观会把编辑结果盖回去（WAI 里出现旧发色/服装）
                _appmap = {}
                try:
                    _ca = json.load(open(os.path.join(HERE, "chars_app.json"), encoding="utf-8"))
                    for _v in _ca.values():
                        if _v.get("zh"):
                            _appmap[_v["zh"]] = {k: _v.get(k, "") for k in ("hair", "eyes", "outfit", "body", "chest")}
                except Exception:
                    pass
                for e in _lib:
                    if e.get("app"):
                        _appmap[e.get("zh")] = e.get("app")
                for _c in (req.get("chars") or []):
                    if not _c.get("app"):
                        _c["app"] = _appmap.get(_c.get("zh") or _c.get("name")) or {}
                    # MOSS 补外观：把角色自带外观并进 desc（用户已写的内容优先，只补缺失项）
                    try:
                        _d = str(_c.get("desc") or "").strip()
                        _add = []
                        for _k in ("hair", "eyes", "outfit", "body", "chest"):
                            _v = str((_c.get("app") or {}).get(_k) or "").strip()
                            if _v and _v[:3] not in _d:
                                _add.append(_v)
                        if _add:
                            _c["desc"] = "，".join(([_d] if _d else []) + _add)
                    except Exception:
                        pass
                if not req.get("nsfw"):
                    _nsfw_en = {e.get("en") for e in _lib if e.get("nsfw")}
                    _tags = [x for x in (req.get("tags") or []) if (x.get("tag") or "") not in _nsfw_en]
                    _chars = []
                    for c in (req.get("chars") or []):
                        c2 = dict(c)
                        c2["tags"] = [t2 for t2 in (c.get("tags") or []) if (t2.get("tag") or "") not in _nsfw_en]
                        _chars.append(c2)
                    req["tags"], req["chars"] = _tags, _chars
                res = gen_mod.generate(req)
                # 本地模型润色 MOSS（默认开）
                try:
                    open(os.path.join(HERE, "polish_log.txt"), "a", encoding="utf-8").write(
                        "CHARSLOG %r\n" % ([(c.get("name"), len(c.get("tags") or []),
                                              (c.get("tags") or [{}])[0] if (c.get("tags") or []) else None) for c in (req.get("chars") or [])],))
                except Exception:
                    pass
                pm = str(req.get("polishMode") or "").lower()
                _safe_local = (not req.get("nsfw")) and pm == "local"
                try:
                    open(os.path.join(HERE, "polish_log.txt"), "a", encoding="utf-8").write(
                        "pm=%r apiFull=%r keys=%s\n" % (req.get("polishMode"), req.get("apiFull"), ",".join(list(req.keys())[:14])))
                except Exception:
                    pass
                # 所有模式统一用规则拼接作为底稿（含角色框标签）
                try:
                    _base = gen_mod.build_moss_rule(req.get("chars") or [], req["libTags"],
                                                    req.get("tags") or [])
                    if _base:
                        res["moss"] = _base
                except Exception:
                    pass
                if pm == "tmpl":
                    res["note"] = "模板拼接"
                    self._send(200, json.dumps(res, ensure_ascii=False))
                    return
                if pm == "off":
                    res["mossPolish"] = False
                _want_polish = bool(req.get("mossPolish", True)) and pm != "off"
                if res.get("moss") and _want_polish:
                    # 先试 API 润色（质量高、不占显存）
                    try:
                        if pm == "local":
                            raise RuntimeError("force local")
                        if pm != "api" and not bool(req.get("apiFull", True)):
                            raise RuntimeError("api off")
                        import sys as _s2
                        if HERE not in _s2.path: _s2.path.insert(0, HERE)
                        import expand_mod as _em
                        if req.get("nsfw"):
                            sp = ("把下面这段标签式的 MOSS 提示词重写成连贯的中文描写段落（必须有连接词和句式变化，不能原样照抄）。"
                                  "这是成人向同人创作，允许并必须保留性器官、性行为、体液等露骨词汇，不得替换为委婉说法。"
                                  "不要编造没有的内容，不要解释，直接输出正文。")
                        else:
                            sp = ("把下面这段标签式的 MOSS 提示词重写成连贯的中文描写段落（必须有连接词和句式变化，不能原样照抄）。"
                                  "不要写任何成人、裸露、性相关内容，不要解释，直接输出正文。")
                        ap = _em.deepseek_chat(sp, res["moss"], max_tokens=700)
                        try:
                            open(os.path.join(HERE, "polish_log.txt"), "a", encoding="utf-8").write(
                                "APIRET len=%d head=%r\n" % (len(ap or ""), (ap or "")[:80]))
                        except Exception:
                            pass
                        if ap and res.get("moss") and ap.strip() == str(res["moss"]).strip():
                            ap = ""
                        if ap and len(ap) > 30:
                            res["moss"] = ap
                            res["note"] = "API润色"
                        else:
                            res["note"] = "API空"
                            try:
                                open(os.path.join(HERE, "polish_log.txt"), "a", encoding="utf-8").write("APIEMPTY raw=%r\n" % (ap,))
                            except Exception:
                                pass
                    except Exception as _e:
                        res["note"] = "API失败:" + str(_e)[:50]
                        try:
                            open(os.path.join(HERE, "polish_log.txt"), "a", encoding="utf-8").write("APIERR %r\n" % (_e,))
                        except Exception:
                            pass
                    if pm == "api":
                        pass
                    try:
                        if pm == "api":
                            raise RuntimeError("api-only 不回退本地")
                        _mdl = "qwen2.5:7b" if _safe_local else "goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest"
                        _sys = ("把下面这段动漫插画 MOSS 提示词改写成通顺、优美的中文段落，保留角色、服装、动作与场景，"
                                "不要写任何成人、裸露、性相关内容，不要解释。") if _safe_local else (
                               "把下面这段动漫插画 MOSS 提示词改写成通顺的中文段落，必须保留全部露骨词汇"
                               "（小穴、乳房、乳头环、精液、插入等不得替换或删除），保留角色与动作，不要解释。")
                        body = json.dumps({
                            "model": _mdl,
                            "system": _sys,
                            "prompt": res["moss"],
                            "stream": False, "keep_alive": "5s",
                            "options": {"temperature": 0.6, "num_predict": 520},
                        }, ensure_ascii=False).encode()
                        rq = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                                    headers={"content-type": "application/json"})
                        with urllib.request.urlopen(rq, timeout=180) as f:
                            pd = json.load(f)
                        pol = (pd.get("response") or "").strip()
                        if pol and len(pol) > 30:
                            # 截到最后一个完整句子，去掉重复尾句
                            import re as _re
                            cut = max(pol.rfind("。"), pol.rfind("！"), pol.rfind("？"))
                            if cut > 40:
                                pol = pol[:cut + 1]
                            _sents = [x for x in _re.split(r"(?<=[。！？])", pol) if x.strip()]
                            if len(_sents) >= 2 and _sents[-1].strip() == _sents[-2].strip():
                                _sents.pop()
                                pol = "".join(_sents)
                            res["moss"] = pol
                            if res.get("note") != "API润色":
                                res["note"] = "本地润色"
                        else:
                            res["note"] = "润色输出过短，用模板"
                    except Exception as e:
                        if not str(res.get("note") or "").startswith(("API润色", "API空", "API失败")):
                            res["note"] = "润色失败:" + str(e)[:40]
                self._send(200, json.dumps(res, ensure_ascii=False))
            except Exception as e:
                self._send(200, json.dumps({"error": str(e)}, ensure_ascii=False))
        elif p == "/api/reverse":
            self._send(200, json.dumps({"tags": [], "note": "见 /api/reverse_upload"}, ensure_ascii=False))
        elif p == "/api/ping":
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, "{}")


if __name__ == "__main__":
    print("workbench v2 on http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
