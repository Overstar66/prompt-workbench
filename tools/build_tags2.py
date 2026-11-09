# -*- coding: utf-8 -*-
"""标签库 v2：取消 NSFW 子分类（只用开关过滤）；道具扁平；按画面重要性排序"""
import json, os

T = []
def add(cat, sub, items, nsfw=False):
    for x in items:
        zh, en = (x, x) if isinstance(x, str) else x
        T.append({"zh": zh, "en": en, "cat": cat, "sub": sub, "nsfw": nsfw})

# ============ 角色（按热度排序） ============
add("角色", "动漫", [
    ("初音未来", "hatsune_miku"), ("博丽灵梦", "hakurei_reimu"), ("雾雨魔理沙", "kirisame_marisa"),
    ("逢坂大河", "aisaka_taiga"), ("时崎狂三", "tokisaki_kurumi"), ("雷姆", "rem"),
    ("艾米莉娅", "emilia"), ("亚丝娜", "asuna"), ("御坂美琴", "misaka_mikoto"),
    ("四宫辉夜", "shinomiya_kaguya"), ("藤原千花", "fujiwara_chika"), ("雪之下雪乃", "yukinoshita_yukino"),
    ("中野三玖", "nakano_miku"), ("和泉纱雾", "izumi_sagiri"), ("康娜", "kanna_kamui"),
    ("托尔", "tohru"), ("伊莉雅", "illyasviel_von_einzbern"), ("远坂凛", "tohsaka_rin"),
    ("阿尔托莉雅", "artoria_pendragon"), ("玛修", "mash_kyrielight"), ("贞德", "jeanne_d'arc"),
    ("2B", "2b_(nier)"), ("蒂法", "tifa_lockhart"), ("明日香", "souryuu_asuka_langley"),
    ("绫波丽", "ayanami_rei"), ("鹿目圆", "kaname_madoka"), ("晓美焰", "akemi_homura"),
    ("十六夜咲夜", "izayoi_sakuya"), ("芙兰朵露", "flandre_scarlet"), ("蕾米莉亚", "remilia_scarlet"),
])
add("角色", "游戏", [
    ("阿米娅", "amiya"), ("凯尔希", "kal'tsit"), ("德克萨斯", "texas"), ("能天使", "exusiai"),
    ("斯卡蒂", "skadi"), ("史尔特尔", "surtr"), ("陈", "chen"), ("银灰", "silverash"),
    ("姬子", "himeko"), ("三月七", "march_7th"), ("希儿", "seele"), ("布洛妮娅", "bronya"),
    ("卡芙卡", "kafka"), ("银狼", "silver_wolf"), ("镜流", "jingliu"), ("花火", "sparkle"),
    ("黄泉", "acheron"), ("流萤", "firefly"), ("霞", "kasumi"), ("绫音", "ayane"),
    ("玛丽萝丝", "marie_rose"), ("穗乃果", "honoka"), ("甘雨", "ganyu"), ("胡桃", "hu_tao"),
    ("雷电将军", "raiden_shogun"), ("八重神子", "yae_miko"), ("芙宁娜", "furina"),
])
add("角色", "MOSS原创", [("角色A", "char_a"), ("角色B", "char_b"), ("角色C", "char_c"),
                     ("角色D", "char_d"), ("角色E", "char_e")])

