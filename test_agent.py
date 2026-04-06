from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
import os
import json
import requests

# 加载环境变量
load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
api_key=os.getenv("OPENAI_API_KEY")
base_url=os.getenv("OPENAI_BASE_URL")
client = OpenAI(api_key=api_key, base_url=base_url)

# ===================== 上下文裁剪配置 =====================
MAX_MESSAGES = 15
def trim_messages():
    global messages
    system_msg = messages[0]
    chat_msgs = messages[1:]
    if len(chat_msgs) > MAX_MESSAGES:
        chat_msgs = chat_msgs[-MAX_MESSAGES:]
    messages = [system_msg] + chat_msgs

# ===================== 工具函数 =====================
def jisuan(fuhao,number1,number2):
    try:
        fuhao_map = {"加法":"+", "减法":"-","乘法":"*","除法":"/"}
        fuhao = fuhao_map.get(fuhao, fuhao)
        number1 = float(number1)
        number2 = float(number2)
        if fuhao=="+":return str(number1+number2)
        elif fuhao=="-":return str(number1-number2)
        elif fuhao=="*":return str(number1*number2)
        elif fuhao=="/":
            if number2==0:return "除数不能为0"
            return str(number1/number2)
        else:return "错误输入"
    except:return "计算失败"

def get_real_weather(city_name):
    try:
        geo_param = {
            "q": city_name,
            "appid": os.getenv("WEATHER_API_KEY"),
            "limit": 1,"lang": "zh_cn"
        }
        geo_response = requests.get("http://api.openweathermap.org/geo/1.0/direct", params=geo_param)
        geo_data = geo_response.json()
        lon = geo_data[0]["lon"]
        lat = geo_data[0]["lat"]

        weather_param = {
            "lat": lat,"lon": lon,
            "appid": os.getenv("WEATHER_API_KEY"),
            "lang": "zh_cn","units": "metric"
        }
        weather_response = requests.get("https://api.openweathermap.org/data/2.5/weather", params=weather_param)
        weather_data = weather_response.json()

        desc = weather_data["weather"][0]["description"]
        temp = weather_data["main"]["temp"]
        city = weather_data["name"]
        return f"{city}:{desc}，当前温度{temp}℃"
    except Exception as e:return f"获取天气失败：{str(e)}"

# ===================== 工具定义 =====================
tools=[
    {
        "type":"function",
        "function":{
            "name":"get_real_weather",
            "description":"获得指定城市的天气预报能力",
            "parameters":{
                "type":"object",
                "properties":{"city_name":{"type":"string","description":"城市名称，例如：北京、上海"}},
                "required":["city_name"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"jisuan",
            "description":"加减乘除数学计算",
            "parameters":{
                "type":"object",
                "properties":{
                    "fuhao":{"type":"string","description":"运算类型：加法、减法、乘法、除法"},
                    "number1":{"type":"number","description":"数字1"},
                    "number2":{"type":"number","description":"数字2"}
                },
                "required":["fuhao","number1","number2"]
            }
        }
    }
]

# ===================== 【ReAct核心】优化Prompt：引导模型思考+多轮调用 =====================
messages = [
    {"role": "system", "content": """
你是一个智能ReAct助手，必须严格遵循以下规则：
1. 先思考解决问题需要几步，需要调用什么工具
2. 查询天气必须调用get_real_weather工具
3. 数学计算必须调用jisuan工具
4. 信息不足时，主动调用工具获取信息
5. 所有工具调用完成后，再整理最终答案
禁止不调用工具直接回答问题！
"""}
]

# ===================== 历史对话总结函数 =====================
def zongjie(messages):
    system_msg = messages[0]
    history = messages[1:]
    if len(history) < 10:
        return messages
    old_messages = history[:-10]
    recent_messages = history[-10:]
    summary_messages = [
        {"role": "system", "content": "请用一段简洁的话总结以下对话"},
        *old_messages
    ]
    response = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        messages=summary_messages
    )
    summary = response.choices[0].message.content
    new_messages = [
        system_msg,
        {"role": "user", "content": f"历史对话总结：{summary}"},
        *recent_messages
    ]
    return new_messages

# ===================== 核心对话函数（已加入ReAct循环） =====================
def ask_for(prompt):
    global messages
    messages.append({"role": "user", "content": prompt})

    # ===================== 【ReAct核心】多轮工具调用循环 =====================
    max_steps = 5  # 最大工具调用步数，防止死循环
    current_step = 0
    
    while current_step < max_steps:
        # 1. 模型思考 + 决策
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            temperature=0.1
        )
        answer = response.choices[0].message

        # 2. ReAct终止条件：无工具需要调用，退出循环
        if not answer.tool_calls:
            break

        # 3. 执行工具调用
        tool_call = answer.tool_calls[0]
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        
        # 工具映射
        function_map = {
            "get_real_weather": get_real_weather,
            "jisuan": jisuan
        }
        
        try:
            tool_result = function_map[func_name](**func_args)
        except:
            tool_result = "工具调用失败，请检查参数"

        # 4. 将工具调用和结果存入上下文（关键：让模型记住上一步）
        messages.append(answer)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(tool_result)
        })
        
        current_step += 1
        print(f"🔄 ReAct执行步骤：{current_step} | 调用工具：{func_name}")

    # ===================== 原有流式输出最终答案 =====================
    print("助手：", end="", flush=True)
    final_answer = ""
    final_res = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True
    )
    for chunk in final_res:
        content = chunk.choices[0].delta.content or ""
        final_answer += content
        print(content, end="", flush=True)
    print()

    # 追加最终答案并裁剪消息
    messages.append({"role": "assistant", "content": final_answer})
    trim_messages()
    
    return final_answer

# ===================== 主程序 =====================
if __name__ == "__main__":
    print("✅ ReAct智能助手已启动! 输入 exit 退出")
    while True:
        prompt = input("你：")
        if prompt.lower() in ["exit", "quit"]:
            print("再见！")
            break
        if not prompt.strip():
            print("输入不能为空！")
            continue
            
        k = ask_for(prompt)
        # 文件写入
        try:
            with open(r"D:\agent_test\information.txt","a",encoding="utf-8") as e:
                e.write(f"问题：{prompt} → 结果：{k}\n")
            print("✅ 对话已保存到文件")
        except:
            print("❌ 文件保存失败")