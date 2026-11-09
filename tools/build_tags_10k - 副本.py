# -*- coding: utf-8 -*-
"""把 tags_cn.json 扩到 >= 10000 条（只追加、不改已有条目的 cat+zh / cat+en 去重）。

规则:
  - 已有条目一个都不删、不改，新条目排在后面
  - 按 (cat, zh) 与 (cat, en) 双重去重（en 归一化：小写、- 和空格 -> 下划线）
  - 「自定义」分类不新增
  - 新增条目 NSFW 占比 >= 55%
  - 可重复运行：第二次运行时所有候选都已存在，产出与第一次完全一致（md5 相同）

运行: python build_tags_10k.py
"""
import json
import os
import shutil
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
LIB = os.path.join(HERE, "tags_cn.json")

# 目标总数（按 cat），以及每个 cat 必须达到的 NSFW 数
TARGET = {"动作": 3050, "服装": 1950, "道具": 1540, "外形": 1310, "场景": 1190}
NSFW_MIN = {"动作": 1800, "道具": 800, "服装": 600, "外形": 400, "场景": 0}
# 子类配额（软上限；不够时由同类其它子类补足）
QUOTA = {
    "动作": {"姿势": 240, "日常": 280, "单人": 380, "双人互动": 480, "亲密": 482},
    "服装": {"上装": 120, "下装": 130, "连衣裙": 90, "制服": 110, "泳装": 80,
             "配饰": 140, "情趣": 560, "袜鞋": 120},
    "道具": {"全部": 1138},
    "外形": {"发色": 55, "发型": 105, "眼睛": 75, "表情": 100, "体型": 62, "身体": 400},
    "场景": {"室内": 190, "室外": 220, "光线": 120, "天气": 70, "时间段": 60, "建筑": 164},
}
# 追加后各分类的硬性要求
REQ = {
    "动作": {"总NSFW": 1800},
    "道具": {"总NSFW": 800},
    "外形": {"身体NSFW": 400},
    "服装": {"情趣": 600},
}

import tags10k_action as D_ACTION
import tags10k_cloth as D_CLOTH
import tags10k_prop as D_PROP
import tags10k_look as D_LOOK
import tags10k_scene as D_SCENE

POOLS = {
    "动作": D_ACTION.ITEMS,
    "服装": D_CLOTH.ITEMS,
    "道具": D_PROP.ITEMS,
    "外形": D_LOOK.ITEMS,
    "场景": D_SCENE.ITEMS,
}

ORIGINAL_TOTAL = 4188          # 首次扩容前的条数
ORIGINAL_NSFW = 748

# 必备翻译：无论分类是否已到目标，都保证存在
MUST_ADD = [
    ("外形", "身体", True, "身上沾精液", "cum_on_body"),
    ("外形", "身体", True, "胸部沾精液", "cum_on_breasts"),
    ("外形", "身体", True, "无码", "uncensored"),
    ("道具", "全部", True, "性玩具", "sex_toy"),
    ("外形", "发型", False, "刘海", "bangs"),
    ("外形", "身体", False, "穿孔饰品", "piercing"),
    # 重点方向覆盖（缺失补点）
    ("动作", "亲密", True, "侧面位", "side_position_sex"),
    ("动作", "亲密", True, "束缚性交", "bound_intercourse"),
    ("服装", "情趣", True, "破坏版比基尼", "torn_bikini"),
]

# 只对「本次扩容后追加」的条目做改名，绝不碰原有 4188 条
RENAME = {
    ("外形", "spread_pussy"): ("掰开小穴", None),
    ("服装", "hair_accessory"): ("发饰", "hair_ornament"),
}


