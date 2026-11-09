# 角色外貌数据（chars_app.json / chars_extra.json）

给标签库补充「角色长什么样」的两份数据。都是纯 JSON，可以直接手改，不需要脚本。
`tags_cn.json`、`build_tags_v3.py`、`预览.html`、`_v*.py` 都属于原有产物，**本目录新增的内容不会改动它们**。

## 文件用途

| 文件 | 用途 |
| --- | --- |
| `chars_app.json` | 给 `tags_cn.json` 里**已有的全部 406 个角色**逐个补外貌。key = 条目的 `en`，用来和原标签一一对应。 |
| `chars_extra.json` | **补充角色包**：`tags_cn.json` 里没有的 107 个动漫/游戏角色，自带外貌，和原库按 `en` 去重、可直接合并使用。 |
| `build_chars_extra.py` | 生成 `chars_extra.json` 的脚本（可重复运行，幂等），末尾带 4 项校验。 |

## 字段含义

`chars_app.json`（展开结构，一人一条）：

```json
"gotoh_hitori": {
  "zh": "后藤一里",
  "hair": "粉色长发，侧马尾",
  "eyes": "蓝色眼睛",
  "outfit": "粉色运动服",
  "body": "娇小",
  "chest": "标准"
}
```

| 字段 | 含义 | 取值 |
| --- | --- | --- |
| `zh` | 中文名，和 `tags_cn.json` 保持一致 | 中文（GUMI / MEIKO / 2B / C.C. 这类专名保留原文） |
| `hair` | 发色 + 发型 | 自由文本，如「黑色长直发，红色发带」 |
| `eyes` | 瞳色（异色瞳、特殊瞳术照实写） | 自由文本，如「左眼红色右眼金色异色瞳」 |
| `outfit` | 常穿的服装 | 自由文本，如「红白巫女服，白色围裙」 |
| `body` | 体型 | `娇小` / `纤细` / `标准` / `高挑` / `丰满`（五选一） |
| `chest` | 胸部 | `贫乳` / `标准` / `巨乳`（三选一） |

`chars_extra.json`（带 `app` 嵌套，其余字段和 `tags_cn.json` 完全同构，方便合并）：

```json
{"zh": "后藤一里", "en": "gotoh_hitori", "cat": "角色", "sub": "孤独摇滚", "nsfw": false,
 "app": {"hair": "粉色长发，侧马尾", "eyes": "蓝色眼睛", "outfit": "粉色运动服",
         "body": "娇小", "chest": "标准"}}
```

和原库的两点差异：
- `sub` 写的是**作品中文名**（`tags_cn.json` 里的 `sub` 只有「动漫 / 游戏 / MOSS原创」这类粗分类）；
- 多一个 `app` 对象装 5 个外貌字段。
- `nsfw` 一律 `false`。

## 如何新增角色

**手写 JSON 就行。** 直接在 `chars_app.json` 里加一个 key（key 用 booru 写法的 `en`），值里写齐六项：

```json
"kita_ikuyo": {
  "zh": "喜多郁代",
  "hair": "红色长发",
  "eyes": "红色眼睛",
  "outfit": "校服，红色外套",
  "body": "标准",
  "chest": "标准"
}
```

往 `chars_extra.json` 里加，就往数组末尾追加一个对象（照上面第二条的结构，`app` 里写全五项）。

如果更习惯用脚本：打开 `build_chars_extra.py`，在 `CHARS` 里对应作品的列表中追加一行七元组
`(en, zh, hair, eyes, outfit, body, chest)`，然后运行：

```bat
D:\Dsh-project\ComfyUI_windows_portable\python_embeded\python.exe build_chars_extra.py
```

它会重写 `chars_extra.json` 并打印校验结果。注意 `chars_extra.json` 是**生成产物**，手改过的内容下次跑脚本会被覆盖——要长期保留请改脚本里的 `CHARS`。

## 脚本末尾的 4 项校验

1. `chars_app.json` 覆盖 `tags_cn.json` 全部 406 个角色（缺一个就 `exit 1`，并列出缺的 en）；
2. `chars_extra.json` 条数 ≥ 100、内部 `en` 无重复、且不与 `tags_cn.json` 撞车；
3. 每个条目的 `hair / eyes / outfit / body / chest` 齐全、非空、是中文，`body` / `chest` 取值在允许集合内，`en` 为小写下划线写法；
4. 打印各作品的角色数量统计。

任一项不过就返回非 0 退出码，便于接到流水线里。

## 现有覆盖

- 外貌覆盖：`tags_cn.json` 的 406 个角色**全部**补齐（0 缺失）。
- 新增角色：**107 个**，覆盖 **29 部作品**。重点作品在「原库已有 + 本包新增」后的总数：
  孤独摇滚 6、轻音少女 6、莉可丽丝 5、更衣人偶坠入爱河 4、五等分的新娘 7、我推的孩子 5、
  我的青春恋爱物语 5、兔女郎学姐 6、无职转生 6、Re:从零开始的异世界生活 9、龙女仆 5、
  辉夜大小姐 8、干物妹小埋 4、埃罗芒阿老师 4、擅长捉弄的高木同学 3、凉宫春日 5、
  Fate/stay night 12、原神 38、崩坏3 15、蔚蓝档案 31、明日方舟 61、胜利女神NIKKE 23。
  另补充：咒术回战、鬼灭之刃、电锯人、葬送的芙莉莲、赛马娘、间谍过家家、吹响！上低音号。
- 外貌按角色真实设定填写；原库里没有的泛用角色（`char_a`~`char_e`）用不指名的通用值。
