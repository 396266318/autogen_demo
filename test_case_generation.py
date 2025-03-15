import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from llms import model_client

from testcase_tasks import PDS_TASK, TESTCASE_WRITER_SYSTEM_MESSAGE

testcase_writer = AssistantAgent(
    name="testcase_writer",
    model_client=model_client,
    system_message=TESTCASE_WRITER_SYSTEM_MESSAGE,
    model_client_stream=True,
)


async def main():
    await Console(testcase_writer.run_stream(task=PDS_TASK))


if __name__ == "__main__":
    asyncio.run(main())
