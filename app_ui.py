# -*- coding: utf-8 -*-
"""
@Project : AICode
@File    : app_ui.py
@Author  : xuan
@Date    : 2025/3/7 17:16
"""
import asyncio
import re
import streamlit as st
from autogen_agentchat.agents import AssistantAgent
from llms import model_client
from prompt_tasks import TESTCASE_WRITER_SYSTEM_MESSAGE
import json
import pandas as pd
import io
import datetime
from pydantic import BaseModel, Field, ValidationError
from typing import List

# 设置页面配置
st.set_page_config(
    page_title="测试用例生成器",
    page_icon="✅",
    layout="wide"
)

# 页面标题
st.title("\U0001F9EA AI 测试用例生成器")
st.markdown("输入你的需求描述，AI 将为你生成相应的测试用例")


# 创建测试用例生成器代理
@st.cache_resource
def get_testcase_writer():
    return AssistantAgent(
        name="testcase_writer",
        model_client=model_client,
        system_message=TESTCASE_WRITER_SYSTEM_MESSAGE,
        model_client_stream=True,
    )


# 定义测试用例模型
class TestCase(BaseModel):
    case_id: str = Field(..., description="测试用例唯一标识符，格式为TC-XXX-NNN")
    priority: str = Field(..., description="优先级，P0(最高)、P1、P2、P3(最低)")
    title: str = Field(..., description="测试用例标题")
    precondition: str = Field(..., description="前置条件")
    steps: str = Field(..., description="测试步骤")
    expected_result: str = Field(..., description="预期结果")


class TestCaseCollection(BaseModel):
    test_cases: List[TestCase] = Field(..., description="测试用例集合")


testcase_writer = get_testcase_writer()

# 用户输入区域
user_input = st.text_area(
    "需求描述",
    height=200,
    placeholder="请详细描述你的功能需求，例如：\n开发一个用户注册功能，要求用户提供用户名、密码和电子邮件。用户名长度为3-20个字符，密码长度至少为8个字符且必须包含数字和字母，电子邮件必须是有效格式。"
)

# 高级选项（可折叠）
with st.expander("高级选项"):
    test_level = st.selectbox(
        "测试级别",
        ["单元测试", "集成测试", "系统测试", "验收测试"],
        index=2
    )

    test_priority = st.selectbox(
        "测试优先级",
        ["高", "中", "低"],
        index=0
    )

    # 添加测试用例数量控制
    test_case_count = st.number_input(
        "生成测试用例数量",
        min_value=1,
        max_value=30,  # 最大数
        value=5,  # 默认条数
        step=1,
        help="指定需要生成的测试用例数量"
    )

    include_edge_cases = st.checkbox("包含边界情况", value=True)
    include_negative_tests = st.checkbox("包含负面测试", value=True)

    output_format = st.radio(
        "输出格式",
        ["Excel", "Markdown", "JSON"],
        index=0,
        help="选择测试用例的输出格式"
    )

# 提交按钮
submit_button = st.button("生成测试用例")


# 尝试从文本中提取JSON
def extract_json_from_text(text):
    """尝试从文本中提取JSON对象"""
    try:
        # 查找JSON块
        json_match = None
        if "```json" in text and "```" in text:
            start_idx = text.find("```json")
            if start_idx != -1:
                end_idx = text.find("```", start_idx + 7)
                if end_idx != -1:
                    json_str = text[start_idx + 7:end_idx].strip()
                    return json.loads(json_str)

        # 尝试直接解析整个文本
        return json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        return None


# 计算测试用例数量
def count_test_cases(markdown_text):
    """计算Markdown文本中的测试用例数量"""
    # 尝试从JSON中计算
    json_data = extract_json_from_text(markdown_text)
    if json_data and "test_cases" in json_data:
        return len(json_data["test_cases"])

    # 计算Markdown中的测试用例数量
    count = 0
    lines = markdown_text.split('\n')
    for line in lines:
        if line.strip().startswith('## '):
            count += 1
    return count


