import asyncio, json, requests, re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import gradio as gr 
import queue as queue_module
import asyncio
import json
import threading
import queue as queue_module
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import gradio as gr
from openai import AsyncOpenAI
CONFIG = {
    # Kimi
    # "base_url": "https://api.moonshot.cn/v1",
    # "api_key": "sk-vnJhZLh3OQz4bMIdhZbBwYBG2lEUqN3lA25gY5xZcsii5mAP",
    # "model": "kimi-k2.5",  # 或 kimi-k2.5（有bug）
    
    # DeepSeek（推荐替代，稳定便宜）
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-c94e4a392acf4229bca23ede7e93dfef",
    "model": "deepseek-reasoner",  # 或 deepseek-reasoner（推理版）
    
    # GPT-4（OpenAI）
    # "base_url": "https://api.openai.com/v1",
    # "api_key": "sk-你的OpenAIKey",
    # "model": "gpt-4-turbo-preview",
    
    # Claude
    # "base_url": "https://api.anthropic.com/v1",  # 或兼容代理
    # "api_key": "sk-你的ClaudeKey",
    # "model": "claude-3-opus-20240229",
}
client = AsyncOpenAI(
    base_url=CONFIG["base_url"],
    api_key=CONFIG["api_key"]
)
MODEL = CONFIG["model"]
SYSTEM_PROMPT = """你是Homunculus，IsaacLab智能调参助手。

【铁律】
- 理解用户语义,用户说什么你干什么，每次调用之后要自我反思这次调用解决了什么问题

【模型信息】
当前使用模型: """ + MODEL + """
如遇API错误，请检查BASE_URL配置。"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_training_log",
            "description": "读取训练日志分析收敛情况，keyword可搜'reward'、'error'、'iteration'",
            "parameters": {
                "type": "object",
                "properties": {
                    "lines": {"type": "integer", "default": 50},
                    "keyword": {"type": "string", "default": ""}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "build_knowledge_base",
            "description": "一次性扫描IsaacLab源码建立本地缓存（rewards/observations/terminations等），后续秒查",
            "parameters": {
                "type": "object",
                "properties": {
                    "force_refresh": {"type": "boolean", "default": False}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_knowledge",
            "description": "从本地缓存查询IsaacLab知识库（秒开）。category可选: rewards, observations, terminations, curriculums, events",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "类别: rewards/observations/terminations/curriculums/events"},
                    "keyword": {"type": "string", "default": "", "description": "搜索关键词，为空返回全部列表"}
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_info",
            "description": "从CFG文件解析真实任务名（如Go2StandUp）。开始训练前必须调用，禁止瞎编任务名",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_config",
            "description": "读取cfg配置里的内容",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_config",
            "description": "精确替换配置文本，自动备份到E:\\HomunculusBackups",
            "parameters": {
                "type": "object",
                "properties": {
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"}
                },
                "required": ["old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_training",
            "description": "在新CMD窗口启动训练（自动conda激活）",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_training",
            "description": "停止训练",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "查看状态",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_checkpoints",
            "description": "检索可用的策略检查点(model.pt)，需要询问用户想要播放哪个策略，多少环境之类的，禁止自主决定",
            "parameters": {
                "type": "object",
                "properties": {"task_name": {"type": "string"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_policy",
            "description": "在新窗口可视化播放策略(checkpoint)",
            "parameters": {
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string"},
                    "num_envs": {"type": "integer", "default": 1}
                },
                "required": ["checkpoint_path"]
            }
        }
    }
]

_mcp_queue = queue_module.Queue()  # Gradio → MCP线程
_result_queue = queue_module.Queue()  # MCP线程 → Gradio
_mcp_thread = None
_session_ready = threading.Event()
# ========== 核心：保留原业务逻辑，只改输入方式 ==========
def _mcp_worker():
    """后台线程：常驻MCP连接，避免阻塞Gradio事件循环"""
    async def run_mcp():
        server = StdioServerParameters(
            command="python", 
            args=["server.py"] 
        )
        
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                _session_ready.set()
                
                # 循环处理请求
                while True:
                    try:
                        task = _mcp_queue.get(timeout=0.1)
                        if task is None:
                            break
                        
                        tool_name, args = task
                        result = await session.call_tool(tool_name, args)
                        _result_queue.put(("ok", result))
                    except queue_module.Empty:
                        continue
                    except Exception as e:
                        _result_queue.put(("error", str(e)))
    
    asyncio.run(run_mcp())

def start_mcp():
    """启动MCP后台线程"""
    global _mcp_thread
    if _mcp_thread is None or not _mcp_thread.is_alive():
        _mcp_thread = threading.Thread(target=_mcp_worker, daemon=True)
        _mcp_thread.start()
        _session_ready.wait(timeout=10)

def call_mcp_sync(tool_name, args, timeout=30):
    """同步调用MCP（Gradio主线程安全）"""
    _mcp_queue.put((tool_name, args))
    result = _result_queue.get(timeout=timeout)
    if result[0] == "error":
        raise Exception(result[1])
    return result[1]

# ========== 启动时初始化 ==========
start_mcp()

# ========== 修改后的chat函数 ==========
async def chat(message, history):
    """Gradio异步生成器"""
    
    # 构建messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        if isinstance(h, dict) and "role" in h:
            messages.append(h)
        elif isinstance(h, (list, tuple)) and len(h) >= 2:
            messages.append({"role": "user", "content": str(h[0])})
            if h[1]:
                messages.append({"role": "assistant", "content": str(h[1])})
    
    messages.append({"role": "user", "content": message})
    
    max_iterations = 10
    iteration = 0
    tool_logs = []
    
    while iteration < max_iterations:
        iteration += 1
        
        if tool_logs:
            yield "思考中...\n" + "\n".join(tool_logs)
        
        # LLM调用
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=5000
        )
        msg = response.choices[0].message
        
        if msg.tool_calls:
            call = msg.tool_calls[0]
            tool = call.function.name
            args = json.loads(call.function.arguments)
            
            tool_logs.append(f"🔧 [{iteration}] 调用: {tool}")
            yield "执行中...\n" + "\n".join(tool_logs)
            
            try:
                result = call_mcp_sync(tool, args, timeout=30)
                content = result.content[0].text
                
                if "[CONFIRM_REQUIRED]" in content:
                    import re
                    
                    # 解析Server返回的数据
                    size_match = re.search(r'size_kb=([\d.]+)', content)
                    lines_match = re.search(r'estimated_lines=(\d+)', content) or re.search(r'requested_lines=(\d+)', content)
                    
                    size_kb = float(size_match.group(1)) if size_match else 100
                    est_lines = int(lines_match.group(1)) if lines_match else int(size_kb * 1024 / 200)
                    
                    # 计算成本（deepseek-reasoner约￥2/M tokens，中文按1.5倍）
                    est_tokens = int(est_lines * 15)
                    cost_rmb = est_tokens * 0.000002 * 7.2  # 假设$2/M，汇率7.2
                    
                    confirm_msg = (
                        f"⚠️ **操作拦截**\n\n"
                        f"请求：读取全文日志（{size_kb:.1f}KB，约{est_lines}行）\n"
                        f"估算：约{est_tokens} tokens，成本约¥{cost_rmb:.4f}\n\n"
                        f"💡 更省钱的方案：\n"
                        f"• 查看最近100行：告诉我「看最后100行」\n"
                        f"• 搜索关键词：告诉我「搜reward」\n\n"
                        f"**是否继续全文读取？**\n"
                        f"回复「确认」继续，或选择上面的替代方案。"
                    )
                    
                    tool_logs.append("⛔ 已拦截大文件读取")
                    yield confirm_msg
                    
                    # 存入上下文，让LLM下次自动带confirmed=True
                    messages.append({
                        "role": "assistant",
                        "content": msg.content or f"我调用了{tool}，但被Server拦截，需要用户确认。",
                        "tool_calls": [{"id": call.id, "type": "function", "function": {"name": tool, "arguments": call.function.arguments}}]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": f"[INTERCEPTED] {content}"
                    })
                    messages.append({
                        "role": "system",
                        "content": "操作被拦截。如果用户回复「确认」「继续」或「读全文」，下次调用时务必设置confirmed=True。"
                    })
                    
                    # 跳出工具循环，让LLM生成自然语言回复（询问用户）
                    break
                
                # 正常返回
                tool_logs.append(f"📦 返回: {content[:80]}...")
                yield "处理中...\n" + "\n".join(tool_logs)
                
            except Exception as e:
                content = f"错误: {e}"
                tool_logs.append(f"❌ 失败: {e}")
            
            # 构建下一步messages（正常流程）
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [{"id": call.id, "type": "function", "function": {"name": tool, "arguments": call.function.arguments}}]
            })
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
            
            # 一步一反思
            if iteration < max_iterations - 1:
                messages.append({
                    "role": "system",
                    "content": f"🔴 检查点：工具'{tool}'已执行。总结获得的信息，判断是否解决了用户需求，决定是否继续调用工具。绝对禁止无脑连续调用。"
                })
        else:
            # 最终回复
            yield msg.content or ""
            break
    
    if iteration >= max_iterations:
        yield "⚠️ 达到最大迭代次数"

# ========== Gradio界面 ==========
with gr.Blocks(title="PCE Mobile") as demo:
    gr.Markdown("PCE数据矿机测试")
    
    chat_interface = gr.ChatInterface(
        fn=chat,
        chatbot=gr.Chatbot(height=500),
        textbox=gr.Textbox(
            placeholder="输入指令（如：启动训练 / 查看最新日志）...", 
            container=False,
            scale=7
        ),
        submit_btn=gr.Button("发送", variant="primary", scale=1),
        examples=[
            "查看当前任务信息",
            "启动训练 --num_envs 64",
            "查看最新日志",
            "列出所有策略,选最新的播放",
            "我想聊天"
        ],
        title="你可以用手机控制IsaacLab",
        description="解决一些蛋疼的问题,可更换模型"
    )

demo.launch(server_name="0.0.0.0", server_port=7860)