import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import ToolCallSummaryMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from docling.document_converter import DocumentConverter
from llama_index.core import SimpleDirectoryReader, Document

from llms import model_client

from pydantic import BaseModel, Field
from typing import Optional


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
    requirements: list[BusinessRequirement] = Field(..., description="业务需求列表")


async def get_document_from_file():
    """获取需求文件内容"""
    source = "05-ucmp_V1.1.8.pdf"  # document per local path or URL
    converter = DocumentConverter()
    result = converter.convert(source)
    return result.document.export_to_markdown()


async def get_document_from_llama_index_file(files: list[str]):
    """
    获取文件内容
    :param files: 文件列表
    :return:
    """
    data = SimpleDirectoryReader(input_files=files).load_data()
    doc = Document(text="\n\n".join([d.text for d in data[0:]]))
    return doc.text


async def structure_requirement(content: str) -> BusinessRequirementList:
    """
    对需求列表内容进行结构化
    :param content: 需求内容列表
    :return:
    """
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIModel

    model = OpenAIModel(
        'deepseek-chat',
        base_url='https://api.deepseek.com',
        api_key='sk-38391b6e2c59451ab98a0f2a6ccd1c83',
    )
    agent = Agent(model, system_prompt="对用户输入的内容进行结构化输出", result_type=BusinessRequirementList)
    result = await agent.run(user_prompt=content)
    return result.data


async def insert_into_database(requirements: BusinessRequirementList):
    """将需求数据插入数据库"""
    from db import BusinessRequirementCRUD
    for requirement in requirements.requirements:
        BusinessRequirementCRUD.create(requirement.model_dump())
    return f"完成【{len(requirements.requirements)}】条需求入库。"


class RequirementAnalysisAgent:
    def __init__(self, files: list[str]):
        self.files = files

    async def create_team(self) -> RoundRobinGroupChat:
        # 需求获取智能体（如果文档过大，可以分批读取）
        requirement_acquisition_agent = AssistantAgent(
            name="requirement_acquisition_agent",
            model_client=model_client,
            tools=[get_document_from_llama_index_file],
            system_message=f"调用工具获取文档内容，传递给工具的文件参数是：{self.files}",
            model_client_stream=False,
        )

        req_analysis_prompt = """
        根据如下格式的需求文档，进行需求分析，输出需求分析报告：

        ## 1. Profile
        **角色**：高级测试需求分析师  
        **核心能力**：
        - 需求结构化拆解与可测试性转化
        - 风险驱动的测试策略设计
        - 全链路需求追溯能力

        ## 2. 需求结构化框架
        ### 2.1 功能需求分解
        ```markdown
        - [必选] 使用Markdown无序列表展示功能模块
        - [必选] 标注规则：
          - 核心功能：★（影响核心业务流程）
          - 高风险功能：⚠️（含外部依赖/复杂逻辑）
        - 示例：
          - 订单风控引擎（★⚠️）：实时交易风险评估
        ```

        ### 2.2 非功能需求矩阵
        ```markdown
        | 维度       | 指标项                 | 验收标准            |
        |------------|------------------------|---------------------|
        | 性能       | 支付接口响应时间       | ≤1.2s(P99)         |
        | 安全性     | 敏感信息加密           | AES-256+SSL/TLS1.3 |
        ```

        ### 2.3 业务规则提取模板
        ```markdown
        - 规则编号：BR-{模块缩写}-001
        - 触发条件：当[条件]时
        - 系统行为：应执行[动作]
        - 示例：
          BR-PAY-003：当连续验证失败3次时，锁定账户1小时
        ```

        ## 3. 深度分析指令
        ### 3.1 可测试性评估表
        ```markdown
        | 需求ID | 可测性(1-5) | 缺陷描述               | 优化建议            |
        |--------|-------------|------------------------|---------------------|
        | F-012  | 2           | "良好的用户体验"无量化 | 增加页面加载进度条 |
        ```

        ### 3.2 测试策略蓝图
        ```markdown
        - [分层策略] 
          █ 单元测试(30%) → 接口测试(40%) → E2E测试(20%) → 探索测试(10%)
        - [工具链] 
          Jest(单元) + Postman(接口) + Cypress(E2E) + OWASP ZAP(安全)
        ```

        ### 3.3 风险热点地图
        ```markdown
        🔥 高风险区（立即处理）：
        - 第三方身份认证服务降级
        - 支付金额计算精度丢失

        🛡️ 缓解措施：
        - 实施接口mock方案
        - 增加金额四舍五入审计日志
        ```

        ## 4. 增强版输出规范
        ### 4.1 文档结构
        ```markdown
        ## 四、测试追踪矩阵
        | 需求ID | 测试类型 | 用例数 | 自动化率 | 验收证据 |
        |--------|----------|--------|----------|----------|

        ## 五、环境拓扑图
        - 测试集群配置：4C8G*3节点
        - 特殊设备：iOS/Android真机测试架
        ```

        ### 4.2 用例设计规范
        ```markdown
        **TC-风险场景验证**：
        - 破坏性测试步骤：
          1. 模拟第三方API返回500错误
          2. 连续发送异常报文10次
        - 预期韧性表现：
          - 系统自动切换备用服务节点
          - 触发告警通知运维人员
        ```

        ## 5. 智能增强模块
        ```markdown
        [!AI辅助提示] 建议执行：
        1. 使用决策表分析登录模块的组合场景
        2. 对核心API进行Swagger规范校验
        3. 生成需求覆盖率热力图（使用JaCoCo）
        ```
        """
        # 需求分析智能体
        requirement_analysis_agent = AssistantAgent(
            name="requirement_analysis_agent",
            model_client=model_client,
            system_message=req_analysis_prompt,
            model_client_stream=False,
        )
        model_client2 = OpenAIChatCompletionClient(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-38391b6e2c59451ab98a0f2a6ccd1c83",
            response_format=BusinessRequirementList,  # type: ignore
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
            reviewer:[田老师]
            estimated_hours:[预计完成工时(整数类型)]
            description:[需求描述] 作为一名<某类型的用户>，我希望<达成某些目的>，这样可以<开发的价值>。\n 验收标准：[明确的验收标准]
            acceptance_criteria:[验收标准]
            """,
            model_client_stream=False,
        )

        # 需求信息结构化
        # requirement_structure_agent = AssistantAgent(
        #     name="requirement_structure_agent",
        #     model_client=model_client,
        #     tools=[structure_requirement],
        #     system_message="调用工具对`requirement_output_agent`输出的内容进行格式化",
        #     model_client_stream=False,
        # )

        # 需求入库智能体
        requirement_into_db_agent = AssistantAgent(
            name="requirement_into_db_agent",
            model_client=model_client,
            tools=[insert_into_database],
            system_message="""调用工具将需求数据插入到数据库""",
            model_client_stream=False,
        )

        source_termination = SourceMatchTermination(sources=["requirement_into_db_agent"])

        team = RoundRobinGroupChat([requirement_acquisition_agent, requirement_analysis_agent, requirement_output_agent,
                                    requirement_into_db_agent],
                                   termination_condition=source_termination)
        return team


async def main():
    agent = RequirementAnalysisAgent(files=["api_doc.pdf"])
    team = await agent.create_team()
    async for message in team.run_stream(task="开始需求分析"):  # type: ignore
        if message.source == "requirement_acquisition_agent" and isinstance(message, ToolCallSummaryMessage):
            print("获取到的需求内容如下：" + message.content)


if __name__ == "__main__":
    asyncio.run(main())
