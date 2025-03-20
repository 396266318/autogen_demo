# -*- conding: utf-8 -*-
"""
@Project : autogen_demo
@File    : initialize_db.py
@Author  : zt20283
@Date    : 2025/3/19 11:12
"""
import sqlite3
from sqlite3 import Error

def create_connection():
    """创建 SQLite 数据库连接"""
    try:
        conn = sqlite3.connect("ai_db.sqlite3")
        return conn
    except Error as e:
        print(f"Error creating connection: {e}")
        return None

def initialize_database():
    """初始化数据库，创建 business_requirement 表"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS business_requirement (
        requirement_id TEXT PRIMARY KEY,
        requirement_name TEXT NOT NULL,
        requirement_type TEXT NOT NULL,
        parent_requirement TEXT,
        module TEXT NOT NULL,
        requirement_level TEXT NOT NULL,
        reviewer TEXT,
        estimated_hours INTEGER,
        description TEXT,
        acceptance_criteria TEXT
    );
    """
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            conn.commit()
            print("Table `business_requirement` created successfully.")
    except Error as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    initialize_database()