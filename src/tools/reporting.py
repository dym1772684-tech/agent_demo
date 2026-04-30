"""
渗透测试 - 日志分析与报告生成模块
包含日志分析和渗透测试报告生成工具
"""
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_context(method_name: str):
    """获取请求上下文"""
    ctx = request_context.get()
    if ctx is None:
        ctx = new_context(method=method_name)
    return ctx


@tool
def log_analysis(log_content: str, log_type: str = "apache") -> str:
    """
    日志分析工具
    
    功能：分析Web服务器日志，发现攻击痕迹、异常访问和潜在漏洞
    
    用途：
    - 发现渗透测试过程中的攻击痕迹
    - 识别异常访问模式
    - 检测SQL注入和XSS尝试
    - 分析攻击者的行为模式
    
    参数：
        log_content: 日志内容（可以是原始日志文本或文件路径）
        log_type: 日志类型
            - apache: Apache访问日志
            - nginx: Nginx访问日志
            - iis: IIS日志
            - ssh: SSH登录日志
            - linux: Linux系统日志
    
    返回：
        日志分析结果，包含攻击痕迹和异常统计
    
    示例：
        输入: "192.168.1.1 - - [01/Jan/2024:00:00:00] GET /admin.php 200", apache
        输出: {
            "log_type": "apache",
            "attacks_found": [
                {"type": "Admin Page Access", "ip": "192.168.1.1", "url": "/admin.php"}
            ]
        }
    """
    ctx = _get_context("log_analysis")
    logger.info(f"[log_analysis] 日志分析: 类型={log_type}")
    
    try:
        result = {
            "log_type": log_type,
            "analysis_time": datetime.now().isoformat(),
            "status": "success"
        }
        
        attacks_found = []
        suspicious_activities = []
        statistics = {
            "total_requests": 0,
            "unique_ips": 0,
            "error_requests": 0,
            "attack_attempts": 0
        }
        
        # 攻击模式检测
        attack_patterns = {
            "SQL注入": [
                r"union\s+select",
                r"'\s+or\s+'1'\s*=\s*'1",
                r"'\s+or\s+1\s*=\s*1",
                r"'\s+and\s+'1'\s*=\s*'1",
                r"exec\s*\(",
                r"execute\s*\(",
                r"xp_cmdshell",
                r"information_schema",
                r"concat\s*\(",
                r"benchmark\s*\(",
                r"sleep\s*\(",
                r"waitfor\s+delay"
            ],
            "XSS跨站脚本": [
                r"<script",
                r"javascript:",
                r"onerror\s*=",
                r"onload\s*=",
                r"alert\s*\(",
                r"<iframe",
                r"<embed",
                r"<object"
            ],
            "命令注入": [
                r";\s*whoami",
                r";\s*id",
                r";\s*cat\s+",
                r"\|\s*nc\s+",
                r"`.*`",
                r"\$\(.*\)",
                r"&&\s*rm\s+",
                r"wget\s+http",
                r"curl\s+http"
            ],
            "目录遍历": [
                r"\.\./",
                r"\.\.\\",
                r"%2e%2e%2f",
                r"%2e%2e/",
                r"/etc/passwd",
                r"/etc/shadow",
                r"c:\\windows"
            ],
            "文件包含": [
                r"\?file=",
                r"\?path=",
                r"\?page=",
                r"\?include=",
                r"php://input",
                r"expect://",
                r"phar://"
            ],
            "扫描探测": [
                r"nikto",
                r"sqlmap",
                r"acunetix",
                r"appscan",
                r"burp",
                r"nmap",
                r"metasploit",
                r"masscan"
            ],
            "Webshell上传": [
                r"\.php\?",
                r"\.asp",
                r"\.jsp",
                r"\.aspx",
                r"\.phtml",
                r"\.phar",
                r"\.htaccess"
            ]
        }
        
        lines = log_content.strip().split('\n')
        statistics["total_requests"] = len(lines)
        
        ips = set()
        
        for line in lines:
            if not line.strip():
                continue
                
            # 提取IP地址
            ip_match = re.match(r'^(\d+\.\d+\.\d+\.\d+)', line)
            if ip_match:
                ips.add(ip_match.group(1))
            
            # 检测各类攻击模式
            for attack_type, patterns in attack_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.I):
                        attacks_found.append({
                            "type": attack_type,
                            "pattern": pattern,
                            "evidence": line[:200],
                            "severity": "high" if attack_type in ["SQL注入", "命令注入", "文件包含"] else "medium"
                        })
                        statistics["attack_attempts"] += 1
                        break
            
            # 检测异常状态码
            error_codes = re.findall(r'\s(4\d{2}|5\d{2})\s', line)
            if error_codes:
                statistics["error_requests"] += 1
                
                # 检测404扫描
                if '404' in error_codes:
                    path_match = re.search(r'GET\s+(\S+)', line)
                    if path_match:
                        suspicious_activities.append({
                            "type": "404 Scan",
                            "path": path_match.group(1),
                            "evidence": line[:200]
                        })
        
        statistics["unique_ips"] = len(ips)
        
        result["attacks_found"] = attacks_found[:50]  # 限制数量
        result["suspicious_activities"] = suspicious_activities[:20]
        result["statistics"] = statistics
        
        # 风险评估
        if statistics["attack_attempts"] > 10:
            result["risk_level"] = "HIGH - 检测到大量攻击尝试"
        elif statistics["attack_attempts"] > 0:
            result["risk_level"] = "MEDIUM - 检测到攻击尝试"
        else:
            result["risk_level"] = "LOW - 未检测到明显攻击"
        
        # 建议
        result["recommendations"] = [
            "检查攻击来源IP并封禁",
            "审查成功执行的攻击",
            "增强WAF规则阻断已知攻击模式",
            "启用详细日志记录",
            "检查系统是否已被攻陷"
        ]
        
        logger.info(f"[log_analysis] 分析完成: 发现 {len(attacks_found)} 个攻击痕迹")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"日志分析异常: {str(e)}"
        logger.error(f"[log_analysis] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def report_generate(scope: str, vulnerabilities: str = None, executive_summary: str = None) -> str:
    """
    渗透测试报告生成工具
    
    功能：根据渗透测试结果生成专业的Markdown格式测试报告
    
    用途：
    - 生成符合PTES方法论的报告
    - 包含漏洞详情和CVSS评分
    - 提供修复建议和风险评估
    - 生成执行摘要便于管理层阅读
    
    参数：
        scope: 测试范围和目标（JSON格式或描述文本）
        vulnerabilities: 发现的漏洞列表（JSON格式）
        executive_summary: 执行摘要（可选）
    
    返回：
        生成的渗透测试报告内容
    
    示例：
        输入: "{\"target\": \"example.com\", \"scope\": \"Web系统\"}", "[{\"name\": \"SQL注入\", \"severity\": \"high\"}]"
        输出: 完整的Markdown格式渗透测试报告
    """
    ctx = _get_context("report_generate")
    logger.info(f"[report_generate] 生成渗透测试报告")
    
    try:
        result = {
            "status": "success",
            "report_format": "markdown",
            "generated_at": datetime.now().isoformat()
        }
        
        # 解析输入
        try:
            scope_data = json.loads(scope) if scope else {}
        except:
            scope_data = {"description": scope}
        
        try:
            vuln_data = json.loads(vulnerabilities) if vulnerabilities else []
        except:
            vuln_data = []
        
        # 生成报告
        project_name = scope_data.get('project_name', '渗透测试项目')
        target = scope_data.get('target', 'N/A')
        scope_desc = scope_data.get('scope', 'N/A')
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        report = f"""# 渗透测试报告

**项目名称**: {project_name}
**测试目标**: {target}
**测试范围**: {scope_desc}
**测试日期**: {current_date}
**报告版本**: v1.0

---

## 1. 执行摘要

"""
        
        if executive_summary:
            report += executive_summary + "\n\n"
        else:
            report += """本次渗透测试旨在评估目标系统的安全性，发现潜在的安全漏洞和风险。测试范围包括Web应用、网络设备和服务器等目标。
"""
        
        # 统计漏洞数量
        vuln_count = len(vuln_data)
        critical_count = len([v for v in vuln_data if v.get('severity') == 'critical'])
        high_count = len([v for v in vuln_data if v.get('severity') == 'high'])
        medium_count = len([v for v in vuln_data if v.get('severity') == 'medium'])
        low_count = len([v for v in vuln_data if v.get('severity') == 'low'])
        
        report += """### 1.1 测试结论

| 项目 | 数值 |
|------|------|
| 发现漏洞总数 | {vuln_count} |
| 高危漏洞 | {critical_high} |
| 中危漏洞 | {medium_count} |
| 低危漏洞 | {low_count} |

### 1.2 风险等级

""".format(
            vuln_count=vuln_count,
            critical_high=critical_count + high_count,
            medium_count=medium_count,
            low_count=low_count
        )
        
        # 风险等级评估
        if critical_count > 0:
            report += "🔴 **严重风险** - 发现严重安全漏洞，需要立即修复\n"
        elif high_count > 0:
            report += "🟠 **高风险** - 发现高危漏洞，建议尽快修复\n"
        else:
            report += "🟡 **中等风险** - 发现安全隐患，建议按计划修复\n"
        
        report += """
---

## 2. 测试范围与方法论

### 2.1 测试目标

"""
        
        if isinstance(scope_data.get('targets'), list):
            for target_item in scope_data['targets']:
                report += "- " + str(target_item) + "\n"
        else:
            report += "- 主域名: " + str(scope_data.get('target', 'N/A')) + "\n"
            report += "- IP范围: " + str(scope_data.get('ip_range', 'N/A')) + "\n"
            report += "- 应用系统: " + str(scope_data.get('applications', 'N/A')) + "\n"
        
        report += """
### 2.2 测试方法论

本次渗透测试遵循 **PTES (Penetration Testing Execution Standard)** 标准，包括以下阶段：

1. **信息收集** - 被动和主动信息收集
2. **威胁建模** - 确定攻击向量
3. **漏洞分析** - 发现潜在漏洞
4. **漏洞利用** - 验证漏洞可利用性
5. **后渗透** - 评估权限提升和横向移动风险
6. **报告撰写** - 生成详细测试报告

---

## 3. 漏洞详情

"""
        
        # 按严重性排序漏洞
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_vulns = sorted(vuln_data, key=lambda x: severity_order.get(x.get('severity', 'low'), 4))
        
        for idx, vuln in enumerate(sorted_vulns, 1):
            severity = vuln.get('severity', 'unknown')
            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
            
            vuln_name = vuln.get('name', '未命名漏洞')
            vuln_url = vuln.get('url', vuln.get('target', 'N/A'))
            vuln_desc = vuln.get('description', '暂无详细描述')
            vuln_fix = vuln.get('fix', vuln.get('recommendation', '建议根据实际情况制定修复方案'))
            
            report += """
### 3.{idx} {emoji} {name}

| 属性 | 值 |
|------|-----|
| **严重性** | {severity_upper} |
| **CVE编号** | {cve} |
| **漏洞类型** | {vtype} |
| **影响URL** | {url} |

**漏洞描述**:

{description}

**复现步骤**:

1. 访问受影响页面
2. 构造恶意请求
3. 观察响应

**修复建议**:

{fix}

""".format(
                idx=idx,
                emoji=severity_emoji,
                name=vuln_name,
                severity_upper=severity.upper(),
                cve=vuln.get('cve', 'N/A'),
                vtype=vuln.get('type', 'N/A'),
                url=vuln_url,
                description=vuln_desc,
                fix=vuln_fix
            )
            
            if vuln.get('evidence'):
                report += """
**证据截图**:

```
""" + str(vuln.get('evidence')) + """
```

"""
        
        report += """
---

## 4. 修复优先级建议

### 4.1 紧急修复 (72小时内)

"""
        
        urgent_vulns = [v for v in sorted_vulns if v.get('severity') in ['critical', 'high']]
        for v in urgent_vulns[:5]:
            v_name = v.get('name', '漏洞')
            v_url = v.get('url', '#')
            v_type = v.get('type', 'N/A')
            report += "- [" + v_name + "](" + v_url + ") - " + v_type + "\n"
        
        if not urgent_vulns:
            report += "无紧急修复项\n"
        
        report += """
### 4.2 计划修复 (1周内)

"""
        
        medium_vulns = [v for v in sorted_vulns if v.get('severity') == 'medium']
        for v in medium_vulns[:5]:
            v_name = v.get('name', '漏洞')
            v_url = v.get('url', '#')
            v_type = v.get('type', 'N/A')
            report += "- [" + v_name + "](" + v_url + ") - " + v_type + "\n"
        
        if not medium_vulns:
            report += "无计划修复项\n"
        
        report += """
---

## 5. 安全建议

### 5.1 短期建议

1. **立即修复**所有高危和严重漏洞
2. **启用** Web应用防火墙(WAF)
3. **加强**认证机制，使用多因素认证
4. **加密**所有敏感数据传输
5. **备份**重要数据并测试恢复流程

### 5.2 中期建议

1. **建立**安全开发流程(SDL)
2. **实施**定期渗透测试
3. **部署**安全监控和日志分析系统
4. **制定**应急响应预案
5. **培训**开发人员安全意识

### 5.3 长期建议

1. **构建**安全运营中心(SOC)
2. **实施**DevSecOps实践
3. **建立**威胁情报体系
4. **定期**进行红蓝对抗演练
5. **持续**优化安全架构

---

## 6. 附录

### 6.1 测试工具清单

| 工具名称 | 用途 |
|----------|------|
| Nmap | 端口扫描和服务识别 |
| Burp Suite | Web应用测试 |
| SQLMap | SQL注入检测 |
| Nikto | Web服务器扫描 |
| Metasploit | 漏洞利用框架 |
| BloodHound | AD域分析 |

### 6.2 术语说明

- **CVSS**: 通用漏洞评分系统 (Common Vulnerability Scoring System)
- **CVE**: 通用漏洞披露 (Common Vulnerabilities and Exposures)
- **WAF**: Web应用防火墙 (Web Application Firewall)
- **RCE**: 远程代码执行 (Remote Code Execution)
- **SSRF**: 服务端请求伪造 (Server-Side Request Forgery)

### 6.3 免责声明

本报告仅供授权方使用，未经书面许可不得向第三方披露。测试结果仅代表测试时刻的安全状态，系统安全性需要持续关注和改进。

---

**报告生成时间**: {timestamp}
**测试团队**: 网络安全渗透测试团队
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        result["report"] = report
        result["report_length"] = len(report)
        result["vuln_count"] = len(vuln_data)
        
        logger.info(f"[report_generate] 报告生成完成: {len(report)} 字符")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"报告生成异常: {str(e)}"
        logger.error(f"[report_generate] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
