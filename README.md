# PCE-Physical-Constraints-Engine
Continuous physical critical-state trajectories for VLA Safety Layers and JEPA Cost Modules. Auto-curating near-failure dynamics (ZMP boundary, torque limits) via IsaacLab from a bedroom lab. 

**Tooling**: IsaacLab MCP automation for continuous physical boundary-proximal trajectory collection.

---

## Positioning (Now → Next)

**Now**: IsaacLab MCP tooling + continuous boundary-proximal trajectory curation  
**Next**: Standard dataset for embodied AI physical constraint evaluation

---

## Why This Matters

- **End-to-end VLAs** (Figure, Tesla, etc.) removed explicit physics layers to maximize inference speed, causing dangerous failures—dragging jammed objects, torque overflows, blind-spot collisions.
- **JEPA World Models** (LeCun architecture) explicitly lack the Cost Module required to evaluate "will this action damage hardware."
- **Real-world data is prohibitively expensive**: Critical states often destroy hardware (e.g., $50k repair per humanoid fall), preventing repeatable experiments and dense negative sampling.

---

## What We Do

Use IsaacLab as a **continuous boundary-proximal trajectory generator**, capturing the complete physical evolution as systems approach and trigger constraint boundaries:

- **Support Boundary**: Center-of-Mass projection drifting from stable zone → support polygon edge → instability (e.g., pre-slip dynamics, terrain edge detection).
- **Torque Boundary**: Joint forces accumulating from safe load → warning threshold → hardware limit violation (e.g., overreach torque buildup in manipulation).
- **Contact Boundary**: Contact forces escalating from light touch → structural risk threshold → overload (e.g., pre-collision force accumulation, grip slip detection).

**Data Format**: Continuous state sequences (multi-frame records of CoM, ZMP, joint torques, contact forces, terrain properties, etc.), labeled with final constraint outcome (safe/limit exceeded/damage/intervened).

---

## Technical Stack

- **MCP Production Layer**: Automated IsaacLab pipeline for batch trajectory generation via mobile/CLI interface.
- **Data Schema**: Continuous state vectors with differentiable physics quantities (gradient-ready for model training).
- **Target Architecture**: Plug-in Cost Critic for JEPA, or real-time Safety Filter for VLA systems.

**Applicable To**:
- Humanoid dynamic balance (any terrain/posture)
- Manipulator force control (contact-rich tasks: insertion, stacking, dragging)
- Legged robot locomotion (any gait/terrain)
- **Any embodied task with physical constraint boundaries**

---

## Roadmap

- [x] Phase 1: MCP tooling + continuous trajectory collection (concept validation via single-workstation setup)
- [ ] Phase 2: Large-scale cross-scene boundary-proximal dataset (locomotion, manipulation, climbing)
- [ ] Phase 3: Open-source Physical Constraint Evaluation models (compatible with JEPA Cost Modules and VLA Safety Layers)

---

## Data Value

Unlike generic video datasets (positive-biased), we provide **"boundary exploration records"**:

- **Dense boundary-proximal states**: Continuous trajectories capturing the approach toward—but not yet fully triggering—hardware damage (impossible to collect in real world due to equipment destruction cost).
- **Temporal Evolution**: Records *how* physical parameters evolve toward boundaries, not just binary boundary triggers.
- **Differentiable Physics**: CoM, ZMP, contact force vectors, joint torques, accelerations—ready for gradient-based optimization and neural network training.

**Used For**:
- Training JEPA Trainable Critics (predicting long-term physical consequences from state trajectories)
- VLA Safety Filters (real-time detection of boundary-approaching trends before damage occurs)
- Model-Based RL constraint shaping (physics-guided policy optimization)

---

*Note: This project does not replace World Models or VLAs. It provides the missing **Physical Constraint Evaluation Layer**—enabling embodied AI to recognize dangerous states before hardware damage occurs.*
