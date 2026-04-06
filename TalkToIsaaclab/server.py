from mcp.server.fastmcp import FastMCP
import subprocess
import shutil
import time
import re
import os
import sys
import json
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional

# ========== 配置区 ==========
ISAACLAB_ROOT = Path(r"E:\IsaacLab")
TRAIN_SCRIPT = "scripts/reinforcement_learning/rsl_rl/train.py"
PLAY_SCRIPT = "scripts/reinforcement_learning/rsl_rl/play.py"
PYTHON_PATH = r"E:\D1CK\envs\isaaclab\python.exe"

HOMUNCULUS_ROOT = Path(r"E:\Homunculus")
CACHE_DIR = HOMUNCULUS_ROOT / "cache"
BACKUP_DIR = HOMUNCULUS_ROOT / "backups"
LOG_DIR = HOMUNCULUS_ROOT / "logs"
PID_FILE = LOG_DIR / "current_training.pid"

# 自动创建目录
for d in [HOMUNCULUS_ROOT, CACHE_DIR, BACKUP_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_FILE = CACHE_DIR / "isaaclab_knowledge.json"
CFG_PATH = Path(r"E:\IsaacLab\source\isaaclab_tasks\isaaclab_tasks\manager_based\locomotion\recovery\config\go2\stand_up_env_cfg.py")
TASK_NAME = "Isaac-StandUp-Go2-v0"

mcp = FastMCP("Homunculus")

# ========== 进程管理核心 ==========
_current_proc: Optional[subprocess.Popen] = None
_log_queue = queue.Queue()
_current_log_path: Optional[Path] = None

def _write_pid(pid: int):
    try:
        PID_FILE.write_text(str(pid))
    except Exception as e:
        print(f"[PID写入失败] {e}", file=sys.stderr)

def _read_pid() -> Optional[int]:
    try:
        if PID_FILE.exists():
            return int(PID_FILE.read_text().strip())
    except:
        pass
    return None

def _clear_pid():
    try:
        PID_FILE.unlink(missing_ok=True)
    except:
        pass

def _is_process_running(pid: int) -> bool:
    if pid is None:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except ImportError:
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            return str(pid) in result.stdout
        except:
            return False

def _get_new_log_path() -> Path:
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    return LOG_DIR / f"training_{timestamp}.log"

# ========== MCP工具（与Client完全匹配） ==========

@mcp.tool()
def get_task_info() -> str:
    """返回当前默认任务的技术信息"""
    return (
        f"【任务信息】\n"
        f"任务名: {TASK_NAME}\n"
        f"配置文件: {CFG_PATH.name}\n"
        f"训练脚本: {TRAIN_SCRIPT}\n"
        f"日志目录: {LOG_DIR}\n\n"
        f"【示例命令】\n"
        f"python {TRAIN_SCRIPT} --task={TASK_NAME} --num_envs 128 --max_iterations 100 --headless\n\n"
        f"【可调参数】\n"
        f"- --num_envs: 并行环境数（默认128，根据显存调整）\n"
        f"- --max_iterations: 最大迭代次数（默认100）\n"
        f"- --headless: 无GUI模式（必须）\n"
        f"- --checkpoint: 从检查点恢复（可选）"
    )

@mcp.tool()
def start_training(command: str = "") -> str:
    """
    一句话启动训练，直接写磁盘日志（解决11KB卡死）。
    """
    global _current_proc, _current_log_path
    
    # 检查已有进程
    existing_pid = _read_pid()
    if existing_pid and _is_process_running(existing_pid):
        return f"⚠️ 已有训练运行中 (PID: {existing_pid})"
    
    # 清理残留
    if _current_proc and _current_proc.poll() is None:
        try:
            _current_proc.terminate()
            _current_proc.wait(timeout=3)
        except:
            pass
    _clear_pid()
    
    # 生成日志路径（立即创建空文件）
    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    log_path = LOG_DIR / f"training_{timestamp}.log"
    _current_log_path = log_path
    log_path.touch()  # 立即创建空文件
    
    # 构建命令
    cmd_parts = [str(PYTHON_PATH), "-u", str(ISAACLAB_ROOT / TRAIN_SCRIPT)]
    
    user_cmd = command.strip()
    if user_cmd:
        user_cmd = re.sub(r'^python\s+', '', user_cmd, flags=re.IGNORECASE)
        user_cmd = re.sub(r'.*?train\.py\s*', '', user_cmd, flags=re.IGNORECASE)
        user_cmd = re.sub(r'[|<>2&1\s]+$', '', user_cmd)
        if user_cmd:
            cmd_parts.extend(user_cmd.split())
    
    if not any('--task' in str(p) for p in cmd_parts):
        cmd_parts.extend(["--task", TASK_NAME])
    if not any('--headless' in str(p) for p in cmd_parts):
        cmd_parts.append("--headless")
    
    # 🔑 关键：Shell重定向到文件，绕过PIPE缓冲
    full_cmd = " ".join(f'"{p}"' if " " in p else p for p in cmd_parts)
    shell_cmd = f'{full_cmd} > "{log_path}" 2>&1'
    
    # 启动（不捕获PIPE）
    try:
        proc = subprocess.Popen(
            shell_cmd,
            shell=True,
            stdin=subprocess.DEVNULL,
            cwd=str(ISAACLAB_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        _current_proc = proc
        _write_pid(proc.pid)
        
        return f"🚀 训练已启动（直接写磁盘）\n📌 PID: {proc.pid}\n📜 日志: {log_path.name}"
        
    except Exception as e:
        _clear_pid()
        return f"❌ 启动失败: {e}"

@mcp.tool()
def stop_training() -> str:
    """强制停止训练（杀进程树），保留完整日志"""
    pid = _read_pid()

    if not pid:
        if _current_proc and _current_proc.poll() is None:
            pid = _current_proc.pid
        else:
            return "ℹ️ 未检测到运行中的训练"

    if not _is_process_running(pid):
        _clear_pid()
        return "ℹ️ 训练已结束"

    try:
        result = subprocess.run(
            ['taskkill', '/PID', str(pid), '/T', '/F'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )

        time.sleep(0.5)

        drain_count = 0
        while not _log_queue.empty() and drain_count < 1000:
            try:
                _log_queue.get_nowait()
                drain_count += 1
            except:
                break

        _clear_pid()

        if result.returncode == 0 or "成功" in result.stdout:
            log_name = _current_log_path.name if _current_log_path else "unknown"
            return f"🛑 已停止 (PID: {pid})\n📜 日志: {log_name}"
        else:
            return f"⚠️ 停止结果: {result.stdout}"

    except Exception as e:
        return f"❌ 停止异常: {e}"

@mcp.tool()
def get_status() -> str:
    """查看训练状态（不读日志，极速响应）"""
    pid = _read_pid()

    if not pid:
        if _current_proc and _current_proc.poll() is None:
            pid = _current_proc.pid
        else:
            return "⏹️ 空闲"

    if _is_process_running(pid):
        try:
            import psutil
            p = psutil.Process(pid)
            runtime = time.time() - p.create_time()
            mins = int(runtime // 60)
            secs = int(runtime % 60)
            time_str = f"{mins}分{secs}秒"
        except:
            time_str = "未知"

        log_name = _current_log_path.name if _current_log_path else "未指定"
        return (
            f"▶️ 训练中 (PID: {pid})\n"
            f"⏱️ 运行时间: {time_str}\n"
            f"📜 当前日志: {log_name}"
        )
    else:
        _clear_pid()
        try:
            latest_log = max(LOG_DIR.glob("training_*.log"), key=lambda x: x.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_log.stat().st_mtime).strftime("%H:%M:%S")
            return f"⏹️ 空闲\n📜 最新日志: {latest_log.name} (更新于{mtime})"
        except:
            return "⏹️ 空闲"
@mcp.tool()
def read_training_log(lines: int = 50, keyword: str = "", confirmed: bool = False) -> str:
    """
    读取训练日志。大文件全文(>100KB)或>500行需confirmed=True。
    """
    target = _current_log_path
    if not target or not target.exists():
        logs = sorted(LOG_DIR.glob("training_*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not logs:
            return "❌ 无日志文件"
        target = logs[0]
    
    try:
        file_size = target.stat().st_size
        size_kb = file_size / 1024
        total_lines = int(file_size / 200)  # 估算总行数
        
        # 大文件需要确认
        if lines == 0 and size_kb > 100 and not confirmed:
            return f"[CONFIRM_REQUIRED] size_kb={size_kb:.1f} estimated_lines={total_lines}"
        
        if lines > 500 and not confirmed:
            return f"[CONFIRM_REQUIRED] size_kb={size_kb:.1f} requested_lines={lines}"
        
        with open(target, 'r', encoding='utf-8', errors='ignore') as f:
            if lines == 0:
                # 读全文（已确认或小文件）
                content = f.read()
                all_lines = content.split('\n')
                
                if keyword:
                    all_lines = [l for l in all_lines if keyword.lower() in l.lower()]
                
                result = '\n'.join(all_lines[-2000:] if len(all_lines) > 2000 else all_lines)
                header = f"📄 全文 {len(all_lines)} 行 ({size_kb:.1f}KB)"
                
            else:
                # 读最后N行
                actual_lines = min(lines, 500) if not confirmed else lines
                
                f.seek(0, 2)
                end_pos = f.tell()
                start_pos = max(0, end_pos - actual_lines * 200 - 1024)
                
                f.seek(start_pos, 0)
                data = f.read()
                
                raw_lines = data.split('\n')
                if start_pos > 0 and raw_lines:
                    raw_lines = raw_lines[1:]
                
                all_lines = [l for l in raw_lines if l.strip()]
                
                if keyword:
                    all_lines = [l for l in all_lines if keyword.lower() in l.lower()]
                
                all_lines = all_lines[-actual_lines:] if len(all_lines) > actual_lines else all_lines
                result = '\n'.join(all_lines)
                header = f"📄 最后 {len(all_lines)} 行"
        
        is_training = bool(_read_pid() and _is_process_running(_read_pid()))
        status_icon = "▶️" if is_training else "⏹️"
        return f"{status_icon} {header}\n```\n{result}\n```"
                
    except Exception as e:
        return f"❌ 读取失败: {e}"

@mcp.tool()
def modify_config(old_text: str, new_text: str) -> str:
    """安全修改配置文件（自动备份，保留最近5个）"""
    try:
        backups = sorted(BACKUP_DIR.glob("backup_*.py"), key=lambda x: x.stat().st_mtime)
        for old in backups[:-5]:
            old.unlink()

        backup = BACKUP_DIR / f"backup_{int(time.time())}.py"
        shutil.copy(CFG_PATH, backup)

        content = CFG_PATH.read_text(encoding='utf-8')
        if old_text not in content:
            return f"❌ 未找到: '{old_text}'"

        new_content = content.replace(old_text, new_text, 1)
        CFG_PATH.write_text(new_content, encoding='utf-8')

        return f"✅ 已修改（备份: {backup.name}）"
    except Exception as e:
        return f"❌ 修改失败: {e}"

@mcp.tool()
def read_config(keyword: str = "") -> str:
    """读取配置文件（摘要或搜索）"""
    try:
        content = CFG_PATH.read_text(encoding='utf-8')

        if not keyword:
            lines = [l.strip() for l in content.split('\n')[:50] if '=' in l and len(l) < 100]
            return "📄 配置摘要:\n" + "\n".join(lines[:20])

        matches = [f"L{i:3d}: {l.strip()}" for i, l in enumerate(content.split('\n'), 1) 
                   if keyword.lower() in l.lower() and '=' in l]

        if matches:
            return f"🔍 找到 {len(matches)} 处:\n" + "\n".join(matches[:15])
        else:
            return f"⚠️ 未找到 '{keyword}'"
    except Exception as e:
        return f"❌ 读取失败: {e}"

@mcp.tool()
def list_checkpoints(user_intent: str = "") -> str:
    """
    返回所有检查点原始列表，让LLM根据user_intent智能推荐。
    user_intent: 用户自然语言描述（如"最新的""go2的""昨天下午的""奖励最高的"）
    """
    try:
        logs_dir = ISAACLAB_ROOT / "logs" / "rsl_rl"
        
        if not logs_dir.exists():
            return f"❌ 目录不存在: {logs_dir}"
        
        # 全量扫描，不做任何过滤
        checkpoints = list(logs_dir.rglob("model_*.pt"))
        
        if not checkpoints:
            return "⚠️ 未找到任何检查点"
        
        # 只按时间排序（最新在前）
        checkpoints.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 构建原始数据列表给 LLM 分析
        items = []
        for i, ckpt in enumerate(checkpoints[:15], 1):  # 返回前15个，足够LLM选
            rel = ckpt.relative_to(logs_dir)  # 如: unitree_go2_flat/2026-04-04_17-57-09/model_1500.pt
            mtime = datetime.fromtimestamp(ckpt.stat().st_mtime).strftime("%m-%d %H:%M")
            iter_num = ckpt.stem.replace("model_", "")
            size_mb = ckpt.stat().st_size / 1024 / 1024
            
            items.append(f"{i}. 路径={rel} | 迭代={iter_num} | 时间={mtime} | 大小={size_mb:.1f}MB")
        
        # 返回原始数据 + 用户意图，让 LLM 自己发挥理解
        response = "📦 可用检查点列表（按时间倒序）：\n" + "\n".join(items)
        
        if user_intent:
            response += f"\n\n💡 用户需求: {user_intent}\n"
            response += "🔍 请根据路径名（如unitree_go2_flat=Go2平地）、时间（最新/昨天）、迭代数（1500=训练充分）智能推荐最合适的序号。"
        
        return response
        
    except Exception as e:
        return f"❌ 失败: {e}"

@mcp.tool()
def play_policy(checkpoint_path: str, num_envs: int = 1) -> str:
    """
    播放训练好的策略。checkpoint_path 可以是完整路径或相对路径，
    自动转换为 IsaacLab 需要的格式（logs\rsl_rl\...\model_xx.pt）。
    """
    try:
        log_path = LOG_DIR / f"play_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        path_obj = Path(checkpoint_path)
        
        if path_obj.is_absolute():
            # 完整路径，提取相对于 ISAACLAB_ROOT 的部分
            try:
                rel_path = path_obj.relative_to(ISAACLAB_ROOT)
                checkpoint_arg = str(rel_path)  # 变成 logs\rsl_rl\...
            except ValueError:
                # 不在 IsaacLab 目录下，尝试提取 logs 以后的部分
                if "logs" in str(path_obj):
                    parts = str(path_obj).split("logs\\")
                    checkpoint_arg = f"logs\\{parts[-1]}"
                else:
                    checkpoint_arg = checkpoint_path  # 兜底，原样传入
        else:
            # 已经是相对路径，检查是否包含 logs\rsl_rl 前缀
            if str(path_obj).startswith("logs"):
                checkpoint_arg = str(path_obj)
            else:
                # 只传了 experiment\timestamp\model_xx.pt，补前缀
                checkpoint_arg = f"logs\\rsl_rl\\{path_obj}"
    
        checkpoint_arg = checkpoint_arg.replace("/", "\\")

        cmd = (
            f'"{PYTHON_PATH}" -u {ISAACLAB_ROOT / PLAY_SCRIPT} '
            f'--task={TASK_NAME} '
            f'--checkpoint={checkpoint_arg} '  
            f'--num_envs={num_envs}'
        )

        subprocess.Popen(
            f'{cmd} > "{log_path}" 2>&1',
            shell=True,
            cwd=str(ISAACLAB_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        return (
            f"▶️ 播放启动\n"
            f"🎬 检查点: {checkpoint_arg}\n"  
            f"📜 日志: {log_path.name}"
        )
    except Exception as e:
        import traceback
        return f"❌ 播放失败: {e}\n{traceback.format_exc()[:200]}"
@mcp.tool()
def build_knowledge_base(force_refresh: bool = False) -> str:
    """扫描IsaacLab源码建立本地知识库"""
    if KNOWLEDGE_FILE.exists() and not force_refresh:
        stats = KNOWLEDGE_FILE.stat()
        mtime = time.strftime("%m-%d %H:%M", time.localtime(stats.st_mtime))
        return (
            f"✅ 知识库已存在 ({stats.st_size/1024:.1f}KB)\n"
            f"   更新于: {mtime}"
        )
    
    try:

        files_to_scan = {
            "rewards": ISAACLAB_ROOT / "source" / "isaaclab" / "isaaclab" / "envs" / "mdp" / "rewards.py",
            "observations": ISAACLAB_ROOT / "source" / "isaaclab" / "isaaclab" / "envs" / "mdp" / "observations.py",
            "terminations": ISAACLAB_ROOT / "source" / "isaaclab" / "isaaclab" / "envs" / "mdp" / "terminations.py",
            "curriculums": ISAACLAB_ROOT / "source" / "isaaclab" / "isaaclab" / "envs" / "mdp" / "curriculums.py",
            "events": ISAACLAB_ROOT / "source" / "isaaclab" / "isaaclab" / "envs" / "mdp" / "events.py",
        }
        
        knowledge = {"meta": {"built_at": time.strftime("%Y-%m-%d %H:%M:%S")}}
        
        for category, full_path in files_to_scan.items():

            if not full_path.exists():
                knowledge[category] = f"❌ 文件不存在: {str(full_path)}"
                continue
            
            content = full_path.read_text(encoding='utf-8')
            
            functions = []
            for match in re.finditer(r'def\s+(\w+)\s*\([^)]*\)[^:]*:', content):
                func_name = match.group(1)
                start = match.start()
                snippet = content[start:start+300].replace('\n', ' ')[:150]
                functions.append({"name": func_name, "snippet": snippet})
            

            knowledge[category] = {
                "file": str(full_path.relative_to(ISAACLAB_ROOT)),  # 转字符串
                "functions": functions[:40],
                "total_lines": len(content.split('\n'))
            }
        
        # 🔑 确保所有value都能JSON序列化
        KNOWLEDGE_FILE.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding='utf-8')
        
        total_funcs = sum(len(k.get("functions", [])) for k in knowledge.values() if isinstance(k, dict))
        return f"✅ 知识库构建完成\n   文件: {KNOWLEDGE_FILE}\n   提取: {total_funcs} 个函数"
        
    except Exception as e:
        import traceback
        return f"❌ 构建失败: {e}\n{traceback.format_exc()[:200]}"

@mcp.tool()
def query_knowledge(category: str, keyword: str = "") -> str:
    """查询本地知识库"""
    try:
        if not KNOWLEDGE_FILE.exists():
            build_knowledge_base()

        if not KNOWLEDGE_FILE.exists():
            return "❌ 知识库创建失败"

        knowledge = json.loads(KNOWLEDGE_FILE.read_text(encoding='utf-8'))

        if category not in knowledge or isinstance(knowledge[category], str):
            available = [k for k in knowledge.keys() if k != "meta"]
            return f"⚠️ 类别 '{category}' 不存在\n可用: {available}"

        cat_data = knowledge[category]
        functions = cat_data.get("functions", [])

        if not keyword:
            lines = [f"{i+1}. {f['name']}" for i, f in enumerate(functions[:20])]
            return (
                f"📚 {category} ({len(functions)}个函数)\n"
                f"   显示前20个:\n" + "\n".join(lines)
            )

        matches = [f for f in functions if keyword.lower() in f['name'].lower()]
        if not matches:
            all_names = [f['name'] for f in functions[:10]]
            return f"⚠️ 未找到 '{keyword}'\n提示: {', '.join(all_names[:5])}"

        lines = []
        for f in matches[:8]:
            lines.append(f"🔧 {f['name']}\n   {f['snippet']}...")

        return f"📚 找到 {len(matches)} 个匹配:\n" + "\n\n".join(lines)

    except Exception as e:
        return f"❌ 查询失败: {e}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
