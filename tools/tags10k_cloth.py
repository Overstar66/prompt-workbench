# -*- coding: utf-8 -*-
"""服装类候选池：ITEMS = [(sub, nsfw, zh, en), ...]"""

ITEMS = []


def add(sub, nsfw, pairs):
    for zh, en in pairs:
        ITEMS.append((sub, bool(nsfw), zh, en))


COLORS = [
    ("黑色", "black"), ("白色", "white"), ("红色", "red"), ("粉色", "pink"),
    ("紫色", "purple"), ("蓝色", "blue"), ("浅蓝色", "light_blue"), ("深蓝色", "navy"),
    ("绿色", "green"), ("黄色", "yellow"), ("橙色", "orange"), ("棕色", "brown"),
    ("灰色", "grey"), ("金色", "gold"), ("银色", "silver"), ("酒红色", "wine_red"),
]


def colorize(sub, nsfw, items, colors=None):
    for cz, ce in (colors or COLORS):
        for iz, ie in items:
            ITEMS.append((sub, bool(nsfw), cz + iz, "%s_%s" % (ce, ie)))


# =====================================================================
# 上装
# =====================================================================
add("上装", False, [
    ("露肩毛衣", "off_shoulder_sweater"), ("高领毛衣", "turtleneck_sweater"),
    ("针织开衫", "knit_cardigan_deep"), ("长款开衫", "long_cardigan"),
    ("短款卫衣", "cropped_hoodie_deep"), ("连帽卫衣", "hooded_sweatshirt"),
    ("拉链卫衣", "zip_up_sweatshirt"), ("棒球服", "varsity_jacket_deep"),
    ("工装外套", "work_jacket_deep"), ("飞行夹克", "bomber_jacket_deep"),
    ("长风衣", "long_trench_coat"), ("短风衣", "short_trench_coat"),
    ("双排扣大衣", "double_breasted_coat"), ("牛角扣大衣", "duffle_coat_deep"),
    ("羽绒背心", "down_vest"), ("棉马甲", "padded_vest"),
    ("冲锋衣", "outdoor_shell_jacket"), ("防晒衣", "sun_protection_jacket"),
    ("雨衣", "raincoat_deep"), ("披风", "capelet"),
    ("罩衫", "smock_top"), ("雪纺衫", "chiffon_top"),
    ("娃娃衫", "babydoll_top"), ("荷叶边上衣", "ruffled_blouse"),
    ("泡泡袖上衣", "puff_sleeve_top"), ("灯笼袖上衣", "lantern_sleeve_top"),
    ("露背上衣", "backless_top"), ("挂脖上衣", "halter_neck_top"),
    ("一字肩上衣", "off_shoulder_top"), ("抹胸上衣", "strapless_top_deep"),
    ("露脐上衣", "midriff_top"), ("短款上衣", "cropped_top_deep"),
    ("长款上衣", "longline_top"), ("紧身上衣", "tight_top"),
    ("宽松上衣", "loose_top"), ("条纹上衣", "striped_top"),
    ("格子上衣", "plaid_top"), ("波点上衣", "polka_dot_top"),
    ("印花上衣", "printed_top"), ("纯色上衣", "solid_color_top"),
    ("蕾丝上衣", "lace_top_deep"), ("网纱上衣", "mesh_top_deep"),
    ("透视上衣", "sheer_top_deep"), ("针织背心", "knit_vest_deep"),
    ("毛线背心", "wool_vest"), ("羽绒服", "down_jacket"),
    ("派克大衣", "parka_coat"), ("工装衬衫", "work_shirt"),
    ("牛仔衬衫", "denim_shirt_deep"), ("法兰绒衬衫", "flannel_shirt_deep"),
    ("亨利衫", "henley_shirt"), ("水手领上衣", "sailor_collar_top"),
    ("体操服上衣", "gym_uniform_top"), ("短袖开衫", "short_sleeve_cardigan"),
    ("长袖开衫", "long_sleeve_cardigan"), ("系带上衣", "tie_front_top"),
    ("蝴蝶结衬衫", "bow_blouse"), ("立领上衣", "mandarin_collar_top"),
    ("背心裙", "pinafore_top"), ("吊带露背", "backless_camisole"),
    ("露肩卫衣", "off_shoulder_hoodie"), ("高领打底衫", "turtleneck_undershirt"),
])
colorize("上装", False, [
    ("T恤", "t_shirt"), ("衬衫", "shirt"), ("毛衣", "sweater"),
    ("卫衣", "sweatshirt"), ("夹克", "jacket"), ("吊带背心", "camisole"),
    ("背心", "tank_top"), ("外套", "coat"), ("针织衫", "knit_top"),
    ("女式衬衫", "blouse"),
])

