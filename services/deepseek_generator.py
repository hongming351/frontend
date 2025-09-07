# -*- coding: utf-8 -*-
import requests
import re
import json
from typing import Dict, Optional, List

class DeepSeekProblemGenerator:
    def __init__(self, api_key: str):
        self.api_key = "sk-5b8aafb9e5e14b40b5bf05199b600d1e"
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.supported_models = ["deepseek-chat", "deepseek-coder"]

    def generate_programming_problem(self,
                                    knowledge_point: str,
                                    difficulty: str = "medium",
                                    model: str = "deepseek-chat",
                                    language: str = "Python",
                                    custom_requirements: List[str] = None) -> Dict:
        if model not in self.supported_models:
            raise ValueError(f"不支持的模型，可选模型：{self.supported_models}")

        # 构建基础提示词
        base_prompt = f"""请生成一道关于「{knowledge_point}」的{difficulty}难度编程题，满足以下要求：

1. 题目描述：清晰描述问题背景和要求，字数50-200字
2. 输入说明：详细说明输入格式、数据范围
3. 输出说明：明确输出要求
4. 输入输出示例：提供2组示例，格式如下
   示例1：
   输入：
   ...
   输出：
   ...
   示例2：
   输入：
   ...
   输出：
   ...
5. 测试用例：提供3组测试用例（包含边缘情况），格式：
   测试用例1：
   输入：...
   输出：...
6. 解题思路：简要说明核心思路（50-100字)
7. 参考答案：使用{language}编写完整可运行的代码，包含必要注释。
   格式要求：
   参考答案：
   ```{language}
   # 代码内容
   ...
   ```

   特别注意：
   - 如果使用C++语言，请务必包含所有必要的头文件（如iostream, string, vector等）
   - 确保include语句完整，格式如：#include <iostream> 或 #include "header.h"
   - 不要生成不完整的include语句，如 #include 后面为空
   - 不要生成HTML风格的结束标签，如</iostream>或</code>
   - 如果使用Java语言，请确保包含完整的类结构和必要的导入语句（如java.util.*, java.io.*等）
   - 代码必须能够独立编译运行，不要包含任何HTML标签或特殊符号
"""

        # 添加自定义要求
        if custom_requirements and len(custom_requirements) > 0:
            custom_reqs_text = "\n8. 自定义要求：请务必满足以下额外要求：\n"
            for i, req in enumerate(custom_requirements, 1):
                custom_reqs_text += f"   - {req}\n"
            prompt = base_prompt + custom_reqs_text
        else:
            prompt = base_prompt

        prompt += "\n请严格按照上述结构生成，不要添加额外内容，各部分用中文标题（如\"题目描述\"）开头。"

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 2000  # 增加最大长度以容纳代码
                }
            )

            print(f"\nDeepSeek API响应状态码: {response.status_code}")
            print("DeepSeek API原始返回内容:")
            print("-" * 50)
            print(response.text)
            print("-" * 50 + "\n")

            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"API调用失败: {str(e)}"}

        try:
            api_result = response.json()
            raw_content = api_result["choices"][0]["message"]["content"]
            print("从API响应中提取的题目内容:")
            print("-" * 50)
            print(raw_content)
            print("-" * 50 + "\n")

            parsed_result = self._parse_problem_content(raw_content, language)
            parsed_result["success"] = True
            parsed_result["knowledge_point"] = knowledge_point  # 添加知识点信息
            return parsed_result
        except (KeyError, ValueError) as e:
            return {
                "success": False,
                "error": f"解析结果失败: {str(e)}",
                "raw_content": raw_content
            }

    def _parse_problem_content(self, content: str, language: str) -> Dict:
        """解析题目内容，新增代码示例提取"""
        sections = {
            "description": self._extract_section(content, "题目描述"),
            "input_description": self._extract_section(content, "输入说明"),
            "output_description": self._extract_section(content, "输出说明"),
            "examples": self._extract_examples(content),
            "test_cases": self._extract_test_cases(content),
            "solution_idea": self._extract_section(content, "解题思路"),
            "reference_code": self._extract_code_example(content, language),  # 新增代码提取
            "language": language,  # 添加语言信息
            "raw_content": content
        }

        print("解析后的题目各部分内容:")
        print("-" * 50)
        for key, value in sections.items():
            if key in ["examples", "test_cases"]:
                print(f"{key}: {len(value)}条数据")
            elif key == "language":
                print(f"{key}: {value}")  # 特殊处理language字段
            else:
                print(f"{key}: {'存在' if value else '缺失'}")
        print("-" * 50 + "\n")

        # 注意：knowledge_point字段是在generate_programming_problem方法中添加的，不在这个sections字典中
        # 但会在最终返回的结果中包含

        return sections

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        pattern = rf"{section_name}：?(.*?)(?=\n\n|题目描述|输入说明|输出说明|示例|测试用例|解题思路|参考答案|$)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_examples(self, content: str) -> list:
        pattern = r"示例\d+：\n输入：(.*?)\n输出：(.*?)(?=\n\n|示例|测试用例|解题思路|参考答案|$)"
        matches = re.findall(pattern, content, re.DOTALL)
        examples = []
        for i, (input_str, output_str) in enumerate(matches, 1):
            examples.append({
                "id": i,
                "input": input_str.strip(),
                "output": output_str.strip()
            })
        return examples

    def _extract_test_cases(self, content: str) -> list:
        # More flexible pattern to match different test case formats
        pattern = r"(测试用例\d+|示例\d+|样例\d+|Case\d+)：?\s*\n?\s*输入[:：]?\s*(.*?)\n\s*输出[:：]?\s*(.*?)(?=\n\n|测试用例|解题思路|参考答案|$)"
        matches = re.findall(pattern, content, re.DOTALL)
        test_cases = []
        for i, (_, input_str, output_str) in enumerate(matches, 1):
            test_cases.append({
                "id": i,
                "input": input_str.strip(),
                "output": output_str.strip()
            })
        return test_cases

    def _extract_code_example(self, content: str, language: str) -> Optional[str]:
        """提取代码示例（支持多种格式）"""
        escaped_language = re.escape(language)
        # Match multiple possible formats:
        # 1. Markdown code blocks with language
        pattern1 = rf"参考答案：?\s*```({escaped_language}|)\s*(.*?)\s*```"
        # 2. Code blocks without language
        pattern2 = rf"参考答案：?\s*```\s*(.*?)\s*```"
        # 3. Plain indented code
        pattern3 = rf"参考答案：?(\n\s*.*?)(?=\n\n|\n\S|$)"

        # Try patterns in order
        for pattern in [pattern1, pattern2, pattern3]:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                code_content = match.group(2 if pattern in [pattern1, pattern2] else 1).strip()
                if code_content:
                    # 后处理：修复C++代码中的include问题
                    code_content = self._post_process_code(code_content, language)
                    return code_content
        return None

    def _post_process_code(self, code: str, language: str) -> str:
        """后处理生成的代码，修复常见问题"""
        if language.lower() == "c++" or language.lower() == "cpp":
            # 修复C++ include语句问题
            code = self._fix_cpp_includes(code)
        elif language.lower() == "java":
            # 修复Java import语句问题
            code = self._fix_java_imports(code)
        return code

    def _fix_cpp_includes(self, code: str) -> str:
        """修复C++代码中的include语句问题，防止生成错误的HTML标签"""
        lines = code.split('\n')
        fixed_lines = []

        for line in lines:
            line = line.strip()
            # 检查不完整的include语句
            if re.match(r'#include\s*<>\s*$', line) or re.match(r'#include\s*""\s*$', line):
                # 跳过不完整的include语句
                continue
            elif re.match(r'#include\s*<([^>]+)>\s*$', line):
                # 正常的尖括号include，保留
                fixed_lines.append(line)
            elif re.match(r'#include\s*"([^"]+)"\s*$', line):
                # 正常的双引号include，保留
                fixed_lines.append(line)
            elif line == '#include':
                # 孤立的#include语句，跳过
                continue
            elif re.match(r'</[^>]*>\s*$', line):
                # 跳过类似</html>、</code>这样的HTML结束标签
                continue
            elif re.match(r'<[^>]*>\s*$', line) and not line.startswith('#') and not 'include' in line:
                # 跳过不相关的HTML标签，但保留正常的代码行
                continue
            else:
                # 保留正常的代码行
                fixed_lines.append(line)

        # 清理空行
        result = '\n'.join(fixed_lines)
        # 移除连续的空行
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)

        return result.strip()

    def _fix_java_imports(self, code: str) -> str:
        """修复Java代码中的import语句和HTML标签问题"""
        lines = code.split('\n')
        fixed_lines = []

        for line in lines:
            line = line.strip()
            # 检查不完整的import语句
            if re.match(r'import\s*;\s*$', line):
                # 跳过不完整的import语句
                continue
            elif re.match(r'import\s+\w+(\.\w+)*(\.\*)?\s*;', line):
                # 正常的import语句，保留
                fixed_lines.append(line)
            elif re.match(r'import\s+\w+', line) and ';' not in line:
                # 不完整的import语句，跳过
                continue
            elif line == 'import':
                # 孤立的import语句，跳过
                continue
            elif re.match(r'</[^>]*>\s*$', line) or re.match(r'<[^>]*>\s*$', line):
                # 跳过HTML标签
                continue
            else:
                # 保留其他正常的代码行
                fixed_lines.append(line)

        # 清理空行
        result = '\n'.join(fixed_lines)
        result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)

        return result.strip()

    def _fix_java_imports(self, code: str) -> str:
        """修复Java代码中的import语句问题"""
        lines = code.split('\n')
        fixed_lines = []

        for line in lines:
            # 检查不完整的import语句
            if re.match(r'import\s*;\s*$', line.strip()):
                # 跳过不完整的import语句
                continue
            elif re.match(r'import\s+\w+(\.\w+)*(\.\*)?\s*;', line.strip()):
                # 正常的import语句，保留
                fixed_lines.append(line)
            elif line.strip() == 'import':
                # 孤立的import语句，跳过
                continue
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def build_multi_lang_prompt(self, problem_desc: str, target_lang: str) -> str:
        """构建多语言代码生成提示词"""
        lang_map = {
            "python": "Python",
            "cpp": "C++",
            "java": "Java"
        }

        display_lang = lang_map.get(target_lang, target_lang)

        prompt = f"""根据以下题目描述，生成{display_lang}语言的完整解决方案代码：

{problem_desc}

要求：
1. 代码必须完整、可运行
2. 包含必要的注释说明
3. 使用标准的{display_lang}语法和最佳实践
4. 正确处理输入输出格式
5. 包含必要的头文件/导入语句

请直接输出代码，不要包含额外的解释文字。代码应该用```{target_lang}```标记包裹。
"""
        return prompt

    def generate_choice_question(self,
                                knowledge_point: str,
                                difficulty: str = "medium",
                                model: str = "deepseek-chat",
                                language: str = "Python",
                                custom_requirements: List[str] = None) -> Dict:
        """生成选择题"""
        if model not in self.supported_models:
            raise ValueError(f"不支持的模型，可选模型：{self.supported_models}")

        # 构建基础提示词
        base_prompt = f"""请生成一道关于「{knowledge_point}」在{language}语言中的{difficulty}难度选择题，满足以下要求：

1. 题目描述：清晰描述问题，字数30-100字，专注于{language}语言特性
2. 选项：提供4个选项（A、B、C、D），每个选项内容清晰明确，与{language}语言相关
3. 正确答案：明确标注正确答案（A、B、C、D中的一个）
4. 解析：提供详细的解析说明，解释为什么这个答案是正确的，特别是与{language}语言相关的理由
"""

        # 添加自定义要求
        if custom_requirements and len(custom_requirements) > 0:
            custom_reqs_text = "\n5. 自定义要求：请务必满足以下额外要求：\n"
            for i, req in enumerate(custom_requirements, 1):
                custom_reqs_text += f"   - {req}\n"
            prompt = base_prompt + custom_reqs_text
        else:
            prompt = base_prompt

        prompt += """
格式要求：
题目描述：
[题目内容]

选项：
["选项A内容", "选项B内容", "选项C内容", "选项D内容"]

正确答案：
[正确答案数字，如0表示第一个选项]

解析：
[详细解析内容]

请严格按照上述结构生成，不要添加额外内容。
"""

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 1000
                }
            )

            response.raise_for_status()
            api_result = response.json()
            raw_content = api_result["choices"][0]["message"]["content"]

            parsed_result = self._parse_choice_question_content(raw_content)
            parsed_result["success"] = True
            parsed_result["type"] = "choice"
            parsed_result["language"] = language
            parsed_result["knowledge_point"] = knowledge_point
            return parsed_result

        except Exception as e:
            return {"success": False, "error": f"生成选择题失败：{str(e)}"}

    def generate_judgment_question(self,
                                  knowledge_point: str,
                                  difficulty: str = "medium",
                                  model: str = "deepseek-chat",
                                  language: str = "Python",
                                  custom_requirements: List[str] = None) -> Dict:
        """生成判断题"""
        if model not in self.supported_models:
            raise ValueError(f"不支持的模型，可选模型：{self.supported_models}")

        # 构建基础提示词
        base_prompt = f"""请生成一道关于「{knowledge_point}」在{language}语言中的{difficulty}难度判断题，满足以下要求：

1. 题目描述：清晰描述陈述内容，字数20-80字，专注于{language}语言特性
2. 正确答案：明确标注正确答案（正确/错误）
3. 解析：提供详细的解析说明，解释为什么这个答案是正确的，特别是与{language}语言相关的理由
"""

        # 添加自定义要求
        if custom_requirements and len(custom_requirements) > 0:
            custom_reqs_text = "\n4. 自定义要求：请务必满足以下额外要求：\n"
            for i, req in enumerate(custom_requirements, 1):
                custom_reqs_text += f"   - {req}\n"
            prompt = base_prompt + custom_reqs_text
        else:
            prompt = base_prompt

        prompt += """
格式要求：
题目描述：
[题目内容]

正确答案：
[正确/错误]

解析：
[详细解析内容]

请严格按照上述结构生成，不要添加额外内容。
"""

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 800
                }
            )

            response.raise_for_status()
            api_result = response.json()
            raw_content = api_result["choices"][0]["message"]["content"]

            parsed_result = self._parse_judgment_question_content(raw_content)
            parsed_result["success"] = True
            parsed_result["type"] = "judgment"
            parsed_result["language"] = language
            parsed_result["knowledge_point"] = knowledge_point
            return parsed_result

        except Exception as e:
            return {"success": False, "error": f"生成判断题失败：{str(e)}"}

    def _parse_choice_question_content(self, content: str) -> Dict:
        """解析选择题内容"""
        sections = {
            "description": self._extract_section(content, "题目描述"),
            "options": self._extract_choice_options(content),
            "correct_answer": self._extract_section(content, "正确答案"),
            "solution_idea": self._extract_section(content, "解析"),
            "raw_content": content
        }

        # 处理正确答案：保持数字索引格式，前端期望的是索引而不是选项文本
        correct_answer_str = sections.get("correct_answer", "").strip()
        options = sections.get("options", [])

        if correct_answer_str and options:
            try:
                # 尝试将正确答案转换为整数索引
                correct_index = int(correct_answer_str)
                if 0 <= correct_index < len(options):
                    # 保持数字索引格式，前端需要用索引来比较
                    sections["correct_answer"] = str(correct_index)
                else:
                    # 如果索引超出范围，保持原值
                    pass
            except ValueError:
                # 如果不是数字，保持原值
                pass

        return sections

    def _parse_judgment_question_content(self, content: str) -> Dict:
        """解析判断题内容"""
        sections = {
            "description": self._extract_section(content, "题目描述"),
            "correct_answer": self._extract_section(content, "正确答案"),
            "solution_idea": self._extract_section(content, "解析"),
            "raw_content": content
        }
        return sections

    def _extract_choice_options(self, content: str) -> List[str]:
        """提取选择题选项，返回列表格式"""
        # 首先尝试匹配列表格式：["选项1", "选项2", "选项3", "选项4"]
        list_pattern = r'\["([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\]'
        list_match = re.search(list_pattern, content, re.DOTALL)

        if list_match:
            # 返回列表格式的选项
            return [list_match.group(1), list_match.group(2), list_match.group(3), list_match.group(4)]

        # 如果没找到列表格式，尝试匹配传统格式（作为后备）
        pattern = r"(A|B|C|D)\.\s*(.*?)(?=\n[A-D]\.|\n\n|$)"
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            # 转换为列表格式
            return [text.strip() for _, text in matches]

        # 如果都没有找到，返回空列表
        return []