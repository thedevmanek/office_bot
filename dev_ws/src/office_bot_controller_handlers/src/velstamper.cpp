#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <chrono>

class CmdVelStamper : public rclcpp::Node
{
public:
    CmdVelStamper()
        : Node("cmd_vel_stamper")
    {
        publish_rate_ = this->declare_parameter<double>("publish_rate", 30.0);
        input_timeout_ = this->declare_parameter<double>("input_timeout", 2.0);

        pub_ = this->create_publisher<geometry_msgs::msg::TwistStamped>("/cmd_vel_stamped", 10);
        sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10,
            [this](geometry_msgs::msg::Twist::UniquePtr msg)
            {
                last_msg_ = *msg;
                last_input_time_ = this->now();
                have_msg_ = true;
            });

        const auto period = std::chrono::duration<double>(1.0 / publish_rate_);
        timer_ = this->create_wall_timer(
            std::chrono::duration_cast<std::chrono::nanoseconds>(period),
            [this]()
            {
                publish_latest();
            });
    }

private:
    void publish_latest()
    {
        if (!have_msg_)
        {
            return;
        }

        auto twist = last_msg_;
        const auto age = (this->now() - last_input_time_).seconds();
        if (age > input_timeout_)
        {
            twist = geometry_msgs::msg::Twist();
        }

        geometry_msgs::msg::TwistStamped stamped_msg;
        stamped_msg.header.stamp = this->now();
        stamped_msg.header.frame_id = "base_footprint";
        stamped_msg.twist = twist;
        pub_->publish(stamped_msg);
    }

    rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
    rclcpp::TimerBase::SharedPtr timer_;
    geometry_msgs::msg::Twist last_msg_;
    rclcpp::Time last_input_time_;
    double publish_rate_;
    double input_timeout_;
    bool have_msg_{false};
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<CmdVelStamper>());
    rclcpp::shutdown();
    return 0;
}