# =====================================================================
# 下装
# =====================================================================
add("下装", False, [
    ("百褶短裙", "pleated_microskirt"), ("长百褶裙", "long_pleated_skirt"),
    ("牛仔短裙", "denim_miniskirt"), ("皮短裙", "leather_miniskirt"),
    ("纱裙", "tulle_skirt_deep"), ("蓬蓬裙", "puffy_skirt"),
    ("鱼尾裙", "mermaid_skirt"), ("包臀裙", "bodycon_skirt"),
    ("开叉裙", "slit_skirt"), ("不规则裙", "asymmetrical_skirt_deep"),
    ("高腰裙", "high_waisted_skirt"), ("低腰裙", "low_rise_skirt"),
    ("工装裙", "cargo_skirt_deep"), ("牛仔阔腿裤", "denim_wide_leg_pants"),
    ("西装裤", "suit_pants"), ("哈伦裤", "harem_pants"),
    ("直筒裤", "straight_leg_pants"), ("微喇裤", "bootcut_pants"),
    ("铅笔裤", "pencil_pants"), ("打底裤", "leggings_deep"),
    ("九分裤", "cropped_pants"), ("七分裤", "capri_pants_deep"),
    ("五分裤", "bermuda_shorts_deep"), ("运动短裤", "sport_shorts"),
    ("骑行裤", "cycling_shorts"), ("连体裤", "jumpsuit"),
    ("工装短裤", "cargo_shorts_deep"), ("沙滩裤", "beach_shorts_deep"),
    ("睡裤", "pajama_bottoms"), ("灯笼裤", "harem_shorts"),
    ("蓬蓬短裤", "puffy_shorts"), ("皮质短裤", "leather_shorts_deep"),
    ("破洞牛仔裤", "distressed_jeans"), ("补丁牛仔裤", "patched_jeans"),
    ("刺绣牛仔裤", "embroidered_jeans"), ("高腰牛仔裤", "high_waisted_jeans"),
    ("老爹裤", "dad_jeans"), ("阔腿短裤", "wide_leg_shorts"),
    ("安全裤", "safety_shorts"), ("平角内裤", "boyshorts"),
    ("三角内裤", "briefs_panties"), ("低腰内裤", "low_rise_panties_deep"),
    ("高腰内裤", "high_waisted_panties"), ("蕾丝内裤", "lace_panties_deep"),
    ("运动短裤裙", "sports_skort"), ("百褶裙裤", "pleated_skort"),
    ("纱质长裙", "chiffon_maxi_skirt"), ("棉麻长裙", "linen_maxi_skirt"),
    ("针织半身裙", "knit_skirt_deep"), ("皮质长裤", "leather_trousers"),
    ("丝绒长裤", "velvet_pants"), ("灯芯绒裤", "corduroy_pants"),
    ("印花长裤", "printed_pants"), ("条纹长裤", "striped_pants"),
])
colorize("下装", False, [
    ("短裙", "skirt"), ("百褶裙", "pleated_skirt"), ("牛仔裤", "jeans"),
    ("短裤", "shorts"), ("长裤", "pants"), ("半身裙", "midi_skirt"),
    ("热裤", "hot_pants_deep"), ("阔腿裤", "wide_leg_pants_deep"),
])

# =====================================================================
# 连衣裙
# =====================================================================
add("连衣裙", False, [
    ("吊带连衣裙", "slip_dress"), ("无袖连衣裙", "sleeveless_dress"),
    ("长袖连衣裙", "long_sleeve_dress"), ("短袖连衣裙", "short_sleeve_dress"),
    ("高领连衣裙", "turtleneck_dress"), ("V领连衣裙", "v_neck_dress"),
    ("方领连衣裙", "square_neck_dress"), ("圆领连衣裙", "round_neck_dress"),
    ("露背连衣裙", "backless_dress"), ("开叉连衣裙", "slit_dress_deep"),
    ("鱼尾连衣裙", "mermaid_dress"), ("蓬蓬连衣裙", "puffy_dress"),
    ("公主裙", "princess_dress"), ("婚纱", "wedding_gown"),
    ("晚礼服", "evening_gown"), ("小礼服", "cocktail_dress"),
    ("鸡尾酒裙", "cocktail_gown"), ("旗袍裙", "qipao_dress"),
    ("汉服裙", "hanfu_skirt"), ("洛丽塔裙", "lolita_dress"),
    ("哥特裙", "gothic_dress"), ("女仆裙", "maid_dress"),
    ("护士裙", "nurse_dress"), ("水手裙", "sailor_dress"),
    ("针织连衣裙", "knit_dress"), ("毛衣裙", "sweater_dress"),
    ("衬衫裙", "shirt_dress"), ("牛仔裙", "denim_dress"),
    ("碎花裙", "floral_dress"), ("波点裙", "polka_dot_dress"),
    ("条纹裙", "striped_dress"), ("纯色裙", "solid_color_dress"),
    ("蕾丝裙", "lace_dress"), ("纱裙", "tulle_dress"),
    ("缎面裙", "satin_dress"), ("丝绒裙", "velvet_dress"),
    ("天鹅绒裙", "velour_dress"), ("吊带长裙", "slip_maxi_dress"),
    ("吊带短裙", "slip_mini_dress"), ("抹胸裙", "strapless_dress"),
    ("一字肩裙", "off_shoulder_dress"), ("挂脖裙", "halter_dress"),
    ("露肩裙", "shoulder_baring_dress"), ("高腰连衣裙", "high_waisted_dress"),
    ("收腰连衣裙", "waist_cinched_dress"), ("宽松连衣裙", "loose_dress"),
    ("斗篷裙", "cape_dress"), ("披肩裙", "shawl_dress"),
    ("和风连衣裙", "japanese_style_dress"), ("欧式洋装", "european_gown"),
    ("中东风长裙", "caftan_dress"), ("衬衫式长裙", "shirt_maxi_dress"),
])
colorize("连衣裙", False, [
    ("连衣裙", "dress"), ("吊带裙", "slip_dress_deep"), ("长裙", "long_dress"),
    ("礼服", "gown"), ("旗袍", "qipao"), ("洛丽塔裙", "lolita_gown"),
])

