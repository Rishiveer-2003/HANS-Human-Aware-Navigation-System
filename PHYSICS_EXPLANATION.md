# Physics Mathematics Behind HANSNavEnv

## Overview

The HANS navigation environment simulates a **differential-drive mobile robot** (like TurtleBot3) in a 2D continuous space using a **unicycle kinematic model**.

---

## 1. Robot State Representation

The robot state is represented as:

$$\mathbf{s} = [x, y, \theta]^T$$

Where:
- **$x, y$**: Robot's (x, y) position in the world (continuous, meters)
- **$\theta$**: Robot's heading angle (orientation) in radians, normalized to $[-\pi, +\pi]$

**Key Convention:**
- $\theta = 0$ means the robot faces in the **+X direction**
- $\theta = \pi/2$ means the robot faces in the **+Y direction**
- Angles increase **counter-clockwise** (standard right-hand rule)

---

## 2. Control Inputs (Action Space)

The agent receives a continuous 2D action vector:

$$\mathbf{a} = [v_{\text{lin}}, v_{\text{ang}}]^T$$

Where:
- **$v_{\text{lin}} \in [0.0, 0.22]$**: Linear (forward) velocity in m/s
  - Clipped to forward motion only (no backward motion allowed)
  - Maximum 0.22 m/s matches TurtleBot3 specifications
  - Value 0 = stationary, 0.22 = full forward speed
  
- **$v_{\text{ang}} \in [-2.84, +2.84]$**: Angular velocity in rad/s
  - Negative values = turn right (clockwise)
  - Positive values = turn left (counter-clockwise)  
  - Maximum ±2.84 rad/s matches TurtleBot3 specifications

---

## 3. Kinematic Update (Step Function Physics)

At each timestep $k$, the robot state updates using the **unicycle (bicycle) model**:

$$\theta_{k+1} = \theta_k + v_{\text{ang}} \cdot \Delta t$$

$$x_{k+1} = x_k + v_{\text{lin}} \cdot \cos(\theta_{k+1}) \cdot \Delta t$$

$$y_{k+1} = y_k + v_{\text{lin}} \cdot \sin(\theta_{k+1}) \cdot \Delta t$$

Where $\Delta t = 0.1$ seconds is the simulation timestep.

### Intuitive Explanation

1. **Heading update first:** The robot's orientation changes by rotating with angular velocity for time $\Delta t$
2. **Direction vector:** Once the new heading is computed, we get the unit vector pointing in that direction:
   $$\mathbf{\hat{d}} = [\cos(\theta_{k+1}), \sin(\theta_{k+1})]$$
3. **Position update:** The robot moves forward along this direction:
   $$\Delta \mathbf{p} = v_{\text{lin}} \cdot \mathbf{\hat{d}} \cdot \Delta t$$

### Why This Model?

This is the standard **non-holonomic kinematic model** for differential-drive robots:
- The robot can **only move in the direction it's facing** (no sideways sliding)
- Turning and forward motion can happen independently
- Matches real robot physics of TurtleBot3 and similar platforms

---

## 4. Observation Space (State Perception)

The agent observes a simplified 12-dimensional vector:

$$\mathbf{o} = [d_{\text{goal}}, \alpha_{\text{goal}}, r_0, r_1, \ldots, r_{n-1}]^T$$

### Components

#### 4.1 Distance to Goal
$$d_{\text{goal}} = \|\mathbf{p}_{\text{goal}} - \mathbf{p}_{\text{robot}}\| = \sqrt{(x_g - x_r)^2 + (y_g - y_r)^2}$$

- **Euclidean distance** from robot position to goal position
- Range: $[0, \text{grid\_size} \cdot \sqrt{2}]$ (diagonal of the world)
- For grid_size=10: range is $[0, 14.14]$ meters

#### 4.2 Relative Heading Angle
$$\alpha_{\text{goal}} = \text{atan2}(y_g - y_r, x_g - x_r) - \theta_r$$

Normalized to $[-\pi, +\pi]$:

- **Positive angle**: Goal is to the left of robot heading
- **Negative angle**: Goal is to the right of robot heading
- **Zero**: Goal is directly ahead
- **±π**: Goal is directly behind

This is the **robot-relative** angle, not the global angle.

#### 4.3 Simplified LiDAR Measurements
$$\mathbf{r} = [r_0, r_1, \ldots, r_{n-1}]^T$$

Each element $r_i$ is a **raycast distance measurement** representing obstacle proximity:

$$r_i = \min_{o \in \text{obstacles}} \text{raycast}(\text{ray}_i, o)$$

**Raycast algorithm for sector $i$:**

