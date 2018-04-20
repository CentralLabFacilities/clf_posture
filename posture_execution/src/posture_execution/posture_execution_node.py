#!/usr/bin/env python

import rospy
import time

from optparse import OptionParser
from posture_execution import PostureExecution
from posture_execution_msgs.srv import *

if __name__ == "__main__":

    parser = OptionParser()
    parser.add_option("--postures", help="Path to postures made available", dest="posture_path")
    
    (opts, args_) = parser.parse_args()
        
    # init posture execution
    posture_exec = PostureExecution()
    
    # load postures
    posture_exec.load_postures(opts.posture_path)
    
    time.sleep(1)

    # list available postures after successfull load
    rospy.loginfo("Postures:")
    rospy.loginfo(posture_exec.get_postures())
    
    posture_execution_client = rospy.Service('execute_posture', ExecutePosture, posture_exec.handle_ros)
    posture_get_execution_client = rospy.Service('get_postures', GetPostures, posture_exec.get_postures_ros)
    posture_named_target_client = rospy.Service('execute_named_target', ExecuteNamedTarget, posture_exec.moveit_pose)
    
    rospy.loginfo('All clients successfully initialized! Waiting for requests.')
    
    rospy.spin()
