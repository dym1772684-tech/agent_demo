"""
Agent 中间件
- 工具调用前后拦截（日志、监控、权限校验）
- 模型调用前后拦截（模型切换、请求改写）
"""

import logging
from functools import wraps

logger = logging.getLogger(__name__)


def log_tool_call(func):
    """记录工具调用的输入输出"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"[Tool Call] {func.__name__} args={args[1:]}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"[Tool Result] {func.__name__} -> {result}")
        return result
    return wrapper


def log_model_call(func):
    """记录模型调用"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info("[Model Call] sending request...")
        result = func(*args, **kwargs)
        logger.info("[Model Call] response received")
        return result
    return wrapper
