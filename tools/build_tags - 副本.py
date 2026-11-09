# -*- coding: utf-8 -*-
"""构建一套汉化完整的标签库 v1：角色（游戏/动漫/MOSS）+ 外形合并 + 服装/姿势/道具/场景/身体 + NSFW 标记"""
import json, os

T = []          # 全部条目
def add(cat, sub, items, nsfw=False):
    for x in items:
        if isinstance(x, str):
            zh, en = x, x
        else:
            zh, en = x
        T.append({"zh": zh, "en": en, "cat": cat, "sub": sub, "nsfw": nsfw})

# ================= 角色 · 游戏 =================
add("角色", "明日方舟", [
    ("阿米娅", "amiya"), ("凯尔希", "kal'tsit"), ("陈", "chen"), ("德克萨斯", "texas"),
    ("能天使", "exusiai"), ("银灰", "silverash"), ("斯卡蒂", "skadi"), ("浊心斯卡蒂", "skadi_the_corrupting_heart"),
    ("史尔特尔", "surtr"), ("夜莺", "nightingale"), ("闪灵", "shining"), ("星熊", "hoshiguma"),
    ("塞雷娅", "saria"), ("白金", "platinum"), ("蓝毒", "blue_poison"), ("砾", "gravel"),
    ("红", "red"), ("初雪", "pramanix"), ("艾雅法拉", "eyjafjalla"), ("莫斯提马", "mostima"),
    ("早露", "rosa"), ("歌蕾蒂娅", "gladiia"), ("温蒂", "weedy"), ("麦哲伦", "magallan"),
    ("号角", "horn"), ("菲亚梅塔", "fiammetta"), ("令", "ling"), ("泥岩", "mudrock"),
    ("森蚺", "eunectes"), ("瑕光", "blemishine"), ("迷迭香", "rosmontis"), ("焰尾", "flametail"),
])
add("角色", "崩坏星穹铁道", [
    ("姬子", "himeko"), ("三月七", "march_7th"), ("布洛妮娅", "bronya"), ("希儿", "seele"),
    ("克拉拉", "clara"), ("银狼", "silver_wolf"), ("卡芙卡", "kafka"), ("佩拉", "pela"),
    ("停云", "tingyun"), ("白露", "bailu"), ("素裳", "sushang"), ("娜塔莎", "natasha"),
    ("希露瓦", "serval"), ("虎克", "hook"), ("艾丝妲", "asta"), ("黑塔", "herta"),
    ("镜流", "jingliu"), ("符玄", "fu_xuan"), ("玲可", "lynx"), ("托帕", "topaz"),
    ("桂乃芬", "guinaifen"), ("藿藿", "huohuo"), ("花火", "sparkle"), ("阮梅", "ruan_mei"),
    ("黑天鹅", "black_swan"), ("黄泉", "acheron"), ("流萤", "firefly"), ("知更鸟", "robin"),
    ("翡翠", "jade"), ("云璃", "yunli"), ("飞霄", "feixiao"),
])
add("角色", "死或生", [
    ("霞", "kasumi"), ("绫音", "ayane"), ("玛丽萝丝", "marie_rose"), ("穗乃果", "honoka"),
    ("心", "kokoro"), ("蒂娜", "tina"), ("雷芳", "lei_fang"), ("瞳", "hitomi"),
    ("克里斯蒂", "christie"), ("海莲娜", "helena"), ("丽莎", "lisa"), ("红叶", "momiji"),
])
add("角色", "原神", [
    ("甘雨", "ganyu"), ("刻晴", "keqing"), ("胡桃", "hu_tao"), ("雷电将军", "raiden_shogun"),
    ("八重神子", "yae_miko"), ("纳西妲", "nahida"), ("芙宁娜", "furina"), ("申鹤", "shenhe"),
    ("夜兰", "yelan"), ("神里绫华", "kamisato_ayaka"), ("优菈", "eula"), ("妮露", "nilou"),
])
add("角色", "胜利女神NIKKE", [
    ("拉毗", "rapi"), ("阿妮斯", "anis"), ("玛丽安", "marian"), ("爱丽丝", "alice"),
    ("红莲", "red_hood"), ("桃乐丝", "dorothy"), ("布兰克", "blanc"), ("诺瓦尔", "noir"),
])