def apply_renames(final):
    from collections import Counter
    zhs = Counter((t["cat"], t["zh"]) for t in final)
    ens = Counter((t["cat"], norm_en(t["en"])) for t in final)
    for i, t in enumerate(final):
        if i < ORIGINAL_TOTAL:
            continue
        key = (t["cat"], norm_en(t["en"]))
        if key not in RENAME:
            continue
        nz, ne = RENAME[key]
        nz = nz or t["zh"]
        ne = ne or t["en"]
        nkz, nke = (t["cat"], nz), (t["cat"], norm_en(ne))
        if (nkz != (t["cat"], t["zh"]) and zhs[nkz]) or (nke != key and ens[nke]):
            continue
        zhs[(t["cat"], t["zh"])] -= 1
        ens[key] -= 1
        t["zh"], t["en"] = nz, ne
        zhs[nkz] += 1
        ens[nke] += 1


def apply_must(final):
    zhs = {(t["cat"], t["zh"]) for t in final}
    ens = {(t["cat"], norm_en(t["en"])) for t in final}
    added = []
    for cat, sub, nsfw, zh, en in MUST_ADD:
        kz, ke = (cat, zh), (cat, norm_en(en))
        if kz in zhs or ke in ens:
            continue
        t = {"zh": zh, "en": en, "cat": cat, "sub": sub, "nsfw": bool(nsfw)}
        final.append(t)
        zhs.add(kz)
        ens.add(ke)
        added.append(t)
    return added


def norm_en(s):
    return (s or "").strip().lower().replace("-", "_").replace(" ", "_")


def load():
    with open(LIB, encoding="utf-8") as f:
        doc = json.load(f)
    return doc, doc["tags"]


def backup_once(count):
    """只在首次扩容（原文 4188 条）时备份，避免重复运行刷屏。"""
    if count >= 10000:
        return None
    dst = os.path.join(HERE, "tags_cn.backup_%s.json" % datetime.now().strftime("%Y%m%d_%H%M"))
    if not os.path.exists(dst):
        shutil.copyfile(LIB, dst)
    return dst


def select(cat, pool, need, quota, nsfw_min, zhset, enset):
    """从候选池挑 need 条；先按子类配额，再从同类别剩余候选补齐。"""
    chosen, usedz, usede, added_idx = [], set(), set(), set()

    def ok(i):
        sub, nsfw, zh, en = pool[i]
        zh, en = (zh or "").strip(), norm_en(en)
        if not zh or not en:
            return False
        kz, ke = (cat, zh), (cat, en)
        return not (kz in zhset or ke in enset or kz in usedz or ke in usede)

    def take(i):
        sub, nsfw, zh, en = pool[i]
        zh, en = zh.strip(), norm_en(en)
        chosen.append({"zh": zh, "en": en, "cat": cat, "sub": sub, "nsfw": bool(nsfw)})
        usedz.add((cat, zh))
        usede.add((cat, en))
        added_idx.add(i)

    bysub = {}
    for i, e in enumerate(pool):
        bysub.setdefault(e[0], []).append(i)

    for sub, q in quota.items():
        n = 0
        for i in bysub.get(sub, []):
            if n >= q:
                break
            if ok(i):
                take(i)
                n += 1

    if len(chosen) < need:
        for i in range(len(pool)):
            if len(chosen) >= need:
                break
            if i not in added_idx and ok(i):
                take(i)

    # NSFW 不够：继续追加 NSFW 候选（允许略超目标数）
    if sum(1 for x in chosen if x["nsfw"]) < nsfw_min:
        for i in range(len(pool)):
            if sum(1 for x in chosen if x["nsfw"]) >= nsfw_min:
                break
            if i in added_idx or not pool[i][1] or not ok(i):
                continue
            take(i)
    return chosen