# ============ 外形（越靠前越重要） ============
add("外形", "发色", [
    ("黑发", "black_hair"), ("棕发", "brown_hair"), ("金发", "blonde_hair"), ("银发", "silver_hair"),
    ("白发", "white_hair"), ("红发", "red_hair"), ("蓝发", "blue_hair"), ("粉发", "pink_hair"),
    ("紫发", "purple_hair"), ("绿发", "green_hair"), ("灰发", "grey_hair"), ("双色发", "two-tone_hair"),
])
add("外形", "发型", [
    ("长发", "long_hair"), ("双马尾", "twintails"), ("短发", "short_hair"), ("马尾", "ponytail"),
    ("丸子头", "hair_bun"), ("姬发式", "hime_cut"), ("麻花辫", "braid"), ("卷发", "curly_hair"),
    ("直发", "straight_hair"), ("齐刘海", "blunt_bangs"), ("呆毛", "ahoge"), ("发带", "hairband"),
])
add("外形", "眼睛", [
    ("蓝眼", "blue_eyes"), ("红眼", "red_eyes"), ("绿眼", "green_eyes"), ("金眼", "yellow_eyes"),
    ("紫眼", "purple_eyes"), ("棕眼", "brown_eyes"), ("异色瞳", "heterochromia"),
    ("半闭眼", "half-closed_eyes"), ("闭眼", "closed_eyes"),
])
add("外形", "表情", [
    ("微笑", "smile"), ("害羞", "shy"), ("脸红", "blush"), ("张嘴", "open_mouth"),
    ("坏笑", "evil_smile"), ("惊讶", "surprised"), ("生气", "angry"), ("无表情", "expressionless"),
    # NSFW 相关但归此组，由开关过滤
    ("媚笑", "seductive_smile"), ("喘息", "panting"), ("阿黑颜", "ahegao"),
], nsfw=False)
add("外形", "体型", [
    ("娇小", "petite"), ("纤细", "slender"), ("高挑", "tall"), ("丰满", "voluptuous"),
    ("贫乳", "flat_chest"), ("巨乳", "large_breasts"), ("长腿", "long_legs"),
])
add("外形", "身体", [
    ("白皙皮肤", "pale_skin"), ("裸体", "nude"), ("全裸", "completely_nude"), ("半裸", "topless"),
    ("露出", "exposed"), ("乳房", "breasts"), ("乳头", "nipples"), ("小穴", "pussy"),
    ("大腿", "thighs"), ("屁股", "ass"), ("爱液", "pussy_juice"),
])

# ============ 服装 ============
add("服装", "上装", [("T恤", "t-shirt"), ("衬衫", "shirt"), ("卫衣", "hoodie"), ("针织衫", "sweater"),
                  ("西装外套", "blazer"), ("吊带", "camisole"), ("露脐装", "crop_top")])
add("服装", "下装", [("短裙", "skirt"), ("百褶裙", "pleated_skirt"), ("长裙", "long_skirt"),
                  ("牛仔短裤", "denim_shorts"), ("长裤", "pants"), ("丝袜", "pantyhose"),
                  ("过膝袜", "thighhighs")])
add("服装", "连衣裙", [("连衣裙", "dress"), ("吊带裙", "sundress"), ("晚礼服", "evening_gown"),
                    ("婚纱", "wedding_dress"), ("旗袍", "china_dress"), ("和服", "kimono")])
add("服装", "制服", [("校服", "school_uniform"), ("水手服", "sailor_uniform"), ("女仆装", "maid"),
                  ("护士服", "nurse"), ("军装", "military_uniform"), ("巫女服", "miko"),
                  ("修女服", "nun")])
add("服装", "泳装", [("泳装", "swimsuit"), ("比基尼", "bikini"), ("连体泳衣", "one-piece_swimsuit"),
                  ("死库水", "school_swimsuit")])
add("服装", "配饰", [("眼镜", "glasses"), ("项链", "necklace"), ("耳环", "earrings"), ("帽子", "hat"),
                  ("围巾", "scarf"), ("手套", "gloves"), ("腰带", "belt")])
add("服装", "情趣", [
    ("情趣内衣", "lingerie"), ("蕾丝内衣", "lace_lingerie"), ("透明内衣", "transparent_lingerie"),
    ("反兔女郎", "reverse_playboy_bunny"), ("兔女郎服", "playboy_bunny"), ("裸体围裙", "naked_apron"),
    ("开胸装", "cleavage_cutout"), ("丁字裤", "thong"), ("吊带袜", "garter_belt"),
    ("紧身衣", "bodysuit"), ("乳胶衣", "latex"),
])

