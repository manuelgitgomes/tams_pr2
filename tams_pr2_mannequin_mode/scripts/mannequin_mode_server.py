#! /usr/bin/env python

from tams_pr2_look.srv import SetTarget
from pr2_mechanism_msgs.srv import *
from std_srvs.srv import *
from std_msgs.msg import Bool, String as StringMsg
from geometry_msgs.msg import PointStamped
import rospy


global run
run = False

global pr2_controllers
global loose_controllers

def toggle_service(req):
    global run
    run = req.data

    # Set look node to mode inactive
    if run:
        rospy.wait_for_service('/look/target')
        try:
            set_look_inactive = rospy.ServiceProxy('/look/target', SetTarget)
            set_look_inactive('inactive', PointStamped(), '')
        except rospy.ServiceException as e:
            print("Service call failed: %s"%e)
            return

    # switch to controllers with low gains / normal controllers
    rospy.wait_for_service('pr2_controller_manager/switch_controller')
    try:
        switch_controllers = rospy.ServiceProxy('pr2_controller_manager/switch_controller', SwitchController)
        if run:
            resp1 = switch_controllers(loose_controllers, pr2_controllers, SwitchControllerRequest.STRICT)
        else:
            resp1 = switch_controllers(pr2_controllers, loose_controllers, SwitchControllerRequest.STRICT)
    except rospy.ServiceException as e:
        print("Service call failed: %s"%e)
        return

    if not resp1:
        print("switching controllers failed")
        return

    # inform our custom mannequin mode to start/stop adjusting the target state on joint state errors
    for i in loose_controllers:
        service_id = i + '/set_trajectory_lock'
        rospy.wait_for_service(service_id)
        try:
            toggle_lock = rospy.ServiceProxy(service_id, SetBool)
            resp2 = toggle_lock(run)
        except rospy.ServiceException as e:
            print("Service call failed: %s"%e)

    state_publisher.publish(run)
    if run:
        message = 'mannequin mode is active'
    else:
        message = 'disabled mannequin mode'
    say_publisher.publish(message)
    return SetBoolResponse(True, message)

if __name__ == "__main__":
    rospy.init_node("mannequin_mode_server")

    pr2_controllers = rospy.get_param('~pr2_controllers')   #['head_traj_controller', 'l_arm_controller', 'r_arm_controller']
    loose_controllers = rospy.get_param('~loose_controllers')   #['head_traj_controller_loose', 'l_arm_controller_loose', 'r_arm_controller_loose']

    state_publisher = rospy.Publisher('mannequin_mode_active', Bool, latch= True, queue_size= 1)
    state_publisher.publish(False)
    say_publisher = rospy.Publisher('/say', StringMsg, queue_size= 1)

    s = rospy.Service('set_mannequin_mode', SetBool, toggle_service)

    rospy.spin()
