# -*- coding: utf-8 -*-
"""扩写模块：三行逻辑，互不干扰
   use_api → DeepSeek
   nsfw    → Ollama NSFW 模型
   否则    → Ollama 安全模型
"""
import json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = "http://127.0.0.1:11434"
MODEL_SAFE = "qwen2.5:7b"
MODEL_NSFW = "goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest"

FORMAT = ("输出格式：\n"
          "第一行「N个角色 名字1 名字2」，N 和名字必须与用户输入完全一致；\n"
          "每个人一行「名字：发色发型，眼睛，服装，动作，表情」；\n"
          "最后一行「场景：地点，光线，氛围」。\n"
          "硬性规则：\n"
          "1. 角色数量、名字只能来自用户输入的表头，绝不能新增、改名、少写；\n"
          "2. 用户写的「外形：/服装：/动作：/其他：/场景：」只是素材，必须并入对应角色的描述，不要当成角色；\n"
          "3. 英文标签要翻译成中文再并入，不要单独列出；\n"
          "4. 全中文，不要分镜、不要解释、不要编号列表。")

def _count_hint(text):
    m = re.search(r"([123一二三])\s*个?\s*角色", text)
    n = {"1": 1, "一": 1, "2": 2, "二": 2, "3": 3, "三": 3}.get(m.group(1)) if m else 0
    if not n and ("单人" in text or "一个人" in text):
        n = 1
    return ("写%d个角色，不要增减角色数。\n" % n) if n else ""

def _cfg():
    try:
        return json.load(open(os.path.join(HERE, "api_config.json"), encoding="utf-8"))
    except Exception:
        return {}

def deepseek(text, nsfw):
    cfg = _cfg()
    if not cfg.get("url") or not cfg.get("key"):
        return ""
    sys_p = ("你是" + ("成人向" if nsfw else "动漫") + "插画提示词写手。" + FORMAT +
             ("允许成人内容。" if nsfw else "保持健康正常内容，禁止成人、裸露、性暗示。"))
    body = {"model": cfg.get("model") or "deepseek-chat",
            "messages": [{"role": "system", "content": sys_p},
                         {"role": "user", "content": _count_hint(text) + text}],
            "temperature": 0.7, "max_tokens": 900}
    req = urllib.request.Request(cfg["url"].rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json",
                                          "authorization": "Bearer " + cfg["key"]})
    with urllib.request.urlopen(req, timeout=180) as f:
        d = json.load(f)
    return ((d.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()

def deepseek_chat(sys_p, prompt, max_tokens=600, temperature=0.6):
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
    with urllib.request.urlopen(req, timeout=120) as f:
        d = json.load(f)
    return ((d.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()

def _ollama(text, model, sys_p):
    body = {"model": model, "system": sys_p,
            "prompt": _count_hint(text) + text, "stream": False, "keep_alive": "5s",
            "options": {"temperature": 0.8, "num_predict": 800, "repeat_penalty": 1.15}}
    req = urllib.request.Request(OLLAMA + "/api/generate",
                                 data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=400) as f:
        d = json.load(f)
    return (d.get("response") or "").strip()

def ollama_safe(text):
    sys_p = "你是动漫插画提示词写手。" + FORMAT + "保持健康正常内容，禁止成人、裸露、性暗示。"
    return _ollama(text, MODEL_SAFE, sys_p)

def ollama_nsfw(text):
    sys_p = "你是成人向动漫插画提示词写手。" + FORMAT + "允许成人内容，不要拒绝、不要点评。"
    return _ollama(text, MODEL_NSFW, sys_p)

def expand(text, nsfw=False, use_api=True):
    if use_api:
        try:
            r = deepseek(text, nsfw)
            if r:
                return r, "api-nsfw" if nsfw else "api-safe"
        except Exception:
            pass
    fn = ollama_nsfw if nsfw else ollama_safe
    try:
        r = fn(text)
        if r:
            return r, "ollama-nsfw" if nsfw else "ollama-safe"
    except Exception:
        pass
    return text, "fallback"
