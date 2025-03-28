#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <string>
#include <vector>

enum class Joint
{
  BODY_DRAWER1,
  BODY_DRAWER2,
  BODY_DRAWER3,
  BODY_DRAWER4,
  BODY_DRAWER5
};

class JointGroupController : public rclcpp::Node
{
public:
  JointGroupController() : Node("joint_group_controller")
  {
    publisher_ = this->create_publisher<std_msgs::msg::Float64MultiArray>(
        "/joint_group_position_controller/commands", 10);
    RCLCPP_INFO(this->get_logger(), "Joint Group Controller Node has been started.");
  }

  void move_joints(const std::vector<double> &positions)
  {
    if (positions.size() != 5)
    {
      RCLCPP_WARN(this->get_logger(), "Expected 5 joint positions, received %zu", positions.size());
      return;
    }

    std_msgs::msg::Float64MultiArray msg;
    msg.data = positions;
    publisher_->publish(msg);
    RCLCPP_INFO(this->get_logger(), "Sent joint positions: [%f, %f, %f, %f, %f]",
                positions[0], positions[1], positions[2], positions[3], positions[4]);
  }

private:
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr publisher_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  auto controller = std::make_shared<JointGroupController>();
  controller->move_joints({0.35, 0.35, 0.35, 0.35, 0.35}); // Example usage
  rclcpp::spin(controller);
  rclcpp::shutdown();
  return 0;
}