# -*- coding: utf-8 -*-
"""合并 tags_cn.json 里 cat == "角色" 的同名(zh)重复条目。

两个阶段（都只写 tags_cn.json，chars_extra.json 只读）：
  阶段 1 组内去重：tags_cn.json 内部同 zh 的多条，留最优一条，其余删除；
  阶段 2 跨文件去重：tags_cn.json 的「图反推」条目如果和 chars_extra.json 里的
         精修条目是同一个角色（同 zh 且 en 对得上），删掉图反推那条 ——
         app.py 的 load_lib() 会把 chars_extra.json 拼进来，不删就是 /api/tags 里的重名。

幂等：重复运行不会二次改动（第 2 次既没有组内重名、也没有可删的跨文件重复，
直接退出、不写文件、不备份）。每次真正改动前备份 tags_cn.backup_merge_<YYYYmmdd_HHMMSS>.json。

保留「最优」一条的优先级（见 rank_key）：
  1) 来源更可靠：sub != "图反推"（内置精修 / 用户自建）优先
     —— 图反推条目的 sub 只是来源标记，没有作品信息；
  2) app 更完整：hair / eyes 至少一项非空；
  3) en 更规范：无 . / __ / 首尾下划线等拼写异常，消歧括号更少。
注：规则 1 之所以排在 app 前面，是因为「app 缺失」可以由下面的字段合并补齐，
    而丢掉作品 sub 补不回来。要按字面「app 优先」跑，把 SOURCE_FIRST 改成 False。

合并：保留条缺的字段从被删条目补（仅补非空值，不覆盖已有值）；
有多个被删条目时按同样的优先级顺序合并，好数据先占位。

用法：python merge_dup_chars.py [--dry-run]
"""
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(HERE, "tags_cn.json")
EXTRA_PATH = os.path.join(HERE, "chars_extra.json")
REPORT_PATH = os.path.join(HERE, "merge_dup_chars_report.txt")

REVERSE_SUB = "图反推"
APP_KEYS = ("hair", "eyes", "outfit", "body", "chest")
SCALAR_KEYS = ("sub", "nsfw", "custom", "from")
SOURCE_FIRST = True          # False → 严格按字面「app 优先」

DRY = "--dry-run" in sys.argv


def app_ok(t):
    """app 是否「完整」：hair / eyes 至少一项非空。"""
    a = t.get("app")
    if not isinstance(a, dict):
        return False
    return bool(str(a.get("hair") or "").strip() or str(a.get("eyes") or "").strip())


def en_score(t):
    """en 规范性打分，越高越规范。"""
    en = str(t.get("en") or "").strip()
    if not en:
        return -100
    s = 0
    if "." in en:
        s -= 8                      # yorha_no._2_type_b / a.b 这类
    if "__" in en:
        s -= 6
    if en.startswith("_") or en.endswith("_"):
        s -= 6
    s -= 2 * en.count("(")          # 消歧括号：少一点更干净
    if re.search(r"[^0-9a-z_()!:.\-]", en):
        s -= 5
    return s


def rank_key(t):
    if SOURCE_FIRST:
        return (0 if str(t.get("sub") or "") == REVERSE_SUB else 1,
                1 if app_ok(t) else 0,
                en_score(t))
    return (1 if app_ok(t) else 0,
            0 if str(t.get("sub") or "") == REVERSE_SUB else 1,
            en_score(t))


def en_tokens(en):
    return {x for x in re.split(r"[^0-9a-z]+", str(en or "").lower()) if x}


def paren_tokens(en):
    """en 里消歧括号中的词，如 rem_(re:zero) → {re, zero}。"""
    out = set()
    for seg in re.findall(r"\(([^)]*)\)", str(en or "")):
        out |= en_tokens(seg)
    return out


def app_merge_verdict(keep, drop, sub_tokens=None):
    """被删条目的外观能不能并到保留条目上。

    same    : en 有共同词 / 括号里的作品与保留条对得上 → 同一角色，正常合并
    unknown : 两边毫无交集也没有冲突证据 → 合并，但在报告里标出来人工看一眼
    conflict: 括号里写着别的作品，和保留条的作品/en 对不上 → 疑似同名不同人，跳过外观合并

    sub_tokens：作品(sub) → 该作品其它角色 en 词表的索引（数据驱动，中文 sub 也能比对）。
    """
    keep_tok = en_tokens(keep.get("en")) | en_tokens(keep.get("sub"))
    drop_tok = en_tokens(drop.get("en"))
    if keep_tok & drop_tok:
        return "same"
    pt = paren_tokens(drop.get("en"))
    if pt:
        fam = (sub_tokens or {}).get(str(keep.get("sub") or ""), set())
        return "same" if (pt & (keep_tok | fam)) else "conflict"
    return "unknown"


