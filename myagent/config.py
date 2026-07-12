from dotenv import load_dotenv, find_dotenv
import os
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent   # 正确的导入

# 加载环境变量
load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
api_key = os.getenv("OPENAI_API_KEY")
api_url = os.getenv("OPENAI_BASE_URL")

# 修正模型名
model = init_chat_model(
    model="deepseek-chat",          # 修正模型名称
    model_provider="openai",
    api_key=api_key,
    base_url=api_url,
    max_tokens=1024,
    temperature=0.7
)

checkpointer = InMemorySaver()

# 使用 create_react_agent，参数名 prompt 而不是 system_prompt
agent = create_agent(
    model=model,          # 工具列表
    temperature=0.7,
    max_tokens=1024
)

system_prompt="""你是一个react模型智能体"""
# 调用 agent，输入必须是一个字典，包含 "messages" 键
print (api_url)
print(api_key)
response = agent.invoke(
    {"messages": 
     [{"role": "user", "content": "请计算一下 12 乘以 8 等于多少？",
       "role":"system","content": system_prompt
       
       
       }]}
)

# 正确获取最后一条 AI 消息的内容
final_message = response["messages"][-1]
print(final_message.content)