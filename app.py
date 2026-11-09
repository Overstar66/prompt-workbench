# -*- coding: utf-8 -*-
"""提示词工作台 v2 后端：只做静态页 + 词库接口 + 代理旧后端(8900)"""
import json, os, re
import threading
import urllib.request
from urllib.parse import unquote, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8901
OLD = "http://127.0.0.1:8900"

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


def proxy(path, payload, timeout=300):
    req = urllib.request.Request(OLD + path,
                                 data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return f.read()


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
                sj = os.path.join(HERE, "styles.json") if os.path.isfile(os.path.join(HERE, "styles.json")) else os.path.join(r"D:\提示词生成\studio", "styles.json")
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
                        sdir = os.path.join(HERE, "styles") if os.path.isdir(os.path.join(HERE, "styles")) else os.path.join(r"D:\提示词生成\studio", "styles")
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
            _sd = os.path.join(HERE, "styles") if os.path.isdir(os.path.join(HERE, "styles")) else os.path.join(r"D:\提示词生成\studio", "styles")
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
                import legacy_expand as _L
                tags = _L.tag_image(img, want_style=True, style_only=False, model="moat") or []
                lib = load_lib()
                m = {e["en"]: e["zh"] for e in lib}
                out = []
                for t in tags:
                    en = (t.get("tag") or t.get("en") or "") if isinstance(t, dict) else str(t)
                    en = en.replace(" ", "_").strip()
                    if not en:
                        continue
                    out.append({"en": en, "zh": m.get(en, en)})
                # 按分类合成自然语言
                bycat = {}
                for x in out:
                    e = next((z for z in lib if z["en"] == x["en"]), None)
                    cat = (e or {}).get("cat") or "其他"
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
            self._send(200, proxy("/api/text2tags", data))
        elif p == "/api/expand":
            text = str(data.get("text") or "")
            use_api = bool(data.get("apiFull", True))
            nsfw_on = bool(data.get("nsfw", False))
            out, engine = "", ""
            # API：DeepSeek
            if use_api:
                try:
                    import sys as _sys
                    if HERE not in _sys.path:
                        _sys.path.insert(0, HERE)
                    import expand_mod
                    out, engine = expand_mod.expand(text, nsfw=nsfw_on, use_api=True)
                except Exception:
                    out, engine = "", ""
            # 本地：老工作台三步（扩写→对齐→清洗）
            if not out:
                try:
                    import sys as _sys
                    if HERE not in _sys.path:
                        _sys.path.insert(0, HERE)
                    import legacy_expand as _L
                    out = (_L.expand_full(text, allow_api=False) or "").strip()
                    try:
                        _a = _L.align_format(out)
                        if _a:
                            out = _a
                    except Exception:
                        pass
                    try:
                        _c = _L.clean_expanded(out)
                        if _c:
                            out = _c
                    except Exception:
                        pass
                    engine = "legacy-local"
                except Exception:
                    out = ""
            if not out:
                # 老工作台数据不可用时的兜底：直接用 Ollama
                try:
                    import sys as _s3
                    if HERE not in _s3.path:
                        _s3.path.insert(0, HERE)
                    import expand_mod as _em2
                    out, engine = _em2.expand(text, nsfw=nsfw_on, use_api=False)
                except Exception:
                    out, engine = "", ""
            self._send(200, json.dumps({"expanded": out or text, "engine": engine, "local": not use_api}, ensure_ascii=False))
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
