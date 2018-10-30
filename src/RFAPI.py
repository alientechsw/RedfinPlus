import os
import hashlib
import urllib
import urllib2
import StringIO
import logging
import json
import csv
#from copy import copy
from utils import UrlCache, AddressToLocation, MS_IN_A_DAY

# TODO: create a wrapper class for the house concept to group commong tasks of getting and cleaning data
class House(object):
    def __init__(self
        , house_info
        , house_details
        , in_dic = {}):
        super(House, self).__init__()
        self.info = house_info
        self.details = house_details
        self.__dict__.update(in_dic)


class RFAPI(object):
    SEARCH_URL = 'https://www.redfin.com/stingray/do/gis-search'
    REGION_URL = 'https://www.redfin.com/stingray/api/region'
    
    INITIAL_INFO_URL = "http://www.redfin.com/stingray/api/home/details/initialInfo"

    PROPERTY_DETAILS_2_URL = 'https://www.redfin.com/stingray/api/home/details/belowTheFold'
    NEIGHBORHOOD_URL = "https://www.redfin.com/stingray/api/home/details/neighborhoodStats/statsInfo"
    PROPERTY_INFO_URL = "https://www.redfin.com/stingray/api/home/details/mainHouseInfoPanelInfo"
    PROPERTY_DETAILS_1_URL = "https://www.redfin.com/stingray/api/home/details/aboveTheFold"
    PROPERTY_DETAILS = [PROPERTY_INFO_URL, NEIGHBORHOOD_URL, PROPERTY_DETAILS_1_URL, PROPERTY_DETAILS_2_URL]

    SEARCH_PARAMS = {
        "status":1,
        "render":"csv",
        "region_id":29439,
        "uipt":1,
        "sp":True,
        "al":3,
        "lpp":50,
        "region_type":6,
        #"mpt":99,
        "page_number":1,
        "v":8,
        #"no_outline":False,
        "num_homes":500,
        "min_price":500000,
        "max_price":760000,
        "min_num_beds":3,
        "min_num_baths":2,
        #"min_stories":2,
        #"gar":True,
        "min_num_park":2
    }

    def __init__(
        self,
        cahe_folder=None
    ):
        self.cahe = UrlCache(cahe_folder)

    def csv_to_dict(self, csv_file, force=False, cache_time_format="%Y%m%d"):
        result_sets = []
        with open(csv_file, "r") as csv_f:
            reader = csv.reader(csv_f, delimiter=',')
            header = []
            while len(header) == 0:
                header = reader.next()
            for row in reader:
                ds = {
                    "address_data": {
                        "undisclosed":False
                    },
                    "parcel":{}
                }
                for v in range(len(header)):
                    h = header[v].lower()
                    if len(row[v]) == 0:
                        ds[h] = None
                    elif "address" in h:
                        ds["address_data"]["display"] = row[v]
                    elif "city" in h:
                        ds["address_data"]["city"] = row[v]
                    elif "state" in h:
                        ds["address_data"]["state"] = row[v]
                    elif "zip" in h:
                        ds["address_data"]["zip"] = row[v]
                    # elif "mls" in h:
                    #     ds["sale_listing_id"] = int(row[v])
                    elif "days on market" in h:
                        ds["dom"] = int(row[v])
                    elif "longitude" in h:
                        ds["parcel"]["longitude"] = row[v]
                    elif "latitude" in h:
                        ds["parcel"]["latitude"] = row[v]
                    elif 'square feet' == h:
                        ds["sqft"] = int(row[v])
                    elif 'lot size' == h:
                        ds["lotsize"] = float(row[v])
                    elif 'beds' == h:
                        ds["beds"] = int(row[v])
                    elif 'baths' == h:
                        ds["baths"] = float(row[v])
                    elif 'year built' in h:
                        ds["year_built"] = int(row[v])
                    elif 'price' in h:
                        ds["price"] = long(row[v])
                    elif 'url' in h:
                        ds["URL"] = row[v].replace("http://www.redfin.com", "")
                        ds["property"] = { "id": int(ds["URL"].split("/")[-1]) }
                        house_info = self.get_house_initial_inf_by_url(ds["URL"], force=force, cache_time_format=cache_time_format)
                        ds["sale_listing_id"] = 0
                        if house_info["payload"].get("listingId") is not None:
                            ds["sale_listing_id"] = int(house_info["payload"].get("listingId"))
                    else:
                        ds[h] = row[v]
                result_sets.append(dict(ds))
        return result_sets

    @staticmethod
    def house_address(house):
        if house["address_data"] is not None and house["address_data"]["undisclosed"] == False:
            streat_address = house["address_data"]["display"]
            city = house["address_data"]["city"]
            state = house["address_data"]["state"]
            zip_code = house["address_data"]["zip"]
            return "{}, {}, {} {}".format(streat_address, city, state, zip_code)
        return ""

    @staticmethod
    def house_address_parts(house):
        if house["address_data"] is not None:
            ha = house["address_data"]
            undisclosed = ha["undisclosed"] == True or ha.get('number') is None or ha.get('street') is None
            return {
                  "suffix": "" if undisclosed else (ha['suffix'] if ha.get('suffix') is not None else (ha['prefix'] if ha.get('prefix') is not None else ''))
                , "number": "" if undisclosed else ha['number']
                , "street": "" if undisclosed else ha["street"]
                , "unitValue": "" if undisclosed else ha["unitValue"] if ha.get('unitValue') is not None else ""
                , "unitType": "" if undisclosed else ha["unitType"] if ha.get('unitType') is not None else ""
                , "display": "" if undisclosed else ha["display"]
                , "city": ha["city"]
                , "state": ha["state"]
                , "type": "" if undisclosed else (ha['type'] if ha.get('type') is not None else ( "Street" if " st" in ha["street"].lower() else ""))
                , "zip": ha["zip"]}
        return {}

    @staticmethod
    def house_neighborhoods(house, details):
        neighborhoods = []
        if details.get("payload") is not None and details.get("payload").get("neighborhoodData") is not None:
            for n in details["payload"]["neighborhoodData"]["regionStats"]:
                if n["regionType"] in [1, 6]: # 1:neighborhood, 6:city
                    if str(n["name"]) not in neighborhoods:
                        neighborhoods.append(str(n["name"]))
        return neighborhoods

    @staticmethod
    def house_county(house, details):
        if details is not None:
            if details.get("payload") is not None:
                if details.get("payload").get("publicRecordsInfo") is not None:
                    if details.get("payload").get("publicRecordsInfo").get("countyName") is not None:
                        return details["payload"]["publicRecordsInfo"]["countyName"]

        return "n/a"

    @staticmethod
    def house_photo_url(house, details):
        if details is not None:
            if details.get("payload") is not None:
                if details.get("payload").get("preloadImageUrl") is not None:
                    return details["payload"]["preloadImageUrl"]

        return ""

    @staticmethod
    def house_location(house):
        if house.get("parcel") is not None:
            if house.get("parcel").get("longitude") is not None:
                return [ house["parcel"]["latitude"], house["parcel"]["longitude"] ]
            if house.get("parcel").get("unmappedLongitude") is not None:
                return [ house["parcel"]["unmappedLatitude"], house["parcel"]["unmappedLongitude"] ]
        house_address = RFAPI.house_address(house)
        if house_address != "":
            return AddressToLocation(house_address)
        return []

    def get_house_initial_info(self, house, force=False, cache_time_format="%Y%m%d"):
        if house.get('URL') is None:
            return { "payload":{} }
        return self.get_house_initial_inf_by_url(house['URL'], force=force, cache_time_format=cache_time_format)

    def get_house_initial_inf_by_url(self, house_url, force=False, cache_time_format="%Y%m%d"):
        if house_url is None or len(house_url) == 0:
            return { "payload":{} }
        initial_info_url = "{}?path={}".format(RFAPI.INITIAL_INFO_URL, house_url)
        json_str = self.cahe.GetWithErrorHandling(url=initial_info_url, force=force, cache_time_format=cache_time_format, save_error=False)[len(r"{}&&"):]
        try:
            as_json = json.loads(json_str)    
        except Exception as e:
            logging.error("loads failed : {}, error = {}".format(json_str, str(e)))
            as_json = None
        return as_json

    def get_house_listing_id(self, house, force=False, cache_time_format="%Y%m%d"):
        if house.get("sale_listing_id") is not None:
            house_url = RFAPI.generate_url_for_house(house)
            house_info = self.get_house_initial_inf_by_url(house_url, force=force, cache_time_format=cache_time_format)
            if house_info["payload"].get("listingId") is not None:
                house["sale_listing_id"] = house_info["payload"].get("listingId")
        return house.get("sale_listing_id")

    def get_house_by_url(self, house_url, force=False, cache_time_format="%Y%m%d"):
        house_url = house_url.replace("http://www.redfin.com", "")
        house_url = house_url.replace("https://www.redfin.com", "")

        house_info = self.get_house_initial_inf_by_url(house_url, force=force, cache_time_format=cache_time_format)
        sale_listing_id=house_info["payload"]["listingId"] if house_info["payload"].get("listingId") is not None else 0
        house_details = self.get_house_details_by_id(property_id=house_info["payload"]["propertyId"], sale_listing_id=sale_listing_id, force=force, cache_time_format=cache_time_format)
        house_details["payload"].update(house_info["payload"])
        house = self.get_house_info_from_details(house_details)
        return (house, house_details)

    def get_house_details(self, house, force=False, cache_time_format="%Y%m%d"):
        if house.get("property") is None or house.get("property").get("id") is None: return {}
        retVal = self.get_house_details_by_id(property_id=house["property"]["id"], sale_listing_id=house["sale_listing_id"], force=force, cache_time_format=cache_time_format)
        initial_info = self.get_house_initial_info(house, force=force, cache_time_format=cache_time_format)
        retVal["payload"].update(initial_info["payload"])
        return retVal

    @staticmethod
    def clean_house_address(address_short):
        address_short = address_short.replace(' ', '-')
        address_short = address_short.replace('(', '')
        address_short = address_short.replace(')', '')
        return address_short

    @staticmethod
    def generate_url_for_house(house):
        ap = RFAPI.house_address_parts(house)

        unit_str = "" if len(ap['unitValue']) == 0 else "/{}{}".format(ap['unitType'], ap['unitValue'])
        address_short = RFAPI.clean_house_address(house['address_data']['display'])

        retVal = "/{}/{}/{}-{}{}/home/{}".format(ap["state"], RFAPI.clean_house_address(ap["city"]), address_short, ap["zip"], unit_str
            , house["property"]["id"] if house.get('property') is not None else "")
        if house.get('URL') is not None and retVal != house['URL']:
            logging.debug("generate_url_for_house failed, actual = 'http://www.redfin.com{}' expected = 'http://www.redfin.com{}'".format(retVal, house['URL']))
        return retVal

    def get_house_details_by_id(self, property_id, sale_listing_id, force=False, cache_time_format="%Y%m%d"):
        override = { "propertyId":property_id, "accessLevel":3, "type":"json", "listingId":sale_listing_id }
        retVal = { "payload": {} }
        for url in RFAPI.PROPERTY_DETAILS:
            property_details_url = UrlCache.BuildURL(url, override)
            json_str = self.cahe.GetWithErrorHandling(url=property_details_url, force=force, cache_time_format=cache_time_format, save_error=False)[len(r"{}&&"):]
            as_json = json.loads(json_str)
            retVal["payload"].update(as_json["payload"])
        
        return retVal

    def get_house_by_id(self, property_id, sale_listing_id, force=False):
        pass

    def get_house_info_from_details(self, house_details):
        return {
            "address_data": {
                "undisclosed":False,
                "streetNumber":house_details['payload']['mainHouseInfo']['propertyAddress']['streetName'],
                "street":house_details['payload']['mainHouseInfo']['propertyAddress']['streetName'],
                "type":house_details['payload']['mainHouseInfo']['propertyAddress']['streetType'],
                "display":house_details['payload']['mainHouseInfo']['streetAddress'],
                "city":house_details['payload']['mainHouseInfo']['propertyAddress']['city'],
                "state":house_details['payload']['mainHouseInfo']['propertyAddress']['stateCode'],
                "zip":house_details['payload']['mainHouseInfo']['propertyAddress']['zip']
            },
            "price":house_details['payload']['addressSectionInfo']['priceInfo']['amount'],
            "dom":0 if house_details['payload']['addressSectionInfo'].get("timeOnRedfin") is None else float(house_details['payload']['addressSectionInfo']["timeOnRedfin"]) / MS_IN_A_DAY,
            "beds":house_details['payload']['addressSectionInfo']['beds'],
            "baths":house_details['payload']['addressSectionInfo']['baths'],
            "sqft":house_details['payload']['addressSectionInfo']['sqFt']['value'],
            "lotsize":0 if house_details['payload']['addressSectionInfo'].get("lotSize") is None else house_details['payload']['addressSectionInfo']['lotSize'],
            "year_built":house_details['payload']['addressSectionInfo']['yearBuilt']
            , "parcel":{
                 "latitude":house_details['payload']['addressSectionInfo']['latLong']['latitude']
                ,"longitude":house_details['payload']['addressSectionInfo']['latLong']['longitude']}
            , "URL":house_details['payload']['mainHouseInfo']['url']
            , "property": { "id":house_details["payload"]["propertyId"] }
            , "sale_listing_id":0 if house_details['payload'].get("listingId") is None else house_details["payload"]["listingId"]
        }

    def zipcode_to_regionid(self, zip_code, force=False):
        override = {
            "region_id":zip_code,
            "region_type":2,
            "tz":True,
            "v":8
        }
        region_url = UrlCache.BuildURL(RFAPI.REGION_URL, override)
        json_str = self.cahe.Get(url=region_url, force=force, cache_time_format="")[len(r"{}&&"):]
        as_json = json.loads(json_str)
        return as_json["payload"]["rootDefaults"]["region_id"]

    def retrieve_raw(self, override, force=False):
        params = dict(RFAPI.SEARCH_PARAMS, **override)
        SEARCH_URL = UrlCache.BuildURL(RFAPI.SEARCH_URL, params)
        raw_str = self.cahe.Get(url=SEARCH_URL, force=force)
        return raw_str

    def retrieve_json(self, override, force=False):
        json_str = self.retrieve_raw(override, force)[len(r"{}&&"):]
        logging.debug("retrieve_json => {}".format(json_str))
        as_json = json.loads(json_str)
        return as_json["payload"]["search_result"]

    def retrieve_csv(self, override, force=False):
        csv_str = self.retrieve_raw(override, force)
        csv_f = StringIO.StringIO(csv_str)
        reader = csv.reader(csv_f, delimiter=',')
        header = []
        result_sets = []
        while len(header) == 0:
            header = reader.next()
        for row in reader:
            ds = zip(header, row)
            result_sets.append(dict(ds))
        return result_sets