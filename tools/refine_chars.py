# -*- coding: utf-8 -*-
"""refine_chars.py — 对 enrich_tags.py 补出来的角色外貌做「第二意见」一致性校验：
同一批角色换一种问法再问一次 qwen2.5:7b，只保留两次一致的 hair/eyes/outfit，
不一致就清空（宁可留空也不要瞎填）。body/chest 保留第一轮（信息量低、风险小）。
用法：python refine_chars.py [--dry-run]
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS_PATH = os.path.join(HERE, "tags_cn.json")
CACHE_PATH = os.path.join(HERE, "enrich_cache.json")
REFINE_CACHE = os.path.join(HERE, "enrich_refine_cache.json")
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:7b"
BATCH = 25

t0 = time.time()
ref = {}
if os.path.exists(REFINE_CACHE):
    try:
        ref = json.load(open(REFINE_CACHE, encoding="utf-8"))
    except Exception:
        ref = {}


def save_ref():
    tmp = REFINE_CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ref, f, ensure_ascii=False)
    os.replace(tmp, REFINE_CACHE)


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
    raise RuntimeError("ollama 失败: %s" % last)


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


def norm(s):
    s = re.sub(r"[\s，,。.;；、]", "", str(s or ""))
    return s


def ask(batch):
    lines = "\n".join("%d. %s | %s" % (i + 1, zh, en) for i, (en, zh) in enumerate(batch))
    prompt = (
        "下面是动漫/游戏角色。请写出你确定知道的「发色+发型」「瞳色」「最经典服装」。\n"
        "只写你确实有把握的，没把握的字段一律留空字符串，绝对不要猜。\n"
        "hair 例：金色双马尾、黑色长直发；eyes 例：蓝色眼睛、红色瞳孔；"
        "outfit 例：红白巫女服、水手服。\n"
        "只输出 JSON 数组，每项 {\"i\":序号(整数),\"hair\":\"\",\"eyes\":\"\",\"outfit\":\"\"}，"
        "不要解释。\n" + lines
    )
    data = parse_json_loose(ollama(prompt))
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
        if 1 <= i <= len(batch):
            out[batch[i - 1][0]] = {k: norm(it.get(k)) for k in ("hair", "eyes", "outfit")}
    return out


def consistent(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if (a in b or b in a) and abs(len(a) - len(b)) <= 3:
        return True
    return False


def main():
    dry = "--dry-run" in sys.argv
    doc = json.load(open(TAGS_PATH, encoding="utf-8"))
    tags = doc["tags"]
    cache = json.load(open(CACHE_PATH, encoding="utf-8"))
    ours = {en for en, v in cache.get("chars", {}).items() if v}
    todo = [x for x in tags if x.get("cat") == "角色" and x.get("en") in ours
            and isinstance(x.get("app"), dict) and x["app"].get("hair")]
    print("[校验] 需要复核 %d 条" % len(todo))
    pending = [x for x in todo if x["en"] not in ref]
    print("[校验] 其中已完成 %d" % (len(todo) - len(pending)))
    for i in range(0, len(pending), BATCH):
        batch = pending[i:i + BATCH]
        pairs = [(x["en"], x.get("zh", "")) for x in batch]
        try:
            got = ask(pairs)
        except Exception as e:
            print("  [warn] 批次失败: %s" % e)
            got = {}
        for en, _zh in pairs:
            ref[en] = got.get(en)
        save_ref()
        done = i + len(batch)
        if done % 200 < BATCH or done == len(pending):
            print("  进度 %d/%d" % (done, len(pending)))

    changed = 0
    kept = {"hair": 0, "eyes": 0, "outfit": 0}
    dropped = {"hair": 0, "eyes": 0, "outfit": 0}
    empty_all = 0
    for x in todo:
        second = ref.get(x["en"])
        if second is None:
            continue
        app = x["app"]
        for k in ("hair", "eyes", "outfit"):
            if consistent(app.get(k), second.get(k)):
                kept[k] += 1
            elif app.get(k):
                app[k] = ""
                dropped[k] += 1
                changed += 1
        if not any(app.get(k) for k in ("hair", "eyes", "outfit", "body", "chest")):
            empty_all += 1
    print("[校验] 保留 hair %d / eyes %d / outfit %d；清空 hair %d / eyes %d / outfit %d"
          % (kept["hair"], kept["eyes"], kept["outfit"],
             dropped["hair"], dropped["eyes"], dropped["outfit"]))
    print("[校验] 清空后完全无外貌 %d 条，变更 %d 条" % (empty_all, changed))
    if dry:
        print("[校验] --dry-run，不写盘")
        return
    if changed:
        bak = os.path.join(HERE, "tags_cn.backup_refine_%s.json"
                           % datetime.now().strftime("%Y%m%d_%H%M%S"))
        if not os.path.exists(bak):
            import shutil
            shutil.copy2(TAGS_PATH, bak)
            print("[备份] %s" % os.path.basename(bak))
        s = json.dumps(doc, ensure_ascii=False, indent=1).replace("\n", "\r\n")
        tmp = TAGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        os.replace(tmp, TAGS_PATH)
        print("[写盘] %d 条变更" % changed)
    else:
        print("[写盘] 无改动")
    print("耗时 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    main()
