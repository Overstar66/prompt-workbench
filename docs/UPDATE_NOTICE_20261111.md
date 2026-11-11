版本一 · 短动态（约 350 字）

提示词工作台今天连更三版：新增 Animagine 和 Krea2，现在能出五种模型的提示词

今天把工作台从 v1.2 一路更到 v1.5，三件事最值得说。

第一，多加了两个模型。现在一次能出五种提示词：MOSS（中文自然语言）、WAI（Danbooru 标签）、Pony（score_9）、Animagine XL（标签 + very_aesthetic）、Krea2（英文自然语言）。Krea2 是 CFG=1 的蒸馏模型，负向不起作用，界面上标了说明。

第二，选角色会自动补外观。发色、瞳色、服装从词库带出来，你自己写的描述优先。

第三，修了几个影响手感的问题：分栏拖拽不会再拖出屏幕、结果区五个标签不再挤成一团、标签拖进自然语言框或草稿会写中文而不是 smile。

下载：github.com/Overstar66/prompt-workbench
Source code (zip) 解压双击 install.bat，Windows 需要 Python 3.10+。


版本二 · 标准专栏（约 900 字）

提示词工作台连更三版：两个新模型、拖拽写中文、布局修复

今天把工作台从 v1.2 更到 v1.5，攒了三版的改动一起说。

亮点：多了两个模型

现在一次能出五种模型的提示词：

MOSS —— 中文自然语言
WAI —— Danbooru 标签（Illustrious 系）
Pony —— score_9 体系
Animagine XL —— 标签 + very_aesthetic 质量词
Krea2 —— 英文自然语言描述

两者定位不同。Animagine 和 WAI 同属标签体系，提示词几乎通用，只换质量前缀；Krea2 走 Qwen3VL 文本编码器，吃句子不吃标签，所以单独拼英文描述，不跟标签混。

提醒一句：Krea2 是 CFG=1 的蒸馏模型，负向提示词对它不起作用，界面上已经标了说明，需要把 KSampler 的 cfg 调到 3 以上才生效。

改进：三处用起来更顺

1. 角色自动补外观
选一个角色，MOSS 会自动带上词库里的发色、瞳色、服装。你自己写的描述优先级更高。

2. 拖标签写中文
把标签拖进「自然语言框」或「MOSS 草稿」，以前出来的是 smile、beach，现在直接写「微笑」「海边」。

3. 扩写骨架统一
本地、API、NSFW 开关三种模式，扩写输出都按「N个角色 + 原始名单」的格式来，不会再自己编名字或把两个人揉成一段。

修复：四个会影响使用的 bug

1. 分栏拖拽没有边界
拖右边界能把「结果」「历史记录」拖出屏幕。现在右侧固定占剩余宽度，最小 300px，窗口缩放也会重新夹紧。

2. 结果区标签挤成一团
五个模型标签放不下会折行，标题和按钮被压扁。现在标签自动换行，标题按钮不折行。

3. 发色整段丢失
「蓝色超长波浪发」这类描述匹配不到词库整词，发色整体消失，出图变成深棕发。现在按「颜色 + 发」兜底成 blue_hair / very_long_hair / wavy_hair。

4. 解析器误判角色
「百合」「内裤」这类题材词、服装词会被当成角色名。现在有表头就只认表头，没有表头才走白名单。

另外

表头写法放宽，这些都能识别：

两个女生 角色A 角色B
两个角色角色a角色b
两个人初音未来，略略略
4个角色 百合 内裤 角色a 角色b

下载

github.com/Overstar66/prompt-workbench

Source code (zip)，解压后双击 install.bat。
Windows 需要 Python 3.10+，macOS / Linux 用 python app.py 启动。
老用户 git pull 即可，配置和自定义角色不会丢。


版本三 · 技术向（约 1300 字）

工作台 v1.3 → v1.5 更新日志：双模型接入与四类 bug 修复

今天三版连更，按「亮点 → 改进 → 修复」的顺序写，方便对照。

一、亮点：Animagine XL 与 Krea2

