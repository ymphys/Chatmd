import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import time

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
        with open("abstract_conclusion.md", 'w', encoding='utf-8') as f:
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
    
def chatgpt_interpretation(md_content, questions, openai_api_key):
    """
    使用ChatGPT对md内容进行解读
    questions: 固定问题列表
    结果按md格式输出保存为"{md-filename}-interp.md"
    """
    if not md_content:
        print("No content to interpret")
        return
    
    # OpenAI API设置
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    # 构建解读结果
    interpretation = "# 文档解读\n\n"
    
    for question in questions:
        try:
            # 构建API请求
            data = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "你是一个学术文献分析专家，请基于提供的文档内容回答问题。"},
                    {"role": "user", "content": f"基于以下文档内容：\n\n{md_content['content']}\n\n问题：{question}"}
                ],
                "temperature": 0.7
            }
            
            # 发送请求
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                # 将问题和回答添加到解读结果中
                interpretation += f"## {question}\n\n{answer}\n\n"
            else:
                print(f"Error with OpenAI API: {response.status_code}")
                interpretation += f"## {question}\n\n无法获取答案，API调用失败。\n\n"
                
            # 添加简单的速率限制
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing question '{question}': {str(e)}")
            interpretation += f"## {question}\n\n处理此问题时发生错误。\n\n"
    
    # 保存解读结果
    try:
        output_path = "interpretation_results.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(interpretation)
        print(f"Interpretation saved to {output_path}")
    except Exception as e:
        print(f"Error saving interpretation: {str(e)}")
        
    return interpretation

def answer_questions(md_content, user_questions, openai_api_key):
    """
    使用ChatGPT结合md内容进行问答
    user_questions: 用户自定义问题列表
    结果按md格式输出保存，直接续写在"{md-filename}-interp.md"后面
    """
    if not md_content:
        print("No content for Q&A")
        return
        
    # OpenAI API设置
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    
    # 构建问答结果
    qa_results = "\n\n# 用户问答\n\n"
    
    for question in user_questions:
        try:
            # 构建API请求
            data = {
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": "你是一个专业的学术助手，请基于文档内容回答问题，如果文档中没有相关信息，请明确指出。"},
                    {"role": "user", "content": f"基于以下文档内容：\n\n{md_content['content']}\n\n问题：{question}"}
                ],
                "temperature": 0.7
            }
            
            # 发送请求
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                qa_results += f"## Q: {question}\n\nA: {answer}\n\n"
            else:
                print(f"Error with OpenAI API: {response.status_code}")
                qa_results += f"## Q: {question}\n\nA: 无法获取答案，API调用失败。\n\n"
                
            # 添加简单的速率限制
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing question '{question}': {str(e)}")
            qa_results += f"## Q: {question}\n\nA: 处理此问题时发生错误。\n\n"
    
    # 追加问答结果到解读文件
    try:
        with open("interpretation_results.md", 'a', encoding='utf-8') as f:
            f.write(qa_results)
        print("Q&A results appended to interpretation_results.md")
    except Exception as e:
        print(f"Error saving Q&A results: {str(e)}")
        
    return qa_results

def main():
    OPENAI_API_KEY = load()
    # print(OPENAI_API_KEY)
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
if __name__ == "__main__":
    main()