def pending_app(keep, drop):
    """drop 有多少 app 子字段是 keep 缺的（用于判断合并是否真的会改动）。"""
    dapp = drop.get("app")
    if not isinstance(dapp, dict):
        return 0
    kapp = keep.get("app") if isinstance(keep.get("app"), dict) else {}
    return sum(1 for k in APP_KEYS
               if str(dapp.get(k) or "").strip() and not str(kapp.get(k) or "").strip())


def same_person_by_en(a_en, b_en):
    """两个 en 是不是同一个角色：共同词 / 一方的消歧括号命中另一方名字。"""
    ta, tb = en_tokens(a_en), en_tokens(b_en)
    if ta & tb:
        return True
    pa, pb = paren_tokens(a_en), paren_tokens(b_en)
    return bool((pa and (pa & tb)) or (pb and (pb & ta)))


def load_extra():
    """chars_extra.json 里的角色条目（只读，用来判断跨文件重复）。"""
    try:
        arr = json.load(open(EXTRA_PATH, encoding="utf-8"))
    except Exception:
        return []
    return [e for e in arr if isinstance(e, dict) and e.get("cat") == "角色"]


def cross_file_pass(tags, skip=()):
    """阶段 2：删掉 tags_cn 里和 chars_extra.json 精修条目重复的「图反推」条目。

    返回 (待删索引集合, 明细行列表)。明细：(zh, 被删 en, 保留来源 en/sub, 丢失的外观字段)
    """
    extra = load_extra()
    by_zh = defaultdict(list)
    for e in extra:
        by_zh[str(e.get("zh") or "").strip()].append(e)
    kill, rows = set(), []
    for i, t in enumerate(tags):
        if i in skip:
            continue
        if t.get("cat") != "角色" or str(t.get("sub") or "") != REVERSE_SUB:
            continue
        zh = str(t.get("zh") or "").strip()
        for e in by_zh.get(zh, []):
            if str(e.get("sub") or "") == REVERSE_SUB:
                continue
            if not same_person_by_en(t.get("en"), e.get("en")):
                continue          # 同名不同人（胡桃 原神 vs 胡桃 莉可丽丝）
            eapp = e.get("app") if isinstance(e.get("app"), dict) else {}
            lost = [k for k in APP_KEYS
                    if str((t.get("app") or {}).get(k) or "").strip()
                    and not str(eapp.get(k) or "").strip()]
            kill.add(i)
            rows.append((zh, t.get("en"), "%s / %s" % (e.get("en"), e.get("sub")),
                         ", ".join(lost) or "-"))
            break
    return kill, rows


def merge_missing(keep, drop, allow_app=True):
    """把 drop 里 keep 缺的非空字段补进来；返回补上的字段名列表。"""
    added = []
    dapp = drop.get("app")
    if allow_app and isinstance(dapp, dict) and pending_app(keep, drop):
        kapp = keep.get("app")
        if not isinstance(kapp, dict):
            kapp = {k: "" for k in APP_KEYS}
            keep["app"] = kapp
        for k in APP_KEYS:
            v = str(dapp.get(k) or "").strip()
            if v and not str(kapp.get(k) or "").strip():
                kapp[k] = v
                added.append("app." + k)
    for k in SCALAR_KEYS:
        if k in keep:
            if str(keep.get(k) or "").strip():
                continue
            if k == "nsfw":
                continue
        v = drop.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        keep[k] = v
        added.append(k)
    return added


