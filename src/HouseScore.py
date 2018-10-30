#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HouseScore class is an attempt to convert all house features, location, into one dimention to enable comparison.
The dimention I chose was `Money`. It is simple and easy to understand. Once we collect the info+details, we run a collection of 
scoring functions that each has a signature of `score_method`(house, details) and returns `HouseScoreResult`. 
The `HouseScore` takes a dictionary of score creterias where it later attempts to find score functions to process otherwise will ignore it.
for example

"distance": {
                "median": 8.0, # stay in King County
                "div": 0.5,
                "weight":-9000.0, # one mile costs ( $900 / year ) * 10 years
                "cutoff":18.0
            }

Will attempt to run `HouseScore.distance(house, details)` and will accumulate the results if it finds the implementation.

of course the buyers point of view is very biased. For example, a house from the buyers point of view may costs the same to 
build here on Earth, or on Mars.. it is the commute that makes location becomes intresting. 
I admit I should have consider the neighborhood's average -specially that I already have this data.
But, I wanted to keep things simple.. we could improve the score functions later to consider this defect.
"""
import calendar
import collections
import concurrent.futures
import datetime
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import time
import traceback

from itertools import cycle, islice
from RFAPI import RFAPI
from sklearn import cluster, datasets, mixture
from tqdm import tqdm
from utils import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CACHE_DIR = os.path.join(SCRIPT_DIR, '.cache')
GENERATED_DIR = os.path.join(SCRIPT_DIR, '.generated')

HouseScoreResult = collections.namedtuple('HouseScoreResult', ['money', 'value', 'accepted', 'message'])
class HouseScore(object):
    DEFAULTS = {
            "distance": {
                "median": 8.0, # stay in King County
                "div": 0.5,
                "weight":-9000.0, # one mile costs ( $900 / year ) * 10 years
                "cutoff":18.0
            },
            "area": {
                "median": 2700.0, # We are looking for a house around this area
                "div": 1.0,
                "weight":225.0, # a good house would cost $275 per SF
                "cutoff":1900.0
            },
            "build": {
                "median": 2018.0,
                "div": 1.0,
                "weight":-2000.0,
                "cutoff":1990.0
            },
            "beds": {
                "median": 4.0,
                "div": 1.0,
                "weight":10000.0, # for each extra room you get 10K
                "cutoff":3.0
            },
            "backyard": {
                "median": 2500.0, # not used
                "div": 1.0,
                "weight":5.0, # I'd pay extra 25K for 5000 SF back yard
                "cutoff": 500.0
            },
            "crime": {
                "median": 236.5,
                "div": 1.0,
                "weight": 1.0,
                "cutoff": -10.0
            },
            "history": {
                "median": 7.0,
                "div": 1000.0, # lose 0.1% every day on market
                "weight":1.0, # penelty = dom * price / div
                "cutoff":155.0, # if no human finds this house good for 5 months, don't consider it!
                "history_days":365.0,
                "pending_penelty": 10000.0,
                "inspection_penelty": 25000.0,
                "delisted_penelty": 5000.0
            },
            "layout": {
                "median": 0.0, # not used
                "div": 0.01,
                "weight":1.0,
                "cutoff": 0.0, # not used
                "beds_min":3.0,
                "bed_bonus":10000.0,
                "baths_min":2.5,
                "bath_bonus":2000.0,
                "required":{
                    "Attached Garage":5000.0,
                    "Living Room":5000.0,
                    "Dining Room":5000.0
                },
                "optional":{
                    "Bonus Room":1000.0,
                    "Family Room":5000.0,
                    "Recreation Room":1000.0,
                    "Walk-In Closet":1000.0,
                    "Utility Room":1000.0,
                    "Loft":1000.0,
                    "Den":3000.0,
                    "Office":1000.0
                }
            },
            "amenities": {
                "median": 95.0, # not used
                "div": 0.01,
                "weight":1.0,
                "cutoff": 80.0, # should have 80% of what we are looking for
                "required":{
                    "Forced Air Heating":10000.0,
                    "Dishwasher":2000.0,
                    "Dryer":1000.0,
                    "Oven":1000.0,
                    "Refrigerator":3000.0,
                    "'Washer'":1000.0,
                    "Public Water Source":5000.0,
                    "Sewer Connected":5000.0,
                    "Garbage Disposal":1000.0,
                    "High Speed Internet":5000.0
                },
                "optional":{
                    "Microwave":500.0,
                    "Composition Roof":2000.0,
                    "Central Air Conditioning":10000.0,
                    "'King County'":100000.0,
                    "'Bothell'":50000.0,
                    "'Kenmore'":50000.0,
                    "'Brier'":20000.0
                }
            },
            "value": {
                # always run this last
                "total_cutoff":500000.0,
                "percentage_cutoff":-50.0
            }
        }

    def __init__(self
        , default_fields=None
        , fav_locations = None
        , cahe_folder = CACHE_DIR):
        super(HouseScore, self).__init__()

        self.cahe_folder = cahe_folder
        self.rfapi = RFAPI(cahe_folder = cahe_folder)

        if default_fields is not None:
            self.default_fields = default_fields
        else:
            self.default_fields = HouseScore.DEFAULTS.copy()

        if fav_locations is not None:
            self.fav_locations = fav_locations
        else:
            self.fav_locations = HouseScore.LoadFavorits(os.path.join(SCRIPT_DIR, "FavoriteLocations.json"))

    def value(self, house, details=None, total_score=0.0):
        total_cutoff = self.default_fields["value"]["total_cutoff"]
        percentage_cutoff = self.default_fields["value"]["percentage_cutoff"]

        details_available = details is not None

        message = []
        accepted = True

        if total_score < total_cutoff and details_available:
            accepted = False
            message.append("house valued at {} which is less than {}".format(total_score, total_cutoff))

        gain = total_score - float(house["price"])
        gain_percentage = gain / total_score * 100
        if gain_percentage < percentage_cutoff and details_available:
            accepted = False
            message.append("house ROI of {} which is less than {}".format(gain_percentage, percentage_cutoff))

        return HouseScoreResult(total_score, gain_percentage, accepted, ", ".join(message))

    def get_scores(self, house, details=None):
        scores = {}
        total_score = 0.0
        for k in self.default_fields:
            if k == "value": continue
            method = getattr(self, k, None)
            if method is None: continue
            result = method(house, details)
            scores[k] = dict(**result._asdict())
            total_score += result.money
            if not result.accepted:
                scores["cutoff"] = ",".join(filter(None, [scores.get("cutoff"), k]))

        # value evaluation must be run last
        result = self.value(house, details, total_score)
        scores["value"] = dict(**result._asdict())
        if not result.accepted:
            scores["cutoff"] = ",".join(filter(None, [scores.get("cutoff"), "value"]))

        scores["facts"] = {
             "build":house.get("year_built", -1)
            ,"full_address":RFAPI.house_address(house)
            ,"beds":house["beds"]
            ,"sqft":house["sqft"] if house.get("sqft") is not None else 0.0
            ,"baths":house.get("baths", 0)
            ,"price":house["price"]
            ,"County":RFAPI.house_county(house, details)
            ,"photo":RFAPI.house_photo_url(house, details)
            ,"neighborhoods":RFAPI.house_neighborhoods(house, details) if details is not None else []
        }
        return scores

    def _get_measure_facts(self, measure_name):
        median = self.default_fields[measure_name]["median"]
        div = self.default_fields[measure_name]["div"]
        cutoff = self.default_fields[measure_name]["cutoff"]
        weight = self.default_fields[measure_name]["weight"]
        return (median, div, cutoff, weight)

    def area(self, house, details):
        median, div, cutoff, weight = self._get_measure_facts("area")
        if house.get("sqft") is None: 
            return HouseScoreResult(0.0, 0.0, False, "missing 'sqft'")
        area = house["sqft"]
        money = area * weight
        message = "" if area >= cutoff else "area {}(sf) is less than cut of {}(sf)".format(area, cutoff)
        return HouseScoreResult(money, area, (area >= cutoff), message)

    def build(self, house, details):
        median, div, cutoff, weight = self._get_measure_facts("build")
        if house.get("year_built") is None: 
            return HouseScoreResult(0.0, 0.0, False, "missing 'year_built'")
        year_built = house["year_built"]
        money = (median - year_built) / div * weight
        message = "" if year_built >= cutoff else "House is built in {}, older than cut of {}".format(year_built, cutoff)
        return HouseScoreResult(money, year_built, (year_built >= cutoff), message)
    
    def backyard(self, house, details):
        if house.get("lotsize") is None or house.get("sqft") is None: 
            return HouseScoreResult(0.0, 0.0, False, "missing 'lotsize' or 'sqft'")
        median, div, cutoff, weight = self._get_measure_facts("backyard")
        remaining_for_backyard = float(house["lotsize"]) - float(house["sqft"])
        money = remaining_for_backyard * weight
        message = "" if remaining_for_backyard >= cutoff else "backyard {}(sf) is less than cut of {}(sf)".format(remaining_for_backyard, cutoff)
        return HouseScoreResult(money, remaining_for_backyard, (remaining_for_backyard >= cutoff), message)

    def amenities(self, house, details):
        return self.amenitiesInfo("amenities", house, details)

    def layout(self, house, details):
        info = self.amenitiesInfo("layout", house, details)
        money_score = info.money
        # check beds / baths
        if house.get("beds") is not None:
            extra_beds = house["beds"] - self.default_fields["layout"]["beds_min"]
            money_score += extra_beds * self.default_fields["layout"]["bed_bonus"]
        if house.get("baths") is not None:
            extra_baths = house["baths"] - self.default_fields["layout"]["baths_min"]
            money_score += extra_baths * self.default_fields["layout"]["bath_bonus"]

        return HouseScoreResult(money_score, info.value, info.accepted, info.message)


    def dom(self, house, details):
        median, div, cutoff, weight = self._get_measure_facts("history")
        now_epoch =  time.time() * 1000.0
        oldest_epoch = now_epoch - self.default_fields["history"]["history_days"] * MS_IN_A_DAY

        house["dom_fixed"] = house["dom"] if house.get("dom") is not None else 0.0
        if details is not None:
            oldest_history_after_sale = now_epoch
            for event in details["payload"]["propertyHistoryInfo"]["events"]:
                if "sold" in event["eventDescription"].lower() or event["eventDate"] < oldest_epoch: # or event["historyEventType"] != 1
                    break # assuming events are sorted!
                event_epoc = event["eventDate"]
                if event_epoc < oldest_history_after_sale:
                    #logging.debug("#1 oldest = {}, this event = {}".format(oldest_history_after_sale,event_epoc))
                    oldest_history_after_sale = event_epoc
            oldest_history_after_sale_days = (now_epoch - oldest_history_after_sale) / MS_IN_A_DAY
            #logging.debug("dom={}, dom_fixed={}".format(house["dom"], oldest_history_after_sale_days))
            house["dom_fixed"] = max(house["dom"], oldest_history_after_sale_days)
        if house.get("dom") is None: 
            return HouseScoreResult(0.0, 0.0, False, "missing 'dom'")
        dom = house["dom_fixed"]
        money = (median - dom) / div * float(house["price"])
        message = "House was on the market for {} days".format(int(dom))
        if int(dom) != int(house["dom"]):
            message = message + " (reported {} days)".format(int(house["dom"]))
        if dom > cutoff:
            message = message + ", more than cut of {}".format(int(cutoff))
        return HouseScoreResult(money, dom, (dom < cutoff), message)
    
    @staticmethod    
    def AddIfNotExists(list_to_append, element):
        if element not in list_to_append:
            list_to_append.append(element)
        return list_to_append
    
    def history(self, house, details):
        na = HouseScoreResult(0, 0.0, True, "Not enough details")
        if details is None:
            return na
        if details.get("payload") is None or details.get("payload").get("propertyHistoryInfo") is None: return na
        median, div, cutoff, weight = self._get_measure_facts("history")
        messages = []
        dom_results = self.dom(house, details)
        messages.append(dom_results.message)

        epoch_days = time.time() * 1000.0 / MS_IN_A_DAY
        oldest_epoch_days = epoch_days - self.default_fields["history"]["history_days"]
        oldest_epoch_days = max(house["dom_fixed"], oldest_epoch_days)
        total_penelty = 0.0
        for event in details["payload"]["propertyHistoryInfo"]["events"]:
            event_epoc = event["eventDate"]
            event_epoc_days = event_epoc / MS_IN_A_DAY
            event_epoc_diff = int(epoch_days - event_epoc_days)
            event_str = json.dumps(event).lower()

            #logging.debug("#2 oldest = {}, this event = {}, diff = {}".format(oldest_epoch_days,event_epoc_days,event_epoc_diff))
            if event_epoc_days < oldest_epoch_days:
                continue
            
            #logging.debug("event = {}".format(event_str))

            if "inspection" in event_str:
                total_penelty -= self.default_fields["history"]["inspection_penelty"]
                HouseScore.AddIfNotExists(messages, "was pending inspection {} days ago".format(event_epoc_diff))
            elif "pending" in event_str:
                total_penelty -= self.default_fields["history"]["pending_penelty"]
                HouseScore.AddIfNotExists(messages, "was pending {} days ago".format(event_epoc_diff))
            elif event["eventDescription"].lower() in ["delisted", "relisted"]:
                total_penelty -= self.default_fields["history"]["delisted_penelty"]
                HouseScore.AddIfNotExists(messages, "was relisted {} days ago".format(event_epoc_diff))

        return HouseScoreResult(total_penelty + dom_results.money, dom_results.value, dom_results.accepted, ", ".join(messages))

    def amenitiesInfo(self, key, house, details):
        na = HouseScoreResult(0, 0.0, True, "Not enough details")
        if details is None:
            return na
        if details.get("payload") is None or details.get("payload").get("amenitiesInfo") is None: return na
        median, div, cutoff, weight = self._get_measure_facts(key)
        #logging.debug("amenities : detials = {}".format(details))
        amenities_str = str(details["payload"]).lower()
        #logging.debug("amenities_str = {}".format(amenities_str)) #disable me
        required_amenities_sum = 0.0
        amenities_score = 0.0
        missing_amenities = []
        for k in self.default_fields[key]["required"]:
            v = self.default_fields[key]["required"][k]
            required_amenities_sum = required_amenities_sum + v
            if k.lower() in amenities_str:
                amenities_score = amenities_score + v
            else:
                missing_amenities.append(k)

        for k in self.default_fields[key]["optional"]:
            if k.lower() in amenities_str:
                amenities_score = amenities_score + self.default_fields[key]["optional"][k]
            else:
                missing_amenities.append(k)
        
        missing_amenities_message = "" if len(missing_amenities) == 0 else "missing : [ {} ]".format(",".join(missing_amenities))
        percentage = amenities_score / required_amenities_sum / div
        message = missing_amenities_message if percentage >= cutoff else " percentage {} is less than cut of {}, {}".format(percentage, cutoff, missing_amenities_message)

        return HouseScoreResult(amenities_score, percentage, (percentage >= cutoff), message)

    def distance(self, house, details):
        ret = 0.0
        median, div, cutoff, weight = self._get_measure_facts("distance")
        fav_len = len(self.fav_locations)
        if fav_len == 0 or house.get("parcel") is None or house.get("parcel").get("longitude") is None:
            house_address = RFAPI.house_address(house)
            if house_address != "":
                loc = AddressToLocation(house_address)
                if loc is not None and len(loc) == 2:
                    house["parcel"] = {
                        "latitude": loc[0],
                        "longitude": loc[1]
                    }
            return HouseScoreResult(cutoff * weight, cutoff, False, "Can't measure distance")

        for fav in self.fav_locations:
            dist = LocationDistance([house["parcel"]["latitude"], house["parcel"]["longitude"]], fav["loc"])
            diff = dist / div
            ret = ret + diff

        distance_average = ret / fav_len
        money = distance_average * weight
        message = "" if distance_average <= cutoff else "distance {}(mil) is larger than cut of {}(mil)".format(distance_average, cutoff)
        return HouseScoreResult(money, distance_average, (distance_average < cutoff), message)

    @staticmethod
    def get_house_score_message(m):
        scores = m['scores']
        id_str = RFAPI.house_address(m)

        if m.get("URL") is not None:
            id_str = "{} : http://www.redfin.com{}".format(id_str, m["URL"])

        if scores.get("cutoff") is not None:
            return False, "{} => Cut for {{ {} }} score = {}".format(id_str, scores["cutoff"], scores)
        else:
            return True, ("{} => {}".format(
                id_str
                , scores))
                
    def post_process_one(self
        , m
        , search_name
        , get_details=False
        , force=False):
        house_details = None
        if get_details:
            house_details = self.rfapi.get_house_details(m, force=force, cache_time_format="")

        #logging.debug("post_process(get_details={})=>{}".format(get_details, house_details))
        RFAPI.generate_url_for_house(m)
        ha = RFAPI.house_address_parts(m)
        scores = None
        try:
            scores = self.get_scores(m, house_details)
        except:
            logging.error("house : {}, throw {}".format(json.dumps(m), traceback.format_exc()))
        if scores is None:
            return m

        m['scores'] = scores
        is_good, message = HouseScore.get_house_score_message(m)

        if is_good:
            if house_details is None:
                house_details = self.rfapi.get_house_details(m, force=force, cache_time_format="")
                scores = self.get_scores(m, house_details)
            house_neighborhoods = RFAPI.house_neighborhoods(m, house_details)
            m['scores'] = scores
            is_good, message = HouseScore.get_house_score_message(m)

            logging.info(message)
            # getting city data takes a long time, will do it only for winning houses!
            """
            self.city_data.get_data(
                house_address= ha['display']
                , city=ha['city']     # Everett
                , state_short=ha['state']
                , zip_code=ha['zip']
                , house_neighborhoods=house_neighborhoods
                , force=force)
            """
        else:
            logging.debug(message)

        return m

    def post_process(self
        , matches
        , search_name
        , get_details=False
        , force=False):
        good_ones = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            executor.map(lambda m : self.post_process_one(m, search_name=search_name, get_details=get_details, force=force), matches)

        logging.debug("Done parallel processing")

        for m in tqdm(matches):
        #     m = self.post_process_one(m, search_name=search_name, get_details=get_details, force=force)

            is_good, message = HouseScore.get_house_score_message(m)
            if is_good:
                good_ones = good_ones + 1


        logging.debug("{} Matches={}/{}".format(search_name, good_ones, len(matches)))
        return matches

    @staticmethod
    def _plot_groups(X, y_pred):
        colors = np.array(list(islice(cycle(['#377eb8', '#ff7f00', '#4daf4a',
                                                '#f781bf', '#a65628', '#984ea3',
                                                '#999999', '#e41a1c', '#dede00']),
                                        int(max(y_pred) + 1))))
        plt.scatter(X[:, 0], X[:, 1], s=10, color=colors[y_pred])
        plt.show()

    @staticmethod
    def ClusterHouses(matches, plot_groups=False):
        groups = {}
        try:
            N = len(matches)
            X = np.zeros((N,2))
            for m in range(N):
                loc = RFAPI.house_location(matches[m])
                #logging.debug("ClusterHouses({})".format(loc))
                X[m] = (loc[0], loc[1])

            params = {  'quantile': .3,
                        'eps': .15,
                        'damping': .9,
                        'preference': -5,
                        'n_neighbors': 2,
                        'n_clusters': 5}

            # a bit buggy..
            spectral = cluster.SpectralClustering(
                n_clusters=params['n_clusters'], eigen_solver='arpack',
                affinity="nearest_neighbors")

            # best so far!
            gmm = mixture.GaussianMixture(
                n_components=params['n_clusters'], covariance_type='full')

            # yielded one cluster..
            affinity_propagation = cluster.AffinityPropagation(
                damping=params['damping'], preference=params['preference'])

            bandwidth = cluster.estimate_bandwidth(X, quantile=params['quantile'])
            ms = cluster.MeanShift(bandwidth=bandwidth, bin_seeding=True)

            algorithm = ms

            algorithm.fit(X)
            if hasattr(algorithm, 'labels_'):
                y_pred = algorithm.labels_.astype(np.int)
            else:
                y_pred = algorithm.predict(X)    
            for m in range(len(matches)):
                key = str(y_pred[m])
                if groups.get(key, None) == None:
                    groups[key] = []

                groups[key].append({
                    "adress":RFAPI.house_address(matches[m])
                    , "location":[X[m][0], X[m][1]]
                })
            logging.debug("groups = {}".format(groups))
            if plot_groups:
                HouseScore._plot_groups(X, y_pred)
        except Exception as e:
            groups["error"] = str(e)
            logging.error(groups["error"])
        return groups

    @staticmethod
    def filter_good_houses(houses):
        return [m for m in houses if m['scores'].get("cutoff") is None]

    @staticmethod
    def add_html_tab(tab_id, tab_name, tab_content, tabs):
        is_first_tab = False
        tab_template = '<button class="tablinks {2}" onclick="openTab(event, \'{0}\')">{1}</button>'
        tab_content_template = '<div id="{0}" class="tabcontent">{1}</div>'

        if tabs is None:
            tabs = {
                "tabs": ['<div class="tab">', '</div>'],
                "contents":[]
            }
            is_first_tab = True

        tabs['tabs'].insert(len(tabs['tabs'])-1, tab_template.format(tab_id, tab_name, 'defaultOpen' if is_first_tab else ""))
        tabs['contents'].append(tab_content_template.format(tab_id, tab_content))
        return tabs

    @staticmethod
    def get_house_summary(house, rank=0):
            score = house.get("scores")
            if score is None:
                logging.warning("score is missing for {}".format(house))
                return {}
            first_listed = datetime.datetime.today() - datetime.timedelta(days=score["history"]["value"])
            house_summary = {
                     "Address":score["facts"]["full_address"]
                    , "score":score["value"]["value"]
                    , "distance":score["distance"]["value"]
                    , "County":score["facts"]["County"]
                    , "Year Build":score["facts"]["build"]
                    , "beds":score["facts"]["beds"]
                    , "baths":score["facts"]["baths"]
                    , "price":score["facts"]["price"]
                    , "sqft":score["facts"]["sqft"]
                    , "lot size":score["facts"]["sqft"]+score["backyard"]["value"]
                    , "first_listed":first_listed.strftime("%m/%d/%Y")
                    , "dom":score["history"]["message"]
                    , "url":"http://www.redfin.com{}".format(house["URL"])
                    , "picture":score["facts"]["photo"]
                    , "price_for_sf":score["facts"]["price"] / score["facts"]["sqft"] if score["facts"]["sqft"] > 0 else 0.0
                    , "user_rank":rank
                }
            return house_summary

    @staticmethod
    def get_houses_category_html(houses, summary="", category_id=""):
        html_content = []
        #logging.debug("houses {}".format(len(houses)))
        even_raw = False
        house_id = 0
        for house in houses:
            house_id += 1

            even_raw = not even_raw
            score = house.get("scores")
            if score is None:
                logging.warning("score is missing for {}".format(house))
                continue
            house_summary_raw = HouseScore.get_house_summary(house)
            house_summary = {
                  "Address":house_summary_raw["Address"]
                , "score":"{:.2f}".format(house_summary_raw["score"])
                , "distance":"{:.2f}".format(house_summary_raw["distance"])
                , "County":house_summary_raw["County"]
                , "Year Build":house_summary_raw["Year Build"]
                , "beds":house_summary_raw["beds"]
                , "baths":house_summary_raw["baths"]
                , "price":house_summary_raw["price"]
                , "sqft":house_summary_raw["sqft"]
                , "lot size":house_summary_raw["lot size"]
                , "dom":house_summary_raw["dom"]
                , "$/sf":"{:.0f}".format(house_summary_raw["price_for_sf"])
            }

            is_good, message = HouseScore.get_house_score_message(house)
            if is_good:
                pass_message = "Good ( score = {:.2f}, distance = {:.2f} )".format(score["value"]["value"], score["distance"]["value"])
            else:
                house_summary["Failed"]="[ {} ]".format(score["cutoff"])
                pass_message = "Failed [ {} ] ( score = {:.2f}, distance = {:.2f} )".format(score["cutoff"], score["value"]["value"], score["distance"]["value"])

            house_summary_html = DicToTHML(house_summary)
            score_html = DicToTHML(score)

            # build taps
            tabs = None
            house_group_id = "{}_{}".format(category_id, house_id)
            tabs = HouseScore.add_html_tab(tab_id="summary_{}".format(house_group_id), tab_name="Summary", tab_content=house_summary_html, tabs=tabs)
            tabs = HouseScore.add_html_tab(tab_id="details_{}".format(house_group_id), tab_name="Details", tab_content=score_html, tabs=tabs)

            maps_url = "https://www.google.com/maps/place/{}".format(score["facts"]["full_address"].replace(' ', '+'))
            areavibes_url = "https://www.areavibes.com/{}-{}/livability/".format(
                house['address_data']['city'].replace('-', '+').replace(' ', '+'),
                house['address_data']['state'])
            spotcrime_url="https://spotcrime.com/#{}".format(score["facts"]["full_address"].replace(' ', '%20').replace('-', '%20').replace(',', '%2C'))

            tabs = HouseScore.add_html_tab(tab_id="links_{}".format(house_group_id), tab_name="Links", 
                tab_content="""
                <H3><A href="{}">Map</A></H3>
                <H3><A href="{}">Areavibes</A></H3>
                <H3><A href="{}">SpotCrime</A></H3>
                """.format(maps_url, areavibes_url, spotcrime_url), 
                tabs=tabs)
            #
            #<IFRAME width='100%' height='500' src='https://spotcrime.com/"+spotcrime_sub_path+"'/>"
            tabs_html = "\n".join(tabs['tabs'] + tabs['contents'])
            this_house_report = r"""
        <TR {4}> <!-- draggable="true" //-->
            <TD align="center" valign="top" >
                <TABLE width="100%">
                    <TR><TD colspan="2" width="100%">
                        <H2><A href="http://www.redfin.com{1}">{2}</A></H2>
                    </TD></TR>
                    <TR><TD width="50%" align="center" valign="top" >
                        <A href="http://www.redfin.com{1}"><IMG width="100%" src="{0}" /></A><BR/>
                        <P>Details : {5}</P>
                    </TD><TD align="left" valign="top" width="50%">
                        {3}
                    </TD></TR>
                </TABLE>
            </TD>
        </TR>
                    """.format(
                          score["facts"]["photo"] #0
                        , house["URL"]            #1
                        , score["facts"]["full_address"] #2
                        , tabs_html #3
                        , ('class="one-house-dragable page-break"' if even_raw else 'class="one-house-dragable no-page-break"') #4
                        , pass_message
                    )

            html_content.append(this_house_report)

        if len(html_content) == 0:
            return ""

        category_template = """
        <H1>{$SUMMARY}</H1>
        <BR/>
        <TABLE width="90%" align="center" valign="top">
            {$ACCORDION_TEMPLATE_BODY}
        </TABLE>
        """

        category_template = category_template.replace("{$SUMMARY}", summary)
        category_template = category_template.replace("{$ACCORDION_TEMPLATE_BODY}", "\n".join(html_content))

        return category_template

    @staticmethod
    def search_for_range(matches, active_only=True, min_price=0, max_price=7600000, only_good=True):
        good_houses = matches
        if active_only:
            good_houses = [m for m in good_houses if m.get('status') is None or m['status'] == 'Active']
        if only_good:
            good_houses = [m for m in good_houses if m['scores'].get("cutoff") is None]
        good_houses = [m for m in good_houses if m['price'] >= min_price and m['price'] <= max_price]
        sorted_good_houses = HouseScore.sort_by_total_score_vs_price(good_houses)
        return sorted_good_houses

    @staticmethod
    def get_houses_html(houses, title="", active_only=True, only_good=True):
        tabs = None
        filtered_matches = HouseScore.search_for_range(houses, active_only=active_only, min_price=490000, max_price=760000, only_good=only_good)
        tab_content = HouseScore.get_houses_category_html(filtered_matches, category_id="full", summary="Found ( {} / {} ) good houses".format(len(filtered_matches), len(houses)))
        tabs = HouseScore.add_html_tab(tab_id="full_id", tab_name="All Houses", tab_content=tab_content, tabs=tabs)

        filtered_matches = HouseScore.search_for_range(houses, active_only=active_only, min_price=490000, max_price=610000, only_good=only_good)
        tab_content = HouseScore.get_houses_category_html(filtered_matches, category_id="low", summary="Found ( {} / {} ) good houses".format(len(filtered_matches), len(houses)))
        tabs = HouseScore.add_html_tab(tab_id="low_id", tab_name="Low", tab_content=tab_content, tabs=tabs)

        filtered_matches = HouseScore.search_for_range(houses, active_only=active_only, min_price=590000, max_price=710000, only_good=only_good)
        tab_content = HouseScore.get_houses_category_html(filtered_matches, category_id="med", summary="Found ( {} / {} ) good houses".format(len(filtered_matches), len(houses)))
        tabs = HouseScore.add_html_tab(tab_id="med_id", tab_name="Medium", tab_content=tab_content, tabs=tabs)

        filtered_matches = HouseScore.search_for_range(houses, active_only=active_only, min_price=690000, max_price=760000, only_good=only_good)
        tab_content = HouseScore.get_houses_category_html(filtered_matches, category_id="high", summary="Found ( {} / {} ) good houses".format(len(filtered_matches), len(houses)))
        tabs = HouseScore.add_html_tab(tab_id="high_id", tab_name="High", tab_content=tab_content, tabs=tabs)

        with open(os.path.join(SCRIPT_DIR, "report_template.html") , "r") as html_template_stream:
            html_template = html_template_stream.read()

        html_template = html_template.replace("{$TITLE}", title)
        html_template = html_template.replace("{$TABS}", "\n".join(tabs['tabs']))
        html_template = html_template.replace("{$TAB_CONTENTS}", "\n".join(tabs['contents']))
        
        return html_template

    @staticmethod
    def sort_by_total_score_vs_price(good_houses):
        cost_gain = {}
        for m in good_houses:
            gain = m['scores']['value']["money"] - m['scores']['facts']['price']
            gain_percentage = m['scores']['value']["value"]
            if cost_gain.get(gain_percentage) is None:
                cost_gain[gain_percentage] = []
            cost_gain[gain_percentage].append(m)

        sorted_keys = sorted(cost_gain, reverse=True)
        #logging.debug(sorted_keys)
        retVal = []
        for k in sorted_keys:
            for m in cost_gain[k]:
                #m['scores']['gain_percentage'] = k
                retVal.append(m)
        return retVal
        
    def SearchByUrl(self, house_url, get_details=True, force=False, cache_time_format="%Y%m%d"):
        house, details = self.rfapi.get_house_by_url(house_url, force=force, cache_time_format=cache_time_format)
        return self.post_process([house], "SearchByUrl({})".format(house_url), get_details=get_details, force=force)

    def Search(self, search_name, search_json, get_details=False, force=False):
        logging.debug("Search(search_name={}, search_json={}, get_details={}, force={})".format(search_name, search_json, get_details, force))
        matches = self.rfapi.retrieve_json(search_json, force=force)
        return self.post_process(matches, search_name, get_details=get_details, force=force)

    def SearchForZIPCodes(self, search_name, search_json, zip_codes, get_details=False, force=False):
        zip_regions = [self.rfapi.zipcode_to_regionid(zipcode, False) for zipcode in zip_codes]
        # need to convert to region_id
        region_types = [2 for zipcode in zip_codes]
        all_matches = []
        for region in zip_regions:
            search_json["region_id"] = [region]
            matches = self.rfapi.retrieve_json(search_json, force=force)
        all_matches += matches
        return self.post_process(all_matches, search_name, get_details=get_details, force=force)

    @staticmethod
    def LoadFavorits(FavoriteLocationsFile):
        with open(FavoriteLocationsFile, "r") as stream:
            fav = json.load(stream)
            ret = []
            for v in fav:
                if v['importance'] != 0:
                    ret.append(v)
            return ret