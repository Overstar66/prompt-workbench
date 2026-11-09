#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给 tags_cn.json 补齐 WD14 打标词表的全部中文译名（幂等）。

为什么这样分层（实测决定，不是照抄顺序）：
  1) 本地社区译名表 `danbooru_zh.csv`（ComfyUI-TagWorkbench 自带，9.8 万条）
     对 WD14 的 general 词覆盖 92%（5073/5502），是人工整理过的通行译法，
     比 7B 模型稳定得多，所以先吃它；
  2) 词库 tags_cn.json 里已有的 1445 条 WD14 词是「词根」，用于规则层里
     取词（颜色/部位/服装单词表 + 组合规则），也用于角色名 base 词复用；
  3) 剩下的（general 约 400 条 + character 全部）走本地 Ollama qwen2.5:7b
     批量翻译（实测 20 词/2 秒），带 few-shot、JSON 数组按序返回；
  4) 所有结果统一过质量闸：必须是中文、1~12 字、不含英文，否则丢弃并重试。

特性：
- 只追加，不改已有条目的 zh/en；不删任何条目；
- 结果缓存到 wd14_zh_cache.json，跑两次结果字节级一致（幂等）；
- 写入前自动备份 tags_cn.json 为 tags_cn.backup_wd14_<YYYYmmdd_HHMM>.json；
- 原子写盘（先写 .tmp 再 replace），输出格式与原文一致：
  json.dumps(indent=1, ensure_ascii=False) + CRLF + 末尾无换行。

用法：
    python build_wd14_zh.py            # 正式写入
    python build_wd14_zh.py --dry-run  # 只统计/试跑，不写 tags_cn.json
    python build_wd14_zh.py --limit 40 # 只对前 40 个缺口调 Ollama（调试）
