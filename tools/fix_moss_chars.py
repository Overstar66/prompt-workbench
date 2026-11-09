# -*- coding: utf-8 -*-
"""把 tags_cn.json 里 cat=角色 & sub=MOSS原创 的 5 条改成 A~E 五个人设（幂等）。

规则：
  * 现有 MOSS原创 条目按 zh 排序，依次对应 A B C D E；
  * 不足 5 条：缺的补齐（zh=角色X，en=moss_original_x）；
  * 超过 5 条：只改前 5 条，其余不动；
  * zh / en 一律不改（新增条目除外）。
  * custom_chars.json 里 from/en 命中这 5 个 en 的覆盖层同步改成同一份 app，
    否则 /api/tags 会用覆盖层的旧外貌盖掉 tags_cn.json（不删除任何自定义角色）。

只有真的有改动才备份 tags_cn.backup_moss_<时间>.json 并写文件，
所以连跑两遍结果一致、第二遍不产生新备份。
"""
import json
import os
import shutil
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = os.path.join(HERE, "tags_cn.json")
CHARS = os.path.join(HERE, "custom_chars.json")
SUB = "MOSS原创"
FIELDS = ("hair", "eyes", "outfit", "body", "chest")

# 表里给出的 5 个人设；app 字段按题目映射规则填
TARGETS = [
    {   # A
        "letter": "A",
        "app": {"hair": "白色长直发", "eyes": "红色眼睛", "outfit": "",
                "body": "高挑纤细，皮肤白皙", "chest": "标准"},
    },
    {   # B
        "letter": "B",
        "app": {"hair": "金色双马尾", "eyes": "蓝色眼睛", "outfit": "",
                "body": "娇小丰满，皮肤白里透红", "chest": "巨乳"},
    },
    {   # C
        "letter": "C",
        "app": {"hair": "银色短发", "eyes": "紫色眼睛", "outfit": "",
                "body": "匀称修长，皮肤偏冷白", "chest": "标准"},
    },
    {   # D
        "letter": "D",
        "app": {"hair": "棕色高马尾", "eyes": "棕色眼睛", "outfit": "",
                "body": "娇小匀称，皮肤健康", "chest": "标准"},
    },
    {   # E
        "letter": "E",
        "app": {"hair": "粉色中长散发", "eyes": "粉色眼睛", "outfit": "",
                "body": "娇小有肉感，皮肤白嫩", "chest": "丰满"},
    },
]


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def dump_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def norm_app(app):
    return {k: str((app or {}).get(k) or "") for k in FIELDS}


def main():
    data = load_json(TAGS, None)
    if not isinstance(data, dict) or not isinstance(data.get("tags"), list):
        raise SystemExit("tags_cn.json 结构异常，放弃")
    tags = data["tags"]

    moss = [(i, t) for i, t in enumerate(tags)
            if isinstance(t, dict) and t.get("cat") == "角色" and t.get("sub") == SUB]
    moss.sort(key=lambda p: str(p[1].get("zh") or ""))
    print(f"[扫描] sub={SUB} 现有 {len(moss)} 条：")
    for i, t in moss:
        print(f"  idx={i} zh={t.get('zh')!r} en={t.get('en')!r} app={json.dumps(t.get('app') or {}, ensure_ascii=False)}")

    changed, added = 0, 0

    # 1) 前 5 条：只改 app
    for k, (idx, t) in enumerate(moss[:len(TARGETS)]):
        want = norm_app(TARGETS[k]["app"])
        if norm_app(t.get("app")) != want:
            t["app"] = want
            changed += 1
            print(f"[改] {t.get('zh')}/{t.get('en')} → {want['hair']} / {want['eyes']} / chest={want['chest']}")

    # 2) 不足 5 条：补齐，插在最后一条 MOSS原创 之后
    have = len(moss)
    if have < len(TARGETS):
        insert_at = (moss[-1][0] + 1) if moss else len(tags)
        for k in range(have, len(TARGETS)):
            letter = TARGETS[k]["letter"]
            rec = {
                "zh": f"角色{letter}",
                "en": f"moss_original_{letter.lower()}",
                "cat": "角色",
                "sub": SUB,
                "nsfw": False,
                "app": norm_app(TARGETS[k]["app"]),
            }
            tags.insert(insert_at, rec)
            insert_at += 1
            added += 1
            print(f"[增] {rec['zh']}/{rec['en']}")

    # 3) custom_chars.json 里的覆盖层（from/en 命中这 5 个 en）同步 app，不删记录
    codes = {}
    for idx, t in [(i, t) for i, t in enumerate(tags)
                   if isinstance(t, dict) and t.get("cat") == "角色" and t.get("sub") == SUB]:
        codes[str(t.get("en") or "")] = t.get("app")
    chars = load_json(CHARS, [])
    chars_changed = 0
    if isinstance(chars, list):
        for c in chars:
            if not isinstance(c, dict):
                continue
            key = str(c.get("from") or "").strip() or str(c.get("en") or "").strip()
            want = codes.get(key)
            if want is None:
                continue
            if norm_app(c.get("app")) != norm_app(want):
                c["app"] = norm_app(want)
                chars_changed += 1
                print(f"[同步覆盖层] {c.get('zh')}/{c.get('en')} from={c.get('from')}")

    if not (changed or added or chars_changed):
        print("[结果] 已是目标状态，无需改动（不备份、不写文件）")
        return 0

    backup = os.path.join(HERE, time.strftime("tags_cn.backup_moss_%Y%m%d_%H%M%S.json"))
    shutil.copy2(TAGS, backup)
    print(f"[备份] {os.path.basename(backup)}")
    dump_json(TAGS, data)
    if chars_changed:
        dump_json(CHARS, chars)
    print(f"[完成] 改 {changed} 条 / 新增 {added} 条 / 覆盖层同步 {chars_changed} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
