from flask import Blueprint, jsonify, request, session
from database import db
import logging
import requests
import json
import re
from config import Config

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)

def call_deepseek_api(prompt, max_tokens=2000):
    """调用DeepSeek API生成内容"""
    try:
        headers = {
            'Authorization': f'Bearer {Config.DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一个专业的编程题目生成助手，擅长生成各种编程题目，包括算法题、数据结构题、编程练习题等。请严格按照要求的格式生成题目。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens,
            'temperature': 0.7
        }
        
        response = requests.post(Config.DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
    
    except requests.exceptions.RequestException as e:
        logger.error(f"DeepSeek API调用失败: {e}")
        raise Exception(f"API调用失败: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"DeepSeek API响应解析失败: {e}")
        raise Exception("API响应解析失败")

def parse_problem_from_ai_response(ai_response):
    """从AI响应中解析题目信息"""
    try:
        # 使用正则表达式提取各个部分
        title_match = re.search(r'标题[:：]\s*(.+)', ai_response)
        description_match = re.search(r'描述[:：]\s*([\s\S]+?)(?=输入格式[:：]|输出格式[:：]|样例输入[:：]|样例输出[:：]|难度[:：]|标签[:：]|$)', ai_response)
        input_format_match = re.search(r'输入格式[:：]\s*([\s\S]+?)(?=输出格式[:：]|样例输入[:：]|样例输出[:：]|难度[:：]|标签[:：]|$)', ai_response)
        output_format_match = re.search(r'输出格式[:：]\s*([\s\S]+?)(?=样例输入[:：]|样例输出[:：]|难度[:：]|标签[:：]|$)', ai_response)
        sample_input_match = re.search(r'样例输入[:：]\s*([\s\S]+?)(?=样例输出[:：]|难度[:：]|标签[:：]|$)', ai_response)
        sample_output_match = re.search(r'样例输出[:：]\s*([\s\S]+?)(?=难度[:：]|标签[:：]|$)', ai_response)
        difficulty_match = re.search(r'难度[:：]\s*(.+)', ai_response)
        tags_match = re.search(r'标签[:：]\s*(.+)', ai_response)
        
        # 提取测试用例（如果有）
        test_cases = []
        test_case_pattern = r'测试用例\s*\d+[:：]\s*输入[:：]\s*([\s\S]+?)\s*输出[:：]\s*([\s\S]+?)(?=测试用例\s*\d+[:：]|$)'
        test_case_matches = re.finditer(test_case_pattern, ai_response)
        
        for match in test_case_matches:
            test_cases.append({
                'input': match.group(1).strip(),
                'expected_output': match.group(2).strip()
            })
        
        # 如果没有找到测试用例，尝试从样例中创建一个
        if not test_cases and sample_input_match and sample_output_match:
            test_cases.append({
                'input': sample_input_match.group(1).strip(),
                'expected_output': sample_output_match.group(1).strip()
            })
        
        problem_data = {
            'title': title_match.group(1).strip() if title_match else 'AI生成的题目',
            'description': description_match.group(1).strip() if description_match else '',
            'input_format': input_format_match.group(1).strip() if input_format_match else '',
            'output_format': output_format_match.group(1).strip() if output_format_match else '',
            'sample_input': sample_input_match.group(1).strip() if sample_input_match else '',
            'sample_output': sample_output_match.group(1).strip() if sample_output_match else '',
            'difficulty': difficulty_match.group(1).strip() if difficulty_match else '中等',
            'tags': [tag.strip() for tag in tags_match.group(1).split(',')] if tags_match else ['AI生成'],
            'test_cases': test_cases
        }
        
        return problem_data
    
    except Exception as e:
        logger.error(f"解析AI响应失败: {e}")
        raise Exception("解析AI响应失败")

@ai_bp.route('/api/ai/generate-problem', methods=['POST'])
def generate_problem():
    """使用AI生成编程题目"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        
        # 验证必填字段
        if 'prompt' not in data:
            return jsonify({"success": False, "message": "缺少提示词"}), 400
        
        prompt = data['prompt']
        language = data.get('language', 'Python')
        difficulty = data.get('difficulty', '中等')
        
        # 构建完整的提示词
        full_prompt = f"""请生成一个{difficulty}难度的{language}编程题目。

要求：
1. 题目应该包含完整的题目描述、输入格式、输出格式、样例输入、样例输出
2. 提供至少2个测试用例（包括输入和期望输出）
3. 难度级别：{difficulty}
4. 编程语言：{language}

用户需求：{prompt}

请按照以下格式返回：
标题: [题目名称]
描述: [详细的题目描述]
输入格式: [输入格式说明]
输出格式: [输出格式说明]
样例输入: [样例输入数据]
样例输出: [样例输出数据]
难度: [简单/中等/困难]
标签: [逗号分隔的标签，如算法,数据结构,字符串]

测试用例1:
输入: [测试输入1]
输出: [期望输出1]

测试用例2:
输入: [测试输入2]
输出: [期望输出2]"""
        
        # 调用DeepSeek API
        ai_response = call_deepseek_api(full_prompt)
        
        # 解析AI响应
        problem_data = parse_problem_from_ai_response(ai_response)
        
        return jsonify({
            "success": True,
            "message": "题目生成成功",
            "data": problem_data,
            "raw_response": ai_response  # 用于调试
        })
        
    except Exception as e:
        logger.error(f"AI生成题目失败: {e}")
        return jsonify({"success": False, "message": f"生成题目失败: {str(e)}"}), 500

@ai_bp.route('/api/ai/save-generated-problem', methods=['POST'])
def save_generated_problem():
    """保存AI生成的题目"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['title', 'description', 'input_format', 'output_format', 
                          'sample_input', 'sample_output', 'difficulty', 'test_cases']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"缺少必填字段: {field}"}), 400
        
        # 处理标签和测试用例
        tags = ','.join(data.get('tags', ['AI生成']))
        test_cases = json.dumps(data['test_cases'])

        # 插入题目（使用实际的数据库字段名）
        sql = """
            INSERT INTO problems (title, description, input_description, output_description, 
                                 sample_input, sample_output, difficulty, tags, test_cases, 
                                 created_by, is_ai_generated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """
        params = [
            data['title'], data['description'], data['input_format'], data['output_format'],
            data['sample_input'], data['sample_output'], data['difficulty'], tags,
            test_cases, session['user_id']
        ]
        problem_id = db.execute_update(sql, params)

        return jsonify({
            "success": True, 
            "message": "题目保存成功", 
            "problem_id": problem_id
        }), 201
        
    except Exception as e:
        logger.error(f"保存AI生成题目失败: {e}")
        return jsonify({"success": False, "message": "保存题目失败"}), 500

@ai_bp.route('/api/ai/code-assistant', methods=['POST'])
def code_assistant():
    """代码助手：获取编程帮助和解释"""
    try:
        # 检查用户是否登录
        if 'user_id' not in session:
            return jsonify({
                "success": False, 
                "message": "请先登录",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        
        if 'question' not in data:
            return jsonify({"success": False, "message": "缺少问题内容"}), 400
        
        question = data['question']
        code_context = data.get('code', '')
        language = data.get('language', 'Python')
        
        prompt = f"""用户正在学习{language}编程，遇到了以下问题：
问题：{question}

{"代码上下文：" + code_context if code_context else "没有提供具体代码"}

请提供专业、清晰的解答，包括：
1. 问题的原因分析
2. 解决方案和代码示例
3. 相关的编程概念解释
4. 最佳实践建议

请用中文回答，保持专业且易于理解。"""
        
        # 调用DeepSeek API
        response = call_deepseek_api(prompt)
        
        return jsonify({
            "success": True,
            "data": {
                "answer": response
            }
        })
        
    except Exception as e:
        logger.error(f"代码助手失败: {e}")
        return jsonify({"success": False, "message": f"获取帮助失败: {str(e)}"}), 500