# 格式化步骤和预期结果文本
def format_numbered_text(text):
    """将带有数字编号的文本格式化为多行文本，去除多余空行"""
    if not text:
        return text

    # 使用正则表达式查找数字编号模式（如"1. ", "2. "等）
    pattern = r'(\d+\.\s)'
    parts = re.split(pattern, text)

    if len(parts) <= 1:  # 没有找到编号模式，返回原文本
        return text

    # 重新组合文本，确保每个编号项都是单独的行，没有多余空行
    formatted_lines = []
    i = 0
    while i < len(parts):
        if re.match(pattern, parts[i]):
            # 这是一个编号
            number = parts[i]
            if i + 1 < len(parts):
                # 编号后面的内容
                content = parts[i + 1].strip()
                formatted_lines.append(number + content)
                i += 2
            else:
                formatted_lines.append(number)
                i += 1
        else:
            # 不是编号的部分，如果不为空则添加
            if parts[i].strip():
                formatted_lines.append(parts[i].strip())
            i += 1

    return "\n".join(formatted_lines)


# 使用结构化方法解析测试用例，不依赖正则表达式
def parse_test_cases_structured(markdown_text):
    """使用结构化方法从Markdown文本中解析测试用例"""
    data = []

    # 首先尝试解析为JSON格式
    json_data = extract_json_from_text(markdown_text)
    if json_data and "test_cases" in json_data:
        # 将JSON转换为所需的字典格式
        for tc in json_data["test_cases"]:
            data.append({
                "用例ID": tc.get("case_id", "未指定"),
                "标题": tc.get("title", "未指定"),
                "测试级别": test_level,  # 使用用户选择的测试级别
                "优先级": tc.get("priority", "未指定"),
                "前置条件": tc.get("precondition", "未指定"),
                "测试步骤": format_numbered_text(tc.get("steps", "未指定")),  # 格式化步骤
                "预期结果": format_numbered_text(tc.get("expected_result", "未指定"))  # 格式化预期结果
            })
        return data

    # 使用分段方法解析Markdown
    # 按测试用例分割文本
    test_cases_blocks = []
    lines = markdown_text.split('\n')
    current_block = []

    for line in lines:
        # 如果找到新的测试用例标记（##开头），保存当前块并开始新块
        if line.strip().startswith('## '):
            if current_block:  # 保存非空块
                test_cases_blocks.append('\n'.join(current_block))
                current_block = []
        # 添加行到当前块
        current_block.append(line)

    # 添加最后一个块
    if current_block:
        test_cases_blocks.append('\n'.join(current_block))

    # 解析每个测试用例块
    for block in test_cases_blocks:
        if not block.strip():
            continue

        # 初始化测试用例数据
        test_case = {
            "用例ID": "未指定",
            "标题": "未指定",
            "测试级别": "未指定",
            "优先级": "未指定",
            "前置条件": "未指定",
            "测试步骤": "未指定",
            "预期结果": "未指定"
        }

        # 解析测试用例ID
        if "用例ID" in block:
            id_lines = [line for line in block.split('\n') if "用例ID" in line]
            if id_lines:
                id_line = id_lines[0]
                # 提取冒号或中文冒号后面的内容
                if ':' in id_line:
                    test_case["用例ID"] = id_line.split(':', 1)[1].strip()
                elif '：' in id_line:
                    test_case["用例ID"] = id_line.split('：', 1)[1].strip()
                # 如果没有找到冒号，尝试直接提取TC开头的ID
                else:
                    words = id_line.split()
                    for word in words:
                        if word.startswith("TC"):
                            test_case["用例ID"] = word.strip()
                            break

        # 如果没有找到ID但标题行包含TC-或TC_开头的文本，使用它作为ID
        if test_case["用例ID"] == "未指定":
            header_line = block.split('\n')[0] if block.split('\n') else ""
            if "TC-" in header_line or "TC_" in header_line:
                words = header_line.split()
                for word in words:
                    if word.startswith("TC"):
                        test_case["用例ID"] = word.strip()
                        break

        # 解析其他字段
        fields = [
            ("标题", ["标题"]),
            ("测试级别", ["测试级别"]),
            ("优先级", ["优先级"]),
            ("前置条件", ["前置条件"]),
            ("测试步骤", ["测试步骤"]),
            ("预期结果", ["预期结果"])
        ]

        for field_name, keywords in fields:
            for keyword in keywords:
                section_start = None
                section_end = None

                # 查找字段开始位置
                lines = block.split('\n')
                for i, line in enumerate(lines):
                    if f"**{keyword}**" in line:
                        section_start = i
                        break

                if section_start is not None:
                    # 查找字段结束位置（下一个字段开始或文本结束）
                    for i in range(section_start + 1, len(lines)):
                        if any(f"**{k}**" in lines[i] for k, _ in fields):
                            section_end = i
                            break

                    if section_end is None:
                        section_end = len(lines)

                    # 提取内容
                    content_start_line = lines[section_start]
                    # 处理冒号后的内容
                    if ':' in content_start_line:
                        first_line_content = content_start_line.split(':', 1)[1].strip()
                    elif '：' in content_start_line:
                        first_line_content = content_start_line.split('：', 1)[1].strip()
                    else:
                        first_line_content = ""

                    # 合并多行内容
                    content = [first_line_content] if first_line_content else []
                    content.extend(lines[section_start + 1:section_end])

                    # 格式化步骤和预期结果
                    content_text = '\n'.join(content).strip()
                    if field_name in ["测试步骤", "预期结果"]:
                        content_text = format_numbered_text(content_text)

                    test_case[field_name] = content_text

        # 只有当测试用例ID不是"未指定"时才添加到结果中
        if test_case["用例ID"] != "未指定":
            data.append(test_case)

    return data


