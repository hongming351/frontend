# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, session
import os
import logging
import subprocess
import tempfile
import json
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_problems_bp = Blueprint('ai_problems', __name__, url_prefix='/api/ai/problems')

# 处理AI返回结果的函数
def process_ai_response(ai_result, question_type='programming'):
    # 确保从AI结果中提取标题，如果没有则生成一个
    title = ai_result.get('title') or generate_title(ai_result.get('description'))

    # 根据题目类型返回不同的字段结构
    base_fields = {
        'title': title,  # 确保title不为空
        'description': ai_result.get('description'),
        'solution_idea': ai_result.get('solution_idea', '')
    }

    if question_type == 'programming':
        # 编程题特有字段
        return {
            **base_fields,
            'input_description': ai_result.get('input_description'),
            'output_description': ai_result.get('output_description'),
            'test_cases': ai_result.get('test_cases', []),
            'reference_code': ai_result.get('reference_code', ''),
            'language': ai_result.get('language', 'Python'),  # 添加语言字段
            'knowledge_point': ai_result.get('knowledge_point', '')  # 添加知识点字段
        }
    elif question_type == 'choice':
        # 选择题特有字段
        return {
            **base_fields,
            'options': ai_result.get('options', []),
            'correct_answer': ai_result.get('correct_answer', ''),
            'language': ai_result.get('language', 'Python'),
            'knowledge_point': ai_result.get('knowledge_point', '')
        }
    elif question_type == 'judgment':
        # 判断题特有字段
        return {
            **base_fields,
            'correct_answer': ai_result.get('correct_answer', ''),
            'language': ai_result.get('language', 'Python'),
            'knowledge_point': ai_result.get('knowledge_point', '')
        }
    else:
        # 默认返回编程题结构
        return {
            **base_fields,
            'input_description': ai_result.get('input_description'),
            'output_description': ai_result.get('output_description'),
            'test_cases': ai_result.get('test_cases', []),
            'reference_code': ai_result.get('reference_code', '')
        }

# 辅助函数：从描述生成标题
def generate_title(description):
    # 简单示例：取描述前20个字作为标题
    if description:
        return description[:20].strip() + '...'
    return '未命名题目'  # 保底值

