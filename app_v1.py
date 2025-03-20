import streamlit as st
import fitz  # PyMuPDF
import os
import time
import asyncio
from typing import Dict, Any
import io
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 设置页面配置
st.set_page_config(
    page_title="PDF需求解析系统",
    page_icon="📄",
    layout="wide"
)

# 导入模型客户端
from llms import model_client

# 定义系统消息
REQUIREMENTS_ANALYZER_SYSTEM_MESSAGE = """
你是一位专业的需求分析师，擅长从文档中提取和分析软件需求。
请分析提供的文本，识别并提取其中的需求信息，包括：

1. 功能需求：系统应该具备的功能
2. 非功能需求：性能、安全性、可用性等方面的需求
3. 用户场景：识别主要的用户场景和用例
4. 约束条件：任何技术或业务约束
5. 关键术语：解释文档中出现的关键术语和概念

请以结构化的方式回答，使用markdown格式。只提取确实存在于文本中的需求，不要添加猜测的内容。
"""

TESTCASE_WRITER_SYSTEM_MESSAGE = """
你是一位专业的测试工程师，擅长根据需求文档编写测试用例。
请基于提供的需求分析，生成详细的测试用例，包含以下字段：

1. 测试用例ID (格式: TC-XXX-NNN)
2. 测试用例标题
3. 前置条件
4. 测试步骤 (请使用编号列表)
5. 预期结果
6. 优先级 (高/中/低)

请以表格形式输出，确保测试用例覆盖关键功能和边界条件。
"""

# 初始化会话状态
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = ""
if 'analyzed_requirements' not in st.session_state:
    st.session_state.analyzed_requirements = None
if 'test_cases' not in st.session_state:
    st.session_state.test_cases = None
if 'processing_time' not in st.session_state:
    st.session_state.processing_time = {"extraction": 0, "analysis": 0, "test_cases": 0}

# 页面标题
st.title("📄 PDF需求解析与分析系统")
st.markdown("上传PDF文档，使用DeepSeek大模型解析需求信息")


