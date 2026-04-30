using UnityEngine;
using ROS2;
using geometry_msgs.msg;
using std_msgs.msg;

/// <summary>
/// ROS2 Bridge for HANS RL Integration
/// Handles communication between Unity robot simulation and ROS2 RL node
/// </summary>
public class ROS2Bridge : MonoBehaviour
{
    [Header("ROS2 Configuration")]
    [SerializeField] private string robotName = "TurtleBot3";
    [SerializeField] private float publishRate = 20f;  // 20 Hz
    
    [Header("Robot References")]
    [SerializeField] private Rigidbody robotRigidbody;
    [SerializeField] private Transform goalTransform;
    [SerializeField] private LayerMask obstacleLayer;
    [SerializeField] private float lidarMaxRange = 3.5f;
    
    private ROS2UnityComponent ros2Component;
    private IPublisher<Float32MultiArray> sensorPublisher;
    private ISubscriber<Twist> cmdVelSubscriber;
    
    private float linearVelocity = 0f;
    private float angularVelocity = 0f;
    private float publishTimer = 0f;
    
    private bool isInitialized = false;

    void Start()
    {
        Debug.Log("========================================");
        Debug.Log("HANS ROS2 Bridge Initializing...");
        Debug.Log("========================================");
        
        // Get ROS2 component
        ros2Component = GetComponent<ROS2UnityComponent>();
        if (ros2Component == null)
        {
            Debug.LogError("❌ ROS2UnityComponent not found on this GameObject!");
            return;
        }
        
        // Get robot rigidbody
        if (robotRigidbody == null)
        {
            robotRigidbody = GetComponent<Rigidbody>();
            if (robotRigidbody == null)
            {
                Debug.LogError("❌ Rigidbody not found! Add Rigidbody component to robot.");
                return;
            }
        }
        
        // Find goal if not assigned
        if (goalTransform == null)
        {
            GameObject goalObj = GameObject.Find("Goal");
            if (goalObj != null)
            {
                goalTransform = goalObj.transform;
                Debug.Log("✓ Found Goal object");
            }
            else
            {
                Debug.LogWarning("⚠ Goal object not found. Create empty GameObject named 'Goal'");
            }
        }
        
        // Create publishers and subscribers
        try
        {
            // Publisher for sensor data to ROS
            sensorPublisher = ros2Component.CreatePublisher<Float32MultiArray>("/robot/sensors");
            Debug.Log("✓ Created publisher: /robot/sensors");
            
            // Subscriber for commands from ROS
            cmdVelSubscriber = ros2Component.CreateSubscription<Twist>(
                "/cmd_vel",
                OnCmdVelReceived,
                new SubscriptionOptions() { QosProfile = QosProfiles.Default }
            );
            Debug.Log("✓ Created subscriber: /cmd_vel");
            
            isInitialized = true;
            Debug.Log("========================================");
            Debug.Log("✓ HANS ROS2 Bridge READY!");
            Debug.Log("========================================");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"❌ Failed to initialize ROS2: {e.Message}");
            isInitialized = false;
        }
    }

    void FixedUpdate()
    {
        if (!isInitialized) return;
        
        // Publish sensor data at configured rate
        publishTimer += Time.fixedDeltaTime;
        if (publishTimer >= 1f / publishRate)
        {
            PublishSensorData();
            publishTimer = 0f;
        }
        
        // Apply commanded velocities to robot
        ApplyMotorCommands();
    }

    private void PublishSensorData()
    {
        try
        {
            float[] sensorData = GetObservation();
            if (sensorData == null || sensorData.Length != 12)
            {
                return;  // Skip publishing if observation invalid
            }
            
            // Create ROS message
            var msg = new Float32MultiArray();
            msg.data = sensorData;
            
            // Publish
            sensorPublisher.Publish(msg);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"❌ Error publishing sensor data: {e.Message}");
        }
    }

    private float[] GetObservation()
    {
        // Observation format: [distance_to_goal, angle_to_goal, lidar_0...lidar_9]
        float[] observation = new float[12];
        
        Vector3 robotPos = transform.position;
        
        // Default goal if not assigned
        Vector3 goalPos = (goalTransform != null) ? 
            goalTransform.position : 
            new Vector3(9f, 0f, 9f);
        
        // 1. Distance to goal (in meters)
        float distanceToGoal = Vector3.Distance(robotPos, goalPos);
        observation[0] = distanceToGoal;
        
        // 2. Angle to goal (in radians)
        Vector3 toGoal = goalPos - robotPos;
        float angleToGoal = Mathf.Atan2(toGoal.x, toGoal.z);
        observation[1] = angleToGoal;
        
        // 3. LiDAR data (10 sectors)
        float[] lidarData = ComputeLiDAR();
        for (int i = 0; i < 10; i++)
        {
            observation[2 + i] = lidarData[i];
        }
        
        return observation;
    }

    private float[] ComputeLiDAR()
    {
        float[] lidar = new float[10];
        
        for (int i = 0; i < 10; i++)
        {
            // Distribute rays evenly across 360 degrees
            float angleStep = (i / 10f) * 2f * Mathf.PI;
            Vector3 rayDirection = new Vector3(
                Mathf.Sin(angleStep),
                0,
                Mathf.Cos(angleStep)
            ).normalized;
            
            // Raycast
            RaycastHit hit;
            if (Physics.Raycast(
                transform.position,
                rayDirection,
                out hit,
                lidarMaxRange,
                obstacleLayer
            ))
            {
                lidar[i] = hit.distance;
            }
            else
            {
                lidar[i] = lidarMaxRange;
            }
        }
        
        return lidar;
    }

    private void OnCmdVelReceived(Twist msg)
    {
        // Parse command velocity from ROS
        linearVelocity = (float)msg.linear.x;
        angularVelocity = (float)msg.angular.z;
        
        // Clamp to safe ranges
        linearVelocity = Mathf.Clamp(linearVelocity, 0f, 0.22f);
        angularVelocity = Mathf.Clamp(angularVelocity, -2.84f, 2.84f);
    }

    private void ApplyMotorCommands()
    {
        if (robotRigidbody == null) return;
        
        // Apply forward velocity in local forward direction
        Vector3 newVelocity = transform.forward * linearVelocity;
        newVelocity.y = robotRigidbody.velocity.y;  // Preserve gravity
        robotRigidbody.velocity = newVelocity;
        
        // Apply angular velocity around Y axis
        robotRigidbody.angularVelocity = Vector3.up * angularVelocity;
    }

    // Debug visualization
    private void OnDrawGizmos()
    {
        if (goalTransform != null)
        {
            Gizmos.color = Color.green;
            Gizmos.DrawSphere(goalTransform.position, 0.5f);
            Gizmos.DrawLine(transform.position, goalTransform.position);
        }
    }
}