# ============ 动作（姿势 + 日常 + 亲密；顺序=画面重要性） ============
add("动作", "姿势", [
    ("站立", "standing"), ("坐在椅子上", "sitting"), ("坐在床边", "sitting_on_bed"),
    ("坐在地上", "sitting_on_ground"), ("跪着", "kneeling"), ("四肢着地", "all_fours"),
    ("爬行", "crawling"), ("仰躺", "lying"), ("侧躺", "on_side"), ("趴着", "on_stomach"),
    ("双腿分开", "spread_legs"), ("M字开腿", "m_legs"),
])
add("动作", "日常", [
    ("拥抱", "hug"), ("牵手", "holding_hands"), ("接吻", "kiss"), ("比心", "heart_hands"),
    ("挥手", "waving"), ("回头看", "looking_back"), ("双手叉腰", "hand_on_hip"),
])
add("动作", "亲密", [
    ("自慰", "masturbation"), ("手指自慰", "fingering_self"), ("手指插入", "fingering"),
    ("口交", "fellatio"), ("乳交", "paizuri"), ("手交", "handjob"), ("舔阴", "cunnilingus"),
    ("骑乘位", "girl_on_top"), ("后背位", "doggy_style"), ("正常位", "missionary"),
    ("69式", "69"), ("中出", "creampie"), ("潮吹", "squinting"), ("足交", "footjob"),
])

# ============ 道具（扁平，不分子类） ============
add("道具", "全部", [
    ("花束", "bouquet"), ("雨伞", "umbrella"), ("书本", "book"), ("相机", "camera"),
    ("手机", "phone"), ("酒杯", "wine_glass"), ("跳蛋", "vibrator"), ("假阳具", "dildo"),
    ("肛塞", "anal_plug"), ("狗尾巴肛塞", "dog_tail_plug"), ("兔子尾巴肛塞", "bunny_tail_plug"),
    ("乳头环", "nipple_rings"), ("阴蒂环", "clitoris_ring"), ("乳夹", "nipple_clamps"),
    ("绳子", "rope"), ("绳索捆绑", "bondage"), ("绳缚", "shibari"), ("项圈", "collar_(bdsm)"),
    ("牵绳", "leash"), ("手铐", "handcuffs"), ("眼罩", "blindfold"), ("狗耳朵", "dog_ears"),
    ("淫纹", "womb_tattoo"), ("触手", "tentacles"),
])

# ============ 场景 ============
add("场景", "室内", [("卧室", "bedroom"), ("床上", "on_bed"), ("浴室", "bathroom"), ("教室", "classroom"),
                  ("办公室", "office"), ("厨房", "kitchen"), ("客厅", "living_room")])
add("场景", "室外", [("街道", "street"), ("公园", "park"), ("海滩", "beach"), ("森林", "forest"),
                  ("学校", "school"), ("神社", "shrine"), ("雨中", "rain"), ("夜晚", "night")])
add("场景", "光线", [("暖黄灯光", "warm_lighting"), ("阳光", "sunlight"), ("逆光", "backlighting"),
                  ("昏暗", "dim_lighting"), ("霓虹灯", "neon_lights")])

# ============ NSFW 标记（由开关过滤，不再单独分类） ============
NSFW_WORDS = ("乳头环", "阴蒂环", "乳夹", "跳蛋", "假阳具", "肛塞", "尾巴肛塞", "绳子", "绳缚", "绑",
              "手铐", "眼罩", "狗耳朵", "淫纹", "触手", "项圈", "牵绳", "情趣", "蕾丝内衣", "透明内衣",
              "反兔女郎", "兔女郎", "裸体围裙", "开胸", "丁字裤", "吊带袜", "紧身衣", "乳胶",
              "自慰", "插入", "口交", "乳交", "手交", "舔阴", "骑乘", "后背位", "正常位", "69", "中出",
              "潮吹", "足交", "阿黑颜", "喘息", "媚笑", "裸体", "全裸", "半裸", "露出", "乳房", "乳头",
              "小穴", "大腿", "屁股", "爱液", "巨乳", "贫乳", "丰满")

for e in T:
    if e["cat"] == "外形" and e["sub"] == "表情":
        pass
    if any(w in e["zh"] for w in NSFW_WORDS):
        e["nsfw"] = True

out, seen = [], set()
for e in T:
    k = (e["cat"], e["zh"])
    if k in seen:
        continue
    seen.add(k)
    out.append(e)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags_cn.json")
json.dump({"version": 2, "order": "按画面重要性排序", "tags": out},
          open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

from collections import Counter
c = Counter((e["cat"], e["sub"]) for e in out)
print("总条目:", len(out), "| NSFW:", sum(1 for e in out if e["nsfw"]))
for k, v in c.items():
    print(" %-3s %-6s %d" % (k[0], k[1], v))
