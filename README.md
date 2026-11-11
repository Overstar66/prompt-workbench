# 提示词工作台（studio2）

本地运行的动漫插画**提示词工作台**：拖图反推 / 中文扩写 → 拆标签 → 一键生成 MOSS、WAI、Pony 全套正向与负向。

`18000+ 词条` · `2900+ 角色` · `50 画风` · `3 套输出` · `后端纯标准库`

> ⚠️ **18+**：本项目内置成人向（NSFW）词库与判定逻辑，仅限 18 岁以上用户，仅供个人学习与创作。
> 角色名与作品名版权归各自权利人所有，本项目为非官方同人工具，与任何官方无关。

![界面截图](docs/screenshot.png)

## 这是什么

- 面向 Stable Diffusion / Illustrious / Pony 系模型，把「想画什么」变成可直接粘贴的提示词。
- 三种输入：拖一张图（WD14 反推）、写几句中文（AI 扩写）、从词库点选。
- 一次输出 6 个区块：MOSS / WAI / Pony 三套正向，加各自负向。
- 单文件后端 + 浏览器前端，无数据库、无需构建；只有勾选 API 时文字才出本机。
- 适合一个人在本机长期用，不适合多人共享或公网部署。

## 快速开始

需要 Python 3.10 ~ 3.12（推荐 3.12；后端只用标准库）。
3.14 / 3.15 也能启动，但 onnxruntime 目前没有对应安装包，图片反推不可用。
以下 4 步，路径均相对项目根目录。

**1. 获取代码**

```bash
git clone https://github.com/Overstar66/prompt-workbench.git
cd prompt-workbench
```

**2. 安装依赖（可选，只在用图反推时装）**

```bash
pip install onnxruntime pillow numpy
```

只用扩写 / 词库 / 模板的话可以跳过。

**3. 配置（可选）**

```bash
# Windows
copy api_config.example.json api_config.json

# macOS / Linux
cp api_config.example.json api_config.json
```

编辑 `api_config.json`，填 `url` / `model` / `key`。不填也能跑：扩写走本地 Ollama，Ollama 也没有就退回模板。

**4. 启动**

```bash
python app.py
```

Windows 双击 `install.bat` 走安装向导（内部调用 `install.ps1`，装依赖时显示下载进度）。
只想启动的话，双击 `启动工作台.bat`——它会自动探测 pythonw / py / python，找不到会提示安装 Python。

打开 <http://127.0.0.1:8901>。默认端口 **8901**，改 `app.py` 顶部的 `PORT = 8901` 后重启即可，访问地址跟着换。
macOS / Linux 用 `python app.py` 启动，没有 bat 脚本，其余操作一致。

## 两种省事装法

| 方式 | 适合 | 怎么做 |
|---|---|---|
| **Windows 安装向导** | 不想敲命令 | 双击根目录的 install.bat，按提示选轻量版或完整离线版 |
| **让 AI 代装** | 装了 DeepSeek Harness | 把 [docs/DEPLOY_WITH_DSH.md](docs/DEPLOY_WITH_DSH.md) 里那段指令复制给 DSH |

## 三种使用模式

| 模式 | 需要什么 | 适合谁 | 怎么配 |
|---|---|---|---|
| 纯本地 | Python；Ollama 可选 | 离线、不想出网、写成人向内容 | 不填 API Key；扩写走 Ollama，没装则退回模板 |
| 纯 API | 一个 DeepSeek API Key | 要快、要通顺、不想在本机跑模型 | 填 `api_config.json`；扩写与润色都走 API |
| 混合 | API Key（扩写）+ 本地 | 想省钱又想要 API 的扩写质量 | 扩写选 API，润色选「本地」或「模板」 |

顶部「⚙ API」按钮也能填地址 / 模型 / Key，保存后同时写浏览器与 `api_config.json`。
三种模式的词库匹配、角色外观补全、负向自适应、标签拼装都在本地完成，与是否联网无关。

## 功能

### 输入侧

| 功能 | 说明 |
|---|---|
| 图反推 | WD14 打标 → 标签自动进入「已选」，并给一段中文描述（需可选依赖） |
| AI 扩写 | 几句中文 → 完整分镜；DeepSeek API 或本地 Ollama |
| 词库点选 | 18000+ 条、7 大类，搜索 / 收藏 / 拖拽分类 / 右键编辑角色 |
| 画风库 | 50 张缩略图，点一张即加对应画风标签 |

### 处理侧

| 功能 | 说明 |
|---|---|
| 拆标签 | 中英文标签匹配，草稿自动拆成角色与标签，各归各位 |
| 外观补全 | 角色自带发色 / 瞳色 / 服装，生成时自动补齐缺失项 |
| 外观约束 | 扩写时把角色外观锁进提示词，禁止串角色、禁止改设定 |
| 密度三档 | 精简 / 标准 / 复杂；精简档每角色 8 个、全局 6 个，标准与复杂不截断 |
| 负向自适应 | 正向出现 uncensored / 裸露 / chibi / 灰度时，自动剔除冲突的负向词 |

