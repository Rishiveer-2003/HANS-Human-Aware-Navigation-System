# HANS ROS2-Unity Integration: 24-Hour Action Plan

## ⏰ Timeline: ONE DAY (8 AM - 8 PM)

---

## **HOUR 0-1: NETWORK SETUP (8 AM - 9 AM) - CRITICAL**

### Task 1.1: Verify Network Connection
**On Ubuntu:**
```bash
# Get Ubuntu IP
ifconfig | grep "inet " | head -2
# Should show: 192.168.x.x (NOT 127.0.0.1)

# Test Mac connectivity
ping 192.168.1.x  # Replace with your Mac IP
```

**On Mac Terminal:**
```bash
# Get Mac IP
ifconfig en0 | grep "inet " | head -1
# Should show: 192.168.x.x (same subnet as Ubuntu)

# Test Ubuntu connectivity
ping 192.168.1.x  # Replace with Ubuntu IP
```

**SUCCESS CRITERIA:**
- ✅ Ping Ubuntu → Mac works (0% packet loss)
- ✅ Ping Mac → Ubuntu works
- ✅ Both on same subnet (192.168.1.x)

### Task 1.2: Open Firewall Ports
**On Ubuntu:**
```bash
# Open required ports
sudo ufw allow 9090/tcp   # ROS Bridge WebSocket
sudo ufw allow 5005/tcp   # TCP Bridge
sudo ufw allow 11311/tcp  # ROS Master
sudo ufw status
```

**SUCCESS CRITERIA:** ✅ All ports open, status shows "active"

---

## **HOUR 1-2: ROS2 CORE SETUP (9 AM - 10 AM)**

### Task 2.1: Start ROS Bridge
**On Ubuntu (Terminal 1):**
```bash
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
# Should show: "Rosbridge WebSocket server started on 0.0.0.0:9090"
```

**SUCCESS CRITERIA:**
- ✅ No errors
- ✅ Shows "started on 0.0.0.0:9090"
- ✅ Keep this terminal OPEN

### Task 2.2: Verify ROS2
**On Ubuntu (Terminal 2):**
```bash
source /opt/ros/humble/setup.bash

# Check ROS topics exist
ros2 topic list
# Should show some system topics

# Create test topic
ros2 topic pub /test std_msgs/String "data: 'hello'" --once
```

**SUCCESS CRITERIA:** ✅ ROS2 responds to commands

---

## **HOUR 2-4: CREATE RL ROS NODE (10 AM - 12 PM)**

### Task 3.1: Create Python Package
**On Ubuntu (Terminal 2):**
```bash
cd /home/vboxuser/HANS

# Create ROS package structure
mkdir -p hans_ros_pkg/hans_ros_pkg
touch hans_ros_pkg/setup.py
touch hans_ros_pkg/package.xml
touch hans_ros_pkg/hans_rl_node.py
touch hans_ros_pkg/hans_rl_node_launch.py
```

### Task 3.2: Install Dependencies
```bash
cd /home/vboxuser/HANS
source .venv/bin/activate

# Already installed (verify)
pip install stable-baselines3 gymnasium numpy rclpy geometry-msgs sensor-msgs
```

### Task 3.3: Create Main ROS Node
**File: `/home/vboxuser/HANS/hans_ros_pkg/hans_rl_node.py`**

