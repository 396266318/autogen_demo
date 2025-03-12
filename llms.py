from autogen_ext.models.openai import OpenAIChatCompletionClient

# model_client = OpenAIChatCompletionClient(
#     # model="deepseek-ai/DeepSeek-V3",
#     model="Qwen/QwQ-32B",
#     base_url="https://api.siliconflow.cn/v1",
#     api_key="sk-okvrtxp",
#     model_info={
#         "vision": False,
#         "function_calling": True,
#         "json_output": True,
#         "family": "unknown",
#     },
# )

model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key="sk-",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "unknown",
    },
)
