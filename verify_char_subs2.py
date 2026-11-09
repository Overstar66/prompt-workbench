# -*- coding: utf-8 -*-
"""verify_char_subs2.py —— 走 HTTP 验证 8901 上实际对外提供的词库。

检查点：
  1. /api/tags 里 角色 总数、sub 为占位值（动漫/游戏/自定义/空）的数量；
  2. 抽查：绫波丽→EVA、明日香→EVA、逢坂大河→龙与虎；
  3. MOSS原创 五个角色的 app.outfit 是否符合预期；
  4. 作品名分布 top 15，便于人工复核。
"""
import collections
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8901"
PLACEHOLDER = {"", "动漫", "游戏", "自定义"}

WANT = {
    "ayanami_rei": ("绫波丽", "EVA"),
    "souryuu_asuka_langley": ("明日香·兰格雷", "EVA"),
    "aisaka_taiga": ("逢坂大河", "龙与虎"),   # 需求里写的「缝坂大河」是错别字
}
MOSS = {
    "char_a": "白色长裙，黑色长手套",
    "char_b": "水手服，红色领结，百褶裙",
    "char_c": "黑色紧身连衣裙，银色颈饰",
    "char_d": "米色针织衫，长裙",
    "char_e": "粉色连衣裙，白色蕾丝边",
}


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    tags = get("/api/tags")["tags"]
    chars = [x for x in tags if x.get("cat") == "角色"]
    ph = [x for x in chars if (x.get("sub") or "").strip() in PLACEHOLDER]
    print("HTTP %s  tags=%d  角色=%d" % (BASE, len(tags), len(chars)))
    print("sub 仍为占位值(动漫/游戏/自定义/空)的角色：%d 条" % len(ph))
    if ph:
        for x in ph[:50]:
            print("   - %s / %s / %s" % (x.get("zh"), x.get("en"), x.get("sub")))

    ok = True
    print("\n抽查：")
    by_en = {x.get("en"): x for x in chars}
    for en, (zh, want) in WANT.items():
        x = by_en.get(en)
        got = (x or {}).get("sub")
        good = got == want
        ok &= good
        print("   %s %s(%s) sub=%r  期望 %r" %
              ("OK " if good else "FAIL", zh, en, got, want))

    print("\nMOSS原创 服装：")
    for en, want in MOSS.items():
        x = by_en.get(en)
        got = ((x or {}).get("app") or {}).get("outfit")
        good = (got or "").strip() == want
        ok &= good
        print("   %s %s outfit=%r" % ("OK " if good else "FAIL", en, got))

    c = collections.Counter(x.get("sub") for x in chars)
    print("\n作品分布 top 15：")
    for k, v in c.most_common(15):
        print("   %4d  %s" % (v, k))

    print("\n结论：%s（剩余占位 %d 条，目标 < 50）"
          % ("通过" if ok and len(ph) < 50 else "未通过", len(ph)))
    return 0 if (ok and len(ph) < 50) else 1


if __name__ == "__main__":
    sys.exit(main())
