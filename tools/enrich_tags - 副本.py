# -*- coding: utf-8 -*-
"""enrich_tags.py — 词库治理：
  1) cat=自定义 & sub=图反推 的词重新归类（规则优先，qwen2.5:7b 兜底）
  2) cat=角色 且 app 全空的角色补外貌（qwen2.5:7b，格式校验，宁缺毋滥）
幂等：跑第二次无改动。用法：
  python enrich_tags.py            # 正式跑
  python enrich_tags.py --rules-only   # 只看规则覆盖率（不调用 LLM、不写文件）
  python enrich_tags.py --task 1|2     # 只跑一个任务
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(HERE, "tags_cn.json")
CHARS_APP_PATH = os.path.join(HERE, "chars_app.json")
CACHE_PATH = os.path.join(HERE, "enrich_cache.json")
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"
TAG_BATCH = 25
CHAR_BATCH = 15
FIELDS = ("hair", "eyes", "outfit", "body", "chest")

SUBS = {
    "外形": ["发色", "发型", "眼睛", "表情", "体型", "身体"],
    "服装": ["上装", "下装", "连衣裙", "制服", "泳装", "配饰", "袜鞋", "情趣"],
    "动作": ["姿势", "日常", "单人", "双人互动", "亲密"],
    "道具": ["全部"],
    "场景": ["室内", "室外", "光线", "天气", "时间段", "建筑"],
}
DEFAULT_SUB = {"外形": "身体", "服装": "上装", "动作": "日常", "道具": "全部", "场景": "室外"}

t0 = time.time()
cache = {"tags": {}, "chars": {}, "ver": 1}
if os.path.exists(CACHE_PATH):
    try:
        _c = json.load(open(CACHE_PATH, encoding="utf-8"))
        if isinstance(_c, dict):
            cache.update(_c)
            cache.setdefault("tags", {})
            cache.setdefault("chars", {})
    except Exception as e:
        print("[warn] 缓存读取失败，忽略: %s" % e)


def save_cache():
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, CACHE_PATH)


def tokens(en):
    return [t for t in re.split(r"[^a-z0-9]+", en.lower()) if t]


_WORD_RE_CACHE = {}


def _word_re(w):
    r = _WORD_RE_CACHE.get(w)
    if r is None:
        p = re.escape(w.replace("_", " "))
        r = re.compile(r"(?<![a-z0-9])" + p + r"(?![a-z0-9])")
        _WORD_RE_CACHE[w] = r
    return r


def has_word(tk, words, low=None):
    """tk 是分词集合；同时按「下划线→空格」的短语边界匹配多词短语。"""
    if low is None:
        return any(w in tk for w in words)
    norm = low.replace("_", " ")
    for w in words:
        if w in tk:
            return True
        if w not in tk and _word_re(w).search(norm):
            return True
    return False


def bigrams(en):
    """把 tag 拆成 '前缀词' 集合，用于 on_/with_/holding_ 这类判断。"""
    return set(tokens(en))


# ---------------------------------------------------------------- 规则表
COLORS = {"blonde", "black", "brown", "red", "blue", "green", "pink", "purple", "white",
          "grey", "gray", "silver", "orange", "aqua", "yellow", "multicolored", "colored",
          "gradient", "streaked", "two-tone", "split-color", "blonde", "platinum", "ash",
          "dark", "light", "teal", "violet", "lavender", "turquoise", "rainbow", "dyed"}
HAIRSTYLE = {"hair", "twintails", "twintail", "ponytail", "braid", "braids", "bangs",
             "bob", "pixie", "sidetail", "side", "tail", "bun", "chignon", "curls",
             "curly", "wavy", "straight", "ahoge", "drill", "drills", "hime", "spiked",
             "messy", "updo", "hairdo", "bobcut", "himecut", "pigtails", "pigtail",
             "french", "ringlets", "cornrows", "dreadlocks"}
EYE_WORDS = {"eyes", "eye", "eyelashes", "eyebrows", "eyebrow", "pupils", "pupil",
             "iris", "heterochromia", "tsurime", "tareme", "eyeliner", "wink",
             "half-closed", "closed", "one_eye_closed"}
EXPR_WORDS = {"smile", "smiles", "grin", "smirk", "blush", "expression", "face",
              "mouth", "lips", "lip", "tongue", "teeth", "tooth", "fang", "fangs",
              "crying", "tears", "tear", "sad", "angry", "happy", "surprised", "pout",
              "frown", "laugh", "laughing", "yawn", "yawning", "drool", "sweatdrop",
              "embarrassed", "shy", "smug", "annoyed", "excited", "bored", "scared",
              "disgust", "disgusted", "serious", "worried", "confused", "sleepy",
              "emotionless", "expressionless", "screaming", "moan", "moaning",
              "open_mouth", "closed_mouth", "parted_lips", "symbol", "emoji", "sticker",
              "sticker_on_face", "blush_stickers", "colored", "tongue_out", "anger_vein", "sweat", "tears", "smile", "grin"}
BODYTYPE_WORDS = {"breasts", "breast", "chest", "bust", "hips", "thighs", "waist",
                  "petite", "slender", "slim", "curvy", "voluptuous", "plump", "chubby",
                  "muscular", "muscle", "toned", "athletic", "tall", "short",
                  "flat_chest", "small_breasts", "medium_breasts", "large_breasts",
                  "huge_breasts", "thick_thighs", "wide_hips", "narrow_waist", "abs",
                  "skinny", "wide_shoulders", "broad_shoulders", "fat", "underweight",
                  "overweight", "stocky", "buff", "ripped", "leggy", "hourglass", "skindentation", "flat_chest", "busty", "top_heavy"}
BODY_WORDS = {"skin", "tan", "tanlines", "freckles", "mole", "neck", "throat",
              "collarbone", "shoulders", "shoulder", "armpits", "arms", "arm",
              "elbows", "wrist", "wrists", "hands", "hand", "fingers", "fingernails",
              "nails", "navel", "belly", "tail", "wings", "wing", "horns", "horn",
              "ears", "ear", "pointy", "scales", "tattoo", "tattoos", "scar", "scars",
              "body_hair", "pubic_hair", "nipples", "nipple", "penis", "vagina", "pussy",
              "anus", "ass", "butt", "buttocks", "genitals", "cum", "semen", "sweat",
              "veins", "feet", "toes", "palms", "back", "spine", "ribs", "stomach",
              "groin", "crotch", "clitoris", "urethra", "glans", "testicles", "balls",
              "facepaint", "makeup", "lips", "teeth", "skinned", "armpit", "pectorals", "beard", "claws", "feathers", "barefoot", "public_hair", "body", "facial_mark", "abs"}
ACCESSORY_WORDS = {"hairclip", "hairpins", "hairpin", "hairband", "hair_bow",
                   "hair_ribbon", "hair_ornament", "hair_flower", "hair_tubes",
                   "hair_stick", "hair_accessory", "headwear", "headdress", "headband",
                   "hat", "hats", "cap", "beret", "tiara", "crown", "veil", "eyewear",
                   "glasses", "sunglasses", "eyepatch", "monocle", "mask", "blindfold",
                   "earrings", "earring", "necklace", "choker", "pendant", "bracelet",
                   "bangle", "anklet", "watch", "belt", "sash", "scarf", "muffler",
                   "ribbon", "ribbons", "bow", "bowtie", "brooch", "badge", "jewelry",
                   "gloves", "glove", "ring", "earmuffs", "hijab", "ornament", "frills",
                   "lace", "suspenders", "garter", "collar", "leash", "harness", "headgear", "helmet", "wristband", "tassel", "obi", "thigh_strap", "scrunchie", "gauntlets", "gauntlet", "headphones", "earmuffs", "pendant"}
UNIFORM_WORDS = {"uniform", "uniforms", "serafuku", "sailor", "maid", "nurse", "nun",
                 "miko", "police", "military", "army", "navy", "pilot", "waitress",
                 "bunny", "suit", "tuxedo", "gym", "buruma", "blazer", "hakama",
                 "flight_attendant", "cheerleader", "school", "office_lady", "armor", "breastplate", "robe", "military_uniform"}
SWIM_WORDS = {"swimsuit", "swimsuits", "bikini", "monokini", "tankini", "rash_guard",
              "swim", "swimwear", "pareo", "trunks", "swim_briefs", "beach_wrap",
              "beach_cover-up", "wetsuit"}
SEXY_WORDS = {"lingerie", "bra", "bras", "panties", "underwear", "underpants", "thong",
              "garter", "corset", "babydoll", "chemise", "teddy", "bodystocking",
              "pasties", "leotard", "bodysuit", "latex", "fishnet", "nightwear",
              "crotchless", "open_crotch", "bunny_girl", "micro", "topless", "bottomless", "highleg", "pantyshot", "upskirt", "areola_slip", "areola", "erection", "nude", "naked", "completely_nude", "pasties", "see-through", "transparent", "skimpy", "revealing"}
LEGWEAR_WORDS = {"socks", "sock", "stockings", "stocking", "thighhighs", "thighhigh",
                 "pantyhose", "tights", "legwear", "footwear", "shoes", "shoe", "boots",
                 "boot", "sandals", "sandal", "heels", "heel", "loafers", "sneakers",
                 "slippers", "geta", "zori", "kneehighs", "legwarmers", "fishnets", "mary_janes", "mary_jane", "heels", "boots"}
DRESS_WORDS = {"dress", "dresses", "gown", "kimono", "yukata", "sari", "dirndl",
               "jumpsuit", "romper", "onepiece", "one-piece", "china_dress",
               "pinafore", "apron_dress", "ballgown"}
BOTTOM_WORDS = {"skirt", "skirts", "pants", "jeans", "shorts", "trousers", "leggings",
                "bloomers", "sarong", "hot_pants", "culottes", "capri", "garter_belt", "skirt_lift", "suspenders", "waistband"}
TOP_WORDS = {"shirt", "shirts", "blouse", "sweater", "cardigan", "hoodie", "sweatshirt",
             "parka", "jacket", "blazer", "vest", "tank_top", "camisole", "coat",
             "cloak", "cape", "capelet", "top", "crop_top", "tube_top", "halter",
             "apron", "jersey", "tracksuit", "clothes", "clothing", "costume",
             "outfit", "uniform_top", "sailor_collar", "sleeves", "long_sleeves",
             "short_sleeves", "sleeveless", "turtleneck", "poncho", "hood", "fur",
             "armor", "breastplate", "kimono_top", "robe", "buttons", "buckle", "casual", "formal", "denim", "sleeve", "collar", "necktie", "neckerchief", "sweater_vest", "t-shirt", "tshirt", "fabric", "cloth"}
POSE_WORDS = {"sitting", "standing", "running", "walking", "lying", "kneeling",
              "crouching", "squatting", "pose", "poses", "arm_up", "arms_up",
              "arms_behind_back", "arms_crossed", "legs_crossed", "legs_up",
              "legs_apart", "spread_legs", "bent_over", "leaning", "all_fours",
              "on_back", "on_stomach", "on_side", "tiptoes", "one_leg_up", "knee_up",
              "looking_back", "facing_away", "back_to_viewer", "contortion",
              "hand_up", "hand_on_hip", "hand_on_own", "crossed_legs", "prone",
              "supine", "jumping", "climbing", "upside_down", "splits", "arched_back",
              "head_tilt", "sitting_on", "standing_on", "lying_on",
              "leaning_on", "against_wall", "straddling", "knees_up", "leg_up",
              "legs_together", "legs_crossed", "curled_up", "crawling", "skipping", "bent_over", "knees_up", "index_finger_raised", "hand_on_own", "arms_behind_back", "on_bed", "sitting_on_lap", "straddling", "carrying", "bound", "presenting", "spread", "spread_legs", "legs_apart", "legs_together", "curtsying", "stretching", "tiptoes"}
DAILY_WORDS = {"eating", "drinking", "sleeping", "waking", "reading", "cooking",
               "bathing", "washing", "waving", "bowing", "saluting", "yawning",
               "stretching", "singing", "dancing", "phone", "texting", "riding",
               "driving", "working", "studying", "drawing", "writing", "playing",
               "gaming", "swimming", "showering", "brushing", "combing", "dressing",
               "undressing", "changing", "smoking", "praying", "meditating", "flying",
               "fighting", "training", "laughing", "crying"}
DUO_WORDS = {"hug", "hugs", "embrace", "kissing", "kiss", "handshake", "piggyback",
             "carry", "carrying", "couple", "arm_in_arm", "hugging", "handholding",
             "holding_hands", "lap_pillow", "princess_carry", "shoulder_ride",
             "cheek_kiss", "forehead_kiss", "hug_from_behind", "back_hug", "carried"}
INTIMATE_WORDS = {"sex", "fellatio", "oral", "blowjob", "handjob", "cumshot",
                  "penetration", "vaginal", "anal", "doggystyle", "cowgirl",
                  "missionary", "paizuri", "titfuck", "licking", "groping", "grope",
                  "masturbation", "fingering", "ahegao", "orgasm", "ejaculation",
                  "creampie", "bukkake", "deepthroat", "sucking", "kissing",
                  "intercourse", "coitus", "copulation", "molestation", "groped",
                  "cum_in", "cum_on", "cum_kiss", "cum_covered", "cumdrip", "after_sex",
                  "sex_from_behind", "spitroast", "threesome", "orgy", "rape", "bdsm", "bondage", "sexually_explicit", "explicit", "genitals", "multiple_penises", "presenting"}
SELF_WORDS = {"self", "self_touching", "self_fingering", "selfcest", "masturbating",
              "own", "pulling_own", "rubbing_own", "covering_breasts", "covering_crotch"}
LIGHT_WORDS = {"light", "lights", "lighting", "sunlight", "shadow", "shadows", "glow",
               "neon", "backlight", "backlighting", "silhouette", "rays", "sunbeam",
               "moonlight", "candlelight", "firelight", "dappled", "lens_flare",
               "bloom", "spotlight", "gobo", "caustics", "reflection", "glare",
               "highlights", "rimlight", "rim_lighting", "ambient", "chiaroscuro"}
WEATHER_WORDS = {"rain", "snow", "fog", "mist", "wind", "sunny", "cloudy", "storm",
                 "thunderstorm", "lightning", "hail", "blizzard", "sandstorm",
                 "rainbow", "drizzle", "downpour", "snowfall", "snowing", "raining",
                 "overcast", "humid", "heatwave", "typhoon", "tornado"}
TIME_WORDS = {"day", "daytime", "night", "morning", "evening", "sunset", "sunrise",
              "dusk", "dawn", "noon", "midnight", "afternoon", "golden_hour",
              "blue_hour", "twilight", "nightfall", "daybreak", "starry", "moonlit"}
INDOOR_WORDS = {"indoors", "indoor", "room", "bedroom", "living_room", "kitchen",
                "bathroom", "classroom", "hallway", "stairs", "library", "office",
                "wall", "floor", "ceiling", "window", "door", "curtain", "bed",
                "desk", "sofa", "bathtub", "toilet", "sink", "shower", "dining_room",
                "attic", "basement", "corridor", "elevator", "onsen", "bathhouse",
                "cafe", "restaurant", "bar", "gym", "locker_room", "closet", "couch", "armchair", "wardrobe", "fireplace", "bathtub"}
OUTDOOR_WORDS = {"outdoors", "outdoor", "sky", "cloud", "clouds", "tree", "trees",
                 "forest", "park", "beach", "sea", "ocean", "river", "lake",
                 "mountain", "street", "city", "garden", "field", "grass", "meadow",
                 "desert", "skyline", "horizon", "rooftop", "balcony", "alley",
                 "bridge", "waterfall", "cliff", "shore", "coast", "hill", "valley",
                 "snowfield", "crosswalk", "sidewalk", "campus", "schoolyard",
                 "courtyard", "parking_lot", "helipad", "dock", "pier", "harbor",
                 "swimming_pool", "pool", "onsen_outdoor", "ruins", "moon", "nature", "plant", "cherry_blossoms", "cherry_blossom", "blossoms", "water", "sun", "stars", "star", "constellation", "galaxy", "nebula", "fire", "campfire", "sunlight"}
BUILDING_WORDS = {"building", "house", "home", "temple", "shrine", "castle", "church",
                  "tower", "gate", "mansion", "windmill", "lighthouse", "skyscraper",
                  "cathedral", "palace", "pagoda", "barn", "cabin", "hut", "station",
                  "hospital", "school", "warehouse", "factory", "museum", "hotel"}
PROP_WORDS = {"weapon", "weapons", "sword", "swords", "gun", "guns", "knife", "knives",
              "dagger", "spear", "axe", "hammer", "staff", "wand", "shield", "arrow",
              "arrows", "bag", "backpack", "handbag", "purse", "cup", "mug", "glass",
              "bottle", "book", "books", "flower", "flowers", "food", "cake", "bread",
              "fruit", "umbrella", "ball", "doll", "teddy_bear", "phone", "smartphone",
              "camera", "microphone", "guitar", "piano", "violin", "rope", "chain",
              "whip", "cigarette", "cigar", "pipe", "handgun", "balloon", "gift", "box", "basket",
              "lantern", "candle", "torch", "potion", "scroll", "map", "paper",
              "letter", "towel", "pillow", "blanket", "chair", "table", "sign",
              "signpost", "clock", "mirror", "vase", "teacup", "teapot", "kettle",
              "pan", "pot", "plate", "bowl", "spoon", "fork", "chopsticks", "fan",
              "parasol", "syringe", "pill", "bomb", "robot", "plushie", "stuffed",
              "credit_card", "keys", "key", "wallet", "headphones", "headset", "game_controller",
              "controller", "joycon", "tv", "monitor", "laptop", "computer", "drink",
              "wine", "beer", "sake", "cocktail", "straw", "juice", "milk", "coffee",
              "tea", "donut", "cookie", "candy", "ice_cream", "pizza", "burger",
              "rice", "sushi", "noodle", "ramen", "soup", "egg", "meat", "vegetable", "rose", "petals", "petal", "bell", "jingle_bell", "musical_note", "instrument", "polearm", "rifle", "sheath", "cellphone", "cat", "dog", "bird", "butterfly", "bug", "insect", "fish", "horse", "animal", "pokemon", "creature", "plushie", "stuffed", "vehicle", "ground_vehicle", "motor_vehicle", "sword", "katana", "spear", "bow_(weapon)"}
PROP_PREFIX = {"holding", "hold", "holds", "grabbing", "grab", "pulling", "pull",
               "lifting", "lift", "carrying", "carry", "wielding", "swinging",
               "throwing", "throw", "putting", "placing", "touching", "petting",
               "feeding", "on", "with", "in"}


META_RULES = [
    ("画质", {"watermark", "signature", "artist_name", "twitter_username", "dated",
              "english_text", "traditional_media", "scan", "censored",
              "mosaic_censoring", "pixelated", "jpeg_artifacts", "lowres",
              "highres", "absurdres", "blurry", "blur", "noise", "grain",
              "chromatic_aberration", "text", "commentary", "speech_bubble",
              "english_commentary", "logo", "web_address", "badge", "sticker",
              "character_name", "copyright_name", "convenient_censoring",
              "censored_censoring", "bar_censor", "mosaic"}),
    ("风格", {"comic", "4koma", "doujinshi", "cover", "parody", "meme",
              "crossover", "chibi", "sketch", "lineart", "watercolor",
              "oil_painting", "impressionism", "art_nouveau", "art_deco",
              "ukiyo-e", "pixel_art", "retro", "vintage", "cyberpunk",
              "steampunk", "gothic", "minimalist", "surreal", "abstract",
              "pop_art", "vaporwave", "synthwave", "vector", "ink", "crayon",
              "pastel", "monochrome", "greyscale", "grayscale", "sepia",
              "cosplay", "realistic", "photorealistic", "3d", "anime_style",
              "flat_color", "cel_shading", "shiny", "sparkle", "glowing",
              "official_art", "concept_art", "illustration", "photo",
              "anime_screencap", "blood_splatter", "symbol", "emoji"}),
    ("构图", {"background", "simple_background", "blue_background",
              "pink_background", "yellow_background", "red_background",
              "white_background", "black_background", "green_background",
              "grey_background", "purple_background", "orange_background",
              "two-tone_background", "gradient_background", "transparent_background",
              "detailed_background", "blurry_background", "portrait", "full_body",
              "upper_body", "lower_body", "close-up", "closeup", "wide_shot",
              "long_shot", "medium_shot", "cowboy_shot", "dutch_angle", "symmetry",
              "composition", "centered", "framing", "border", "letterboxed",
              "split_screen", "collage", "multiple_views", "turnaround",
              "reference_sheet", "character_sheet", "1girl", "2girls", "3girls",
              "4girls", "5girls", "6+girls", "1boy", "2boys", "3boys",
              "multiple_girls", "multiple_boys", "1other", "solo", "duo", "group",
              "crowd", "hetero", "yuri", "yaoi", "siblings", "sisters", "twins",
              "family", "couple", "pair", "trio", "quartet", "head_out_of_frame",
              "feet_out_of_frame", "out_of_frame", "partially_offscreen"}),
    ("视角", {"from_above", "from_below", "from_side", "from_behind",
              "front_view", "side_view", "back_view", "dutch_angle", "pov",
              "first-person", "bird's_eye_view", "worm's_eye_view", "aerial_view",
              "overhead", "looking_at_viewer", "looking_away",
              "looking_to_the_side", "facing_viewer", "eye_contact", "viewer"}),
    ("镜头", {"lens", "fisheye", "telephoto", "wide_angle", "macro", "bokeh",
              "depth_of_field", "shallow_depth_of_field", "motion_blur",
              "panning", "zoom_blur", "tilt_shift", "telescope", "zoom"}),
    ("色彩", {"monochrome", "greyscale", "grayscale", "sepia", "gradient",
              "rainbow", "two-tone", "multicolored", "colorful", "neon",
              "warm_colors", "cool_colors", "muted_colors", "saturated",
              "oversaturated", "desaturated", "duotone", "limited_palette",
              "color_balance", "hue", "tint", "shading", "colored"}),
    ("效果", {"particles", "light_particles", "floating_particles", "glitch",
              "vignetting", "bloom", "motion_lines", "speed_lines",
              "impact_lines", "halftone", "screentone", "dot_pattern",
              "cross-hatching", "hatching", "engraving", "emboss",
              "drop_shadow", "ghosting", "trails", "afterimage", "reflection",
              "mirror_image", "still_life", "silhouette", "wind_effect",
              "sparkles", "anger_vein", "sweatdrop", "blush_stickers"}),
]
EXPR_SYMBOLS = {":d", ":o", ":3", ";d", "^_^", ">_<", "^^^", "?", "...", "<3",
                "!", "!!", "!?", "?!", ".", "~", "=", "-", "+", "*", "@", "#",
                ":p", ":<", ":|", "xd", ":q", ":s", "o_o", "-_-", "=_=",
                "composition", "note"}


CLOTHING_ALL = (UNIFORM_WORDS | SWIM_WORDS | SEXY_WORDS | LEGWEAR_WORDS |
                DRESS_WORDS | BOTTOM_WORDS | TOP_WORDS | ACCESSORY_WORDS)
BODY_ALL = BODY_WORDS | BODYTYPE_WORDS
ACTION_VERBS = {"grab", "grabs", "grabbing", "pull", "pulls", "pulling", "lift",
                "lifting", "carry", "carrying", "carried", "hold", "holds",
                "holding", "hands_on", "hand_on", "hand_in", "hands_in",
                "touching", "touch", "petting", "pinch", "pinching", "squeeze",
                "squeezing", "rub", "rubbing", "press", "pressing", "cover",
                "covering", "cupping", "stroke", "stroking", "bite", "biting",
                "lick", "licking", "kiss", "kissing", "hug", "hugging",
                "embrace", "embracing", "riding", "straddling", "suck",
                "sucking", "pull_down", "pulling_down", "lift_up", "lifting_up",
                "insert", "inserting", "penetrate", "penetrating", "spread",
                "spreading", "present", "presenting", "restrained", "bound",
                "bdsm", "wading", "wading_in"}
ANOTHER_WORDS = {"another", "other", "person", "partner", "viewer", "man",
                 "woman", "boy", "girl", "girls", "boys", "people", "someone",
                 "character", "s", "one"}
HAIR_ACC_WORDS = {"clip", "clips", "ornament", "ornaments", "bow", "bows", "shibari", "bondage", "tied", "restrained",
                  "band", "bandana", "pin", "pins", "flower", "flowers", "tube",
                  "tubes", "stick", "sticks", "ribbon", "ribbons", "tie", "ties",
                  "roller", "rollers", "net", "accessory", "accessories", "ring",
                  "rings", "bead", "beads", "bun", "buns"}


def meta_classify(en):
    tk = set(tokens(en))
    low = en.lower()
    for sub, words in META_RULES:
        if has_word(tk, words, low):
            return "自定义", sub
    return None


def cloth_sub(tk, low):
    if has_word(tk, SEXY_WORDS, low):
        return "情趣"
    if has_word(tk, SWIM_WORDS, low):
        return "泳装"
    if has_word(tk, UNIFORM_WORDS, low):
        return "制服"
    if has_word(tk, LEGWEAR_WORDS, low):
        return "袜鞋"
    if has_word(tk, DRESS_WORDS, low) or low.endswith("_dress") or low == "dress":
        return "连衣裙"
    if low.startswith("miniskirt") or low.endswith("_skirt") or has_word(tk, BOTTOM_WORDS, low):
        return "下装"
    if has_word(tk, {"plaid", "striped", "polka_dot", "polka_dots", "floral_print",
                     "animal_print", "jaguar_print", "leopard_print", "zebra_print",
                     "camo", "camouflage", "checkered", "tartan", "paisley",
                     "houndstooth"}, low):
        return "上装"
    if has_word(tk, TOP_WORDS, low) or low.endswith("_shirt") or low.endswith("_jacket"):
        return "上装"
    if has_word(tk, ACCESSORY_WORDS, low):
        return "配饰"
    return None


def content_classify(en):
    tk = set(tokens(en))
    low = en.lower()
    # 0) 背景 / 表情符号
    if "background" in tk:
        return "自定义", "构图"
    if low.strip() in EXPR_SYMBOLS:
        return "外形", "表情"
    # 1) 发色 / 发型 / 发饰
    if "pubic_hair" in low:
        return "外形", "身体"
    hairish = ("hair" in tk or re.search(r"(^|_)hairs?(_|$)", low) is not None)
    if hairish:
        hair_tk = tk - {"hair", "hairs"}
        if hair_tk & HAIR_ACC_WORDS:
            return "服装", "配饰"
        if tk & COLORS or has_word(tk, {"multicolored", "colored", "gradient",
                                        "streaked", "two-tone", "split-color",
                                        "dyed"}, low):
            return "外形", "发色"
        return "外形", "发型"
    # 2) 眼睛
    if low.endswith("_eyes") or low == "eyes" or has_word(tk, EYE_WORDS, low):
        return "外形", "眼睛"
    # 4) 明显的动作动词（手/身体/拿物）
    if has_word(tk, ACTION_VERBS, low):
        if low.startswith("holding_hands") or low == "holding_hand":
            return "动作", "双人互动"
        if tk & {"self", "own"}:
            return "动作", "单人"
        if tk & ANOTHER_WORDS:
            return "动作", "双人互动"
        cs = cloth_sub(tk, low)
        if cs and not (tk & BODY_ALL):
            return "服装", cs
        if tk & BODY_ALL:
            return "动作", "姿势"
        if tk & PROP_WORDS or tokens(en)[0] in PROP_PREFIX:
            return "道具", "全部"
        return "动作", "姿势"
    # 4b) 表情
    if has_word(tk, EXPR_WORDS, low):
        return "外形", "表情"
    # 4c) 强 NSFW 动作
    if tk & {"shibari", "bondage", "bdsm", "tied", "restrained", "fellatio",
             "blowjob", "handjob", "doggystyle", "cowgirl", "missionary",
             "paizuri", "titfuck", "ahegao", "penetration", "vaginal", "anal",
             "creampie", "bukkake", "threesome", "orgy", "deepthroat"}:
        return "动作", "亲密"
    # 5) 服装
    cs = cloth_sub(tk, low)
    if cs:
        return "服装", cs
    # 6) 体型
    if has_word(tk, BODYTYPE_WORDS, low):
        return "外形", "体型"
    # 7) 身体
    if has_word(tk, BODY_WORDS, low):
        return "外形", "身体"
    # 8) 动作
    if has_word(tk, INTIMATE_WORDS, low):
        return "动作", "亲密"
    if has_word(tk, SELF_WORDS, low) or low.startswith("self_"):
        return "动作", "单人"
    if has_word(tk, DUO_WORDS, low):
        return "动作", "双人互动"
    if has_word(tk, POSE_WORDS, low) or low.strip() == "v":
        return "动作", "姿势"
    if has_word(tk, DAILY_WORDS, low):
        return "动作", "日常"
    # 9) 场景
    if has_word(tk, LIGHT_WORDS, low):
        return "场景", "光线"
    if has_word(tk, WEATHER_WORDS, low):
        return "场景", "天气"
    if has_word(tk, TIME_WORDS, low):
        return "场景", "时间段"
    if has_word(tk, BUILDING_WORDS, low):
        return "场景", "建筑"
    if has_word(tk, INDOOR_WORDS, low):
        return "场景", "室内"
    if has_word(tk, OUTDOOR_WORDS, low):
        return "场景", "室外"
    # 10) 道具
    head = tokens(en)
    if has_word(tk, PROP_WORDS, low):
        return "道具", "全部"
    if head and head[0] in PROP_PREFIX:
        return "道具", "全部"
    return None


def rule_classify(en):
    """先按内容分类；内容判不出再看是否是元信息 tag（水印/背景/构图等）。"""
    r = content_classify(en)
    if r:
        return r
    return meta_classify(en)


# ---------------------------------------------------------------- Ollama
def ollama(prompt, timeout=600, retries=3):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": 1500}}).encode("utf-8")
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(OLLAMA, data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")).get("response", "")
        except Exception as e:
            last = e
            time.sleep(2 + i * 3)
    raise RuntimeError("ollama 调用失败: %s" % last)


def parse_json_loose(txt):
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"[\[{].*[\]}]", txt, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def ask_tags(batch):
    """batch: [(en, zh)] -> {en: (cat,sub)}"""
    lines = "\n".join("%d. %s | %s" % (i + 1, en, zh) for i, (en, zh) in enumerate(batch))
    prompt = (
        "你是动漫图片 tag 分类器。把每个英文 tag 归到唯一分类。\n"
        "允许的 cat/sub 组合（sub 必须从对应列表里选）：\n"
        "外形: 发色/发型/眼睛/表情/体型/身体\n"
        "服装: 上装/下装/连衣裙/制服/泳装/配饰/袜鞋/情趣\n"
        "动作: 姿势/日常/单人/双人互动/亲密\n"
        "道具: 全部\n"
        "场景: 室内/室外/光线/天气/时间段/建筑\n"
        "其他: 其他\n"
        "判断要点：\n"
        "- 发色只用于「头发颜色」的 tag（如 blonde_hair），物体/角色类型绝对不能用发色；\n"
        "- 角色类型（如 cat_girl、elf、mecha）、作品名、画质/水印/构图/风格/数量/视角"
        "这类归「其他」；\n"
        "- 衣服鞋袜帽子首饰→服装；身体部位与五官→外形/身体；表情符号→外形/表情；\n"
        "- 手持/放置的物品→道具；环境光线天气时间建筑→场景。\n"
        "只输出 JSON 数组，每项 {\"i\":序号(整数),\"cat\":\"分类\",\"sub\":\"子类\"}，"
        "不要解释，不要漏项。\n"
        "待分类：\n" + lines
    )
    txt = ollama(prompt)
    data = parse_json_loose(txt)
    out = {}
    if isinstance(data, dict):
        data = list(data.values())
    if not isinstance(data, list):
        return out
    for it in data:
        if not isinstance(it, dict):
            continue
        try:
            i = int(it.get("i"))
        except Exception:
            continue
        cat = str(it.get("cat") or "").strip()
        sub = str(it.get("sub") or "").strip()
        if 1 <= i <= len(batch):
            en = batch[i - 1][0]
            if cat in SUBS:
                sub = sub if sub in SUBS[cat] else DEFAULT_SUB[cat]
                # 防幻觉：发色/眼睛必须有对应的词根，否则不算数（留给「其他」）
                tk = set(tokens(en))
                low = en.lower()
                if sub == "发色" and not (tk & COLORS or "hair" in low):
                    continue
                if sub == "眼睛" and not (tk & EYE_WORDS or "eye" in low):
                    continue
                out[en] = (cat, sub)
            elif cat == "其他":
                out[en] = ("其他", "其他")
    return out


# ---------------------------------------------------------------- 角色外貌校验
COLOR_RE = re.compile(r"黑|棕|金|银|白|红|蓝|粉|紫|灰|橙|绿|咖啡|栗|酒红|亚麻|茶|巧克力|"
                      r"青|黄|褐|米|墨|浅|深|琥珀|彩虹|渐变|挑染|双色")
HAIR_STYLE_RE = re.compile(r"长发|短发|中发|卷发|直发|马尾|辫|刘海|丸子头|呆毛|波波头|"
                           r"盘发|散发|披肩|双马尾|单马尾|麻花|螺旋|爆炸|寸头|平头|"
                           r"波浪|大波浪|公主切|发梢")
GARMENT_RE = re.compile(r"服|裙|衣|裤|袜|鞋|帽|手套|披风|围巾|甲|袍|装|领带|领结|泳装|"
                        r"内衣|外套|背心|斗篷|和服|浴衣|旗袍|校服|制服|女仆|巫女|"
                        r"比基尼|丝袜|长靴|短靴|靴|围裙|束腰|腰封|护目镜|眼镜")
BODY_RE = re.compile(r"娇小|纤细|高挑|匀称|丰满|苗条|健壮|微胖|标准|中等|修长|结实|"
                     r"纤瘦|清瘦|矮小|高大|偏瘦|偏胖|匀称|窈窕|魁梧")
CHEST_VALUES = {"贫乳", "微乳", "标准", "中等", "丰满", "巨乳", "爆乳", "平胸", "小胸",
                "大胸", "巨乳", "超巨乳", "无", "胸围不明"}
BAD_CHARS = re.compile(r"[A-Za-z0-9]")


def _clean(s):
    return re.sub(r"\s+", "", str(s or "")).strip("，,。.;；、")


def valid_hair(s):
    s = _clean(s)
    if not s or BAD_CHARS.search(s) or len(s) > 18 or len(s) < 3:
        return ""
    if not re.search(r"发|辫|马尾", s):
        return ""
    if not (COLOR_RE.search(s) or HAIR_STYLE_RE.search(s)):
        return ""
    return s


def valid_eyes(s):
    s = _clean(s)
    if not s or BAD_CHARS.search(s) or len(s) > 14 or len(s) < 2:
        return ""
    if not re.search(r"眼|瞳", s):
        return ""
    if not COLOR_RE.search(s):
        return ""
    return s


def valid_outfit(s):
    s = _clean(s)
    if not s or BAD_CHARS.search(s) or len(s) > 40 or len(s) < 2:
        return ""
    if not GARMENT_RE.search(s):
        return ""
    return s


def valid_body(s):
    s = _clean(s)
    if not s or BAD_CHARS.search(s) or len(s) > 14:
        return ""
    if not BODY_RE.search(s):
        return ""
    return s


def valid_chest(s):
    s = _clean(s)
    if not s or BAD_CHARS.search(s) or len(s) > 6:
        return ""
    for v in ("超巨乳", "巨乳", "爆乳", "贫乳", "微乳", "丰满", "标准", "中等", "平胸",
              "小胸", "大胸"):
        if v in s:
            return v
    if "乳" in s or "胸" in s:
        return ""
    return ""


def ask_chars(batch):
    """batch: [(en, zh)] -> {en: app|None}；None 表示这条被丢弃。"""
    lines = "\n".join("%d. %s | %s" % (i + 1, zh, en) for i, (en, zh) in enumerate(batch))
    prompt = (
        "你是动漫/游戏角色资料库。下面每题给「中文名 | 英文tag」，请写出该角色的外观设定。\n"
        "要求：\n"
        "- hair 写「发色+发型」，例如「金色双马尾」「黑色长直发」；\n"
        "- eyes 写瞳色，例如「蓝色眼睛」「红色瞳孔」；\n"
        "- outfit 写最经典的服装，例如「红白巫女服」「水手服配百褶裙」；\n"
        "- body 写体型，例如「娇小」「高挑纤细」「匀称」；\n"
        "- chest 只能是：贫乳/标准/丰满/巨乳 之一。\n"
        "只写你确实知道的角色。完全不了解的角色，把该角色五个字段全部留空字符串。"
        "不要编造，不要用英文，不要写数字。\n"
        "只输出 JSON 数组，每项 {\"i\":序号(整数),\"hair\":\"\",\"eyes\":\"\","
        "\"outfit\":\"\",\"body\":\"\",\"chest\":\"\"}，不要解释。\n" + lines
    )
    txt = ollama(prompt)
    data = parse_json_loose(txt)
    out = {}
    if isinstance(data, dict):
        data = list(data.values())
    if not isinstance(data, list):
        return out
    for it in data:
        if not isinstance(it, dict):
            continue
        try:
            i = int(it.get("i"))
        except Exception:
            continue
        if not (1 <= i <= len(batch)):
            continue
        en = batch[i - 1][0]
        app = {k: _clean(it.get(k)) for k in FIELDS}
        hair, eyes = valid_hair(app["hair"]), valid_eyes(app["eyes"])
        if not (hair and eyes):
            out[en] = None
            continue
        outfit = valid_outfit(app["outfit"])
        body = valid_body(app["body"])
        chest = valid_chest(app["chest"])
        out[en] = {"hair": hair, "eyes": eyes, "outfit": outfit, "body": body,
                   "chest": chest}
    # 同一批里 3 个以上角色外观完全相同 → 判定为模板化胡编，全部丢弃
    groups = {}
    for en, app in out.items():
        if not app:
            continue
        key = (app["hair"], app["eyes"], app["outfit"])
        groups.setdefault(key, []).append(en)
    for key, ens in groups.items():
        if len(ens) >= 3:
            for en in ens:
                out[en] = None
    return out


# ---------------------------------------------------------------- 主流程
def load_tags():
    return json.load(open(TAGS_PATH, encoding="utf-8"))


def save_tags(doc):
    s = json.dumps(doc, ensure_ascii=False, indent=1)
    s = s.replace("\n", "\r\n")
    tmp = TAGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, TAGS_PATH)


def classify_stats(tags):
    stats = {"rule": {}, "llm": {}, "left": 0}


def main():
    argv = sys.argv[1:]
    rules_only = "--rules-only" in argv
    only_task = None
    if "--task" in argv:
        only_task = argv[argv.index("--task") + 1]

    doc = load_tags()
    tags = doc["tags"]
    changed = 0
    report = {"rule_hits": {}, "llm_hits": {}, "left": 0, "llm_fail": 0}

    # ---------------- 任务 1
    if only_task in (None, "1"):
        cand = [x for x in tags if x.get("cat") == "自定义" and x.get("sub") == "图反推"]
        print("[任务1] 待归类 %d 条" % len(cand))
        todo = []
        for i, x in enumerate(cand, 1):
            r = rule_classify(x.get("en", ""))
            if r:
                x["cat"], x["sub"] = r
                key = "%s/%s" % r
                report["rule_hits"][key] = report["rule_hits"].get(key, 0) + 1
                changed += 1
            else:
                todo.append(x)
            if i % 200 == 0:
                print("  规则进度 %d/%d，已命中 %d，待 LLM %d"
                      % (i, len(cand), sum(report["rule_hits"].values()), len(todo)))
        print("[任务1] 规则命中 %d，剩 %d 走 LLM" % (sum(report["rule_hits"].values()),
                                                len(todo)))
        if rules_only:
            print("[任务1] --rules-only，未匹配示例：")
            for x in todo[:60]:
                print("   ", x["en"], "|", x["zh"])
            return
        # 没跑过 LLM 的才需要请求；缓存里 None 的记为历史失败
        pending = [x for x in todo if x["en"] not in cache["tags"]]
        for i in range(0, len(pending), TAG_BATCH):
            batch = pending[i:i + TAG_BATCH]
            pairs = [(x["en"], x.get("zh", "")) for x in batch]
            got = {}
            try:
                got = ask_tags(pairs)
            except Exception as e:
                print("  [warn] 批次失败: %s" % e)
            miss = [p for p in pairs if p[0] not in got]
            if miss:
                try:
                    got.update(ask_tags(miss))
                except Exception as e:
                    print("  [warn] 重试失败: %s" % e)
            for en, _zh in pairs:
                cache["tags"][en] = list(got[en]) if en in got else None
            save_cache()
            done = i + len(batch)
            if done % 200 < TAG_BATCH:
                print("  LLM 进度 %d/%d（本批命中 %d/%d）"
                      % (done, len(pending), len(got), len(batch)))
        for x in todo:
            v = cache["tags"].get(x["en"])
            if v and v[0] == "其他":
                m = meta_classify(x["en"])
                if m:
                    x["cat"], x["sub"] = m
                    key = "%s/%s" % m
                    report["meta_hits"] = report.get("meta_hits", {})
                    report["meta_hits"][key] = report["meta_hits"].get(key, 0) + 1
                    changed += 1
                else:
                    report.setdefault("other_left", 0)
                    report["other_left"] += 1
                    report["llm_fail"] += 1
                continue
            if v and v[0] in SUBS:
                x["cat"], x["sub"] = v[0], v[1] if v[1] in SUBS[v[0]] else DEFAULT_SUB[v[0]]
                key = "%s/%s" % (x["cat"], x["sub"])
                report["llm_hits"][key] = report["llm_hits"].get(key, 0) + 1
                changed += 1
            else:
                report["llm_fail"] += 1
        report["left"] = report["llm_fail"]
        all_hits = sum(report["rule_hits"].values()) + sum(report["llm_hits"].values())
        print("[任务1] 规则/LLM 共归类 %d/%d = %.1f%%，仍未归类 %d"
              % (all_hits, len(cand), 100.0 * all_hits / max(1, len(cand)),
                 report["llm_fail"]))

    # ---------------- 任务 2
    if only_task in (None, "2"):
        try:
            chars_app = json.load(open(CHARS_APP_PATH, encoding="utf-8"))
        except Exception:
            chars_app = {}
        def all_empty(a):
            if not isinstance(a, dict):
                return True
            return not any(str(a.get(k) or "").strip() for k in FIELDS)
        app_names = set(chars_app.keys())
        app_zh = {str(v.get("zh") or "").strip() for v in chars_app.values()
                  if isinstance(v, dict)}
        cand = [x for x in tags if x.get("cat") == "角色" and all_empty(x.get("app"))]
        skip_names = [x for x in cand if x.get("en") in app_names
                      or str(x.get("zh") or "").strip() in app_zh]
        todo = [x for x in cand if not (x.get("en") in app_names
                                        or str(x.get("zh") or "").strip() in app_zh)]
        print("[任务2] 角色 app 全空 %d 条，chars_app 已有 %d 条跳过，待补 %d"
              % (len(cand), len(skip_names), len(todo)))
        ok = fail = 0
        pending = [x for x in todo if x["en"] not in cache["chars"]]
        print("[任务2] 其中缓存已判定 %d 条" % (len(todo) - len(pending)))
        for i in range(0, len(pending), CHAR_BATCH):
            batch = pending[i:i + CHAR_BATCH]
            pairs = [(x["en"], x.get("zh", "")) for x in batch]
            got = {}
            try:
                got = ask_chars(pairs)
            except Exception as e:
                print("  [warn] 批次失败: %s" % e)
            for en, _zh in pairs:
                cache["chars"][en] = got.get(en)
            save_cache()
            done = i + len(batch)
            if done % 200 < CHAR_BATCH or done == len(pending):
                print("  进度 %d/%d，已接受 %d，丢弃 %d"
                      % (done, len(pending),
                         sum(1 for v in cache["chars"].values() if v),
                         sum(1 for v in cache["chars"].values() if v is None)))
        for x in todo:
            app = cache["chars"].get(x["en"])
            if app:
                x["app"] = {k: app.get(k, "") for k in FIELDS}
                ok += 1
                changed += 1
            else:
                fail += 1
        print("[任务2] 成功补齐 %d，失败/丢弃 %d（保持空），chars_app 跳过 %d"
              % (ok, fail, len(skip_names)))
        report["char_ok"], report["char_fail"] = ok, fail
        report["char_skip"] = len(skip_names)

    # ---------------- 写盘
    if changed:
        bak = os.path.join(HERE, "tags_cn.backup_enrich_%s.json"
                           % datetime.now().strftime("%Y%m%d_%H%M%S"))
        if not os.path.exists(bak):
            shutil.copy2(TAGS_PATH, bak)
            print("[备份] %s" % os.path.basename(bak))
        save_tags(doc)
        print("[写盘] 变更 %d 条 -> tags_cn.json" % changed)
    else:
        print("[写盘] 无改动")

    # ---------------- 汇总
    import collections
    cats = collections.Counter(x.get("cat") for x in tags)
    print("\n=== 汇总 ===")
    print("总条目 %d" % len(tags))
    for c, n in cats.most_common():
        print("  %-6s %d" % (c, n))
    print("规则命中:", json.dumps(report["rule_hits"], ensure_ascii=False))
    print("LLM命中:", json.dumps(report["llm_hits"], ensure_ascii=False))
    if report.get("meta_hits"):
        print("元信息归位:", json.dumps(report["meta_hits"], ensure_ascii=False))
    print("仍未归类:", report.get("left", 0))
    if "char_ok" in report:
        print("角色补齐 成功/失败/跳过: %d/%d/%d"
              % (report["char_ok"], report["char_fail"], report["char_skip"]))
    print("耗时 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
