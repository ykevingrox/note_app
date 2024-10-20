import dashscope
from http import HTTPStatus
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('DASHSCOPE_API_KEY')
dashscope.api_key = API_KEY

def call_ai_model(content, prompt):
    try:
        messages = [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': f"Content: {content}\n\nPrompt: {prompt}"}
        ]
        
        response = dashscope.Generation.call(
            model='qwen-turbo',
            messages=messages,
        )
        
        if response.status_code == HTTPStatus.OK:
            return response.output.text
        else:
            print(f'调用失败: {response.code}, {response.message}')
            return None
    except Exception as e:
        print(f"调用 AI 模型时出错: {e}")
        return None
