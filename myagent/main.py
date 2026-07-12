"""
程序入口
- 初始化 Agent
- 交互式对话循环
"""

import os
from dotenv import find_dotenv, load_dotenv
from agent import AgentMaker
from langchain.tools import tool
from memory import MemoryManager

load_dotenv(find_dotenv(r"D:\agent_test\test.env"))

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")


def main():
    memory = MemoryManager()
    agent = AgentMaker(
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        stream_check=False,
        tools=tools,
    )

    thread_id = "thread_1"
    config = {"configurable": {"thread_id": thread_id}}
    messages = []

    print("Agent 已启动，输入 'quit' 退出。")
    while True:
        user_input = input("\n你: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        messages = memory.trim_messages(messages)

        try:
            result = agent.think(messages, config)
            messages.append({"role": "assistant", "content": result})
            print(f"\nAgent: {result}")
        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    main()