### 输出侧

| 功能 | 说明 |
|---|---|
| MOSS | 中文段落 + 中文负向，适合中文模型与文案 |
| WAI | 英文标签串，Illustrious 系直接用 |
| Pony | `score_9, score_8_up, ...` 前缀 + Pony 专用负向 |
| 一键复制 | 每个区块右上角单独复制，6 个区块互不影响 |
| 历史记录 | 最近 30 条扩写记录，可回填 |

## 效果展示

三张图均由本工作台生成提示词，ComfyUI + WAI-illustrious v16 出图。

**Q版 · 角色C**

![Q版 角色C](docs/showcase-1.jpg)

Q 版比例，海边、水手服、玫瑰花束，另有两只缩小分身。

**粉发 · 角色E**

![粉发 角色E](docs/showcase-2.jpg)

街景逆光，粉发粉瞳，单手拈花。

**白发 · 角色A**

![白发 角色A](docs/showcase-3.jpg)

室内窗边逆光，白发红瞳，长裙。

> 角色外观来自词库设定；同一套标签换角色即换风格。

## 内置说明书

点顶部「📖 说明书」打开内置说明书，四个页签：概览 / 流程 / 开关 / 技巧。

| 概览 | 开关说明 |
|---|---|
| ![说明书概览](docs/guide-overview.png) | ![开关说明](docs/guide-switches.png) |

![流程与快捷键](docs/guide-flow.png)

## 可选依赖

