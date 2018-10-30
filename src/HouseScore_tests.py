#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
import datetime
import json
import logging
import numpy as np
import os
import sys
import unittest

from dotenv import load_dotenv
from HouseScore import *
from RFAPI import RFAPI
from sklearn import cluster, datasets, mixture
from utils import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, '.cache')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, ".generated")

class HouseScore_tests(unittest.TestCase):
    @staticmethod
    def SearchForSnohomishAndKingCountyWA(
          house_score
        , dom=""
        , get_details=False
        , force=False
        , min_price=490000
        , max_price=760000):
        return house_score.Search("SearchForSnohomishAndKingCountyWA", {
            "render":"json"
            #, "cluster_bounds":"122.93818%2046.92567%2C-119.89496%2046.92567%2C-119.89496%2048.13656%2C-122.93818%2048.13656%2C-122.93818%2046.92567"
            , "market":"seattle"
            , "region_id":[2,118]
            , "region_type":[5,5]
            , "uipt":[1,3] # House,Townhouse
            #, "zoomLevel":9
            , "num_homes":3000
            , "min_price":min_price
            , "max_price":max_price
            , "min_num_baths":2
            , "min_num_beds":3
            , "min_listing_approx_size":1500
            #, "time_on_market_range":"{}".format(dom) # less than
            , "min_year_built":1980
            , "user_poly":"-122.19238 47.554611,-122.087324 47.554147,-122.055051 47.558781,-122.041318 47.564341,-122.033079 47.570828,-122.025526 47.585187,-122.027586 47.641659,-122.029645 47.647673,-122.036512 47.656461,-122.038572 47.665248,-122.042005 47.67126,-122.044752 47.693449,-122.049558 47.70223,-122.057111 47.726253,-122.062604 47.738261,-122.09625 47.777959,-122.101057 47.786726,-122.112043 47.800564,-122.119596 47.807943,-122.134702 47.818549,-122.153242 47.825004,-122.182081 47.840215,-122.201993 47.844363,-122.244565 47.84851,-122.277524 47.84851,-122.297437 47.844823,-122.331083 47.833762,-122.335203 47.830075,-122.337949 47.822699,-122.337949 47.81486,-122.336576 47.812555,-122.334516 47.795952,-122.326963 47.78811,-122.320097 47.783496,-122.306364 47.769191,-122.29881 47.763191,-122.286451 47.757191,-122.280271 47.752574,-122.277524 47.749343,-122.275465 47.739185,-122.267911 47.720248,-122.237012 47.68328,-122.235639 47.673109,-122.240446 47.659699,-122.250059 47.647211,-122.252119 47.642584,-122.253492 47.638421,-122.252805 47.62639,-122.250059 47.622225,-122.232893 47.608339,-122.225339 47.599542,-122.207487 47.583797,-122.201993 47.573607,-122.20062 47.568048,-122.19238 47.554611"
            }
            , get_details=get_details, force=force)

    @staticmethod
    def SearchForZIPCodes(
          house_score
        , dom="30-"
        , force=False):
        zip_codes = [
            98006, 98008, 98007, 98005, 98027, 98029, 98075, 98074, 98053, 98014, 98033, 98034, 98077, 98072, 98011, 98028, 98296, 98012, 
            98021, 98036, 98043, 98037, 98208, 98290] # Maybe : 98019, 98272
        return house_score.SearchForZIPCodes("SearchForZIPCodes", {
                "render":"json"
                #, "cluster_bounds":"122.93818%2046.92567%2C-119.89496%2046.92567%2C-119.89496%2048.13656%2C-122.93818%2048.13656%2C-122.93818%2046.92567"
                , "market":"seattle"
                , "region_id":[]
                , "region_type":[2]
                , "uipt":[1,3] # House,Townhouse
                #, "zoomLevel":9
                , "num_homes":1500
                , "min_price":500000
                , "max_price":750000
                , "min_num_baths":2
                , "min_num_beds":3
                , "min_listing_approx_size":2000
                , "time_on_market_range":"{}".format(dom) # less than
                #, "min_year_built":2000
                }
                , zip_codes
                , force=force)

    @staticmethod
    def GetTimeStamp():
        return datetime.datetime.now().strftime("%Y%m%d")

    @staticmethod
    def SaveHTMLReport(houses, html_file_path, title="", active_only=True, only_good=True):
        html_content = HouseScore.get_houses_html(houses, title=title, active_only=active_only, only_good=only_good)
        with open(html_file_path, "w") as html_out_stream:
            html_out_stream.write(html_content)
        return html_content

    def test_DailySearch(self, dom="", get_details=False, force=False):
        house_score = HouseScore()
        results = HouseScore_tests.SearchForSnohomishAndKingCountyWA(house_score, dom="", get_details=get_details, force=force)
        self.assertIsNotNone(results)
        self.assertNotEqual(len(results), 0)     

        html_file_path = os.path.join(OUTPUT_DIR, "DailySearch_{}.html".format(HouseScore_tests.GetTimeStamp()))
        html_content = HouseScore_tests.SaveHTMLReport(results, html_file_path=html_file_path, title="test_DailySearch")
        self.assertIsNotNone(html_content)
        self.assertNotEqual(len(html_content), 0)        

        groups = house_score.ClusterHouses(results, plot_groups=False)
        self.assertIsNotNone(groups)
        self.assertNotEqual(len(groups), 0)        


if __name__ == '__main__':
    LOG_PATH = os.path.join(CACHE_PATH, '{}.log'.format(datetime.datetime.now().strftime("%Y%m%d")))

    if not os.path.exists(CACHE_PATH):
        os.mkdir(CACHE_PATH)
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)

    unittest.main()
