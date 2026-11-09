# -*- coding: utf-8 -*-
"""WD14 图反推（本地 ONNX，不依赖 ComfyUI 运行时 / 老工作台数据）

只读两个外部文件：
  - onnx 模型：默认 WD14_MOAT 常量，可用环境变量 `WD14_MODEL` 覆盖
  - 标签表  ：模型同目录下的 `<模型名>.csv`（或 `selected_tags.csv`），可用 `WD14_TAGS` 覆盖

中文映射取项目自己的 tags_cn.json（en → zh）。
"""
import csv
import io
import json
import os
import threading

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_MODEL_DIR = r"D:\Dsh-project\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-WD14-Tagger\models"
WD14_MOAT = os.path.join(DEFAULT_MODEL_DIR, "wd-v1-4-moat-tagger-v2.onnx")

# 分类：0=general 4=character 9=rating
CAT_GENERAL, CAT_CHARACTER = 0, 4
CHAR_THRESHOLD = 0.75          # 角色标签单独用更高阈值，避免误判

_lock = threading.Lock()
_sess = None
_input_name = None
_input_size = None
_tag_names = []
_tag_cats = []
_zh_map = None


def model_path():
    return os.environ.get("WD14_MODEL") or WD14_MOAT


def tags_path(mp=None):
    p = os.environ.get("WD14_TAGS")
    if p:
        return p
    mp = mp or model_path()
    stem = os.path.splitext(mp)[0]
    for cand in (stem + ".csv", os.path.join(os.path.dirname(mp), "selected_tags.csv")):
        if os.path.isfile(cand):
            return cand
    return stem + ".csv"


def _ensure_loaded():
    global _sess, _input_name, _input_size, _tag_names, _tag_cats
    if _sess is not None:
        return
    with _lock:
        if _sess is not None:
            return
        mp = model_path()
        if not os.path.isfile(mp):
            raise RuntimeError("WD14 模型不存在：%s（可设环境变量 WD14_MODEL 覆盖）" % mp)
        tp = tags_path(mp)
        if not os.path.isfile(tp):
            raise RuntimeError("WD14 标签表不存在：%s（可设环境变量 WD14_TAGS 覆盖）" % tp)
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.enable_cpu_mem_arena = False      # 关内存池，跑完还给系统，别和 ComfyUI 抢
        so.intra_op_num_threads = 2
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        sess = ort.InferenceSession(mp, sess_options=so, providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        names, cats = [], []
        with open(tp, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                names.append((row.get("name") or "").strip())
                try:
                    cats.append(int(row.get("category") or 0))
                except ValueError:
                    cats.append(0)
        _input_size = int(inp.shape[1]) if isinstance(inp.shape[1], int) else 448
        _input_name, _sess, _tag_names, _tag_cats = inp.name, sess, names, cats


def _ensure_zh():
    global _zh_map
    if _zh_map is not None:
        return
    with _lock:
        if _zh_map is not None:
            return
        m = {}
        try:
            data = json.load(open(os.path.join(HERE, "tags_cn.json"), encoding="utf-8"))
            for e in (data.get("tags") or []):
                en, zh = e.get("en"), e.get("zh")
                if en and zh:
                    m[en] = zh
        except Exception:
            pass
        _zh_map = m


def _preprocess(data):
    from PIL import Image
    import numpy as np
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    size = _input_size
    ratio = float(size) / max(img.size)
    new_size = (max(1, int(img.size[0] * ratio)), max(1, int(img.size[1] * ratio)))
    img = img.resize(new_size, Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(img, ((size - new_size[0]) // 2, (size - new_size[1]) // 2))
    arr = np.asarray(canvas).astype(np.float32)
    arr = arr[:, :, ::-1]              # RGB -> BGR（该 ONNX 导出要求）
    return np.expand_dims(arr, 0)      # 0-255，模型内部已按此训练，不要 /255


def tag_image(data: bytes, threshold=0.35, max_tags=60, character_threshold=CHAR_THRESHOLD):
    """图片 bytes → [{"en","zh","score"}]，按分数降序、过滤阈值、最多 max_tags 条。"""
    _ensure_loaded()
    probs = _sess.run(None, {_input_name: _preprocess(data)})[0][0]
    hits = []
    for name, cat, p in zip(_tag_names, _tag_cats, probs):
        if not name:
            continue
        p = float(p)
        if cat == CAT_GENERAL and p >= threshold:
            hits.append((name, p))
        elif cat == CAT_CHARACTER and p >= character_threshold:
            hits.append((name, p))
    hits.sort(key=lambda x: -x[1])
    hits = hits[:max(0, int(max_tags))]
    _ensure_zh()
    return [{"en": name, "zh": _zh_map.get(name, ""), "score": round(p, 4)} for name, p in hits]


if __name__ == "__main__":
    import sys
    fp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "styles", "anime_style.jpg")
    with open(fp, "rb") as f:
        res = tag_image(f.read())
    for r in res[:20]:
        print("%.3f  %-40s %s" % (r["score"], r["en"], r["zh"] or "-"))
    print("total:", len(res))
