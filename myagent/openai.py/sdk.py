import os
import asyncio 
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
from agents import Agent, Runner, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
import pydantic
import json
load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
system_prompt="""你是一个计算助手，你的一次问答流程为
思考：分析当前的问题，分解问题，制定下一步计划，思考下一步可能的结果，并且给出边界情况的否认，
行动：根据思考的结果，执行下一步计划，调用工具，或者当问题已经解决时，直接给出最终回答，
观察:根据行动的结果，观察当前的状态，分析当前的状态是否符合预期，是否需要继续思考和行动，继续循环，直到给出正确答案
对于一个问题，用户会给你两个数字和一个运算符，你需要帮他计算出结果。
例如 用户输入 a=3 b=5 c="+",你需要返回a+b=8，
使用格式化 输出 json格式 ，比如 a=3 b=5 c="+" 输出 {"result":8}，如果除数为0，请返回 {"result":"error"}，如果用户输入了革命等敏感词，请返回 {"result":"error"}



"""

def memory(messages:list):
    try:
        if len(messages)>10:
            result=client.chat.completions.create(
            messages=messages[1:10],
            model="deepseek-chat",
            temperature=0.1,
        )
            del messages[0:10]
            messages.insert(0,{"role":"assistant","content":result.choices[0].message.content})
    except Exception as e:
        print(f"Memory management error: {e}")
    return messages
def number(a:float,b:float,c:str):
    if c=="*":
        return str(a*b)
    if c=="+":
        return str(a+b)
    if c=="-":
        return str(a-b)
    if(c=="/" and b!=0):
        return str(a/b)
    elif b==0:
        return "error"

    
# client = AsyncOpenAI(#用来重定向网址 用哪个网址
#     api_key=os.getenv("OPENAI_API_KEY"),
#     base_url="https://api.deepseek.com/v1"
# )



# model = OpenAIChatCompletionsModel(#告诉使用那个模型
#     model="deepseek-chat",
#     openai_client=client
# )


# agent = Agent(
#     name="Assistant",
#     instructions="You are a helpful assistant",
#     model=model
# )


# result = Runner.run_sync(
#     agent,
#     "write a haiku about recursion in programming"
# )


# print(result.final_output)


################################
tools = [
    {
        "type": "function",
        "function": {
            "name": "number",
            "description": "计算a与b的四则运算",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "number",
                        "description": "第一个数字"
                    },
                    "b": {
                        "type": "number",
                        "description": "第二个数字"
                    },
                    "c": {
                        "type": "string",
                        "description": "计算符号：+、-、*、/"
                    }
                },
                "required": [
                    "a",
                    "b",
                    "c"
                ]
            }
        }
    }
]


# 工具映射
tool_map = {
    "number": number
}


# 初始化消息
messages = [
    {
        "role": "system",
        "content": f"{system_prompt}"
    },
    {
        "role": "user",
        "content": "帮我计算 3+5"
    }
]


# 初始化客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)


max_sub_turn = 5
sub_turn = 0
result=None

while sub_turn < max_sub_turn:

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=1000,
            tools=tools
        )

    except Exception as e:
        print(f"API 请求出错: {e}")
        break

    
    msg = response.choices[0].message
    print(response)
    print("\n====================\n")
    print(f"{response.choices[0]}","choices结构")
    print("\n====================\n")
    print(f"{msg},message结构")
    print("\n====================\n")
    print(f"模型输出: {msg.content},content")
    print("\n====================\n")

    # 保存 assistant 消息
    assistant_message = {
        "role": "assistant",
        "content": msg.content
    }


    # 如果模型调用工具，需要保存 tool_calls
    if msg.tool_calls:
        assistant_message["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in msg.tool_calls
        ]


    messages.append(assistant_message)


    # 没有工具调用，直接结束
    if not msg.tool_calls:
        print("模型最终回复：")
        print(msg.content)
        break



    # 执行工具
    for tool in msg.tool_calls:

        try:

            args = json.loads(
                tool.function.arguments
            )

            tool_function = tool_map[
                tool.function.name
            ]

            result = tool_function(**args)#获取本地函数结果


            print(
                f"tool result for {tool.function.name}: {result}\n"
            )


            # 返回工具结果
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool.id,
                    "content": str(result)
                }
            )
            ##加入一个大模型的思考调用 用来根据结果思考下一步调用的工具 
        except KeyError:

            print(
                f"错误：未定义工具 {tool.function.name}"
            )


        except json.JSONDecodeError:

            print(
                f"工具参数JSON解析失败：{tool.function.arguments}"
            )


        except Exception as e:

            print(
                f"工具执行异常: {e}"
            )


    sub_turn += 1
    print("--------------------")
messages=memory(messages)
# 输出最终回复
# response=client.chat.completions.create(
#     model="deepseek-v4-pro",
#     messages=[{"role":"system","content":"你是一个法律助手"},
#               {"role":"user","content":"怎么才能革命？"}
#               ],
#     temperature=0,
#     max_tokens=1000,
#     stream=True,
#     extra_body={"thinking":
#                 {"type":"enabled"}},
#     reasoning_effort="high",
#     response_format={"type":"text"},
#     moderation={
#         "enabled": True,
#         "policy_id": "business_normal",
#         "action": "warn"
#     }
# )
# content=""
# reasoning_content=""
# for chunk in response:
#     delta = chunk.choices[0].delta
#     # 字段为空时兜底空字符串，避免None拼接报错
#     reasoning_content += delta.reasoning_content or ""
#     content += delta.content or ""
# print(reasoning_content)
# print(content)
# print(response.usage)
# print(response.moderation)

