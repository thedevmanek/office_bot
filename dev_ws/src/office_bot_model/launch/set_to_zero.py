import rclpy
from rclpy.node import Node
from controller_manager import controller_manager_interface
from controller_manager_msgs.srv import ListControllers, SwitchController
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class RobotControlNode(Node):
    def __init__(self):
        super().__init__('robot_control_node')
        
        # Initialize the controller manager interface
        self.controller_manager = controller_manager_interface.ControllerManager(self)
        
        # List of joints to control
        self.position_joints = [
            'body_drawer1', 'body_drawer2', 'body_drawer3', 
            'body_drawer4', 'body_drawer5', 'body_top'
        ]
        
        # self.wheel_joints = [
        #     'body_wheel1', 'body_wheel2', 'body_wheel3', 'body_wheel4'
        # ]
        
        # Set all joints to 0 position
        self.set_joint_positions_to_zero()

    def set_joint_positions_to_zero(self):
        # Create a JointTrajectory message
        trajectory_msg = JointTrajectory()
        trajectory_msg.joint_names = self.position_joints 
        # Create a trajectory point with all positions set to 0
        point = JointTrajectoryPoint()
        point.positions = [0.0] * len(trajectory_msg.joint_names)
        point.time_from_start.sec = 1  # 1 second to reach the desired position
        
        trajectory_msg.points.append(point)
        
        # Publish the trajectory to the joint trajectory controller
        self.publish_trajectory(trajectory_msg)

    def publish_trajectory(self, trajectory_msg):
        # Create a publisher for the joint trajectory controller
        trajectory_pub = self.create_publisher(JointTrajectory, '/position_controller/JointGroupPositionController', 10)
        
        # Publish the trajectory
        trajectory_pub.publish(trajectory_msg)
        self.get_logger().info('Published trajectory to set all joints to 0 position.')

def main(args=None):
    rclpy.init(args=args)
    node = RobotControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()