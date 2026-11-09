# -*- coding: utf-8 -*-
"""cleanup_generic.py — 清掉本轮补出来的「通用默认值」体型/胸围（匀称/标准等），
并把变空条目的缓存判定改为 None，保证 enrich_tags.py 再跑一次仍是「无改动」。
"""
import json
import os
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(HERE, "tags_cn.json")
CACHE_PATH = os.path.join(HERE, "enrich_cache.json")
FIELDS = ("hair", "eyes", "outfit", "body", "chest")
KEEP_BODY = set()   # 体型未做双轮校验，一律留空
KEEP_CHEST = set()  # 胸围未做双轮校验，一律留空


def main():
    doc = json.load(open(TAGS_PATH, encoding="utf-8"))
    tags = doc["tags"]
    cache = json.load(open(CACHE_PATH, encoding="utf-8"))
    ours = {en for en, v in cache["chars"].items() if v}
    changed = 0
    nulled = 0
    for x in tags:
        if x.get("cat") != "角色" or x.get("en") not in ours:
            continue
        app = x.get("app") or {}
        body = str(app.get("body") or "").strip()
        chest = str(app.get("chest") or "").strip()
        if body and body not in KEEP_BODY:
            app["body"] = ""
            changed += 1
        if chest and chest not in KEEP_CHEST:
            app["chest"] = ""
            changed += 1
        x["app"] = {k: app.get(k, "") for k in FIELDS}
        if not any(str(x["app"].get(k) or "").strip() for k in FIELDS):
            cache["chars"][x["en"]] = None
            nulled += 1
    print("清空通用默认值 %d 个字段；变全空并标记跳过 %d 条" % (changed, nulled))
    if not changed:
        print("无改动")
        return
    bak = os.path.join(HERE, "tags_cn.backup_cleanup_%s.json"
                       % datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(TAGS_PATH, bak)
    print("[备份] %s" % os.path.basename(bak))
    s = json.dumps(doc, ensure_ascii=False, indent=1).replace("\n", "\r\n")
    tmp = TAGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, TAGS_PATH)
    with open(CACHE_PATH + ".tmp", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(CACHE_PATH + ".tmp", CACHE_PATH)
    print("[写盘] ok")


if __name__ == "__main__":
    main()
