# *-* coding: utf-8 *-*
"""
This module contains miscellaneous methods.
"""

import os, shelve

home = os.curdir                        # Default
if 'HOME' in os.environ:
    home = os.environ['HOME']
elif os.name == 'posix':
    home = os.path.expanduser("~/")
elif os.name == 'nt':                   # Contributed by Jeff Bauer
    if 'HOMEPATH' in os.environ:
        if 'HOMEDRIVE' in os.environ:
            home = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']
        else:
            home = os.environ['HOMEPATH']


def seconds2human(time, separator=":"):
    """
    seconds2human(int[, separator=str]) -> str
    Converts time in seconds to an human readable format.
    If separator is provided, the numbers in the string will be separated by it.
    """
    if time != None:
        minutes = (time - (time % 60)) / 60
        if minutes >= 60:
            hours = (time - (time % 60)) / 60
        else:
            hours = ""
        seconds = time % 60
        htime = ""
        if len(str(hours)) == 1:
            hours = "0" + str(hours)
        if len(str(minutes)) == 1:
            minutes = "0" + str(minutes)
        if len(str(seconds)) == 1:
            seconds = "0" + str(seconds)
        if hours != "":
            htime = hours + ":"
        htime = htime + str(minutes) + ":" + str(seconds)
    else:
        htime = "00:00"
    return htime

def human2seconds(time, separator=None):
    """
    human2seconds(str[, separator=str]) -> int
    Converts human readable time to seconds.
    """
    if separator != None:
        tlist = time.split(separator)
    else:
        if "." in time:
            tlist = time.split(".")
        elif ":" in time:
            tlist = time.split(":")
    if len(tlist) == 0:
        hours, minutes, seconds = 0, 0, 0
    elif len(tlist) == 1:
        hours, minutes = 0, 0
        seconds = tlist[0]
    elif len(tlist) == 2:
        hours = 0
        minutes, seconds = tlist
    elif len(tlist) == 3:
        hours, minutes, seconds = tlist
    stime = (hours * 3600) + (minutes * 60) + seconds
    return stime

def rgb2bash(rgb):
    for i in rgb:
        i = (i > 127 and 1 or 0)
    if rgb == [1, 0, 0]:
        color = "red"
    elif rgb == [1, 0, 1]:
        color = "magenta"
    elif rgb == [0, 0, 1]:
        color = "blue"
    elif rgb == [0, 1, 1]:
        color = "cyan"
    elif rgb == [0, 1, 0]:
        color = "green"
    elif rgb == [1, 1, 0]:
        color = "yellow"
    elif rgb == [1, 1, 1]:
        color = "white"
    elif rgb == [0, 0, 0]:
        color = "black"