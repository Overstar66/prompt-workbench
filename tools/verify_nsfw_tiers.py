# -*- coding: utf-8 -*-
"""NSFW 三级判定的回归自检（离线，直接调 sanitize_nsfw_text）。

三级口径：
  露骨 explicit → 命中整句删
  擦边 soft     → 原样保留（不删句、不改写）
用法：python verify_nsfw_tiers.py
"""
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import app

FAIL = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


ex, soft = app.nsfw_words()
print("=" * 78)
print("[分级] 露骨 = %d 词，擦边 = %d 词，合计 = %d" % (len(ex), len(soft), len(ex) + len(soft)))

print("\n[1] 用户反馈的擦边词必须保留")
for w in ("内裤外露", "走光", "长筒袜", "开裆裤袜", "透视", "内衣"):
    out, hits = app.sanitize_nsfw_text("女孩穿着%s，坐在草地上微笑。" % w)
    check(out.strip() == "女孩穿着%s，坐在草地上微笑。" % w and hits == 0,
          "%s 保留（hits=%d）" % (w, hits))

print("\n[2] 露骨词必须删句")
for w in ("小穴", "肉棒", "精液", "跳蛋", "眼罩", "做爱", "手交", "后穴"):
    out, hits = app.sanitize_nsfw_text("女孩%s。" % w)
    check(out == "" and hits >= 1, "%s 删句（hits=%d）" % (w, hits))

print("\n[3] 擦边整段不被改写")
t = "一个女孩，内裤外露，白衬衫，坐在草地上微笑。"
out, hits = app.sanitize_nsfw_text(t)
check(out.strip() == t and hits == 0, "「内裤外露」原句保留")

print("\n[4] 单字兜底：正常词不误杀、露骨语境照删")
for t, want in (("画风逼近真实，光影逼真。", 0), ("她憋不住尿尿了。", 0),
                ("他把她逼到墙角。", 1), ("她淫荡地笑着。", 1)):
    out, hits = app.sanitize_nsfw_text(t)
    check(hits == want, "「%s」 hits=%d（期望 %d）" % (t, hits, want))

print("\n[5] 删句后收尾：人数重算 / 空壳行删除 / 永不空输出")
mixed = ("2个角色 明日香 绫波丽\n"
         "明日香：她跪在地上，嘴里含着肉棒。\n"
         "绫波丽：她站在窗边微笑，穿着长筒袜。\n"
         "场景：房间，暖光。")
out, hits = app.sanitize_nsfw_text(mixed)
print("  --- 输出 ---")
for ln in out.split("\n"):
    print("  " + ln)
check(out.startswith("1个角色 绫波丽"), "人数由 2 改成 1")
check("肉棒" not in out and "长筒袜" in out, "露骨句删除、擦边句保留")
check(app.sanitize_nsfw_text("") == ("", 0), "空输入返回 ('', 0)")
empty, _ = app.sanitize_nsfw_text("跳蛋")
check(empty == "", "全删时返回空串，由接口补 _SFW_EMPTY：%r" % app._SFW_EMPTY)

print("\n" + "=" * 78)
if FAIL:
    print("FAIL:", len(FAIL))
    for f in FAIL:
        print(" -", f)
    sys.exit(1)
print("全部通过")
