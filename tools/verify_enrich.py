# -*- coding: utf-8 -*-
"""verify_enrich.py — 用 urllib 从 8901 验证词库治理结果（只读）"""
import collections
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:8901/api/tags"
FIELDS = ("hair", "eyes", "outfit", "body", "chest")


def stats(tags):
    cats = collections.Counter(x.get("cat") for x in tags)
    sub = collections.Counter("%s/%s" % (x.get("cat"), x.get("sub")) for x in tags
                              if x.get("cat") == "自定义")
    chars = [x for x in tags if x.get("cat") == "角色"]

    def full(a):
        return isinstance(a, dict) and all(str(a.get(k) or "").strip() for k in FIELDS)

    def anyf(a):
        return isinstance(a, dict) and any(str(a.get(k) or "").strip() for k in FIELDS)

    return {
        "total": len(tags),
        "cats": dict(cats),
        "custom_sub": dict(sub),
        "tu": sum(1 for x in tags
                  if x.get("cat") == "自定义" and x.get("sub") == "图反推"),
        "chars": len(chars),
        "chars_full": sum(1 for x in chars if full(x.get("app"))),
        "chars_any": sum(1 for x in chars if anyf(x.get("app"))),
    }


def main():
    d = json.load(urllib.request.urlopen(URL, timeout=60))
    now = stats(d["tags"])
    print("=== 现在（/api/tags，total %d）===" % now["total"])
    for k, v in sorted(now["cats"].items(), key=lambda kv: -kv[1]):
        print("  %-6s %5d" % (k, v))
    print("  自定义子类:", json.dumps(now["custom_sub"], ensure_ascii=False,
                                  sort_keys=True))
    print("  自定义/图反推 剩余: %d" % now["tu"])
    print("  角色 %d，五字段齐全 %d (%.1f%%)，至少一项 %d (%.1f%%)"
          % (now["chars"], now["chars_full"],
             100.0 * now["chars_full"] / max(1, now["chars"]),
             now["chars_any"], 100.0 * now["chars_any"] / max(1, now["chars"])))

    base_path = os.path.join(HERE, "_baseline_tags_api.json")
    if os.path.exists(base_path):
        try:
            base = stats(json.load(open(base_path, encoding="utf-8"))["tags"])
        except Exception:
            base = None
        if base:
            print("\n=== 对比基线（total %d）===" % base["total"])
            keys = sorted(set(base["cats"]) | set(now["cats"]))
            print("  %-6s %8s %8s %8s" % ("分类", "前", "后", "差"))
            for k in keys:
                b, n = base["cats"].get(k, 0), now["cats"].get(k, 0)
                print("  %-6s %8d %8d %+8d" % (k, b, n, n - b))
            print("  图反推: %d -> %d" % (base["tu"], now["tu"]))
            print("  角色五字段齐全: %d (%.1f%%) -> %d (%.1f%%)"
                  % (base["chars_full"],
                     100.0 * base["chars_full"] / max(1, base["chars"]),
                     now["chars_full"],
                     100.0 * now["chars_full"] / max(1, now["chars"])))


if __name__ == "__main__":
    main()
