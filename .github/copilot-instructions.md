# Copilot 指南

面向自动化编码代理的精简提示，帮助快速理解并修改 Chatmd 脚本。

## 核心流程
- 入口：`main.py`，脚本式执行；无包结构。
- `load()` 读取 `OPENAI_API_KEY` 环境变量，未调用 `load_dotenv()`。
- `read_md_content()` 按路径载入 Markdown 全文，返回字典 `{'content': ...}`。
- `split_into_chunks()` 按 100000 字符的默认大小切分文本；调用处可以覆盖参数。
- `chatgpt_interpretation()` 对每个问题遍历片段，逐片调用 GPT-4 Turbo；多片段时再发起一次合并请求，单片段直接使用片段回答。
- `load_existing_answers()` 扫描 `output/interpretation_results.md` 中所有以 `## ` 开头的标题，用于避免重复提问。
- `main()` 配置单一 Markdown 文件路径和问题列表，调用 `chatgpt_interpretation()` 并写日志。

## 文件与输出
- 输入示例在 `mds/` 目录；`md_file_path` 目前硬编码。
- 输出文件固定为 `output/interpretation_results.md`（追加模式，必要时会新建并写入 `# 文档解读` 标题）。
- 详细日志位于 `output/chatmd.log`；终端仅打印 INFO 级别。

## 速率与费用控制
- `_post_with_retries()` 对 `429/5xx` 做指数退避，最多 4 次重试；每个片段请求后 `time.sleep(1)`。
- 响应包含 `usage` 时会记录 token 用量与估算费用，帮助评估问题列表或分片策略的成本。
- 如果遇到速率限制，可考虑增大 `chunk_size`、减少问题数量或拉长休眠间隔。

## 修改建议
- 若要支持批量文件或自定义问题集，可在 `main()` 中循环文件列表，或接受命令行参数。
- 如需从 `.env` 自动加载 key，可在 `main()` 开头调用 `load_dotenv()`。
- 模型名称在多个调用点硬编码为 `gpt-4-turbo-preview`，适合提取为常量以便统一修改。

## 注意事项
- 不要在仓库中写入 API Key； `.gitignore` 已排除 `.env`。
- 任何会触发大量 API 调用的改动请在本地验证后再提交。