def main():
    data = json.load(open(TAGS_PATH, encoding="utf-8"))
    tags = data["tags"]
    chars_before = sum(1 for t in tags if t.get("cat") == "角色")

    groups = defaultdict(list)
    for i, t in enumerate(tags):
        if t.get("cat") == "角色":
            groups[str(t.get("zh") or "").strip()].append(i)
    dups = {zh: idxs for zh, idxs in groups.items() if len(idxs) > 1}

    print("角色条数:", chars_before, "| 组内重名组:", len(dups))

    removed = set()
    rows = []          # (zh, keep_desc, [drop_desc], merged_fields, notes)
    merged_total = 0
    app_merged = 0
    skipped_app = []   # 疑似同名不同人，没合并外观
    guessed_app = []   # 无法判断但合并了外观

    # 作品(sub) → 该作品角色的 en 词表：中文 sub 也能和 en 括号里的作品名对上
    sub_tokens = defaultdict(set)
    for t in tags:
        if t.get("cat") == "角色":
            sub_tokens[str(t.get("sub") or "")] |= en_tokens(t.get("en"))

    for zh, idxs in dups.items():
        items = [(i, tags[i]) for i in idxs]
        best = max(items, key=lambda p: (rank_key(p[1]), -p[0]))
        keep_i, keep = best
        drops = [(i, t) for i, t in items if i != keep_i]
        # 好数据先占位
        drops.sort(key=lambda p: (rank_key(p[1]), -p[0]), reverse=True)
        merged_here = []
        notes = []
        for i, t in drops:
            verdict = app_merge_verdict(keep, t, sub_tokens)
            allow = verdict != "conflict"
            n_pending = pending_app(keep, t)
            if verdict == "conflict" and n_pending:
                skipped_app.append((zh, keep.get("en"), t.get("en")))
                notes.append("跳过外观(疑似不同人)")
            elif verdict == "unknown" and n_pending:
                guessed_app.append((zh, keep.get("en"), t.get("en")))
                notes.append("外观待确认")
            added = merge_missing(keep, t, allow_app=allow)
            merged_total += len(added)
            app_merged += sum(1 for a in added if a.startswith("app."))
            merged_here.extend(added)
            removed.add(i)
        rows.append((
            zh,
            "%s / %s" % (keep.get("en"), keep.get("sub")),
            ["%s / %s" % (t.get("en"), t.get("sub")) for _, t in drops],
            merged_here,
            notes,
        ))

    # ---- 阶段 2：和 chars_extra.json 的跨文件重复 ----
    x_kill, x_rows = cross_file_pass(tags, skip=removed)
    removed |= x_kill

    if not removed:
        print("没有重名角色，无需处理（幂等退出）。")
        return 0

    new_tags = [t for i, t in enumerate(tags) if i not in removed]
    chars_after = sum(1 for t in new_tags if t.get("cat") == "角色")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(HERE, "tags_cn.backup_merge_%s.json" % stamp)

    if not DRY:
        shutil.copy2(TAGS_PATH, backup)
        data["tags"] = new_tags
        tmp = TAGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, TAGS_PATH)
        print("已备份:", os.path.basename(backup))

    # ---- 报告 ----
    lines = []
    lines.append("合并重名角色报告 " + time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 70)
    lines.append("备份文件: " + (os.path.basename(backup) if not DRY else "(dry-run 未写)"))
    lines.append("角色条数: %d → %d（共删除 %d 条）" % (chars_before, chars_after, len(removed)))
    lines.append("阶段1 组内重名: %d 组 → 0（删除 %d 条）" % (len(dups), len(removed) - len(x_kill)))
    lines.append("阶段2 与 chars_extra.json 跨文件重复: 删除 %d 条「图反推」重复" % len(x_kill))
    lines.append("合并字段: %d 个（其中 app 子字段 %d 个）" % (merged_total, app_merged))
    lines.append("疑似同名不同人、跳过外观合并: %d 条" % len(skipped_app))
    for zh, a, b in skipped_app:
        lines.append("  x %s: 保留 %s  ← 丢弃 %s 的外观（作品对不上，可能是同名不同人）" % (zh, a, b))
    lines.append("无法判断是否同一人、已合并外观（建议人工扫一眼）: %d 条" % len(guessed_app))
    for zh, a, b in guessed_app:
        lines.append("  ? %s: 保留 %s  ← 取自 %s" % (zh, a, b))
    lines.append("")
    lines.append("阶段1 明细（zh | 保留 en / sub | 删除 en / sub | 合并进来的字段）")
    lines.append("-" * 70)
    for zh, keep_desc, drop_descs, merged_here, notes in rows:
        lines.append("%s | 保留 %s | 删除 %s | 合并 %s | %s" % (
            zh, keep_desc, "; ".join(drop_descs), ", ".join(merged_here) or "-",
            "；".join(notes) or "-"))
    lines.append("")
    lines.append("阶段2 明细（zh | 删除 tags_cn 的 en | 保留 chars_extra.json 的 en / sub | 丢掉的外观字段）")
    lines.append("-" * 70)
    for zh, dead_en, keep_desc, lost in x_rows:
        lines.append("%s | 删除 %s | 保留(extra) %s | 丢掉外观 %s" % (zh, dead_en, keep_desc, lost))
    text = "\n".join(lines) + "\n"
    if not DRY:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    print(text.split("明细")[0])
    print("报告:", "merge_dup_chars_report.txt" if not DRY else "(dry-run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
