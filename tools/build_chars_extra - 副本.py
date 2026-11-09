#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成 chars_extra.json —— 标签库的「附加角色包」。

用途
----
tags_cn.json 是别人的产物（只读）。本脚本把「补充角色」单独维护在这个文件里：
  1. 每个条目带 5 个外貌字段（hair / eyes / outfit / body / chest）；
  2. 只写 chars_extra.json，不改动 tags_cn.json 与其它任何文件；
  3. 可重复运行（幂等）：重复跑只会得到同样的 chars_extra.json。

用法
----
    python build_chars_extra.py

如何新增角色
------------
在下面 CHARS 里对应作品的列表中追加一行八元组即可：
    (en, zh, hair, eyes, outfit, body, chest)
  - en   : booru 写法，小写 + 下划线，例如 gotoh_hitori / kita_ikuyo
  - zh   : 中文名
  - body : 娇小 / 纤细 / 标准 / 高挑 / 丰满
  - chest: 贫乳 / 标准 / 巨乳
  - 作品名直接用 CHARS 的 key（作品中文名），会自动写进 sub 字段。
脚本末尾的校验会拦住：缺字段、空值、非中文、en 重复、与 tags_cn.json 撞车。
"""

import json
import os
import sys
from collections import OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(BASE, "tags_cn.json")
APP_PATH = os.path.join(BASE, "chars_app.json")
OUT_PATH = os.path.join(BASE, "chars_extra.json")

BODY_OK = ("娇小", "纤细", "标准", "高挑", "丰满")
CHEST_OK = ("贫乳", "标准", "巨乳")
APP_FIELDS = ("hair", "eyes", "outfit", "body", "chest")

# ---------------------------------------------------------------------------
# 补充角色表：作品名 -> [(en, zh, hair, eyes, outfit, body, chest), ...]
# 已有角色见 tags_cn.json，这里只放它里面没有的（按 en 去重）。
# ---------------------------------------------------------------------------
CHARS = OrderedDict([

    # ------------------------------ 孤独摇滚 ------------------------------
    ("孤独摇滚", [
        ("kikuri_hiroi", "广井菊里", "紫色长发，略显凌乱", "红色眼睛", "米色外套，白色T恤配牛仔裤", "标准", "巨乳"),
        ("ijichi_seika", "伊地知星歌", "金色长发，侧马尾", "红色眼睛", "黑色外套，白色衬衫", "标准", "标准"),
    ]),

    # ------------------------------ 轻音少女 ------------------------------
    ("轻音少女", [
        ("tainaka_ritsu", "田井中律", "深棕色短发，黄色发箍", "棕色眼睛", "樱丘高中校服，白色发箍", "标准", "标准"),
        ("kotobuki_tsumugi", "琴吹紬", "金色长发，齐刘海", "蓝色眼睛", "樱丘高中校服", "标准", "巨乳"),
        ("hirasawa_ui", "平泽忧", "棕色短发，波波头", "棕色眼睛", "樱丘高中校服", "娇小", "贫乳"),
    ]),

    # ------------------------------ 莉可丽丝 ------------------------------
    ("莉可丽丝", [
        ("kusunoki_(lycoris_recoil)", "楠木", "黑色长发，低马尾", "紫色眼睛", "黑色西装，眼镜", "高挑", "标准"),
        ("kurumi_(lycoris_recoil)", "胡桃", "金色长发", "蓝色眼睛", "灰色连帽衫", "娇小", "贫乳"),
        ("harukawa_fuki", "春川风希", "黑色短发，马尾", "紫色眼睛", "深蓝色莉可丽丝制服", "标准", "标准"),
    ]),

    # -------------------------- 更衣人偶坠入爱河 --------------------------
    ("更衣人偶坠入爱河", [
        ("inui_sajuna", "乾纱寿叶", "黑色长发，双马尾", "红色眼睛", "校服，黑色外套", "标准", "标准"),
        ("inui_shinju", "乾心寿", "黑色长直发", "紫色眼睛", "校服，白衬衫配百褶裙", "娇小", "贫乳"),
    ]),

    # ------------------------------ 五等分的新娘 ------------------------------
    ("五等分的新娘", [
        ("uesugi_raiha", "上杉濑叶", "橙色短发，双马尾", "蓝色眼睛", "校服，白衬衫配百褶裙", "娇小", "贫乳"),
        ("nakano_rena", "中野零奈", "棕色长发", "棕色眼睛", "白色连衣裙", "标准", "标准"),
    ]),

    # ------------------------------ 我推的孩子 ------------------------------
    ("我推的孩子", [
        ("hoshino_aqua", "星野阿库亚", "金色短发，发梢偏深", "蓝色眼睛", "校服，黑色外套", "高挑", "标准"),
        ("kotobuki_minami", "寿美奈美", "黑色长发", "棕色眼睛", "白色衬衫，黑色外套", "高挑", "巨乳"),
    ]),

    # -------------------------- 我的青春恋爱物语 --------------------------
    ("我的青春恋爱物语", [
        ("hiratsuka_shizuka", "平冢静", "黑色长发", "红色眼睛", "白色大褂，黑色衬衫", "高挑", "巨乳"),
        ("hikigaya_komachi", "比企谷小町", "深棕色中长发", "棕色眼睛", "总武高黑色西装校服配红格裙", "娇小", "标准"),
    ]),

    # ------------------------------ 兔女郎学姐 ------------------------------
    ("兔女郎学姐", [
        ("sakurajima_mai", "樱岛麻衣", "黑色长直发，兔耳发带", "紫色眼睛", "校服，黑色兔女郎装", "高挑", "标准"),
        ("koga_tomoe", "古贺朋绘", "浅棕色短发，双马尾", "棕色眼睛", "校服，白衬衫配百褶裙", "娇小", "标准"),
        ("futaba_rio", "双叶理央", "黑色短发", "黑色眼睛", "白色大褂", "标准", "标准"),
        ("toyohama_nodoka", "丰浜和花", "浅色长发", "蓝色眼睛", "白色偶像装", "标准", "标准"),
        ("makinohara_shouko", "牧之原翔子", "黑色长发", "蓝色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
        ("azusagawa_kaede", "梓川枫", "白色长发", "蓝色眼睛", "白色连衣裙", "娇小", "贫乳"),
    ]),

    # ------------------------------ 无职转生 ------------------------------
    ("无职转生", [
        ("elinalise_dragonroad", "艾莉娜丽洁·杜拉冈罗德", "金色长发", "绿色眼睛", "冒险者装，精灵耳", "高挑", "巨乳"),
        ("zenith_greyrat", "塞妮丝·格雷拉特", "棕色长发", "棕色眼睛", "白绿色长袍", "标准", "标准"),
        ("lilia_(mushoku_tensei)", "莉莉娅", "紫色短发", "蓝色眼睛", "白色女仆装", "标准", "标准"),
    ]),

    # -------------------------- Re:从零开始的异世界生活 --------------------------
    ("Re:从零开始的异世界生活", [
        ("priscilla_barielle", "普莉希拉·巴利埃尔", "红色长发", "红色眼睛", "红色洋装", "高挑", "巨乳"),
        ("crusch_karsten", "库珥修·卡尔斯腾", "绿色长发", "绿色眼睛", "白色军装", "高挑", "标准"),
        ("anastasia_hoshin", "安娜塔西亚·合辛", "紫色长发", "紫色眼睛", "紫白色洋装", "娇小", "标准"),
        ("petra_leyte", "佩特拉·莱特", "棕色短发", "棕色眼睛", "白色女仆装，围裙", "娇小", "贫乳"),
        ("satella", "莎缇拉", "黑色长发", "紫色眼睛", "黑色长袍", "高挑", "巨乳"),
    ]),

    # ------------------------------ 龙女仆 ------------------------------
    ("龙女仆", [
        ("elma_(maidragon)", "艾尔玛·乔伊斯", "黑色长发，头生双角", "红色眼睛", "公司制服", "标准", "巨乳"),
        ("ilulu", "伊露露", "红色短发，双马尾，头生双角", "红色眼睛", "红色连衣裙", "娇小", "巨乳"),
    ]),

    # ------------------------------ 辉夜大小姐 ------------------------------
    ("辉夜大小姐", [
        ("hayasaka_ai", "早坂爱", "金色长发，编发", "蓝色眼睛", "秀知院黑西装校服配红裙", "标准", "标准"),
        ("shijo_maki", "四条真妃", "紫色长发，双马尾", "紫色眼睛", "秀知院黑西装校服配红裙", "标准", "标准"),
        ("kashiwagi_nagisa", "柏木渚", "棕色长发", "棕色眼睛", "秀知院黑西装校服配红裙", "标准", "标准"),
        ("osaragi_kobachi", "大佛小钵", "黑色长发", "黑色眼睛", "秀知院黑西装校服配红裙", "标准", "巨乳"),
    ]),

    # ------------------------------ 干物妹小埋 ------------------------------
    ("干物妹小埋", [
        ("doman_umaru", "土间埋", "橙色长发，双马尾", "橙色眼睛", "白色卫衣，橙色短裤", "娇小", "贫乳"),
        ("ebina_nana", "海老名菜菜", "黑色长发", "黑色眼睛", "校服，白衬衫配百褶裙", "标准", "巨乳"),
        ("homba_kirie", "本场切绘", "黑色短发", "黑色眼睛", "校服，白衬衫配百褶裙", "娇小", "贫乳"),
        ("tachibana_sylphynford", "橘·希尔芬福特", "金色长发，双马尾", "蓝色眼睛", "白色连衣裙", "标准", "标准"),
    ]),

    # ------------------------------ 埃罗芒阿老师 ------------------------------
    ("埃罗芒阿老师", [
        ("yamada_elf", "山田妖精", "金色长发，双马尾", "蓝色眼睛", "白色哥特洋装", "娇小", "标准"),
        ("senju_muramasa", "千寿村征", "黑色长直发", "黑色眼睛", "深色和服", "标准", "标准"),
        ("jinno_megumi", "神野惠", "黑色短发", "棕色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
    ]),

    # -------------------------- 擅长捉弄的高木同学 --------------------------
    ("擅长捉弄的高木同学", [
        ("mina_(karakai_jouzu)", "美奈", "浅棕色长发，马尾", "棕色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
        ("sanae_(karakai_jouzu)", "早苗", "黑色短发", "黑色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
    ]),

    # ------------------------------ 凉宫春日 ------------------------------
    ("凉宫春日", [
        ("asakura_ryouko", "朝仓凉子", "绿色长发", "绿色眼睛", "北高校服，白衬衫配百褶裙", "标准", "标准"),
        ("tsuruya", "鹤屋", "绿色长发", "绿色眼睛", "北高校服，白衬衫配百褶裙", "标准", "标准"),
    ]),

    # ------------------------------ Fate/stay night ------------------------------
    ("Fate/stay night", [
        ("fujimura_taiga", "藤村大河", "棕色长发", "棕色眼睛", "黄色外套，黑色上衣", "标准", "标准"),
        ("medusa_(fate)", "美杜莎", "紫色超长发", "紫色眼睛", "黑色紧身衣，紫色面罩", "高挑", "巨乳"),
        ("artoria_pendragon_(alter)", "阿尔托莉雅·潘德拉贡·Alter", "金色长发，盘发", "黄色眼睛", "黑色骑士装，黑色铠甲", "娇小", "贫乳"),
    ]),

    # ------------------------------ 原神 ------------------------------
    ("原神", [
        ("navia", "娜维娅", "金色长卷发", "蓝色眼睛", "白金色礼服，宽檐帽", "高挑", "巨乳"),
        ("clorinde", "克洛琳德", "深蓝色长发", "蓝色眼睛", "深蓝色军装", "高挑", "标准"),
        ("sigewinne", "希格雯", "浅蓝色短发", "蓝色眼睛", "白蓝色护士装", "娇小", "贫乳"),
        ("chiori", "千织", "黑色短发", "紫色眼睛", "黑色和风洋装", "标准", "巨乳"),
        ("chevreuse", "夏沃蕾", "红色短发", "红色眼睛", "白红色军装", "标准", "标准"),
        ("faruzan", "珐露珊", "蓝绿色长发，双马尾", "蓝绿色眼睛", "白蓝色学者装", "标准", "标准"),
        ("layla_(genshin_impact)", "莱依拉", "蓝紫色长发，双马尾", "蓝色眼睛", "白紫色学者装", "标准", "标准"),
        ("kuki_shinobu", "久岐忍", "绿色短发", "绿色眼睛", "绿色忍者装，面罩", "标准", "标准"),
        ("xianyun", "闲云", "黑色长发，眼镜", "金色眼睛", "白蓝色仙装", "高挑", "巨乳"),
        ("yanfei", "烟绯", "粉色长发", "粉色眼睛", "红白色律师装，帽子", "娇小", "标准"),
        ("yun_jin", "云堇", "黑色长发，戏曲头饰", "红色眼睛", "白色戏曲装", "娇小", "贫乳"),
    ]),

    # ------------------------------ 崩坏3 ------------------------------
    ("崩坏3", [
        ("bronya_zaychik", "布洛妮娅·扎伊切克", "灰色长发，双螺旋卷", "灰色眼睛", "白蓝色军装", "娇小", "贫乳"),
        ("kallen_kaslana", "卡莲·卡斯兰娜", "白色长发", "蓝色眼睛", "白红色修女装", "标准", "标准"),
        ("aponia", "阿波尼亚", "白色长发", "紫色眼睛", "白色修女装", "高挑", "巨乳"),
        ("mobius_(honkai_impact)", "梅比乌斯", "绿色长发", "绿色眼睛", "白绿色实验服", "标准", "标准"),
        ("pardofelis", "帕朵菲莉丝", "灰褐色短发，猫耳", "绿色眼睛", "灰色斗篷", "娇小", "贫乳"),
        ("griseo", "格蕾修", "白色短发", "蓝色眼睛", "白色洋装", "娇小", "贫乳"),
    ]),

    # ------------------------------ 蔚蓝档案 ------------------------------
    ("蔚蓝档案", [
        ("ajitani_hifumi", "阿慈谷日富美", "金色长发，双马尾", "蓝色眼睛", "校服，白衬衫配百褶裙", "标准", "巨乳"),
        ("kirifuji_nagisa", "桐藤渚", "白色长发", "蓝色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
        ("kensaki_tsurugi", "剑先鹤城", "黑色短发", "红色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
        ("shizuyama_mashiro", "静山真白", "白色长发", "蓝色眼睛", "修女装", "标准", "标准"),
        ("hasumi_(blue_archive)", "羽川莲见", "黑色长发", "红色眼睛", "校服，白衬衫配百褶裙", "高挑", "标准"),
        ("izuna_(blue_archive)", "泉奈", "棕色短发，狐耳", "红色眼睛", "忍者装", "娇小", "标准"),
        ("atsuko_(blue_archive)", "元宫温", "紫色长发", "紫色眼睛", "校服，白衬衫配百褶裙", "标准", "标准"),
    ]),

    # ------------------------------ 明日方舟 ------------------------------
    ("明日方舟", [
        ("saria_(arknights)", "塞雷娅", "银灰色短发", "蓝色眼睛", "白蓝色研究员装", "高挑", "巨乳"),
        ("swire_(arknights)", "诗怀雅", "棕色长发", "棕色眼睛", "白金色西装", "标准", "标准"),
        ("dobermann_(arknights)", "杜宾", "棕色长发", "棕色眼睛", "黑色军装", "高挑", "标准"),
        ("estelle_(arknights)", "艾丝黛尔", "金色长发", "绿色眼睛", "白色连衣裙", "标准", "标准"),
        ("astesia_(arknights)", "星极", "银白色长发", "蓝色眼睛", "白蓝色礼服", "标准", "标准"),
        ("suzuran_(arknights)", "铃兰", "白色长发，狐耳", "蓝色眼睛", "白蓝色和风装", "娇小", "贫乳"),
        ("goldenglow_(arknights)", "澄闪", "金色长发，猫耳", "蓝色眼睛", "白金色裙装", "标准", "标准"),
        ("ines_(arknights)", "伊内丝", "黑色短发", "红色眼睛", "黑色作战服", "高挑", "巨乳"),
    ]),

    # ------------------------------ 胜利女神NIKKE ------------------------------
    ("胜利女神NIKKE", [
        ("helm_(nikke)", "赫尔姆", "蓝色长发", "蓝色眼睛", "蓝白色军装", "高挑", "巨乳"),
        ("cinderella_(nikke)", "辛德瑞拉", "银白色长发", "蓝色眼睛", "白色礼服", "高挑", "巨乳"),
        ("maxwell_(nikke)", "麦斯威尔", "紫色长发", "紫色眼睛", "紫黑色战斗服", "标准", "巨乳"),
        ("laplace_(nikke)", "拉普拉斯", "蓝色长发", "蓝色眼睛", "白蓝色战斗服", "标准", "标准"),
    ]),

    # ------------------------------ 咒术回战 ------------------------------
    ("咒术回战", [
        ("miwa_kasumi", "三轮霞", "黑色长发，马尾", "蓝色眼睛", "咒术高专校服", "标准", "标准"),
        ("iori_utahime", "庵歌姬", "黑色长发", "黑色眼睛", "巫女装", "高挑", "巨乳"),
        ("zenin_mai", "禅院真依", "黑色短发", "黑色眼睛", "咒术高专校服", "标准", "标准"),
        ("meimei_(jujutsu_kaisen)", "冥冥", "白色长发", "蓝色眼睛", "白色外套", "高挑", "巨乳"),
    ]),

    # ------------------------------ 鬼灭之刃 ------------------------------
    ("鬼灭之刃", [
        ("daki", "堕姬", "白色长发", "红色眼睛", "红色和服", "高挑", "巨乳"),
        ("tamayo_(kimetsu_no_yaiba)", "珠世", "黑色长发", "紫色眼睛", "紫色和服", "标准", "标准"),
        ("kanzaki_aoi", "神崎葵", "黑色短发，双马尾", "蓝色眼睛", "鬼杀队制服", "娇小", "贫乳"),
        ("kochou_kanae", "胡蝶香奈惠", "黑色长发，紫色发梢", "紫色眼睛", "蝴蝶纹羽织", "标准", "标准"),
    ]),

    # ------------------------------ 电锯人 ------------------------------
    ("电锯人", [
        ("higashiyama_kobeni", "东山小红", "黑色短发", "红色眼睛", "黑色西装", "娇小", "贫乳"),
        ("nayuta_(chainsaw_man)", "那由多", "黑色长发", "红色眼睛", "白色衬衫，黑色短裙", "娇小", "贫乳"),
    ]),

    # ------------------------------ 葬送的芙莉莲 ------------------------------
    ("葬送的芙莉莲", [
        ("ubel", "尤贝尔", "紫色长发", "紫色眼睛", "黑紫色魔法使长袍", "标准", "标准"),
        ("serie_(sousou_no_frieren)", "赛莉耶", "白色长发", "金色眼睛", "白色长袍", "高挑", "巨乳"),
    ]),

    # ------------------------------ 赛马娘 ------------------------------
    ("赛马娘", [
        ("special_week", "特别周", "棕色长发，马尾", "棕色眼睛", "赛马娘制服，马耳马尾", "标准", "标准"),
        ("silence_suzuka", "无声铃鹿", "橙色长发", "橙色眼睛", "赛马娘制服，马耳马尾", "标准", "标准"),
        ("tokai_teio", "东海帝王", "棕色短发", "棕色眼睛", "赛马娘制服，马耳马尾", "娇小", "贫乳"),
        ("oguri_cap", "小栗帽", "灰白色短发", "灰色眼睛", "赛马娘制服，马耳马尾", "标准", "标准"),
        ("gold_ship", "黄金船", "银灰色长发", "灰色眼睛", "赛马娘制服，马耳马尾", "高挑", "标准"),
    ]),

    # ------------------------------ 间谍过家家 ------------------------------
    ("间谍过家家", [
        ("becky_blackbell", "贝姬·布莱克贝尔", "黑色短发", "蓝色眼睛", "校服，白色衬衫", "娇小", "贫乳"),
    ]),

    # ------------------------------ 吹响！上低音号 ------------------------------
    ("吹响！上低音号", [
        ("oumae_kumiko", "黄前久美子", "棕色长发", "棕色眼睛", "北宇治高中校服", "标准", "标准"),
        ("kousaka_reina", "高坂丽奈", "黑色长发", "紫色眼睛", "北宇治高中校服", "标准", "标准"),
        ("tanaka_asuka", "田中明日香", "黑色长发", "黑色眼睛", "北宇治高中校服", "高挑", "巨乳"),
    ]),
])


def is_cn(text):
    """至少含一个中日韩统一表意文字。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def build():
    """把 CHARS 展开成最终条目列表（并做基本字段检查）。"""
    entries = []
    for work, rows in CHARS.items():
        for row in rows:
            if len(row) != 7:
                raise SystemExit("[错误] %s 下的条目不完整（需 7 项）: %r" % (work, row))
            en, zh, hair, eyes, outfit, body, chest = row
            entries.append({
                "zh": zh,
                "en": en,
                "cat": "角色",
                "sub": work,
                "nsfw": False,
                "app": {
                    "hair": hair,
                    "eyes": eyes,
                    "outfit": outfit,
                    "body": body,
                    "chest": chest,
                },
            })
    return entries


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_app(app_path, tags_chars):
    """校验 1：chars_app.json 覆盖 tags_cn.json 全部角色；外貌五字段齐全、非空、中文。"""
    problems = []
    app = load_json(app_path)
    missing = [c["en"] for c in tags_chars if c["en"] not in app]
    extra = [k for k in app if k not in {c["en"] for c in tags_chars}]
    if missing:
        problems.append("chars_app.json 缺少 %d 个角色：%s" % (len(missing), ", ".join(missing[:10])))
    if extra:
        problems.append("chars_app.json 多出 %d 个未知角色：%s" % (len(extra), ", ".join(extra[:10])))
    for en, item in app.items():
        if not isinstance(item.get("zh"), str) or not item["zh"].strip():
            problems.append("chars_app.json [%s].zh 为空" % en)
        for field in APP_FIELDS:
            val = item.get(field, "")
            if not isinstance(val, str) or not val.strip():
                problems.append("chars_app.json [%s].%s 为空" % (en, field))
            elif not is_cn(val):
                problems.append("chars_app.json [%s].%s 不是中文：%s" % (en, field, val))
        if item.get("body") not in BODY_OK:
            problems.append("chars_app.json [%s].body 取值非法：%s" % (en, item.get("body")))
        if item.get("chest") not in CHEST_OK:
            problems.append("chars_app.json [%s].chest 取值非法：%s" % (en, item.get("chest")))
    return app, problems


