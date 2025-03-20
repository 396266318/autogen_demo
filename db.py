import os
import sqlite3
from sqlite3 import Error
from typing import Dict, Any, List, Optional




def create_connection():
    """
    创建链接db
    """
    try:
        conn = sqlite3.connect("ai_db.sqlite3")
        return conn
    except Error as e:
        print(f"Error creating connection: {e}")
        return None


class BusinessRequirementCRUD:
    @staticmethod
    def create(requirement):
        sql = """
        INSERT INTO business_requirement (
            requirement_id, requirement_name, requirement_type, parent_requirement,
            module, requirement_level, reviewer, estimated_hours, description, acceptance_criteria
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    requirement["requirement_id"],
                    requirement["requirement_name"],
                    requirement["requirement_type"],
                    requirement["parent_requirement"],
                    requirement["module"],
                    requirement["requirement_level"],
                    requirement["reviewer"],
                    requirement["estimated_hours"],
                    requirement["description"],
                    requirement["acceptance_criteria"]
                ))
                conn.commit()
                return cursor.lastrowid
        except Error as e:
            print(f"Error creating requirement: {e}")
            raise e

    @staticmethod
    def read_all():
        sql = """SELECT * FROM business_requirement"""
        try:
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()

                # 获取列名
                column_names = [description[0] for description in cursor.description]

                # 将结果转换为字典列表
                result = []
                for row in rows:
                    result.append(dict(zip(column_names, row)))

                return result
        except Error as e:
            print(f"Error reading requirements: {e}")
            return []

    @staticmethod
    def read_by_id(requirement_id):
        sql = """SELECT * FROM business_requirement WHERE requirement_id = ?"""
        try:
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (requirement_id,))
                row = cursor.fetchone()

                if row:
                    # 获取列名
                    column_names = [description[0] for description in cursor.description]
                    # 将结果转换为字典
                    return dict(zip(column_names, row))
                return None
        except Error as e:
            print(f"Error reading requirement: {e}")
            return None

    @staticmethod
    def update(requirement):
        sql = """
        UPDATE business_requirement SET
            requirement_name = ?,
            requirement_type = ?,
            parent_requirement = ?,
            module = ?,
            requirement_level = ?,
            reviewer = ?,
            estimated_hours = ?,
            description = ?,
            acceptance_criteria = ?
        WHERE requirement_id = ?
        """
        try:
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    requirement["requirement_name"],
                    requirement["requirement_type"],
                    requirement["parent_requirement"],
                    requirement["module"],
                    requirement["requirement_level"],
                    requirement["reviewer"],
                    requirement["estimated_hours"],
                    requirement["description"],
                    requirement["acceptance_criteria"],
                    requirement["requirement_id"]
                ))
                conn.commit()
                return cursor.rowcount
        except Error as e:
            print(f"Error updating requirement: {e}")
            raise e

    @staticmethod
    def delete(requirement_id):
        sql = """DELETE FROM business_requirement WHERE requirement_id = ?"""
        try:
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (requirement_id,))
                conn.commit()
                return cursor.rowcount
        except Error as e:
            print(f"Error deleting requirement: {e}")
            raise e
