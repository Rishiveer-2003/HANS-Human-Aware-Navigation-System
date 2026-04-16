# ⚡ HANS RL Quick Reference

## Installation (First Time Only)

```bash
cd /home/vboxuser/HANS
pip install -r requirements.txt
```

---

## 🎮 Training Commands

| Task | Command | Time |
|------|---------|------|
| **Train** (100k steps) | `python hans_rl/train.py` | 5-10 min |
| **Train** (custom steps) | `python hans_rl/train.py --timesteps 50000` | ~2-5 min |
| **Save to custom path** | `python hans_rl/train.py --model my_model.zip` | 5-10 min |

**Output:**
- Console logs with progress bar
- Checkpoints: `models/hans_ppo_*.zip` (every 20k steps)
- Final model: `models/hans_ppo.zip`

---

## 🧪 Evaluation Commands

| Task | Command | Output |
|------|---------|--------|
| **Evaluate default** | `python hans_rl/train.py --eval` | 5 episodes |
| **Evaluate extended** | `python hans_rl/train.py --eval --episodes 20` | 20 episodes |
| **Evaluate checkpoint** | `python hans_rl/train.py --eval --model models/hans_ppo_40000_steps.zip` | 5 episodes |

**Output Metrics:**
- ✓ Goal: Reached goal successfully
- Timeout: Exceeded 200 steps
- Reward: Sum of episode rewards
- Success rate: Percentage of successful episodes

---

## 📊 Performance Metrics

**Good Training Indicators:**
- Episode reward increases over time (learning curve)
- Success rate → 70-80%+
- Average steps to goal decreases

**Checkpoints to Compare:**
```
models/hans_ppo_20000_steps.zip   (early training)
models/hans_ppo_40000_steps.zip   (mid training)
models/hans_ppo_60000_steps.zip   (late training)
models/hans_ppo_80000_steps.zip   (near convergence)
models/hans_ppo.zip                (final model)
```

---

## 🧠 Key Hyperparameters

| Parameter | Value | Can Change? |
|-----------|-------|-------------|
| Grid size | 10×10 m | `HANSNavEnv(grid_size=20)` |
| Max steps | 200 per episode | `HANSNavEnv(max_steps=300)` |
| LiDAR sectors | 10 rays | `HANSNavEnv(n_lidar=20)` |
| Learning rate | 3e-4 | In `train()` function |
| PPO timesteps | 100k | CLI `--timesteps` arg |

---

## 📐 Physics Formula Cheat Sheet

**Kinematics (differential drive):**

$$\theta_{t+1} = \theta_t + v_{ang} \cdot 0.1$$
$$x_{t+1} = x_t + v_{lin} \cdot \cos(\theta_{t+1}) \cdot 0.1$$
$$y_{t+1} = y_t + v_{lin} \cdot \sin(\theta_{t+1}) \cdot 0.1$$

**Observation (12 values):**
- `[0]` = distance to goal (Euclidean)
- `[1]` = angle to goal (robot frame)
- `[2:12]` = LiDAR distances (10 sectors)

**Reward per step:**
$$R = -1 + 10 \cdot \Delta d + R_{goal} + R_{collision}$$

---

## 📁 File Organization

```
hans_rl/envs.py
  ├─ HANSNavEnv class
  ├─ __init__()        → Setup action/observation spaces
  ├─ reset()           → Initialize robot at (1, 1), goal at (9, 9)
  ├─ step(action)      → Physics update + reward computation
  └─ render()          → Print ASCII visualization

hans_rl/train.py
  ├─ train()           → Initialize env, PPO, train for N steps
  ├─ evaluate()        → Load model, run episodes, print stats
  └─ if __name__ == "__main__":  → CLI argument parsing

PHYSICS_EXPLANATION.md
  → Full derivations and intuitions (20+ pages)

HANS_AIML_Report.md
  → Mentor-facing technical report (dataset, model, results)
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: gymnasium` | Run `pip install -r requirements.txt` |
| `ModuleNotFoundError: stable_baselines3` | Run `pip install stable-baselines3[extra]` |
| Training is slow | Use fewer timesteps: `--timesteps 10000` |
| Model not learning (reward → -100) | Check reward function or increase progress reward in `envs.py` |
| No checkpoints saved | Ensure `models/` directory exists |
| Permission denied on model save | Use `chmod u+w models/` or save to different path |

---

## 🚀 Typical Workflow

```bash
# 1. Install (one-time)
pip install -r requirements.txt

# 2. Train for a quick test (10k steps)
python hans_rl/train.py --timesteps 10000

# 3. Evaluate the checkpoint
python hans_rl/train.py --eval --model models/hans_ppo_10000_steps.zip --episodes 5

# 4. If good performance → Train full model
python hans_rl/train.py --timesteps 100000

# 5. Evaluate full model
python hans_rl/train.py --eval --episodes 20

# 6. Export model info
# (Model saved as models/hans_ppo.zip for ROS2 integration later)
```

---

## 📋 Debugging: Print Robot State

Modify `hans_rl/envs.py` → `step()` function, add:

```python
# Add after physics update
print(f"Robot pos: {self.robot_pos}, heading: {self.robot_theta:.2f} rad")
print(f"Observation: {obs}")
print(f"Reward: {reward:.2f}")
```

Then run training to see per-step diagnostics.

---

## 🎯 Next Phase: ROS2 Integration

1. Load model: `model = PPO.load("models/hans_ppo.zip")`
2. Subscribe to ROS topics: `/scan`, `/odom`
3. Convert ROS data → observation vector (same 12 values)
4. Call: `action, _ = model.predict(obs, deterministic=True)`
5. Publish action → `/cmd_vel`

See `PHYSICS_EXPLANATION.md` for observation format details.
