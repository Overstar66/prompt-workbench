# 用 DSH 一键部署（AI 代装）

如果你装了 [DeepSeek Harness](https://github.com/)，可以让它替你把这套工作台装好、跑起来，你不用记命令。

下面这份文档就是给 DSH 看的「部署说明书」——把整段发给它即可。

---

## 给 DSH 的完整指令（直接复制）

````text
请帮我部署「提示词工作台」这个项目，按下面步骤执行，每步做完告诉我结果。

## 背景
- 项目地址：https://github.com/Overstar66/prompt-workbench
- 它是一个本地运行的 Python 网页应用，端口 8901
- 后端只用 Python 标准库，额外依赖只有图反推用的 onnxruntime / pillow / numpy（可选）

## 步骤

1. 检查环境
   - 确认已安装 Python 3.10+：运行 `python --version`
   - 如果没有，告诉我需要先装 Python，并给出 https://www.python.org/downloads/ 链接

2. 获取代码（二选一，按我机器上是否装了 git 决定）
   - 有 git：`git clone https://github.com/Overstar66/prompt-workbench.git`
   - 没有 git：提醒我下载 https://github.com/Overstar66/prompt-workbench/releases 里的 zip 并解压

3. 安装可选依赖
   - 运行 `pip install onnxruntime pillow numpy`
   - 失败也不要中断，告诉我「图反推不可用，其他功能正常」

4. 配置 API（可选）
   - 把 `api_config.example.json` 复制成 `api_config.json`
   - 问我有没有 DeepSeek API Key：
     - 有 → 让我把 key 给你，你写进 api_config.json 的 `key` 字段
     - 没有 → 跳过，说明会自动退回模板模式或本地 Ollama

5. 启动服务
   - 在项目目录运行 `python app.py`（Windows 可用 `pythonw app.py` 后台跑）
   - 等待 3 秒，访问 http://127.0.0.1:8901 确认返回 200
   - 如果端口被占用，告诉我，或改 app.py 里的 PORT

6. 验证功能
   - 请求 `http://127.0.0.1:8901/api/tags`，确认返回的条数大于 18000
   - 请求 `http://127.0.0.1:8901/api/styles`，确认返回 50 个画风
   - 把两个结果告诉我

7. 收尾
   - 告诉我访问地址、当前是「API 模式 / 本地模式 / 模板模式」中的哪一种
   - 如果没有 API Key 也没装 Ollama，提醒我扩写会退化成模板
````

---

## 部署完成后你会得到什么

| 检查项 | 期望 |
|---|---|
| 访问地址 | http://127.0.0.1:8901 |
| 词库条数 | 18000+ |
| 画风库 | 50 张 |
| 模式 | API / 本地 / 模板（取决于你提供了什么） |

## 常见问题

**Q：DSH 装到一半失败了怎么办？**
让 DSH 把报错原文贴给你，或直接手动执行：

```bash
git clone https://github.com/Overstar66/prompt-workbench.git
cd prompt-workbench
pip install onnxruntime pillow numpy
python app.py
```

**Q：能不能不装 Python 就让 DSH 跑？**
不能。这个项目是 Python 后端，必须有 Python 3.10+。

**Q：DSH 能帮我装 Ollama 吗？**
能引导，但安装包需要你自己点确认（约 1 GB）。装好后可以让 DSH 执行
`ollama pull qwen2.5:7b` 拉模型。

**Q：以后更新怎么办？**
```bash
cd prompt-workbench
git pull
```
然后重启服务即可，词库和配置不会丢。

---

## 不想用 DSH？

Windows 用户直接双击仓库根目录的 `install.bat`，它是同一套流程的批处理版本。

手动部署见 [README 的快速开始](../README.md#快速开始)。
