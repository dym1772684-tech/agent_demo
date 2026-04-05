from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
import os
import json
import requests

load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
api_key=os.getenv("OPENAI_API_KEY")
base_url=os.getenv("OPENAI_BASE_URL")
client = OpenAI(api_key=api_key, base_url=base_url)

def jisuan(fuhao,number1,number2):
    try:
        if(fuhao=="+"):
            return str(number1+number2)
        elif(fuhao=="-"):
            return str(number1-number2)
        elif(fuhao=="*"):
            return str(number1*number2)
        elif(fuhao=="/"):
            if(number2==0):
                return "除数不能为0"
            return number1*1.0/number2
        else:return "错误输入"
    except Exception as e:
        return "计算失败"#要返回字符串类型，这样大语言模型才能分辨

    
def get_real_weather(city_name):
    try:
        geo_param = {
            "q": city_name,
            "appid": os.getenv("WEATHER_API_KEY"),
            "limit": 1,
            "lang": "zh_cn"
        }
        geo_response = requests.get("http://api.openweathermap.org/geo/1.0/direct", params=geo_param)
        geo_data = geo_response.json()
        
        lon = geo_data[0]["lon"]
        lat = geo_data[0]["lat"]

        weather_param = {
            "lat": lat,
            "lon": lon,
            "appid": os.getenv("WEATHER_API_KEY"),
            "lang": "zh_cn",
            "units": "metric"
        }
        weather_response = requests.get("https://api.openweathermap.org/data/2.5/weather", params=weather_param)
        weather_data = weather_response.json()

        desc = weather_data["weather"][0]["description"]
        temp = weather_data["main"]["temp"]
        city = weather_data["name"]
        return f"{city}:{desc}，当前温度{temp}℃"
    
    except Exception as e:
        return f"获取天气失败：{str(e)}"

tools=[{
    "type":"function",
    "function":{
        "name":"get_real_weather",
        "description":"获得天气预报能力",
        "parameters":{
            "type":"object",
            "properties":{
                "city_name":{
                    "type":"string",
                    "description":"城市名称,如吉林,长春"
                },
              
            },
              "required":["city_name"]
        }
    }
},
{
    "type":"function",
    "function":{
        "name":"jisuan",
        "description":"用户输入符号,数字1,数字2,然后根据符号进行加减乘除计算",
        "parameters":{
            "type":"object",
            "properties":{
                "fuhao":{
                "type":"string",
                "description":"计算符号"
            },
            "number1":{
                "type":"number",
                "description":"第一个数字"
            },
            "number2":{
                "type":"number",
                "description":"第二个数字"
            }
            },
        "required":["fuhao","number1","number2"]
        }
    }
}
]
messages=None
if messages is None:
    messages = [
        {"role": "system", "content": "你是一个智能助手，需要查询天气时必须调用工具，计算时也必须调用对应工具"}
    ]
def ask_for(prompt):
    
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        temperature=0.1
    )
    answer = response.choices[0].message

    if answer.tool_calls:
        func_name=answer.tool_calls[0].function.name
        func_args = json.loads(answer.tool_calls[0].function.arguments)
        
        # =============== 修复点：删掉多余的if判断，直接调用工具 ===============
        function_map={
          "get_real_weather":get_real_weather,
          "jisuan":jisuan
        }
        tool_result=function_map[func_name](**func_args)
        
        messages.append(answer) 
        messages.append({
            "role": "tool",
            "tool_call_id": answer.tool_calls[0].id,
            "content": tool_result
        })
        final_res = client.chat.completions.create(model="deepseek-chat", messages=messages)
        final_answer = final_res.choices[0].message.content
        messages.append({"role": "assistant", "content": final_answer})
        return final_answer

    messages.append({"role": "assistant", "content": answer.content})
    return answer.content

if __name__ == "__main__":
    print("智能助手已启动！")
    print(ask_for("1550*5100是几"))
#     {
#   "id": "chatcmpl-xxx",
#   "object": "chat.completion",
#   "created": 1743728400,
#   "model": "deepseek-3.5",
#   "choices": [
#     {
#       "index": 0,
#       "message": {
#         "role": "assistant",
#         "content": null,
#         "tool_calls": [
#           {
#             "id": "call_xxx123",
#             "type": "function",
#             "function": {
#               "name": "get_real_weather",
#               "arguments": "{\"city\":\"北京\",\"date\":\"2026-04-04\"}"
#             }
#           }
#         ]
#       },
#       "finish_reason": "tool_calls"
#     }
#   ],
#   "usage": {
#     "prompt_tokens": 100,
#     "completion_tokens": 20,
#     "total_tokens": 120
#   }
# }
# def ask_for(prompt, messages=None):
#     if messages is None:
#         messages = [
#             {"role": "system", "content": "你是一个天气助手，需要查询天气时必须调用工具"}
#         ]
    
#     messages.append({"role": "user", "content": prompt})

#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=messages,
#         tools=tools,
#         temperature=0.1
#     )
#     answer = response.choices[0].message

#     if answer.tool_calls:
#         func_args = json.loads(answer.tool_calls[0].function.arguments)
        
#         # =============== 修复点：删掉多余的if判断，直接调用工具 ===============
#         weather_result = get_real_weather(** func_args)
        
#         messages.append(answer)
#         messages.append({
#             "role": "tool",
#             "tool_call_id": answer.tool_calls[0].id,
#             "content": weather_result
#         })
        
#         final_res = client.chat.completions.create(model="deepseek-chat", messages=messages)
#         final_answer = final_res.choices[0].message.content
#         messages.append({"role": "assistant", "content": final_answer})
#         return final_answer

#     messages.append({"role": "assistant", "content": answer.content})
#     return answer.content