# =====================================================================
# 制服
# =====================================================================
add("制服", False, [
    ("夏季水手服", "summer_sailor_uniform"), ("冬季水手服", "winter_sailor_uniform"),
    ("学校制服", "school_uniform_deep"), ("西装校服", "blazer_uniform"),
    ("运动校服", "tracksuit_uniform"), ("女仆制服", "maid_uniform"),
    ("护士制服", "nurse_uniform_deep"), ("白大褂", "white_coat"),
    ("巫女服", "miko_outfit"), ("神官服", "shinto_priest_outfit"),
    ("修女服", "nun_outfit"), ("空姐制服", "flight_attendant_uniform"),
    ("OL套装", "office_lady_suit"), ("职业套装", "business_suit"),
    ("军装", "military_uniform"), ("警察制服", "police_uniform"),
    ("消防服", "firefighter_uniform"), ("厨师服", "chef_uniform"),
    ("咖啡店制服", "cafe_uniform"), ("和服", "kimono"),
    ("浴衣", "yukata"), ("汉服", "hanfu"), ("旗袍", "qipao_uniform"),
    ("哥特洋装", "gothic_lolita_outfit"), ("女警制服", "policewoman_uniform"),
    ("保安制服", "security_uniform"), ("快递制服", "courier_uniform"),
    ("清洁工制服", "janitor_uniform"), ("学生帽", "school_hat"),
    ("领结", "ribbon_tie"), ("领带", "necktie"),
    ("臂章", "armband"), ("胸牌", "name_tag"),
    ("水手领", "sailor_collar_deep"), ("百褶校裙", "school_pleated_skirt"),
    ("体操服", "gym_uniform"), ("布鲁马", "bloomers_uniform"),
    ("运动短裤制服", "gym_shorts_uniform"), ("泳帽", "swim_cap"),
    ("弓道服", "kyudo_uniform"), ("剑道服", "kendo_uniform"),
    ("柔道服", "judo_uniform"), ("空手道服", "karate_gi"),
    ("侍应生制服", "waiter_uniform"), ("酒保制服", "bartender_uniform"),
    ("花店围裙", "florist_apron"), ("女仆围裙", "maid_apron_deep"),
    ("执事服", "butler_outfit"), ("礼宾制服", "concierge_uniform"),
    ("列车员制服", "train_conductor_uniform"), ("机长制服", "pilot_uniform"),
    ("赛车服", "racing_suit"), ("潜水服", "diving_suit"),
    ("防化服", "hazmat_suit"), ("太空服", "space_suit"),
    ("骑士铠甲", "knight_armor"), ("武士铠甲", "samurai_armor"),
    ("忍者服", "ninja_outfit"), ("魔法师袍", "mage_robe"),
    ("祭司服", "priestess_outfit"), ("修女头巾", "nun_veil"),
    ("水手服外套", "sailor_jacket"), ("校服开衫", "school_cardigan"),
    ("校服背心", "school_vest"), ("校服蝴蝶结", "school_ribbon"),
    ("女仆头饰", "maid_headpiece"), ("护士帽", "nurse_cap_deep"),
    ("空姐帽", "flight_attendant_hat"), ("警帽", "police_hat"),
    ("军帽", "military_cap"), ("贝雷帽制服", "beret_uniform"),
])
colorize("制服", False, [
    ("水手服", "sailor_uniform"), ("女仆装", "maid_outfit"),
    ("护士服", "nurse_outfit"), ("西装", "suit"), ("巫女服", "miko_dress"),
], COLORS[:12])

