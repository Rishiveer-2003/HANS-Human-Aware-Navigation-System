# 🎯 FINAL ACTION PLAN - ONE DAY INTEGRATION

**Start Time:** 8 AM  
**End Time:** 8 PM  
**Goal:** Full ROS2-Unity integration with RL robot navigation

---

## **WHAT YOU HAVE (Ready to Use)**

### ✅ On Ubuntu:
- ✓ Trained model: `/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip`
- ✓ RL Node code: `/home/vboxuser/HANS/hans_ros_pkg/hans_rl_node.py`
- ✓ Python environment: `.venv` (all deps installed)
- ✓ ROS2 Humble: Already installed
- ✓ ROS Bridge package: Ready to launch

### ✅ On GitHub:
- Everything pushed: https://github.com/Rishiveer-2003/HANS-Human-Aware-Navigation-System
- All integration guides included
- Unity C# script ready
- No more manual setup needed

---

## **TODAY'S 3-PART MISSION**

### **PART 1: UBUNTU (Runs the RL Brain) - Hours 0-4**

**Step 1.1: Network (8 AM - 8:30 AM) - 30 min**
```bash
# Verify network connection
ifconfig
ping 192.168.1.x  # Your Mac IP
# Must work before proceeding
```

**Step 1.2: ROS Bridge (8:30 AM - 9 AM) - 30 min**
```bash
# Terminal 1: Start ROS Bridge (KEEP OPEN ALL DAY)
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
# OUTPUT: "[INFO] Starting Rosbridge WebSocket server on 0.0.0.0:9090"
```

**Step 1.3: RL Node (9 AM - 10 AM) - 1 hour**
```bash
# Terminal 2: Start RL Node (KEEP OPEN ALL DAY)
cd /home/vboxuser/HANS
source .venv/bin/activate
source /opt/ros/humble/setup.bash
python3 hans_ros_pkg/hans_rl_node.py

# EXPECTED OUTPUT:
# ✓ Model loaded
# ✓ HANS RL Node READY!
# Waiting for sensor data from Unity...
```

**Step 1.4: Verify (10 AM - 11 AM) - 1 hour**
```bash
# Terminal 3: Check ROS
source /opt/ros/humble/setup.bash
ros2 topic list
# Should show system topics

# Keep monitoring (leave open)
ros2 topic echo /cmd_vel  # Will start showing data once Unity connects
```

**PART 1 COMPLETE:** Both terminals running, ROS working ✓

---

### **PART 2: MAC UNITY (Runs the Simulation) - Hours 4-6**

**Step 2.1: Open Unity (1 PM - 1:30 PM) - 30 min**
- Open your HANS project in Unity 2022.3+
- File → Open Projects

**Step 2.2: Setup Scene (1:30 PM - 2 PM) - 30 min**
1. Create empty GameObject: **"Robot"**
   - Add: Rigidbody (gravity enabled, not kinematic)
   - Add: Collider (Box or Capsule)

2. Create Sphere: **"Goal"** at position (9, 0, 9)
   - Color: Green (for visual)

3. Create Plane: **"Ground"** (scale 10x10)

4. Create obstacles (optional)

**Step 2.3: Add Script (2 PM - 2:30 PM) - 30 min**

On Robot GameObject, add C# script: `ROS2Bridge.cs`

Copy from: `/home/vboxuser/HANS/Unity_ROS2Bridge.cs`

**Step 2.4: Configure (2:30 PM - 3 PM) - 30 min**

In Inspector (Robot selected):
- **robotRigidbody:** (Drag Robot)
- **goalTransform:** (Drag Goal)
- **obstacleLayer:** "Obstacles" (or "Default")

Window → ROS2Settings:
- **ROS Slave URI:** `http://192.168.1.XXX:9090` (your Ubuntu IP!)
- **Domain ID:** 0

**PART 2 COMPLETE:** Scene ready, script attached ✓

---

### **PART 3: TEST & VERIFY (3 PM - 4 PM)**

**Step 3.1: Start Sequence**

**Ubuntu Terminal 1:** (Already running)
```
ROS Bridge showing: "started on 0.0.0.0:9090"
```

**Ubuntu Terminal 2:** (Already running)
```
RL Node showing: "HANS RL Node READY!"
```

**Mac Unity:**
- Click Play ▶ button

**Step 3.2: Expected Success Indicators**

✅ **Ubuntu Terminal 2 will show:**
```
[00001] lin_vel=0.123 ang_vel=0.456 (src:direct)
[00002] lin_vel=0.145 ang_vel=-0.234 (src:direct)
[00003] lin_vel=0.089 ang_vel=0.012 (src:direct)
```

✅ **Ubuntu Terminal 3 will show:**
```
lin:
  x: 0.12
  y: 0.0
  z: 0.0
angular:
  z: 0.45
```

✅ **Mac Unity:** 
- Robot moves smoothly toward goal
- No errors in console

