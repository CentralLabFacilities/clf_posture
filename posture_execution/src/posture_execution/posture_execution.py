#!/usr/bin/env python

import threading
import yaml
import time
import logging
import json

from os import sys, path
from optparse import OptionParser
from math import radians

import rospy
from actionlib import SimpleActionClient
from control_msgs.msg import FollowJointTrajectoryAction, \
FollowJointTrajectoryGoal

from sensor_msgs.msg import JointState

from trajectory_msgs.msg import JointTrajectoryPoint

from posture.posture import Posture
from posture_execution_msgs.srv import *

from functools import partial

JNT_TRAJ_SRV_SUFFIX = "_position_trajectory_controller/follow_joint_trajectory"


class PostureExecution(object):
    
    def __init__(self, name=''):        
        try:
            rospy.init_node('posture_execution', anonymous=True, log_level=rospy.DEBUG)
        except rospy.exceptions.ROSException:
            print("rospy.init_node() has already been called with different arguments:")

        self._name = name
        self._prefix = "meka_roscontrol"
        self._client = {}
        self._movement_finished = {}
        self._posture = Posture("mypostures")
        self.all_done = True;
        self.failed = True;
        self._posture_when_done = "waiting"

        threading.Thread(None, rospy.spin)

    def _set_up_action_client(self,group_name):
        """
        Sets up an action client to communicate with the trajectory controller
        """

        self._client[group_name] = SimpleActionClient(
            self._prefix + "/"+ group_name + JNT_TRAJ_SRV_SUFFIX,
            FollowJointTrajectoryAction
        )

        if self._client[group_name].wait_for_server(timeout=rospy.Duration(4)) is False:
            rospy.logfatal("Failed to connect to %s action server in 4 sec",group_name)
            del self._client[group_name]
            raise
        else:
            self._movement_finished[group_name] = True

    def rescale_time_from_start(self, goal, timescale):
        if timescale != 0.0:
            for point in goal.trajectory.points:
                point.time_from_start /= timescale

    def on_done(self, group_name, *cbargs):
        msg = cbargs[1]
        if msg != None and msg.error_code != 0:
            self.failed = True;
        self._movement_finished[group_name] = True
        all_finished = True
        for name in self._movement_finished:
            if not self._movement_finished[name]:
                all_finished = False
                break
        if all_finished:
            self.all_done_callback()

    def all_done_callback(self):
        """
        triggers when all the movement finished
        """
        self._movement_finished = {}
        rospy.loginfo("All movement finished")
        if self._previous_posture != self._posture_when_done and self._posture_when_done != "":
            self.execute("all", self._posture_when_done)
        else:
            self.all_done = True

    def execute(self, group_name, posture_name, timescale=1.0):
        """
        Executes
        @param group_name: group to control
        @param posture_name: posture in this group
        @param timescale: factor to scale the time_from_start of each point
        """
        self._previous_posture = posture_name
        if group_name == "all":
            self._movement_finished = {}
            rospy.loginfo("Calling all the groups")
            groups = ["right_arm", "right_hand", "left_arm","left_hand","torso", "head"]
            self.execute(groups, posture_name)

        elif not isinstance(group_name, basestring):
            for names in group_name:
                self.execute(names, posture_name)

        else:
            goal = self._posture.get_trajectory_goal(group_name, posture_name)
            if goal is not None:
                if timescale != 1.0:
                    # rescale the time_from_start for each point
                    self.rescale_time_from_start(goal, timescale)

                if group_name not in self._client:
                    rospy.loginfo("Action client for %s not initialized. Trying to initialize it...", group_name)
                    try:
                        self._set_up_action_client(group_name)
                    except:
                        rospy.logerr("Could not set up action client for %s.", group_name)
                        return False

                self._movement_finished[group_name] = False
                self.failed = False;
                self._client[group_name].send_goal(goal, done_cb=partial(self.on_done, group_name))
                self.all_done = False;
            else:
                rospy.logerr("No goal found for posture %s in group  %s.", posture_name, group_name)
                return False
        return True

    def load_postures(self, path):
        self._posture.load_postures(path,1)

    def handle_ros(self, req):
        rospy.loginfo('Group: %s Posture: %s' % (req.group_name, req.posture))

        return ExecutePostureResponse(self.execute(req.group_name, req.posture))
        
    def handle(self, event):
        rospy.logdebug("Received event: %s" % event)
        
        if event.getType() != str:
            rospy.logerr("Received non string  event")
            return

        call_str = event.data.split()
        if len(call_str) < 2:
            rospy.logerr("recieved garbage")
            return
        
        des_jnt, des_pos = call_str[0], call_str[1]    

        self.execute(des_jnt, des_pos)
    
    def moveit_pose(self, req):
        rospy.loginfo('Executing named target group: %s & target: %s' % (req.group_name, req.target))

        return ExecuteNamedTargetResponse(self._posture.named_target(req.group_name, req.target))

    def execute_rpc(self, request):
        rospy.logdebug("Received request: %s" % request)

        call_str = request.split()
        if len(call_str) < 2:
            rospy.logerr("recieved garbage")
            return False
            
        des_jnt, des_pos = call_str[0], call_str[1]

        self.execute(des_jnt, des_pos)
        while not self.all_done:
            print "not done"
            time.sleep(4)
        return True
        
    def get_postures_ros(self, req):
        group = req.group_name if req.group_name is not '' else None 
        
        rospy.loginfo('Getting postures for %s' % group)
        
        d = self._posture.list_postures(group)
        return GetPosturesResponse(d)
        
    def get_postures(self, ev=None):
        print "called get postures"
        d = self._posture.list_postures()
        return json.dumps(d)
        
        
if __name__ == "__main__":
    FORMAT = "%(levelname)s %(asctime)-15s %(name)s %(module)s - %(message)s"
    logging.basicConfig(format=FORMAT)

    parser = OptionParser()
    parser.add_option("--joints", help="Path to joints made available", 
        dest="joint_path")
    parser.add_option("--postures", help="Path to postures made available", 
        dest="posture_path")
    parser.add_option("--scope", help="Scope to listen to for remote events",
        dest="scope")
    parser.add_option("--serverScope", help="Scope to listen to for remote procedure calls",
        dest="serverscope")
    
    (opts, args_) = parser.parse_args()
        
    posture_exec = PostureExecution()
    
    posture_exec.load_postures(opts.posture_path)
    
    time.sleep(1)

    print "Postures:"
    print posture_exec.get_postures()
    
    rospy.logdebug("current ver")
    
    rospy.spin()