# AI自测功能：验证测试用例是否都能通过
def validate_test_cases(reference_code, test_cases, language='Python'):
    """
    验证参考代码是否能通过所有测试用例
    """
    logger.info(f"[自测调试] 开始验证测试用例，language={language}, test_cases数量={len(test_cases) if test_cases else 0}")

    if not reference_code or not test_cases:
        logger.warning(f"[自测调试] 缺少必要数据: reference_code={bool(reference_code)}, test_cases={bool(test_cases)}")
        return {
            "success": False,
            "message": "缺少参考代码或测试用例",
            "passed": 0,
            "total": 0
        }

    # 支持的语言列表
    supported_languages = ['python', 'java', 'cpp', 'c++']

    if language.lower() not in supported_languages:
        logger.warning(f"[自测调试] 不支持的语言: {language}")
        return {
            "success": False,
            "message": f"暂不支持{language}语言的自测，支持的语言：{', '.join(supported_languages)}",
            "passed": 0,
            "total": len(test_cases)
        }

    passed_count = 0
    failed_cases = []

    logger.info(f"[自测调试] 初始化failed_cases变量: {type(failed_cases)}")

    for i, test_case in enumerate(test_cases):
        # 处理新格式的测试用例（包含id字段）或旧格式（不含id字段）
        test_input = test_case.get('input', '')
        expected_output = test_case.get('output', '')

        if not test_input or not expected_output:
            continue

        try:
            temp_file = None  # 初始化临时文件路径

            if language.lower() == 'python':
                # 创建临时文件保存Python代码
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(reference_code)
                    temp_file = f.name

                # 执行Python代码
                proc = subprocess.Popen(
                    ['python', temp_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # 传入输入数据并等待执行
                stdout, stderr = proc.communicate(input=test_input, timeout=5)

            elif language.lower() in ['cpp', 'c++']:
                # 处理C++代码
                stdout, stderr = execute_cpp_code(reference_code, test_input)

                # 如果execute_cpp_code返回错误，那么stderr就是错误信息
                # 我们创建一个模拟的process对象来表示执行状态
                if stderr:
                    # 有错误信息
                    proc = type('MockProcess', (), {'returncode': 1})()
                else:
                    # 执行成功
                    proc = type('MockProcess', (), {'returncode': 0})()

            elif language.lower() == 'java':
                # 处理Java代码（临时文件在函数内部管理）
                stdout, stderr = execute_java_code(reference_code, test_input)

                # 如果execute_java_code返回错误，那么stderr就是错误信息
                # 我们创建一个模拟的process对象来表示执行状态
                if stderr:
                    # 有错误信息
                    proc = type('MockProcess', (), {'returncode': 1})()
                else:
                    # 执行成功
                    proc = type('MockProcess', (), {'returncode': 0})()

            else:
                # 不应该到达这里，因为前面已有语言检查
                stdout, stderr = "", f"不支持的语言: {language}"
                proc = type('MockProcess', (), {'returncode': 1})()

            if proc.returncode != 0:
                # 执行错误
                failed_cases.append({
                    "index": i + 1,
                    "input": test_input,
                    "expected": expected_output,
                    "actual": stderr,
                    "error": f"执行错误 (返回码: {proc.returncode})"
                })
                continue

            # 比对输出结果（忽略空格和换行差异）
            actual_output = stdout.strip()

            # 如果程序产生了错误输出且没有标准输出，则显示错误信息
            if not actual_output and stderr:
                actual_output = f"程序错误: {stderr.strip()}"

            if actual_output.replace(' ', '').replace('\n', '') == expected_output.replace(' ', '').replace('\n', ''):
                passed_count += 1
            else:
                failed_cases.append({
                    "index": i + 1,
                    "input": test_input,
                    "expected": expected_output,
                    "actual": actual_output,
                    "error": "输出不匹配"
                })

            # 清理临时文件（仅适用于Python分支）
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

        except subprocess.TimeoutExpired:
            proc.kill()
            failed_cases.append({
                "index": i + 1,
                "input": test_input,
                "expected": expected_output,
                "actual": "",
                "error": "执行超时（超过5秒）"
            })
        except Exception as e:
            failed_cases.append({
                "index": i + 1,
                "input": test_input,
                "expected": expected_output,
                "actual": "",
                "error": f"系统错误: {str(e)}"
            })

    success = passed_count == len(test_cases)

    return {
        "success": success,
        "message": f"通过 {passed_count}/{len(test_cases)} 个测试用例" if not success else "所有测试用例均可通过",
        "passed": passed_count,
        "total": len(test_cases),
        "failed_cases": failed_cases
    }

# 执行C++代码
def execute_cpp_code(cpp_code, input_data):
    """
    编译并执行C++代码
    """
    logger.info(f"[C++自测] 开始执行C++代码，输入: {input_data[:20]}{'...' if len(input_data) > 20 else ''}")
    logger.info(f"[C++自测] C++代码前100字符: {cpp_code[:100]}...")

    try:
        # 创建临时目录用于C++编译
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # 确保C++代码包含main函数
            if 'int main(' not in cpp_code and 'main(' not in cpp_code:
                logger.error("[C++自测] C++代码缺少main函数")
                return "", "C++代码格式错误：缺少main函数\n"

            # 写入C++文件
            cpp_file = os.path.join(temp_dir, 'main.cpp')
            with open(cpp_file, 'w', encoding='utf-8') as f:
                f.write(cpp_code)

            logger.info(f"[C++自测] C++文件已写入: {cpp_file}")

            # 编译C++文件
            exe_file = os.path.join(temp_dir, 'main')
            compile_result = subprocess.run(
                ['g++', '-o', exe_file, cpp_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if compile_result.returncode != 0:
                logger.error(f"[C++自测] 编译失败: {compile_result.stderr}")
                logger.error(f"[C++自测] 尝试编译的文件内容: {cpp_code[:200]}...")
                return "", f"编译错误:\n{compile_result.stderr}\n"

            logger.info("[C++自测] C++编译成功")

            # 执行C++程序
            execute_result = subprocess.run(
                [exe_file],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=10
            )

            stdout = execute_result.stdout
            stderr = execute_result.stderr

            logger.info(f"[C++自测] 执行C++命令: {exe_file}")
            logger.info(f"[C++自测] 输入数据: {input_data[:50]}{'...' if len(input_data) > 50 else ''}")

            if execute_result.returncode != 0:
                logger.error(f"[C++自测] 执行失败: {stderr}")
                logger.error(f"[C++自测] 错误详情 - 返回码: {execute_result.returncode}, stderr: {stderr[:200]}...")
                return "", f"运行错误 (返回码: {execute_result.returncode}):\n{stderr}\n"

            logger.info(f"[C++自测] C++执行成功，输出: {stdout[:50]}{'...' if len(stdout) > 50 else ''}")
            return stdout, ""

    except subprocess.TimeoutExpired:
        logger.error("[C++自测] C++执行超时")
        return "", "执行超时（超过10秒）\n"
    except FileNotFoundError as e:
        logger.error(f"[C++自测] 系统缺少C++环境: {e}")
        return "", "系统未安装C++编译器g++，请联系管理员安装GCC编译套件\n"
    except Exception as e:
        logger.error(f"[C++自测] C++执行出现异常: {e}")
        return "", f"系统错误: {str(e)}\n"

# 执行Java代码
def execute_java_code(java_code, input_data):
    """
    编译并执行Java代码
    """
    # 清理Java代码，确保只有一个类和主函数（使用更灵活的检查）
    # 支持多种main函数格式
    main_patterns = [
        r'\bstatic\s+(\w+\s+)*void\s+main\s*\([^)]*\)',  # static void main(...)
        r'\bpublic\s+static\s+void\s+main\s*\([^)]*\)', # public static void main(...)
        r'\bmain\s*\([^)]*\)',                          # 不要求static或public的main
        r'\bvoid\s+main\s*\([^)]*\)',                  # 不要求static的void main
    ]

    has_class = re.search(r'\b(class|interface|enum)\s+\w+', java_code)

    # 检查多种main函数格式
    has_main = False
    main_method_match = None
    for pattern in main_patterns:
        match = re.search(pattern, java_code)
        if match:
            has_main = True
            main_method_match = match
            logger.info(f"[Java自测] 找到main函数格式: {pattern}")
            break

    if not has_class:
        return "", "Java代码格式错误：缺少类定义\n"

    if not has_main:
        # 更详细的main函数检测失败信息
        logger.warning("[Java自测] 未找到有效的main函数，尝试自动修复")
        logger.info("[Java自测] 考虑生成默认main函数")

        # 检查代码是否包含计算逻辑但缺少main函数
        has_logic = re.search(r'\bpublic\s+static\s+\w+', java_code) or \
                   re.search(r'\bint|float|double|String\b.*=', java_code) or \
                   re.search(r'System\.out', java_code)

        if has_logic:
            logger.info("[Java自测] 检测到代码逻辑但缺少main函数，添加默认main函数")

            # 检测是否有静态方法可以调用
            static_methods = re.findall(r'\bpublic\s+static\s+(\w+)\s*\(', java_code)
            if static_methods:
                # 直接调用静态方法
                method_calls = []
                for method in static_methods[:3]:  # 限制调用前3个方法
                    if method != 'main':  # 避免递归调用
                        method_calls.append(f"        {method}();")

                default_main = f'''
public static void main(String[] args) {{
    // 自测系统自动添加的main函数
{chr(10).join(method_calls)}
}}
'''
                # 在类结尾插入main函数
                last_closing_brace = java_code.rfind('}')
                if last_closing_brace > 0:
                    java_code = java_code[:last_closing_brace] + default_main + java_code[last_closing_brace:]
                    has_main = True
                    logger.info(f"[Java自测] 添加调用静态方法的main函数: {static_methods}")
                else:
                    logger.error("[Java自测] 无法找到类结尾位置")
            else:
                # 添加简单的main函数包装器
                default_main = '''
public static void main(String[] args) {
    // 自测系统自动添加的main函数
    Solution sol = new Solution();
    // 如果有具体的算法方法，请在这里调用
}
'''

                # 在类结尾插入main函数
                if java_code.endswith('}'):
                    java_code = java_code[:-1] + default_main + '}'
                    has_main = True
                    logger.info("[Java自测] 添加简单的main函数包装器")
                else:
                    logger.error("[Java自测] 无法找到类结尾位置")
                    return "", "Java代码格式错误：缺少有效的main函数且无法自动修复\n"
        else:
            logger.info("[Java自测] 代码没有检测到明显的计算逻辑")
            # 检查是否只有一个main关键词但格式不标准
            if 'main' in java_code:
                logger.error(f"[Java自测] 代码包含main关键词，但格式不匹配")
                problematic_main = re.findall(r'.{0,20}main.*', java_code, re.IGNORECASE)[:3]
                for pm in problematic_main:
                    logger.error(f"[Java自测] 可疑main行: {repr(pm)}")
            return "", "Java代码格式错误：缺少有效的main函数\n"

    # 最后再次验证main函数是否存在
    if not re.search(r'\bvoid\s+main\s*\([^)]*\)', java_code):
        logger.error("[Java自测] 最终main函数验证失败")
        return "", "Java代码格式错误：无法创建有效的main函数\n"

    logger.info(f"[Java自测] 类定义: {has_class.group() if has_class else '未找到'}")
    logger.info("[Java自测] main函数验证通过")

    logger.info(f"[Java自测] 原始输入数据: {repr(input_data)}")

    # 智能预处理输入数据 - 根据输入特征选择处理策略
    original_input = input_data

    # 检测输入特征
    has_quotes = '"' in input_data or '"' in input_data
    has_brackets = '[' in input_data or ']' in input_data
    is_pure_numeric = bool(re.match(r'^[\d\s\n]+$', input_data.strip()))
    has_characters = bool(re.search(r'[a-zA-Z\u4e00-\u9fff]', input_data))
    has_commas = ',' in input_data

    logger.info(f"[Java自测] 输入特征分析:")
    logger.info(f"[Java自测] - 包含引号: {has_quotes}")
    logger.info(f"[Java自测] - 包含方括号: {has_brackets}")
    logger.info(f"[Java自测] - 纯数字: {is_pure_numeric}")
    logger.info(f"[Java自测] - 包含字符: {has_characters}")
    logger.info(f"[Java自测] - 包含逗号: {has_commas}")

    # 根据特征选择处理策略
    if has_quotes and ',' in input_data:
        # 处理像 "abc","def","cba" 这样的字符串数组输入
        filtered_input = re.sub(r'^.*?["]', '', input_data)  # 去掉开头可能的非配对引号
        filtered_input = re.sub(r'[""]\s*$', '', filtered_input)  # 去掉结尾可能的非配对引号
        logger.info(f"[Java自测] 应用字符串数组处理模式")
    elif has_characters and not has_quotes and not is_pure_numeric:
        # 处理字母字符输入
        filtered_input = re.sub(r'[^\w\s\n\t]', '', input_data).strip()
        logger.info(f"[Java自测] 应用字母字符处理模式")
    elif any(word in input_data for word in ['输入', 'input', '数据']):
        # 处理包含提示信息的输入
        filtered_input = re.sub(r'[输入input数据：:]+\s*', '', input_data).strip()
        logger.info(f"[Java自测] 应用输入提示处理模式")
    elif is_pure_numeric:
        # 纯数字输入 - 不需要过滤
        filtered_input = input_data
        logger.info(f"[Java自测] 纯数字输入，无需过滤")
    else:
        # 默认策略
        filtered_input = re.sub(r'[^\d\s\n\t]', '', input_data).strip()
        logger.info(f"[Java自测] 应用默认过滤模式")

    logger.info(f"[Java自测] 过滤后输入数据: {repr(filtered_input)}")
    logger.info(f"[Java自测] 输入长度变化: 原始={len(original_input)}, 过滤后={len(filtered_input)}")

    # 检查Java代码中的Scanner使用模式
    scanner_pattern = r'Scanner\s+\w+\s*=\s*new\s+Scanner'
    has_scanner = re.search(scanner_pattern, java_code) is not None
    logger.info(f"[Java自测] 代码使用Scanner: {has_scanner}")

    if has_scanner:
        scanner_usage = re.findall(r'\w+\.(next\w+|next)\s*\(', java_code)
        logger.info(f"[Java自测] Scanner方法调用: {scanner_usage}")

    # 安全检查 - 只有当过滤后仍有足够内容时才使用
    if len(filtered_input.strip()) == 0:
        logger.warning(f"[Java自测] 过滤结果为空，使用原始输入")
        filtered_input = original_input
    elif len(filtered_input) < 2 and has_characters:
        logger.warning(f"[Java自测] 过滤后内容太少但包含字符，使用原始输入")
        filtered_input = original_input

    input_data = filtered_input
    logger.info(f"[Java自测] 最终使用的输入数据: {repr(input_data)}")

    try:
        # 创建临时目录用于Java编译
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # 统一提取类名，支持多种格式
            class_name_match = re.search(r'\b(class|interface|enum)\s+(\w+)', java_code)
            if class_name_match:
                actual_class_name = class_name_match.group(2)
                java_file = os.path.join(temp_dir, f'{actual_class_name}.java')
                logger.info(f"[Java自测] 提取类名: {actual_class_name}, 文件路径: {java_file}")
            else:
                logger.error("[Java自测] 无法提取Java代码中的类名")
                return "", "Java代码格式错误：无法提取类名\n"

            # 检查代码中是否有包声明，如果有则移除
            # 注意：需要处理词边界，避免破坏类名中的"import"或"package"
            cleaned_code = java_code
            cleaned_code = re.sub(r'(?<![\w])\bpackage\s', '// package ', cleaned_code)

            # 检查是否需要添加必要的import语句
            required_imports = []

            # 检查是否需要java.util包（包含Scanner等工具类）
            has_java_util_import = 'import java.util' in cleaned_code
            has_util_classes = any(cls in cleaned_code for cls in ['Scanner', 'List', 'ArrayList', 'LinkedList', 'Deque', 'Queue'])

            logger.info(f"[Java自测] 清理后代码前100字符: {cleaned_code[:100]}")
            logger.info(f"[Java自测] 工具类使用检测: {[cls for cls in ['Scanner', 'List', 'ArrayList', 'LinkedList', 'Deque', 'Queue'] if cls in cleaned_code]}")
            logger.info(f"[Java自测] java.util导入检测: {has_java_util_import}")

            # 只有当确实需要工具类且没有相应导入时才添加
            if has_util_classes and not has_java_util_import:
                required_imports.append('import java.util.*;')
                logger.info("[Java自测] 将添加 java.util.*; 导入")

            logger.info(f"[Java自测] 需要添加的导入列表: {required_imports}")

            # 如果需要添加import语句
            if required_imports:
                # 总是添加到代码开头（类声明之前）
                class_start = cleaned_code.find('public class')
                if class_start >= 0 and class_start > 0:
                    # 在类声明前添加，但保留已经存在的import语句
                    imports_string = '\n'.join(required_imports) + '\n'
                    cleaned_code = cleaned_code[:class_start] + imports_string + cleaned_code[class_start:]
                    logger.info("[Java自测] 在类前添加必需的import语句")
                else:
                    # 如果找不到类声明，添加到开头
                    imports_string = '\n'.join(required_imports) + '\n'
                    cleaned_code = imports_string + cleaned_code
                    logger.info("[Java自测] 无法找到类声明，将import添加到开头")

            logger.info(f"[Java自测] 需要添加的import语句: {required_imports}")
            logger.info(f"[Java自测] 清理打包声明后的代码长度: {len(cleaned_code)}")
            logger.info(f"[Java自测] 清理打包声明后的代码前100字符: {cleaned_code[:100]}...")

            # 记录完整的代码内容用于调试
            logger.info(f"[Java自测] 完整清理后的代码内容:")
            for i, line in enumerate(cleaned_code.split('\n'), 1):
                logger.info(f"[Java自测] 行{i}: {line}")

            # 检查清洁后的代码是否仍然包含有效的类定义
            cleaned_class_match = re.search(r'\b(class|interface|enum)\s+\w+', cleaned_code)
            if not cleaned_class_match:
                logger.error("[Java自测] 清洁后的代码中找不到有效的类定义")
                return "", "Java代码格式错误：清洁后找不到有效的类定义\n"

            logger.info(f"[Java自测] 清洁后类定义: {cleaned_class_match.group()}")

            # 写入Java文件（指定UTF-8编码）
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_code)

            logger.info(f"[Java自测] Java文件已写入: {java_file}")

            # 类名已经在前面提取并验证了
            logger.info(f"[Java自测] 使用类名执行: {actual_class_name}")

            # 编译Java文件（使用Dawn JDK完整路径）
            compile_result = subprocess.run(
                [r'C:\Program Files\Java\jdk-24\bin\javac.exe', '-cp', temp_dir, '-encoding', 'utf-8', java_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if compile_result.returncode != 0:
                logger.error(f"[Java自测] 编译失败: {compile_result.stderr}")
                logger.error(f"[Java自测] 尝试编译的文件内容: {cleaned_code[:200]}...")
                return "", f"编译错误:\n{compile_result.stderr}\n"

            logger.info("[Java自测] Java编译成功")

            # 执行Java程序，使用Dawn JDK完整路径
            execute_result = subprocess.run(
                [r'C:\Program Files\Java\jdk-24\bin\java.exe', '-cp', temp_dir, actual_class_name],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=10
            )

            stdout = execute_result.stdout.strip()
            stderr = execute_result.stderr

            logger.info(f"[Java自测] 执行Java命令: java -cp {temp_dir} {actual_class_name}")
            logger.info(f"[Java自测] 输入数据: {input_data[:50]}{'...' if len(input_data) > 50 else ''}")

            if execute_result.returncode != 0:
                logger.error(f"[Java自测] 执行失败: {stderr}")
                logger.error(f"[Java自测] 错误详情 - 返回码: {execute_result.returncode}, stderr: {stderr[:200]}...")
                return "", f"运行错误 (返回码: {execute_result.returncode}):\n{stderr}\n"

            logger.info(f"[Java自测] Java执行成功，输出: {stdout[:50]}{'...' if len(stdout) > 50 else ''}")
            return stdout.strip(), ""

    except subprocess.TimeoutExpired:
        logger.error("[Java自测] Java执行超时")
        return "", "执行超时（超过10秒）\n"
    except FileNotFoundError as e:
        logger.error(f"[Java自测] 系统缺少Java环境: {e}")
        return "", "系统未安装Java开发环境，请联系管理员安装JDK\n"
    except Exception as e:
        logger.error(f"[Java自测] Java执行出现异常: {e}")
        return "", f"系统错误: {str(e)}\n"

# 延迟导入生成器，确保环境变量已加载
def get_generator():
    from services.deepseek_generator import DeepSeekProblemGenerator
    from config import Config

    api_key = Config.DEEPSEEK_API_KEY
    if not api_key:
        logger.error("DEEPSEEK_API_KEY未设置")
        return None

    try:
        generator = DeepSeekProblemGenerator(api_key)
        logger.info("DeepSeek生成器初始化成功")
        return generator
    except Exception as e:
        logger.error(f"生成器初始化失败：{str(e)}")
        return None

@ai_problems_bp.route('/generate', methods=['POST', 'OPTIONS'])
def generate_problem():
    if request.method == 'OPTIONS':
        return '', 204

    # 检查教师权限
    if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
        return jsonify({
            "success": False,
            "message": "需要教师或管理员权限"
        }), 401

    # 获取生成器
    generator = get_generator()
    if not generator:
        error_msg = "DeepSeek API密钥未配置或无效，请设置环境变量DEEPSEEK_API_KEY"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

    # 获取请求参数
    try:
        data = request.get_json()
        if not data:
            raise ValueError("请求体为空或格式不正确")

        knowledge_point = data.get('knowledge_point', '动态规划')
        difficulty = data.get('difficulty', 'medium')
        language = data.get('language', 'Python')
        question_type = data.get('type', data.get('problem_type', 'programming'))
        user_title = data.get('title')  # 获取用户提供的标题
        custom_requirements = data.get('custom_requirements', [])  # 获取自定义要求

        logger.info(f"接收生成请求 - 类型: {question_type}, 知识点: {knowledge_point}, 难度: {difficulty}, 语言: {language}, 标题: {user_title}")
        if custom_requirements:
            logger.info(f"自定义要求: {custom_requirements}")
    except Exception as e:
        error_msg = f"解析请求参数失败：{str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400

    # 调用生成器生成题目
    try:
        # 根据题目类型调用不同的生成方法
        if question_type == 'choice':
            # 生成选择题
            raw_result = generator.generate_choice_question(
                knowledge_point=knowledge_point,
                difficulty=difficulty,
                language=language,
                custom_requirements=custom_requirements
            )
        elif question_type == 'judgment':
            # 生成判断题
            raw_result = generator.generate_judgment_question(
                knowledge_point=knowledge_point,
                difficulty=difficulty,
                language=language,
                custom_requirements=custom_requirements
            )
        else:
            # 默认生成编程题
            raw_result = generator.generate_programming_problem(
                knowledge_point=knowledge_point,
                difficulty=difficulty,
                language=language,
                custom_requirements=custom_requirements
            )

        # 检查生成结果
        if not raw_result.get('success', False):
            raise ValueError(f"生成失败: {raw_result.get('error', '未知错误')}")

        # 处理AI返回结果，优先使用用户提供的标题
        result = process_ai_response(raw_result, question_type)
        if user_title:  # 如果用户提供了标题，则覆盖AI生成的标题
            result['title'] = user_title

        # 添加题目类型信息
        result["type"] = question_type

        logger.info(f"{question_type}题目生成成功，返回预览结果")

        # 返回生成结果（不包含数据库ID）
        return jsonify({
            **result,
            "success": True
        })

    except Exception as e:
        error_msg = f"生成题目失败：{str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@ai_problems_bp.route('/import', methods=['POST', 'OPTIONS'])
def import_problem():
    if request.method == 'OPTIONS':
        return '', 204

    # 检查教师权限
    if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
        return jsonify({
            "success": False,
            "message": "需要教师或管理员权限"
        }), 401

    # 获取要导入的题目数据
    try:
        data = request.get_json()
        logger.info(f"接收导入请求，原始请求体: {request.data}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"请求方法: {request.method}")

        if not data:
            logger.error("request.get_json() 返回 None 或空值")
            raise ValueError("请求体为空或格式不正确")

        logger.info(f"接收导入请求，数据类型: {type(data)}")
        logger.debug(f"接收到的数据: {data}")

        # 处理前端可能发送列表的情况
        if isinstance(data, list):
            if len(data) > 0:
                # 取列表中的第一个元素作为题目数据
                data = data[0]
                logger.info("检测到列表格式数据，使用第一个元素")
            else:
                raise ValueError("接收到的列表为空")

        # 转换难度格式（如果需要）
        difficulty_mapping = {
            'easy': '简单',
            'medium': '中等',
            'hard': '困难'
        }
        difficulty = data.get('difficulty', 'medium')
        db_difficulty = difficulty_mapping.get(difficulty, difficulty)

        # 获取题目类型
        question_type = data.get('type', 'programming')

        # 根据题目类型准备不同的参数
        knowledge_point = data.get('knowledge_point') or data.get('knowledge_points') or ''
        import_kwargs = {
            'title': data.get('title'),
            'description': data.get('description'),
            'difficulty': db_difficulty,
            'solution_idea': data.get('solution_idea', ''),
            'question_type': question_type,
            'language': data.get('language', 'Python'),
            'knowledge_points': knowledge_point
        }

        if question_type == 'programming':
            # 编程题特有参数
            import_kwargs.update({
                'input_desc': data.get('input_description'),
                'output_desc': data.get('output_description'),
                'test_cases': data.get('test_cases', []),
                'reference_code': data.get('reference_code', '')
            })
        elif question_type == 'choice':
            # 选择题特有参数
            options = data.get('options', [])
            correct_answer = data.get('correct_answer')

            # 检查选项格式 - 如果是列表格式，直接使用；如果是旧的键值对格式，需要转换
            if options and isinstance(options[0], dict) and 'key' in options[0]:
                # 旧的键值对格式，需要转换
                for option in options:
                    option['is_correct'] = (option.get('key') == correct_answer)
                import_kwargs.update({
                    'options': options,
                    'correct_answer': correct_answer
                })
            else:
                # 新的列表格式，直接使用
                import_kwargs.update({
                    'options': options,
                    'correct_answer': str(correct_answer)  # 确保是字符串格式
                })
        elif question_type == 'judgment':
            # 判断题特有参数
            correct_answer = data.get('correct_answer')
            is_true = None
            if correct_answer == '正确':
                is_true = True
            elif correct_answer == '错误':
                is_true = False

            import_kwargs.update({
                'is_true': is_true
            })

        # 调用数据库导入函数
        from utils.db_utils import import_problem_to_db
        db_result = import_problem_to_db(**import_kwargs)

        if not db_result.get('success', False):
            raise ValueError(f"数据库存储失败: {db_result.get('error', '未知错误')}")

        logger.info(f"{question_type}题目已成功导入数据库")

        # 返回包含数据库ID的结果
        return jsonify({
            "success": True,
            "id": db_result.get('id'),
            "message": "题目导入成功"
        })

    except Exception as e:
        error_msg = f"导入题目失败：{str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@ai_problems_bp.route('/self-test', methods=['POST', 'OPTIONS'])
def self_test_problem():
    """AI自测功能：验证生成的题目测试用例是否都能通过"""
    if request.method == 'OPTIONS':
        return '', 204

    # 检查教师权限
    if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
        return jsonify({
            "success": False,
            "message": "需要教师或管理员权限"
        }), 401

    try:
        data = request.get_json()
        if not data:
            raise ValueError("请求体为空或格式不正确")

        # 获取题目数据
        reference_code = data.get('reference_code', '')
        test_cases = data.get('test_cases', [])
        language = data.get('language', 'Python')
        question_type = data.get('type', 'programming')

        logger.info(f"[自测调试] 接收AI自测请求 - 类型: {question_type}, 语言: {language}, 测试用例数量: {len(test_cases)}")
        logger.info(f"[自测调试] 参考代码长度: {len(reference_code)}")
        logger.info(f"[自测调试] 测试用例详情: {test_cases}")

        # 验证测试用例格式
        for i, tc in enumerate(test_cases):
            logger.info(f"[自测调试] 测试用例{i+1}: {tc}")
            if 'input' not in tc or 'output' not in tc:
                logger.error(f"[自测调试] 测试用例{i+1}格式错误: {tc}")

        # 只有编程题需要自测
        if question_type != 'programming':
            return jsonify({
                "success": True,
                "message": f"{question_type}题目无需自测",
                "passed": 0,
                "total": 0
            })

        # 验证测试用例
        logger.info(f"[自测调试] 开始调用validate_test_cases函数")
        test_result = validate_test_cases(reference_code, test_cases, language)
        logger.info(f"[自测调试] validate_test_cases返回值: {test_result}")

        # 确保返回值包含必要字段
        if not isinstance(test_result, dict):
            logger.error(f"[自测调试] validate_test_cases返回类型错误: {type(test_result)}")
            test_result = {
                "success": False,
                "message": "测试函数返回格式错误",
                "passed": 0,
                "total": 0,
                "failed_cases": []
            }

        # 安全地访问字典字段
        success = test_result.get('success', False)
        passed = test_result.get('passed', 0)
        total = test_result.get('total', 0)
        failed_cases = test_result.get('failed_cases', [])
        message = test_result.get('message', '测试完成')

        logger.info(f"[自测调试] 准备返回结果: success={success}, passed={passed}, total={total}, failed_cases={len(failed_cases)}项")

        if success:
            logger.info("AI自测成功：所有测试用例均可通过")
            return jsonify({
                "success": True,
                "message": message,
                "passed": passed,
                "total": total,
                "failed_cases": failed_cases
            })
        else:
            logger.warning(f"AI自测失败：通过 {passed}/{total} 个测试用例")
            return jsonify({
                "success": False,
                "message": message,
                "passed": passed,
                "total": total,
                "failed_cases": failed_cases
            })

    except Exception as e:
        error_msg = f"AI自测失败：{str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            "success": False,
            "error": error_msg,
            "passed": 0,
            "total": 0,
            "failed_cases": []
        }), 500