# 从PDF提取文本
def extract_text_from_pdf(pdf_file) -> Dict[str, Any]:
    """从PDF文件中提取文本内容"""
    start_time = time.time()

    try:
        # 直接从内存加载PDF
        pdf_bytes = pdf_file.getvalue()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # 提取文本
        text_content = ""
        metadata = {
            "title": doc.metadata.get("title", "未知"),
            "author": doc.metadata.get("author", "未知"),
            "page_count": len(doc)
        }

        # 逐页提取文本
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content += page.get_text()

        # 确保资源释放
        doc.close()

        end_time = time.time()
        extraction_time = end_time - start_time

        return {
            "success": True,
            "text": text_content,
            "metadata": metadata,
            "processing_time": extraction_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# 安全运行异步代码的辅助函数
def run_async(coroutine):
    """安全地在Streamlit环境中运行异步代码"""
    try:
        # 尝试使用标准的asyncio.run
        return asyncio.run(coroutine)
    except RuntimeError as e:
        # 如果已有事件循环在运行，创建新的事件循环
        if "There is no current event loop in thread" in str(e) or "Event loop is running" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
        else:
            raise e  # 重新抛出其他RuntimeError


# 使用缓存创建分析器代理
@st.cache_resource
def get_requirements_analyzer():
    return AssistantAgent(
        name="requirements_analyzer",
        model_client=model_client,
        system_message=REQUIREMENTS_ANALYZER_SYSTEM_MESSAGE,
        model_client_stream=True,
    )


# 使用缓存创建测试用例生成器代理
@st.cache_resource
def get_testcase_writer():
    return AssistantAgent(
        name="testcase_writer",
        model_client=model_client,
        system_message=TESTCASE_WRITER_SYSTEM_MESSAGE,
        model_client_stream=True,
    )


# 使用DeepSeek模型分析需求
def analyze_requirements(text: str) -> Dict[str, Any]:
    """使用模型分析需求"""
    start_time = time.time()

    try:
        analyzer = get_requirements_analyzer()

        # 限制文本长度，避免超出token限制
        limited_text = text[:8000]
        user_message = f"""请分析以下从PDF文档提取的文本，识别并提取其中的需求信息：

        {limited_text}
        """

        # 定义异步函数处理响应
        async def process_response():
            response = await analyzer.generate_async(user_message)
            return response.content

        # 使用辅助函数运行异步代码
        analysis = run_async(process_response())

        end_time = time.time()
        analysis_time = end_time - start_time

        return {
            "success": True,
            "analysis": analysis,
            "processing_time": analysis_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"需求分析过程发生错误: {str(e)}"
        }


# 生成测试用例
def generate_test_cases(requirements: str) -> Dict[str, Any]:
    """使用模型生成测试用例"""
    start_time = time.time()

    try:
        testcase_writer = get_testcase_writer()

        user_message = f"""请基于以下需求分析，生成详细的测试用例：

        {requirements}
        """

        # 定义异步函数处理响应
        async def process_response():
            response = await testcase_writer.generate_async(user_message)
            return response.content

        # 使用辅助函数运行异步代码
        test_cases = run_async(process_response())

        end_time = time.time()
        generation_time = end_time - start_time

        return {
            "success": True,
            "test_cases": test_cases,
            "processing_time": generation_time
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"测试用例生成过程发生错误: {str(e)}"
        }


# 创建标签页
tab1, tab2, tab3 = st.tabs(["文档上传", "需求分析", "测试用例"])

# 标签页1：文档上传
with tab1:
    st.header("上传PDF文档")

    uploaded_file = st.file_uploader("选择PDF文件", type=["pdf"])

    if uploaded_file is not None:
        file_details = {
            "文件名": uploaded_file.name,
            "文件大小": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.write("文件信息:", file_details)

        if st.button("解析文档"):
            with st.spinner("正在提取文档内容..."):
                extraction_result = extract_text_from_pdf(uploaded_file)

                if extraction_result["success"]:
                    st.session_state.extracted_text = extraction_result["text"]
                    st.session_state.processing_time["extraction"] = extraction_result["processing_time"]

                    # 显示元数据
                    if "metadata" in extraction_result:
                        st.subheader("文档元数据")
                        st.json(extraction_result["metadata"])

                    # 显示提取的文本预览
                    st.subheader("提取的文本预览")
                    preview_length = min(500, len(extraction_result["text"]))
                    st.text_area("文本内容预览", extraction_result["text"][:preview_length] + "...", height=200)

                    # 显示处理时间
                    st.info(f"文本提取完成，耗时 {extraction_result['processing_time']:.2f} 秒")

                    # 自动进行需求分析
                    with st.spinner("正在分析需求..."):
                        analysis_result = analyze_requirements(extraction_result["text"])

                        if analysis_result["success"]:
                            st.session_state.analyzed_requirements = analysis_result["analysis"]
                            st.session_state.processing_time["analysis"] = analysis_result["processing_time"]
                            st.success(f"需求分析完成，耗时 {analysis_result['processing_time']:.2f} 秒")
                        else:
                            st.error(f"需求分析失败: {analysis_result['error']}")
                else:
                    st.error(f"文本提取失败: {extraction_result['error']}")

# 标签页2：需求分析
with tab2:
    st.header("需求分析结果")

    if st.session_state.analyzed_requirements:
        st.markdown(st.session_state.analyzed_requirements)

        # 显示处理时间
        st.info(f"需求分析耗时: {st.session_state.processing_time['analysis']:.2f} 秒")

        # 添加生成测试用例的按钮
        if st.button("生成测试用例"):
            with st.spinner("正在生成测试用例..."):
                test_case_result = generate_test_cases(st.session_state.analyzed_requirements)

                if test_case_result["success"]:
                    st.session_state.test_cases = test_case_result["test_cases"]
                    st.session_state.processing_time["test_cases"] = test_case_result["processing_time"]
                    st.success(f"测试用例生成完成，耗时 {test_case_result['processing_time']:.2f} 秒")
                    # 自动切换到测试用例标签页
                    st.experimental_rerun()
                else:
                    st.error(f"测试用例生成失败: {test_case_result['error']}")
    else:
        st.info("请先上传PDF文档并进行需求分析")

# 标签页3：测试用例
with tab3:
    st.header("测试用例")

    if st.session_state.test_cases:
        st.markdown(st.session_state.test_cases)

        # 显示处理时间
        st.info(f"测试用例生成耗时: {st.session_state.processing_time['test_cases']:.2f} 秒")

        # 添加导出功能
        if st.button("导出测试用例"):
            st.download_button(
                label="下载MD文件",
                data=st.session_state.test_cases,
                file_name="测试用例.md",
                mime="text/markdown"
            )
    else:
        st.info("请先生成测试用例")