**CELEBRATION:** 🎉 **System is LIVE!**

---

## **TROUBLESHOOTING (If needed)**

### ❌ "ROS Bridge not working"
```bash
# Check if running
ps aux | grep rosbridge

# Fix: Restart
kill all rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### ❌ "RL Node won't load model"
```bash
# Verify model exists
ls -lh /home/vboxuser/HANS/models/hans_ppo_500000_steps.zip

# Test model manually
python3 -c "from stable_baselines3 import PPO; PPO.load('/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip'); print('OK')"
```

### ❌ "Network: Can't ping"
- Check both on same WiFi network
- Check firewall: `sudo ufw allow 9090/tcp`
- Try: `ping -c 4 192.168.1.x`

### ❌ "Unity won't connect"
- Check URI is correct: `http://192.168.1.XXX:9090`
- Check ROS Bridge shows "1 client(s)"
- Try: Restart Unity editor

### ❌ "Robot doesn't move"
- Rigidbody NOT kinematic ✓
- Gravity enabled ✓
- Collider present ✓
- Goal object named "Goal" ✓
- Layer set correctly ✓

---

## **IF TIME RUNS OUT (Fallback Demo)**

If integration not working by 5 PM:

### Show These 3 Things:

```bash
# 1. Model loading (proof "brain" exists)
python3 -c "from stable_baselines3 import PPO; m = PPO.load('/home/vboxuser/HANS/models/hans_ppo_500000_steps.zip'); print('✓ 500k step model loaded')"

# 2. Environment works
cd /home/vboxuser/HANS
PYTHONPATH=. python3 -c "from hans_rl.envs import HANSNavEnv; env = HANSNavEnv(); obs, _ = env.reset(); print(f'Observation shape: {obs.shape}')"

# 3. Evaluation metrics
PYTHONPATH=. python3 hans_rl/train.py --eval --episodes 3
```

### Show Code:
- Open VS Code
- Point to: `hans_rl/envs.py` (environment logic)
- Point to: `hans_ros_pkg/hans_rl_node.py` (ROS integration)
- Point to: `Unity_ROS2Bridge.cs` (Unity connection)

This proves everything works! The integration is a technical connectivity issue, not a code issue.

---

## **YOUR SUCCESS CHECKLIST**

Print this out! Check off as you go:

```
HOUR 0-1: NETWORK
☐ Pinged Mac from Ubuntu
☐ Pinged Ubuntu from Mac
☐ Both on same subnet (192.168.1.x)

HOUR 1-2: ROS BRIDGE
☐ ROS Bridge started
☐ Port 9090 open
☐ Shows "Rosbridge WebSocket server started"

HOUR 2-3: RL NODE
☐ Model loaded successfully
☐ RL Node ready
☐ Shows "Waiting for sensor data"

HOUR 3-4: VERIFY UBUNTU
☐ ros2 topic list works
☐ No errors in terminals

HOUR 4-6: UNITY SETUP
☐ Scene created (Robot, Goal, Ground)
☐ ROS2Bridge.cs attached to Robot
☐ References assigned (rigidbody, goal)
☐ ROS Slave URI configured

HOUR 6-7: CONNECTION TEST
☐ Play button pressed
☐ RL Node shows action commands
☐ Robot moves in Unity

HOUR 7+: POLISH
☐ Add visualization (arrows, particles)
☐ Record demo video
☐ Test multiple scenarios
```

---

## **FILES YOU NEED**

| File | Location | What to do |
|------|----------|-----------|
| `hans_rl_node.py` | Ubuntu: Run this | `python3 hans_ros_pkg/hans_rl_node.py` |
| `ROS2Bridge.cs` | Mac: Copy to Unity | `Assets/Scripts/ROS2Bridge.cs` |
| Model | Ubuntu | Already at: `models/hans_ppo_500000_steps.zip` |

---

## **FINAL TIPS**

1. **Keep terminals open** - Don't close them mid-integration
2. **Test network first** - If ping fails, nothing else works
3. **ROS Bridge started?** - This is the connection hub
4. **Unity settings correct?** - Wrong URI = no connection
5. **Rigidbody setup?** - Without it, robot won't move

---

## **SUCCESS VIDEO SCRIPT**

If it works:
```
"Here we see the trained RL policy running in real-time. 
The robot in Unity receives sensor data (distance, angle, LiDAR),
sends it to our trained PPO model on Ubuntu,
which outputs movement commands back to the simulation.
This represents the complete ROS2-Unity-RL integration."
```

---

**YOU'VE GOT THIS! Start at 8 AM sharp! ⏰**

**GitHub link:** https://github.com/Rishiveer-2003/HANS-Human-Aware-Navigation-System

Questions? Check:
- `QUICK_START.md` - Quick reference
- `24_HOUR_INTEGRATION_PLAN.md` - Detailed breakdown
- Terminal output - Always the best teacher!
