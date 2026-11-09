# -*- coding: utf-8 -*-
"""修正 tags_cn.json 里「角色」条目的作品字段 sub（幂等）。

规则只做**明确可判定**的：
  1. 逢坂大河 / aisaka_taiga            → 龙与虎
  2. en 后缀 _(arknights) / 明日方舟角色 → 明日方舟
  3. _(azur_lane)                       → 碧蓝航线
  4. _(blue_archive)                    → 蔚蓝档案
  5. _(genshin_impact) / 原神角色        → 原神
  6. _(honkai_star_rail)                → 崩坏星穹铁道
  7. 明日香·兰格雷 / souryuu_asuka_langley → EVA

其余 sub 为空或只是占位（游戏 / 动漫）的条目**不做猜测**，只在报告里列出数量。
第一次真正改动前会备份为 tags_cn.backup_subs_<时间>.json；没有改动则不写文件也不备份，
所以连跑两遍结果一致。
"""
import json
import os
import re
import shutil
import time
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = os.path.join(HERE, "tags_cn.json")

# sub 不是具体作品的占位值（空串也算）
PLACEHOLDER = {"", "游戏", "动漫"}

# en 后缀 → 作品名（honkai_star_rail 在数据里写作 honkai:_star_rail，统一归一化）
SUFFIX_SUB = {
    "arknights": "明日方舟",
    "azur_lane": "碧蓝航线",
    "blue_archive": "蔚蓝档案",
    "genshin_impact": "原神",
    "honkai_star_rail": "崩坏星穹铁道",
}

# 名字明确属于某作品、但 en 没有后缀的角色（只列数据里确实存在的名字）
ARKNIGHTS_ZH = {
    "阿米娅", "凯尔希", "德克萨斯", "能天使", "斯卡蒂", "史尔特尔", "陈", "银灰",
    "歌蕾蒂娅", "泥岩", "令", "号角", "夜莺", "闪灵", "星熊", "推进之王", "安洁莉娜",
    "黑", "白金", "蓝毒", "空", "初雪", "崖心", "拉普兰德", "莫斯提马", "森蚺",
    "温蒂", "早露", "瑕光", "迷迭香", "棘刺", "山", "焰尾", "耀骑士临光",
    "归溟幽灵鲨", "百炼嘉维尔", "浊心斯卡蒂", "菲亚梅塔", "多萝西", "鸿雪",
    "缄默德克萨斯", "白面鸮", "赫默", "麦哲伦", "刻俄柏", "艾雅法拉", "伊芙利特",
    "天火", "砾", "流星", "杰西卡", "蛇屠箱", "古米",
}
GENSHIN_ZH = {
    "空（原神）", "派蒙", "温迪", "钟离", "行秋", "重云", "迪卢克", "凯亚", "七七",
    "早柚", "九条裟罗", "神里绫人", "荒泷一斗", "枫原万叶", "提纳里", "赛诺",
    "流浪者", "那维莱特", "迪希雅", "坎蒂丝", "多莉", "柯莱",
}

# 明确的一对一修正：(en, zh) → sub
EXPLICIT = [
    (("aisaka_taiga", "逢坂大河"), "龙与虎"),
    (("souryuu_asuka_langley", "明日香·兰格雷"), "EVA"),
]


def norm_en(en):
    return re.sub(r"[^a-z0-9]+", "_", (en or "").strip().lower()).strip("_")


def suffix_of(en):
    """取 en 末尾的 _(...) 后缀并归一化（honkai:_star_rail → honkai_star_rail）。"""
    m = re.search(r"_\(([a-z0-9:_]+)\)\s*$", (en or "").lower())
    if not m:
        return ""
    return re.sub(r"_+", "_", m.group(1).replace(":", "_")).strip("_")


def sub_is_placeholder(sub):
    return str(sub or "").strip() in PLACEHOLDER


def target_sub(tag):
    """返回该条目「明确可判定」的作品名，判定不了返回 None。"""
    raw_en = str(tag.get("en") or "").strip()
    en = norm_en(raw_en)
    zh = str(tag.get("zh") or "").strip()

    for (e, z), want in EXPLICIT:
        if en == e or zh == z:
            return want
    suf = suffix_of(raw_en)
    if suf in SUFFIX_SUB:
        return SUFFIX_SUB[suf]
    if zh in ARKNIGHTS_ZH:
        return "明日方舟"
    if zh in GENSHIN_ZH:
        return "原神"
    return None


def stat(tags):
    chars = [t for t in tags if t.get("cat") == "角色"]
    empty = [t for t in chars if not str(t.get("sub") or "").strip()]
    unk = [t for t in chars if sub_is_placeholder(t.get("sub"))]
    return chars, empty, unk


def main():
    with open(TAGS, encoding="utf-8") as f:
        data = json.load(f)
    tags = data.get("tags") or []

    chars, empty, unk = stat(tags)
    print("=" * 62)
    print("【修正前】")
    print("  角色总数：%d" % len(chars))
    print("  sub 为空：%d" % len(empty))
    print("  sub 为空 / 不是具体作品（游戏·动漫占位）：%d" % len(unk))
    print("  其中前 30 条：")
    for t in unk[:30]:
        print("    - %s | %s | sub=%r" % (t.get("zh"), t.get("en"), t.get("sub")))

    # 只改「判定出的作品」和现有 sub 不一致的条目
    changes = []
    for t in chars:
        want = target_sub(t)
        if want and str(t.get("sub") or "").strip() != want:
            changes.append((t, str(t.get("sub") or "").strip(), want))

    if not changes:
        print("\n没有可明确判定的条目需要修正 —— 数据已是目标状态（幂等，跳过备份/写盘）。")
    else:
        bak = os.path.join(HERE, "tags_cn.backup_subs_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(TAGS, bak)
        print("\n已备份：%s" % os.path.basename(bak))
        cnt = collections.Counter(want for _, _, want in changes)
        for t, old, want in changes:
            t["sub"] = want
        tmp = TAGS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, TAGS)
        print("已修正 %d 条：" % len(changes))
        for want, n in cnt.most_common():
            print("  %-14s %d 条" % (want, n))
        print("  明细：")
        for t, old, want in changes[:40]:
            print("    %s | %s : %r → %r" % (t.get("zh"), t.get("en"), old, want))
        if len(changes) > 40:
            print("    …（其余 %d 条省略）" % (len(changes) - 40))

    chars, empty, unk = stat(tags)
    print("\n【修正后】")
    print("  角色总数：%d" % len(chars))
    print("  sub 为空：%d" % len(empty))
    print("  sub 为空 / 不是具体作品（游戏·动漫占位）：%d" % len(unk))
    if unk:
        print("  无法判定的条目（不猜，仅列出）：")
        by_sub = collections.Counter(str(t.get("sub") or "").strip() or "<空>" for t in unk)
        for s, n in by_sub.most_common():
            print("    sub=%-8s %d 条" % (s, n))
    # 修正后各作品计数（只有角色分类）
    print("\n  角色 sub 分布（Top 30）：")
    for s, n in collections.Counter(str(t.get("sub") or "").strip() or "<空>"
                                    for t in chars).most_common(30):
        print("    %-16s %d" % (s, n))
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
