"""
对话记忆管理
- 短期记忆：当前会话消息列表
- 长期记忆：跨会话持久化（基于 LangGraph checkpointer）
- 消息裁剪：避免 token 超限
"""

from langgraph.checkpoint.memory import InMemorySaver
from typing import Optional


class MemoryManager:
    def __init__(self, max_messages: int = 20, summarize_threshold: int = 30):
        self.checkpointer = InMemorySaver()
        self.max_messages = max_messages
        self.summarize_threshold = summarize_threshold

    def get_checkpointer(self) -> InMemorySaver:
        return self.checkpointer

    def trim_messages(self, messages: list) -> list:
        """消息数量超过阈值时裁剪，保留 system + 最近的消息"""
        if len(messages) <= self.max_messages:
            return messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        keep = other_msgs[-(self.max_messages - len(system_msgs)):]
        return system_msgs + keep

    def should_summarize(self, messages: list) -> bool:
        return len(messages) >= self.summarize_threshold