def check_extra(extra, tags_chars):
    """校验 2/3：数量、去重、六字段齐全非空中文。"""
    problems = []
    existing = {c["en"] for c in tags_chars}
    seen = set()
    if len(extra) < 100:
        problems.append("chars_extra.json 只有 %d 条，少于 100 条" % len(extra))
    for item in extra:
        en = item["en"]
        if en in seen:
            problems.append("chars_extra.json 内 en 重复：%s" % en)
        seen.add(en)
        if en in existing:
            problems.append("chars_extra.json 与 tags_cn.json 撞车：%s" % en)
        for field in ("en", "cat", "sub"):
            val = item.get(field)
            if not isinstance(val, str) or not val.strip():
                problems.append("chars_extra.json [%s].%s 为空" % (en, field))
        if not isinstance(item.get("zh"), str) or not item["zh"].strip():
            problems.append("chars_extra.json [%s].zh 为空" % en)
        app = item.get("app") or {}
        for field in APP_FIELDS:
            val = app.get(field, "")
            if not isinstance(val, str) or not val.strip():
                problems.append("chars_extra.json [%s].app.%s 为空" % (en, field))
            elif not is_cn(val):
                problems.append("chars_extra.json [%s].app.%s 不是中文：%s" % (en, field, val))
        if app.get("body") not in BODY_OK:
            problems.append("chars_extra.json [%s].app.body 取值非法：%s" % (en, app.get("body")))
        if app.get("chest") not in CHEST_OK:
            problems.append("chars_extra.json [%s].app.chest 取值非法：%s" % (en, app.get("chest")))
        if en != en.lower() or " " in en:
            problems.append("chars_extra.json [%s] 的 en 不是 booru 写法（应小写+下划线）" % en)
    return problems