```python
#!/usr/bin/env python3
"""
HANS RL Node - Loads trained model and publishes commands to robot
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Float32MultiArray
import numpy as np
from stable_baselines3 import PPO
import os

class HANSRLNode(Node):
    def __init__(self):
        super().__init__('hans_rl_node')
        
        self.get_logger().info("Initializing HANS RL Node...")
        
        # Load trained model
        model_path = "/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip"
        if not os.path.exists(model_path):
            self.get_logger().error(f"Model not found: {model_path}")
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model = PPO.load(model_path)
        self.get_logger().info(f"✓ Loaded model from {model_path}")
        
        # Subscribers
        self.pose_sub = self.create_subscription(
            PoseStamped, '/robot/pose', self.pose_callback, 10)
        self.lidar_sub = self.create_subscription(
            LaserScan, '/robot/scan', self.lidar_callback, 10)
        self.sensor_sub = self.create_subscription(
            Float32MultiArray, '/robot/sensors', self.sensor_callback, 10)
        
        # Publisher
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # State buffer
        self.current_pose = None
        self.current_lidar = None
        self.current_sensors = None
        self.goal_pose = np.array([9.0, 9.0])  # Default goal
        self.last_action = None
        
        # Timer for RL inference (20 Hz)
        self.timer = self.create_timer(0.05, self.inference_step)
        
        self.get_logger().info("✓ HANS RL Node initialized successfully!")
        self.get_logger().info("Waiting for sensor data...")
    
    def pose_callback(self, msg):
        """Update robot pose"""
        self.current_pose = np.array([
            msg.pose.position.x,
            msg.pose.position.y
        ])
    
    def lidar_callback(self, msg):
        """Update LiDAR data - reduce to 10 sectors"""
        ranges = np.array(msg.ranges)
        
        # Reduce 360 rays to 10 buckets
        num_buckets = 10
        bucket_size = len(ranges) // num_buckets
        lidar_buckets = []
        
        for i in range(num_buckets):
            start_idx = i * bucket_size
            end_idx = start_idx + bucket_size
            bucket_data = ranges[start_idx:end_idx]
            
            # Take minimum distance in each bucket (closest obstacle)
            min_dist = np.min(bucket_data[~np.isinf(bucket_data)]) if len(bucket_data[~np.isinf(bucket_data)]) > 0 else 10.0
            lidar_buckets.append(min_dist)
        
        self.current_lidar = np.array(lidar_buckets)
    
    def sensor_callback(self, msg):
        """Receive sensor data from Unity"""
        # Expected: [distance_to_goal, angle_to_goal, lidar_0...lidar_9]
        self.current_sensors = np.array(msg.data)
    
    def inference_step(self):
        """Run RL inference and publish commands"""
        # Option 1: Use direct sensor message from Unity
        if self.current_sensors is not None:
            obs = self.current_sensors
        
        # Option 2: Compute from pose + lidar
        elif self.current_pose is not None and self.current_lidar is not None:
            distance = np.linalg.norm(self.goal_pose - self.current_pose)
            angle_to_goal = np.arctan2(
                self.goal_pose[1] - self.current_pose[1],
                self.goal_pose[0] - self.current_pose[0]
            )
            obs = np.concatenate([[distance, angle_to_goal], self.current_lidar])
        
        else:
            # Wait for sensor data
            return
        
        # Ensure observation is correct shape (12,)
        if len(obs) != 12:
            self.get_logger().warn(f"Unexpected observation shape: {len(obs)}, expected 12")
            return
        
        # Get action from RL model
        try:
            action, _ = self.model.predict(obs, deterministic=True)
            self.last_action = action
            
            # Publish action
            cmd = Twist()
            cmd.linear.x = float(action[0])   # linear velocity (0.0 - 0.22)
            cmd.angular.z = float(action[1])  # angular velocity (-2.84 - 2.84)
            
            self.cmd_pub.publish(cmd)
            
            # Log periodically
            if hasattr(self, 'step_count'):
                self.step_count += 1
            else:
                self.step_count = 0
                
            if self.step_count % 20 == 0:  # Log every 1 second
                self.get_logger().info(
                    f"Action: lin_vel={cmd.linear.x:.3f}, ang_vel={cmd.angular.z:.3f}")
        
        except Exception as e:
            self.get_logger().error(f"Inference error: {str(e)}")

def main(args=None):
    rclpy.init(args=args)
    node = HANSRLNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Task 3.4: Setup.py and package.xml

**File: `/home/vboxuser/HANS/hans_ros_pkg/setup.py`**
```python
from setuptools import setup

