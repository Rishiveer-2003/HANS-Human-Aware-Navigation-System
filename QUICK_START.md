# QUICK START: HANS ROS2-Unity Integration

## ⚡ ONE-DAY SETUP CHECKLIST

### ✅ **HOUR 0-1: Network (8 AM)**

```bash
# Ubuntu: Get IP
ifconfig | grep "inet " | head -2

# Mac: Get IP  
ifconfig en0 | grep "inet "

# Test both directions ping
ping <MAC_IP>
```

**Success:** Both machines on same network (192.168.x.x)

---

### ✅ **HOUR 1-2: Start ROS Bridge (9 AM)**

**Ubuntu Terminal 1:**
```bash
source /opt/ros/humble/setup.bash
sudo ufw allow 9090/tcp
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

**Expected output:**
```
[INFO] Starting Rosbridge WebSocket server on 0.0.0.0:9090
```

**Leave this running → Do NOT close**

---

### ✅ **HOUR 2-3: Start RL Node (10 AM)**

**Ubuntu Terminal 2:**
```bash
cd /home/vboxuser/HANS
source .venv/bin/activate
source /opt/ros/humble/setup.bash

python3 hans_ros_pkg/hans_rl_node.py
```

**Expected output:**
```
============================================================
HANS RL ROS2 Node Starting...
✓ Model loaded: /home/vboxuser/HANS/models/hans_ppo_500000_steps.zip
✓ Subscribed to /robot/pose
✓ Subscribed to /robot/scan
✓ Subscribed to /robot/sensors
✓ Publishing to /cmd_vel
✓ HANS RL Node READY!
Waiting for sensor data from Unity...
============================================================
```

**Leave this running → Do NOT close**

---

### ✅ **HOUR 3-5: Setup Unity (11 AM - 1 PM)**

**On Mac:**

1. **Open Unity Project** (2022.3+ LTS)

2. **Import ROS#:**
   - Window → Asset Store
   - Search: "ROS#" or download from GitHub
   - https://github.com/siemens/ros-sharp/releases

3. **Create Scene:**
   - Create empty GameObject called "Robot"
   - Add Rigidbody component
   - Add Collider component
   - Create sphere called "Goal" at position (9, 0, 9)
   - Create ground plane

4. **Add Scripts:**
   - Create `Assets/Scripts/ROS2Bridge.cs`
   - Copy content from: `/home/vboxuser/HANS/Unity_ROS2Bridge.cs`
   - Attach to Robot GameObject

5. **Configure ROS2:**
   - Window → ROS2Settings
   - ROS Slave URI: `http://192.168.1.XXX:9090` (your Ubuntu IP)
   - Domain ID: 0

6. **Assign References in Inspector:**
   - Drag Robot into "robotRigidbody"
   - Drag Goal into "goalTransform"
   - Set obstacleLayer: "Obstacles"

---

### ✅ **HOUR 5-6: TEST CONNECTION (1 PM)**

**Ubuntu Terminal 3 (verification):**
```bash
source /opt/ros/humble/setup.bash

# List topics
ros2 topic list

# Monitor sensors
ros2 topic echo /robot/sensors --once

# Monitor commands
ros2 topic echo /cmd_vel --once
```

**Unity:**
- Click Play ▶

**Expected:**
- RL Node terminal shows: `[00001] lin_vel=0.123 ang_vel=0.456 (src:direct)`
- Robot moves in Unity
- Terminal 3 shows sensor/command data flowing

---

## **IF SOMETHING FAILS**

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Connection refused" on RL node | Check bridge is running: `ps aux \| grep rosbridge` |
| "Model not found" | Check path: `ls /home/vboxuser/HANS/models/hans_ppo_500000_steps.zip` |
| Unity won't connect | Check ROS Slave URI is correct IP |
| Robot doesn't move | Check Rigidbody gravity enabled + not kinematic |
| ROS topics not visible | Try: `ros2 daemon stop && ros2 daemon start` |
| Firewall blocking | `sudo ufw allow 9090/tcp && sudo ufw reload` |

### Quick Debug

```bash
# Test 1: Network
ping <MAC_IP>

# Test 2: ROS Bridge running
curl http://localhost:9090

# Test 3: Model loads
python3 -c "from stable_baselines3 import PPO; PPO.load('/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip'); print('✓ Model OK')"

# Test 4: Topics visible
ros2 topic list | grep -E "cmd_vel|robot"

# Test 5: Data flowing
ros2 topic hz /robot/sensors  # Should show ~20 Hz
```

---

## **FILES CREATED**

```
/home/vboxuser/HANS/
├── hans_ros_pkg/
│   ├── hans_rl_node.py           ← RUN THIS on Ubuntu
│   ├── setup.py
│   └── package.xml
└── Unity_ROS2Bridge.cs           ← COPY THIS to Unity Assets/Scripts/
```

---

## **SUCCESS CRITERIA (All must be ✓)**

- [ ] Ping Ubuntu ↔ Mac works
- [ ] ROS Bridge running on port 9090
- [ ] RL node loaded model (green ✓)
- [ ] RL node says "READY!"
- [ ] Unity plays without errors
- [ ] RL node shows action commands
- [ ] Robot moves in Unity

---

## **DEMO (If everything works)**

```
Narrator: "Our RL-trained policy is now controlling the robot in real-time"

Demo:
1. Show: ROS Bridge running (Ubuntu Terminal 1)
2. Show: RL Node loaded (Ubuntu Terminal 2)
3. Show: Robot moving in Unity
4. Explain: Data flow: Unity sensors → RL → Robot commands
```

---

## **FALLBACK (If integration fails)**

If real-time integration doesn't work by 3 PM:

### Show:
1. **Model Loading** (Terminal):
   ```bash
   python3 -c "from stable_baselines3 import PPO; m = PPO.load('/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip'); print('Model loaded!')"
   ```

2. **Evaluation Results** (Terminal):
   ```bash
   cd /home/vboxuser/HANS
   PYTHONPATH=. python3 hans_rl/train.py --eval --episodes 5
   ```

3. **Code** (VS Code):
   - Show: `hans_rl/envs.py` (environment)
   - Show: `hans_ros_pkg/hans_rl_node.py` (ROS integration)
   - Show: `Unity_ROS2Bridge.cs` (Unity bridge)

This proves the code is working even if live demo doesn't work.

---

**START AT 8 AM! You've got this! 💪**