def main():
    if not os.path.exists(TAGS_PATH):
        raise SystemExit("[错误] 找不到 %s" % TAGS_PATH)
    if not os.path.exists(APP_PATH):
        raise SystemExit("[错误] 找不到 %s（先跑生成 chars_app.json 的步骤）" % APP_PATH)

    tags = load_json(TAGS_PATH)
    tags_chars = [t for t in tags["tags"] if t.get("cat") == "角色"]

    entries = build()
    entries.sort(key=lambda x: (x["sub"], x["en"]))
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print("=" * 62)
    print("已写出 %s" % OUT_PATH)

    app, p1 = check_app(APP_PATH, tags_chars)
    p2 = check_extra(entries, tags_chars)

    print("-" * 62)
    print("[1] chars_app.json 覆盖：%d / %d 个角色%s"
          % (len(app), len(tags_chars), "  OK" if not p1 else "  有 %d 处问题" % len(p1)))
    if p1:
        for p in p1[:20]:
            print("    ! " + p)
    print("[2] chars_extra.json：%d 条（要求 >= 100），其中 en 唯一：%d 个  %s"
          % (len(entries), len({e["en"] for e in entries}), "OK" if len(entries) >= 100 else "不足"))
    bad = [p for p in p2 if "为空" in p or "不是中文" in p or "非法" in p]
    print("[3] 六字段齐全 / 非空 / 中文：%s"
          % ("全部通过" if not bad else "有 %d 处问题" % len(bad)))
    if bad:
        for p in bad[:20]:
            print("    ! " + p)
    print("[4] 各作品角色数量：")
    counts = OrderedDict()
    for e in entries:
        counts[e["sub"]] = counts.get(e["sub"], 0) + 1
    for work, n in counts.items():
        print("    %-22s %2d 个" % (work, n))
    print("-" * 62)
    print("合计新增 %d 个角色，覆盖 %d 部作品" % (len(entries), len(counts)))
    latin = [e["zh"] for e in entries if not is_cn(e["zh"])]
    if latin:
        print("说明：以下中文名字本身是拉丁字母专名，予以保留：%s" % "、".join(latin))

    problems = p1 + p2
    if problems:
        print("\n[失败] 校验未通过，共 %d 处问题" % len(problems))
        sys.exit(1)
    print("[通过] 全部校验通过")
    print("=" * 62)


if __name__ == "__main__":
    main()