package_name = 'hans_ros_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    install_requires=['setuptools', 'rclpy', 'geometry-msgs', 'sensor-msgs'],
    entry_points={
        'console_scripts': [
            'hans_rl_node = hans_ros_pkg.hans_rl_node:main',
        ],
    },
)
```

**File: `/home/vboxuser/HANS/hans_ros_pkg/package.xml`**
```xml
<?xml version="1.0"?>
<package format="2">
  <name>hans_ros_pkg</name>
  <version>0.1.0</version>
  <description>HANS RL integration for ROS2</description>
  <maintainer email="rishi@example.com">Rishi</maintainer>
  <license>MIT</license>
  <depend>rclpy</depend>
  <depend>geometry_msgs</depend>
  <depend>sensor_msgs</depend>
</package>
```

### Task 3.5: Test ROS Node
**On Ubuntu (Terminal 2):**
```bash
source /opt/ros/humble/setup.bash
cd /home/vboxuser/HANS/hans_ros_pkg

# Run the node (will wait for sensor data)
python3 hans_rl_node.py

# Should show:
# "✓ Initialized successfully!"
# "Waiting for sensor data..."
```

**SUCCESS CRITERIA:**
- ✅ Node starts without errors
- ✅ Shows "Waiting for sensor data..."
- ✅ Keep running (Ctrl+C to stop later)

---

## **HOUR 4-6: UNITY SETUP (12 PM - 2 PM)**

### Task 4.1: Open Unity Project on Mac

**Requirements:**
- Unity 2022.3+ LTS (free)
- Already have project with TurtleBot3 model

### Task 4.2: Install ROS# Plugin

**In Unity:**
1. Window → TextMesh Pro → Import TMP Essentials (if needed)
2. Assets → Import Package → ROS# (from Asset Store)
3. or manually download from: https://github.com/siemens/ros-sharp/releases

### Task 4.3: Create Bridge Manager Script

**File: `Assets/Scripts/ROS2Bridge.cs`**

```csharp
using UnityEngine;
using ROS2;
using geometry_msgs.msg;

public class ROS2Bridge : MonoBehaviour
{
    private ROS2UnityComponent ros2;
    private IPublisher<Float32MultiArray> sensorPub;
    private ISubscriber<Twist> cmdVelSub;
    
    private Rigidbody robotRb;
    private float linearVel = 0f;
    private float angularVel = 0f;
    
    void Start()
    {
        // Get ROS component
        ros2 = GetComponent<ROS2UnityComponent>();
        if (ros2 == null)
        {
            Debug.LogError("ROS2UnityComponent not found!");
            return;
        }
        
        // Create publisher for sensor data
        sensorPub = ros2.CreatePublisher<Float32MultiArray>("/robot/sensors");
        
        // Create subscriber for commands
        cmdVelSub = ros2.CreateSubscription<Twist>("/cmd_vel", OnCmdVelReceived);
        
        // Get robot rigidbody
        robotRb = GetComponent<Rigidbody>();
        
        Debug.Log("✓ ROS2 Bridge initialized!");
    }
    
    void FixedUpdate()
    {
        // 1. Get sensor data from robot
        float[] sensorData = GetSensorData();
        
        // 2. Publish to ROS
        if (sensorData != null)
        {
            var msg = new Float32MultiArray();
            msg.data = sensorData;
            sensorPub.Publish(msg);
        }
        
        // 3. Apply commanded velocities to robot
        ApplyMotorCommands();
    }
    