"""
import argparse
import csv
import json
import os
import random
import re
import shutil
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "tags_cn.json")
CACHE = os.path.join(HERE, "wd14_zh_cache.json")

WD14_CSV = r"D:\Dsh-project\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-WD14-Tagger\models\wd-v1-4-moat-tagger-v2.csv"
ZH_CSV = r"D:\Dsh-project\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-TagWorkbench\assets\danbooru_zh.csv"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"

CAT_GENERAL, CAT_CHARACTER = 0, 4
MAXLEN = 12

CJK = re.compile(r"[\u4e00-\u9fff]")
LATIN = re.compile(r"[A-Za-z]")
BAD_ZH = ("游戏", "关联", "未知", "名字", "角色名", "（无）", "无中文")

# ── 规则层词表（人工整理，按 Danbooru 常见构词） ──────────────────────────
COLORS = {
    "red": "红", "blue": "蓝", "black": "黑", "white": "白", "grey": "灰", "gray": "灰",
    "brown": "棕", "pink": "粉", "yellow": "黄", "green": "绿", "purple": "紫",
    "orange": "橙", "silver": "银", "blonde": "金", "gold": "金", "aqua": "水蓝",
    "cyan": "青", "tan": "棕褐", "platinum": "铂金", "multicolored": "多彩",
    "two-tone": "双色", "violet": "紫罗兰", "indigo": "靛蓝", "navy": "藏青",
    "teal": "青绿", "magenta": "洋红", "crimson": "绯红", "lavender": "薰衣草紫",
    "beige": "米色", "ivory": "象牙白", "peach": "桃色", "mint": "薄荷绿",
    "olive": "橄榄绿", "khaki": "卡其", "amber": "琥珀", "rose": "玫瑰",
}
LIGHT = {"light": "浅", "dark": "深", "pale": "浅"}

PARTS = {
    "hair": "头发", "eyes": "眼睛", "eye": "眼睛", "ears": "耳朵", "skin": "皮肤",
    "lips": "嘴唇", "nail": "指甲", "nails": "指甲", "tail": "尾巴",
    "horns": "角", "wings": "翅膀", "fur": "毛皮", "feathers": "羽毛",
    "pupils": "瞳孔", "beard": "胡子", "eyebrows": "眉毛", "eyelashes": "睫毛",
}
CLOTH = {
    "footwear": "鞋子", "headwear": "头饰", "choker": "项圈", "shirt": "衬衫",
    "skirt": "裙子", "dress": "连衣裙", "jacket": "夹克", "coat": "大衣",
    "sweater": "毛衣", "vest": "马甲", "necktie": "领带", "ribbon": "缎带",
    "bow": "蝴蝶结", "gloves": "手套", "socks": "袜子", "panties": "内裤",
    "bra": "胸罩", "bikini": "比基尼", "swimsuit": "泳衣", "leotard": "连体衣",
    "cape": "披风", "cloak": "斗篷", "hat": "帽子", "mask": "面罩",
    "scarf": "围巾", "belt": "腰带", "boots": "靴子", "sandals": "凉鞋",
    "shorts": "短裤", "pants": "裤子", "kimono": "和服", "leggings": "紧身裤",
    "thighhighs": "过膝袜", "earrings": "耳环", "hat_removed": "帽子",
}
SYMBOLS = {
    "w": "笑", "^_^": "开心表情", "^o^": "张嘴笑", "@_@": "晕眩表情",
    "x_x": "晕倒表情", ":x": "闭嘴", "=3": "嘟嘴", "v": "V字手势",
    "39": "感谢", "3:": "猫嘴表情", "o-ring": "O形环", "o_ring": "O形环",
}

# 人工校对：跑完抽样后发现的明显错译，按 en 覆盖（任何来源都会被它盖掉）
MANUAL = {
    "u_u": "困倦表情", "mmf_threesome": "三人行", "mmf_threesome_": "三人行",
    "mmm_threesome": "三人行", "ffm_threesome": "三人行", "fff_threesome": "三人行",
    "yes": "肯定", "on_head": "放在头上", "boned_meat": "带骨肉",
    "column": "柱子", "gao": "吼叫", "meta": "元梗", "bow_(weapon)": "弓",
    "bow_(music)": "琴弓", "meme": "梗图", "2011": "2011年", "2012": "2012年",
    "2013": "2013年", "2014": "2014年", "2015": "2015年", "2016": "2016年",
    "2017": "2017年", "2018": "2018年", "2019": "2019年", "2020": "2020年",
    "sakazuki": "酒杯", "hauchiwa": "羽扇", "nanodesu_(phrase)": "呜喵口头禅",
}

SYS_GEN = ("你是资深的 Danbooru 标签中文翻译。翻译必须保留原标签的每一个修饰成分，"
           "用简洁自然的中文名词短语表达，不解释、不音译、不带英文。")
EX_GEN = ('示例：\n输入 ["grey_scarf","sakuragaoka_high_school_uniform","no_bra",'
          '"holding_cup","blue_eyes"]\n输出 ["灰色围巾","樱丘高中校服","未穿胸罩","拿着杯子","蓝色眼睛"]\n')

SYS_CHA = ("你是资深的动漫角色名中文翻译，熟悉日本动画、游戏（东方Project、舰队Collection、碧蓝航线、"
           "明日方舟、Fate、原神、少女前线等）角色的中文通用译名。"
           "把英文 Danbooru 角色标签翻译成该角色的中文名字，只用汉字和「·」，不要英文、不要日文假名、不要解释；"
           "中文圈没有通行译名时按罗马音音译成 2-6 个汉字。")
EX_CHA = ('示例：\n输入 ["kazami_yuuka","moriya_suwako","konpaku_youmu_(ghost)","saber"]\n'
          '输出 ["风见幽香","洩矢诹访子","魂魄妖梦","阿尔托莉雅"]\n')

# 角色兜底提示词：逼出汉字（音译），不带作品名
SYS_CHA2 = ("你是动漫角色名中文音译工具。把英文角色标签翻成中文名，只能用汉字和「·」，"
            "绝对不要英文、不要日文假名、不要解释、不要带作品名；不确定就按罗马音音译成 2-6 个汉字。")
EX_CHA2 = '示例：\n输入 ["saber","nagato_(azur_lane)"]\n输出 ["阿尔托莉雅","长门"]\n'

LEN_HINTS = ("其它要求：保留全部修饰成分；不要英文、不要编号、不要解释；"
             "输出必须是长度为 {n} 的 JSON 字符串数组，顺序与输入一致。\n")


# ── 基础 IO ────────────────────────────────────────────────────────────────
def load_lib():
    with open(LIB, encoding="utf-8") as f:
        return json.load(f)


def save_lib(data):
    txt = json.dumps(data, ensure_ascii=False, indent=1).replace("\n", "\r\n")
    tmp = LIB + ".tmp_write"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    os.replace(tmp, LIB)


def load_zh_csv(path=ZH_CSV):
    m = {}
    if not os.path.isfile(path):
        return m
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n\r").split(",")
            if len(parts) >= 2:
                en, zh = parts[0].strip().lower(), parts[1].strip()
                if en and zh:
                    m[en] = zh
    return m


def load_wd14():
    rows = []
    with open(WD14_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            name = (r.get("name") or "").strip()
            try:
                cat = int(r.get("category") or 0)
            except ValueError:
                cat = 0
            if name and cat in (CAT_GENERAL, CAT_CHARACTER):
                rows.append((name.replace(" ", "_"), cat))
    return rows


# ── 质量闸 ─────────────────────────────────────────────────────────────────
def clean(zh, strip_alts=True):
    if not zh:
        return ""
    z = str(zh).strip().strip('"').strip("'").strip()
    if strip_alts and "|" in z:
        cands = [c.strip() for c in z.split("|") if c.strip()]
        good = [c for c in cands if ok_zh(c)]
        z = good[0] if good else cands[0]
    # 去掉含英文字母的括号内容（如「提督（舰队Collection）」→「提督」）
    z = re.sub(r"[（(][^）)]*[A-Za-z][^）)]*[）)]", "", z)
    z = re.sub(r"[（(]\s*[）)]", "", z)
    z = re.sub(r"\s+", "", z)
    z = z.strip("。、，,；;：:·-—")
    return z


def ok_zh(z):
    if not z:
        return False
    if not CJK.search(z):
        return False
    if LATIN.search(z):
        return False
    if len(z) > MAXLEN or len(z) < 1:
        return False
    if any(b in z for b in BAD_ZH):
        return False
    # 只允许中文 + 少量中文标点/间隔号
    if not re.fullmatch(r"[\u4e00-\u9fff\u3000-\u303f·（）()]+", z):
        return False
    return True


# ── 规则层 ─────────────────────────────────────────────────────────────────
def rules(name, vocab):
    """按构词规则翻译；拿不准就返回空串。vocab(word) 返回单词中文或空。"""
    low = name.lower()
    if low in SYMBOLS:
        return SYMBOLS[low]
    if low in COLORS:
        return COLORS[low] + "色"

    # 数字/人数：1girl / 2boys / multiple_girls
    m = re.fullmatch(r"(\d+)(girl|boy|other)s?", low)
    if m:
        return "%s个%s" % (m.group(1), {"girl": "女孩", "boy": "男孩", "other": "人"}[m.group(2)])

    words = low.split("_")

    def c(w):
        base = COLORS.get(w) or ""
        # 「多彩」「双色」这类本身已含色义，不要再补「色」
        return base if (base.endswith("色") or w in ("multicolored", "two-tone")) else base + "色"

    def n(s):
        return PARTS.get(s) or CLOTH.get(s) or ""

    # <色>_<部位/服装>
    if len(words) == 2 and words[0] in COLORS and n(words[1]):
        return c(words[0]) + n(words[1])
    # light_purple_hair / dark_blue_eyes
    if len(words) == 3 and words[0] in LIGHT and words[1] in COLORS and n(words[2]):
        return LIGHT[words[0]] + c(words[1]) + n(words[2])

    # holding_xxx
    if low.startswith("holding_") and len(words) == 2:
        core = n(words[1]) or vocab(words[1])
        if core:
            return "拿着" + core
    # no_xxx
    if low.startswith("no_") and len(words) == 2:
        core = n(words[1]) or vocab(words[1])
        if core:
            return ("未穿" if words[1] in CLOTH else "没有") + core
    # xxx_removed
    if low.endswith("_removed") and len(words) == 2:
        core = n(words[0]) or vocab(words[0])
        if core:
            return core + "脱下"
    # xxx_print
    if low.endswith("_print") and len(words) == 2:
        core = n(words[0]) or vocab(words[0])
        if core:
            return core + "印花"
    # xxx_background
    if low.endswith("_background") and len(words) == 2:
        core = vocab(words[0])
        if core:
            return core + "背景"
    return ""


# ── Ollama ─────────────────────────────────────────────────────────────────
def ollama(system, prompt, num_predict=1800):
    body = {
        "model": MODEL, "system": system, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict, "num_ctx": 8192,
                    "repeat_penalty": 1.05},
    }
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8")).get("response", "")


def parse_arr(txt):
    m = re.search(r"\[.*\]", txt or "", re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
        return [str(x) for x in arr] if isinstance(arr, list) else []
    except Exception:
        return []


def translate_batch(tags, is_char, attempt=0):
    """返回 {tag: zh}，只含通过质量闸的。"""
    if not tags:
        return {}
    system = SYS_CHA if is_char else SYS_GEN
    ex = EX_CHA if is_char else EX_GEN
    extra = ""
    if attempt:
        extra = "注意：只输出中文，绝对不能出现英文字母。\n"
    prompt = (("把下列 {n} 个英文 Danbooru 角色标签按原顺序翻译成中文，输出长度为 {n} 的 JSON 字符串数组。\n"
               if is_char else
               "把下列 {n} 个英文 Danbooru 标签按原顺序翻译成中文，输出长度为 {n} 的 JSON 字符串数组。\n")
              ).format(n=len(tags)) + ex + extra + LEN_HINTS.format(n=len(tags)) + \
             "\n输入 " + json.dumps(tags, ensure_ascii=False) + "\n输出"
    try:
        txt = ollama(system, prompt)
    except Exception as e:
        sys.stderr.write("[ollama error] %s\n" % e)
        return {}
    arr = parse_arr(txt)
    if len(arr) != len(tags):
        return {}
    out = {}
    for en, zh in zip(tags, arr):
        z = clean(zh)
        if ok_zh(z):
            out[en] = z
    return out


def translate_all(tags, is_char, batch, progress=None):
    """批量翻译，失败项折半重试一次，最后仍失败的丢弃。"""
    todo = list(tags)
    out = {}
    first = True
    while todo:
        chunk, todo = todo[:batch], todo[batch:]
        got = translate_batch(chunk, is_char)
        out.update(got)
        miss = [t for t in chunk if t not in got]
        if miss:
            # 失败项：折半再试一次
            half = max(1, len(miss) // 2)
            for seg in (miss[:half], miss[half:]):
                if not seg:
                    continue
                g2 = translate_batch(seg, is_char, attempt=1)
                out.update(g2)
                miss2 = [t for t in seg if t not in g2]
                if miss2:
                    g3 = translate_batch(miss2, is_char, attempt=1)
                    out.update(g3)
        if progress:
            progress(out, first)
            first = False
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="不写 tags_cn.json")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个缺口（调试）")
    ap.add_argument("--samples", type=int, default=30)
    args = ap.parse_args()
    t_start = time.time()

    data = load_lib()
    old_tags = data["tags"]
    have = {}
    for e in old_tags:
        en, zh = (e.get("en") or "").strip(), (e.get("zh") or "").strip()
        if en and zh:
            have.setdefault(en.lower(), zh)
    print("词库现有条目 %d（去重 en %d）" % (len(old_tags), len(have)))

    wd = load_wd14()
    n_gen = sum(1 for _, c in wd if c == CAT_GENERAL)
    n_cha = sum(1 for _, c in wd if c == CAT_CHARACTER)
    missing = [(n, c) for n, c in wd if n.lower() not in have]
    miss_gen = [n for n, c in missing if c == CAT_GENERAL]
    miss_cha = [n for n, c in missing if c == CAT_CHARACTER]
    print("WD14 词表：总 %d（general %d + character %d），已有中文 %d，缺口 %d（general %d + character %d）"
          % (len(wd), n_gen, n_cha, len(wd) - len(missing), len(missing), len(miss_gen), len(miss_cha)))

    zhcsv = load_zh_csv()
    print("社区译名表 %s：%d 条" % (os.path.basename(ZH_CSV), len(zhcsv)))

    cache = {}
    if os.path.isfile(CACHE):
        try:
            raw = json.load(open(CACHE, encoding="utf-8"))
            cache = {k: v for k, v in (raw.get("zh") or {}).items() if ok_zh(v)}
        except Exception:
            cache = {}
    print("翻译缓存：%d 条" % len(cache))

    def vocab(word):
        w = (word or "").lower()
        if w in PARTS:
            return PARTS[w]
        if w in CLOTH:
            return CLOTH[w]
        if w in COLORS:
            return COLORS[w] + "色"
        z = clean(zhcsv.get(w) or "")
        return z if ok_zh(z) else ""

    plan, src_count = {}, {}

    def put(en, zh, src):
        if ok_zh(zh) and en not in plan:
            plan[en] = zh
            src_count[src] = src_count.get(src, 0) + 1

    # 1) 缓存
    for en, zh in cache.items():
        put(en, zh, "cache")
    # 2) 社区译名表（general 优先；角色表里大量是作品名误映射，不用）
    for en in miss_gen:
        put(en, clean(zhcsv.get(en.lower()) or ""), "zhcsv")
    # 3) 规则层
    for en in miss_gen:
        put(en, rules(en, vocab), "rule")

    left_gen = [en for en in miss_gen if en not in plan]
    left_cha = [en for en in miss_cha if en not in plan]
    print("分层结果：zhcsv %d / 规则 %d / 缓存 %d / 待 Ollama %d（general %d + character %d）"
          % (src_count.get("zhcsv", 0), src_count.get("rule", 0), src_count.get("cache", 0),
             len(left_gen) + len(left_cha), len(left_gen), len(left_cha)))

    if args.limit:
        left_gen = left_gen[:args.limit]
        left_cha = left_cha[:args.limit]

    # 4) Ollama 兜底
    t0 = time.time()
    done = [0]
    total = len(left_gen) + len(left_cha)

    def prog(d, first):
        done[0] = len(plan) - src_count.get("zhcsv", 0) - src_count.get("rule", 0) - src_count.get("cache", 0)
        print("  Ollama 进度 %d/%d …" % (len([1 for e in d if e]), total), flush=True)

    if left_gen:
        print("[Ollama] general %d 条，批 25 …" % len(left_gen), flush=True)
        res = translate_all(left_gen, False, 25, progress=prog)
        for en, zh in res.items():
            put(en, zh, "ollama_gen")
        print("  完成 %.1fs，成功 %d/%d" % (time.time() - t0, len(res), len(left_gen)), flush=True)
    t1 = time.time()
    if left_cha:
        print("[Ollama] character %d 条，批 18 …" % len(left_cha), flush=True)
        res = translate_all(left_cha, True, 18, progress=prog)
        for en, zh in res.items():
            put(en, zh, "ollama_cha")
        print("  完成 %.1fs，成功 %d/%d" % (time.time() - t1, len(res), len(left_cha)), flush=True)

    # 角色名可疑的再试一轮
    sus = [en for en in miss_cha if en in plan and (len(plan[en]) < 2 or len(plan[en]) > 8)]
    if sus:
        print("[Ollama] 角色名可疑 %d 条，重译 …" % len(sus), flush=True)
        res = translate_all(sus, True, 12)
        for en, zh in res.items():
            if en in plan and (len(plan[en]) < 2 or len(plan[en]) > 8):
                plan[en] = zh

    # 人工校对覆盖（最后生效）
    for en, zh in MANUAL.items():
        if ok_zh(zh):
            plan[en] = zh

    new_entries = []
    for en, cat in missing:
        zh = plan.get(en)
        if not zh:
            continue
        if cat == CAT_CHARACTER:
            new_entries.append({"zh": zh, "en": en, "cat": "角色", "sub": "图反推",
                                "nsfw": False,
                                "app": {"hair": "", "eyes": "", "outfit": "", "body": "", "chest": ""}})
        else:
            new_entries.append({"zh": zh, "en": en, "cat": "自定义", "sub": "图反推", "nsfw": False})

    total_miss = len(missing)
    print("-" * 60)
    for k in ("zhcsv", "rule", "ollama_gen", "ollama_cha"):
        print("  %-12s %d" % (k, src_count.get(k, 0)))
    print("新增 %d / 缺口 %d，成功率 %.1f%%" % (len(new_entries), total_miss,
                                              100.0 * len(new_entries) / max(1, total_miss)))
    fail = [en for en, c in missing if en not in plan]
    if fail:
        print("  未覆盖 %d 条：%s" % (len(fail), fail[:12]))

    # 缓存回写（只存通过质量闸的）
    allmap = {k: v for k, v in cache.items()}
    allmap.update({e["en"]: e["zh"] for e in new_entries})
    try:
        json.dump({"model": MODEL, "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "zh": dict(sorted(allmap.items()))},
                  open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    except Exception as e:
        sys.stderr.write("[warn] 缓存写入失败 %s\n" % e)

    # 抽样检查
    if new_entries and args.samples:
        random.seed(20261109)
        print("-" * 60)
        print("随机抽样 %d 条：" % min(args.samples, len(new_entries)))
        for e in random.sample(new_entries, min(args.samples, len(new_entries))):
            print("  %-44s -> %s" % (e["en"], e["zh"]))

    if args.dry_run:
        print("[dry-run] 未写入 tags_cn.json，耗时 %.1fs" % (time.time() - t_start))
        return

    if not new_entries:
        print("没有需要新增的条目，直接结束")
        return

    stamp = time.strftime("%Y%m%d_%H%M")
    bak = os.path.join(HERE, "tags_cn.backup_wd14_%s.json" % stamp)
    shutil.copy2(LIB, bak)
    print("已备份:", os.path.basename(bak))

    data["tags"] = old_tags + new_entries
    save_lib(data)
    print("已写入 %s（%d 条，%.2f MB），总耗时 %.1fs"
          % (os.path.basename(LIB), len(data["tags"]), os.path.getsize(LIB) / 1048576.0,
             time.time() - t_start))


if __name__ == "__main__":
    main()
