# -*- coding: utf-8 -*-
"""reconcile_chars.py — 用两轮 LLM 结果（enrich_cache / enrich_refine_cache）重算角色外貌：
  颜色一致 → 保留颜色级描述（发型细节不一致就只说「X色头发」）；
  服装两次一致才保留；没被复核到的一律清空。不调用 LLM。
"""
import json
import os
import re
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(HERE, "tags_cn.json")
C1 = os.path.join(HERE, "enrich_cache.json")
C2 = os.path.join(HERE, "enrich_refine_cache.json")
FIELDS = ("hair", "eyes", "outfit", "body", "chest")

COLORS = ["酒红", "咖啡", "巧克力", "亚麻", "琥珀", "彩虹", "渐变", "挑染", "双色",
          "银白", "黑色", "棕色", "金色", "银色", "白色", "红色", "蓝色", "粉色",
          "紫色", "灰色", "橙色", "绿色", "青色", "黄色", "褐色", "米色", "墨绿",
          "黑", "棕", "金", "银", "白", "红", "蓝", "粉", "紫", "灰", "橙",
          "绿", "青", "黄", "褐", "米"]
STYLES = ["长发", "短发", "中发", "卷发", "直发", "马尾", "辫", "刘海", "丸子头",
          "呆毛", "波波头", "盘发", "散发", "披肩", "麻花", "螺旋", "爆炸",
          "寸头", "平头", "波浪", "公主切", "双马尾", "单马尾"]


def norm(s):
    return re.sub(r"[\s，,。.;；、]", "", str(s or ""))


def color_of(s):
    s = norm(s)
    for c in COLORS:
        if c in s:
            return c
    return ""


def style_of(s):
    s = norm(s)
    for c in STYLES:
        if c in s:
            return c
    return ""


def hair_short(color):
    if not color:
        return ""
    if color.endswith("色"):
        return color + "头发"
    return color + "色头发"


def main():
    doc = json.load(open(TAGS_PATH, encoding="utf-8"))
    tags = doc["tags"]
    c1 = json.load(open(C1, encoding="utf-8"))["chars"]
    c2 = json.load(open(C2, encoding="utf-8"))

    stats = {"hair_full": 0, "hair_color": 0, "hair_none": 0,
             "eyes_full": 0, "eyes_color": 0, "eyes_none": 0,
             "outfit": 0, "outfit_none": 0, "unverified": 0}
    changed = 0
    for x in tags:
        if x.get("cat") != "角色":
            continue
        en = x.get("en")
        first = c1.get(en)
        if not first:
            continue
        second = c2.get(en)
        if not second:
            # 第一轮补过、第二轮没复核到 → 按「宁可留空」清掉三项
            app = x.get("app") or {}
            if any(app.get(k) for k in ("hair", "eyes", "outfit")):
                for k in ("hair", "eyes", "outfit"):
                    app[k] = ""
                x["app"] = app
                changed += 1
            stats["unverified"] += 1
            continue
        app = dict(x.get("app") or {k: "" for k in FIELDS})
        # 发色
        c1h, c2h = color_of(first.get("hair")), color_of(second.get("hair"))
        s1h, s2h = style_of(first.get("hair")), style_of(second.get("hair"))
        if c1h and c1h == c2h and s1h and s1h == s2h and norm(first.get("hair")) == norm(second.get("hair")):
            new_hair = first["hair"]
            stats["hair_full"] += 1
        elif c1h and c1h == c2h:
            new_hair = hair_short(c1h)
            stats["hair_color"] += 1
        elif s1h and s1h == s2h and not c1h and not c2h:
            new_hair = s1h
            stats["hair_color"] += 1
        else:
            new_hair = ""
            stats["hair_none"] += 1
        # 瞳色
        c1e, c2e = color_of(first.get("eyes")), color_of(second.get("eyes"))
        if c1e and c1e == c2e and norm(first.get("eyes")) == norm(second.get("eyes")):
            new_eyes = first["eyes"]
            stats["eyes_full"] += 1
        elif c1e and c1e == c2e:
            new_eyes = c1e + "色眼睛"
            stats["eyes_color"] += 1
        else:
            new_eyes = ""
            stats["eyes_none"] += 1
        # 服装（两次一致才留）
        o1, o2 = norm(first.get("outfit")), norm(second.get("outfit"))
        if o1 and o2 and (o1 == o2 or (o1 in o2 or o2 in o1) and abs(len(o1) - len(o2)) <= 4):
            new_outfit = first["outfit"]
            stats["outfit"] += 1
        else:
            new_outfit = ""
            stats["outfit_none"] += 1
        old = (app.get("hair", ""), app.get("eyes", ""), app.get("outfit", ""))
        app["hair"], app["eyes"], app["outfit"] = new_hair, new_eyes, new_outfit
        if (new_hair, new_eyes, new_outfit) != old:
            changed += 1
        x["app"] = {k: app.get(k, "") for k in FIELDS}

    print("发色: 完整 %d / 仅颜色 %d / 清空 %d" % (stats["hair_full"],
                                                stats["hair_color"], stats["hair_none"]))
    print("瞳色: 完整 %d / 仅颜色 %d / 清空 %d" % (stats["eyes_full"],
                                                stats["eyes_color"], stats["eyes_none"]))
    print("服装: 保留 %d / 清空 %d" % (stats["outfit"], stats["outfit_none"]))
    print("未复核清空 %d；变更 %d" % (stats["unverified"], changed))
    filled = sum(1 for x in tags if x.get("cat") == "角色" and isinstance(x.get("app"), dict)
                 and x["app"].get("hair"))
    print("最终有发色的角色 %d" % filled)
    if not changed:
        print("无改动")
        return
    bak = os.path.join(HERE, "tags_cn.backup_reconcile_%s.json"
                       % datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(TAGS_PATH, bak)
    print("[备份] %s" % os.path.basename(bak))
    s = json.dumps(doc, ensure_ascii=False, indent=1).replace("\n", "\r\n")
    tmp = TAGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, TAGS_PATH)
    print("[写盘] ok")


if __name__ == "__main__":
    main()
