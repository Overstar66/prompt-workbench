# -*- coding: utf-8 -*-
"""fix_all_char_subs.py —— 补全 tags_cn.json 里「角色」条目的作品字段 sub。

背景：约 297 条角色的 sub 是占位值（动漫 / 游戏 / 自定义 / 空），不是真作品名。
本脚本按「确定性从高到低」三级处理：

  1. en 括号后缀规则：_(nikke) → 胜利女神NIKKE、_(doa) → 死或生、_(fate) → Fate ...
  2. 人工核对过的 角色 en → 作品 对照表（约 250 条，逐个确认过，不靠猜）
  3. 仍未确定的，可选地交给本地 Ollama(qwen2.5:7b) 判断，但**只接受**「两次提问
     答案一致」且命中「词库已存在的作品名白名单」的结果；其余一律丢弃，保持原值进报告。
     （实测 qwen2.5:7b 单独一次答得很飘：把「高木同学」说成《高分少女》、把「不知火舞」
     说成《火影忍者》，所以必须双票一致 + 白名单双重闸。本次 297 条全部由 1/2 级确定，
     LLM 实际未参与。）

特性：
  * 幂等：只处理 sub 仍为占位值的条目，所以跑第二遍不会再有改动，也不会再备份。
  * 第一次真正写盘前备份 tags_cn.backup_subs2_<时间>.json。
  * 每 N 条打印进度；结尾输出按作品分组的修正统计 + 剩余不确定清单前 50。

用法：
  python fix_all_char_subs.py               # 正常跑（含 LLM 兜底）
  python fix_all_char_subs.py --dry-run     # 只看会怎么改，不写盘
  python fix_all_char_subs.py --no-llm      # 不调用模型
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = os.path.join(HERE, "tags_cn.json")
EXTRA = os.path.join(HERE, "chars_extra.json")
REPORT = os.path.join(HERE, "fix_all_char_subs_report.txt")
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"

# 这些 sub 不是作品名
PLACEHOLDER = {"", "动漫", "游戏", "自定义"}
# 非角色类别把 sub 当分组名用（发色/姿势/...），不能进作品白名单
NON_WORK = {
    "发色", "发型", "眼睛", "表情", "体型", "身体", "上装", "下装", "连衣裙",
    "制服", "泳装", "配饰", "情趣", "姿势", "日常", "单人", "双人互动", "亲密",
    "全部", "室内", "室外", "光线", "天气", "时间段", "画质", "构图", "视角",
    "镜头", "风格", "色彩", "效果", "袜鞋", "建筑",
}

# ---------------------------------------------------------------- 1. 后缀规则
# (正则, 作品名)。按顺序匹配 en 末尾的 _(xxx)。
SUFFIX_RULES = [
    (r"honkai_star_rail", "崩坏星穹铁道"),
    (r"honkai_impact", "崩坏3"),
    (r"arknights", "明日方舟"),
    (r"azur_lane", "碧蓝航线"),
    (r"blue_archive", "蔚蓝档案"),
    (r"genshin_impact", "原神"),
    (r"nikke", "胜利女神NIKKE"),
    (r"doa", "死或生"),
    (r"fate", "Fate"),
    (r"vocaloid", "VOCALOID"),
    (r"re:zero", "Re:零"),
    (r"sao", "刀剑神域"),
    (r"sousou_no_frieren", "芙莉莲"),
    (r"darling_in_the_franxx", "Darling in the Franxx"),
    (r"maidragon", "小林家的龙女仆"),
    (r"nier", "尼尔"),
    (r"karakai_jouzu", "擅长捉弄的高木同学"),
    (r"one_piece", "海贼王"),
    (r"gintama", "银魂"),
    (r"chainsaw_man", "电锯人"),
    (r"majo_no_tabiji", "魔女之旅"),
    (r"overlord", "OVERLORD"),
    (r"made_in_abyss", "来自深渊"),
    (r"kemono_friends", "兽娘动物园"),
    (r"ff13", "最终幻想13"),
    (r"ff7", "最终幻想7"),
]

# ------------------------------------------------------- 2. 人工核对的对照表
# 只写「我确定」的：角色 en → 作品名。作品名优先复用词库里已有的写法
# （含 chars_extra.json 里的写法，因为 app 运行时会把它并进词库）。
EN_MAP = {
    # 东方Project
    "hakurei_reimu": "东方Project", "kirisame_marisa": "东方Project",
    "izayoi_sakuya": "东方Project", "flandre_scarlet": "东方Project",
    "remilia_scarlet": "东方Project", "patchouli_knowledge": "东方Project",
    "konpaku_youmu": "东方Project", "saigyouji_yuyuko": "东方Project",
    "shameimaru_aya": "东方Project", "kochiya_sanae": "东方Project",
    "yakumo_yukari": "东方Project", "alice_margatroid": "东方Project",
    "reisen_udongein_inaba": "东方Project", "fujiwara_no_mokou": "东方Project",
    "houraisan_kaguya": "东方Project", "komeiji_koishi": "东方Project",
    "komeiji_satori": "东方Project", "shiki_eiki": "东方Project",
    "hinanawi_tenshi": "东方Project", "ibuki_suika": "东方Project",
    # VOCALOID / UTAU
    "hatsune_miku": "VOCALOID", "kagamine_rin": "VOCALOID",
    "megurine_luka": "VOCALOID", "luo_tianyi": "VOCALOID",
    "gumi_(vocaloid)": "VOCALOID", "meiko_(vocaloid)": "VOCALOID",
    "yuzuki_yukari": "VOCALOID", "kasane_teto": "UTAU",
    # 龙与虎
    "kushieda_minori": "龙与虎", "kawashima_ami": "龙与虎",
    # 约会大作战
    "tokisaki_kurumi": "约会大作战", "yatogami_tohka": "约会大作战",
    "itsuka_kotori": "约会大作战", "yoshino": "约会大作战",
    # Re:零
    "rem": "Re:零", "ram_(re:zero)": "Re:零",
    "emilia": "Re:零", "beatrice_(re:zero)": "Re:零",
    # 刀剑神域
    "asuna_(sao)": "刀剑神域", "leafa": "刀剑神域",
    "sinon": "刀剑神域", "yui_(sao)": "刀剑神域",
    # 某科学的超电磁炮
    "misaka_mikoto": "超电磁炮", "shirai_kuroko": "超电磁炮",
    "uiharu_kazari": "超电磁炮", "saten_ruiko": "超电磁炮",
    "shokuhou_misaki": "超电磁炮",
    # 辉夜大小姐
    "shinomiya_kaguya": "辉夜大小姐", "fujiwara_chika": "辉夜大小姐",
    "iino_miko": "辉夜大小姐", "shirogane_kei": "辉夜大小姐",
    # 我的青春恋爱物语
    "yukinoshita_yukino": "我的青春恋爱物语",
    "yuigahama_yui": "我的青春恋爱物语",
    "isshiki_iroha": "我的青春恋爱物语",
    # 五等分的新娘
    "nakano_miku": "五等分的新娘", "nakano_ichika": "五等分的新娘",
    "nakano_nino": "五等分的新娘", "nakano_yotsuba": "五等分的新娘",
    "nakano_itsuki": "五等分的新娘",
    # 埃罗芒阿老师
    "izumi_sagiri": "埃罗芒阿老师",
    # 小林家的龙女仆
    "kanna_kamui": "小林家的龙女仆", "tohru_(maidragon)": "小林家的龙女仆",
    "lucoa": "小林家的龙女仆",
    # Fate
    "illyasviel_von_einzbern": "Fate", "tohsaka_rin": "Fate",
    "matou_sakura": "Fate", "artoria_pendragon": "Fate",
    "mash_kyrielight": "Fate", "jeanne_d'arc_(fate)": "Fate",
    "scathach": "Fate", "nero_claudius": "Fate", "tamamo_no_mae": "Fate",
    "morgan_(fate)": "Fate", "baobhan_sith": "Fate",
    "artoria_caster": "Fate", "koyanskaya_of_light": "Fate",
    "melusine_(fate)": "Fate", "ereshkigal_(fate)": "Fate",
    "abigail_williams_(fate)": "Fate", "katsushika_hokusai": "Fate",
    "mystery_heroine_x": "Fate", "okita_souji": "Fate",
    "oda_nobunaga": "Fate", "shuten_douji": "Fate",
    "minamoto_no_raikou": "Fate", "tomoe_gozen": "Fate",
    "kama_(fate)": "Fate", "kiara_sesshouin": "Fate",
    "meltryllis": "Fate", "space_ishtar": "Fate",
    "anastasia_(fate)": "Fate", "carmilla_(fate)": "Fate",
    "nemo_(fate)": "Fate", "kiyohime_(fate)": "Fate",
    # 尼尔 / 最终幻想
    "2b_(nier)": "尼尔",
    "tifa_lockhart": "最终幻想7", "aerith_gainsborough": "最终幻想7",
    "yuffie_kisaragi": "最终幻想7", "lightning_(ff13)": "最终幻想13",
    # EVA
    "ayanami_rei": "EVA", "katsuragi_misato": "EVA",
    # 魔法少女小圆
    "kaname_madoka": "魔法少女小圆", "akemi_homura": "魔法少女小圆",
    "miki_sayaka": "魔法少女小圆", "tomoe_mami": "魔法少女小圆",
    "sakura_kyouko": "魔法少女小圆",
    # 路人女主
    "kato_megumi": "路人女主", "sawamura_spencer_eriri": "路人女主",
    "kasumigaoka_utaha": "路人女主",
    # 高木同学
    "takagi_(karakai_jouzu)": "擅长捉弄的高木同学",
    # 中二病 / 冰菓
    "takanashi_rikka": "中二病也要谈恋爱", "chitanda_eru": "冰菓",
    # 轻音少女
    "hirasawa_yui": "轻音少女", "akiyama_mio": "轻音少女",
    "nakano_azusa": "轻音少女",
    # 凉宫春日
    "suzumiya_haruhi": "凉宫春日", "nagato_yuki": "凉宫春日",
    "asahina_mikuru": "凉宫春日",
    # 幸运星
    "izumi_konata": "幸运星", "hiiragi_kagami": "幸运星",
    "hiiragi_tsukasa": "幸运星",
    # 物语系列
    "senjougahara_hitagi": "物语系列", "hachikuji_mayoi": "物语系列",
    "oshino_shinobu": "物语系列", "sengoku_nadeko": "物语系列",
    "hanekawa_tsubasa": "物语系列",
    # 灼眼的夏娜 / 零之使魔 / 旋风管家
    "shana": "灼眼的夏娜", "louise_francoise": "零之使魔",
    "sanzenin_nagi": "旋风管家", "katsura_hinagiku": "旋风管家",
    # 东京喰种 / 加速世界 / 进击的巨人
    "kirishima_touka": "东京喰种", "kuroyukihime": "加速世界",
    "mikasa_ackerman": "进击的巨人", "annie_leonhart": "进击的巨人",
    "sasha_blouse": "进击的巨人", "christa_lenz": "进击的巨人",
    # 海贼王
    "nami_(one_piece)": "海贼王", "nico_robin": "海贼王",
    "boa_hancock": "海贼王", "perona": "海贼王", "shirahoshi": "海贼王",
    # 火影忍者
    "haruno_sakura": "火影忍者", "tsunade": "火影忍者",
    "hyuuga_hinata": "火影忍者", "mei_terumi": "火影忍者",
    # 死神
    "inoue_orihime": "死神", "kuchiki_rukia": "死神",
    "shihouin_yoruichi": "死神", "nel_tu": "死神",
    # 妖精的尾巴
    "erza_scarlet": "妖精的尾巴", "lucy_heartfilia": "妖精的尾巴",
    "wendy_marvell": "妖精的尾巴",
    # 美少女战士 / 魔卡少女樱
    "tsukino_usagi": "美少女战士",
    "kinomoto_sakura": "魔卡少女樱", "daidouji_tomoyo": "魔卡少女樱",
    # 银魂
    "kagura_(gintama)": "银魂", "tsukuyo": "银魂",
    # 名侦探柯南
    "haibara_ai": "名侦探柯南", "moori_ran": "名侦探柯南",
    "vermouth": "名侦探柯南",
    # 叛逆的鲁路修
    "c.c.": "叛逆的鲁路修", "euphemia_li_britannia": "叛逆的鲁路修",
    "shirley_fenette": "叛逆的鲁路修",
    # 狼与香辛料 / 租借女友 / 宇崎学妹 / 长瀞同学
    "horo": "狼与香辛料",
    "mizuhara_chizuru": "租借女友", "nanami_mami": "租借女友",
    "uzaki_hana": "宇崎学妹想要玩", "nagatoro_hayase": "长瀞同学",
    # 更衣人偶
    "kitagawa_marin": "更衣人偶", "kurokawa_akane": "更衣人偶",
    # 芙莉莲
    "frieren": "芙莉莲", "fern_(sousou_no_frieren)": "芙莉莲",
    "aura_(sousou_no_frieren)": "芙莉莲",
    # 咒术回战
    "kugisaki_nobara": "咒术回战", "zen'in_maki": "咒术回战",
    "ieiri_shouko": "咒术回战",
    # 鬼灭之刃
    "kamado_nezuko": "鬼灭之刃", "kochou_shinobu": "鬼灭之刃",
    "kanroji_mitsuri": "鬼灭之刃", "tsuyuri_kanao": "鬼灭之刃",
    # 电锯人
    "makima": "电锯人", "power_(chainsaw_man)": "电锯人", "reze": "电锯人",
    # 间谍过家家
    "yor_forger": "间谍过家家", "anya_forger": "间谍过家家",
    # 孤独摇滚
    "gotoh_hitori": "孤独摇滚", "ijichi_nijika": "孤独摇滚",
    "yamada_ryo": "孤独摇滚", "kita_ikuyo": "孤独摇滚",
    # Lycoris Recoil
    "chisato_nishikigi": "Lycoris Recoil", "takina_inoue": "Lycoris Recoil",
    # 我推的孩子
    "hoshino_ai": "我推的孩子", "hoshino_ruby": "我推的孩子",
    "arima_kana": "我推的孩子",
    # 魔女之旅
    "elaina_(majo_no_tabiji)": "魔女之旅",
    # 无职转生
    "roxy_migurdia": "无职转生", "eris_boreas_greyrat": "无职转生",
    "sylphiette": "无职转生",
    # 转生史莱姆 / OVERLORD / 盾之勇者
    "rimuru_tempest": "转生史莱姆",
    "albedo_(overlord)": "OVERLORD", "shalltear_bloodfallen": "OVERLORD",
    "raphtalia": "盾之勇者",
    # Darling in the Franxx
    "zero_two_(darling_in_the_franxx)": "Darling in the Franxx",
    "ichigo_(darling_in_the_franxx)": "Darling in the Franxx",
    # SSSS.GRIDMAN
    "takarada_rikka": "SSSS.GRIDMAN", "shinjou_akane": "SSSS.GRIDMAN",
    # 来自深渊
    "riko_(made_in_abyss)": "来自深渊", "nanachi": "来自深渊",
    # 兽娘动物园
    "serval_(kemono_friends)": "兽娘动物园",
    # 崩坏星穹铁道
    "march_7th": "崩坏星穹铁道", "bronya_rand": "崩坏星穹铁道",
    "silver_wolf": "崩坏星穹铁道", "jingliu": "崩坏星穹铁道",
    "tingyun": "崩坏星穹铁道", "fu_xuan": "崩坏星穹铁道",
    "sushang": "崩坏星穹铁道", "qingque": "崩坏星穹铁道",
    "guinaifen": "崩坏星穹铁道", "xueyi": "崩坏星穹铁道",
    "ruan_mei": "崩坏星穹铁道", "huohuo": "崩坏星穹铁道",
    "herta": "崩坏星穹铁道", "yunli": "崩坏星穹铁道",
    "feixiao": "崩坏星穹铁道", "lingsha": "崩坏星穹铁道",
    "rappa": "崩坏星穹铁道",
    # 崩坏3
    "kiana_kaslana": "崩坏3", "raiden_mei": "崩坏3",
    "yae_sakura": "崩坏3", "theresa_apocalypse": "崩坏3",
    "fu_hua": "崩坏3", "rita_rossweisse": "崩坏3",
    "durandal_(honkai_impact)": "崩坏3",
    "elysia_(honkai_impact)": "崩坏3", "seele_vollerei": "崩坏3",
    # 死或生
    "kasumi_(doa)": "死或生", "ayane_(doa)": "死或生",
    "marie_rose": "死或生", "honoka_(doa)": "死或生",
    "kokoro_(doa)": "死或生", "tina_armstrong": "死或生",
    "lei_fang": "死或生", "hitomi_(doa)": "死或生",
    "christie_(doa)": "死或生", "helena_douglas": "死或生",
    "mira_(doa)": "死或生", "momiji_(doa)": "死或生",
    "rachel_(doa)": "死或生", "nyotengu": "死或生",
    "tamaki_(doa)": "死或生", "lisa_hamilton": "死或生",
    "nico_(doa)": "死或生", "phase_4": "死或生",
    # 拳皇
    "mai_shiranui": "拳皇", "kula_diamond": "拳皇",
    # 原神
    "ganyu": "原神", "hu_tao": "原神", "raiden_shogun": "原神",
    "yae_miko": "原神", "furina": "原神", "kamisato_ayaka": "原神",
    "yoimiya": "原神", "sangonomiya_kokomi": "原神", "nahida": "原神",
    "nilou": "原神", "shenhe": "原神", "yelan": "原神", "keqing": "原神",
    "fischl": "原神", "eula": "原神", "klee": "原神", "diona": "原神",
    "rosaria": "原神", "beidou": "原神", "ningguang": "原神",
    "xiangling": "原神", "lumine": "原神", "arlecchino": "原神",
    # 胜利女神NIKKE（无后缀的几位）
    "modernia": "胜利女神NIKKE", "privaty": "胜利女神NIKKE",
    "eunhwa": "胜利女神NIKKE",
}

# 本脚本会新引入的作品名（词库里原先没有的）。写清楚便于复核。
NEW_WORKS = {
    "UTAU", "超电磁炮", "路人女主", "幸运星", "物语系列", "灼眼的夏娜",
    "零之使魔", "旋风管家", "叛逆的鲁路修", "狼与香辛料", "宇崎学妹想要玩",
    "长瀞同学", "Darling in the Franxx", "SSSS.GRIDMAN", "来自深渊",
    "死或生", "拳皇", "最终幻想13",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def build_whitelist(tags):
    """词库里「已经存在」的作品名：角色条目的 sub（含 chars_extra）+ 非角色类别里
    那些明显是作品名的 sub。排除占位值与非作品分组名。"""
    works = set()
    for x in tags:
        s = (x.get("sub") or "").strip()
        if s and s not in PLACEHOLDER and s not in NON_WORK:
            works.add(s)
    if os.path.exists(EXTRA):
        try:
            for x in load_json(EXTRA):
                s = (x.get("sub") or "").strip()
                if s and s not in PLACEHOLDER and s not in NON_WORK:
                    works.add(s)
        except Exception:
            pass
    return works


def suffix_lookup(en):
    m = re.search(r"_\(([^()]*)\)\s*$", en)
    if not m:
        return None
    raw = m.group(1).strip().lower()
    for pat, work in SUFFIX_RULES:
        if re.search(pat, raw):
            return work
    return None


def ask_llm(zh, en):
    """让本地模型判断，只返回干净的作品名（或 None）。"""
    prompt = (
        "你是动漫游戏角色资料库。判断角色「%s」(英文 tag: %s) 出自哪部动漫/游戏/漫画。\n"
        "只输出作品的中文名，不要标点，不要解释。如果不确定，只输出：不确定"
        % (zh, en)
    )
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "num_predict": 24},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read().decode("utf-8")).get("response", "")
    ans = out.strip().splitlines()[0].strip() if out.strip() else ""
    ans = re.sub(r"^[《「『\"']|[》」』\"'。，,.]$", "", ans).strip()
    ans = re.sub(r"^(作品|答案|出处)[：:]\s*", "", ans).strip()
    return ans or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--progress", type=int, default=25)
    args = ap.parse_args()

    t0 = time.time()
    doc = load_json(TAGS)
    tags = doc["tags"]
    whitelist = build_whitelist(tags)
    valid_works = whitelist | NEW_WORKS

    chars = [x for x in tags if x.get("cat") == "角色"]
    todo = [x for x in chars if (x.get("sub") or "").strip() in PLACEHOLDER]
    print("角色 %d 条，其中 sub 为占位值 %d 条；词库作品名 %d 个"
          % (len(chars), len(todo), len(whitelist)))

    changes = []       # (zh, en, old, new, how)
    uncertain = []     # (zh, en, old)
    llm_used = 0

    for i, x in enumerate(todo, 1):
        zh, en = x.get("zh", ""), x.get("en", "")
        old = (x.get("sub") or "").strip()
        new, how = None, ""

        # 1) 后缀规则
        s = suffix_lookup(en)
        if s:
            new, how = s, "suffix"
        # 2) 对照表
        if new is None:
            s = EN_MAP.get(en)
            if s:
                new, how = s, "map"

        # 3) LLM 兜底（两次一致 + 白名单，双闸）
        if new is None and not args.no_llm:
            try:
                a1 = ask_llm(zh, en)
                a2 = ask_llm(zh, en)
                llm_used += 1
                if a1 and a1 == a2 and a1 in whitelist:
                    new, how = a1, "llm"
            except Exception as e:      # 模型挂了也不影响主流程
                print("  ! LLM 调用失败 %s: %s" % (en, e))

        if new and new not in PLACEHOLDER:
            assert new in valid_works or how == "map", (en, new)
            x["sub"] = new
            changes.append((zh, en, old, new, how))
        else:
            uncertain.append((zh, en, old))

        if args.progress and i % args.progress == 0:
            print("  ... 已处理 %d/%d，已定 %d，存疑 %d"
                  % (i, len(todo), len(changes), len(uncertain)))

    # ------------------------------------------------ 报告
    by_work = collections.Counter(c[3] for c in changes)
    lines = []
    lines.append("=" * 66)
    lines.append("fix_all_char_subs 报告  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 66)
    lines.append("角色总数            : %d" % len(chars))
    lines.append("占位值待处理        : %d" % len(todo))
    lines.append("本次可定 / 已修正   : %d" % len(changes))
    lines.append("其中 后缀规则       : %d" % sum(1 for c in changes if c[4] == "suffix"))
    lines.append("其中 人工对照表     : %d" % sum(1 for c in changes if c[4] == "map"))
    lines.append("其中 本地模型白名单 : %d" % sum(1 for c in changes if c[4] == "llm"))
    lines.append("仍不确定（保持原值）: %d" % len(uncertain))
    lines.append("")
    lines.append("—— 按作品分组（全部 %d 部）——" % len(by_work))
    for k, v in by_work.most_common():
        lines.append("  %4d  %s%s" % (v, k, "   [新增作品名]" if k in NEW_WORKS else ""))
    lines.append("")
    lines.append("—— 剩余不确定 前 50（zh / en / 原 sub）——")
    for zh, en, old in uncertain[:50]:
        lines.append("  %s / %s / %s" % (zh, en, old))
    lines.append("")
    lines.append("耗时 %.1f 秒" % (time.time() - t0))
    report = "\n".join(lines)
    print(report)

    # ------------------------------------------------ 写盘
    if not changes:
        print("没有需要改的条目（幂等：可能已经跑过了），不写文件、不备份。")
        return 0
    if args.dry_run:
        print("[dry-run] 不写盘。")
        return 0

    backup = os.path.join(
        HERE, "tags_cn.backup_subs2_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(TAGS, backup)
    print("已备份 -> %s" % os.path.basename(backup))
    save_json(TAGS, doc)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report + "\n")
    print("已写入 tags_cn.json（%d 条），报告 -> %s"
          % (len(changes), os.path.basename(REPORT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
