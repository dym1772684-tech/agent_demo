from pydantic import BaseModel,Field
from typing import Callable
from langchain.tools import tool,ToolRuntime
import requests
import os
class defInfo(BaseModel):#函数的参数
    number1:float
    number2:float
    fuhao:str
tools=[]
def regiser_tool_map(map: list):
    def decorator(func_name: Callable):
        map.append(func_name)
        return func_name
    return decorator
@regiser_tool_map(map=tools)
@tool("calculator",description="计算",args_schema=defInfo)
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



class location(BaseModel):
    city_name:str=Field(description="City name or coordinates")
@regiser_tool_map(map=tools)
@tool("get_real_weather",description="用来获得天气",args_schema=location,return_direct=False)
#这个args_schema 可以使用json（也就是之前的sdk，然后的话也可以使用pydantic
def get_real_weather(city_name:str,runtime:ToolRuntime):
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
            "lat": lat,
            "lon": lon,
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

#    @dataclass
# class ToolRuntime[ContextT]:
#     state: dict                  # 当前Agent全局状态（可变）
#     context: ContextT | dict    # 会话固定配置（不可变）
#     store: BaseStore | None     # 跨对话长期持久记忆
#     stream_writer: StreamWriter # 实时流式输出
#     previous: Any               # 上一轮节点返回结果
#     tool_call_id: str           # 当前本次工具调用唯一ID