# 验证和格式化测试用例函数
def validate_and_format_testcases(raw_output, expected_count):
    """验证测试用例数量并格式化输出"""
    # 计算测试用例数量
    actual_count = count_test_cases(raw_output)

    # 构建格式化输出
    formatted_output = raw_output

    # 检查用例数量
    if actual_count != expected_count:
        warning = f"\n\n> ⚠️ **警告**: 生成了 {actual_count} 条测试用例，但要求是 {expected_count} 条。"
        formatted_output += warning

    # 检查是否有重复ID
    data = parse_test_cases_structured(raw_output)
    if data:
        ids = [tc["用例ID"] for tc in data]
        unique_ids = set(ids)
        if len(unique_ids) != len(ids):
            warning = "\n\n> ⚠️ **警告**: 存在重复的测试用例ID，请检查。"
            formatted_output += warning

    return formatted_output


# 将Markdown转换为JSON格式
def markdown_to_json(markdown_text):
    """将Markdown格式的测试用例转换为JSON格式"""
    data = parse_test_cases_structured(markdown_text)
    if not data:
        return None

    # 将解析的数据转换为TestCase对象列表
    test_cases = []
    for tc in data:
        try:
            test_case = TestCase(
                case_id=tc["用例ID"],
                priority=tc["优先级"],
                title=tc["标题"],
                precondition=tc["前置条件"],
                steps=tc["测试步骤"],
                expected_result=tc["预期结果"]
            )
            test_cases.append(test_case)
        except ValidationError as e:
            st.warning(f"测试用例验证失败: {str(e)}")
            continue

    # 创建TestCaseCollection对象
    if test_cases:
        collection = TestCaseCollection(test_cases=test_cases)
        return collection.json(indent=2, ensure_ascii=False)
    return None