# ================= 角色 · 动漫 =================
add("角色", "动漫", [
    ("初音未来", "hatsune_miku"), ("镜音铃", "kagamine_rin"), ("巡音流歌", "megurine_luka"),
    ("逢坂大河", "aisaka_taiga"), ("逢坂大河", "aisaka_taiga"),
    ("博丽灵梦", "hakurei_reimu"), ("雾雨魔理沙", "kirisame_marisa"), ("十六夜咲夜", "izayoi_sakuya"),
    ("芙兰朵露", "flandre_scarlet"), ("蕾米莉亚", "remilia_scarlet"),
    ("时崎狂三", "tokisaki_kurumi"), ("五河琴里", "itsuka_kotori"), ("夜刀神十香", "yatogami_tohka"),
    ("雷姆", "rem"), ("拉姆", "ram"), ("艾米莉娅", "emilia"),
    ("亚丝娜", "asuna"), ("诗乃", "sinon"), ("莉法", "leafa"),
    ("御坂美琴", "misaka_mikoto"), ("白井黑子", "shirai_kuroko"), ("食蜂操祈", "shokuhou_misaki"),
    ("四宫辉夜", "shinomiya_kaguya"), ("藤原千花", "fujiwara_chika"), ("白银圭", "shirogane_kei"),
    ("雪之下雪乃", "yukinoshita_yukino"), ("由比滨结衣", "yuigahama_yui"),
    ("中野三玖", "nakano_miku"), ("中野二乃", "nakano_nino"), ("中野五月", "nakano_itsuki"),
    ("和泉纱雾", "izumi_sagiri"), ("高木同学", "takagi_san"), ("小埋", "umaru"),
    ("康娜", "kanna_kamui"), ("托尔", "tohru"), ("露科亚", "lucoa"),
    ("伊莉雅", "illyasviel_von_einzbern"), ("远坂凛", "tohsaka_rin"), ("间桐樱", "matou_sakura"),
    ("阿尔托莉雅", "artoria_pendragon"), ("尼禄", "nero_claudius"), ("玉藻前", "tamamo_no_mae"),
    ("斯卡哈", "scathach"), ("玛修", "mash_kyrielight"), ("贞德", "jeanne_d'arc"),
    ("阿比盖尔", "abigail_williams"), ("迦摩", "kama"), ("杀生院祈荒", "sessyoin_kiara"),
    ("2B", "2b_(nier)"), ("蒂法", "tifa_lockhart"), ("爱丽丝", "aerith_gainsborough"),
    ("明日香", "souryuu_asuka_langley"), ("绫波丽", "ayanami_rei"),
    ("灰原哀", "haibara_ai"), ("毛利兰", "mouri_ran"),
    ("鹿目圆", "kaname_madoka"), ("晓美焰", "akemi_homura"),
    ("绪山真寻", "oyama_mahiro"), ("加藤惠", "kato_megumi"),
])

# ================= 角色 · MOSS 原创 =================
add("角色", "MOSS原创", [
    ("角色A", "char_a"), ("角色B", "char_b"), ("角色C", "char_c"),
    ("角色D", "char_d"), ("角色E", "char_e"),
])

# ================= 外形（发型/眼睛/表情合并） =================
add("外形", "发色", [
    ("黑发", "black_hair"), ("棕发", "brown_hair"), ("金发", "blonde_hair"),
    ("银发", "silver_hair"), ("白发", "white_hair"), ("红发", "red_hair"),
    ("蓝发", "blue_hair"), ("绿发", "green_hair"), ("紫发", "purple_hair"),
    ("粉发", "pink_hair"), ("橙发", "orange_hair"), ("灰发", "grey_hair"),
    ("双色发", "two-tone_hair"), ("渐变色发", "gradient_hair"),
])
add("外形", "发型", [
    ("长发", "long_hair"), ("及肩发", "medium_hair"), ("短发", "short_hair"),
    ("双马尾", "twintails"), ("马尾", "ponytail"), ("单侧马尾", "side_ponytail"),
    ("丸子头", "hair_bun"), ("双丸子头", "double_bun"), ("姬发式", "hime_cut"),
    ("齐刘海", "blunt_bangs"), ("空气刘海", "see-through_bangs"), ("中分", "parted_bangs"),
    ("麻花辫", "braid"), ("双麻花辫", "twin_braids"), ("卷发", "curly_hair"),
    ("直发", "straight_hair"), ("呆毛", "ahoge"), ("发带", "hairband"),
])
add("外形", "眼睛", [
    ("蓝眼", "blue_eyes"), ("红眼", "red_eyes"), ("绿眼", "green_eyes"),
    ("金眼", "yellow_eyes"), ("紫眼", "purple_eyes"), ("棕眼", "brown_eyes"),
    ("灰眼", "grey_eyes"), ("异色瞳", "heterochromia"),
    ("吊眼", "tareme"), ("垂眼", "tsurime"), ("半闭眼", "half-closed_eyes"),
    ("眯眼", "narrowed_eyes"), ("闭眼", "closed_eyes"), ("单眼闭", "one_eye_closed"),
])
add("外形", "表情", [
    ("微笑", "smile"), ("大笑", "laughing"), ("坏笑", "evil_smile"),
    ("害羞", "shy"), ("脸红", "blush"), ("张嘴", "open_mouth"),
    ("惊讶", "surprised"), ("生气", "angry"), ("哭泣", "crying"),
    ("无表情", "expressionless"), ("媚笑", "seductive_smile"), ("喘息", "panting"),
])
add("外形", "体型", [
    ("娇小", "petite"), ("高挑", "tall"), ("纤细", "slender"),
    ("丰满", "voluptuous"), ("肌肉", "muscular"), ("贫乳", "flat_chest"),
    ("巨乳", "large_breasts"), ("长腿", "long_legs"),
])

