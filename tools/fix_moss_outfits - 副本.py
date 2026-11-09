# -*- coding: utf-8 -*-
"""fix_moss_outfits.py —— 给 sub=MOSS原创 的 5 个角色（char_a~char_e）补 app.outfit。

角色气质 → 服装（按需求给定）：
  A 冷艳（白发红眼）  白色长裙，黑色长手套
  B 活泼（金发蓝眼）  水手服，红色领结，百褶裙
  C 疏离（银发紫眼）  黑色紧身连衣裙，银色颈饰
  D 温柔（棕发棕眼）  米色针织衫，长裙
  E 软萌（粉发粉眼）  粉色连衣裙，白色蕾丝边

注意：custom_chars.json 里 角色C / 角色E 是「覆盖层」（带 from），app.py 会用它的
app 整体替换内置条目的 app，所以两处都要写，否则改了 tags_cn 也会被覆盖回去。

幂等：已经是目标值的条目跳过；没有实际改动就不写盘、不备份。
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = os.path.join(HERE, "tags_cn.json")
CUSTOM = os.path.join(HERE, "custom_chars.json")

OUTFITS = {
    "char_a": "白色长裙，黑色长手套",
    "char_b": "水手服，红色领结，百褶裙",
    "char_c": "黑色紧身连衣裙，银色颈饰",
    "char_d": "米色针织衫，长裙",
    "char_e": "粉色连衣裙，白色蕾丝边",
}


def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def main():
    dry = "--dry-run" in sys.argv
    doc = load(TAGS, None)
    if doc is None:
        print("找不到 tags_cn.json")
        return 1
    tags = doc["tags"]

    changed_tags, changed_custom = [], []
    moss = [x for x in tags if x.get("cat") == "角色" and x.get("sub") == "MOSS原创"]
    print("MOSS原创 角色 %d 条：%s" % (len(moss), ", ".join(x.get("en", "") for x in moss)))
    for x in moss:
        en = x.get("en", "")
        want = OUTFITS.get(en)
        if not want:
            print("  ? 未知的 MOSS 角色，跳过：%s" % en)
            continue
        app = x.setdefault("app", {})
        if (app.get("outfit") or "").strip() == want:
            print("  = %s(%s) 已是目标值" % (x.get("zh"), en))
            continue
        app["outfit"] = want
        changed_tags.append(en)
        print("  + %s(%s) outfit -> %s" % (x.get("zh"), en, want))

    custom = load(CUSTOM, [])
    for c in custom:
        key = (c.get("from") or c.get("en") or "").strip()
        want = OUTFITS.get(key)
        if not want:
            continue
        app = c.setdefault("app", {})
        if (app.get("outfit") or "").strip() == want:
            continue
        app["outfit"] = want
        changed_custom.append(key)
        print("  * custom_chars 覆盖层 %s(%s) outfit -> %s"
              % (c.get("zh"), key, want))

    if not changed_tags and not changed_custom:
        print("全部已是目标值（幂等），不写盘。")
        return 0
    if dry:
        print("[dry-run] 不写盘。")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(TAGS, os.path.join(HERE, "tags_cn.backup_moss2_%s.json" % stamp))
    if changed_custom:
        shutil.copy2(CUSTOM, os.path.join(HERE, "custom_chars.backup_moss2_%s.json" % stamp))
    save(TAGS, doc)
    if changed_custom:
        save(CUSTOM, custom)
    print("已写入：tags_cn.json 改 %d 条，custom_chars.json 改 %d 条"
          % (len(changed_tags), len(changed_custom)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
