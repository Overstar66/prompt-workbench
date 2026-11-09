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
BAD_ZH = ("游戏", "关联", "未知", "名字", "角色名", "无中文")
BAD_EXACT = {"游戏", "关联", "未知", "名字", "角色名", "无中文", "游戏名", "中文"}

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

# 人工校对：模型/社区表搞不定的（占位符、拉丁字母、枪械型号、冷门角色），
# 按 en 覆盖（任何来源都会被它盖掉）
MANUAL = {
    # —— 符号/手势/量词 ——
    "v": "胜利手势", "double_v": "双胜利手势", "double_w": "双手势",
    "v-fin": "叉形天线", "v-neck": "深领口", "v_over_eye": "遮眼手势",
    "x": "叉号", "x-shaped_pupils": "叉形瞳孔", "circled_9": "圆圈九",
    "3d_background": "三维背景", "o-ring_bikini": "圆环比基尼", "z-ring": "环形手环",
    "character_name": "角色名称",
    "facebook_username": "社交网站用户名",
    # —— 网络/平台 ——
    "twitter_username": "推特用户名", "patreon_username": "赞助平台用户名",
    "deviantart_username": "绘站用户名", "instagram_username": "照片墙用户名",
    "pixiv_username": "插画站用户名", "pixiv_id": "插画站编号",
    "weibo_logo": "微博标志", "patreon_logo": "赞助平台标志",
    # —— 游戏机/电子 ——
    "gameplay_mechanics": "玩法机制", "video_game": "电子游戏",
    "game_console": "游戏主机", "handheld_game_console": "掌上游戏机",
    "gamepad": "游戏手柄", "playstation_controller": "游戏机手柄",
    "playstation_portable": "掌上游戏机", "nintendo_switch": "任天堂游戏机",
    "nintendo_ds": "任天堂掌上机", "nintendo_3ds": "任天堂掌上机",
    "game_boy": "掌上机", "ipod": "音乐播放器", "dvd_cover": "光盘封面",
    "holding_game_controller": "拿着游戏手柄", "karaoke": "唱歌",
    # —— 服装/鞋 ——
    "toeless_footwear": "露趾鞋", "winged_footwear": "带翅鞋",
    "plunging_neckline": "深领口",
    "bc_freedom_military_uniform": "自由联邦军服",
    "griffin_&_kryuger_military_uniform": "格里芬军服",
    "hololive_idol_uniform": "虚拟主播偶像制服",
    "homurahara_academy_school_uniform": "穗群原学园制服",
    "tsab_ground_military_uniform": "管理局陆军制服",
    "pegasus_knight_uniform_(fire_emblem)": "天马骑士制服",
    "mod3_(girls'_frontline)": "三改人形", "elite_ii_(arknights)": "精英二",
    # —— 枪械 ——
    "m4_carbine": "卡宾枪", "ar-15": "自动步枪", "ak-47": "突击步枪",
    "m1911": "手枪", "p90": "冲锋枪", "beretta_92": "手枪",
    "h&k_hk416": "突击步枪", "h&k_ump": "冲锋枪", "m16a1": "步枪",
    "ump45_(girls'_frontline)": "冲锋枪人形", "ump9_(girls'_frontline)": "冲锋枪人形",
    "m4a1_(girls'_frontline)": "卡宾枪人形", "an-94_(girls'_frontline)": "步枪人形",
    "g36_(girls'_frontline)": "步枪人形", "g41_(girls'_frontline)": "步枪人形",
    "wa2000_(girls'_frontline)": "狙击枪人形", "z23_(azur_lane)": "驱逐舰娘",
    # —— 杂项 ——
    "karakasa_obake": "唐伞小僧", "vocaloid_append": "虚拟歌姬追加音源",
    "voyakiloid": "波亚基洛依德", "squidbeak_splatoon": "乌贼军团",
    "player_2": "二号玩家", "team_9": "九号小队", "super_saiyan_1": "超级赛亚人一",
    "panzerkampfwagen_iv": "四号坦克", "boo_(mario)": "幽灵布",
    "ui_(blue_archive)": "忧", "fine_motion_(umamusume)": "优美运动",
    "yumeno_himiko": "梦野秘密子", "shishiro_botan": "狮白牡丹",
    "touhoku_kiritan": "东北切丹", "ranma-chan": "女乱马", "nu-13": "纽十三",
    "matou_kariya": "间桐雁夜", "yorha_no._9_type_s": "九号机体",
    "heckler_&_koch": "冲锋枪",
    "hiro_(darling_in_the_franxx)": "广",
    "reines_el-melloi_archisorte": "莱妮丝",
    "kayneth_el-melloi_archibald": "凯奈斯",
    # —— 冷门角色/皮肤 ——
    "hatsune_miku_(append)": "初音未来追加音源", "ia_(vocaloid)": "伊亚",
    "i-19_(kancolle)": "伊号一九潜", "i-8_(kancolle)": "伊号八潜",
    "i-168_(kancolle)": "伊号一六八潜", "i-13_(kancolle)": "伊号一三潜",
    "agano_(kancolle)": "阿贺野", "tokitsukaze_(kancolle)": "时津风",
    "richelieu_(kancolle)": "黎塞留",
    "jeanne_d'arc_alter_(swimsuit_berserker)_(fate)": "泳装黑贞德",
    "jeanne_d'arc_alter_santa_lily_(fate)": "圣诞黑贞德",
    "jeanne_d'arc_(swimsuit_archer)_(second_ascension)_(fate)": "泳装贞德",
    "bb_(swimsuit_mooncancer)_(second_ascension)_(fate)": "泳装比伊",
    "mysterious_heroine_x_(fate)": "谜之女主角甲",
    "mysterious_heroine_xx_(fate)": "谜之女主角乙",
    "mysterious_heroine_x_alter_(first_ascension)_(fate)": "谜之女主角丙",
    # —— 社区表/模型明显错译的修正 ——
    "u_u": "困倦表情", "mmf_threesome": "三人行", "ffm_threesome": "三人行",
    "fff_threesome": "三人行", "mmm_threesome": "三人行", "yes": "肯定",
    "on_head": "放在头上", "boned_meat": "带骨肉", "column": "柱子",
    "gao": "吼叫", "meta": "元梗", "bow_(weapon)": "弓", "bow_(music)": "琴弓",
    "meme": "梗图", "2011": "2011年", "2012": "2012年", "2013": "2013年",
    "2014": "2014年", "2015": "2015年", "2016": "2016年", "2017": "2017年",
    "2018": "2018年", "2019": "2019年", "2020": "2020年",
    "sakazuki": "酒杯", "hauchiwa": "羽扇", "nanodesu_(phrase)": "呜喵口头禅",
    "turnaround": "转身展示", "nijigasaki_academy_school_uniform": "虹咲学园校服",
    "curtained_hair": "窗帘式刘海", "iori_rinko": "伊织凛子",
    "shindou_takuto": "神童拓人", "tomoe_gozen_(fate)": "巴御前",
    "nemoto_hina": "根本雏", "asuna_(bunny)_(blue_archive)": "阿丝娜",
    "master_3_(housamo)": "三号主人", "tiki_(young)_(fire_emblem)": "琪琪",
    # —— 抽样复核时发现的明显错译（角色） ——
    "xiao_(genshin_impact)": "魈", "xiangling_(genshin_impact)": "香菱",
    "kaguya_luna": "辉夜月", "flareon": "火伊布", "kohaku_(tsukihime)": "琥珀",
    "kinu_(kancolle)": "鬼怒", "hina_ichigo": "雏莓", "sakawa_(kancolle)": "酒匂",
    "uzuki_(kancolle)": "卯月", "katsuragi_(kancolle)": "葛城",
    "maya_kai_ni_(kancolle)": "摩耶改二", "gangut_(kancolle)": "甘古特",
    "kishinami_(kancolle)": "岸波", "zuikaku_(azur_lane)": "瑞鹤",
    "neru_(blue_archive)": "宁瑠", "tsukumo_benben": "九十九弁弁",
    "sirius_(azure_horizons)_(azur_lane)": "天狼星", "ookami_mio": "大神澪",
    "kousaka_reina": "高坂丽奈", "ushiroiya_battler": "右代宫战人",
    "hisakawa_hayate": "久川飒", "higuchi_madoka": "樋口圆香",
    "minamino_kanade": "南奏", "jigglypuff": "胖丁",
    "grass_wonder_(umamusume)": "草上飞", "morpeko": "莫鲁贝可",
    "kuma_(kancolle)": "球磨", "ushio_(kancolle)": "潮",
    # —— 抽样复核时发现的明显错译（通用词） ——
    "newhalf": "变性人", "fingersmile": "手指比笑", "column_lineup": "一字排开",
    "mitakihara_school_uniform": "见泷原中学制服", "kuki_shinobu": "九鬼忍",
    "mizunashi_akari": "水无灯里", "scooter": "踏板摩托车",
    "pov_crotch": "第一人称胯部视角", "kotatsu": "被炉", "gyaru": "辣妹",
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


KEEP_PAREN = ("女", "男", "幼", "幼年", "少年", "成年", "萝莉", "正太")


def strip_series_paren(z):
    """角色名去掉「（命运）」「（复仇者）」这类作品/职阶尾巴，保留（女）（男）这种区分。"""
    m = re.fullmatch(r"(.+?)[（(]([^（）()]{1,6})[）)]", z)
    if m and m.group(2) not in KEEP_PAREN:
        return m.group(1).strip("·-—")
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
    if z in BAD_EXACT:
        return False
    # 社区表里的「（碧蓝幻想）游戏」这类作品名误映射
    if z[0] in "（(" and any(b in z for b in BAD_ZH):
        return False
    # 只允许中文 + 数字 + 少量中文标点/间隔号
    if not re.fullmatch(r"[\u4e00-\u9fff0-9\u3000-\u303f·（）()]+", z):
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

    # 数字/人数：1girl / 2boys / 6+others / multiple_girls
    m = re.fullmatch(r"(\d+)(\+)?(girl|boy|other)s?", low)
    if m:
        n_zh = {"girl": "女孩", "boy": "男孩", "other": "其他人"}[m.group(3)]
        return "%s个%s%s" % (m.group(1), "以上" if m.group(2) else "", n_zh)

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


def translate_batch(tags, kind="gen", attempt=0):
    """kind: gen / cha / cha2。返回 {tag: zh}，只含通过质量闸的。"""
    if not tags:
        return {}
    if kind == "cha":
        system, ex = SYS_CHA, EX_CHA
        head = "把下列 {n} 个英文 Danbooru 角色标签按原顺序翻译成中文，输出长度为 {n} 的 JSON 字符串数组。\n"
    elif kind == "cha2":
        system, ex = SYS_CHA2, EX_CHA2
        head = "把下列 {n} 个英文角色标签按原顺序音译成中文名，输出长度为 {n} 的 JSON 字符串数组。\n"
    else:
        system, ex = SYS_GEN, EX_GEN
        head = "把下列 {n} 个英文 Danbooru 标签按原顺序翻译成中文，输出长度为 {n} 的 JSON 字符串数组。\n"
    extra = "注意：只输出中文，绝对不能出现英文字母。\n" if attempt else ""
    prompt = (head.format(n=len(tags)) + ex + extra + LEN_HINTS.format(n=len(tags))
              + "\n输入 " + json.dumps(tags, ensure_ascii=False) + "\n输出")
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


def translate_all(tags, kind, batch, progress=None, flush=None):
    """批量翻译；失败项折半重试一次，最后仍失败的丢弃。flush 每批回调一次（存缓存）。"""
    todo = list(tags)
    out = {}
    n_done = 0
    while todo:
        chunk, todo = todo[:batch], todo[batch:]
        got = translate_batch(chunk, kind)
        out.update(got)
        miss = [t for t in chunk if t not in got]
        if miss:
            half = max(1, len(miss) // 2)
            for seg in (miss[:half], miss[half:]):
                if not seg:
                    continue
                got2 = translate_batch(seg, kind, attempt=1)
                out.update(got2)
                miss2 = [t for t in seg if t not in got2]
                if miss2:
                    out.update(translate_batch(miss2, kind, attempt=1))
        n_done += len(chunk)
        if flush:
            flush(out, n_done, len(tags))
        if progress:
            progress(out, n_done, len(tags))
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

    # 1) 缓存（人工校对表里的词不许被旧缓存盖住）
    for en, zh in cache.items():
        if en in MANUAL:
            continue
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
    def flush_cache(*_a) -> None:
        allmap = {k: v for k, v in cache.items()}
        allmap.update({e: z for e, z in plan.items() if ok_zh(z)})
        try:
            tmp = CACHE + ".tmp"
            json.dump({"model": MODEL, "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "zh": dict(sorted(allmap.items()))},
                      open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            os.replace(tmp, CACHE)
        except Exception as e:
            sys.stderr.write("[warn] 缓存写入失败 %s\n" % e)

    def prog(out, n_done, n_total):
        print("  Ollama 进度 %d/%d（本阶段成功 %d）…" % (n_done, n_total, len(out)), flush=True)
        if n_done % 200 < 25:
            flush_cache()

    t0 = time.time()
    if left_gen:
        print("[Ollama] general %d 条，批 25 …" % len(left_gen), flush=True)
        res = translate_all(left_gen, "gen", 25, progress=prog, flush=flush_cache)
        for en, zh in res.items():
            put(en, zh, "ollama_gen")
        print("  完成 %.1fs，成功 %d/%d" % (time.time() - t0, len(res), len(left_gen)), flush=True)
    t1 = time.time()
    if left_cha:
        print("[Ollama] character %d 条，批 18 …" % len(left_cha), flush=True)
        res = translate_all(left_cha, "cha", 18, progress=prog, flush=flush_cache)
        for en, zh in res.items():
            put(en, zh, "ollama_cha")
        print("  完成 %.1fs，成功 %d/%d" % (time.time() - t1, len(res), len(left_cha)), flush=True)
        # 第一轮没出来的角色：换「音译兜底」提示词再逼一轮
        left_cha2 = [en for en in left_cha if en not in plan]
        if left_cha2:
            print("[Ollama] character 兜底 %d 条（音译提示词）…" % len(left_cha2), flush=True)
            res = translate_all(left_cha2, "cha2", 15, progress=prog, flush=flush_cache)
            for en, zh in res.items():
                put(en, zh, "ollama_cha2")
            print("  兜底成功 %d/%d" % (len(res), len(left_cha2)), flush=True)
        # 再不行：退回社区译名表里的汉字写法（去掉 ? 分隔符）
        left_cha3 = [en for en in left_cha if en not in plan]
        for en in left_cha3:
            z = clean((zhcsv.get(en.lower()) or "").replace("?", "·").replace("？", "·"))
            put(en, z, "zhcsv_cha")
        if left_cha3:
            print("  社区表兜底 %d 条 → 补上 %d"
                  % (len(left_cha3), len([e for e in left_cha3 if e in plan])), flush=True)

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
            z = strip_series_paren(zh)
            if not ok_zh(z):
                z = zh
            new_entries.append({"zh": z, "en": en, "cat": "角色", "sub": "图反推",
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
    flush_cache()

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

    need_fix = [e for e in old_tags
                if (e.get("en") or "").strip() in MANUAL and e.get("sub") == "图反推"
                and ok_zh(MANUAL[(e.get("en") or "").strip()])
                and e.get("zh") != MANUAL[(e.get("en") or "").strip()]]
    if not new_entries and not need_fix:
        print("没有需要新增的条目，直接结束")
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = os.path.join(HERE, "tags_cn.backup_wd14_%s.json" % stamp)
    n = 1
    while os.path.exists(bak):          # 别覆盖已有备份
        bak = os.path.join(HERE, "tags_cn.backup_wd14_%s_%d.json" % (stamp, n))
        n += 1
    shutil.copy2(LIB, bak)
    print("已备份:", os.path.basename(bak))

    # 人工校对表对本脚本此前写入的条目同样生效（可重复修正，保持幂等）
    for e in need_fix:
        e["zh"] = MANUAL[(e.get("en") or "").strip()]
    if need_fix:
        print("人工校对修正既有条目 %d 条" % len(need_fix))

    data["tags"] = old_tags + new_entries
    save_lib(data)
    print("已写入 %s（%d 条，%.2f MB），总耗时 %.1fs"
          % (os.path.basename(LIB), len(data["tags"]), os.path.getsize(LIB) / 1048576.0,
             time.time() - t_start))


if __name__ == "__main__":
    main()
