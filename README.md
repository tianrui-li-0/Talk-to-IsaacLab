# Talk to IsaacLab

> **18yo-built in a bedroom.**  
> No more manual tuning or **staring at screens** (you know what I mean). Just talk.
> Control training from your bed. ¥1.5/3days (DeepSeek API cost).

[Watch Demo](./lv_0_20260406231406.mp4)


---

## ⚡ What it actually does

**The good:**
- **One-liner training:** "Train Go2 with 8 envs, stop at 1000 iter" → it runs (PID tracked, logs saved)
- **Phone-side monitoring:** Real-time training stream without SSH/VNC
- **AI cfg editor:** Change `alive=2` → `terminated=-5` via chat, not manual
- **Cost circuit-breaker:** Blocks >¥0.20 ops (prevents token-cost shock from full log reads)
- **Cyber Therapy:** When training crashes, ask "wtf happened?" — AI analyzes logs + maybe roasts your code.

**The messy (v0.1):**
- LLM occasionally "hallucinates" tool urgency (mitigated with confirm-first gates)
- Windows path handling: 90% auto, 10% manual if your IsaacLab is non-standard
- Go2-tested only; other robots/envs pending community validation

**Bottom line:** It doesn't replace your brain. It replaces your 100 daily `python scripts/...` keystrokes and the anxiety of "is it still training?"

---

## 🚀 Run (less than 5 minutes)

**1. Edit 5 lines**

`server.py` (top of file):

```python
ISAACLAB_ROOT = Path(r"X:\IsaacLab")           # ← Your IsaacLab root
PYTHON_PATH = r"X:\conda\envs\isaaclab\python.exe"  # ← Your conda python.exe
CFG_PATH = Path(r"X:\IsaacLab\...\XXX_env_cfg.py") # ← Your task config file
TASK_NAME = "Isaac-StandUp-Go2-v0"             # ← Your task ID
```

`client.py` (in `CONFIG = {}`):

```python
api_key = "sk-your-key-here"  # ← Get from platform.deepseek.com (¥10)
```

2. Run (single window)

```bash
# Win+R → cmd → Enter
cd X:\path\to\TalkToIsaacLab
python client.py
```

Wait for `http://0.0.0.0:7860`.

3. Phone control

- PC: Win+R → cmd → `ipconfig` → find `IPv4` (e.g., `192.168.1.5`)
- Phone: Browser → `http://192.168.1.5:7860` (same WiFi required)

Done. Train robots from your bed.
