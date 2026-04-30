#!/usr/bin/env python3
"""
HANS RL Node - Loads trained model and publishes commands to robot
Subscribes to sensor data from Unity, runs RL inference, publishes cmd_vel
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32MultiArray
import numpy as np
from stable_baselines3 import PPO
import os
import sys

class HANSRLNode(Node):
    def __init__(self):
        super().__init__('hans_rl_node')
        
        self.get_logger().info("=" * 60)
        self.get_logger().info("HANS RL ROS2 Node Starting...")
        self.get_logger().info("=" * 60)
        
        # Load trained model
        model_path = "/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip"
        if not os.path.exists(model_path):
            self.get_logger().error(f"❌ Model not found: {model_path}")
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        try:
            self.model = PPO.load(model_path)
            self.get_logger().info(f"✓ Model loaded: {model_path}")
        except Exception as e:
            self.get_logger().error(f"❌ Failed to load model: {str(e)}")
            raise
        
        # Subscribers
        self.pose_sub = self.create_subscription(
            PoseStamped, '/robot/pose', self.pose_callback, 10)
        self.get_logger().info("✓ Subscribed to /robot/pose")
        
        self.lidar_sub = self.create_subscription(
            LaserScan, '/robot/scan', self.lidar_callback, 10)
        self.get_logger().info("✓ Subscribed to /robot/scan")
        
        self.sensor_sub = self.create_subscription(
            Float32MultiArray, '/robot/sensors', self.sensor_callback, 10)
        self.get_logger().info("✓ Subscribed to /robot/sensors")
        
        # Publisher
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info("✓ Publishing to /cmd_vel")
        
        # State buffer
        self.current_pose = None
        self.current_lidar = None
        self.current_sensors = None
        self.goal_pose = np.array([9.0, 9.0])
        self.last_action = None
        
        # Statistics
        self.step_count = 0
        self.total_actions = 0
        
        # Timer for RL inference (20 Hz)
        self.timer = self.create_timer(0.05, self.inference_step)
        self.get_logger().info("✓ Inference timer: 20 Hz (50ms)")
        
        self.get_logger().info("=" * 60)
        self.get_logger().info("✓ HANS RL Node READY!")
        self.get_logger().info("Waiting for sensor data from Unity...")
        self.get_logger().info("=" * 60)
    
    def pose_callback(self, msg):
        """Update robot pose from Unity"""
        self.current_pose = np.array([
            msg.pose.position.x,
            msg.pose.position.y
        ])
    
    def lidar_callback(self, msg):
        """Update LiDAR data - reduce to 10 sectors"""
        ranges = np.array(msg.ranges)
        
        # Handle NaN/inf values
        ranges = np.nan_to_num(ranges, nan=10.0, posinf=10.0)
        
        # Reduce 360 rays to 10 buckets
        num_buckets = 10
        bucket_size = len(ranges) // num_buckets
        lidar_buckets = []
        
        for i in range(num_buckets):
            start_idx = i * bucket_size
            end_idx = start_idx + bucket_size
            bucket_data = ranges[start_idx:end_idx]
            
            # Minimum distance in each bucket
            min_dist = np.min(bucket_data) if len(bucket_data) > 0 else 10.0
            lidar_buckets.append(float(min_dist))
        
        self.current_lidar = np.array(lidar_buckets)
    
    def sensor_callback(self, msg):
        """Receive sensor data directly from Unity (preferred)"""
        try:
            self.current_sensors = np.array(msg.data, dtype=np.float32)
        except Exception as e:
            self.get_logger().warn(f"Error parsing sensor data: {str(e)}")
    
    def inference_step(self):
        """Run RL inference and publish commands"""
        
        # Option 1: Use direct sensor message from Unity (PREFERRED)
        if self.current_sensors is not None and len(self.current_sensors) == 12:
            obs = self.current_sensors
            source = "direct"
        
        # Option 2: Compute from pose + lidar
        elif self.current_pose is not None and self.current_lidar is not None:
            distance = np.linalg.norm(self.goal_pose - self.current_pose)
            angle_to_goal = np.arctan2(
                self.goal_pose[1] - self.current_pose[1],
                self.goal_pose[0] - self.current_pose[0]
            )
            obs = np.concatenate([[distance, angle_to_goal], self.current_lidar])
            source = "computed"
        
        else:
            # Waiting for sensor data
            return
        
        # Ensure observation is correct shape (12,)
        if len(obs) != 12:
            self.get_logger().warn(f"⚠ Observation shape mismatch: {len(obs)}, expected 12")
            return
        
        # Get action from RL model
        try:
            action, _ = self.model.predict(obs, deterministic=True)
            self.last_action = action
            self.total_actions += 1
            
            # Clip to safe ranges
            linear_vel = np.clip(float(action[0]), 0.0, 0.22)
            angular_vel = np.clip(float(action[1]), -2.84, 2.84)
            
            # Publish action
            cmd = Twist()
            cmd.linear.x = linear_vel
            cmd.angular.z = angular_vel
            self.cmd_pub.publish(cmd)
            
            # Log periodically (every 20 steps = 1 second)
            self.step_count += 1
            if self.step_count % 20 == 0:
                self.get_logger().info(
                    f"[{self.total_actions:05d}] lin_vel={linear_vel:.3f} "
                    f"ang_vel={angular_vel:.3f} (src:{source})")
        
        except Exception as e:
            self.get_logger().error(f"❌ Inference error: {str(e)}")

def main(args=None):
    try:
        rclpy.init(args=args)
        node = HANSRLNode()
        rclpy.spin(node)
        rclpy.shutdown()
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("HANS RL Node stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
