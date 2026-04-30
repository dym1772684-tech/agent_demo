"""
渗透测试 - 信息收集模块
包含被动信息收集和主动信息收集工具
"""
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import logging
import socket
import subprocess
import json

# 可选依赖
try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

logger = logging.getLogger(__name__)


def _get_context(method_name: str):
    """获取请求上下文"""
    ctx = request_context.get()
    if ctx is None:
        ctx = new_context(method=method_name)
    return ctx


@tool
def domain_lookup(domain: str) -> str:
    """
    域名基础查询工具
    
    功能：对目标域名进行基础信息查询，获取域名解析情况
    
    用途：
    - 确认域名有效性
    - 获取域名解析IP
    - 初步判断目标网络环境
    
    参数：
        domain: 目标域名 (例: example.com)
    
    返回：
        域名解析结果，包含IP地址、TTL等信息
    
    示例：
        输入: example.com
        输出: [{'ip': '93.184.216.34', 'type': 'A', 'ttl': 3600}]
    """
    ctx = _get_context("domain_lookup")
    logger.info(f"[domain_lookup] 查询域名: {domain}")
    
    try:
        # 使用socket进行域名解析
        ip = socket.gethostbyname(domain)
        
        result = {
            "domain": domain,
            "resolved_ip": ip,
            "status": "success",
            "message": f"域名 {domain} 解析成功"
        }
        
        logger.info(f"[domain_lookup] 解析结果: {json.dumps(result)}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except socket.gaierror as e:
        error_msg = f"域名解析失败: {str(e)}"
        logger.error(f"[domain_lookup] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"域名查询异常: {str(e)}"
        logger.error(f"[domain_lookup] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def whois_query(domain: str) -> str:
    """
    Whois查询工具
    
    功能：查询域名的注册信息，包括注册商、注册时间、过期时间、DNS服务器等
    
    用途：
    - 获取目标域名注册信息
    - 判断域名年龄和有效期
    - 发现管理员联系信息（可用于社会工程学）
    - 发现 Nameserver 用于后续测试
    
    参数：
        domain: 目标域名 (例: example.com)
    
    返回：
        Whois查询结果，包含注册商、注册时间、过期时间、DNSServer等
    
    示例：
        输入: example.com
        输出: 注册商: VeriSign, 注册时间: 1995-08-14, 过期时间: 2025-08-13
    """
    ctx = _get_context("whois_query")
    logger.info(f"[whois_query] Whois查询: {domain}")
    
    if not WHOIS_AVAILABLE:
        error_msg = "whois库未安装，请运行: uv add python-whois"
        logger.error(f"[whois_query] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    
    try:
        # 使用python-whois库查询
        w = whois.whois(domain)
        
        # 处理可能的字典或对象响应
        if isinstance(w, dict):
            registrar = w.get('registrar', 'Unknown')
            creation_date = str(w.get('creation_date', 'Unknown'))
            expiration_date = str(w.get('expiration_date', 'Unknown'))
            name_servers = w.get('name_servers', [])
            status = w.get('status', 'Unknown')
            emails = w.get('emails', [])
            org = w.get('org', 'Unknown')
        else:
            registrar = getattr(w, 'registrar', 'Unknown')
            creation_date = str(getattr(w, 'creation_date', 'Unknown'))
            expiration_date = str(getattr(w, 'expiration_date', 'Unknown'))
            name_servers = getattr(w, 'name_servers', [])
            status = getattr(w, 'status', 'Unknown')
            emails = getattr(w, 'emails', [])
            org = getattr(w, 'org', 'Unknown')
        
        result = {
            "domain": domain,
            "registrar": registrar,
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "name_servers": name_servers,
            "status": status,
            "emails": emails,
            "org": org
        }
        
        logger.info(f"[whois_query] 查询成功: {domain}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"Whois查询异常: {str(e)}"
        logger.error(f"[whois_query] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def dns_enum(domain: str, record_type: str = "A") -> str:
    """
    DNS枚举工具
    
    功能：查询指定类型的DNS记录
    
    用途：
    - 获取域名对应的IP地址 (A记录)
    - 获取邮件交换服务器 (MX记录)
    - 获取域名权威DNS服务器 (NS记录)
    - 获取SPF记录分析邮件安全配置
    - 发现隐藏的服务和子域名
    
    参数：
        domain: 目标域名 (例: example.com)
        record_type: DNS记录类型，可选值:
            - A: IPv4地址记录
            - AAAA: IPv6地址记录
            - MX: 邮件交换记录
            - NS: 域名服务器记录
            - TXT: 文本记录
            - CNAME: 别名记录
            - SOA: 起始授权记录
            - PTR: 反向DNS记录
    
    返回：
        DNS记录查询结果
    
    示例：
        输入: example.com, MX
        输出: [{'priority': 10, 'exchange': 'mail.example.com'}]
    """
    ctx = _get_context("dns_enum")
    logger.info(f"[dns_enum] DNS枚举: {domain}, 类型: {record_type}")
    
    if not DNS_AVAILABLE:
        error_msg = "dnspython库未安装，请运行: uv add dnspython"
        logger.error(f"[dns_enum] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    
    try:
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(domain, record_type)
        
        results = []
        for rdata in answers:
            if record_type == "MX":
                results.append({
                    "priority": rdata.preference,
                    "exchange": str(rdata.exchange).rstrip('.')
                })
            elif record_type in ["A", "AAAA"]:
                results.append({
                    "address": str(rdata),
                    "type": record_type
                })
            elif record_type == "NS":
                results.append({
                    "nameserver": str(rdata).rstrip('.')
                })
            elif record_type == "TXT":
                results.append({
                    "text": str(rdata)
                })
            elif record_type == "CNAME":
                results.append({
                    "cname": str(rdata).rstrip('.')
                })
            else:
                results.append({"value": str(rdata)})
        
        output = {
            "domain": domain,
            "record_type": record_type,
            "count": len(results),
            "records": results,
            "status": "success"
        }
        
        logger.info(f"[dns_enum] 查询成功: {domain} {record_type}, 返回 {len(results)} 条记录")
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except dns.resolver.NXDOMAIN:
        error_msg = f"域名不存在: {domain}"
        logger.error(f"[dns_enum] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    except dns.resolver.NoAnswer:
        error_msg = f"无{record_type}记录: {domain}"
        logger.warning(f"[dns_enum] {error_msg}")
        return json.dumps({"status": "no_answer", "message": error_msg}, ensure_ascii=False)
    except dns.resolver.NoResolverConfiguration:
        error_msg = "DNS配置错误"
        logger.error(f"[dns_enum] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"DNS枚举异常: {str(e)}"
        logger.error(f"[dns_enum] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def subdomain_discovery(domain: str, wordlist: str = None) -> str:
    """
    子域名发现工具
    
    功能：使用字典枚举和被动数据源发现目标域名的子域名
    
    用途：
    - 发现更多的攻击面
    - 识别遗忘的测试系统
    - 发现配置错误的服务
    - 绕过主域名限制（如CDN）
    
    参数：
        domain: 目标域名 (例: example.com)
        wordlist: 可选的子域名字典文件路径 (默认使用内置常用字典)
    
    返回：
        发现的子域名列表及状态
    
    示例：
        输入: example.com
        输出: {
            "domain": "example.com",
            "subdomains": [
                {"subdomain": "www.example.com", "status": "alive"},
                {"subdomain": "mail.example.com", "status": "alive"},
                {"subdomain": "api.example.com", "status": "alive"}
            ],
            "total": 3
        }
    """
    ctx = _get_context("subdomain_discovery")
    logger.info(f"[subdomain_discovery] 子域名发现: {domain}")
    
    if not DNS_AVAILABLE:
        error_msg = "dnspython库未安装，请运行: uv add dnspython"
        logger.error(f"[subdomain_discovery] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    
    try:
        # 内置常用子域名字典
        default_subdomains = [
            "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "dns2",
            "owa", "webdisk", "ns", "cpanel", "whm", "autodiscover", "autoconfig", "m",
            "imap", "test", "ns", "pop3", "dev", "www2", "admin", "forum", "news",
            "vpn", "ns3", "mail2", "new", "mysql", "old", "lists", "support", "mobile",
            "mx", "static", "docs", "beta", "shop", "sql", "secure", "demo", "cms",
            "www1", "api", "images", "img", "www3", "mail1", "server", "ns1", "proxy",
            "auth", "mailserver", "email", "web", "office", "portal", "private", "登入",
            "内部", "git", "svn", "bbs", "blog", "oab", "corpsite", "site", "login"
        ]
        
        # 如果提供了字典文件，读取并合并
        if wordlist:
            try:
                with open(wordlist, 'r', encoding='utf-8') as f:
                    custom_words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                default_subdomains.extend(custom_words)
            except Exception as e:
                logger.warning(f"[subdomain_discovery] 无法读取字典文件: {e}")
        
        discovered = []
        
        # 使用DNS枚举检查每个子域名
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        
        for sub in default_subdomains:
            full_domain = f"{sub}.{domain}"
            try:
                answers = resolver.resolve(full_domain, 'A')
                ips = [str(rdata) for rdata in answers]
                discovered.append({
                    "subdomain": full_domain,
                    "ip": ips,
                    "status": "alive"
                })
                logger.info(f"[subdomain_discovery] 发现子域名: {full_domain} -> {ips}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                # 子域名不存在
                pass
            except Exception as e:
                logger.debug(f"[subdomain_discovery] 检查{full_domain}时异常: {e}")
        
        output = {
            "domain": domain,
            "subdomains": discovered,
            "total": len(discovered),
            "status": "success"
        }
        
        logger.info(f"[subdomain_discovery] 完成: 发现 {len(discovered)} 个子域名")
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"子域名发现异常: {str(e)}"
        logger.error(f"[subdomain_discovery] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def port_scan(target: str, port_range: str = "1-1000", scan_type: str = "SYN") -> str:
    """
    端口扫描工具（基于Nmap封装）
    
    功能：对目标主机进行端口扫描，识别开放端口和服务
    
    用途：
    - 发现目标网络暴露的服务
    - 识别运行的应用和版本
    - 发现潜在的攻击入口点
    - 验证防火墙规则配置
    
    参数：
        target: 目标IP或域名 (例: 192.168.1.1 或 example.com)
        port_range: 端口范围，格式: start-end (默认: 1-1000)
            常用范围:
            - 1-1000: 常用端口
            - 1-65535: 全端口
            - 22,80,443,3389: 指定端口
        scan_type: 扫描类型
            - SYN: SYN扫描（半开扫描，需要root权限）
            - TCP: TCP全连接扫描
            - UDP: UDP扫描
    
    返回：
        扫描结果，包含开放端口列表、服务版本、操作系统信息
    
    示例：
        输入: 192.168.1.1, 1-1000, SYN
        输出: {
            "target": "192.168.1.1",
            "open_ports": [
                {"port": 22, "service": "ssh", "version": "OpenSSH 7.4"},
                {"port": 80, "service": "http", "version": "Apache 2.4.6"}
            ],
            "scan_type": "SYN"
        }
    """
    ctx = _get_context("port_scan")
    logger.info(f"[port_scan] 端口扫描: {target}, 范围: {port_range}, 类型: {scan_type}")
    
    try:
        # 构建Nmap命令
        if scan_type == "SYN":
            flags = "-sS"
        elif scan_type == "UDP":
            flags = "-sU"
        else:
            flags = "-sT"
        
        # 执行Nmap扫描
        cmd = f"nmap {flags} -sV -O -p {port_range} --min-rate 1000 {target}"
        logger.info(f"[port_scan] 执行命令: {cmd}")
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout
        
        # 解析Nmap输出
        open_ports = []
        lines = output.split('\n')
        for line in lines:
            if '/open' in line and 'tcp' in line:
                parts = line.split()
                if len(parts) >= 3:
                    port_info = parts[0].split('/')
                    port = port_info[0]
                    service = parts[2] if len(parts) > 2 else "unknown"
                    version = ' '.join(parts[3:]) if len(parts) > 3 else ""
                    
                    open_ports.append({
                        "port": port,
                        "protocol": port_info[1] if len(port_info) > 1 else "tcp",
                        "service": service,
                        "version": version
                    })
        
        result_output = {
            "target": target,
            "port_range": port_range,
            "scan_type": scan_type,
            "open_ports": open_ports,
            "total_open": len(open_ports),
            "raw_output": output,
            "status": "success"
        }
        
        logger.info(f"[port_scan] 扫描完成: {target} 发现 {len(open_ports)} 个开放端口")
        return json.dumps(result_output, ensure_ascii=False, indent=2)
        
    except subprocess.TimeoutExpired:
        error_msg = f"端口扫描超时: {target}"
        logger.error(f"[port_scan] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"端口扫描异常: {str(e)}"
        logger.error(f"[port_scan] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def service_detection(target: str, port: int) -> str:
    """
    服务识别工具
    
    功能：识别目标端口上运行的具体服务及其版本信息
    
    用途：
    - 确认端口对应服务的具体类型
    - 获取服务版本号用于漏洞匹配
    - 识别非标准端口的服务
    - 检测隐藏或伪装的服务
    
    参数：
        target: 目标IP或域名
        port: 端口号 (例: 80, 443, 22)
    
    返回：
        服务识别结果，包含banner信息、版本详情、可能的漏洞
    
    示例：
        输入: 192.168.1.1, 80
        输出: {
            "target": "192.168.1.1",
            "port": 80,
            "service": "http",
            "banner": "Apache/2.4.6 (CentOS)",
            "technologies": ["PHP", "jQuery"],
            "potential_vulns": ["CVE-2017-15710"]
        }
    """
    ctx = _get_context("service_detection")
    logger.info(f"[service_detection] 服务识别: {target}:{port}")
    
    try:
        import socket
        
        result = {
            "target": target,
            "port": port,
            "status": "success"
        }
        
        # 尝试连接并获取banner
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((target, port))
            
            # 发送HTTP请求获取更多信息
            if port in [80, 8080, 8000, 443, 8443]:
                s.send(b"HEAD / HTTP/1.0\r\n\r\n")
            
            banner = s.recv(1024).decode('utf-8', errors='ignore').strip()
            s.close()
            
            result["banner"] = banner
            
            # 分析banner提取信息
            if "Apache" in banner:
                result["service"] = "http"
                result["server"] = "Apache"
            elif "nginx" in banner:
                result["service"] = "http"
                result["server"] = "Nginx"
            elif "Microsoft" in banner:
                result["service"] = "http"
                result["server"] = "IIS"
            else:
                result["service"] = "unknown"
                
        except socket.timeout:
            result["banner"] = "Connection timeout"
        except ConnectionRefusedError:
            result["banner"] = "Connection refused"
        except Exception as e:
            result["banner"] = f"Error: {str(e)}"
        
        logger.info(f"[service_detection] 识别完成: {target}:{port}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"服务识别异常: {str(e)}"
        logger.error(f"[service_detection] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def dir_enum(target_url: str, wordlist: str = None, extensions: str = "php,html,asp") -> str:
    """
    目录枚举工具
    
    功能：使用字典枚举Web服务器的隐藏目录和文件
    
    用途：
    - 发现管理后台和敏感路径
    - 找到备份文件和配置文件
    - 识别测试页面和调试接口
    - 发现Webshell和后门文件
    
    参数：
        target_url: 目标URL (例: http://example.com)
        wordlist: 字典文件路径 (默认使用内置字典)
        extensions: 要测试的文件扩展名，用逗号分隔 (默认: php,html,asp)
    
    返回：
        发现的目录和文件列表
    
    示例：
        输入: http://example.com, extensions=php,html
        输出: {
            "target": "http://example.com",
            "found": [
                {"path": "/admin", "status": 200},
                {"path": "/login.php", "status": 200},
                {"path": "/config.php", "status": 200},
                {"path": "/robots.txt", "status": 200}
            ],
            "total": 4
        }
    """
    ctx = _get_context("dir_enum")
    logger.info(f"[dir_enum] 目录枚举: {target_url}")
    
    try:
        # 内置常用目录字典
        default_dirs = [
            "/", "/admin", "/login", "/admin.php", "/login.php", "/administrator",
            "/wp-admin", "/wp-login.php", "/cms", "/manage", "/management",
            "/backup", "/backups", "/admin/login", "/dashboard", "/console",
            "/api", "/api.php", "/rest", "/soap", "/graphql", "/swagger",
            "/robots.txt", "/sitemap.xml", "/crossdomain.xml", "/clientaccesspolicy.xml",
            "/config", "/configuration", "/settings", "/includes", "/inc",
            "/lib", "/library", "/vendor", "/node_modules", "/packages",
            "/test", "/tests", "/testing", "/debug", "/debugger",
            "/phpmyadmin", "/pma", "/adminer", "/mysql", "/sql",
            "/upload", "/uploads", "/images", "/img", "/files",
            "/docs", "/documents", "/downloads", "/data", "/database",
            "/.git", "/.svn", "/.env", "/.htaccess", "/web.config",
            "/index.php", "/index.html", "/index.htm", "/default.aspx",
            "/info.php", "/phpinfo.php", "/status", "/health", "/ping",
            "/actuator", "/env", "/heapdump", "/spring", "/jmx",
            "/console", "/swagger-ui", "/api-docs", "/v2/api-docs",
            "/webmail", "/owa", "/autodiscover", "/microsoft-server-activesync"
        ]
        
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        found = []
        ext_list = [e.strip() for e in extensions.split(',')]
        
        # 规范化URL
        if not target_url.startswith('http'):
            target_url = 'http://' + target_url
        base_url = target_url.rstrip('/')
        
        # 添加URL末尾斜杠
        if not base_url.endswith('/') and not target_url.endswith('/'):
            base_url += '/'
        
        # 遍历目录字典
        for path in default_dirs:
            for ext in ext_list:
                if ext:
                    test_path = f"{base_url}{path}.{ext}" if not path.startswith('/') else f"{base_url}{path}.{ext}"
                else:
                    test_path = f"{base_url}{path}" if not path.startswith('/') else f"{base_url}{path}"
                
                try:
                    response = requests.get(test_path, timeout=5, verify=False, allow_redirects=False)
                    
                    if response.status_code in [200, 201, 204, 301, 302, 403]:
                        found.append({
                            "path": test_path,
                            "status": response.status_code,
                            "size": len(response.content)
                        })
                        logger.info(f"[dir_enum] 发现: {test_path} [{response.status_code}]")
                        
                except requests.RequestException:
                    pass
        
        result = {
            "target": target_url,
            "found": found,
            "total": len(found),
            "status": "success"
        }
        
        logger.info(f"[dir_enum] 完成: 发现 {len(found)} 个路径")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"目录枚举异常: {str(e)}"
        logger.error(f"[dir_enum] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def fingerprint_scan(target_url: str) -> str:
    """
    指纹识别工具
    
    功能：识别Web应用的技术栈、框架和组件
    
    用途：
    - 确定目标使用的技术框架
    - 识别CMS类型和版本
    - 发现JavaScript库和前端框架
    - 辅助漏洞利用和版本匹配
    
    参数：
        target_url: 目标URL (例: http://example.com)
    
    返回：
        指纹识别结果，包含服务器类型、CMS、框架、JS库等
    
    示例：
        输入: http://example.com
        输出: {
            "target": "http://example.com",
            "server": "Apache/2.4.6",
            "cms": "WordPress 5.8",
            "frameworks": ["jQuery 3.6.0", "PHP 7.4"],
            "technologies": ["MySQL", "WordPress"]
        }
    """
    ctx = _get_context("fingerprint_scan")
    logger.info(f"[fingerprint_scan] 指纹识别: {target_url}")
    
    try:
        import requests
        import re
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        result = {
            "target": target_url,
            "status": "success"
        }
        
        # 发送请求获取响应头和内容
        try:
            if not target_url.startswith('http'):
                target_url = 'http://' + target_url
            
            response = requests.get(target_url, timeout=10, verify=False)
            headers = response.headers
            content = response.text
            
            # 服务器指纹
            if 'Server' in headers:
                result['server'] = headers['Server']
            
            # X-Powered-By
            if 'X-Powered-By' in headers:
                result['powered_by'] = headers['X-Powered-By']
            
            # 检测CMS
            cms_patterns = {
                'WordPress': r'wp-content|wp-includes|wordpress',
                'Joomla': r'/joomla|com_content|Joomla',
                'Drupal': r'drupal|sites/all|drupal.org',
                'Typecho': r'typecho|admin/index.php|欢迎使用Typecho',
                'MetInfo': r'MetInfo|member/login|metinfo',
                'ECShop': r'ecshop|shop powered by|d60b2f2'
            }
            
            result['cms'] = []
            for cms, pattern in cms_patterns.items():
                if re.search(pattern, content, re.I):
                    result['cms'].append(cms)
            
            # 检测前端框架
            framework_patterns = {
                'jQuery': r'jquery[/-](\d+\.\d+\.\d+)',
                'Vue': r'vue[.-](\d+\.\d+\.\d+)',
                'React': r'react[.-](\d+\.\d+\.\d+)',
                'Angular': r'@angular/core[/-](\d+\.\d+\.\d+)',
                'Bootstrap': r'bootstrap[/-](\d+\.\d+\.\d+)'
            }
            
            result['frameworks'] = []
            for framework, pattern in framework_patterns.items():
                match = re.search(pattern, content, re.I)
                if match:
                    result['frameworks'].append(f"{framework} {match.group(1) if match.lastindex else ''}".strip())
            
            # 检测编程语言
            lang_patterns = {
                'PHP': r'<\?php|\.php|PHP',
                'ASP.NET': r'\.aspx|__VIEWSTATE|aspnet',
                'Java': r'\.jsp|JSESSIONID',
                'Python': r'\.py|flask|django|python'
            }
            
            result['languages'] = []
            for lang, pattern in lang_patterns.items():
                if re.search(pattern, content, re.I):
                    result['languages'].append(lang)
            
            # 检测CDN和WAF
            if 'CDN' in headers.get('X-Cache', '') or 'Cloudflare' in headers.get('Server', ''):
                result['cdn'] = 'Cloudflare'
            elif 'Akamai' in headers.get('Server', ''):
                result['cdn'] = 'Akamai'
                
        except requests.RequestException as e:
            result['error'] = str(e)
        
        logger.info(f"[fingerprint_scan] 指纹识别完成: {target_url}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"指纹识别异常: {str(e)}"
        logger.error(f"[fingerprint_scan] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