# =====================================================================
# 泳装
# =====================================================================
add("泳装", False, [
    ("三角比基尼", "triangle_bikini"), ("连体泳衣", "one_piece_swimsuit"),
    ("高叉泳衣", "high_cut_swimsuit"), ("竞赛泳衣", "competition_swimsuit"),
    ("分体泳衣", "two_piece_swimsuit"), ("泳裤", "swim_briefs"),
    ("沙滩裙", "beach_cover_up"), ("潜水服", "wetsuit_deep"),
    ("冲浪服", "surf_suit"), ("泳镜", "swim_goggles"),
    ("微比基尼", "micro_bikini"), ("绳结比基尼", "string_bikini"),
    ("绑带比基尼", "strappy_bikini"), ("挂脖比基尼", "halter_bikini"),
    ("抹胸比基尼", "bandeau_bikini"), ("透视泳衣", "sheer_swimsuit"),
    ("学校泳衣", "school_swimsuit"), ("死库水", "sukumizu"),
    ("旧式泳衣", "vintage_swimsuit"), ("高领泳衣", "high_neck_swimsuit"),
    ("长袖泳衣", "long_sleeve_swimsuit"), ("裙式泳衣", "skirted_swimsuit"),
    ("荷叶边泳衣", "ruffled_swimsuit"), ("镂空泳衣", "cutout_swimsuit"),
    ("亮片泳衣", "sequin_swimsuit"), ("印花泳衣", "printed_swimsuit"),
    ("条纹泳衣", "striped_swimsuit"), ("波点泳衣", "polka_dot_swimsuit"),
    ("防晒泳衣", "sun_protection_swimsuit"), ("浮潜服", "snorkel_suit"),
    ("沙滩罩衫", "beach_smock"), ("泳装外搭", "swimsuit_cover_up"),
    ("男孩风泳裤", "boy_swim_trunks"), ("高腰泳裤", "high_waisted_swim_briefs"),
    ("绑带泳裤", "lace_up_swim_briefs"), ("丁字泳裤", "thong_swimwear"),
    ("侧系带泳裤", "side_tie_swim_briefs"), ("泳装裙裤", "swim_skort"),
], )
colorize("泳装", False, [
    ("比基尼", "bikini"), ("连体泳衣", "one_piece_swimsuit_deep"),
    ("泳裤", "swim_trunks"), ("分体泳衣", "two_piece_swimsuit_deep"),
    ("死库水", "sukumizu_deep"),
], COLORS[:14])

# =====================================================================
# 配饰
# =====================================================================
add("配饰", False, [
    ("发饰", "hair_ornament"), ("发卡", "hairpin_deep"), ("发绳", "hair_tie_deep"),
    ("发圈", "hair_scrunchie_deep"), ("发带", "hairband_deep"),
    ("大蝴蝶结", "big_ribbon"), ("头纱", "veil"), ("贝雷帽", "beret"),
    ("草帽", "straw_hat"), ("鸭舌帽", "baseball_cap"), ("毛线帽", "beanie"),
    ("礼帽", "top_hat"), ("猫耳", "cat_ears_accessory"),
    ("兔耳", "bunny_ears"), ("狐狸耳", "fox_ears"),
    ("天使光环", "angel_halo"), ("恶魔角", "demon_horns"),
    ("圆框眼镜", "round_glasses"), ("墨镜", "sunglasses_deep"),
    ("单片眼镜", "monocle_deep"), ("耳钉", "stud_earrings"),
    ("长耳坠", "long_drop_earrings"), ("珍珠项链", "pearl_necklace"),
    ("十字架项链", "cross_necklace"), ("锁骨链", "collarbone_chain"),
    ("手链", "bracelet"), ("手镯", "bangle"), ("戒指", "ring"),
    ("宝石戒指", "gemstone_ring"), ("丝巾", "silk_scarf"),
    ("领结配饰", "bow_tie_accessory"), ("胸针", "brooch"),
    ("腰带", "belt"), ("皮带", "leather_belt"), ("吊带", "suspender_strap"),
    ("臂环", "armlet"), ("腿环", "thigh_ring"), ("脚链", "anklet"),
    ("长手套", "long_gloves"), ("蕾丝手套", "lace_gloves"),
    ("露指手套", "fingerless_gloves"), ("袖套", "sleeves_accessory"),
    ("分离式袖套", "detached_sleeves"), ("披肩", "shawl_deep"),
    ("面纱", "face_veil"), ("口罩", "face_mask"), ("耳罩", "earmuffs_deep"),
    ("发簪", "hair_stick_deep"), ("花冠", "flower_crown"),
    ("皇冠", "crown"), ("王冠", "tiara"), ("发箍", "headband_deep"),
    ("发夹", "hair_clip_deep"), ("围脖", "neck_warmers"),
    ("臂章配饰", "arm_patch"), ("腰链", "waist_chain"),
    ("眼镜链", "glasses_chain"), ("鼻环", "nose_ring_deep"),
    ("唇环", "lip_ring"), ("眉钉", "eyebrow_piercing"),
    ("脐环", "navel_ring"), ("脚环", "ankle_ring"),
    ("耳骨夹", "ear_cuff"), ("耳线", "ear_threader"),
    ("发梳", "hair_comb"), ("簪花", "flower_hairpin"),
    ("蝴蝶结发饰", "ribbon_hair_accessory"), ("星星发卡", "star_hairpin"),
    ("月亮发卡", "moon_hairpin"), ("心形发卡", "heart_hairpin"),
    ("珍珠发夹", "pearl_hairpin"), ("蕾丝发带", "lace_headband"),
    ("水手帽", "sailor_hat"), ("学士帽", "graduation_cap"),
    ("女巫帽", "witch_hat"), ("圣诞帽", "santa_hat"),
    ("派对帽", "party_hat"), ("头巾", "headscarf"),
    ("头绳", "head_cord"), ("护目镜", "goggles_accessory"),
    ("单肩包", "shoulder_bag_deep"), ("斜挎包", "crossbody_bag"),
    ("小方包", "mini_bag"), ("手拿包", "clutch_bag"),
    ("零钱包", "coin_purse"), ("珍珠手包", "pearl_clutch"),
    ("丝带腰带", "ribbon_belt"), ("金属腰链", "metal_waist_chain"),
    ("锁链项链", "chain_necklace"), ("颈圈", "choker_necklace"),
    ("蕾丝颈圈", "lace_choker"), ("缎带颈圈", "ribbon_choker"),
])
colorize("配饰", False, [
    ("发带", "headband"), ("蝴蝶结", "ribbon"), ("围巾", "scarf"),
    ("手套", "gloves"), ("帽子", "hat"), ("耳环", "earrings"),
    ("项链", "necklace"), ("手链", "bracelet_deep"), ("发卡", "hairclip"),
    ("领结", "bowtie"),
], COLORS[:12])

