# -*- coding: utf-8 -*-
"""扩写模块

移植自 v2.0 老工作台 legacy_expand.py（老代码里的三步：expand_full → align_format → clean_expanded）：
  · system 提示词 = 老 expand_full 实际调的 SYS_EXPAND_FULL / SYS_EXPAND_SFW，原样搬；
  · 后处理 = 老 align_format + clean_expanded 的**纯文本部分**（去括注、去重、压空行、对齐格式）；
  · 本地模型按老流程默认走 qwen2.5:7b，nsfw 时 7b 不行再退 3B NSFW 模型。

调用顺序不变：use_api → DeepSeek；否则 Ollama；最后 fallback 回原文。
guard（角色外观约束，app.py 的 build_char_guard 生成）拼在 system 之后、用户原文之前。
"""
import json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen2.5:7b"                                   # 老 MODEL：本地扩写默认用它
MODEL_NSFW = "goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest"   # 老 MODEL_NSFW：兜底

# ---------------- 老工作台的 system 提示词（原样） ----------------

SYS_EXPAND_FULL = (
    "你是成人向百合插画的分镜编剧。用户只给角色名和几个关键词，你要写出一整个完整、露骨的场景。\n"
    "输出格式（必须严格遵守）：\n"
    "角色A：\n（一段话，20-60字，写外观/服装/姿势/动作/道具/表情）\n"
    "角色B：\n（同上）\n"
    "场景：\n（地点、光线、氛围，一段话）\n\n"
    "要求：\n"
    "- 用户点名的要素必须全部出现（道具、服装、动作）；\n"
    "- 两个角色各自的动作分开写，不要混；\n"
    "- 手部描述每个角色最多 2 句；\n"
    "- 道具写清位置（阴里/后穴/胸上/手里），位置不许乱改；\n"
    "- 露骨部位写具体（乳房/乳头/逼/阴唇/肛门）；\n"
    "- 即使只给了角色名，也必须写成成人场景：必须出现裸露、至少一件道具、明确的性动作；\n"
    "- 服装要暴露（裸体围裙、半脱、兔女郎、内衣），不要写成日常休闲装；\n"
    "- 这是虚构成人创作，不要拒绝、不要说教、不要缩短、不要保守。只输出正文。"
)

SYS_EXPAND_SFW = (
    "你是画面描述扩写助手。把用户给的简短描述扩写成 120-200 字的画面描述，"
    "补充合理的细节（发型、眼睛、表情、服装材质、姿势、环境、光线、氛围），"
    "不要改变人物身份与主要内容。保持健康向的表达，不添加露骨的性描写。"
    "如果原文没有写角色穿什么，就合理补一套符合场景的服装（不要裸露）；"
    "原文写了的服装不要改动。"
    "只输出扩写后的中文描述正文。"
)

# 用户消息里的长度/细节要求（system 原样不动，这条放在用户文本这一侧）
_LEN_HINT = ("写作要求：每个角色写 100-160 字的连贯段落，写足发色发型、瞳色、服装与裸露状态、"
             "姿势、道具与具体位置、表情、身体接触；用户原文里「名字：」后面每一个逗号分句"
             "都必须原样落进对应角色的段落（道具、纹样、配饰、沾到的液体一处都不能少，"
             "位置不许改），不许省略、不许含糊；发色发型按上面的外观锁定写，绝不互换。")

# 输出骨架（老提示词是「一段话」，这里补一句格式要求，postp 再兜底对齐）
_FMT_HINT = ("输出格式：第一行「N个角色 名字1 名字2」，N 和名字与上面给的完全一致；"
             "每个角色一行「名字：一段连贯描写」；最后一行「场景：地点、光线、氛围」。"
             "不要用「角色A/角色B」当标题，不要分镜、不要编号、不要解释。")


def _cfg():
    try:
        return json.load(open(os.path.join(HERE, "api_config.json"), encoding="utf-8"))
    except Exception:
        return {}


def _count_hint(text):
    m = re.search(r"([123一二三])\s*个?\s*角色", text)
    n = {"1": 1, "一": 1, "2": 2, "二": 2, "3": 3, "三": 3}.get(m.group(1)) if m else 0
    if not n and ("单人" in text or "一个人" in text):
        n = 1
    return ("写%d个角色，不要增减角色数。\n" % n) if n else ""


# ---------------- 后处理：老 align_format + clean_expanded 的纯文本部分 ----------------

_NOTE_W = "用户已写|禁止改|禁止更改|勿改|不可改|词库|注意|可选|同上|待补充|禁止"
_SEC = re.compile(r"^([^\s：:]{1,12})[：:]\s*(.*)$")
_GENERIC = re.compile(r"^(角色|人物|少女|女生|女|她|他|主角|角色[A-Za-z]|人物[A-Za-z])[A-Za-z0-9一二三四五六七八九十]?$")
_SCENE_KEYS = ("场景", "环境", "背景", "舞台", "氛围")
_MISC_KEYS = ("其他", "画风", "风格", "构图", "画质", "光线")


