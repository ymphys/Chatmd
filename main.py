import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import time
import logging

# Logging: brief info to console, detailed debug to file
LOG_FILE = "./output/chatmd.log"
logger = logging.getLogger("chatmd")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)

def load():
    """
    加载环境变量中的 OpenAI API Key
    """
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("未找到 OPENAI_API_KEY 环境变量，请确保已设置系统环境变量")
    return OPENAI_API_KEY

def extract_md_content(file_path):
    """
    提取md文件中的摘要和结论
    关键词： 摘要, 结论, Abstract, Conclusion
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 定义关键词列表
        abstract_keywords = ['摘要', 'Abstract']
        conclusion_keywords = ['结论', 'Conclusion']
        
        # 提取摘要
        abstract = None
        for keyword in abstract_keywords:
            if keyword in content:
                # 查找关键词后的内容
                start_idx = content.find(keyword) + len(keyword)
                # 查找下一个标题（以#开头的行）
                next_section = content.find('\n#', start_idx)
                if next_section == -1:
                    abstract = content[start_idx:].strip()
                else:
                    abstract = content[start_idx:next_section].strip()
                break
        
        # 提取结论
        conclusion = None
        for keyword in conclusion_keywords:
            if keyword in content:
                start_idx = content.find(keyword) + len(keyword)
                next_section = content.find('\n#', start_idx)
                if next_section == -1:
                    conclusion = content[start_idx:].strip()
                else:
                    conclusion = content[start_idx:next_section].strip()
                break
        md_content = {
            'content': content,  # 完整内容
            'abstract': abstract,
            'conclusion': conclusion
        }
        with open("./output/abstract_conclusion.md", 'w', encoding='utf-8') as f:
            f.write("# 摘要与结论\n\n")
            if md_content['abstract']:
                f.write("## Abstract\n\n")
                f.write(f"{md_content['abstract']}\n\n")
            if md_content['conclusion']:
                f.write("## Conclusion\n\n")
                f.write(f"{md_content['conclusion']}\n\n")
        print("Abstract and conclusion saved to abstract_conclusion.md")
        return md_content
    except Exception as e:
        print(f"Error reading or processing file {file_path}: {str(e)}")
        return None
    
def split_into_chunks(content, chunk_size=3000):
    """
    将内容分成多个块，每块不超过指定字符数
    """
    return [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

def _post_with_retries(url, headers, json_data, max_retries=4, base_delay=1):
    """
    发送 POST 请求，遇到 429/5xx 时重试（指数退避），返回 requests.Response
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
            if resp.status_code == 200:
                logger.debug(f"POST {url} success (200)")
                return resp
            # 对于429和常见5xx做重试
            if resp.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"OpenAI API returned {resp.status_code}, attempt {attempt}/{max_retries}")
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
                    continue
            # 非重试场景或最后一次重试，直接返回响应
            logger.debug(f"POST {url} returned status {resp.status_code}")
            return resp
        except requests.RequestException as e:
            logger.error(f"Request exception on attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** (attempt - 1)))
                continue
            raise


def load_existing_answers(path="./output/interpretation_results.md"):
    """
    读取已有的 interpretation_results.md，提取已经存在的问答问题（以避免重复处理）
    返回一个 set，包含已回答的问题文本（尽量保持与问题源文本一致的匹配）
    """
    existing = set()
    if not os.path.exists(path):
        return existing
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('## '):
                qline = line[3:].strip()
                # 支持两种形式："Q: ..." 或 直接问题文本
                if qline.startswith('Q:'):
                    q = qline[2:].strip()
                else:
                    q = qline
                if q:
                    existing.add(q)
    except Exception as e:
        logger.error(f"Failed to read existing answers from {path}: {e}")
    return existing

def chatgpt_interpretation(md_content, questions, openai_api_key):
    """
    使用ChatGPT对md内容进行解读
    questions: 固定问题列表
    结果按md格式输出保存为"{md-filename}-interp.md"
    """
    if not md_content:
        logger.info("No content to interpret")
        return
    
    # OpenAI API设置
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    # 读取已存在的答案，避免重复处理同一问题
    existing = load_existing_answers()

    # 收集新生成的部分，最后统一写入/追加到 interpretation_results.md
    new_sections = ""

    for question in questions:
        if question in existing:
            logger.info(f"Skipping interpretation for question (already present): {question}")
            continue
        try:
            # 按块发送，每块单独获取针对该块的回答片段
            chunks = split_into_chunks(md_content['content'], chunk_size=3000)
            partial_answers = []
            for i, chunk in enumerate(chunks, start=1):
                data = {
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "system", "content": "你是一个学术文献分析专家，请基于提供的文档内容回答问题。"},
                        {"role": "user", "content": f"文档片段 {i}/{len(chunks)}：\n\n{chunk}\n\n问题：{question}"}
                    ],
                    "temperature": 0.7
                }
                resp = _post_with_retries("https://api.openai.com/v1/chat/completions", headers, data)
                if resp is None:
                    partial_answers.append("[请求失败，未获得该片段回答]")
                    logger.warning(f"No response for chunk {i}/{len(chunks)} for question: {question}")
                elif resp.status_code == 200:
                    text = resp.json()['choices'][0]['message']['content'].strip()
                    partial_answers.append(text)
                    logger.info(f"Chunk {i}/{len(chunks)} answered for question: {question}")
                    logger.debug(f"Chunk {i} preview: {text[:120].replace('\n', ' ')}")
                else:
                    logger.error(f"Error with OpenAI API for chunk {i}: {resp.status_code}")
                    partial_answers.append(f"[片段调用失败：{resp.status_code}]")
                time.sleep(1)  # 保持速率限制
            # 把各片段回答合并为最终答案（再调用一次让模型整合）
            synth_prompt = "请基于下面各片段回答，综合出一个简洁、连贯且基于文档的最终回答；若文档未提供信息请明确说明。\n\n" + "\n\n---\n\n".join(partial_answers)
            synth_data = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "你负责把分片回答合并成最终答案。"},
                    {"role": "user", "content": f"{synth_prompt}\n\n问题：{question}"}
                ],
                "temperature": 0.0
            }
            resp = _post_with_retries("https://api.openai.com/v1/chat/completions", headers, synth_data)
            if resp and resp.status_code == 200:
                final_answer = resp.json()['choices'][0]['message']['content'].strip()
                logger.info(f"Synthesized final answer for question: {question}")
                new_sections += f"## {question}\n\n{final_answer}\n\n"
            else:
                logger.error(f"Failed to synthesize answer for question '{question}': {resp.status_code if resp else 'no response'}")
                new_sections += f"## {question}\n\n无法获取答案，API调用失败。\n\n"
        except Exception as e:
            logger.exception(f"Error processing question '{question}': {e}")
            new_sections += f"## {question}\n\n处理此问题时发生错误。\n\n"
    # 将新生成部分追加到文件（若无则创建）
    output_path = "./output/interpretation_results.md"
    try:
        if new_sections:
            if not os.path.exists(output_path):
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("# 文档解读\n\n")
                    f.write(new_sections)
            else:
                with open(output_path, 'a', encoding='utf-8') as f:
                    f.write(new_sections)
            logger.info(f"Interpretation answers appended to {output_path}")
        else:
            logger.info("No new interpretation sections to write (all questions were already present).")
    except Exception as e:
        logger.error(f"Error saving interpretation: {e}")

    return new_sections