# ================= 服装 =================
add("服装", "上装", [
    ("T恤", "t-shirt"), ("衬衫", "shirt") if False else ("衬衫", "shirt"), ("卫衣", "hoodie"),
    ("针织衫", "sweater"), ("西装外套", "blazer"), ("吊带", "camisole"),
    ("露脐装", "crop_top"), ("比基尼上衣", "bikini_top"),
])
add("服装", "下装", [
    ("短裙", "skirt"), ("百褶裙", "pleated_skirt"), ("长裙", "long_skirt"),
    ("牛仔短裤", "denim_shorts"), ("热裤", "short_shorts"), ("长裤", "pants"),
    ("丝袜", "pantyhose"), ("过膝袜", "thighhighs"), ("短袜", "socks"),
])
add("服装", "连衣裙", [
    ("连衣裙", "dress"), ("吊带裙", "sundress"), ("晚礼服", "evening_gown"),
    ("婚纱", "wedding_dress"), ("旗袍", "china_dress"), ("和服", "kimono"),
])
add("服装", "制服", [
    ("校服", "school_uniform"), ("水手服", "sailor_uniform"), ("女仆装", "maid"),
    ("护士服", "nurse"), ("警服", "police_uniform"), ("军装", "military_uniform"),
    ("巫女服", "miko"), ("修女服", "nun"), ("空姐制服", "flight_attendant"),
])
add("服装", "泳装", [
    ("泳装", "swimsuit"), ("比基尼", "bikini"), ("连体泳衣", "one-piece_swimsuit"),
    ("死库水", "school_swimsuit"),
])
add("服装", "配饰", [
    ("眼镜", "glasses"), ("耳环", "earrings"), ("项链", "necklace"),
    ("发饰", "hair_ornament"), ("帽子", "hat"), ("围巾", "scarf"),
    ("手套", "gloves"), ("项圈", "collar"), ("腰带", "belt"),
])

# ================= 姿势 =================
add("姿势", "站姿", [("站立", "standing"), ("双手叉腰", "hand_on_hip"), ("背手", "arms_behind_back")])
add("姿势", "坐姿", [("坐在椅子上", "sitting"), ("坐在地上", "sitting_on_ground"),
                 ("正坐", "seiza"), ("盘腿坐", "crossed_legs"), ("坐在床边", "sitting_on_bed")])
add("姿势", "躺姿", [("仰躺", "lying"), ("侧躺", "on_side"), ("趴着", "on_stomach"),
                 ("仰面朝天", "on_back")])
add("姿势", "跪姿", [("跪着", "kneeling"), ("四肢着地", "all_fours"), ("爬行", "crawling")])
add("姿势", "腿部", [("双腿分开", "spread_legs"), ("双腿交叉", "crossed_legs"),
                 ("抬起一条腿", "leg_up"), ("M字开腿", "m_legs")])

# ================= 动作 =================
add("动作", "普通", [("拥抱", "hug"), ("牵手", "holding_hands"), ("接吻", "kiss"),
                 ("比心", "heart_hands"), ("挥手", "waving"), ("回头看", "looking_back")])
