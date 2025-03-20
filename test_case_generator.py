import asyncio
import json
import uuid
from typing import List, Dict, Any

from autogen_agentchat.agents import AssistantAgent
from llms import model_client

from requirements_analysis import BusinessRequirementList


class TestCaseGeneratorService:
    def __init__(self):
        self.model_client = model_client

    async def _generate_test_cases_async(self, requirements: BusinessRequirementList) -> List[Dict[str, Any]]:
        """
        异步生成测试用例
        :param requirements: 需求列表
        :return: 测试用例列表
        """
        # 创建测试用例生成智能体
        test_case_agent = AssistantAgent(
            name="test_case_generator",
            model_client=self.model_client,
            system_message="""
            你是一位专业的测试用例设计师，负责根据业务需求创建高质量的测试用例。请根据提供的需求信息，为每个需求设计至少一个测试用例。

            测试用例应包含以下字段：
            1. case_id: 测试用例ID，格式为TC-XXX (XXX为三位数字)
            2. case_name: 测试用例名称
            3. related_requirement: 关联的需求ID
            4. priority: 优先级 (高/中/低)
            5. preconditions: 前置条件
            6. steps: 测试步骤 (详细描述每个步骤)
            7. expected_results: 预期结果 (与测试步骤相对应)
            8. test_type: 测试类型 (功能测试/性能测试/安全测试/接口测试/UI测试等)

            请确保:
            - 测试用例覆盖需求的核心功能点
            - 包含正向和异常场景测试
            - 测试步骤清晰、可执行
            - 预期结果具体、可验证
            - 测试用例与需求有明确的关联性

            请以JSON格式输出测试用例列表。
            """,
            model_client_stream=False,
        )

        # 准备输入数据
        requirements_json = {
            "requirements": [req.model_dump() for req in requirements.requirements]
        }
        requirements_str = json.dumps(requirements_json, ensure_ascii=False)

        # 执行测试用例生成
        response = await test_case_agent.generate_response(
            messages=[{
                "role": "user",
                "content": f"请根据以下需求生成测试用例：\n\n{requirements_str}"
            }]
        )

        # 解析测试用例结果
        try:
            # 尝试提取JSON内容
            content = response.content
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                test_cases_data = json.loads(json_str)

                if isinstance(test_cases_data, dict) and "test_cases" in test_cases_data:
                    return test_cases_data["test_cases"]
                elif isinstance(test_cases_data, list):
                    return test_cases_data
                else:
                    # 尝试提取顶层键
                    for key in test_cases_data:
                        if isinstance(test_cases_data[key], list):
                            return test_cases_data[key]

            # 如果无法解析JSON，尝试生成基本测试用例
            basic_test_cases = []
            for req in requirements.requirements:
                test_case = {
                    "case_id": f"TC-{str(uuid.uuid4())[:3].upper()}",
                    "case_name": f"测试 {req.requirement_name}",
                    "related_requirement": req.requirement_id,
                    "priority": "中",
                    "preconditions": "系统环境已准备好",
                    "steps": "1. 准备测试数据\n2. 执行测试流程\n3. 验证结果",
                    "expected_results": "结果符合需求验收标准",
                    "test_type": "功能测试"
                }
                basic_test_cases.append(test_case)
            return basic_test_cases

        except Exception as e:
            print(f"Error parsing test cases: {e}")
            print(f"Raw content: {response.content}")
            # 创建基本的测试用例作为备选
            basic_test_cases = []
            for req in requirements.requirements:
                test_case = {
                    "case_id": f"TC-{str(uuid.uuid4())[:3].upper()}",
                    "case_name": f"测试 {req.requirement_name}",
                    "related_requirement": req.requirement_id,
                    "priority": "中",
                    "preconditions": "系统环境已准备好",
                    "steps": "1. 准备测试数据\n2. 执行测试流程\n3. 验证结果",
                    "expected_results": "结果符合需求验收标准",
                    "test_type": "功能测试"
                }
                basic_test_cases.append(test_case)
            return basic_test_cases

    def generate_test_cases(self, requirements: BusinessRequirementList) -> List[Dict[str, Any]]:
        """
        同步生成测试用例的入口方法
        :param requirements: 需求列表
        :return: 测试用例列表
        """
        return asyncio.run(self._generate_test_cases_async(requirements))
