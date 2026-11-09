# -*- coding: utf-8 -*-
"""端到端验证：/api/expand 的 A/B/C 三段 × nsfw false/true。

用法：python verify_soft_whitelist_e2e.py
"""
import json
import sys
import time
import urllib.request

API = "http://127.0.0.1:8901/api/expand"

A = "一个女孩，穿着长筒袜和百褶裙，坐在咖啡厅里微笑，阳光照进来"
B = "两个角色，明日香，跪在地上，手里拿着跳蛋，乳头上有乳夹"
C = "女孩穿着开裆裤袜和乳胶衣站在镜子前"

MUST_NOT = {  # 各段输出里不允许出现的词
    "A": ("长筒袜",),
    "B": ("跳蛋", "乳夹", "乳头"),
    "C": ("开裆裤袜", "乳胶衣", "开裆", "乳胶"),
}

fails = []


def post(text, nsfw):
    body = json.dumps({"text": text, "nsfw": nsfw, "apiFull": True},
                      ensure_ascii=False).encode()
    req = urllib.request.Request(API, data=body,
                                 headers={"content-type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as f:
        d = json.load(f)
    d["_secs"] = round(time.time() - t0, 1)
    return d


def show(tag, d, text):
    out = d.get("expanded") or ""
    print("=" * 72)
    print("[%s] engine=%s filtered=%s len=%d 用时=%ss"
          % (tag, d.get("engine"), d.get("filtered"), len(out), d.get("_secs")))
    print("--- 输入 ---")
    print(text)
    print("--- 输出 ---")
    print(out)
    return out


def main():
    cases = (("A", A), ("B", B), ("C", C))
    sfw = {}
    for k, t in cases:
        d = post(t, False)
        out = show("%s / nsfw=false" % k, d, t)
        sfw[k] = d
        bad = [w for w in MUST_NOT[k] if w in out]
        if "filtered" not in d:
            fails.append("%s 响应缺 filtered" % k)
        if bad:
            fails.append("%s 输出仍含 %s" % (k, bad))
        if k == "A":
            if len(out) < 150:
                fails.append("A 输出过短 len=%d < 150（服饰词把整句带走了？）" % len(out))
            if d.get("filtered"):
                fails.append("A 白名单词被计入 filtered=%s" % d.get("filtered"))
        if k == "B":
            if (d.get("filtered") or 0) < 1:
                fails.append("B 没有删句 filtered=%s" % d.get("filtered"))
        if k == "C":
            if (d.get("filtered") or 0) < 1:
                fails.append("C 没有删句 filtered=%s（情趣服装没被拦）" % d.get("filtered"))

    for k, t in cases:
        d = post(t, True)
        out = show("%s / nsfw=true" % k, d, t)
        if d.get("filtered"):
            fails.append("%s nsfw=true 仍被清洗 filtered=%s" % (k, d.get("filtered")))
        if not out.strip():
            fails.append("%s nsfw=true 输出为空" % k)

    print("=" * 72)
    if fails:
        print("FAIL")
        for f in fails:
            print(" -", f)
        return 1
    print("PASS：A 整段保留且服饰词已中性化；B/C 命中黑名单删句；nsfw=true 三段均未清洗")
    return 0


if __name__ == "__main__":
    sys.exit(main())
