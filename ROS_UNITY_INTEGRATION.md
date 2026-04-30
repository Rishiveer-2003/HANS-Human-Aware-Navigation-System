# ROS2-Unity Integration Architecture for HANS

## System Overview

```
┌─────────────────────────────────────┐                    ┌─────────────────────────────┐
│   Ubuntu (VMware on Windows)        │  TCP/IP Channel    │   Mac (Unity Editor)        │
│                                     │ ◄────────────────► │                             │
│  ┌──────────────────────────────┐   │   (Port 5005)      │  ┌───────────────────────┐  │
│  │ ROS2 - CORE                  │   │                    │  │ Unity 3D Environment  │  │
│  │ ├─ ros2_control node         │   │                    │  │ ├─ TurtleBot3 Model   │  │
│  │ ├─ ROS# Bridge (TCP)         │   │                    │  │ ├─ LiDAR Simulation   │  │
│  │ └─ RL Policy Server          │   │                    │  │ ├─ Physics Engine     │  │
│  │                              │   │                    │  │ ├─ ROS Universe       │  │
│  │ ┌──────────────────────────┐ │   │                    │  │ │  Bridge             │  │
│  │ │ HANS RL Model            │ │   │                    │  │ └───────────────────────┘  │
│  │ │ (han_ppo_500k.zip)       │ │   │                    │                             │
│  │ └──────────────────────────┘ │   │                    │  ┌───────────────────────┐  │
│  │                              │   │                    │  │ ROS Messages/Topics   │  │
│  │ python hans_rl_ros_node.py   │   │  Sensor Data       │  │ /odom, /cmd_vel,      │  │
│  │ (inference server)           │   │ ◄─────────────────►  │ /scan, /goal_pose     │  │
│  └──────────────────────────────┘   │                    │  └───────────────────────┘  │
│                                     │                    └─────────────────────────────┘
│  Network Config:                    │
│  Ubuntu IP: 192.168.x.x (VMware)    │
│  Mac IP:    192.168.x.y (WiFi)      │  
└─────────────────────────────────────┘
```

---

## Phase 1: Network Setup (Days 1-2)

### Step 1.1: Configure Network Bridge
**On Windows (VMware Host):**
```
- Use VMware Bridged Networking (not NAT)
- Set Ubuntu network to: Bridged Adapter
- Verify connectivity: Ubuntu ↔ Windows ↔ Mac WiFi
```

**On Ubuntu Terminal:**
```bash
# Check IP (should be on same subnet as Mac)
ifconfig
# Example: 192.168.1.105

# Test connectivity to Mac
ping <MAC_IP>  # Example: ping 192.168.1.120
```

**On Mac Terminal:**
```bash
# Check Mac IP
ifconfig en0
# Test Ubuntu
ping 192.168.1.105
```

### Step 1.2: Open Ports
**On Ubuntu (firewall):**
```bash
sudo ufw allow 5005/tcp   # ROS# Bridge port
sudo ufw allow 11311/tcp  # ROS Master (if needed)
```

---

## Phase 2: ROS2 Setup (Days 2-3)

### Step 2.1: Install ROS# (C#/Unity Bridge)
**On Ubuntu:**
```bash
# Install ROS# library
sudo apt install ros-humble-rosbridge-server
```

**Start ROS Bridge:**
```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
# Listens on 0.0.0.0:9090 (WebSocket)
```

### Step 2.2: Create RL ROS Node (Python)
**File: `hans_ros_node.py`**

This node will:
- Load trained RL model
- Subscribe to `/sensors` (pose, lidar)
- Publish to `/cmd_vel` (robot actions)