# 处理提交
if submit_button and user_input:
    # 准备JSON格式示例
    json_example = '''```json
{
  "test_cases": [
    {
      "case_id": "TC-XXX-001",
      "priority": "P0",
      "title": "测试用例标题",
      "precondition": "前置条件",
      "steps": "1. 第一步操作\n2. 第二步操作",
      "expected_result": "1. 第一步预期结果\n2. 第二步预期结果"
    }
  ]
}
```'''

    # 准备Markdown格式示例
    markdown_example = f'''## 用例ID：TC-XXX-001
        **标题**：测试用例标题
        **测试级别**：{test_level}
        **优先级**：{test_priority}
        **前置条件**：
        - 前置条件1
        - 前置条件2
        
        **测试步骤**：
        1. 第一步操作
        2. 第二步操作
        3. 第三步操作
        
        **预期结果**：
        1. 第一步预期结果
        2. 第二步预期结果
        3. 第三步预期结果'''

    # 准备任务描述
    task = f"""
    需求描述: {user_input}

    测试级别: {test_level}
    测试优先级: {test_priority}
    包含边界情况: {'是' if include_edge_cases else '否'}
    包含负面测试: {'是' if include_negative_tests else '否'}

    【重要】请严格生成 {test_case_count} 条测试用例，不多不少。每个用例ID必须唯一。

    请根据以上需求生成结构化的测试用例，使用以下格式：

    {"请以JSON格式输出，符合TestCaseCollection模型" if output_format == "JSON" else "请使用以下Markdown格式："}

    {json_example if output_format == "JSON" else markdown_example}

    每个测试用例ID必须唯一，格式为 {"TC-XXX-NNN" if output_format == "JSON" else "TC_XXX_NNN"}，其中XXX是功能模块代码，NNN是数字编号。

    【重要】对于测试步骤和预期结果，请确保每个步骤单独成行，使用数字编号（如"1. "，"2. "等）开头。
    """

    # 创建一个固定的容器用于显示生成内容
    response_container = st.container()


    # 定义一个异步函数来处理流式输出
    async def generate_testcases():
        full_response = ""

        # 创建一个空元素用于更新内容
        with response_container:
            placeholder = st.empty()

        async for chunk in testcase_writer.run_stream(task=task):
            if chunk:
                # 处理不同类型的chunk
                if hasattr(chunk, 'content'):
                    content = chunk.content
                elif isinstance(chunk, str):
                    content = chunk
                else:
                    content = str(chunk)

                # 将新内容添加到完整响应中
                full_response += content

                # 更新显示区域（替换而非追加）
                placeholder.markdown(full_response)

        # 在完成生成后验证和格式化输出
        formatted_response = validate_and_format_testcases(full_response, test_case_count)
        placeholder.markdown(formatted_response)

        return formatted_response


    try:
        # 显示生成中状态
        with st.spinner("正在生成测试用例..."):
            # 执行异步函数
            result = asyncio.run(generate_testcases())

        # 生成完成后显示成功消息（在容器外部）
        st.success("✅ 测试用例生成完成!")

        # 处理输出格式
        if output_format == "Markdown":
            # 添加下载按钮
            st.download_button(
                label="下载测试用例 (Markdown)",
                data=result,
                file_name="测试用例.md",
                mime="text/markdown",
            )
        elif output_format == "JSON":
            # 尝试提取或转换为JSON
            json_data = extract_json_from_text(result)
            if json_data:
                # 如果成功提取到JSON，直接使用
                json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="下载测试用例 (JSON)",
                    data=json_str,
                    file_name="测试用例.json",
                    mime="application/json",
                )
            else:
                # 尝试将Markdown转换为JSON
                json_str = markdown_to_json(result)
                if json_str:
                    st.download_button(
                        label="下载测试用例 (JSON)",
                        data=json_str,
                        file_name="测试用例.json",
                        mime="application/json",
                    )
                else:
                    st.error("无法解析为JSON格式，请检查生成的内容")
                    # 提供Markdown格式作为备选
                    st.download_button(
                        label="下载测试用例 (Markdown)",
                        data=result,
                        file_name="测试用例.md",
                        mime="text/markdown",
                    )
        else:  # Excel 格式
            # 解析 Markdown 内容并转换为 Excel
            try:
                # 解析测试用例
                data = parse_test_cases_structured(result)

                if not data:
                    st.error("无法解析测试用例，请检查生成的内容格式")
                    # 显示原始内容的一部分（用于调试）
                    with st.expander("查看原始内容（用于调试）"):
                        st.code(result[:1000] + "..." if len(result) > 1000 else result)
                    # 提供Markdown格式作为备选
                    st.download_button(
                        label="下载测试用例 (Markdown)",
                        data=result,
                        file_name="测试用例.md",
                        mime="text/markdown",
                    )
                else:
                    # 创建 DataFrame
                    df = pd.DataFrame(data)

                    # 生成时间戳文件名
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
                    filename = f"测试用例_{timestamp}.xlsx"

                    # 转换为 Excel
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='测试用例')
                        # 获取工作簿和工作表对象
                        workbook = writer.book
                        worksheet = writer.sheets['测试用例']

                        # 设置单元格自动换行格式
                        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

                        # 应用格式到所有列
                        for i, col in enumerate(df.columns):
                            # 计算最大列宽
                            col_values = df[col].astype(str)
                            max_len = max([len(str(s).split('\n')[0]) for s in col_values] + [len(col)]) + 2
                            max_len = min(max_len, 50)  # 限制最大宽度

                            # 设置列宽和格式
                            worksheet.set_column(i, i, max_len, wrap_format)

                        # 特别处理测试步骤和预期结果列，确保换行正确显示
                        steps_col = df.columns.get_loc("测试步骤") if "测试步骤" in df.columns else None
                        results_col = df.columns.get_loc("预期结果") if "预期结果" in df.columns else None

                        # 为每一行设置适当的行高
                        for row_num, row_data in enumerate(df.itertuples(), 1):
                            # 计算行高 - 基于步骤和预期结果中的换行数
                            row_height = 15  # 默认行高

                            if steps_col is not None:
                                steps_text = str(df.iloc[row_num - 1, steps_col])
                                steps_lines = steps_text.count('\n') + 1
                                row_height = max(row_height, steps_lines * 15)

                            if results_col is not None:
                                results_text = str(df.iloc[row_num - 1, results_col])
                                results_lines = results_text.count('\n') + 1
                                row_height = max(row_height, results_lines * 15)

                            # 设置行高
                            worksheet.set_row(row_num, row_height)

                    buffer.seek(0)

                    # 添加下载按钮
                    st.download_button(
                        label="下载测试用例 (Excel)",
                        data=buffer,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

                    # 显示解析到的测试用例数量
                    st.info(f"成功解析了 {len(data)} 条测试用例")
            except Exception as e:
                st.error(f"转换为Excel格式时出错: {str(e)}")
                # 提供Markdown格式作为备选
                st.download_button(
                    label="下载测试用例 (Markdown)",
                    data=result,
                    file_name="测试用例.md",
                    mime="text/markdown",
                )

    except Exception as e:
        st.error(f"生成测试用例时出错: {str(e)}")

        # 尝试使用非流式API作为备选方案
        try:
            with st.spinner("正在尝试替代方法..."):
                response = testcase_writer.run(task=task)

            if response:
                # 验证和格式化非流式输出
                formatted_response = validate_and_format_testcases(response, test_case_count)

                with response_container:
                    st.markdown(formatted_response)

                st.success("✅ 测试用例生成完成!")
                st.download_button(
                    label="下载测试用例",
                    data=formatted_response,
                    file_name="测试用例.md",
                    mime="text/markdown",
                )
        except Exception as e2:
            st.error(f"替代方法也失败: {str(e2)}")

elif submit_button and not user_input:
    st.error("请输入需求描述")

# 添加使用说明
with st.sidebar:
    st.header("使用说明")
    st.markdown("""
    1. 在文本框中输入详细的需求描述
    2. 根据需要调整高级选项和测试用例数量
    3. 点击"生成测试用例"按钮
    4. 等待AI生成测试用例
    5. 可以下载生成的测试用例（Excel、Markdown或JSON格式）
    """)

    st.header("关于")
    st.markdown("""
    本工具使用AI技术自动生成测试用例，帮助开发和测试团队提高效率。

    生成的测试用例包括：
    - 测试场景
    - 测试步骤
    - 预期结果
    - 测试数据建议
    """)
