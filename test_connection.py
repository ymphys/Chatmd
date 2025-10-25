import requests
from dotenv import load_dotenv
import os

def load():
    """
    加载环境变量中的 OpenAI API Key
    """
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("未找到 OPENAI_API_KEY 环境变量，请确保已设置系统环境变量")
    return OPENAI_API_KEY

def test_openai_connection(api_key):
    """测试与 OpenAI API 的连接"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 使用最简单的请求测试连接
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ API 连接成功")
            return True
        elif response.status_code == 429:
            print("❌ 触发限流，请稍后重试")
            print(response.json())  # 打印详细错误信息
        else:
            print(f"❌ API 连接失败: {response.text}")
        return False
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        return False

def main():
    OPENAI_API_KEY = load()
    
    # 测试 API 连接
    if not test_openai_connection(OPENAI_API_KEY):
        print("API 连接测试失败，程序退出")
        return