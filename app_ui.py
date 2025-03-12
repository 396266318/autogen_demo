# -*- coding: utf-8 -*-
"""
@Project : AICode
@File    : app_ui.py
@Author  : zt20283
@Date    : 2025/3/12 08:12
"""
import re
import pandas as pd
import streamlit as st
import asyncio
from io import BytesIO
from datetime import datetime
from typing import List, Optional, Any, Union
import json
import hashlib

# 设置页面配置（必须是第一个Streamlit命令）
st.set_page_config(
    page_title="AI测试用例生成器",
    page_icon="✅",
    layout="wide"
)

from autogen_agentchat.agents import AssistantAgent
from pydantic import BaseModel, Field

from llms import model_client


# ================= Pydantic 模型 =================
class TestStep(BaseModel):
    """测试步骤模型"""
    step_number: int = Field(..., description="步骤编号")
    action: str = Field(..., description="操作步骤")


class TestCase(BaseModel):
    """测试用例模型"""
    case_id: str = Field(..., description="用例ID")
    priority: str = Field(..., description="优先级")
    title: str = Field(..., description="用例标题")
    precondition: str = Field(..., description="前置条件")
    steps: str = Field(..., description="步骤")
    expected_result: str = Field(..., description="预期结果")


class TestCaseList(BaseModel):
    """测试用例列表模型"""
    test_cases: List[TestCase] = Field(default_factory=list, description="测试用例列表")


# ================= 测试用例生成 =================
def extract_keywords(text, max_words=3):
    """从需求中提取关键词用于生成默认测试标题"""
    # 简单实现：取前N个字符
    words = text.strip().split()[:10]
    return " ".join(words[:max_words])


def generate_test_title(requirement, index):
    """根据需求和索引生成测试用例标题"""
    keywords = extract_keywords(requirement)
    return f"测试{keywords}的功能场景 {index}"


async def generate_test_cases(requirement: str, count: int = 3) -> TestCaseList:
    """
    基于需求生成测试用例
    :param requirement: 需求内容
    :param count: 测试用例数量
    :return: 结构化的测试用例列表
    """
    try:
        # 创建测试用例生成智能体
        test_agent = AssistantAgent(
            name="testcase_generator",
            model_client=model_client,
            system_message=f"""
            你是一个专业的测试用例生成专家。根据提供的需求描述，生成{count}个详细的测试用例，每个测试用例包含以下字段：
            - case_id: 用例ID，格式为TC-XXX-NNN，其中XXX为功能缩写，NNN为序号
            - priority: 优先级，从P0(最高)到P3(最低)
            - title: 用例标题，简明扼要描述测试内容
            - precondition: 前置条件，测试执行前需满足的条件
            - steps: 测试步骤，详细的操作步骤
            - expected_result: 预期结果，执行步骤后应观察到的结果

            请以JSON格式输出，确保输出可以被解析为有效的JSON。格式如下:
            ```json
            {
            "test_cases": [
                {
            "case_id": "TC-REG-001",
                  "priority": "P0",
                  "title": "验证用户注册功能 - 有效输入",
                  "precondition": "用户未登录，访问注册页面",
                  "steps": "1. 输入有效用户名\\n2. 输入符合要求的密码\\n3. 输入有效邮箱\\n4. 点击注册按钮",
                  "expected_result": "注册成功，提示注册成功信息"
                }
              ]
            }
            ```
            """,
        )

        # 直接运行而不是使用stream
        task = f"""请根据以下需求生成{count}个测试用例：\n{requirement}"""

        # 使用线程池执行agent.run以避免阻塞
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: test_agent.run(task=task))

        # 解析JSON响应
        if isinstance(response, str):
            # 尝试提取JSON部分
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response

            # 清理可能的非JSON内容
            json_str = re.sub(r'^[^{]*', '', json_str)
            json_str = re.sub(r'[^}]*$', '', json_str)

            try:
                data = json.loads(json_str)
                return TestCaseList(**data)
            except json.JSONDecodeError as je:
                st.error(f"JSON解析失败: {str(je)}")
                # 创建一些示例测试用例以保证程序继续运行
                return create_example_test_cases(count, requirement)

        return TestCaseList(test_cases=[])
    except Exception as e:
        st.error(f"生成测试用例失败: {str(e)}")
        # 返回示例用例作为默认值
        return create_example_test_cases(count, requirement)


def create_example_test_cases(count: int, requirement: str) -> TestCaseList:
    """创建示例测试用例（用于错误恢复）"""
    test_cases = []

    # 尝试从需求中提取功能关键词
    keywords = re.sub(r'[^\w\s]', '', requirement.split('\n')[0])[:20]

    # 功能类型映射
    if '登录' in requirement or '注册' in requirement:
        feature_code = 'REG'
    elif '搜索' in requirement:
        feature_code = 'SRCH'
    elif '购买' in requirement or '支付' in requirement:
        feature_code = 'PAY'
    else:
        feature_code = 'FUNC'

    # 通用测试场景
    scenarios = [
        "正常功能验证",
        "边界条件测试",
        "异常情况处理",
        "性能测试",
        "安全性测试",
        "兼容性测试"
    ]

    # 创建测试用例
    for i in range(1, count + 1):
        scenario_index = min(i - 1, len(scenarios) - 1)
        title = f"{scenarios[scenario_index]} - {keywords}"

        test_cases.append(
            TestCase(
                case_id=f"TC-{feature_code}-{i:03d}",
                priority=f"P{(i % 3)}",
                title=title,
                precondition="系统处于可测试状态",
                steps=f"1. 准备测试环境\n2. 执行测试操作\n3. 验证结果",
                expected_result="测试通过，功能正常工作"
            )
        )
    return TestCaseList(test_cases=test_cases)


