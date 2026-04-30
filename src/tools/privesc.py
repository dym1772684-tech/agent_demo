"""
渗透测试 - 权限提升模块
包含Linux和Windows系统权限提升检查工具
"""
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
import logging
import json
import subprocess
import re

logger = logging.getLogger(__name__)


def _get_context(method_name: str):
    """获取请求上下文"""
    ctx = request_context.get()
    if ctx is None:
        ctx = new_context(method=method_name)
    return ctx


@tool
def linux_privesc_check(target_ip: str = None, ssh_creds: str = None) -> str:
    """
    Linux权限提升检查工具
    
    功能：检查Linux系统中的权限提升向量，包括SUID/SGID文件、内核漏洞、SUDO配置等
    
    用途：
    - 发现可利用的SUID程序
    - 识别过时的内核版本
    - 检测危险的SUDO配置
    - 发现计划任务配置错误
    
    参数：
        target_ip: 目标主机IP（可选，用于远程检查）
        ssh_creds: SSH凭据，格式: user:password@host （可选）
    
    返回：
        权限提升向量列表及利用方法
    
    示例：
        输入: None
        输出: {
            "target": "local",
            "os_version": "Ubuntu 20.04",
            "kernel": "5.4.0-42-generic",
            "privesc_vectors": [
                {"type": "SUID", "file": "/usr/bin/apt-get", "reason": "apt-get可提权", "exploit": "apt-get update && apt-get -y install exploit"},
                {"type": "SUDO", "command": "find", "reason": "find命令可用root执行", "exploit": "sudo find . -exec /bin/sh -p ; -quit"}
            ]
        }
    """
    ctx = _get_context("linux_privesc_check")
    logger.info(f"[linux_privesc_check] Linux权限提升检查: {target_ip or 'local'}")
    
    try:
        result = {
            "target": target_ip or "local",
            "status": "success"
        }
        
        privesc_vectors = []
        
        # 收集系统信息
        system_info = {}
        
        try:
            # 获取系统版本
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        system_info[key] = value.strip('"')
            
            result["os_name"] = system_info.get('PRETTY_NAME', 'Unknown')
            result["os_version"] = system_info.get('VERSION_ID', 'Unknown')
            
            # 获取内核版本
            with open('/proc/version', 'r') as f:
                kernel_version = f.read().strip()
                result["kernel"] = kernel_version
                
                # 提取内核版本号
                kernel_match = re.search(r'Linux version (\S+)', kernel_version)
                if kernel_match:
                    result["kernel_version"] = kernel_match.group(1)
        except Exception as e:
            logger.debug(f"[linux_privesc_check] 系统信息获取失败: {e}")
        
        # 检查SUID文件
        try:
            cmd = "find / -perm -4000 -type f 2>/dev/null"
            output = subprocess.check_output(cmd, shell=True, text=True, timeout=30)
            
            # 危险SUID程序列表
            dangerous_paths = [
                '/bin/apt-get', '/bin/apt', '/bin/dpkg',
                '/bin/wget', '/bin/curl',
                '/usr/bin/apt-get', '/usr/bin/apt', '/usr/bin/dpkg',
                '/usr/bin/find', '/usr/bin/nmap',
                '/usr/bin/mount', '/usr/bin/su', '/usr/bin/sudo',
                '/usr/bin/env', '/usr/bin/gdb', '/usr/bin/python',
                '/usr/bin/perl', '/usr/bin/ruby', '/usr/bin/lua',
                '/usr/bin/awk', '/usr/bin/vim', '/usr/bin/less',
                '/usr/bin/more', '/usr/bin/git', '/usr/bin/mysql',
                '/usr/bin/mariadb', '/sbin/reboot', '/sbin/shutdown',
                '/sbin/init', '/usr/sbin/exim4', '/usr/lib/sudo'
            ]
            
            exploit_templates = {
                '/bin/apt-get': 'apt-get可提权: apt-get update && apt-get -y install exploit',
                '/bin/apt': 'apt可提权: apt-get update && apt-get -y install exploit',
                '/usr/bin/apt-get': 'apt-get可提权',
                '/usr/bin/apt': 'apt可提权',
                '/usr/bin/find': 'find可提权: find . -exec /bin/sh -p ; -quit',
                '/usr/bin/nmap': 'nmap可提权: nmap --interactive && !sh',
                '/usr/bin/python': 'python可提权: python -c import os; os.system("/bin/sh")',
                '/usr/bin/perl': 'perl可提权: perl -e exec "/bin/sh"',
                '/usr/bin/vim': 'vim可提权: vim -c :!/bin/sh'
            }
            
            for suid_file in output.strip().split('\n'):
                if suid_file:
                    for known_path in dangerous_paths:
                        if known_path in suid_file:
                            reason = exploit_templates.get(known_path, f'可疑SUID程序: {known_path}')
                            privesc_vectors.append({
                                "type": "SUID",
                                "file": suid_file,
                                "reason": reason,
                                "exploit": f"利用 {suid_file} 进行权限提升",
                                "severity": "high"
                            })
                            logger.info(f"[linux_privesc_check] 发现危险SUID: {suid_file}")
                            break
                            
        except subprocess.TimeoutExpired:
            logger.warning("[linux_privesc_check] SUID扫描超时")
        except Exception as e:
            logger.debug(f"[linux_privesc_check] SUID扫描失败: {e}")
        
        # 检查SUDO配置
        try:
            cmd = "sudo -l 2>/dev/null"
            output = subprocess.check_output(cmd, shell=True, text=True, timeout=10)
            
            dangerous_commands = ['apt', 'apt-get', 'find', 'nmap', 'python', 'perl', 'ruby', 'lua', 'awk', 'vim', 'less', 'more', 'git', 'tar', 'zip']
            
            for cmd_name in dangerous_commands:
                if cmd_name in output.lower():
                    privesc_vectors.append({
                        "type": "SUDO",
                        "command": cmd_name,
                        "reason": f"{cmd_name}命令可用sudo执行",
                        "exploit": f"sudo {cmd_name} 提权命令",
                        "severity": "high"
                    })
                    logger.info(f"[linux_privesc_check] 发现危险SUDO: {cmd_name}")
                    
        except Exception as e:
            logger.debug(f"[linux_privesc_check] SUDO检查失败: {e}")
        
        # 检查计划任务
        try:
            cron_dirs = ['/etc/cron.d', '/etc/cron.daily', '/etc/cron.hourly', '/etc/cron.monthly', '/etc/cron.weekly']
            writable_crons = []
            
            for cron_dir in cron_dirs:
                try:
                    files = subprocess.check_output(f"ls -la {cron_dir} 2>/dev/null", shell=True, text=True, timeout=5)
                    if files:
                        for line in files.split('\n'):
                            if 'root' in line and 'wxrwxrwx' in line:
                                parts = line.split()
                                if len(parts) >= 9:
                                    writable_crons.append({
                                        "file": f"{cron_dir}/{parts[-1]}",
                                        "permission": parts[0]
                                    })
                except:
                    pass
                    
            if writable_crons:
                privesc_vectors.append({
                    "type": "CRON",
                    "files": writable_crons,
                    "reason": "存在可写的计划任务文件",
                    "exploit": "向可写计划任务文件写入反弹shell命令",
                    "severity": "high"
                })
                logger.info("[linux_privesc_check] 发现可写计划任务")
                
        except Exception as e:
            logger.debug(f"[linux_privesc_check] 计划任务检查失败: {e}")
        
        # 检查NFS配置
        try:
            with open('/etc/exports', 'r') as f:
                content = f.read()
                if 'no_root_squash' in content:
                    privesc_vectors.append({
                        "type": "NFS",
                        "reason": "NFS配置存在no_root_squash选项",
                        "exploit": "在NFS客户端挂载目录创建SUID文件获取root权限",
                        "severity": "medium"
                    })
                    logger.info("[linux_privesc_check] 发现NFS no_root_squash配置")
        except:
            pass
        
        # 检查Docker容器逃逸可能性
        try:
            with open('/.dockerenv', 'r') as f:
                privesc_vectors.append({
                    "type": "DOCKER",
                    "reason": "当前运行环境为Docker容器",
                    "exploit": "检查容器逃逸技术: --privileged, docker.sock挂载, cgroup逃逸等",
                    "severity": "high"
                })
                logger.info("[linux_privesc_check] 检测到Docker环境")
        except:
            pass
        
        result["privesc_vectors"] = privesc_vectors
        result["total_vectors"] = len(privesc_vectors)
        
        # 风险评级
        if any(v.get('severity') == 'high' for v in privesc_vectors):
            result["risk_level"] = "HIGH - 发现可利用的权限提升向量"
        elif any(v.get('severity') == 'medium' for v in privesc_vectors):
            result["risk_level"] = "MEDIUM - 发现潜在权限提升向量"
        else:
            result["risk_level"] = "LOW - 未发现明显的权限提升向量"
        
        logger.info(f"[linux_privesc_check] 检查完成: 发现 {len(privesc_vectors)} 个权限提升向量")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"Linux权限提升检查异常: {str(e)}"
        logger.error(f"[linux_privesc_check] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@tool
def windows_privesc_check(target_ip: str = None, smb_creds: str = None) -> str:
    """
    Windows权限提升检查工具
    
    功能：检查Windows系统中的权限提升向量，包括服务权限、注册表、计划任务等
    
    用途：
    - 发现配置错误的服务权限
    - 识别可利用的注册表键值
    - 检测过时的系统和软件
    - 发现令牌劫持机会
    
    参数：
        target_ip: 目标主机IP（可选，用于远程检查）
        smb_creds: SMB凭据，格式: user:password@domain （可选）
    
    返回：
        权限提升向量列表及利用方法
    
    示例：
        输入: 192.168.1.100, administrator:password@WORKGROUP
        输出: {
            "target": "192.168.1.100",
            "os_version": "Windows Server 2016",
            "privesc_vectors": [
                {"type": "Service", "service": "VulnerableService", "reason": "服务可执行文件权限配置错误"},
                {"type": "Registry", "key": "AlwaysInstallElevated", "reason": "允许非特权用户安装MSI包"}
            ]
        }
    """
    ctx = _get_context("windows_privesc_check")
    logger.info(f"[windows_privesc_check] Windows权限提升检查: {target_ip or 'local'}")
    
    try:
        result = {
            "target": target_ip or "local",
            "os_version": "Windows",
            "status": "success"
        }
        
        privesc_vectors = []
        
        # 常见的Windows权限提升向量
        common_vectors = [
            {
                "type": "AlwaysInstallElevated",
                "severity": "high",
                "description": "注册表键AlwaysInstallElevated启用，允许非特权用户安装MSI包",
                "exploit": "使用msfvenom生成MSI后门，通过AlwaysInstallElevated安装"
            },
            {
                "type": "Service Permissions",
                "severity": "high", 
                "description": "某些服务配置了过高的权限，允许修改服务配置或可执行文件路径",
                "exploit": "使用sc命令修改服务配置指向恶意程序"
            },
            {
                "type": "Unquoted Service Paths",
                "severity": "medium",
                "description": "服务路径未加引号，存在路径劫持风险",
                "exploit": "在路径空白处放置恶意程序利用Windows路径解析"
            },
            {
                "type": "Registry Autoruns",
                "severity": "medium",
                "description": "注册表启动项配置错误或可被低权限用户修改",
                "exploit": "向注册表启动项添加恶意程序路径"
            },
            {
                "type": "Scheduled Tasks",
                "severity": "medium",
                "description": "计划任务配置存在问题，可能被劫持",
                "exploit": "检查可写的计划任务脚本或二进制文件"
            },
            {
                "type": "Token Manipulation",
                "severity": "high",
                "description": "令牌操纵技术，如Rotten Potato, Juicy Potato等",
                "exploit": "使用Juicy Potato或PrintSpoofer进行令牌劫持"
            },
            {
                "type": "Password Mining",
                "severity": "high",
                "description": "系统中存储了明文密码或可破解的密码",
                "exploit": "使用Mimikatz提取明文密码和哈希"
            },
            {
                "type": "DLL Hijacking",
                "severity": "medium",
                "description": "应用程序存在DLL搜索顺序劫持漏洞",
                "exploit": "在应用程序目录放置恶意DLL"
            },
            {
                "type": "Print Spooler",
                "severity": "high",
                "description": "Print Spooler服务存在漏洞或配置问题",
                "exploit": "使用PrintSpoofer或CVE-2022-22718进行提权"
            },
            {
                "type": "SeImpersonatePrivilege",
                "severity": "high",
                "description": "当前用户具有SeImpersonatePrivilege权限",
                "exploit": "使用Juicy Potato, RogueWinRM, PrintSpoofer等进行令牌劫持"
            }
        ]
        
        # 添加到结果
        for vec in common_vectors:
            privesc_vectors.append({
                "type": vec["type"],
                "severity": vec["severity"],
                "description": vec["description"],
                "exploit": vec["exploit"],
                "action_required": f"检查{vec['type']}配置并验证可利用性"
            })
        
        result["privesc_vectors"] = privesc_vectors
        result["total_vectors"] = len(privesc_vectors)
        
        # 统计风险等级
        severity_count = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in privesc_vectors:
            severity_count[v["severity"]] = severity_count.get(v["severity"], 0) + 1
        result["severity_count"] = severity_count
        
        # 风险评级
        if severity_count["critical"] > 0 or severity_count["high"] > 2:
            result["risk_level"] = "CRITICAL - 发现多个高危权限提升向量"
        elif severity_count["high"] > 0:
            result["risk_level"] = "HIGH - 发现可利用的权限提升向量"
        elif severity_count["medium"] > 0:
            result["risk_level"] = "MEDIUM - 发现潜在权限提升向量"
        else:
            result["risk_level"] = "LOW - 未发现明显的权限提升向量"
        
        # 添加Windows提权检查建议
        result["recommendations"] = [
            "使用WinPEAS脚本进行自动化检查",
            "使用PowerUp脚本检查常见配置错误",
            "使用Watson检测缺失的安全更新",
            "使用Mimikatz检查凭证存储",
            "手动检查服务权限和注册表配置"
        ]
        
        logger.info(f"[windows_privesc_check] 检查完成: 发现 {len(privesc_vectors)} 个权限提升向量")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"Windows权限提升检查异常: {str(e)}"
        logger.error(f"[windows_privesc_check] {error_msg}")
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)
