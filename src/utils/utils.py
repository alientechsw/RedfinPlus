#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import time
import math
import matplotlib.patches as patches
import pylab
import pyclipper
from random import randint
from geopy.distance import great_circle
from geopy.geocoders import Nominatim

NOMINATIM_APP_NAME = "RedfinPlusUtil"

def LocationDistance(loc1, loc2):
    """
    Usage: Pass the location as an array [lat,long]
    """
    return great_circle((loc1[0], loc1[1]), (loc2[0], loc2[1])).miles

def AddressToLocation(address):
    """
    Finds the longitude/latitude of an address usin Nominatim
    This doesn't always work, and I was wondering if I need another service. Google is no longer free
    So until a better choice is available I'm stuck with OpenStreetMap
    """
    geolocator = Nominatim(user_agent=NOMINATIM_APP_NAME)
    location = geolocator.geocode(address, timeout=10, exactly_one=True)
    if location is None or len(location) == 0:
        return None
    return [location.latitude, location.longitude]

def InflateRegion(pp, inflate, show_plot=False):
    """
    Given a regoin pp, this mthod will sort the pints, creats a simply-connected-polygon.
    Then uses pyclipper to inflate it by `inflate` amount. I haven't figured aout the math yet. 
    so adjust `inflate` as needed to get a reasonable region
    """
    # url : https://stackoverflow.com/questions/10846431/ordering-shuffled-points-that-can-be-joined-to-form-a-polygon-in-python

    # compute centroid
    cent=(sum([p[0] for p in pp])/len(pp),sum([p[1] for p in pp])/len(pp))
    # sort by polar angle
    pp.sort(key=lambda p: math.atan2(p[1]-cent[1],p[0]-cent[0]))

    # plot points
    if show_plot: 
        pylab.scatter([p[0] for p in pp],[p[1] for p in pp])
        # plot polyline
        pylab.gca().add_patch(patches.Polygon(pp,closed=True,fill=True))

    # inflating the polygon using pyclipper
    coordinates = pp

    clipper_offset = pyclipper.PyclipperOffset()
    coordinates = pyclipper.scale_to_clipper(coordinates)
    clipper_offset.AddPath(coordinates, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
    scaled_coordinates = clipper_offset.Execute(inflate)
    scaled_coordinates = pyclipper.scale_from_clipper(scaled_coordinates)

    if show_plot: 
        for p in scaled_coordinates:
            pylab.gca().add_patch(patches.Polygon(p,closed=True,fill=False))
        pylab.grid()
        pylab.show()

    return scaled_coordinates

STATE_APP = [
     ["Alabama", "AL"]
    ,["Alaska", "AK"]
    ,["Arizona", "AZ"]
    ,["Arkansas", "AR"]
    ,["California", "CA"]
    ,["Colorado", "CO"]
    ,["Connecticut", "CT"]
    ,["Delaware", "DE"]
    ,["Florida", "FL"]
    ,["Georgia", "GA"]
    ,["Hawaii", "HI"]
    ,["Idaho", "ID"]
    ,["Illinois", "IL"]
    ,["Indiana", "IN"]
    ,["Iowa", "IA"]
    ,["Kansas", "KS"]
    ,["Kentucky", "KY"]
    ,["Louisiana", "LA"]
    ,["Maine", "ME"]
    ,["Maryland", "MD"]
    ,["Massachusetts", "MA"]
    ,["Michigan", "MI"]
    ,["Minnesota", "MN"]
    ,["Mississippi", "MS"]
    ,["Missouri", "MO"]
    ,["Montana", "MT"]
    ,["Nebraska", "NE"]
    ,["Nevada", "NV"]
    ,["New Hampshire", "NH"]
    ,["New Jersey", "NJ"]
    ,["New Mexico", "NM"]
    ,["New York", "NY"]
    ,["North Carolina", "NC"]
    ,["North Dakota", "ND"]
    ,["Ohio", "OH"]
    ,["Oklahoma", "OK"]
    ,["Oregon", "OR"]
    ,["Pennsylvania", "PA"]
    ,["Rhode Island", "RI"]
    ,["South Carolina", "SC"]
    ,["South Dakota", "SD"]
    ,["Tennessee", "TN"]
    ,["Texas", "TX"]
    ,["Utah", "UT"]
    ,["Vermont", "VT"]
    ,["Virginia", "VA"]
    ,["Washington", "WA"]
    ,["West Virginia", "WV"]
    ,["Wisconsin", "WI"]
    ,["Wyoming", "WY"]]

def get_long_state(short_state):
    for s in STATE_APP:
        if short_state.upper() == s[1]:
            return s[0]
    return ""

def get_short_state(long_state):
    for s in STATE_APP:
        if long_state.lower() == s[0].lower():
            return s[1]
    return ""

