# -*- coding: utf-8 -*-
"""验证白名单/黑名单：SOFT_WORDS 只换不删，黑名单必删词仍删句（单元级）。"""
import sys, json, re
sys.path.insert(0, ".")
import app

FAIL = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


soft = app.soft_words()
nsfw = app.nsfw_words()
hard = set(nsfw) - set(soft)
hard_rx = app._hard_rx()

print("=" * 72)
print("[白名单来源] cat==服装 的 nsfw 词 / 纯服饰词根 构建")
print("  SOFT_WORDS 词数 =", len(soft), " 词根数 =", len(app._SOFT_HEADS))
print("  颜色前缀 =", " ".join(app._SOFT_COLORS))
print("  检测集 nsfw_words() =", len(nsfw), " 黑名单 = 检测集-白名单 =", len(hard))

print("\n[1] 替换词必须干净（不含任何检测集词/黑名单词/兜底单字）")
bad = [(w, r) for w, r in soft.items() if r in nsfw or hard_rx.search(r) or app._RESIDUE_RX.search(r)]
check(not bad, "所有 %d 个替换词都不含 nsfw 词 %s" % (len(soft), bad[:5]))

print("\n[2] 白名单词不能被黑名单词吞掉（否则会被整句删）")
swallow = [(w, h) for w in soft for h in hard if h in w]
check(not swallow, "没有黑名单词是白名单词的子串 %s" % swallow[:5])

print("\n[3] ② 必删清单必须还在黑名单里（不得被白名单放行）")
MUST = ("跳蛋", "假阳具", "肛塞", "拉珠", "口球", "乳夹", "乳铃", "束缚绳", "手铐",
        "眼罩", "项圈", "触手", "尿道棒", "震动棒", "飞机杯", "避孕套",
        "开裆裤袜", "乳胶衣", "乳首贴", "贞操带", "透视上衣", "开裆连裤袜",
        "撕裂丝袜", "长筒袜情趣", "过膝袜情趣")
for w in MUST:
    check(w in hard and w not in soft, "%s 在黑名单且不在白名单" % w)

print("\n[4] 白名单词示例（长筒袜 系）")
for w in ("长筒袜", "黑色长筒袜", "白色连裤袜", "渔网袜", "睡裙", "黑色睡裙"):
    check(w in soft, "%s -> %s" % (w, soft.get(w)))

print("\n[5] 单句行为：白名单只替换、不删句、不计 filtered")
CASES = [
    ("她穿着长筒袜和百褶裙。", "长袜", 0),
    ("她穿着黑色长筒袜，坐在咖啡厅里微笑。", "长袜", 0),
    ("她穿着渔网袜和短裙。", "网纹袜", 0),
    ("她穿着黑色睡裙靠在窗边。", "睡裙", 0),
]
for text, want, want_hits in CASES:
    out, hits = app.sanitize_nsfw_text(text)
    check(want in out and hits == want_hits and out != "",
          "「%s」 -> 「%s」 hits=%d" % (text, out, hits))

print("\n[6] 单句行为：黑名单整句删 + 计数")
BAD = [
    "她手里拿着跳蛋。",
    "她穿着开裆裤袜。",
    "她穿着乳胶衣。",
    "乳房上贴着乳首贴。",
    "乳头上有乳夹。",
    "她戴着项圈和眼罩。",
    "桌上放着一根假阳具。",
    "她腰上缠着束缚绳。",
]
for text in BAD:
    out, hits = app.sanitize_nsfw_text(text)
    check(out == "" and hits >= 1, "「%s」 -> 删句 hits=%d" % (text, hits))

print("\n[7] 混合文本：干净句保留、露骨句删、白名单替换")
mixed = ("1个角色 女孩\n"
         "女孩：栗色长发，穿着黑色长筒袜和百褶裙，坐在窗边微笑。\n"
         "女孩：伸手拿起跳蛋，乳夹闪着光。\n"
         "场景：咖啡厅，午后阳光。\n")
out, hits = app.sanitize_nsfw_text(mixed)
print("  --- 输出 ---")
for ln in out.split("\n"):
    print("  " + ln)
check("长筒袜" not in out and "长袜" in out, "长筒袜已换成 长袜")
check("跳蛋" not in out and hits >= 2, "跳蛋/乳夹 那句被删且计数 hits=%d" % hits)
check("咖啡厅" in out, "干净句保留")

print("\n[8] 永不空输出（接口层兜底）")
out, hits = app.sanitize_nsfw_text("跳蛋")
check(out == "" and hits == 1, "全删时 sanitize 返回空，由接口补 _SFW_EMPTY")

print("\n" + "=" * 72)
if FAIL:
    print("FAIL:", len(FAIL))
    for f in FAIL:
        print(" -", f)
    sys.exit(1)
print("全部通过")
