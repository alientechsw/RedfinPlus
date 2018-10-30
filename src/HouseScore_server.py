#!/usr/bin/env python
# -*- coding: utf-8 -*-
import BaseHTTPServer, SimpleHTTPServer
import collections
import json
import logging
import os
import ssl
import sys
from HouseScore import *
from RFAPI import RFAPI
from utils import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, '.cache')
GENERATED_DIR = os.path.join(SCRIPT_DIR, '.generated')

class HouseHuntHTTPSServer(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    run using :
    then access the reports from web browser with https://localhost:8000/SearchByURL/<redfin url>
    """
    """
    def __init__(self, **args):
        super(HouseHuntHTTPSServer, self).__init__(**args)
        self.house_score_calc = HouseScore()
    """
    def get_house_by_url(self, url, force=False):
        house_score_calc = HouseScore()
        if url is None or len(url)==0:
            return ""

        logging.debug("get_house_by_url = {}".format(url))
        with CheckCache(url, forced=force, cahe_folder=GENERATED_DIR, cache_time_format="") as cache_check:
            if cache_check.content is not None and force==False:
                return json.loads(cache_check.content)

            # we will make use of daily cache, but force udate every day for the details
            match = house_score_calc.SearchByUrl(url, force=True, cache_time_format="")
            if match is None:
                return None
            
            score = match[0]["scores"]
            cache_check.content = json.dumps(score, indent=2)

            return score

    def get_house_html_by_url(self, url, force=False):
        score = self.get_house_by_url(url, force=force)
        if score is None:
            return ""

        html_table = DicToTHML(score)
        html_content = r"""
        <HTML>
            <HEAD>
                <STYLE>
                    table, th, td {
                        border:1px solid #c0c0c0;
                        border-spacing: 0px;
                    }

                    th, td {
                        padding: 5px;
                    }

                    tr:nth-child(even) {
                    background-color: #f2f2f2;
                    }

                    tr:nth-child(odd) {
                    background-color: white;
                    }
                </STYLE>
            </HEAD>
            <BODY>""" + html_table + "</BODY></HTML>"

        return html_content

    def HTMLFavorites(self, force=False, force_search=False, cache_time_format="%Y%m%d"):
        with CheckCache("Favorites", forced=force, cahe_folder=GENERATED_DIR, cache_time_format=cache_time_format) as cache_check:
            if cache_check.content is not None and force==False:
                #logging.debug("#1 {}".format(cache_check.enc_url))
                return cache_check.content

            house_score_calc = HouseScore()
            csv_file = os.path.join(SCRIPT_DIR, "Redfin.com", "data", "fav.csv")
            matches = house_score_calc.rfapi.csv_to_dict(csv_file, force=force_search, cache_time_format="")
            matches = house_score_calc.post_process(matches, "Favorites", get_details=True, force=force_search)
            if matches is None or len(matches) == 0:
                #logging.debug("#2 {}".format(cache_check.enc_url))
                return ""

            cache_check.content = HouseScore.get_houses_html(matches
                , only_good=False, active_only=True
                , title="{} {}".format("Favorites", datetime.datetime.now().strftime("%Y%m%d")))
            #logging.debug("#3 {}".format(cache_check.enc_url))
            return cache_check.content

    def HTMLUrlLists(self, title, urlsfile, force=False, force_search=False, cache_time_format="%Y%m%d"):
        with CheckCache(urlsfile, forced=force, cahe_folder=GENERATED_DIR, cache_time_format=cache_time_format) as cache_check:
            if cache_check.content is not None and force==False:
                #logging.debug("#1 {}".format(cache_check.enc_url))
                return cache_check.content

            house_score_calc = HouseScore()
            with open(urlsfile, "r") as tour_stream:
                urls = tour_stream.read().split("\n")
            matches = []
            for url in urls:
                match = house_score_calc.SearchByUrl(house_url=url, force=force_search, get_details=True, cache_time_format="") # cheeting relist
                matches.append(match[0]) 
            matches = house_score_calc.post_process(matches, urlsfile, get_details=True, force=force_search)
            if matches is None or len(matches) == 0:
                #logging.debug("#2 {}".format(cache_check.enc_url))
                return ""

            cache_check.content = HouseScore.get_houses_html(matches
                , only_good=False, active_only=True
                , title="{} {}".format(title, datetime.datetime.now().strftime("%Y%m%d")))
            #logging.debug("#3 {}".format(cache_check.enc_url))
            return cache_check.content

    def HTMLTour(self, force=False, force_search=False, cache_time_format="%Y%m%d"):
        return self.HTMLUrlLists(title="Tour", urlsfile=os.path.join(SCRIPT_DIR, "Redfin.com", "data", "tour.txt"), force=force, force_search=force_search, cache_time_format=cache_time_format)

    def HTMLBest(self, force=False, force_search=False, cache_time_format="%Y%m%d"):
        return self.HTMLUrlLists(title="Best", urlsfile=os.path.join(SCRIPT_DIR, "Redfin.com", "data", "best.txt"), force=force, force_search=force_search, cache_time_format=cache_time_format)

    def HTMLSearchByJSON(self, get_details=False, force=False, force_search=True, only_good=False, name="AnySearch", override={}, cache_time_format="%Y%m%d"):
        with CheckCache(name, forced=force, cahe_folder=GENERATED_DIR, cache_time_format=cache_time_format) as cache_check:
            if cache_check.content is not None and force==False:
                #logging.debug("#1 {}".format(cache_check.enc_url))
                return cache_check.content

            house_score_calc = HouseScore()
            matches = house_score_calc.Search(name, override, get_details=get_details, force=force_search)
            if matches is None or len(matches) == 0:
                #logging.debug("#2 {}".format(cache_check.enc_url))
                return ""

            cache_check.content = HouseScore.get_houses_html(matches
                , only_good=only_good
                , title="{} {}".format(name, datetime.datetime.now().strftime("%Y%m%d")))
            #logging.debug("#3 {}".format(cache_check.enc_url))
            return cache_check.content

    def HTMLSearchEastSide(self, name="HTMLSearchEastSide", get_details=False, force=False, force_search=True, only_good=False, cache_time_format="%Y%m%d"):
        return self.HTMLSearchByJSON(get_details=get_details, force=force, force_search=force_search, only_good=only_good, name=name, cache_time_format=cache_time_format, override={
              "render":"json"
            #, "cluster_bounds":"122.93818%2046.92567%2C-119.89496%2046.92567%2C-119.89496%2048.13656%2C-122.93818%2048.13656%2C-122.93818%2046.92567"
            , "market":"seattle"
            , "region_id":[2,118]
            , "region_type":[5,5]
            , "uipt":[1,3] # House,Townhouse
            #, "zoomLevel":9
            , "num_homes":3000
            , "min_price":490000
            , "max_price":760000
            , "min_num_baths":2
            , "min_num_beds":3
            , "min_listing_approx_size":1500
            #, "time_on_market_range":"{}".format(dom) # less than
            , "min_year_built":1980
            , "user_poly":"-122.19238 47.554611,-122.087324 47.554147,-122.055051 47.558781,-122.041318 47.564341,-122.033079 47.570828,-122.025526 47.585187,-122.027586 47.641659,-122.029645 47.647673,-122.036512 47.656461,-122.038572 47.665248,-122.042005 47.67126,-122.044752 47.693449,-122.049558 47.70223,-122.057111 47.726253,-122.062604 47.738261,-122.09625 47.777959,-122.101057 47.786726,-122.112043 47.800564,-122.119596 47.807943,-122.134702 47.818549,-122.153242 47.825004,-122.182081 47.840215,-122.201993 47.844363,-122.244565 47.84851,-122.277524 47.84851,-122.297437 47.844823,-122.331083 47.833762,-122.335203 47.830075,-122.337949 47.822699,-122.337949 47.81486,-122.336576 47.812555,-122.334516 47.795952,-122.326963 47.78811,-122.320097 47.783496,-122.306364 47.769191,-122.29881 47.763191,-122.286451 47.757191,-122.280271 47.752574,-122.277524 47.749343,-122.275465 47.739185,-122.267911 47.720248,-122.237012 47.68328,-122.235639 47.673109,-122.240446 47.659699,-122.250059 47.647211,-122.252119 47.642584,-122.253492 47.638421,-122.252805 47.62639,-122.250059 47.622225,-122.232893 47.608339,-122.225339 47.599542,-122.207487 47.583797,-122.201993 47.573607,-122.20062 47.568048,-122.19238 47.554611"
            })
        
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()

    @staticmethod
    def get_or_flip(cmds, key, default=True):
        if cmds.get(key) is None:
            return default
        return not default

    @staticmethod
    def parse_args(path_parts):
        if len(path_parts) == 0:
            return None

        logging.debug("path_parts = {}".format(path_parts))

        retVal = {
            "cmd":path_parts[0]
        }

        for i in path_parts[1:]:
            retVal[i] = True

        return retVal

    def do_GET(s):
        """Respond to a GET request."""
        #LOG_PATH = os.path.join(CACHE_PATH, '{}_server.log'.format(datetime.datetime.now().strftime("%Y%m%d"))) #%H%M%S

        path_parts = filter(None, s.path.split("/"))
        if len(path_parts) < 1:
            s.send_response(404)
            s.send_header("Content-type", "text/html")
            s.end_headers()
            return

        s.send_response(200)
        s.send_header('Access-Control-Allow-Origin', '*')
        if(path_parts[0] == "HTMLScoreByURL"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            rf_url = "/" + "/".join(path_parts[1:])
            s.wfile.write(s.get_house_html_by_url(rf_url, force=False))
            return
        if(path_parts[0] == "JSONScoreByURL"):
            s.send_header("Content-type", "application/json")
            s.end_headers()
            rf_url = "/" + "/".join(path_parts[1:])
            score = s.get_house_by_url(rf_url, force=False)
            s.wfile.write(json.dumps(score, indent=2))
            return

        commands = HouseHuntHTTPSServer.parse_args(path_parts)

        if(commands['cmd'] == "HTMLSearchEastSide"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            s.wfile.write(s.HTMLSearchEastSide(
                get_details=HouseHuntHTTPSServer.get_or_flip(commands, "get_details", True), 
                force=HouseHuntHTTPSServer.get_or_flip(commands, "force", False), 
                only_good=HouseHuntHTTPSServer.get_or_flip(commands, "only_good", False), 
                force_search=HouseHuntHTTPSServer.get_or_flip(commands, "force_search", True), 
                cache_time_format="%Y%m%d"))
            return
        if(commands['cmd'] == "HTMLGoodEastSide"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            s.wfile.write(s.HTMLSearchEastSide(
                get_details=HouseHuntHTTPSServer.get_or_flip(commands, "get_details", True), 
                name="HTMLGoodEastSide", 
                force=HouseHuntHTTPSServer.get_or_flip(commands, "force", False), 
                force_search=HouseHuntHTTPSServer.get_or_flip(commands, "force_search", False), 
                only_good=HouseHuntHTTPSServer.get_or_flip(commands, "only_good", True), 
                cache_time_format="%Y%m%d"))
            return
        if(commands['cmd'] == "HTMLFavorites"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            s.wfile.write(s.HTMLFavorites(
                force=HouseHuntHTTPSServer.get_or_flip(commands, "force", False), 
                force_search=HouseHuntHTTPSServer.get_or_flip(commands, "force_search", False), 
                cache_time_format="%Y%m%d"))
            return
        if(commands['cmd'] == "HTMLTour"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            s.wfile.write(s.HTMLTour(
                force=HouseHuntHTTPSServer.get_or_flip(commands, "force", False), 
                force_search=HouseHuntHTTPSServer.get_or_flip(commands, "force_search", False), 
                cache_time_format="%Y%m%d"))
            return
        if(commands['cmd'] == "HTMLBest"):
            s.send_header("Content-type", "text/html")
            s.end_headers()
            s.wfile.write(s.HTMLBest(
                force=HouseHuntHTTPSServer.get_or_flip(commands, "force", False), 
                force_search=HouseHuntHTTPSServer.get_or_flip(commands, "force_search", False), 
                cache_time_format="%Y%m%d"))
            return

        s.wfile.write(s.path)

if __name__ == '__main__':
    
    httpd = BaseHTTPServer.HTTPServer(('', 8000)
        #, SimpleHTTPServer.SimpleHTTPRequestHandler)
        , HouseHuntHTTPSServer)

    # C:\OpenSSL-Win64\bin\openssl req -config "C:\OpenSSL-Win64\bin\openssl.cfg" -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365
    # C:\OpenSSL-Win64\bin\openssl rsa -in key.pem -out key_.pem
    # https://localhost:4443
    httpd.socket = ssl.wrap_socket (httpd.socket,
          keyfile="key_.pem"
        , certfile='cert.pem'
        , server_side=True)

    httpd.serve_forever()
