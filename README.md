# PCE-Physical-Constraints-Engine
Continuous physical critical-state trajectories for VLA Safety Layers and JEPA Cost Modules. Auto-curating near-failure dynamics (ZMP boundary, torque limits) via IsaacLab from a bedroom lab. 

**Tooling**: IsaacLab MCP automation for continuous trajectory collection from a bedroom lab.

## Positioning (Now → Next)

**Now**: IsaacLab MCP tooling + continuous near-failure trajectory curation  
**Next**: Standard dataset for VLA Safety Filters and JEPA Cost Module training

## Why This Matters

- **V-JEPA 2 (Meta 2025)** shipped World Model but **deliberately omitted Cost Module & Actor**[^222^], leaving no "pain evaluation" capability.
- **LeCun's JEPA** requires Cost Module: Intrinsic Cost (hard-coded physics) + Trainable Critic (learned consequences from **temporal trajectories**)[^316^].
- **Current VLAs (Figure/Tesla)** dropped explicit physics layers for end-to-end speed, causing **physical hallucinations** (dragging pitchforks, torque overflows)[^255^][^261^].
- **The Gap**: VLAs can generate motion, but **someone must tell them "this hurts"** — that's the Cost Module's job.

## What We Do

Use IsaacLab as a **continuous critical-trajectory generator**, capturing **temporal dynamics from stability → boundary → failure**:

- **Instability Trajectories**: Continuous CoM projection drifting from support polygon interior → boundary → violation (ZMP-critical sequences).
- **Torque Limit Trajectories**: Joint torque evolution from safe → warning → overload over 100-200ms.
- **Contact Hazard Trajectories**: Contact force accumulation from light touch → critical threshold → structural risk.

**Data Format**: **Time-series state vectors** `[s_t0, s_t1, ..., s_tn]` (50-200 frames per trajectory) mapping to final outcome (recovered/fallen/intervened).

## Tech Stack

- **MCP Production Layer**: Automated IsaacLab pipeline for batch trajectory generation.
- **Data Schema**: Continuous state sequences with physics gradients (differentiable CoM, ZMP, torques).
- **Target**: Plug-in Cost Critic for JEPA, or real-time Safety Filter for VLAs.

## Roadmap

- [x] Phase 1: MCP tooling + continuous trajectory capture (bedroom validation)
- [ ] Phase 2: 100k+ continuous critical trajectories (locomotion, manipulation, climbing)
- [ ] Phase 3: Open-source Cost Critic weights (JEPA-compatible, VLA Safety Layer)

## Data Value

Unlike video datasets (positive-biased), we provide **"physics pain memory"**:

- **Dense negative samples**: 100k+ continuous near-failure trajectories (impossible to collect in real world due to hardware damage cost).
- **Temporal resolution**: Precise dynamics of *how* failure unfolds, not just *that* it fails.
- **Differentiable physics**: CoM, ZMP, contact forces, torques — ready for gradient-based optimization.

**Use for**:
- JEPA Trainable Critic (predicting long-term physical consequences from trajectories)
- VLA Safety Filter (real-time trend detection: "this trajectory leads to pain")
- Model-Based RL cost shaping

---

*Note: We don't replace World Models or VLAs. We provide the missing **physics pain nervous system** — teaching AI to feel hurt before it breaks.*
