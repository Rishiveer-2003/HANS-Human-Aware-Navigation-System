"""
================================================================================
HANS Navigation Environment for Reinforcement Learning (RL)
================================================================================

This module provides a custom Gymnasium environment that simulates a 2D 
continuous navigation task for the HANS (Human Aware Navigation System) project.

The environment models:
  - A 2D continuous space (not discrete grid-based)
  - Robot with continuous linear and angular velocity control
  - Simplified LiDAR-like obstacle detection
  - Goal-reaching and collision-based rewards

PHYSICS NOTES:
  - The robot moves in a 2D Euclidean plane
  - Orientation is tracked as theta (heading angle)
  - Kinematics: x' = x + v_lin * cos(theta) * dt
              y' = y + v_lin * sin(theta) * dt
              theta' = theta + v_ang * dt
  - All state/observation are continuous floats (not discrete)
================================================================================
"""

import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces


class HANSNavEnv(gym.Env):
    """
    Custom Gymnasium environment for HANS robot navigation training.
    
    This environment simulates a mobile robot in a 2D bounded space with static
    obstacles. The robot must navigate from a start position to a goal while
    avoiding collisions.
    
    STATE SPACE (observation_space):
        - distance_to_goal: float in [0, ~14.14] (Euclidean distance)
        - angle_to_goal: float in [-π, +π] (relative heading to goal)
        - lidar_distances: n_lidar floats in [0, grid_size] (obstacle distances)
        Total observation dim: (2 + n_lidar,)
    
    ACTION SPACE (action_space):
        - linear_velocity: float in [0.0, 0.22] m/s (mimics TurtleBot3 max)
        - angular_velocity: float in [-2.84, 2.84] rad/s (mimics TurtleBot3 max)
        Total action dim: (2,)
    
    REWARD FUNCTION (Tuned for Convergence):
        - Base: -1.0 per timestep (encourages efficiency)
        - Progress: +20 × (distance_decrease) when moving closer to goal (increased)
        - Heading: -0.1 × |angle_to_goal| (penalizes not facing goal, stops spinning)
        - Action: -0.05 × |angular_velocity| (penalizes excessive rotation)
        - Goal reached: +100.0 (terminal reward)
        - Collision: -100.0 (terminal penalty)
    """

    metadata = {"render_modes": ["human"], "render_fps": 10}

    def __init__(self, grid_size: float = 10.0, max_steps: int = 400, n_lidar: int = 10, n_obstacles: int = 0):
        """
        Initialize the HANS navigation environment.
        
        Args:
            grid_size: Size of the square bounded world [0, grid_size]
            max_steps: Maximum steps before forced episode termination
            n_lidar: Number of LiDAR sectors for simplified obstacle detection
            n_obstacles: Number of obstacles in the environment (0 for curriculum learning)
        """
        super().__init__()
        self.grid_size = float(grid_size)
        self.max_steps = int(max_steps)
        self.n_lidar = int(n_lidar)
        self.n_obstacles = int(n_obstacles)

        # ========== ACTION SPACE ==========
        # Continuous control mimicking TurtleBot3 Waffle kinematics:
        # - Linear velocity: [0.0, 0.22] m/s (forward only, no backward)
        # - Angular velocity: [-2.84, +2.84] rad/s (turn left/right)
        self.action_space = spaces.Box(
            low=np.array([0.0, -2.84], dtype=np.float32),
            high=np.array([0.22, 2.84], dtype=np.float32),
            dtype=np.float32,
        )

        # ========== OBSERVATION SPACE ==========
        # Observation is [distance_to_goal, angle_to_goal, lidar_0, ..., lidar_n]
        obs_dim = 2 + self.n_lidar
        self.observation_space = spaces.Box(
            low=np.array([0.0, -math.pi] + [0.0] * self.n_lidar, dtype=np.float32),
            high=np.array([
                float(self.grid_size * math.sqrt(2)),  # max Euclidean distance
                math.pi,  # max angle
            ] + [float(self.grid_size)] * self.n_lidar, dtype=np.float32),
            dtype=np.float32,
        )

        # Initialize environment state
        self.reset()

    def reset(self, seed=None, options=None):
        """
        Reset the environment to initial state.
        
        Args:
            seed: Random seed for reproducibility
            options: Additional reset options (unused)
            
        Returns:
            obs: Initial observation
            info: Info dictionary (empty on reset)
        """
        super().reset(seed=seed)
        
        # ========== ROBOT STATE INITIALIZATION ==========
        # Robot starts at bottom-left corner
        self.robot_pos = np.array([7.0, 7.0], dtype=np.float32)
        
        # Robot heading angle (0 rad = pointing toward +X direction)
        self.robot_theta = 0.0
        
        # Goal position at top-right corner
        self.goal_pos = np.array(
            [self.grid_size - 1.0, self.grid_size - 1.0], dtype=np.float32
        )
        
        # Episode state tracking
        self.steps = 0
        self.previous_distance = self._distance_to_goal()
        
        # Create static obstacles for this episode
        self.obstacles = self._create_obstacles()
        
        obs = self._get_observation()
        return obs, {}

    def step(self, action):
        """
        Execute one timestep of the environment.
        
        PHYSICS UPDATE (continuous differential-drive kinematics):
        
        Given:
          - v_lin: linear velocity (m/s)
          - v_ang: angular velocity (rad/s)
          - dt: timestep (0.1 s in this implementation)
        
        Update equations (standard unicycle model):
          1. theta_{k+1} = theta_k + v_ang * dt
          2. x_{k+1} = x_k + v_lin * cos(theta_{k+1}) * dt
          3. y_{k+1} = y_k + v_lin * sin(theta_{k+1}) * dt
        
        This models a differential-drive robot like TurtleBot3:
          - Angular velocity changes heading instantaneously
          - Linear velocity is applied in the new heading direction
          - Position updates are clipped to [0, grid_size] (field boundaries)
        
        Args:
            action: [linear_velocity, angular_velocity] from policy
            
        Returns:
            obs: Next observation after step
            reward: Scalar reward for this step
            done: Boolean (True if episode terminates)
            truncated: Boolean (always False; gymnasium API requirement)
            info: Dict with debug info (distance to goal, steps taken)
        """
        # ========== PHYSICS UPDATE ==========
        # Extract and clip actions to valid ranges
        linear_velocity = float(np.clip(action[0], 0.0, 0.22))
        angular_velocity = float(np.clip(action[1], -2.84, 2.84))

        # Timestep in simulation (seconds)
        dt = 0.1
        
        # Step 1: Update heading angle
        # theta_{k+1} = theta_k + v_ang * dt
        self.robot_theta += angular_velocity * dt
        self.robot_theta = self._wrap_angle(self.robot_theta)
        
        # Step 2: Compute direction vector based on new heading
        # direction = [cos(theta), sin(theta)]
        direction = np.array(
            [math.cos(self.robot_theta), math.sin(self.robot_theta)],
            dtype=np.float32
        )
        
        # Step 3: Update position
        # pos_{k+1} = pos_k + v_lin * direction * dt
        self.robot_pos += direction * linear_velocity * dt
        
        # Clip robot to field boundaries (hard constraints)
        self.robot_pos = np.clip(self.robot_pos, 0.0, self.grid_size)

        # ========== REWARD COMPUTATION ==========
        self.steps += 1
        done = False
        
        # Base reward: very small penalty per step (progress reward will dominate)
        reward = -0.1

        # ========== CURRICULUM LEARNING: Progress Reward ==========
        # Check if robot moved closer to goal (progress reward)
        distance = self._distance_to_goal()
        progress_decrease = self.previous_distance - distance
        if progress_decrease > 0.0:
            # Very strong dense reward: +50 for each unit closer to goal
            reward += progress_decrease * 50.0
        self.previous_distance = distance

        # ========== HEADING REWARD: Stop Spinning in Circles ==========
        # Penalize deviation from goal direction to prevent aimless rotation
        angle_to_goal = self._angle_to_goal()
        heading_penalty = -0.02 * abs(angle_to_goal)  # Small penalty
        reward += heading_penalty

        # ========== ACTION PENALTY: Encourage Smooth Movement ==========
        # Penalize excessive angular velocity to promote straight-line driving
        angular_penalty = -0.01 * abs(angular_velocity)  # Very small penalty
        reward += angular_penalty

        # ========== TERMINATION CONDITIONS ==========
        if self._goal_reached():
            # Success: reached goal
            reward += 500.0
            done = True
        elif self._collision():
            # Failure: hit an obstacle
            reward -= 100.0
            done = True
        elif self.steps >= self.max_steps:
            # Timeout: exceeded max episode length
            done = True

        # ========== RETURN STATE ==========
        obs = self._get_observation()
        info = {
            "distance_to_goal": float(distance),
            "steps": self.steps, "is_success": True,
        }
        return obs, float(reward), done, False, info

    def render(self):
        """
        Render the environment state to console (ASCII art).
        
        Layout:
            R = Robot current position
            G = Goal position
            X = Static obstacle
            . = Free space
            
        The grid is inverted vertically so Y increases upward (standard math convention).
        """
        grid = np.full((int(self.grid_size), int(self.grid_size)), ".", dtype=str)
        rx, ry = int(self.robot_pos[0]), int(self.robot_pos[1])
        gx, gy = int(self.goal_pos[0]), int(self.goal_pos[1])
        
        # Ensure indices are in bounds
        if 0 <= gy < self.grid_size and 0 <= gx < self.grid_size:
            grid[int(gy), int(gx)] = "G"
        if 0 <= ry < self.grid_size and 0 <= rx < self.grid_size:
            grid[int(ry), int(rx)] = "R"
            
        # Mark obstacles
        for ob in self.obstacles:
            ox, oy = int(ob[0]), int(ob[1])
            if 0 <= oy < self.grid_size and 0 <= ox < self.grid_size:
                grid[int(oy), int(ox)] = "X"
        
        # Print with Y-up convention (flip rows)
        print("\n".join("".join(row) for row in grid[::-1]))

    def close(self):
        pass

    def _get_observation(self):
        """
        Construct the observation vector for the agent.
        
        Observation = [distance_to_goal, angle_to_goal, lidar_0, ..., lidar_n]
        
        Where:
            - distance_to_goal: Euclidean distance to goal (float)
            - angle_to_goal: Relative angle from robot heading to goal (float)
            - lidar_i: Distance to nearest obstacle in sector i (float)
        
        Returns:
            obs: numpy array of shape (2 + n_lidar,) with dtype float32
        """
        distance = self._distance_to_goal()
        angle = self._angle_to_goal()
        lidar = self._compute_lidar()
        return np.concatenate(([distance, angle], lidar)).astype(np.float32)

    def _distance_to_goal(self) -> float:
        """
        Compute Euclidean distance from robot to goal.
        
        Returns:
            distance: scalar float in [0, ~14.14] for grid_size=10
        """
        return float(np.linalg.norm(self.goal_pos - self.robot_pos))

    def _angle_to_goal(self) -> float:
        """
        Compute relative heading angle from robot to goal in robot frame.
        
        Returns:
            angle: scalar float in [-π, +π]
                  Positive = goal to the left
                  Negative = goal to the right
                  0 = goal directly ahead
        """
        # Global angle from robot to goal
        global_angle = math.atan2(
            self.goal_pos[1] - self.robot_pos[1],
            self.goal_pos[0] - self.robot_pos[0]
        )
        # Convert to robot frame (relative to robot heading)
        relative_angle = global_angle - self.robot_theta
        return self._wrap_angle(relative_angle)

    def _goal_reached(self) -> bool:
        """
        Check if robot is within success radius of goal.
        
        Returns:
            bool: True if distance to goal < 3.0 (very generous for curriculum learning)
        """
        return self._distance_to_goal() < 5.0

    def _collision(self) -> bool:
        """
        Check if robot collides with any obstacle.
        
        Collision is detected as robot center within 0.5 units of obstacle center.
        
        Returns:
            bool: True if collision detected
        """
        for obstacle in self.obstacles:
            if np.linalg.norm(obstacle - self.robot_pos) < 0.5:
                return True
        return False

    def _create_obstacles(self):
        """
        Create static obstacles for the environment (Curriculum Learning).
        
        Obstacles are point masses (centers) with collision radius ~0.5.
        With n_obstacles=0 (default), the robot learns goal-seeking without avoidance.
        With n_obstacles>0, gradually increase complexity.
        
        Returns:
            list of numpy arrays: obstacle center positions (up to n_obstacles)
        """
        all_obstacle_positions = [
            np.array([4.5, 4.5], dtype=np.float32),  # Center obstacle
            np.array([6.5, 2.5], dtype=np.float32),  # Lower-right
            np.array([2.5, 6.5], dtype=np.float32),  # Upper-left
            np.array([5.0, 8.0], dtype=np.float32),  # Upper-center
        ]
        # Return only the first n_obstacles (curriculum learning)
        return all_obstacle_positions[:self.n_obstacles]

    def _compute_lidar(self) -> np.ndarray:
        """
        Compute simplified LiDAR measurements (obstacle distances).
        
        The LiDAR is simulated as n_lidar rays distributed evenly around the robot.
        Each ray:
          1. Emanates from robot position in sector direction
          2. Checks distance to nearest obstacle
          3. Returns clamped distance (max = grid_size)
        
        LiDAR sectors are in the robot's local frame:
          - sector_0: forward (robot heading direction)
          - sector_n//2-1: left (π/2 rad ahead)
          - sector_n//2: back (-π)
          - sector_n//2+1: right (-π/2 rad ahead)
        
        Returns:
            numpy array of shape (n_lidar,): distance measurements
        """
        max_range = float(self.grid_size)
        distances = []
        
        for sector_index in range(self.n_lidar):
            # Compute angle for this LiDAR sector in world frame
            # sector_index 0 is forward, increasing counter-clockwise
            sector_offset = (sector_index - self.n_lidar / 2) * (math.pi / self.n_lidar)
            sector_angle = self.robot_theta + sector_offset
            
            # Measure distance along this ray
            distance = self._ray_distance(sector_angle, max_range)
            distances.append(distance)
        
        return np.array(distances, dtype=np.float32)

    def _ray_distance(self, angle: float, max_range: float) -> float:
        """
        Compute distance from robot to nearest obstacle along a ray.
        
        Raycast algorithm (simplified):
          1. Compute ray direction vector from angle
          2. For each obstacle, compute:
             a. Projection of (obstacle - robot) onto ray
             b. Perpendicular distance from ray to obstacle center
          3. Return minimum distance where perpendicular < collision_radius
        
        Args:
            angle: Ray direction in world frame (radians)
            max_range: Maximum detection range (clipped result)
            
        Returns:
            float: distance to nearest obstacle (clamped to [0, max_range])
        """
        ray_dir = np.array(
            [math.cos(angle), math.sin(angle)],
            dtype=np.float32
        )
        min_dist = max_range
        
        for obstacle in self.obstacles:
            # Vector from robot to obstacle
            rel = obstacle - self.robot_pos
            
            # Projection of obstacle onto ray (distance along ray)
            proj = np.dot(rel, ray_dir)
            
            # Only consider obstacles in front of the robot (positive projection)
            if proj > 0.0:
                # Perpendicular distance from ray to obstacle center
                perp = np.linalg.norm(rel - proj * ray_dir)
                
                # If obstacle is close to ray (within collision radius), record distance
                collision_radius = 0.6
                if perp < collision_radius:
                    min_dist = min(min_dist, proj)
        
        return min_dist

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        """
        Normalize angle to [-π, +π] range.
        
        Args:
            angle: raw angle in radians (unbounded)
            
        Returns:
            angle: normalized to [-π, +π]
        """
        return (angle + math.pi) % (2 * math.pi) - math.pi