```python
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from sensor_msgs.msg import LaserScan
from stable_baselines3 import PPO
import numpy as np

class HANSRLNode(Node):
    def __init__(self):
        super().__init__('hans_rl_node')
        
        # Load RL model
        self.model = PPO.load("models/hans_ppo_500000_steps.zip")
        
        # Subscribers
        self.pose_sub = self.create_subscription(
            PoseStamped, '/robot/pose', self.pose_callback, 10)
        self.lidar_sub = self.create_subscription(
            LaserScan, '/robot/scan', self.lidar_callback, 10)
        
        # Publisher
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # State buffer
        self.current_pose = None
        self.current_lidar = None
        
        # Timer for RL inference (20Hz)
        self.timer = self.create_timer(0.05, self.inference_step)
    
    def pose_callback(self, msg):
        self.current_pose = msg
    
    def lidar_callback(self, msg):
        # Convert LaserScan to 10-bucket LiDAR (matching training env)
        self.current_lidar = msg.ranges
    
    def inference_step(self):
        if self.current_pose is None or self.current_lidar is None:
            return
        
        # Compute observation (matching HANS training env format)
        distance = np.linalg.norm([...])  # distance to goal
        angle = np.arctan2(...)  # angle to goal
        lidar_buckets = self.process_lidar(self.current_lidar)
        
        obs = np.array([distance, angle, *lidar_buckets])
        
        # Get action from RL model
        action, _ = self.model.predict(obs, deterministic=True)
        
        # Publish action
        cmd = Twist()
        cmd.linear.x = action[0]   # linear velocity
        cmd.angular.z = action[1]  # angular velocity
        self.cmd_pub.publish(cmd)

if __name__ == '__main__':
    rclpy.init()
    node = HANSRLNode()
    rclpy.spin(node)
```

**Launch file: `hans_rl_launch.py`**
```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='rl_robot_pkg',
            executable='hans_rl_node.py',
            name='hans_rl_node',
            output='screen',
        ),
    ])
```

---

## Phase 3: Unity Setup (Days 3-5)

### Step 3.1: Install ROS# in Unity
**In Unity Asset Store (Free):**
1. Download & import: **ROS# for Unity**
2. Version: 1.0+ for ROS2 support

**Or manual:**
```
Assets/
├── Ros2For Unity/  (from Asset Store)
├── Scripts/
│   ├── HANSRobotController.cs
│   ├── ROSBridge.cs
│   └── SensorSimulator.cs
└── Models/
    └── TurtleBot3_Waffle.fbx
```

### Step 3.2: Import TurtleBot3 Model in Unity
**Options:**

**Option A: URDF Import (Best)**
1. Export TurtleBot3 URDF from ROS:
   ```bash
   cd /opt/ros/humble/share/turtlebot3_description
   find . -name "*.urdf"
   ```
2. Import into Unity using URDF Importer:
   - Asset Store → Search "URDF Importer"
   - Drag URDF into Assets
   - Unity generates prefab automatically

**Option B: Manual Modeling**
- Create 3D model in Blender/Maya
- Export as .fbx
- Import into Unity
- Add Rigidbody components

### Step 3.3: Create ROS Bridge in Unity (C#)

**File: `Assets/Scripts/ROSBridge.cs`**

```csharp
using UnityEngine;
using ROS2;

public class ROSBridge : MonoBehaviour
{
    private ROS2UnityComponent ros2Component;
    private ISubscription<sensor_msgs.msg.LaserScan> lidarSub;
    private ISubscription<geometry_msgs.msg.PoseStamped> poseSub;
    private IPublisher<geometry_msgs.msg.Twist> cmdVelPub;
    
    void Start()
    {
        // Initialize ROS2
        ros2Component = GetComponent<ROS2UnityComponent>();
        
        // Create subscriptions
        lidarSub = ros2Component.CreateSubscription<
            sensor_msgs.msg.LaserScan>(
            "/robot/scan", OnLidarReceived);
        
        poseSub = ros2Component.CreateSubscription<
            geometry_msgs.msg.PoseStamped>(
            "/robot/pose", OnPoseReceived);
        
        // Create publisher
        cmdVelPub = ros2Component.CreatePublisher<
            geometry_msgs.msg.Twist>("/cmd_vel");
    }
    
    private void OnLidarReceived(sensor_msgs.msg.LaserScan msg)
    {
        // Update Unity LiDAR visualization
        Debug.Log($"LiDAR: {msg.ranges.Length} points");
    }
    
    private void OnPoseReceived(geometry_msgs.msg.PoseStamped msg)
    {
        // Update robot position in Unity
        Vector3 pos = new Vector3(
            (float)msg.pose.position.x,
            (float)msg.pose.position.z,
            (float)msg.pose.position.y
        );
        transform.position = pos;
    }
    
    public void PublishCmdVel(float linearX, float angularZ)
    {
        var msg = new geometry_msgs.msg.Twist();
        msg.linear.x = linearX;
        msg.angular.z = angularZ;
        cmdVelPub.Publish(msg);
    }
}
```