# =====================================================================
# 情趣（全部 NSFW）
# =====================================================================
add("情趣", True, [
    ("蕾丝内衣", "lace_lingerie_deep"), ("半杯文胸", "half_cup_bra"),
    ("无肩带文胸", "strapless_bra"), ("前扣文胸", "front_close_bra"),
    ("聚拢文胸", "push_up_bra"), ("无钢圈文胸", "wireless_bra"),
    ("透明文胸", "transparent_bra"), ("网纱文胸", "mesh_bra"),
    ("缎面文胸", "satin_bra"), ("丝绸文胸", "silk_bra"),
    ("无痕内裤", "seamless_panties"), ("低腰内裤", "low_waist_panties"),
    ("高腰内裤", "high_waist_panties"), ("开裆内裤", "open_crotch_panties_deep"),
    ("绑带内裤", "strappy_panties_deep"), ("珍珠内裤", "pearl_panties"),
    ("丁字裤", "thong_deep"), ("C字裤", "c_string_deep"),
    ("绳带内裤", "string_panty"), ("透明内裤", "transparent_panties"),
    ("网纱内裤", "mesh_panties"), ("蕾丝丁字裤", "lace_thong"),
    ("胸贴", "nipple_cover"), ("乳贴", "nipple_pasty"),
    ("硅胶胸贴", "silicone_nipple_cover"), ("防水胸贴", "waterproof_pasties"),
    ("花瓣胸贴", "petal_pasties"), ("隐形胸罩", "invisible_bra"),
    ("内衣套装", "lingerie_set_deep"), ("蕾丝套装", "lace_lingerie_set"),
    ("丝绸睡衣套装", "silk_pajama_set"), ("两件套内衣", "two_piece_lingerie_set"),
    ("三件套内衣", "three_piece_lingerie_set"), ("新娘内衣套装", "bridal_lingerie_deep"),
    ("吊带袜", "garter_stockings_deep"), ("大腿袜", "thigh_high_stockings"),
    ("过膝袜情趣", "over_knee_stockings"), ("长筒袜情趣", "long_stockings"),
    ("网袜", "fishnet_stockings_deep"), ("渔网袜", "fishnet_tights"),
    ("蕾丝长袜", "lace_stockings"), ("露趾连裤袜", "open_toe_pantyhose"),
    ("开裆连裤袜", "crotchless_pantyhose_deep"), ("无缝连裤袜", "seamless_pantyhose"),
    ("破洞连裤袜", "ripped_pantyhose_deep"), ("撕裂丝袜", "torn_stockings_deep"),
    ("袜带", "garter"), ("吊袜带", "suspender_belt"),
    ("袜圈", "garter_band"), ("大腿环", "thigh_band"),
    ("绳衣", "rope_outfit"), ("束缚绳衣", "bondage_rope_outfit"),
    ("龟甲绳衣", "kikko_rope_outfit"), ("绳裤", "rope_pants"),
    ("乳胶衣", "latex_suit"), ("乳胶连体衣", "latex_bodysuit"),
    ("乳胶裙", "latex_skirt"), ("PVC连体衣", "pvc_bodysuit"),
    ("皮衣情趣", "leather_outfit"), ("皮裤情趣", "leather_pants_outfit"),
    ("皮革胸衣", "leather_bustier"), ("皮革束带", "leather_strap_outfit"),
    ("束胸带", "chest_binder"), ("束腰", "waist_cincher"),
    ("腰封", "corset_waist"), ("塑身衣", "shapewear"),
    ("紧身胸衣", "tight_corset"), ("马甲式束腰", "underbust_corset"),
    ("绑带束腰", "lace_up_corset"), ("金属腰封", "metal_waist_corset"),
    ("睡裙", "nightdress"), ("吊带睡裙", "slip_nightdress"),
    ("透明睡裙", "sheer_nightgown"), ("蕾丝睡裙", "lace_nightgown"),
    ("真丝睡裙", "silk_nightgown"), ("薄纱睡裙", "gauze_nightgown"),
    ("睡袍", "night_robe"), ("晨袍", "morning_robe"),
    ("浴袍", "bathrobe_deep"), ("和服睡袍", "kimono_robe"),
    ("睡衣上衣", "pajama_top_deep"), ("睡衣短裤", "pajama_shorts"),
    ("透视装", "see_through_outfit"), ("薄纱上衣", "sheer_blouse"),
    ("网纱裙", "mesh_skirt"), ("露背装", "backless_outfit"),
    ("露脐装", "midriff_baring_outfit"), ("深V裙", "deep_v_dress"),
    ("高开叉裙", "high_slit_dress"), ("开裆裙", "open_crotch_skirt"),
    ("超短裙情趣", "micro_skirt"), ("露肩装", "off_shoulder_outfit"),
    ("一字肩情趣", "off_shoulder_lingerie"), ("挂脖装", "halter_outfit"),
    ("肚兜", "dudou_deep"), ("抹胸情趣", "strapless_lingerie"),
    ("兔女郎装", "bunny_girl_outfit"), ("反向兔女郎", "reverse_bunny_outfit"),
    ("裸体围裙", "naked_apron_deep"), ("裸体衬衫", "naked_shirt_deep"),
    ("敞开衬衫", "open_shirt_deep"), ("情趣女仆装", "sexy_maid_outfit"),
    ("情趣护士服", "sexy_nurse_outfit"), ("情趣空姐服", "sexy_flight_attendant"),
    ("情趣教师装", "sexy_teacher_outfit"), ("情趣OL装", "sexy_office_lady"),
    ("情趣警服", "sexy_police_outfit"), ("情趣军装", "sexy_military_outfit"),
    ("情趣修女服", "sexy_nun_outfit"), ("情趣巫女服", "sexy_miko_outfit"),
    ("情趣和服", "sexy_kimono"), ("情趣旗袍", "sexy_qipao"),
    ("情趣婚纱", "sexy_wedding_dress"), ("情趣泳装", "sexy_swimsuit"),
    ("项圈情趣", "collar_lingerie"), ("皮革项圈", "leather_collar"),
    ("蕾丝项圈", "lace_collar"), ("金属项圈", "metal_collar"),
    ("颈链情趣", "choker_lingerie"), ("身体链", "body_chain"),
    ("腰链情趣", "waist_chain_lingerie"), ("腿链", "leg_chain"),
    ("脚链情趣", "ankle_chain_lingerie"), ("乳环链", "nipple_chain"),
    ("乳夹链", "nipple_clamp_chain_deep"), ("蕾丝眼罩", "lace_blindfold"),
    ("半脸面具", "half_mask"), ("猫耳发箍", "cat_ear_headband"),
    ("兔耳发箍", "bunny_ear_headband"), ("女仆头饰情趣", "maid_headpiece_lingerie"),
    ("头纱情趣", "veil_lingerie"), ("面纱情趣", "face_veil_lingerie"),
    ("长手套情趣", "long_gloves_lingerie"), ("蕾丝手套情趣", "lace_gloves_lingerie"),
    ("露指手套情趣", "fingerless_gloves_lingerie"), ("手臂套", "arm_sleeves"),
    ("腿套", "leg_sleeves"), ("袜套", "sock_sleeves"),
    ("乳首贴", "nipple_tapes"), ("十字乳贴", "cross_pasties"),
    ("心形乳贴", "heart_pasties"), ("星星乳贴", "star_pasties"),
    ("亮片乳贴", "glitter_pasties"), ("身体彩绘", "body_paint"),
    ("纹身贴", "tattoo_sticker"), ("淫纹贴纸", "womb_tattoo_sticker_deep"),
    ("液体丝袜", "liquid_stockings"), ("人体彩绘", "body_painting"),
    ("荧光涂料", "glow_paint"), ("贞操带情趣", "chastity_belt_lingerie"),
    ("贞操裤", "chastity_panties_deep"), ("吊带连体衣", "suspender_bodysuit"),
    ("高叉连体衣", "high_cut_bodysuit"), ("露背连体衣", "backless_bodysuit"),
    ("透明连体衣", "transparent_bodysuit"), ("开裆连体衣", "open_crotch_bodysuit"),
    ("渔网连体衣", "fishnet_bodysuit_deep"), ("无袖连体衣", "sleeveless_bodysuit"),
    ("紧身衣", "tight_bodysuit"), ("打底连体衣", "base_layer_bodysuit"),
    ("滑落的肩带", "slipped_strap"), ("半脱的胸罩", "bra_half_off"),
    ("挂在手臂的内衣", "bra_on_arm"), ("卷到腰间的裙子", "skirt_at_waist"),
    ("敞开的衬衫", "shirt_hanging_open"), ("滑到腿间的内裤", "panties_slipping_down"),
    ("拉下一半的拉链", "half_open_zipper"), ("解开扣子的胸衣", "unhooked_bustier"),
    ("松开的束腰", "loosened_corset"), ("掉落的浴巾", "dropping_towel"),
    ("半脱的丝袜", "stockings_half_off"), ("撕破的丝袜", "torn_stockings_tear"),
    ("湿透的白衬衫", "wet_white_shirt"), ("透视的湿衣服", "wet_see_through_clothes"),
    ("贴着身体的湿衣", "wet_clothes_clinging"), ("被水浸透的内衣", "soaked_lingerie"),
    ("开胸毛衣", "open_chest_sweater"), ("露背毛衣", "backless_sweater"),
    ("毛线比基尼", "knit_bikini"), ("皮革比基尼", "leather_bikini"),
    ("金属比基尼", "metal_bikini"), ("链子比基尼", "chain_bikini_deep"),
    ("绳结内衣", "knotted_lingerie"), ("绑带内衣", "strappy_lingerie"),
    ("镂空内衣", "cutout_lingerie"), ("开背内衣", "open_back_lingerie"),
    ("无罩杯内衣", "cupless_bra"), ("开胸内衣", "open_bust_lingerie"),
    ("钥匙孔内衣", "keyhole_lingerie"), ("蝴蝶结内衣", "ribbon_lingerie"),
    ("缎带束缚", "ribbon_bondage_wear"), ("丝带缠身", "ribbon_wrapped_body"),
    ("薄纱斗篷", "sheer_cape"), ("蕾丝斗篷", "lace_cape"),
    ("透视睡袍", "sheer_robe"), ("蕾丝罩衫", "lace_cover_up"),
    ("比基尼内裤", "bikini_panties"), ("运动风情趣", "sporty_lingerie"),
    ("水手服情趣", "sailor_lingerie"), ("校服情趣", "school_uniform_lingerie"),
    ("和风情趣", "japanese_style_lingerie"), ("中式肚兜情趣", "chinese_dudou_lingerie"),
    ("肚皮舞腰链", "belly_dance_chain"), ("脚趾环", "toe_ring"),
    ("乳铃", "nipple_bell_lingerie"), ("乳夹装饰", "decorative_nipple_clamps"),
    ("阴蒂链", "clit_chain"), ("阴唇链", "labia_chain"),
    ("珍珠链", "pearl_chain"), ("身体缎带", "body_ribbon"),
])

