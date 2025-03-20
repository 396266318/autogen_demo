import asyncio
import json
from typing import List, Tuple, Dict, Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from llama_index.core import SimpleDirectoryReader, Document

from pydantic import BaseModel, Field
from typing import Optional, List as PydanticList

from llms import model_client
from autogen_ext.models.openai import OpenAIChatCompletionClient
from prompt_tasks import REQUIREMENTS_ANALYZER_SYSTEM_MESSAGE


class BusinessRequirement(BaseModel):
    requirement_id: str = Field(..., description="需求编号")
    requirement_name: str = Field(..., description="业务需求名称")
    requirement_type: str = Field(..., description="需求类别:[功能需求/性能需求/安全需求/其它需求]")
    parent_requirement: Optional[str] = Field(None, description="父需求")
    module: str = Field(..., description="所属模块")
    requirement_level: str = Field(..., description="需求层级")
    reviewer: str = Field(..., description="评审人")
    estimated_hours: int = Field(..., description="预计完成工时")
    description: str = Field(..., description="需求描述")
    acceptance_criteria: str = Field(..., description="验收标准")


class BusinessRequirementList(BaseModel):
    requirements: PydanticList[BusinessRequirement] = Field(..., description="业务需求列表")


class RequirementAnalysisService:
    def __init__(self):
        self.model_client = model_client

    async def get_document_from_files(self, files: list[str]) -> str:
        """
        获取文件内容
        :param files: 文件列表
        :return: 文件内容
        """
        try:
            data = SimpleDirectoryReader(input_files=files).load_data()
            doc = Document(text="\n\n".join([d.text for d in data[0:]]))
            return doc.text
        except Exception as e:
            print(f"Error loading documents: {e}")
            raise

    async def _analyze_requirements_async(self, files: List[str]) -> Tuple[BusinessRequirementList, Dict[str, Any]]:
        """
        异步分析需求
        :param files: 文件路径列表
        :return: 需求分析结果
        """
        # 需求获取智能体
        requirement_acquisition_agent = AssistantAgent(
            name="requirement_acquisition_agent",
            model_client=self.model_client,
            tools=[self.get_document_from_files],
            system_message=f"调用工具获取文档内容，传递给工具的文件参数是：{files}",
            model_client_stream=False,
        )

        # 需求分析提示词
        req_analysis_prompt = REQUIREMENTS_ANALYZER_SYSTEM_MESSAGE

        # 需求分析智能体
        requirement_analysis_agent = AssistantAgent(
            name="requirement_analysis_agent",
            model_client=self.model_client,
            system_message=req_analysis_prompt,
            model_client_stream=False,
        )

        # 需求输出智能体的配置
        model_client2 = OpenAIChatCompletionClient(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-38391b6e2c59451ab98a0f2a6ccd1c83",
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
            },
        )

        # 需求输出智能体
        requirement_output_agent = AssistantAgent(
            name="requirement_output_agent",
            model_client=model_client2,
            system_message="""
            请根据需求分析报告进行详细的需求整理，尽量覆盖到报告中呈现所有的需求内容，每条需求信息都参考如下格式，生成合适条数的需求项。最终以 JSON 形式输出：
            requirements:
            requirement_id:[需求编号(业务缩写+需求类型+随机3位数字)]
            requirement_name:[需求名称]
            requirement_type:[功能需求/性能需求/安全需求/其它需求]
            parent_requirement:[该需求的上级需求]
            module:[所属的业务模块]
            requirement_level:需求层级[BR]
            reviewer:[需求助理]
            estimated_hours:[预计完成工时(整数类型)]
            description:[需求描述] 作为一名<某类型的用户>，我希望<达成某些目的>，这样可以<开发的价值>。\n 验收标准：[明确的验收标准]
            acceptance_criteria:[验收标准]
            """,
            model_client_stream=False,
        )

        # 创建团队
        source_termination = SourceMatchTermination(sources=["requirement_output_agent"])

        team = RoundRobinGroupChat(
            [requirement_acquisition_agent, requirement_analysis_agent, requirement_output_agent],
            termination_condition=source_termination
        )

        # 运行需求分析流程
        task_result = await team.run(task="开始需求分析")

        # 解析结果并返回
        try:
            result_json = json.loads(task_result.content)
            requirements = BusinessRequirementList(**result_json)
            return requirements, result_json
        except Exception as e:
            print(f"Error parsing requirements: {e}")
            print(f"Raw content: {task_result.content}")
            raise

    def analyze_requirements(self, files: List[str]) -> Tuple[BusinessRequirementList, Dict[str, Any]]:
        """
        同步分析需求的入口方法
        :param files: 文件路径列表
        :return: 需求分析结果
        """
        return asyncio.run(self._analyze_requirements_async(files))