1. **Ray direction** (in robot's local frame, converted to world):
   $$\text{ray\_angle}_i = \theta_r + \left(i - \frac{n}{2}\right) \cdot \frac{\pi}{n}$$
   
2. **Ray direction vector**:
   $$\mathbf{\hat{r}}_i = [\cos(\text{ray\_angle}_i), \sin(\text{ray\_angle}_i)]$$

3. **For each obstacle** $o$ at position $\mathbf{p}_o$:
   - **Vector from robot to obstacle**: $\mathbf{v} = \mathbf{p}_o - \mathbf{p}_r$
   - **Projection onto ray**: $\text{proj} = \mathbf{v} \cdot \mathbf{\hat{r}}_i$ (distance along ray)
   - **Perpendicular distance**: $\text{perp} = \|\mathbf{v} - \text{proj} \cdot \mathbf{\hat{r}}_i\|$
   - **If obstacle is detected** ($\text{perp} < 0.6$ units):
     $$r_i = \min(r_i, \text{proj})$$

4. **Final clamping**: $r_i \in [0, \text{grid\_size}]$

**What does this mean?**
- Each LiDAR beam scans outward from the robot
- If an obstacle is nearby (within collision radius), we report distance to it
- If no obstacles nearby, report max_range (grid_size)
- 10 beams distributed 180° around the robot (every 18°)

---

## 5. Collision Detection

A collision occurs when the robot's center gets too close to an obstacle:

$$\text{collision} = \exists \, o \in \text{obstacles} : \|\mathbf{p}_{\text{robot}} - \mathbf{p}_o\| < r_{\text{collision}}$$

Where $r_{\text{collision}} = 0.5$ meters (effective collision radius).

**In code:**
```python
for obstacle in obstacles:
    if np.linalg.norm(obstacle - robot_pos) < 0.5:
        collision = True
```

---

## 6. Reward Function (Learning Signal)

The reward signal guides the PPO agent to learn good navigation behavior:

$$R_t = R_{\text{base}} + R_{\text{progress}} + R_{\text{goal}} + R_{\text{collision}}$$

### Components

| Component | Formula | Value | Purpose |
|-----------|---------|-------|---------|
| **Base penalty** | $-1$ per step | $-1.0$ | Encourages speed/efficiency |
| **Progress reward** | $+10 \times \Delta d$ | $[0, \infty)$ | Dense reward for moving closer |
| **Goal success** | $+100$ (terminal) | $+100.0$ | Sparse reward for reaching goal |
| **Collision penalty** | $-100$ (terminal) | $-100.0$ | Large penalty for hitting obstacle |

### Intuitions

- **Small time cost (-1)**: Forces the robot to find routes quickly, not just any safe route
- **Progress reward (+10×distance_decrease)**: Acts as a "shaping" signal that smooths learning
  - Each meter closer to goal = +10 reward
  - Encourages steady progress toward goal
- **Terminal rewards (±100)**: Sparse signals for success/failure
  - Large enough to override accumulated step penalties

---

## 7. Angle Wrapping

Angles are always normalized to $[-\pi, +\pi]$ using:

$$\text{wrapped}(\alpha) = (\alpha + \pi) \mod (2\pi) - \pi$$

This ensures:
- Angular differences never exceed 180°
- Smooth learning (no discontinuity at $\pi / -\pi$ boundary)
- Prevents numerical issues in trigonometric computations

---

## 8. Boundary Constraints

The robot is confined to a square world:

$$\mathbf{p}_{\text{robot}} \in [0, \text{grid\_size}]^2$$

Position after each step is clipped:
$$x_{k+1} = \text{clip}(x'_{k+1}, 0, \text{grid\_size})$$
$$y_{k+1} = \text{clip}(y'_{k+1}, 0, \text{grid\_size})$$

This prevents the robot from escaping the world boundaries.

---

## Summary: Physics Timeline per Step

```
Input: action = [v_lin, v_ang]
  ↓
1. Clip velocities to valid ranges
2. Update heading:        θ ← θ + v_ang × 0.1
3. Wrap angle to [-π, π]
4. Compute direction:     d = [cos(θ), sin(θ)]
5. Update position:       p ← p + d × v_lin × 0.1
6. Clip position to world bounds
7. Compute observation:   o = [distance, angle, lidar_distances]
8. Compute reward based on progress/collision/goal
9. Check termination conditions
  ↓
Output: (observation, reward, done, truncated, info)
```

---

## References

- **Unicycle Model**: Standard in mobile robotics (Siegwart & Nourbakhsh, 2004)
- **LiDAR Raycasting**: Used in robotics simulators like Gazebo
- **Gymnasium API**: OpenAI Gym-compatible environment (https://gymnasium.farama.org/)