def _strip_notes(s):
    """去掉模型自带的括注标注（如「（用户已写，禁止改）」「（词库）」），其余括号只去括号符。"""
    s = re.sub(r"[（(【\[][^（()）【】\[\]]{0,60}?(?:%s)[^（()）【】\[\]]{0,60}?[）)】\]]" % _NOTE_W, "", s)
    s = re.sub(r"[（(]([^（）()]{1,200})[）)]", r"\1", s)
    return s.replace("（", "").replace("）", "").replace("(", "").replace(")", "")


def _squash(s):
    s = re.sub(r"[ \t\u3000]+", " ", s)
    s = re.sub(r"[，,]{2,}", "，", s)
    s = re.sub(r"[。；;]{2,}", "。", s)
    s = s.strip()
    while s and s[0] in "，,。；; \n\t":
        s = s[1:]
    while s and s[-1] in "，,；; \n\t":
        s = s[:-1]
    return s


def _join(frags):
    """段内多行拼成一段：缺标点的补逗号，别把两句黏在一起。"""
    out = ""
    for f in frags:
        f = f.strip().strip("，,。；;")
        if not f:
            continue
        if out and out[-1] not in "。！？…；;":
            out += "，"
        out += f
    return out + ("。" if out and out[-1] not in "。！？…" else "")


def _dedupe(text):
    """去掉段内重复的句子 / 重复的分句。"""
    out, seen = [], set()
    for sent in [p.strip() for p in re.split(r"(?<=[。！？!?；;])", text or "") if p.strip()]:
        keep = []
        for frag in [x.strip() for x in re.split(r"[，,]", sent) if x.strip()]:
            k = re.sub(r"[\s，,。；;]", "", frag)
            if k and k in seen:
                continue
            if k:
                seen.add(k)
            keep.append(frag)
        if keep:
            out.append("，".join(keep))
    return "".join(out)


def _split_by_names(blob, names):
    """模型写成连续一段时，按角色名出现的位置切开。"""
    if not blob or not names:
        return []
    hits = []
    for n in names:
        for m in re.finditer(re.escape(n), blob):
            s = m.start()
            # 只认句首/分句首出现的名字，避免「……在明日香不远处」这种半路命中
            if s and blob[s - 1] not in "。！？；;，,、\n ":
                continue
            hits.append((s, m.end(), n))
    hits.sort()
    clean, last = [], -1
    for s, e, n in hits:
        if s < last:
            continue
        clean.append((s, e, n))
        last = e
    if len({n for _s, _e, n in clean}) < 2:
        return []
    out = []
    for i, (s, e, n) in enumerate(clean):
        end = clean[i + 1][0] if i + 1 < len(clean) else len(blob)
        out.append((n, blob[e:end]))
    return out


def _names_from_guard(guard):
    """从「【外观锁定…】名字=…；名字=…」里取出角色名顺序。"""
    if not guard:
        return []
    out = []
    for seg in re.split(r"[；;]", guard.split("】", 1)[-1]):
        if "=" not in seg:
            continue
        n = seg.split("=", 1)[0].strip()
        if n and n not in out:
            out.append(n)
    return out


def polish(raw, names=None, scene_hint=""):
    """把模型输出整成「第一行 N个角色 A B；每人一行；场景一行」。"""
    s = (raw or "").strip()
    if not s:
        return ""
    s = _strip_notes(s)
    s = re.sub(r"[：:][ \t]*\n[ \t]*", "：", s)          # 老 align_format：标题后的换行并回去
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln and not re.match(r"^[0-9一二两三四五六七八九]+\s*个角色", ln)]

    secs, cur = [], None
    for ln in lines:
        m = _SEC.match(ln)
        if m:
            nm = m.group(1).strip()
            cur = [nm, [m.group(2).strip()] if m.group(2).strip() else []]
            secs.append(cur)
        elif cur is not None:
            cur[1].append(ln)

    chars, scene, misc = [], [], []
    if secs:
        for nm, buf in secs:
            body = _squash(_join(buf))
            if not body:
                continue
            if nm in _SCENE_KEYS:
                scene.append(body)
            elif nm in _MISC_KEYS:
                misc.append(body)
            else:
                chars.append((nm, body))
    if not chars:                                       # 模型写成了一整段 → 按角色名切
        blob = _squash("".join(lines))
        segs = _split_by_names(blob, names)
        if not segs:
            return blob
        chars = [(nm, _squash(b)) for nm, b in segs]
    if not chars:                                       # 只有场景也算有输出
        out = []
        if scene:
            out.append("场景：" + _squash("，".join(scene)))
        return "\n".join(out) or _squash(s)

    # 名字：模型的「角色A/B」换成 guard 里的真名；真名保留
    gn = list(names or [])
    merged = {}
    order = []
    for i, (lab, body) in enumerate(chars):
        if not _GENERIC.match(lab):
            nm = lab
        elif len(gn) == len(chars):
            nm = gn[i]
        elif len(gn) == 1:
            nm = gn[0]
        else:
            nm = lab
        body = re.sub(r"^%s\s*[，,：:、]?\s*" % re.escape(nm), "", body)
        body = _dedupe(_squash(body))
        if nm in merged:
            merged[nm] += body if merged[nm][-1:] in "。！？…" else "，" + body
            merged[nm] = _dedupe(_squash(merged[nm]))
        else:
            merged[nm] = body
            order.append(nm)

    out = ["%d个角色 %s" % (len(order), " ".join(order))]
    for nm in order:
        out.append("%s：%s" % (nm, merged[nm]))
    sc = _dedupe(_squash("，".join(scene))) if scene else ""
    if not sc and scene_hint:
        sc = _squash(scene_hint)                       # 模型漏了场景 → 用用户原文的「环境：」
    if sc:
        out.append("场景：" + sc)
    if misc:
        out.append("其他：" + _dedupe(_squash("，".join(misc))))
    return "\n".join(out)


