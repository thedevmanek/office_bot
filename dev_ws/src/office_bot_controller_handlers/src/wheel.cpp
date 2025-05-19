#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include <chrono>
#include <vector>
#include "tf2/utils.h"                             // for tf2::getYaw
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp" // optional, for TF2 + geometry_msgs integration

using namespace std::chrono_literals;

class MotionTestNode : public rclcpp::Node
{
public:
    MotionTestNode()
        : Node("motion_test_node"), state_(0)
    {
        cmd_pub_ = this->create_publisher<geometry_msgs::msg::TwistStamped>("/cmd_vel", 10);
        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            "/odom", 10,
            std::bind(&MotionTestNode::odom_callback, this, std::placeholders::_1));

        last_step_time_ = this->now();
        timer_ = this->create_wall_timer(100ms, std::bind(&MotionTestNode::step, this));
        RCLCPP_INFO(this->get_logger(), "Starting motion test...");
    }

private:
    void odom_callback(const nav_msgs::msg::Odometry::SharedPtr msg)
    {
        latest_x_ = msg->pose.pose.position.x;
        latest_y_ = msg->pose.pose.position.y;
        latest_yaw_ = tf2::getYaw(msg->pose.pose.orientation);
    }

    void publish_twist(double vx, double vy, double wz)
    {
        geometry_msgs::msg::TwistStamped msg;
        msg.header.stamp = this->now();
        msg.header.frame_id = "base_link";
        msg.twist.linear.x = vx;
        msg.twist.linear.y = vy;
        msg.twist.angular.z = wz;
        cmd_pub_->publish(msg);
    }

    void step()
    {
        auto now = this->now();
        if ((now - last_step_time_).seconds() < 2.0) // Wait 2 seconds between steps
            return;

        last_step_time_ = now;

        switch (state_)
        {
        case 0:
            start_x_ = latest_x_;
            publish_twist(0.5, 0.0, 0.0); // forward
            publish_twist(0.5, 0.0, 0.0); // forward
            publish_twist(0.5, 0.0, 0.0); // forward

            break;
        case 1:
            check_movement(latest_x_ > start_x_, "Forward");
            publish_twist(-0.5, 0.0, 0.0); // backward
            publish_twist(-0.5, 0.0, 0.0); // backward
            publish_twist(-0.5, 0.0, 0.0); // backward

            break;
        case 2:
            check_movement(latest_x_ < start_x_, "Backward");
            start_y_ = latest_y_;
            publish_twist(0.0, 0.5, 0.0); // left
            publish_twist(0.0, 0.5, 0.0); // left
            publish_twist(0.0, 0.5, 0.0); // left

            break;
        case 3:
            check_movement(latest_y_ > start_y_, "Left");
            publish_twist(0.0, -0.5, 0.0); // right
            publish_twist(0.0, -0.5, 0.0); // right
            publish_twist(0.0, -0.5, 0.0); // right

            break;
        case 4:
            check_movement(latest_y_ < start_y_, "Right");
            start_yaw_ = latest_yaw_;
            publish_twist(0.0, 0.0, 0.5); // rotate CW
            publish_twist(0.0, 0.0, 0.5); // rotate CW
            publish_twist(0.0, 0.0, 0.5); // rotate CW

            break;
        case 5:
            check_rotation(latest_yaw_ > start_yaw_, "Clockwise Rotation");
            publish_twist(0.0, 0.0, -0.5); // rotate CCW
            publish_twist(0.0, 0.0, -0.5); // rotate CCW
            publish_twist(0.0, 0.0, -0.5); // rotate CCW

            break;
        case 6:
            check_rotation(latest_yaw_ < start_yaw_, "Counter-Clockwise Rotation");
            publish_twist(0.0, 0.0, 0.0); // stop

            RCLCPP_INFO(this->get_logger(), "Test complete.");
            rclcpp::shutdown();
            break;
        }
        state_++;
    }

    void check_movement(bool condition, const std::string &label)
    {
        if (condition)
            RCLCPP_INFO(this->get_logger(), "%s test passed", label.c_str());
        else
            RCLCPP_WARN(this->get_logger(), "%s test failed", label.c_str());
    }

    void check_rotation(bool condition, const std::string &label)
    {
        if (condition)
            RCLCPP_INFO(this->get_logger(), "%s test passed", label.c_str());
        else
            RCLCPP_WARN(this->get_logger(), "%s test failed", label.c_str());
    }

    rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr cmd_pub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::TimerBase::SharedPtr timer_;

    int state_;
    double latest_x_ = 0.0, latest_y_ = 0.0, latest_yaw_ = 0.0;
    double start_x_ = 0.0, start_y_ = 0.0, start_yaw_ = 0.0;
    rclcpp::Time last_step_time_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MotionTestNode>());
    rclcpp::shutdown();
    return 0;
}
