"""
自定义异常
"""


class AgentError(Exception):
    """Agent 基础异常"""
    pass


class ToolCallError(AgentError):
    """工具调用失败"""
    pass


class ModelTimeoutError(AgentError):
    """模型请求超时"""
    pass


class ConfigError(AgentError):
    """配置错误"""
    pass


class RAGError(AgentError):
    """RAG 检索错误"""
    pass