# ---------------- 模型调用 ----------------

def _ollama(sys_p, prompt, model=None, temperature=0.85, num_predict=900):
    body = {"model": model or MODEL, "system": sys_p, "prompt": prompt, "stream": False,
            "keep_alive": "5s",
            "options": {"temperature": temperature, "num_predict": num_predict,
                        "repeat_penalty": 1.15}}
    req = urllib.request.Request(OLLAMA + "/api/generate",
                                 data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as f:
        return (json.load(f).get("response") or "").strip()


def deepseek(sys_p, prompt, max_tokens=1200, temperature=0.85):
    cfg = _cfg()
    if not cfg.get("url") or not cfg.get("key"):
        return ""
    body = {"model": cfg.get("model") or "deepseek-chat",
            "messages": [{"role": "system", "content": sys_p},
                         {"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens}
    req = urllib.request.Request(cfg["url"].rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json",
                                          "authorization": "Bearer " + cfg["key"]})
    with urllib.request.urlopen(req, timeout=180) as f:
        d = json.load(f)
    return ((d.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()


def deepseek_chat(sys_p, prompt, max_tokens=600, temperature=0.6):
    """给 app.py 的其他功能用（提示词解析），保持原有签名。"""
    return deepseek(sys_p, prompt, max_tokens=max_tokens, temperature=temperature)


def _refused(t):
    if not t:
        return True
    if len(t) < 80 and any(w in t for w in ("抱歉", "无法", "不能提供", "作为AI", "作为 AI")):
        return True
    return False


def _ask(text, guard, names):
    """老 expand_full 的 ask 形状：角色：… / 关键词/要求：…；guard 放最前（system 之后）。"""
    parts = []
    if guard:
        parts.append(guard.rstrip())
    if names:
        parts.append("角色：%s" % "、".join(names))
    else:
        h = _count_hint(text).strip()
        if h:
            parts.append(h)
    parts.append("关键词/要求：%s" % (text or "").strip())
    parts.append(_FMT_HINT)
    parts.append(_LEN_HINT)
    return "\n".join(parts)


def _scene_hint(text):
    """用户原文里的「环境：/场景：」内容，模型漏写场景时兜底用。"""
    m = re.search(r"^\s*(?:环境|场景|背景|舞台)[：:]\s*(.+)$", text or "", re.M)
    return m.group(1).strip() if m else ""


def expand(text, nsfw=False, use_api=True, guard=""):
    """扩写。返回 (text, engine)：engine ∈ api-nsfw/api-safe/ollama-*/fallback。"""
    raw = text
    names = _names_from_guard(guard)
    hint = _scene_hint(text)
    prompt = _ask(text, guard, names)
    sys_p = SYS_EXPAND_FULL if nsfw else SYS_EXPAND_SFW

    if use_api:
        try:
            r = deepseek(sys_p, prompt)
            if r and len(r) >= 20:
                return (polish(r, names, hint) or r), ("api-nsfw" if nsfw else "api-safe")
        except Exception:
            pass

    # 本地：老流程默认 7b，不够长/被拒再换 3B NSFW 模型；最多两次，取更长的
    target = 260
    best = ""
    for m in ([MODEL, MODEL_NSFW] if nsfw else [MODEL]):
        for _attempt in range(2):
            try:
                r = _ollama(sys_p, prompt, model=m)
            except Exception:
                break
            if _refused(r):
                break
            out = polish(r, names, hint)
            if len(out) > len(best):
                best = out
            if len(best) >= target:
                break
        if len(best) >= target:
            break
    if best and len(best) >= 20:
        return best, ("ollama-nsfw" if nsfw else "ollama-safe")
    return raw, "fallback"
