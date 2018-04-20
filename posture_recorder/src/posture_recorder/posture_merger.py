#!/usr/bin/env python

# author: Guillaume WALCK (2015)

import rospy
from os import sys, path
from optparse import OptionParser

from posture.posture import Posture

def get_file_list(option, opt, value, parser):
    setattr(parser.values, option.dest, value.split(','))

def main():

    parser = OptionParser()
    parser.add_option('-i', '--input', help="List of input posture files, comma separated.", type='string', action='callback', callback=get_file_list, dest = "file_list")
    parser.add_option('-o', '--output', help="Path to output file.", type='string', dest = "output_file")
    
    (opts, args_) = parser.parse_args()
    
    posture = Posture("myposture")
    
    for filepath in opts.file_list:
        print filepath
        posture.append_postures(filepath, strategy="keep")
    posture.save_postures(opts.output_file, strategy="append")


if __name__ == "__main__":
    main()