1. Animagine XL（v1.4）

和 WAI 同属 Danbooru 标签体系，共用一套标签，差异只在质量前缀：

WAI：masterpiece, best quality, amazing quality
Animagine：masterpiece, best quality, very aesthetic, absurdres

新增输出块「Animagine XL」和独立开关，本地模型 animagine-xl-3.1 已部署（6.94 GB），ComfyUI 里也建好了对应工作流。

2. Krea2（v1.5）

Qwen-Image 系，文本编码器 Qwen3VL，8 步 turbo，CFG=1。

它不吃标签，所以单独写了构建器，输出形如：

A detailed anime illustration of lueluelue. Character details: lueluelue, smile, heart ahoge, thighhighs, dress, maid. Scene: beach, sunset. Soft lighting, clean lineart, high detail, full body composition.

三个细节：

· 特征上限从 10 放宽到 18，否则 blue_hair 被截断，出图变深棕发
· 外观里的「藏青色」会误匹配 naganami_(kancolle)，现在过滤所有 cat=角色 的标签
· CFG=1 时负向无效，界面标注「需把 KSampler cfg 调到 3 以上才起作用」

二、改进：三处手感

1. 角色自动补外观

MOSS 拼装走规则版函数，原来只读角色标签不读描述。两处改动：生成入口把 app 里的中文外观并进 desc；规则版拼行时，有标签就把外观拼在前面，没标签就用外观兜底。

2. 拖拽写中文（v1.3）

标签拖进 #nl 或 #draft 时，取 zh 而不是 en，插入到光标处，按中文顿号补分隔符，并触发 input 事件同步状态。

3. 扩写骨架统一

本地 / API × NSFW 开 / 关，三种模式的输出统一为：

N个角色 原名A 原名B
原名A：一段描写
原名B：一段描写
场景：地点、光线、氛围

不允许改写成「名字1/名字2」，也不允许从正文里编出假角色（例如把「搞百合」当成角色名）。表头声明几个就输出几段，缺的用解析结果补。

三、修复：四类 bug

1. 分栏拖拽无边界（v1.4）

原因：拖 mid|right 时把右侧也写成固定像素，丢了弹性；恢复保存栏宽时没按窗口夹紧。
改法：右侧 flex:1 吃剩余宽度，最小 300px；左列上限 = 容器宽 − 320；window.resize 时重新夹紧。

2. 结果区标签拥挤（v1.4）

五个模型标签放不下会折行，标题与按钮被压扁。
改法：标题、按钮强制 nowrap；标签容器 flex-wrap；头部高度改 auto。

3. 发色整体丢失（v1.4）

原因：描述写「蓝色超长波浪发」，正则的长度词表里没有「波浪」「超长」，整段匹配失败，发色被跳过。
改法：加兜底——描述里出现「颜色 + 发」时直接落 blue_hair / very_long_hair / wavy_hair。

修前：blue_eyes, white_maid_outfit
修后：blue_eyes, white_maid_outfit, blue_hair, very_long_hair, wavy_hair

4. 解析器误判角色（v1.3）

原因：旧逻辑是「谁写了冒号谁就是角色」，且表头正则只认「N个角色」；「两个女生」不匹配就落到「扫词库角色名」的兜底分支，正文里的「无内裤」三个字命中了角色 panty_(psg)，于是内裤变成角色。

改法三层：有表头只认表头；表头名字可粘连拆分（角色a角色b → 角色a、角色b）；没有表头才走白名单；只有标签行时不硬凑角色。

另外，扩写输出里模型会从正文编出假角色（「搞百合」），现在按表头名单强制重排，多出来的段落丢弃。

四、其他

· 词库补回自定义角色「略略略」（之前 reset 时被回滚）
· 测试输出文件从仓库移除，加入 .gitignore
· 维护 tools/ 目录，开发脚本与业务代码分离

下载

github.com/Overstar66/prompt-workbench
Source code (zip)，解压双击 install.bat；Windows 需要 Python 3.10+。