add("情趣", True, [
    ("开裆睡裙", "open_crotch_nightgown"), ("情趣围裙", "sexy_apron"),
    ("透明旗袍", "transparent_qipao"), ("蕾丝长袍", "lace_gown_robe"),
    ("吊带连裤袜", "suspender_pantyhose_deep"), ("露臀裙", "butt_baring_skirt"),
    ("开背裙", "open_back_skirt"), ("侧开裙", "side_open_skirt"),
    ("绑带裙", "strappy_skirt"), ("破洞丝袜情趣", "ripped_stockings_lingerie"),
    ("开裆睡衣", "open_crotch_pajamas"), ("提臀内裤", "butt_lifting_panties"),
    ("半罩杯内衣", "shelf_bra"), ("交叉绑带内衣", "crisscross_lingerie"),
    ("挂脖内衣", "halter_lingerie"), ("背部全裸内衣", "fully_backless_lingerie"),
    ("丁字连体衣", "thong_bodysuit"), ("珍珠连体衣", "pearl_bodysuit"),
    ("蕾丝连体衣", "lace_bodysuit_deep"), ("网状连体衣", "mesh_bodysuit"),
    ("金属环内衣", "metal_ring_lingerie"), ("乳胶长手套", "latex_long_gloves"),
    ("乳胶长袜", "latex_stockings"), ("皮革短裙", "leather_miniskirt_lingerie"),
    ("铆钉项圈", "studded_collar"), ("链条项圈", "chain_collar"),
    ("锁链乳夹", "chain_nipple_clamps"), ("阴蒂夹链", "clit_clamp_chain"),
    ("阴唇环", "labia_rings"), ("舌环", "tongue_ring"),
    ("身体穿刺", "body_piercing"), ("锁骨链饰", "collarbone_chain_decoration"),
    ("后腰链", "lower_back_chain"), ("大腿链", "thigh_chain"),
    ("胸前链", "chest_chain"), ("腰部绑带", "waist_strap_lingerie"),
    ("腿部绑带", "leg_strap_lingerie"), ("手臂绑带", "arm_strap_lingerie"),
    ("颈部绑带", "neck_strap_lingerie"), ("全身绑带", "full_body_straps"),
    ("交叉胸带", "cross_chest_straps"), ("交叉背带", "cross_back_straps"),
    ("吊带胸衣", "suspender_bustier"), ("无背带胸衣", "backless_bustier"),
    ("前扣连体衣", "front_closure_bodysuit"), ("拉链连体衣", "zip_bodysuit"),
    ("拉链裙", "zip_skirt"), ("拉链内衣", "zip_lingerie"),
    ("开口内衣", "open_cup_lingerie"), ("半开胸衣", "half_open_bustier"),
    ("露乳装", "breast_baring_outfit"), ("露臀裤", "butt_baring_pants"),
    ("开裆短裤", "open_crotch_shorts"), ("开裆裙裤", "open_crotch_skort"),
    ("开裆连衣裙", "open_crotch_dress"), ("透明围裙", "transparent_apron"),
    ("湿身围裙", "wet_apron"), ("泡沫围裙", "foam_apron"),
    ("泡泡浴裙", "bubble_bath_dress"), ("浴巾围身", "towel_wrapped_body"),
    ("被单裹身", "wrapped_in_sheet_lingerie"),
])