add("动作", "NSFW", [
    ("自慰", "masturbation"), ("手指自慰", "fingering_self"), ("手指插入", "fingering"),
    ("口交", "fellatio"), ("乳交", "paizuri"), ("手交", "handjob"),
    ("舔阴", "cunnilingus"), ("骑乘位", "girl_on_top"), ("后背位", "doggy_style"),
    ("正常位", "missionary"), ("69式", "69"), ("中出", "creampie"),
    ("潮吹", "squirting"), ("阿黑颜", "ahegao"), ("射精", "ejaculation"),
    ("足交", "footjob"), ("乳首责", "nipple_stimulation"),
], nsfw=True)

# ================= 道具 =================
add("道具", "普通", [("花束", "bouquet"), ("雨伞", "umbrella"), ("书本", "book"),
                 ("相机", "camera"), ("手机", "phone"), ("酒杯", "wine_glass")])
add("道具", "NSFW", [
    ("跳蛋", "vibrator"), ("假阳具", "dildo"), ("肛塞", "anal_plug"),
    ("狗尾巴肛塞", "dog_tail_plug"), ("兔子尾巴肛塞", "bunny_tail_plug"),
    ("乳头环", "nipple_rings"), ("阴蒂环", "clitoris_ring"), ("乳夹", "nipple_clamps"),
    ("绳子", "rope"), ("绳索捆绑", "bondage"), ("绳缚", "shibari"),
    ("项圈", "collar_(bdsm)"), ("牵绳", "leash"), ("手铐", "handcuffs"),
    ("眼罩", "blindfold"), ("口塞", "ball_gag"), ("狗耳朵", "dog_ears"),
    ("触手", "tentacles"), ("淫纹", "womb_tattoo"),
], nsfw=True)

# ================= 场景 =================
add("场景", "室内", [("卧室", "bedroom"), ("床上", "on_bed"), ("浴室", "bathroom"),
                 ("教室", "classroom"), ("办公室", "office"), ("厨房", "kitchen"),
                 ("客厅", "living_room"), ("旅店", "hotel_room")])
add("场景", "室外", [("街道", "street"), ("公园", "park"), ("海滩", "beach"),
                 ("森林", "forest"), ("学校", "school"), ("神社", "shrine"),
                 ("雨中", "rain"), ("夜晚", "night")])
add("场景", "光线", [("暖黄灯光", "warm_lighting"), ("阳光", "sunlight"),
                 ("逆光", "backlighting"), ("昏暗", "dim_lighting"), ("霓虹灯", "neon_lights")])

# ================= 身体 =================
add("身体", "一般", [("裸体", "nude"), ("半裸", "topless"), ("全裸", "completely_nude"),
                 ("露出", "exposed"), ("白皙皮肤", "pale_skin")])
add("身体", "NSFW", [
    ("乳房", "breasts"), ("乳头", "nipples"), ("小穴", "pussy"), ("阴唇", "labia"),
    ("阴蒂", "clitoris"), ("肛门", "anus"), ("大腿", "thighs"), ("屁股", "ass"),
    ("体液", "bodily_fluids"), ("爱液", "pussy_juice"), ("精液", "cum"),
], nsfw=True)

# ================= NSFW 服装 =================
add("服装", "情趣", [
    ("情趣内衣", "lingerie"), ("蕾丝内衣", "lace_lingerie"), ("透明内衣", "transparent_lingerie"),
    ("反兔女郎", "reverse_playboy_bunny"), ("兔女郎服", "playboy_bunny"),
    ("裸体围裙", "naked_apron"), ("露出装", "revealing_outfit"), ("乳环装", "nipple_ring_outfit"),
    ("开胸装", "cleavage_cutout"), ("开裆裤", "open_crotch_panties"), ("丁字裤", "thong"),
    ("吊带袜", "garter_belt"), ("紧身衣", "bodysuit"), ("乳胶衣", "latex"),
], nsfw=True)

# ================= 写文件 =================
seen = set()
out = []
for e in T:
    key = (e["cat"], e["zh"])
    if key in seen:
        continue
    seen.add(key)
    out.append(e)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags_cn.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump({"version": 1, "built": "2026-11-08", "tags": out}, f, ensure_ascii=False, indent=1)

from collections import Counter
c = Counter((e["cat"], e["sub"]) for e in out)
print("总条目:", len(out))
for k, v in c.items():
    print(" %-4s %-8s %d" % (k[0], k[1], v))
nsfw = sum(1 for e in out if e["nsfw"])
print("NSFW 条目:", nsfw)