    private float[] GetSensorData()
    {
        // Compute observation: [distance, angle, lidar_0...lidar_9]
        Vector3 robotPos = transform.position;
        Transform goalObject = GameObject.Find("Goal")?.transform;
        
        if (goalObject == null)
        {
            Debug.LogWarning("Goal object not found!");
            return null;
        }
        
        Vector3 goalPos = goalObject.position;
        
        // Distance to goal
        float distance = Vector3.Distance(robotPos, goalPos);
        
        // Angle to goal
        Vector3 toGoal = goalPos - robotPos;
        float angleToGoal = Mathf.Atan2(toGoal.x, toGoal.z);
        
        // LiDAR (10 buckets) - raycasting
        float[] lidarBuckets = ComputeLiDAR();
        
        // Combine: [distance, angle, lidar_0...9]
        float[] observation = new float[12];
        observation[0] = distance;
        observation[1] = angleToGoal;
        for (int i = 0; i < 10; i++)
        {
            observation[2 + i] = lidarBuckets[i];
        }
        
        return observation;
    }
    
    private float[] ComputeLiDAR()
    {
        float[] lidar = new float[10];
        float maxRange = 3.5f;
        LayerMask obstacleLayer = LayerMask.GetMask("Obstacles");
        
        for (int i = 0; i < 10; i++)
        {
            // Raycast in each direction
            float angle = (i / 10f) * 2f * Mathf.PI;
            Vector3 direction = new Vector3(
                Mathf.Cos(angle),
                0,
                Mathf.Sin(angle)
            );
            
            RaycastHit hit;
            if (Physics.Raycast(transform.position, direction, out hit, maxRange, obstacleLayer))
            {
                lidar[i] = hit.distance;
            }
            else
            {
                lidar[i] = maxRange;
            }
        }
        
        return lidar;
    }
    
    private void OnCmdVelReceived(Twist msg)
    {
        linearVel = (float)msg.linear.x;
        angularVel = (float)msg.angular.z;
    }
    
    private void ApplyMotorCommands()
    {
        if (robotRb == null) return;
        
        // Apply linear velocity
        robotRb.velocity = transform.forward * linearVel;
        
        // Apply angular velocity
        robotRb.angularVelocity = Vector3.up * angularVel;
    }
}
```

### Task 4.4: Setup Unity Scene
**In Unity Editor:**

1. **Create Game Objects:**
   - Robot (with Rigidbody, collider)
   - Goal (empty GameObject at position 9, 9)
   - Obstacles (if any)

2. **Add Scripts:**
   - Attach `ROS2Bridge.cs` to Robot
   - Set LayerMask to "Obstacles"

3. **Configure ROS2:**
   - Window → ROS2Settings
   - Set Domain ID: 0
   - ROS Slave URI: `http://192.168.1.x:9090` (your Ubuntu IP)

**SUCCESS CRITERIA:**
- ✅ Scene loads without errors
- ✅ ROS2 Bridge script appears in Inspector
- ✅ Robot has Rigidbody

---

## **HOUR 6-7: CONNECT & TEST (2 PM - 3 PM)**

### Task 5.1: Start Everything in Order

**Step 1: Ubuntu - Terminal 1** (Should already be running)
```bash
# ROS Bridge (should be running from 10 AM)
# Check: grep "started on" or tail the output
```

**Step 2: Ubuntu - Terminal 2**
```bash
source /opt/ros/humble/setup.bash
cd /home/vboxuser/HANS/hans_ros_pkg
python3 hans_rl_node.py

# Should output:
# "✓ Initialized successfully!"
# "Waiting for sensor data..."
```

**Step 3: Mac - Unity**
```
Play button ▶ (in Unity Editor)
```

**SUCCESS CRITERIA - Check all:**
- ✅ ROS Bridge running: "started on 0.0.0.0:9090"
- ✅ RL Node running: "Waiting for sensor data..."
- ✅ Unity plays without errors
- ✅ RL Node shows: "Action: lin_vel=..., ang_vel=..."
- ✅ Robot moves in Unity

### Task 5.2: Verify Data Flow

**On Ubuntu Terminal 3:**
```bash
source /opt/ros/humble/setup.bash

# Check topics are publishing
ros2 topic list
# Should see: /robot/sensors, /cmd_vel, /rosbridge_websocket

# Monitor sensor data
ros2 topic echo /robot/sensors --once

# Monitor commands
ros2 topic echo /cmd_vel --once
```

