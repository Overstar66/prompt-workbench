版本一 · 短动态（约 300 字，适合图文动态）

提示词工作台 v1.5 更新：新增 Krea2，修了三个影响手感的问题

提示词工作台更新到 v1.5。

新增 Krea2：现在一次能出五种提示词——MOSS（中文自然语言）、WAI（Danbooru 标签）、Pony（score_9）、Animagine（标签 + very_aesthetic）、Krea2（英文自然语言）。Krea2 是 CFG=1 的蒸馏模型，负向提示词对它不起作用，界面上已标注。

MOSS 现在会自动补角色外观：选一个角色，发色、瞳色、服装会跟着带出来，你在描述里自己写的内容优先。

修了三个手感问题：分栏拖拽加了边界，右侧不会再被拖出屏幕；结果区五个模型标签自动换行，不再挤压标题；标签拖进自然语言框或 MOSS 草稿时写中文，出来的是「微笑」「海边」，不是 smile、beach。

下载：GitHub 搜 prompt workbench，或访问 github.com/Overstar66/prompt-workbench
Source code (zip) 解压后双击 install.bat，Windows 需要 Python 3.10+。


版本二 · 标准专栏（约 800 字，适合专栏/长动态）

提示词工作台更新到 v1.5，现在能出五种模型的提示词了

提示词工作台更新到 v1.5 了，这次三件事。

一、新增 Krea2

工作台现在能一次出五种提示词：

MOSS —— 中文自然语言
WAI —— Danbooru 标签（Illustrious 系）
Pony —— score_9 体系
Animagine —— 标签 + very_aesthetic 质量词
Krea2 —— 英文自然语言描述

Krea2 走的是 Qwen3VL 文本编码器，吃的是句子不是标签，所以它的输出单独拼了一段英文描述，不跟标签混。

注意一点：Krea2 是 CFG=1 的蒸馏模型，负向提示词对它不起作用，界面上已经标了这个说明，别以为是 bug。

二、MOSS 现在会自动补角色外观

以前选个角色，MOSS 只给你名字，发色瞳色服装全靠自己写。现在会自动带上词库里的默认外观：

略略略：蓝色超长波浪发、浅蓝渐变发梢、心形呆毛、鲸鱼鳍状耳、蓝眼睛、白色蕾丝围裙女仆装、娇小、标准。

你自己在描述里写的内容优先级更高，不会被覆盖。

三、修了三个影响手感的问题

1. 分栏拖拽
以前拖右边界能把「结果」「历史记录」拖出可视区，现在有最小宽度限制。

2. 结果区标签拥挤
五个模型标签挤在一起会折行，现在自动换行，标题和按钮不再被压扁。

3. 拖标签写中文
把标签拖进「自然语言框」或「MOSS 草稿」，以前出来的是 smile、beach 这种英文，现在直接写「微笑」「海边」。

另外

解析器认表头的写法多了，这些都能识别：

两个女生 角色A 角色B
两个角色角色a角色b
两个人初音未来，略略略
4个角色 百合 内裤 角色a 角色b

不会再出现「百合」「内裤」被当成角色名的情况。

下载

GitHub 搜 prompt workbench，或直接访问：
github.com/Overstar66/prompt-workbench

下载 Source code (zip)，解压后双击 install.bat。
Windows 需要 Python 3.10+，macOS / Linux 用 python app.py 启动。

老用户直接 git pull 就行，配置和自定义角色不会丢。


版本三 · 技术向（约 1100 字，适合专栏，给懂的人看）

v1.5 更新日志：Krea2 接入、外观兜底回归、布局修复

这次更新偏工程，写细一点，方便遇到问题的人对照。

一、Krea2 接入

Krea2 是 Qwen-Image 系的模型，文本编码器是 Qwen3VL，8 步 turbo，CFG=1。它和标签模型是两条路：标签模型吃逗号分隔的 Danbooru 标签，它吃完整句子。

所以工作台里给它单独写了一个构建器，输出形如：

A detailed anime illustration of lueluelue. Character details: lueluelue, smile, mary jane shoes, heart ahoge, thighhighs, dress, maid. Scene: beach, sunset. Soft lighting, clean lineart, high detail, full body composition.

三个细节：

1. 特征上限从 10 放宽到 18，否则 blue_hair 会被截掉，出图变成深棕发。
2. 外观里的「藏青色」会误匹配到 naganami_(kancolle)，现在过滤所有 cat=角色 的标签。
3. CFG=1 时负向不生效，界面上明确标注「需把 KSampler cfg 调到 3 以上才起作用」，避免被当成 bug。

二、发色兜底回归

之前有个问题是「蓝色超长波浪发」这类描述，正则匹配不到词库整词，发色整体丢失。现在加了一层兜底：描述里出现「颜色 + 发」时，直接落成 blue_hair、very_long_hair、wavy_hair 这类标签。

效果：

修前：blue_eyes, white_maid_outfit
修后：blue_eyes, white_maid_outfit, blue_hair, very_long_hair, wavy_hair

三、MOSS 补外观

MOSS 是中文输出，但它的拼装走的是规则版函数，原来只读角色标签，不读描述。两处改动：

1. 生成入口把角色自带外观并进 desc，用户已写的部分优先。
2. 规则版拼行时，有标签就把外观拼在前面，没标签就用外观兜底。

四、布局修复

1. 分栏拖拽
   原因：拖 mid|right 时把右侧也写成了固定像素，丢掉了弹性；恢复保存栏宽时也没按窗口夹紧。
   改法：右侧固定 flex:1 吃剩余宽度，最小 300px；左列上限 = 容器宽 - 320；窗口 resize 时重新夹紧。

2. 结果区标签
   五个模型标签（MOSS / WAI / Pony / Animagine / Krea2）挤在一起会折行。
   改法：标题和按钮强制 nowrap，标签容器 flex-wrap，头部高度改 auto。

3. 底部两栏
   草稿与历史记录原来沿用保存的像素宽度，窗口变小就把草稿挤成一条缝。
   改法：固定 2:1 弹性比例，不再存像素值。

五、解析器

表头识别放宽，支持：

两个女生 角色A 角色B
两个角色角色a角色b（粘连自动拆分）
两个人初音未来，略略略
4个角色 百合 内裤 角色a 角色b

规则：有表头只认表头名字；没有表头才走白名单；只有标签行时不硬凑角色。

下载

github.com/Overstar66/prompt-workbench
Source code (zip)，解压双击 install.bat；Windows 需要 Python 3.10+。
