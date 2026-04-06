# 和IsaacLab对话

> **18岁，卧室里手搓的**  
> 不用再手动调参，不用一直死盯着屏幕（你懂的），直接一句话搞定
> 躺床上也能控制训练，3天仅需¥1.5（DeepSeek API费用）

[视频演示](./lv_0_20260406231406.mp4)

---

## ⚡ 它到底能干啥

**优点：**
- **一句话开训：** "用X个环境训练Go2，跑100轮" → 自动运行（PID追踪，日志自动保存）
- **手机看监控：** 实时看训练流，不用SSH/VNC
- **AI改配置：** 聊天改 `alive=2`、`terminated=-5`，不用手动翻文件
- **话费保险：** 超过两毛钱（¥0.20）的操作自动拦截（防止LLM一下把文件全读完导致Token账单爆炸）
- **赛博陪聊：** 训练跑崩了可以问AI"咋回事？？？"，LLM会分析（有可能还有吐槽）

**现状（v0.1）：**
- LLM偶尔会"幻觉"式急着调工具（用"先确认"机制缓解了）
- Windows路径处理：90%自动，10%需手动（如果你的IsaacLab安装位置很奇葩）
- 仅在Go2和我的自定义环境配置文件上测试过；其他机器人/环境等待社区验证

**底线：** 它不代替你思考，它代替你每天敲100次`python scripts/...`和"还在训吗？"的焦虑。

---

## 🚀 运行（5分钟搞定）

**1. 改5行配置**

`server.py`（文件顶部）：

```python
ISAACLAB_ROOT = Path(r"X:\IsaacLab")           # ← 你的IsaacLab根目录
PYTHON_PATH = r"X:\conda\envs\isaaclab\python.exe"  # ← 你的conda python.exe路径
CFG_PATH = Path(r"X:\IsaacLab\...\XXX_env_cfg.py") # ← 你的任务配置文件
TASK_NAME = "Isaac-StandUp-Go2-v0"             # ← 你的任务ID
```

`client.py`（在 `CONFIG = {}` 里）：

```python
api_key = "sk-your-key-here"  # ← 从 platform.deepseek.com 获取（¥10就行）
```

2. 运行（单个窗口）

```bash
# Win+R → 输入cmd → 回车
cd X:\path\to\TalkToIsaacLab
python client.py
```

等待显示 `http://0.0.0.0:7860`。

3. 手机控制

- 电脑：Win+R → cmd → 输入`ipconfig` → 找到`IPv4`（例如 `192.168.1.5`）
- 手机：浏览器打开 `http://192.168.1.5:7860`（需同一WiFi）

搞定，躺床上训机器人吧

```
