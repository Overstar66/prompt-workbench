# -*- coding: utf-8 -*-
"""验证「密度」三档：同一组标签分别用 compact / normal / complex 生成 WAI，字符数应递增。

夹具固定：2 个角色各 10 个标签 + 30 个全局标签（无 NSFW、无重复），
所以「标签本来就多于上限」，三档差异完全由密度决定。

用法：python verify_density.py            # 直接调 gen_mod（不依赖 8901）
      python verify_density.py --http     # 打 8901 /api/generate（验证线上链路）
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIMITS = {"compact": (8, 6), "normal": (18, 14), "complex": (30, 24)}
QUALITY = "masterpiece, best quality, amazing quality"
GIRLS = "(2girls:1.45)"
NAME1, NAME2 = "(hatsune_miku)", "(luo_tianyi)"


def load_fixture():
    """固定夹具：2 个角色各 10 个标签 + 30 个全局标签（都不含 NSFW、不和角色标签重复）"""
    tags = json.load(open(os.path.join(HERE, "tags_cn.json"), encoding="utf-8"))["tags"]
    pool, seen = [], set()
    for e in tags:
        en = (e.get("en") or "").strip()
        if not en or en in seen or e.get("nsfw"):
            continue
        if e.get("cat") not in ("外形", "服装", "动作", "道具"):
            continue
        seen.add(en)
        pool.append(en)
    glob = pool[:30]
    c1 = [{"tag": x, "weight": 1} for x in pool[30:40]]
    c2 = [{"tag": x, "weight": 1} for x in pool[40:50]]
    # 显式传空 app：不让角色自带外观被后端自动补齐，三档差异只来自密度
    empty_app = {"hair_en": [], "eyes_en": [], "outfit_en": []}
    chars = [
        {"name": "初音未来", "en": "hatsune_miku", "app": empty_app, "tags": c1},
        {"name": "洛天依", "en": "luo_tianyi", "app": empty_app, "tags": c2},
    ]
    return chars, [{"tag": x, "weight": 1} for x in glob]


def direct(req):
    sys.path.insert(0, HERE)
    import gen_mod
    return gen_mod.generate(req)


def via_http(req):
    r = urllib.request.Request(
        "http://127.0.0.1:8901/api/generate",
        data=json.dumps(req, ensure_ascii=False).encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(r, timeout=120) as f:
        return json.loads(f.read().decode("utf-8"))


def main():
    use_http = "--http" in sys.argv
    chars, global_tags = load_fixture()
    print("夹具：%d 个角色（各 %d 标签）+ 全局 %d 标签%s" %
          (len(chars), len(chars[0]["tags"]), len(global_tags),
           "  [走 8901]" if use_http else "  [直接调 gen_mod]"))
    rows, ok = [], True
    for density in ("compact", "normal", "complex"):
        req = {
            "chars": chars,
            "tags": global_tags,
            "density": density,
            "neg": "full",
            "nsfw": False,
            "polishMode": "off",
            "mossPolish": False,
        }
        res = via_http(req) if use_http else direct(req)
        if res.get("error"):
            print(density, "ERROR", res["error"])
            return 1
        wai, pony = res.get("wai") or "", res.get("pony") or ""
        rows.append((density, len(wai), len(pony), wai))
        print("%-8s WAI %4d 字符  Pony %4d 字符" % (density, len(wai), len(pony)))

    sizes = [r[1] for r in rows]
    inc = sizes[0] < sizes[1] < sizes[2]
    print("字符数递增：", "PASS" if inc else "FAIL")
    ok = ok and inc

    for density, _n, _pn, wai in rows:
        per_max, glob_max = LIMITS[density]
        tok = wai.split(", ")
        head = tok[:3] == QUALITY.split(", ") and GIRLS in tok
        names_ok = NAME1 in tok and NAME2 in tok
        i1, i2 = tok.index(NAME1), tok.index(NAME2)
        c1, c2 = i2 - i1 - 1, len(tok) - i2 - 1
        last_own = min(10, per_max)          # 夹具里每个角色只有 10 个标签
        own2, glob = (last_own, c2 - last_own) if c2 >= last_own else (c2, 0)
        ok = ok and head and names_ok and c1 <= per_max and own2 <= per_max and glob <= glob_max
        print("%-8s 标签 %2d 个  quality前缀=%s 角色名=%s 角色1=%d 角色2=%d 全局=%d (上限 每角色%d/全局%d)"
              % (density, len(tok), "OK" if head else "FAIL", "OK" if names_ok else "FAIL",
                 c1, own2, glob, per_max, glob_max))

    # 低档必须是大档的子序列：顺序保留、只做尾部裁剪
    seq = rows[0][3].split(", ")
    sub = rows[2][3].split(", ")
    kept = [x for x in sub if x in seq]
    print("顺序保留（精简档是大档的子序列）：", "PASS" if kept == seq else "FAIL")
    ok = ok and kept == seq

    print("\ncompact WAI:\n" + rows[0][3])
    print("\ncomplex WAI:\n" + rows[2][3])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
