import os
import json
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from typing import Annotated, List

# 渗透测试Agent配置路径
LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 30 轮对话 (60 条消息)
MAX_MESSAGES = 60


class AgentState(MessagesState):
    """渗透测试Agent状态管理"""
    pass


def build_agent(ctx=None):
    """
    构建渗透测试专家Agent
    
    参数:
        ctx: 请求上下文，用于链路追踪
    
    返回:
        配置好的Agent实例
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    # 读取LLM配置
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # 获取API配置
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 初始化LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        top_p=cfg['config'].get('top_p', 0.9),
        max_completion_tokens=cfg['config'].get('max_completion_tokens', 10000),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 导入所有工具
    from tools.reconnaissance import (
        domain_lookup, whois_query, dns_enum, subdomain_discovery,
        port_scan, service_detection, dir_enum, fingerprint_scan
    )
    from tools.vulnerability import (
        vuln_scan, web_vuln_scan, sql_injection_test, xss_test,
        file_upload_test, command_injection_test
    )
    from tools.privesc import (
        linux_privesc_check, windows_privesc_check
    )
    from tools.post_exploitation import (
        lateral_movement, domain_penetration, webshell_deploy, backdoor_check
    )
    from tools.reporting import log_analysis, report_generate

    # 工具列表
    tools = [
        # 信息收集工具
        domain_lookup, whois_query, dns_enum, subdomain_discovery,
        port_scan, service_detection, dir_enum, fingerprint_scan,
        # 漏洞扫描工具
        vuln_scan, web_vuln_scan, sql_injection_test, xss_test,
        file_upload_test, command_injection_test,
        # 权限提升工具
        linux_privesc_check, windows_privesc_check,
        # 后渗透工具
        lateral_movement, domain_penetration, webshell_deploy, backdoor_check,
        # 日志分析
        log_analysis,
        # 报告生成
        report_generate
    ]

    # 构建Agent
    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )


# Agent元数据
AGENT_METADATA = {
    "name": "网络安全渗透测试专家",
    "version": "1.0.0",
    "framework": "LangChain + LangGraph",
    "methodology": "PTES (Penetration Testing Execution Standard)",
    "capabilities": [
        "信息收集（被动+主动）",
        "漏洞扫描与发现",
        "漏洞利用与验证",
        "权限提升",
        "内网渗透",
        "权限维持",
        "痕迹清理",
        "报告生成"
    ],
    "compliance": [
        "仅测试授权目标",
        "遵循PTES方法论",
        "详细记录所有操作",
        "CVSS漏洞评级"
    ]
}
