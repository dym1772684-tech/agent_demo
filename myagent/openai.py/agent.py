#langgraph.graph import StateGraph  
#InMemortStroe InMemorySaver 解决
import os
import operator
from typing_extensions import TypedDict, Annotated
from typing import TypedDict
from dataclasses import dataclass, field
from typing import Any, Dict
from typing import TypedDict
from dataclasses import dataclass
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel#类型检查
from typing import TypedDict#注释
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent,AgentState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AnyMessage,HumanMessage, BaseMessage,AIMessage,SystemMessage
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call,dynamic_prompt,AgentMiddleware
# 1. 加载环境变量
from langchain_core.messages.ai import AIMessageChunk
from langgraph.graph.state import StateGraph
from langgraph.types import StreamPart
from langgraph.graph import StateGraph,MessagesState,START,END
load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")


class MessagesState(TypedDict):
    messages:Annotated[list[AnyMessage],operator.add]#Annotated 用来注释类型，额外说明，operator.add是一个运算符，表示这个字段是可以累加的
    llm_calls:int
model=init_chat_model(
    model="deepseek-chat",
    model_provider="openai",  # 明确指定 provider，防止 LangChain 误判
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    max_tokens=1024,
    timeout=30,
    max_retries=3,
)
model_with_tools=model.bind_tools(tools=[])
def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            model_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get('llm_calls', 0) + 1
    }##用来统计调用次数 也就是经过这个函数节点 ，做出了什么改变
class CustomState(AgentState):
    user_preferences:dict
@dataclass
class Context():
   user_role:str
# 模拟一些基础工具，防止 import 报错（请替换为你真实的 tool 导入）
from langchain_core.tools import tool
# @wrap_tool_call 中间件就是加保险 也就是加需求 dynamic_prompt
@wrap_model_call
def choose_model_middleware( request: ModelRequest, handler):
         print("="*60)
         print("✅ 中间件成功执行！")
         print("1. model：", request.model)
         print("2. messages：", request.messages)
         print("3. system_message：", request.system_message)
         print("4. system_prompt：", request.system_prompt)  # 官方兼容字段
         print("5. tool_choice：", request.tool_choice)
         print("6. tools：", request.tools)
         print("7. response_format：", request.response_format)
         print("8. state：", request.state)
         print("9. runtime：", request.runtime)
         print("10. model_settings：", request.model_settings)
         print("="*60) 
        # 从 request 的 state 中获取当前对话的历史消息列表
         messages = request.state.get("messages", [])
         msg_count = len(messages)
        
        # 如果对话轮数过多（大于5条），切换到更严谨的低智能体温度配置，或者切换到另一个模型
         if msg_count > 5:
                new_model = init_chat_model(
            model="deepseek-chat",
            model_provider="openai",  # 明确指定 provider，防止 LangChain 误判
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=1024,
            timeout=30,
            max_retries=3,
        )
            # 使用 request.override 动态替换底层的 model 实例
                return handler(request.override(model=new_model))
         else:
            new_model=init_chat_model(
            model="deepseek-chat",
            model_provider="openai",  # 明确指定 provider，防止 LangChain 误判
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=1024,
            timeout=30,
            max_retries=3,
        )
            return handler(request.override(model=new_model))

@tool
def calculator(expression: str) -> str:
    """Useful for bound math calculations."""
    try:
        return str(eval(expression))
    except:
        return "Error calculating"

tools = [calculator]

# 2. 系统提示词
system_prompt = """你是一个react模型智能体,
对于任何的问题，一定要基于现有的rag库回答，不能够编造，
如果是问首都问题的话 ,你就直接回答即可 ,不用检索
需要调用相关的工具，而不是直接回答问题，除非你确定工具无法回答问题，然后你就不需要调用工具。
你的思路流程是，先分析问题，得到一定的思路，然后根据思路去调用工具，
得到答案后，再根据工具的答案去分析问题，得到新的思路，再调用工具，循环往复，直到你确定工具无法回答问题了。
"""

@dynamic_prompt
def user_role_prompt(request: ModelRequest) -> str:
    try:
        print(request.runtime.context)
        if request.runtime.context.user_role=="expert":
            return  "你的名字是小dym"
    except Exception as e:
        return None
# 3. 结构化输出定义（备用）
class ResponseFormat(BaseModel):
    name:str
    jingdu:str
    weidu:str
    