### Step 3.4: TurtleBot3 Controller Script

**File: `Assets/Scripts/HANSRobotController.cs`**

```csharp
using UnityEngine;

public class HANSRobotController : MonoBehaviour
{
    [SerializeField] private float wheelRadius = 0.033f;
    [SerializeField] private float wheelBase = 0.287f;  // TurtleBot3 specs
    [SerializeField] private Rigidbody rb;
    
    private Vector3 targetLinearVel = Vector3.zero;
    private float targetAngularVel = 0f;
    
    void FixedUpdate()
    {
        ApplyDifferentialDrive();
    }
    
    private void ApplyDifferentialDrive()
    {
        // Convert linear velocity (m/s) to forward movement
        rb.velocity = transform.forward * (float)targetLinearVel.magnitude;
        
        // Apply angular velocity (rad/s)
        rb.angularVelocity = Vector3.up * targetAngularVel;
    }
    
    public void ReceiveRLCommand(float linearVel, float angularVel)
    {
        targetLinearVel = new Vector3(linearVel, 0, 0);
        targetAngularVel = angularVel;
    }
}
```

---

## Phase 4: Sensor Simulation in Unity (Days 5-6)

### Step 4.1: LiDAR Simulation
**File: `Assets/Scripts/LiDARSimulator.cs`**

```csharp
using UnityEngine;
using ROS2;

public class LiDARSimulator : MonoBehaviour
{
    [SerializeField] private LayerMask obstacleLayer;
    [SerializeField] private int numRays = 360;
    [SerializeField] private float maxRange = 3.5f;
    
    private IPublisher<sensor_msgs.msg.LaserScan> laserPub;
    private ROS2UnityComponent ros2Component;
    
    void Start()
    {
        ros2Component = GetComponent<ROS2UnityComponent>();
        laserPub = ros2Component.CreatePublisher<
            sensor_msgs.msg.LaserScan>("/robot/scan");
    }
    
    void FixedUpdate()
    {
        PublishLiDARScan();
    }
    
    private void PublishLiDARScan()
    {
        var msg = new sensor_msgs.msg.LaserScan();
        msg.angle_min = -Mathf.PI;
        msg.angle_max = Mathf.PI;
        msg.angle_increment = 2 * Mathf.PI / numRays;
        msg.range_min = 0.12f;
        msg.range_max = maxRange;
        
        float[] ranges = new float[numRays];
        
        for (int i = 0; i < numRays; i++)
        {
            float angle = msg.angle_min + i * msg.angle_increment;
            Vector3 rayDir = new Vector3(
                Mathf.Cos(angle), 0, Mathf.Sin(angle));
            
            if (Physics.Raycast(transform.position, rayDir, 
                out RaycastHit hit, maxRange, obstacleLayer))
            {
                ranges[i] = hit.distance;
            }
            else
            {
                ranges[i] = maxRange;
            }
        }
        
        msg.ranges = ranges;
        laserPub.Publish(msg);
    }
}
```

### Step 4.2: Odometry Publisher
**File: `Assets/Scripts/OdometryPublisher.cs`**

