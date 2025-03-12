# -*- conding: utf-8 -*-
"""
@Project : AICode
@File    : ui.py
@Author  : xuan
@Date    : 2025/3/7 17:16
"""
import asyncio
import re
import streamlit as st
from autogen_agentchat.agents import AssistantAgent
from llms import model_client
from testcase_tasks import TESTCASE_WRITER_SYSTEM_MESSAGE

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
        index=0
    )

    test_priority = st.selectbox(
        "测试优先级",
        ["高", "中", "低"],
        index=1
    )

    # 添加测试用例数量控制
    test_case_count = st.number_input(
        "生成测试用例数量",
        min_value=1,
        max_value=20,
        value=3,
        step=1,
        help="指定需要生成的测试用例数量"
    )

    include_edge_cases = st.checkbox("包含边界情况", value=True)
    include_negative_tests = st.checkbox("包含负面测试", value=True)

# 提交按钮
submit_button = st.button("生成测试用例")


# 验证和格式化测试用例函数
def validate_and_format_testcases(raw_output, expected_count):
    """验证测试用例数量并格式化输出"""
    # 查找所有测试用例ID
    case_ids = re.findall(r'(用例ID|test case ID)[:：]\s*([A-Z_0-9]+)', raw_output, re.IGNORECASE)

    # 构建格式化输出
    formatted_output = raw_output

    # 检查用例数量
    if len(case_ids) != expected_count:
        warning = f"\n\n> ⚠️ **警告**: 生成了 {len(case_ids)} 条测试用例，但要求是 {expected_count} 条。"
        formatted_output += warning

    # 检查是否有重复ID
    unique_ids = set([id[1] for id in case_ids])
    if len(unique_ids) != len(case_ids):
        warning = "\n\n> ⚠️ **警告**: 存在重复的测试用例ID，请检查。"
        formatted_output += warning

    return formatted_output


# 处理提交
if submit_button and user_input:
    # 准备任务描述
    task = f"""
    需求描述: {user_input}

    测试级别: {test_level}
    测试优先级: {test_priority}
    包含边界情况: {'是' if include_edge_cases else '否'}
    包含负面测试: {'是' if include_negative_tests else '否'}

    【重要】请严格生成 {test_case_count} 条测试用例，不多不少。每个用例ID必须唯一。

    请根据以上需求生成结构化的测试用例，使用清晰的Markdown格式。
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

        # 添加下载按钮
        st.download_button(
            label="下载测试用例",
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
    5. 可以下载生成的测试用例
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