# 4. 模块化 Agent 生成器
class AgentMaker:
    def __init__(self, api_key, base_url, temperature, tools, config,checkpointer=None):
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.tools = tools
        self.checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
        self.agent = None
        self.config = config  # 传入的配置字典

    def make_model(self, is_deep_analysis=False):
        """根据策略生成模型，支持动态切换配置"""
        # 可以根据是否是深度分析调整 temperature 或模型
        temp = self.temperature if not is_deep_analysis else 0.2
        
        return init_chat_model(
            model="deepseek-chat",
            model_provider="openai",  # 明确指定 provider，防止 LangChain 误判
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temp,
            max_tokens=1024,
            timeout=30,
            max_retries=3,
            extra_body={"thinking":{"type":"disabled"}}
        )
    def make(self):
        self.agent = create_agent(
            model=self.make_model(),
            tools=self.tools,
            # middleware=[user_role_prompt, choose_model_middleware], 
            system_prompt=system_prompt,
            checkpointer=self.checkpointer,
            context_schema=Context, # 这里传入类名，而不是 config 实例,用来注入上下文类型,这个是会自动传到request.runtime.context中去，作为一个配置项
            response_format=ResponseFormat,#用来限制回复内容的格式,其实是添加了 一个 structured_response这个字段 然后再后面我再去解析这个字段
            state_schema=CustomState#用来改变AgentState默认状态添加 还可以用中间件
        )
        # print(self.agent.invoke(
        #     {"messages":[{"role":"system","content":system_prompt}]},
        #     config=self.config,
        #     context=Context(user_role="expert")))  # 初始化系统消息
        return self.agent
    

    def think(self, messages: list[BaseMessage], config):#BaseMessgae------------------------------------------
        """执行 Agent 并返回最后的结果"""
        # 每次执行确保 Agent 已经构建
        if self.agent is None:
           self.agent = self.make()
        full_response=""
        agent=self.agent
        # 传入的应该是一个 State 字典，其中 "messages" 必须是 List[BaseMessage]
        result=agent.invoke(
            input={"messages":messages,
                   "user_preferences":{"name":"tom"}},##最好转换成state_schema一样的格式
            config=config,
            context=Context(user_role="expert"),
            output_keys=["messages","user_preferences","structured_response"],#指定返回的keys 最终返回那些keys
        )
        print(result)
        print("---------------------------------------------------------------\n")
        print(result["messages"])
        print("---------------------------------------------------------------\n")
        print(result["structured_response"])
        print("---------------------------------------------------------------\n")
        print(result["messages"][-1].content)
        # for chunk in  agent.stream(
        #     input={"messages": messages}, 
        #     config=config,#这个是长对话，久对话必备的配置
        #     context=Context(user_role="expert"),
        #     stream_mode="messages",
        #     version="v2"
        # ):
        #      if chunk["type"] != "messages":
        #         continue

        #      message, meta = chunk["data"]

        #      if isinstance(message, AIMessageChunk):

        #          if message.content:
        #             print(
        #         message.content,
        #         end="",
        #         flush=True
        #     )  # 逐字输出不换行#最开始还有返回其他类型的数据 我如果只限定content 那他就会回显空
        print("---------------------------------------------------------------")
      # 获取当前状态的正确方式
        # state = agent.get_state(config)
        # print("当前对话状态中的消息数:", len(state.values.get("messages", [])))
        
        # 从返回的状态字典中取出最后一条 AI 消息
        return None
if __name__ == "__main__":
    # 检查环境变量
    print(api_key)
    print(base_url)
    if not api_key:
        print("警告: 您的 API_KEY 未能成功加载，请检查本地路径！")
    
    # 实例化我们的模块化 AgentMaker
    agent_maker = AgentMaker(
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        tools=tools,
        config = {"configurable": 
              {"thread_id": "thread_unique_123"}
              }
    )
    
    # 准备标准格式的参数：
    # 1. 消息必须放在 List 里面
    input_messages = [HumanMessage(content="请帮我说出中国的首都在哪里，包括经纬度，别名")
                      
                      
                      ]
    
    # 2. 标准的 LangGraph 记忆配置项
    config = {"configurable": 
              {"thread_id": "thread_unique_123"
              },
              
              
              }
    
    print("开始让智能体思考并调用工具...")
    try:
        result = agent_maker.think(input_messages, config)
        print("\n--- 最终回答 ---")
    except Exception as e:
        print(f"\n运行中发生错误: {e}")
        import traceback
        traceback.print_exc()