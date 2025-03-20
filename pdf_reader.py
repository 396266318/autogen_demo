# -*- coding: utf-8 -*-
"""
@Project : autogen_demo
@File    : pdf_reader.py
@Author  : xuan
@Date    : 2025/3/20
"""
import os
import fitz  # PyMuPDF
from typing import Optional, Tuple


def ensure_data_dir():
    """确保data目录存在"""
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def save_uploaded_pdf(uploaded_file) -> Tuple[bool, str]:
    """
    保存上传的PDF文件到data目录
    Args:
        uploaded_file: Streamlit上传的文件对象
    Returns:
        Tuple[bool, str]: (是否成功, 文件路径或错误信息)
    """
    try:
        # 确保data目录存在
        data_dir = ensure_data_dir()
        # 构建文件路径
        file_path = os.path.join(data_dir, uploaded_file.name)

        # 写入文件
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return True, file_path
    except Exception as e:
        return False, f"保存文件失败: {str(e)}"


def read_pdf_content(file_path: str) -> Tuple[bool, str]:
    """
    读取PDF文件内容
    Args:
        file_path: PDF文件路径
    Returns:
        Tuple[bool, str]: (是否成功, 文本内容或错误信息)
    """
    try:
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"

        # 读取PDF内容
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()

        if not text.strip():
            return False, "PDF文件未包含可提取的文本内容"

        return True, text
    except Exception as e:
        return False, f"读取PDF内容失败: {str(e)}"
