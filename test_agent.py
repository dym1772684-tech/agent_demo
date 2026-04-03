from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
import os
import json
import requests

load_dotenv(find_dotenv(r"D:\agent_test\test.env"))
api_key=os.getenv("OPENAI_API_KEY")
base_url=os.getenv("OPENAI_BASE_URL")
client = OpenAI(api_key=api_key, base_url=base_url)

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
        return f"{city}：{desc}，当前温度{temp}℃"
    
    except Exception as e:
        return f"获取天气失败：{str(e)}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_real_weather",
            "description": "获取指定城市的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {
                        "type": "string",
                        "description": "城市名称，例如：长春,吉林"
                    }
                },
                "required": ["city_name"]
            }
        }
    }
]

def ask_for(prompt, messages=None):
    if messages is None:
        messages = [
            {"role": "system", "content": "你是一个天气助手，需要查询天气时必须调用工具"}
        ]
    
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-3.5",
        messages=messages,
        tools=tools,
        temperature=0.1
    )
    answer = response.choices[0].message

    if answer.tool_calls:
        func_name = answer.tool_calls[0].function.name
        func_args = json.loads(answer.tool_calls[0].function.arguments)
        
        if func_name == "get_real_weather":
            weather_result = get_real_weather(** func_args)
        
        messages.append(answer)
        messages.append({
            "role": "tool",
            "tool_call_id": answer.tool_calls[0].id,
            "content": weather_result
        })
        
        final_res = client.chat.completions.create(model="deepseek-3.5", messages=messages)
        final_answer = final_res.choices[0].message.content
        messages.append({"role": "assistant", "content": final_answer})
        return final_answer

    messages.append({"role": "assistant", "content": answer.content})
    return answer.content

if __name__ == "__main__":
    print("智能天气助手已启动！")
    print(ask_for("长春,吉林的天气怎么样？"))