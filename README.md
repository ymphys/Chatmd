# Chatmd — 使用与开发说明

本仓库是一个脚本工具，用于从 Markdown 论文/报告中提取“摘要/结论”、按片段调用 OpenAI Chat 接口进行文档解读与问答，并把结果写回到仓库根目录的 Markdown 文件中。

核心职责与入口
- 入口脚本：`main.py`。主要流程：读取 `mds/` 下的 md 文件 -> `extract_md_content` 提取摘要/结论 -> `split_into_chunks` 切分 -> 对每个片段调用 OpenAI（`_post_with_retries`）-> 合并片段回答（`chatgpt_interpretation` / `answer_questions`）-> 写入 `abstract_conclusion.md` / `interpretation_results.md`。

关键文件
- `main.py` — 主实现（必须阅读）：`load()`, `extract_md_content()`, `split_into_chunks()`, `_post_with_retries()`, `chatgpt_interpretation()`, `answer_questions()`。
- `test_connection.py` — 验证 OpenAI API key 与网络。
- `pyproject.toml` — Python 版本与依赖（Python >= 3.12, `requests`, `dotenv`）。
- `mds/` — 输入 Markdown 文件目录（示例：`Relativistic electron beam propagation...md`）。
- 输出文件：`abstract_conclusion.md`, `interpretation_results.md`（追加模式，支持中断恢复）。
- 日志文件（运行时产生）：`chatmd.log`（DEBUG 级别详细日志，终端只打印 INFO 摘要）。

快速上手（macOS / zsh）
- 设置 API key（临时）：

```bash
export OPENAI_API_KEY="sk-..."
```

- 安装依赖：

```bash
pip install requests python-dotenv
```

- 运行：

```bash
# 测试连接
python test_connection.py

# 执行主流程（会打印简要进度，详细信息见 chatmd.log）
python main.py
```

行为约定（重要实现细节）
- 分片策略：`split_into_chunks(content, chunk_size=3000)` — 默认 3000 字符/片。增减会直接影响 API 调用次数和速率。
- 合并策略：当前实现为“分片 -> 每片调用 -> 再次调用模型合并片段回答”。合并会产生额外请求；如需节省调用，可改为本地拼接/摘要然后只在必要时调用模型精炼。
- 重试与限流：`_post_with_retries` 对 429/5xx 做指数退避（`base_delay=1`, `max_retries=4`）。每片请求后会 `time.sleep(1)` 以降低速率。
- 断点续跑：程序会读取 `interpretation_results.md` 中以 `## ` 开头的条目来判断哪些问题已被回答，跳过已存在的问题，从而避免重复调用与重复写入。
- 日志：终端显示 INFO 摘要；所有 DEBUG/详细信息写入 `chatmd.log`（包括每个 chunk 的短预览）。

安全与提交流程
- 请不要把 API key 或 `.env` 提交到仓库（`.gitignore` 已包含 `.env`）。
- 在推送触发实际 API 请求的改动前，请在本地运行 `python test_connection.py` 确认 key 与网络可用。

可直接改进点（可 PR）
- 将模型名抽成顶部常量（例如 `MODEL = "gpt-4-turbo-preview"`），避免在多个位置硬编码。
- 把合并改为客户端拼接（在 `chatgpt_interpretation`/`answer_questions` 中用本地合并/摘要替代第二轮模型调用），可显著减少请求次数与费用。
- 若需更细粒度的断点续跑（例如保存每个片段的部分回答以在中断后从中间恢复），可以为每个问题写入单独的 JSON checkpoint 文件。

故障排查要点
- 如果遇到 429：先把 `time.sleep(1)` 增加到 `2-5` 秒做试验，或改为更少的合并调用；检查 OpenAI 账户配额。
- 出现 5xx 或不可预期错误：查看 `chatmd.log` 获取请求与响应的详细信息（`chatmd.log` 在项目根目录）。

代理 / Copilot 使用提示（对自动化编码代理）
- 本 README 已包含 Copilot 指南要点：入口函数、关键约定、速率与安全注意事项。若要对代码做出修改，请优先在本地运行 `test_connection.py`。
- 避免在 PR 中引入频繁的 API 调用或在主分支直接触发大量请求。对可能产生额外请求的改动（例如修改问题列表或增加自动化测试）请先在本地验证。

反馈与迭代
- 如果你希望我把某项建议（例如把模型名抽成常量、实现更强的中断恢复、或把合并改成本地摘要）直接实现为补丁/PR，请说明优先级，我将附带简单测试与变更说明。