| 组件 | 用途 | 没有它会怎样 | 安装 / 配置 |
|---|---|---|---|
| Python 3.10 ~ 3.12 | 运行后端 | 起不来 | 从 python.org 安装，勾选 PATH；3.14+ 图片反推不可用 |
| onnxruntime + Pillow + numpy | 图反推 | 图反推不可用，其余功能正常 | `pip install onnxruntime pillow numpy` |
| WD14 模型 | 图反推权重 | 图反推不可用，其余功能正常 | 下载 `wd-v1-4-moat-tagger-v2.onnx` + 同名 `.csv` |
| DeepSeek API Key | API 扩写 / 润色 | 只能用 Ollama 或模板，功能仍完整 | 填 `api_config.json` 或界面「API」 |
| Ollama | 本地扩写 / 润色 | 本地模式不可用，API 模式不受影响 | 从 [ollama.com](https://ollama.com) 安装并常驻 |
| ComfyUI | 出图 | 与本工具无关，只影响出图 | 独立安装 |

### WD14 模型路径

默认从 ComfyUI 的插件目录找（下面是示例路径，`<ComfyUI>` 换成你的实际安装目录）：

```
<ComfyUI>/custom_nodes/ComfyUI-WD14-Tagger/models/wd-v1-4-moat-tagger-v2.onnx
```

模型放在别处时用环境变量覆盖：

```bash
# Windows（仅当前终端有效）
set WD14_MODEL=<你的模型路径>
set WD14_TAGS=<你的标签表路径>

# macOS / Linux
export WD14_MODEL=<你的模型路径>
export WD14_TAGS=<你的标签表路径>
```

`WD14_TAGS` 可省略，默认取模型同名 `.csv`，或同目录的 `selected_tags.csv`。
中文名由项目内 `tags_cn.json` 映射，不需要额外数据文件。模型可从 [SmilingWolf/wd-v1-4-moat-tagger-v2](https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2) 获取。

### Ollama 模型（可选）

```bash
ollama pull qwen2.5:7b     # 本地扩写默认模型
ollama pull qwen2.5:3b     # 备用，显存小时换它
ollama pull goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest   # 成人向兜底
```

服务地址默认 `http://127.0.0.1:11434`，模型名与地址在 `expand_mod.py` 顶部常量里改。

## 目录结构

`
studio2/
├── 提示词工作台.lnk        ← 双击启动（推荐）
├── install.bat             ← 安装向导（调用 install.ps1）
├── install.ps1 / launch.ps1
├── 启动工作台.bat          ← 启动脚本（自动探测 Python）
│
├── app.py                 后端 HTTP 服务 + 全部接口（仅标准库）
├── parse_mod.py           拆标签：中英文匹配 + 角色外貌补全
├── gen_mod.py             MOSS / WAI / Pony 拼装 + 负向自适应
├── expand_mod.py          扩写：DeepSeek / Ollama / 模板兜底
├── wd14_mod.py            图反推：WD14 ONNX 打标
│
├── static/                前端（index.html + app.js + favicon）
├── styles/                画风库 50 张缩略图 + styles.json
├── docs/                  README 配图、说明书截图、开发报告
├── tools/                 开发脚本（词库构建 / 数据修正 / 验证）
│
├── tags_cn.json           词库（18000+ 条）
├── chars_app.json         内置角色外貌表
├── chars_extra.json       补充角色
├── custom_chars.json      用户自定义角色（运行时生成，不入库）
├── api_config.json        API 配置（不入库）
├── api_config.example.json
├── icon.ico               程序图标
├── README.md
└── LICENSE
`

> 	ools/ 里的脚本只在维护词库时用，日常使用不需要。
> 里面的路径多为相对项目根目录，移动目录后请检查后再运行。

## 数据说明

**词库字段** `tags_cn.json`

```json
{ "zh": "中文名", "en": "english_tag", "cat": "分类", "sub": "子分类", "nsfw": false, "app": {} }
```

- `cat`：角色 / 外形 / 服装 / 动作 / 道具 / 场景 / 自定义
- `sub`：子分类；角色条目这里是作品名
- `app`：角色外观五字段 `hair / eyes / outfit / body / chest`，值为中文描述；角色另有 `hair_en / eyes_en / outfit_en` 英文标签

**自定义角色** 界面上右键角色卡可改外观；新建角色写入 `custom_chars.json`，同时同步到浏览器 localStorage。
优先级高于内置角色，删掉该文件即恢复内置。

**存储位置**

| 位置 | 内容 | 是否入库 |
|---|---|---|
| `tags_cn.json`、`chars_*.json` | 词库与内置角色 | 是 |
| `custom_chars.json` | 自定义角色 | 否 |
| `api_config.json` | API 地址 / 模型 / Key | 否 |
| 浏览器 localStorage | 开关、面板尺寸、收藏、分类调整、扩写历史（30 条） | — |

数据只在本机，不上传云端；只有勾选「API」或润色选「API」时，文字才发给 DeepSeek。
清浏览器数据会丢 localStorage 里的偏好，`custom_chars.json` 与 API 配置另存于项目目录。

## 常见问题 FAQ

**1. 8901 打不开 / 页面白屏？**
确认进程在跑（`python app.py` 应打印 `workbench v2 on ...`）；白屏多半是缓存了旧 `app.js`，Ctrl+F5 强制刷新。
仍不行查端口占用：`netstat -ano | findstr 8901`，或改 `PORT` 重启。

**2. 图反推报错「WD14 模型不存在」？**
模型没下或路径没对上。按上面的「WD14 模型路径」设 `WD14_MODEL`，确认同目录有 `.csv`，再重启。

**3. 扩写等很久后失败 / 连接被拒？**
本地扩写走 Ollama：确认已安装、`ollama serve` 在跑、`curl http://127.0.0.1:11434/api/tags` 有 JSON 返回；没拉模型也会失败。
失败不影响出结果，界面会退回模板。

**4. 生成的是标签串，不是通顺中文？**
「润色」选了「关」或「模板」。改成「API」或「本地」重新生成；只关心 WAI / Pony 的话不受影响。

**5. 图反推出来有英文没翻译？**
`tags_cn.json` 里缺该词的中文名，只能原样显示英文。可当普通标签用，或补齐词库后刷新页面。

**6. 改了词库 / 角色要不要重启？**
`tags_cn.json`、`chars_app.json` 只在页面加载时读一次，改完刷新页面即可；`app.py`、`gen_mod.py` 等 Python 改动必须重启。

## NSFW 说明

三级判定，只作用于扩写出的中文文本：

| 级别 | 例子 | 处理 |
|---|---|---|
| 露骨 explicit | 具体性器官、性行为描写 | 命中即整句删除 |
| 擦边 soft | 内裤外露、走光、长筒袜、透视、内衣 | 原样保留，不删句不改写 |
| 其余 | 普通外观 / 场景描述 | 放行 |

- 删句后重算人数、清空空壳行；全删时返回占位文本，不会输出空串。
- 顶部「NSFW 模式」关闭时：正向过滤 NSFW 标签，WAI / Pony 负向追加裸露类词；MOSS 负向不受该开关影响。
- 词库约 4100 条标记 `nsfw: true`。
- 自检：`python verify_nsfw_tiers.py`。

## 已知限制

- 本地扩写质量取决于 Ollama 模型：7B 以下容易跑题或被内容策略拒绝；要稳定就上 API 或换更大模型。
- WD14 只输出英文标签，中文名靠 `tags_cn.json` 映射；词库没有的只能显示英文。
- 单角色时负向会自动追加 `2girls / multiple_girls / split_screen / character_sheet` 防克隆，这会堵住多角色。
  要画多角色：加多个角色框，把位置词写进对应角色框，并把负向改成「精简」或「关」。
- 密度三档里只有「精简」真正截断（每角色 8 / 全局 6），标准与复杂输出一致。
- 单进程、无鉴权，默认只监听 `127.0.0.1`，不要直接暴露到公网。

## 许可证

MIT，详见 [LICENSE](LICENSE)。

## 致谢

- [DeepSeek](https://deepseek.com) — API 扩写与润色
- [Ollama](https://ollama.com) — 本地模型运行
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — 出图
- [SmilingWolf](https://huggingface.co/SmilingWolf) — WD14 标签模型与标签表
- 词库中的角色与作品版权归各自权利人所有