**SUCCESS CRITERIA:**
- ✅ `/robot/sensors` publishing (12 floats)
- ✅ `/cmd_vel` publishing (linear.x, angular.z values)
- ✅ No errors in terminal

---

## **HOUR 7-8: DEBUGGING & POLISH (3 PM - 4 PM)**

### Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "Connection refused" | Ping Ubuntu ↔ Mac, check firewall |
| "Model not found" | Verify path: `/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip` |
| Robot doesn't move | Check Rigidbody is not kinematic, gravity enabled |
| Node says "Waiting..." | Unity not publishing `/robot/sensors` |
| "Permission denied" | `chmod +x hans_rl_node.py` |

### Debug Checklist

```bash
# Test 1: Network
ping <MAC_IP>  # Should work

# Test 2: ROS Bridge
curl http://localhost:9090  # Should respond

# Test 3: Model
python3 -c "from stable_baselines3 import PPO; PPO.load('/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip')"
# Should load without errors

# Test 4: ROS Topics
ros2 topic list | grep -E "sensors|cmd_vel"
# Should show both

# Test 5: Message flow
ros2 topic echo /robot/sensors
ros2 topic echo /cmd_vel
# Should see data flowing
```

---

## **HOURS 8+: FINAL INTEGRATION & DEMO (4 PM onwards)**

### Final Checklist

- [ ] Network: Ubuntu ↔ Mac ping works
- [ ] ROS Bridge: Running, port 9090 open
- [ ] RL Node: Loads model, waiting for data
- [ ] Unity: Scene loads, ROS component configured
- [ ] Data Flow: Sensors → RL → Commands → Robot
- [ ] Robot Movement: Visibly moves in Unity based on RL commands

### Success Demo

```
1. Run: ros2 launch rosbridge_server ...
2. Run: python3 hans_rl_node.py
3. Click Play in Unity
4. Watch robot navigate using trained RL policy!
```

---

## **FILES TO CREATE (Summary)**

| File | Location | Purpose |
|------|----------|---------|
| `hans_rl_node.py` | `/home/vboxuser/HANS/hans_ros_pkg/` | RL inference node |
| `setup.py` | `/home/vboxuser/HANS/hans_ros_pkg/` | Python package config |
| `package.xml` | `/home/vboxuser/HANS/hans_ros_pkg/` | ROS package config |
| `ROS2Bridge.cs` | `Assets/Scripts/` (Unity) | Sensor/command bridge |

---

## **EMERGENCY FALLBACK (If Integration Fails)**

If real-time ROS doesn't work:

### Option A: Record & Playback
```bash
# On Ubuntu, record sensor data
python3 record_sensors.py > sensor_data.csv

# Run RL offline
python3 hans_rl/train.py --eval --episodes 20

# Show metrics in presentation
```

### Option B: Simplified Demo
```
Show 3 things:
1. Trained model loading (terminal)
2. LiDAR visualization in ROS (rqt)
3. Sample trajectories (plot)
```

---

## **TIME BREAKDOWN**

| Phase | Time | Start | End |
|-------|------|-------|-----|
| Network Setup | 1 hr | 8 AM | 9 AM |
| ROS2 Core | 1 hr | 9 AM | 10 AM |
| RL Node Creation | 2 hrs | 10 AM | 12 PM |
| Unity Setup | 2 hrs | 12 PM | 2 PM |
| Connection & Test | 1 hr | 2 PM | 3 PM |
| Debugging | 1 hr | 3 PM | 4 PM |
| **BUFFER** | **2 hrs** | **4 PM** | **6 PM** |

---

## **Priority: MUST HAVE TODAY**

1. ✅ RL node running
2. ✅ ROS Bridge running
3. ✅ Unity connecting
4. ✅ Data flowing (sensors → commands)
5. ✅ Robot moving in Unity

**Nice-to-have (if time permits):**
- Visualization in RViz
- Real-time metrics display
- Multiple obstacles

---

**Start NOW! Let me know when you hit each milestone!**
