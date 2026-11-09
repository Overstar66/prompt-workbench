# 提示词工作台（studio2）

一个本地运行的动漫插画**提示词工作台**：从图片反推标签 → AI 扩写 → 拆成标签 → 生成 MOSS / WAI / Pony 提示词。

> ⚠️ 本项目包含成人向（NSFW）词库与内容，**仅限 18 岁以上用户**，仅供个人学习与创作使用。
> 角色名与作品名版权归各自权利人所有，本项目为非官方同人工具，与任何官方无关。

## 功能

- **图反推**：WD14 打标 → 标签自动进入「已选」，同时给出一段中文描述
- **AI 扩写**：DeepSeek API（快、通顺）或本地 Ollama（离线、可写成人内容）
- **拆标签**：中英文标签匹配 + 角色外貌自动补全
- **MOSS / WAI / Pony**：一键生成三套提示词与负向
- **润色四模式**：模板 / 关 / API / 本地
- **词库 11000+**：角色 1600+（219 部作品，带发色瞳色服装）、外形 / 服装 / 动作 / 道具 / 场景
- **界面**：面板尺寸记忆、收藏、拖拽分类、右键编辑角色、历史记录

## 环境要求

| 组件 | 必需 | 说明 |
|---|---|---|
| Python 3.10+ | ✅ | 只用标准库，无第三方依赖 |
| DeepSeek API Key | 可选 | 用于 API 扩写 / API 润色 |
| Ollama | 可选 | 本地扩写与润色 |
| ComfyUI | 可选 | 本项目只生成提示词，出图在 ComfyUI |

### 可选：Ollama 模型

```bash
ollama pull qwen2.5:7b     # 安全内容润色
ollama pull qwen2.5:3b     # 备用
ollama pull goonsai/qwen2.5-3b-goonsai-nsfw-100k:latest   # 成人向润色
```

未安装 Ollama 时，本地扩写会自动降级，不影响其余功能。

## 快速开始

```bash
git clone <仓库地址>
cd studio2

# 1) 配置 API（可选）
copy api_config.example.json api_config.json
#   填入你的 key

# 2) 启动（Windows）
python app.py
#   或双击 启动工作台.bat

# 3) 打开浏览器
http://127.0.0.1:8901
```

默认端口 **8901**，可在 `app.py` 末尾修改。

## 目录结构

```
studio2/
├── app.py                 后端 HTTP 服务（标准库，无依赖）
├── parse_mod.py           拆标签：中文匹配 + 外貌补全
├── gen_mod.py             MOSS / WAI / Pony 生成 + 负向自适应
├── expand_mod.py          扩写：DeepSeek / Ollama
├── legacy_expand.py       老版三步扩写（可选，缺数据会自动降级）
├── static/                前端（index.html + app.js）
├── styles/                画风库 50 张
├── tags_cn.json           词库（11000+ 条）
├── chars_app.json         角色外貌表
├── chars_extra.json       补充角色
├── custom_chars.json      用户自定义角色（运行时生成，不入库）
├── api_config.json        API 配置（不入库）
└── build_*.py             词库构建脚本（可重跑）
```

## 数据说明

- `tags_cn.json`：`{zh, en, cat, sub, nsfw, app}`，角色条目带外貌五字段
- `chars_app.json`：角色 `hair / eyes / outfit / body / chest` 中文描述
- 用户自定义角色写入 `custom_chars.json`，优先级高于内置

## NSFW 说明

- 词库中约 4000 条标记 `nsfw: true`
- 界面顶部「NSFW模式」控制扩写是否生成成人内容
- 关闭时：正向过滤 NSFW 标签，WAI/Pony 负向自动追加裸露类词
- MOSS 负向不受该开关影响

## 许可证

MIT，详见 [LICENSE](LICENSE)。

## 致谢

- [DeepSeek](https://deepseek.com) — API 扩写与润色
- [Ollama](https://ollama.com) — 本地模型
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — 出图
