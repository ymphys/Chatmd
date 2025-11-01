# Chatmd

Chatmd 是一个命令行辅助脚本，用于读取指定的 Markdown 文档，把内容拆分成适合投递到 OpenAI Chat Completions API 的片段，并针对一组预设问题产出结构化解读。所有回答会被追加写入 `output/interpretation_results.md`，详细执行日志则保存在 `output/chatmd.log`。

## 功能概览
- 读取 `main.py` 中配置的 Markdown 源文件，并将全文载入内存。
- 采用 `split_into_chunks`（默认 100000 字符/片）对内容分块；如果只有一块，则直接回收该块的回答。
- 为列表中的每一个问题逐片调用 GPT-4 Turbo（`gpt-4-turbo-preview`），必要时再触发一次合并调用以整合多片段答案。
- 通过 `load_existing_answers` 避免对已经写入过 `## 问题` 标题的条目重复提问。
- 对每次请求记录 token 用量和费用估算，终端输出简要进度，详细信息写入 `chatmd.log`。

## 依赖与环境
- Python 3.12+
- 包管理使用 [uv](https://github.com/astral-sh/uv)；依赖在 `pyproject.toml` 中声明（`requests`, `python-dotenv` 等）。
- 运行前需在环境变量中设置 `OPENAI_API_KEY`。

在使用 uv 的情况下，可按以下步骤准备环境（示例命令基于 zsh）：

```bash
# 安装依赖并创建虚拟环境（默认放在 .venv）
uv sync

# 让当前 shell 使用该虚拟环境
source .venv/bin/activate

# 配置 API Key（建议写入 ~/.zshrc 以持久化）
export OPENAI_API_KEY="sk-..."
```

## 配置与运行
1. **设置输入文档**：在 `main.py` 的 `md_file_path` 指向你要解读的 Markdown 文件（默认示例位于 `mds/` 目录）。
(如果你手头只有PDF文件，可以先使用[MinerU](https://mineru.net/OpenSourceTools/Extractor/)将它转换为md格式。)

2. **编辑问题列表**：调整 `questions` 列表即可控制脚本会提出的解读问题；字符串会按顺序处理。已经解读过的问题及其返回的答案会被自动跳过(load_existing_answers函数的功能)，请不要注释或更改，否则会被视为新问题。

3. **启动脚本**：
   ```bash
   uv run python main.py
   ```
   运行结束后可在终端看到 INFO 级别日志，详尽日志请查看 `output/chatmd.log`。

## 输出内容
- `output/interpretation_results.md`：若不存在会创建，并在文件尾部追加新的回答。每个问题以 `## 问题` 的形式记录，便于日后查找。
- `output/chatmd.log`：记录所有 API 请求、重试、用量统计及错误信息。

脚本在写入新答案前会扫描 `interpretation_results.md` 中的 `##` 标题；如果发现同样的问题文本将跳过，以保持幂等。

## 实现要点
- `_post_with_retries` 对 `429`/`5xx` 做指数退避，最多尝试 4 次；分片请求之间默认等待 1 秒，可视速率限制调整。
- 若文档长度只产生一个片段，则直接使用该片段的回答，避免额外的“合并”模型调用；多片段情况下会再次请求模型整合文本。
- 费用估算基于 GPT-4 Turbo（2025 年 10 月版）的输入/输出单价，仅供调试参考。
- 当前脚本不会自动调用 `load_dotenv()`；如需从 `.env` 文件加载 key，可在 `main()` 中手动加入。

## 常见问题排查
- **`OPENAI_API_KEY` 缺失**：`load()` 会抛出异常；请确认在当前 shell 中设置了环境变量。
- **频繁出现 429**：适当增大 `split_into_chunks` 的大小、减少问题数量，或延长分片间的 `time.sleep`。
- **输出重复**：手动删除或重命名 `output/interpretation_results.md` 中的旧条目，脚本即可重新生成对应问题的回答。

如需扩展（例如批量处理多文件、引入独立问答接口或调整模型），可在 `main.py` 上直接修改流程；当前实现的体量便于快速试验与迭代。
