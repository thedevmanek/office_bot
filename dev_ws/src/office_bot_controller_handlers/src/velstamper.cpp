#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>

class CmdVelStamper : public rclcpp::Node
{
public:
    CmdVelStamper()
        : Node("cmd_vel_stamper")
    {
        pub_ = this->create_publisher<geometry_msgs::msg::TwistStamped>("/cmd_vel_stamped", 10);
        sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10,
            [this](geometry_msgs::msg::Twist::UniquePtr msg)
            {
                geometry_msgs::msg::TwistStamped stamped_msg;
                stamped_msg.header.stamp = this->now();
                stamped_msg.header.frame_id = "base";
                stamped_msg.twist = *msg;
                pub_->publish(stamped_msg);
            });
    }

private:
    rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<CmdVelStamper>());
    rclcpp::shutdown();
    return 0;
}