```csharp
using UnityEngine;
using ROS2;

public class OdometryPublisher : MonoBehaviour
{
    private IPublisher<nav_msgs.msg.Odometry> odomPub;
    private ROS2UnityComponent ros2Component;
    private Vector3 lastPosition;
    private Quaternion lastRotation;
    
    void Start()
    {
        ros2Component = GetComponent<ROS2UnityComponent>();
        odomPub = ros2Component.CreatePublisher<
            nav_msgs.msg.Odometry>("/odom");
        lastPosition = transform.position;
        lastRotation = transform.rotation;
    }
    
    void FixedUpdate()
    {
        PublishOdometry();
    }
    
    private void PublishOdometry()
    {
        var msg = new nav_msgs.msg.Odometry();
        msg.header.frame_id = "odom";
        msg.child_frame_id = "base_link";
        
        // Position
        msg.pose.pose.position.x = transform.position.x;
        msg.pose.pose.position.y = transform.position.z;
        msg.pose.pose.position.z = 0;
        
        // Orientation
        msg.pose.pose.orientation.w = transform.rotation.w;
        msg.pose.pose.orientation.x = transform.rotation.x;
        msg.pose.pose.orientation.y = transform.rotation.z;
        msg.pose.pose.orientation.z = transform.rotation.y;
        
        odomPub.Publish(msg);
    }
}
```

---

## Phase 5: Data Flow & Execution (Days 6-7)

### Communication Flow:

```
1. Unity spawns TurtleBot3
   ↓
2. Unity publishes sensor data (LiDAR, Odometry)
   ↓
3. ROS node receives sensor data
   ↓
4. RL model processes observations
   ↓
5. RL model outputs action (linear_vel, angular_vel)
   ↓
6. ROS node publishes cmd_vel to Unity
   ↓
7. Unity applies forces to robot
   ↓
   [Loop back to 2]
```

### Execution Steps:

**Terminal 1 - Ubuntu (ROS Bridge):**
```bash
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

**Terminal 2 - Ubuntu (RL Node):**
```bash
cd /home/vboxuser/HANS
source .venv/bin/activate
PYTHONPATH=/home/vboxuser/HANS python3 hans_ros_node.py
```

**On Mac - Unity Editor:**
1. Open project
2. Set ROS slave URI: `http://192.168.1.105:9090`
3. Enable ROS connection
4. Press Play
5. Watch robot navigate using RL policy

---

## Phase 6: Testing & Debugging (Days 7-8)

### Test checklist:
- [ ] Ubuntu → Mac network ping works
- [ ] ROS Bridge running on Ubuntu (port 9090)
- [ ] ROS node loads model successfully
- [ ] Unity connects to ROS Bridge
- [ ] LiDAR data flowing to ROS
- [ ] Robot moves in Unity based on RL commands
- [ ] Visualize robot path and obstacles

### Debug commands:

```bash
# Monitor ROS topics
ros2 topic list
ros2 topic echo /cmd_vel
ros2 topic echo /robot/scan

# Check ROS nodes
ros2 node list

# View ROS graph
rqt_graph
```

---

## Hardware Specs Needed

| Component | Requirement |
|-----------|-------------|
| Network | Both Ubuntu & Mac on same WiFi subnet |
| Ubuntu VM | Minimum 4GB RAM, 2 cores |
| Mac | Unity 2022.3+ LTS (free Personal edition) |
| ROS2 | Humble or newer |
| Python | 3.8+ (for stable-baselines3) |

---

## Directory Structure

```
/home/vboxuser/HANS/
├── hans_rl/
│   ├── envs.py
│   ├── train.py
│   └── ros_integration/
│       ├── hans_ros_node.py ← NEW
│       ├── hans_rl_launch.py ← NEW
│       └── package.xml ← NEW
├── models/
│   └── hans_ppo_500000_steps.zip
└── requirements.txt
```

---

## Next Steps

1. **Setup network** (Day 1)
2. **Verify ping** Ubuntu ↔ Mac (Day 1)
3. **Install ROS#** in Unity (Day 2)
4. **Test ROS Bridge** (Day 2)
5. **Import TurtleBot3 URDF** (Day 3)
6. **Implement ROS Node** (Day 3-4)
7. **Wire up sensors** (Day 5)
8. **Test end-to-end** (Day 6)
9. **Debug & optimize** (Day 7-8)

---

**Estimated Timeline:** 7-10 days for full integration

Start with network setup and let me know if you need detailed code for any phase!
