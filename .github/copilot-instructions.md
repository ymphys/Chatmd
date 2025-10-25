# Copilot 指南 — Chatmd 仓库（快速上手）

以下为针对自动化编码代理（Copilot / AI 代码助手）在本仓库中应遵循的可执行说明，关注点为立刻可用的信息和可修改的代码位置。

1. 代码入口与核心职责
- 入口：`main.py`（脚本式工具，非 web 服务）。主要职责：读取 `mds/` 下的 md 文件、提取摘要/结论、按块调用 OpenAI Chat 接口合成解读并写入 `abstract_conclusion.md` / `interpretation_results.md`。
- 关键函数：`load()`（读取环境变量 `OPENAI_API_KEY`）、`extract_md_content(path)`（提取摘要/结论）、`split_into_chunks(content, chunk_size=3000)`、`_post_with_retries(...)`、`chatgpt_interpretation(...)`、`answer_questions(...)`。

2. 运行与调试（在 macOS / zsh）
- 依赖：Python >= 3.12（见 `pyproject.toml`），主要包：`requests`、`dotenv`。
- 快速命令：
  - `python test_connection.py` — 验证 OpenAI API key 与网络是否可用（先设置 `OPENAI_API_KEY`）。
  - `python main.py` — 执行主流程，会读取 `mds/` 指定文件并写入输出文件。

3. 项目约定与可发现行为（对 AI 代理重要）
- 配置来源：项目当前从系统环境变量读取 `OPENAI_API_KEY`（`load()`）；仓库未自动加载 `.env` 为默认行为，若更改请在 PR 中标注。
- 分片策略：使用 `chunk_size=3000`（在 `split_into_chunks` 中硬编码）。这会直接影响 API 调用次数与速率。
- 重试策略：`_post_with_retries` 对 429/5xx 做指数退避（`base_delay=1`, `max_retries=4`）。对速率问题的快速修复点：增加片段间 `time.sleep`（当前为 1s）或改用本地合并策略以减少合并轮调用。
- 输出文件：`abstract_conclusion.md` 和 `interpretation_results.md`（均写入仓库根目录）。

4. 速率与费用敏感点（必须注意）
- 每个文档会按 chunk 多次调用模型，且在每个问题上会做一次“合并”调用（在 `chatgpt_interpretation` / `answer_questions` 中）。在修改模型或问题列表前，请评估会产生的额外请求数。
- 遇到 429：优先避免频繁修改并直接推送到主分支；先本地运行 `test_connection.py`，在本地将 `time.sleep(1)` 提高到 `2-5` 秒做快速试验。

5. 可直接修改/建议修补点（举例）
- 若想减少调用次数：将“分片 -> 每片调用 -> 再次调用合并”改为“分片 -> 每片调用（或本地摘要） -> 客户端拼接 -> 仅在必要时调用模型精炼”。参考 `chatgpt_interpretation` 中 `partial_answers` 的处理位置。
- 把模型名抽成常量：在文件顶部定义 `MODEL = "gpt-4-turbo-preview"`，避免在多个函数中硬编码。
- 增强调试：让 `_post_with_retries` 在非 200 响应时打印 `resp.status_code` 与 `resp.text`（当前已有基础日志，但可扩展为 debug 级别）。

6. 安全与提交规则
- 不要在仓库中写入或提交任何 API keys（仓库 `.gitignore` 已屏蔽 `.env`）。
- 在提交会触发 API 调用的改动前，先运行 `python test_connection.py` 并确认本地 key 与网络正常。

7. 参考文件（首选检查顺序）
- `main.py` — 阅读函数签名与调用流（必读）。
- `README.md` — 已包含针对本项目的使用说明（可合并到 copilot 指令中）。
- `pyproject.toml` — 查看 Python 版本与依赖声明。
- `mds/` — 示例输入文件位置（检查具体 md 的结构以了解标题/关键词提取是否稳健）。

如果你需要我把某个建议直接实现为补丁（例如把模型名抽成常量、或把合并改成本地拼接的具体实现），请告诉我优先级；我会生成对应的代码补丁与测试变更。是否要我现在把上述内容写入仓库（我已完成）并进行一次 PR 风格改动？