# 情趣：颜色变体
core_lingerie = [
    ("蕾丝内衣", "lace_lingerie"), ("蕾丝内裤", "lace_panties"),
    ("丁字裤", "thong"), ("吊带袜", "garter_stockings"),
    ("连裤袜", "pantyhose"), ("长筒袜", "stockings"),
    ("睡裙", "nightdress"), ("睡袍", "night_robe"),
    ("束腰", "waist_cincher"), ("紧身胸衣", "corset"),
    ("连体衣", "bodysuit"), ("乳胶衣", "latex_suit"),
    ("项圈", "collar"), ("胸贴", "pasties"),
    ("开裆裤袜", "crotchless_tights"), ("网袜", "fishnet_stockings"),
]
colorize("情趣", True, core_lingerie)
colorize("情趣", True, core_lingerie, [
    ("浅粉色", "light_pink"), ("玫红色", "rose_red"), ("深红色", "deep_red"),
    ("香槟金", "champagne_gold"), ("玫瑰金", "rose_gold"), ("藏青色", "navy_blue"),
    ("天蓝色", "sky_blue"), ("薄荷绿", "mint_green"), ("藕荷色", "lilac_purple"),
    ("米白色", "cream_white"),
])

# =====================================================================
# 袜鞋
# =====================================================================
add("袜鞋", False, [
    ("过膝袜", "over_knee_socks"), ("大腿袜", "thigh_high_socks"),
    ("长筒袜", "knee_socks"), ("短袜", "ankle_socks_deep"),
    ("船袜", "no_show_socks"), ("堆堆袜", "slouch_socks_deep"),
    ("露趾袜", "open_toe_socks"), ("五趾袜", "toe_socks"),
    ("连裤袜", "pantyhose_deep"), ("开裆连裤袜", "crotchless_pantyhose_wear"),
    ("吊带袜", "suspender_stockings"), ("网袜", "fishnet_wear"),
    ("渔网袜", "fishnet_tights_wear"), ("蕾丝袜", "lace_socks"),
    ("丝袜", "silk_stockings"), ("棉袜", "cotton_socks"),
    ("羊毛袜", "wool_socks"), ("运动袜", "sports_socks"),
    ("白丝", "white_stockings"), ("黑丝", "black_stockings"),
    ("条纹袜", "striped_socks"), ("图案袜", "patterned_socks"),
    ("过膝袜圈", "over_knee_band"), ("袜带", "sock_garter"),
    ("高跟鞋", "high_heels_deep"), ("细高跟", "stiletto_heels"),
    ("粗高跟", "chunky_heels"), ("坡跟鞋", "wedge_heels"),
    ("尖头鞋", "pointed_toe_shoes"), ("圆头鞋", "round_toe_shoes"),
    ("玛丽珍鞋", "mary_jane_shoes"), ("乐福鞋", "loafers"),
    ("牛津鞋", "oxford_shoes"), ("短靴", "ankle_boots"),
    ("长靴", "tall_boots"), ("过膝靴", "over_knee_boots"),
    ("马丁靴", "combat_boots"), ("雪地靴", "snow_boots"),
    ("绑带凉鞋", "strappy_sandals"), ("拖鞋", "slippers_deep"),
    ("运动鞋", "sneakers_deep"), ("帆布鞋", "canvas_shoes"),
    ("老爹鞋", "chunky_sneakers"), ("单鞋", "flat_shoes"),
    ("舞鞋", "dance_shoes"), ("芭蕾鞋", "ballet_flats"),
    ("足袋", "tabi_socks"), ("分趾袜", "split_toe_socks"),
    ("蕾丝过膝袜", "lace_thighhighs"), ("透明丝袜", "sheer_stockings"),
    ("渐变丝袜", "gradient_stockings"), ("亮片丝袜", "sequin_stockings"),
    ("珍珠丝袜", "pearl_stockings"), ("刺绣丝袜", "embroidered_stockings"),
    ("破洞袜", "ripped_socks"), ("羊毛过膝袜", "wool_thighhighs"),
    ("针织袜套", "knit_leg_warmers"), ("毛绒袜", "fluffy_socks"),
    ("兔耳拖鞋", "bunny_slippers"), ("猫爪袜", "cat_paw_socks"),
    ("高跟靴", "high_heel_boots"), ("防水台鞋", "platform_shoes"),
    ("厚底鞋", "platform_sneakers"), ("穆勒鞋", "mules"),
    ("罗马鞋", "gladiator_sandals"), ("绑腿鞋", "lace_up_sandals"),
    ("木屐", "geta_sandals"), ("草履", "zori_sandals"),
    ("雨靴", "rain_boots_deep"), ("工装靴", "work_boots"),
    ("机车靴", "motorcycle_boots"), ("军靴", "military_boots"),
    ("袜套鞋", "sock_shoes"), ("露跟鞋", "slingback_heels"),
    ("珍珠高跟鞋", "pearl_heels"), ("缎面高跟鞋", "satin_heels"),
])
colorize("袜鞋", False, [
    ("过膝袜", "thighhigh"), ("长筒袜", "knee_high"),
    ("连裤袜", "tights"), ("短袜", "ankle_sock"),
    ("高跟鞋", "high_heel"), ("靴子", "boots"),
    ("运动鞋", "sneaker"), ("凉鞋", "sandals"),
], COLORS[:12])

if __name__ == "__main__":
    from collections import Counter
    c = Counter(x[0] for x in ITEMS)
    n = Counter(x[0] for x in ITEMS if x[1])
    print("服装候选:", len(ITEMS))
    for k in c:
        print(" ", k, c[k], "nsfw", n[k])