def answer_questions(md_content, user_questions, openai_api_key):
    """
    使用ChatGPT结合md内容进行问答
    user_questions: 用户自定义问题列表
    结果按md格式输出保存，直接续写在"{md-filename}-interp.md"后面
    """
    if not md_content:
        logger.info("No content for Q&A")
        return
        
    # OpenAI API设置
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    # 读取已存在的答案，避免重复问答
    existing = load_existing_answers()
    qa_results = "\n\n# 用户问答\n\n"

    for question in user_questions:
        if question in existing:
            logger.info(f"Skipping user question (already present): {question}")
            continue
        try:
            chunks = split_into_chunks(md_content['content'], chunk_size=3000)
            partials = []
            for i, chunk in enumerate(chunks, start=1):
                data = {
                    "model": "gpt-4-turbo-preview",
                    "messages": [
                        {"role": "system", "content": "你是一个专业的学术助手，请基于文档内容回答问题，如果文档中没有相关信息，请明确指出。"},
                        {"role": "user", "content": f"文档片段 {i}/{len(chunks)}：\n\n{chunk}\n\n问题：{question}"}
                    ],
                    "temperature": 0.7
                }
                resp = _post_with_retries("https://api.openai.com/v1/chat/completions", headers, data)
                if resp and resp.status_code == 200:
                    text = resp.json()['choices'][0]['message']['content'].strip()
                    partials.append(text)
                    logger.info(f"Chunk {i}/{len(chunks)} answered for user question: {question}")
                    logger.debug(f"Chunk preview: {text[:120].replace('\n', ' ')}")
                else:
                    logger.error(f"Error with OpenAI API for chunk {i}: {resp.status_code if resp else 'no response'}")
                    partials.append(f"[片段调用失败：{resp.status_code if resp else 'no response'}]")
                time.sleep(1)
            # 合并片段回答
            synth_prompt = "请把以下片段回答整合为一个针对问题的最终答案：\n\n" + "\n\n---\n\n".join(partials)
            synth_data = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "整合并精简以下片段回答，输出最终答复。"},
                    {"role": "user", "content": f"{synth_prompt}\n\n问题：{question}"}
                ],
                "temperature": 0.0
            }
            resp = _post_with_retries("https://api.openai.com/v1/chat/completions", headers, synth_data)
            if resp and resp.status_code == 200:
                answer = resp.json()['choices'][0]['message']['content'].strip()
                logger.info(f"Synthesized final answer for user question: {question}")
                qa_results += f"## Q: {question}\n\nA: {answer}\n\n"
            else:
                logger.error(f"Failed to synthesize final answer for user question '{question}': {resp.status_code if resp else 'no response'}")
                qa_results += f"## Q: {question}\n\nA: 无法获取答案，API调用失败。\n\n"
        except Exception as e:
            logger.exception(f"Error processing user question '{question}': {e}")
            qa_results += f"## Q: {question}\n\nA: 处理此问题时发生错误。\n\n"
    
    # 追加问答结果到解读文件
    try:
        if qa_results.strip():
            with open("./output/interpretation_results.md", 'a', encoding='utf-8') as f:
                f.write(qa_results)
            logger.info("Q&A results appended to interpretation_results.md")
        else:
            logger.info("No new Q&A results to append (all user questions already present).")
    except Exception as e:
        logger.error(f"Error saving Q&A results: {e}")
        
    return qa_results

def main():
    logger.info("Starting Chatmd main process")
    OPENAI_API_KEY = load()
    md_file_path = "./mds/Relativistic electron beam propagation in the Earth's magnetosphere_MinerU__20251025025446.md"
    md_content = extract_md_content(md_file_path)

    fixed_questions = [
        "请总结该文档的主要内容。",
        "该文档的关键结论是什么？",
        "有哪些重要的数据或发现？"
    ]
    chatgpt_interpretation(md_content, fixed_questions, OPENAI_API_KEY)
    user_questions = [
        "该文档中提到的方法有哪些优缺点？",
        "这些结论在实际应用中有哪些潜在影响？"]
    answer_questions(md_content, user_questions, OPENAI_API_KEY)
    logger.info("Chatmd main process finished")
if __name__ == "__main__":
    main()