# ================= Excel 导出功能 =================
def test_cases_to_excel(test_cases: TestCaseList):
    """将测试用例转换为Excel"""
    data = []

    for case in test_cases.test_cases:
        case_data = {
            "用例ID": case.case_id,
            "优先级": case.priority,
            "标题": case.title,
            "前置条件": case.precondition,
            "步骤": case.steps,
            "预期结果": case.expected_result
        }
        data.append(case_data)

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return output


def get_current_time():
    """获取当前时间"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


# ================= Streamlit界面 =================
def main():
    st.title("🧪 AI测试用例生成器")
    st.markdown("基于DeepSeek大语言模型和Pydantic结构化输出，为您生成高质量测试用例")

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
            "测试优先级基准",
            ["高", "中", "低"],
            index=0
        )

        # 添加测试用例数量控制
        test_case_count = st.number_input(
            "生成测试用例数量",
            min_value=1,
            max_value=10,
            value=3,
            step=1,
            help="指定需要生成的测试用例数量"
        )

        include_edge_cases = st.checkbox("包含边界情况", value=True)
        include_negative_tests = st.checkbox("包含负面测试", value=True)

    # 提交按钮
    submit_button = st.button("生成测试用例")

    # 处理提交
    if submit_button and user_input:
        # 创建容器用于显示生成内容
        response_container = st.container()

        try:
            with st.spinner("AI正在分析需求并生成结构化测试用例..."):
                # 准备完整的任务描述
                full_requirement = f"""
                {user_input}

                测试级别: {test_level}
                测试优先级: {test_priority}
                包含边界情况: {'是' if include_edge_cases else '否'}
                包含负面测试: {'是' if include_negative_tests else '否'}
                """

                # 异步调用测试用例生成函数
                # 创建新的事件循环来运行异步函数
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                test_cases = loop.run_until_complete(generate_test_cases(full_requirement, test_case_count))
                loop.close()

                # 生成分析报告
                analysis_result = f"""
                # 需求分析与测试用例

                ## 原始需求
                {user_input}

                ## 测试级别
                {test_level}

                ## 测试用例列表
                """

                for i, case in enumerate(test_cases.test_cases, 1):
                    analysis_result += f"""
                    ### 用例{i}: {case.title}

                    - **用例ID**: {case.case_id}
                    - **优先级**: {case.priority}

                    **前置条件**:
                    {case.precondition}

                    **步骤**:
                    {case.steps}

                    **预期结果**:
                    {case.expected_result}

                    ---
                    """

                st.success("✅ 测试用例生成完成!")

                # 显示结构化测试用例
                if test_cases and test_cases.test_cases:
                    st.subheader("📊 结构化测试用例")

                    # 创建表格显示测试用例
                    test_case_data = []
                    for case in test_cases.test_cases:
                        test_case_data.append({
                            "用例ID": case.case_id,
                            "优先级": case.priority,
                            "标题": case.title
                        })

                    st.table(pd.DataFrame(test_case_data))

                    with response_container:
                        for i, case in enumerate(test_cases.test_cases):
                            # 使用实际的用例标题，而非固定文本
                            with st.expander(f"{case.title}", expanded=(i == 0)):
                                st.write(f"**用例ID**: {case.case_id}")
                                st.write(f"**优先级**: {case.priority}")
                                st.write(f"**前置条件**: {case.precondition}")
                                st.write(f"**步骤**: {case.steps}")
                                st.write(f"**预期结果**: {case.expected_result}")

                    # 下载按钮
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="下载测试用例报告(Markdown)",
                            data=analysis_result,
                            file_name=f"testcases_{get_current_time()}.md",
                            mime="text/markdown"
                        )
                    with col2:
                        try:
                            excel_data = test_cases_to_excel(test_cases)
                            st.download_button(
                                label="下载测试用例(Excel)",
                                data=excel_data,
                                file_name=f"testcases_{get_current_time()}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        except Exception as e:
                            st.error(f"转换Excel失败：{str(e)}")
                else:
                    st.warning("未能生成有效的测试用例，请尝试修改需求描述或调整高级选项")

        except Exception as e:
            st.error(f"测试用例生成失败：{str(e)}")

            # 显示错误信息并提供帮助
            st.info("这可能是由于临时网络问题或API限制导致的。请尝试重新提交或稍后再试。")

    elif submit_button and not user_input:
        st.error("请输入需求描述")

    # 添加使用说明
    with st.sidebar:
        st.header("使用说明")
        st.markdown("""
        ### 使用步骤
        1. 在文本框中输入详细的需求描述
        2. 根据需要调整高级选项和测试用例数量
        3. 点击"生成测试用例"按钮
        4. 等待AI分析并生成测试用例
        5. 下载Excel或Markdown格式的测试用例

        ### 测试用例字段
        - **用例ID**: 唯一标识符
        - **优先级**: 测试用例的重要程度
        - **标题**: 简明扼要的用例描述
        - **前置条件**: 执行测试前的环境设置
        - **步骤**: 详细的测试执行步骤
        - **预期结果**: 成功执行后应该观察到的结果
        """)

        st.header("关于")
        st.markdown("""
        本工具基于先进的大语言模型进行需求分析和测试用例生成。

        技术栈:
        - DeepSeek大语言模型
        - Autogen智能代理框架
        - Pydantic结构化数据
        - Streamlit交互界面
        - Pandas数据处理

        主要特点:
        - 结构化测试用例输出
        - 自动生成Excel测试文档
        - 高效异步处理
        - 智能边界条件识别
        """)


if __name__ == "__main__":
    main()