def main():
    doc, tags = load()
    orig_count = len(tags)
    bpath = backup_once(orig_count)

    zhset = {(t["cat"], t["zh"]) for t in tags}
    enset = {(t["cat"], norm_en(t["en"])) for t in tags}
    from collections import Counter
    before = Counter(t["cat"] for t in tags)

    appended = []
    for cat, pool in POOLS.items():
        cur = before.get(cat, 0)
        need = max(0, TARGET[cat] - cur)
        if need == 0:
            continue
        part = select(cat, pool, need, QUOTA[cat], NSFW_MIN[cat], zhset, enset)
        appended.extend(part)
        zhset.update((cat, x["zh"]) for x in part)
        enset.update((cat, norm_en(x["en"])) for x in part)

    final = tags + appended
    apply_renames(final)
    must_added = apply_must(final)

    # ---------- 校验 ----------
    from collections import Counter
    cnt = Counter(t["cat"] for t in final)
    subcnt = Counter((t["cat"], t.get("sub")) for t in final)
    total = len(final)
    nsfw_all = sum(1 for t in final if t["nsfw"])
    new_count = total - ORIGINAL_TOTAL
    new_nsfw = nsfw_all - ORIGINAL_NSFW
    custom_cnt = cnt.get("自定义", 0)
    body_nsfw = sum(1 for t in final if t["cat"] == "外形" and t.get("sub") == "身体" and t["nsfw"])
    act_nsfw = sum(1 for t in final if t["cat"] == "动作" and t["nsfw"])
    prop_nsfw = sum(1 for t in final if t["cat"] == "道具" and t["nsfw"])
    ling_cnt = subcnt.get(("服装", "情趣"), 0)

    dups = Counter((t["cat"], t["zh"]) for t in final)
    dup_zh = [k for k, v in dups.items() if v > 1]
    dups_en = Counter((t["cat"], norm_en(t["en"])) for t in final)
    dup_en = [k for k, v in dups_en.items() if v > 1]
    bad = [t for t in final if not all(t.get(k) for k in ("zh", "en", "cat", "sub"))]

    print("=" * 62)
    print("原有条数 :", ORIGINAL_TOTAL, "  本次追加:", len(appended), " 必备补齐:", len(must_added))
    print("新增条数 :", new_count, "  新增 NSFW:", new_nsfw,
          "(%.1f%%)" % (100.0 * new_nsfw / new_count if new_count else 0))
    print("实际总数 :", total, "  全库 NSFW:", nsfw_all)
    print("各分类   :", {k: cnt[k] for k in ("动作", "服装", "道具", "外形", "场景", "角色", "自定义")})
    print("  自定义 :", custom_cnt, "(原 639)")
    print("  动作NSFW:", act_nsfw, " 道具NSFW:", prop_nsfw,
          " 身体NSFW:", body_nsfw, " 情趣:", ling_cnt)
    print("子类分布 :")
    for cat in ("动作", "服装", "道具", "外形", "场景"):
        parts = ["%s=%d" % (s, n) for (c, s), n in sorted(subcnt.items()) if c == cat]
        print("   %s: %s" % (cat, " ".join(parts)))
    if bpath:
        print("备份文件 :", os.path.basename(bpath))

    assert total >= 10000, "总数不足: %d" % total
    assert not dup_zh, "cat+zh 重复: %s" % dup_zh[:5]
    assert not dup_en, "cat+en 重复: %s" % dup_en[:5]
    assert not bad, "字段缺失: %s" % bad[:3]
    assert custom_cnt == 639, "「自定义」被改动: %d" % custom_cnt
    assert new_nsfw >= 0.55 * new_count, "新增 NSFW 占比不足: %.1f%%" % (100.0 * new_nsfw / new_count)
    assert act_nsfw >= 1800 and prop_nsfw >= 800 and ling_cnt >= 600 and body_nsfw >= 400, "NSFW 配额不足"
    for _en in ("spread_pussy", "cum_on_body", "cum_on_breasts", "uncensored", "sex_toy",
                "bangs", "piercing", "hair_ornament", "detached_sleeves",
                "nipple_piercing", "navel", "belly"):
        assert any(norm_en(t["en"]) == _en for t in final), "缺必备翻译: " + _en

    doc["tags"] = final
    doc.setdefault("version", 3)
    with open(LIB, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("已写入 :", LIB)

    # 抽查 10 条 NSFW（取首次扩容后追加的部分）
    picks = [t for t in final[ORIGINAL_TOTAL:] if t["nsfw"]][:10]
    print("-" * 62)
    print("新增 NSFW 抽样 10 条:")
    for i, t in enumerate(picks, 1):
        print(" %2d. %-9s %-7s %-26s %s" % (i, t["cat"], t["sub"], t["zh"], t["en"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
