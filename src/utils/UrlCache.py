#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import hashlib
import urllib
import urllib2
import datetime
import logging
import csv
import socket
import time
import math
from random import randint
from fake_useragent import UserAgent

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
CACHE_PATH = os.path.join(SCRIPT_PATH, '.cache')

class UrlCache(object):
    """
    This class wraps urllib calls, and caches these calls locally.

    You can bypass the cache with `forced` argument. 
    
    The class doesn't clean the cache so it can graw out of control. I used it to track the history
    or particular page. The page is appended with cache expiration signature like cache_time_format="%Y%m%d"
    will expire the cache every day. You could use cache_time_format="" for permininat cached urls.
    """
    ERR_STR = "Error "

    def __init__(self, cahe_folder=CACHE_PATH, cache_time_format="%Y%m%d"):
        if cahe_folder is None:
            cahe_folder = CACHE_PATH
        if not os.path.exists(cahe_folder):
            os.mkdir(cahe_folder)

        self.cahe_folder = cahe_folder

    def _check_cache(self, enc_url, reload_failed=False):
        if self.cahe_folder is None: return None
        content = None
        cache_file = os.path.join(self.cahe_folder, enc_url)
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as content_file:
                content = content_file.read()

            if content is None or UrlCache.ERR_STR in content or ":404," in content:
                logging.error("error in cache {} => {}".format(enc_url, content))
                if reload_failed:
                    logging.debug("attempting reload")
                    return None
            else:
                logging.debug("found in cache {}".format(enc_url))

        return content

    def _add_cache(self, enc_url, content):
        if self.cahe_folder is None: return
        cache_file = os.path.join(self.cahe_folder, enc_url)
        with open(cache_file, 'w') as content_file:
            logging.debug("adding to cache {}".format(enc_url))
            content_file.write(content)

    @staticmethod
    def GetCacheKey(url, cache_time_format="%Y%m%d"):
        ts_now = datetime.datetime.now()
        ts = ts_now.strftime(cache_time_format)

        hash_object = hashlib.md5(url)
        enc_request = hash_object.hexdigest()
        return enc_request + ts

    @staticmethod
    def GetAgentHeader():
        ua = UserAgent()
        ua.update
        user_agent = ua.chrome # ua.random
        headers = { 'User-Agent': user_agent }
        return headers
        
    @staticmethod
    def BuildURL(url, params={}):
        url_params = urllib.urlencode(params, doseq=True)
        url = "%s?%s" % (url, url_params)
        #logging.debug("url={}".format(url))
        return url

    def GetWithErrorHandling(self, url, headers=None, force=False, cache_time_format="%Y%m%d", sleep_on_download=-1, save_error=True, reload_failed=False):
        if sleep_on_download < 0:
            sleep_on_download = randint(0, 2)
        for trial in range(3):
            try:
                html_str = self.Get(url=url, headers=headers, force=force, cache_time_format=cache_time_format, sleep_on_download=sleep_on_download, reload_failed=reload_failed)
                return html_str
            except urllib2.HTTPError, error:
                logging.error("{} : HTTPError ({}) = {}".format(url, trial, error))
                error_message = error
                break
            except socket.error, error:
                logging.error("{} : socket error ({}) = {}".format(url, trial, error))
                error_message = error
                time.sleep(5)
                continue
            except urllib2.URLError, error:
                logging.error("{} : URLError error ({}) = {}".format(url, trial, error))
                error_message = error
                time.sleep(5)
                continue
        if save_error:
            if UrlCache.ERR_STR not in error_message:
                error_message = "{} : {} = {}".format(url, UrlCache.ERR_STR, error_message)
            enc_url = UrlCache.GetCacheKey(url, cache_time_format)
            self._add_cache(enc_url, error_message)

        return error_message

    def Get(self, url, headers=None, force=False, cache_time_format="%Y%m%d", sleep_on_download=0, reload_failed=False):
        logging.debug("getting url = {}".format(url))
        if headers is None:
            headers = UrlCache.GetAgentHeader()
        enc_url = UrlCache.GetCacheKey(url, cache_time_format)
        ret = self._check_cache(enc_url, reload_failed=reload_failed)
        if ret is not None and force==False:
            return ret
        req = urllib2.Request(url, headers=headers)
        time.sleep(sleep_on_download)
        browse = urllib2.urlopen(req)
        content = browse.read()
        self._add_cache(enc_url, content)
        return content

class CheckCache(object):
    def __init__(self, url, forced=False, cahe_folder=CACHE_PATH, cache_time_format="%Y%m%d"):
        super(CheckCache, self).__init__()
        self.url = url
        self.cahe_folder = cahe_folder
        self.enc_url = UrlCache.GetCacheKey(self.url, cache_time_format=cache_time_format)
        self.content = None
        self.cache_file = os.path.join(self.cahe_folder, self.enc_url)
        self.forced = forced
        self.need_save = True

    def __enter__(self):
        if os.path.exists(self.cache_file) and not self.forced:
            with open(self.cache_file, 'r') as content_file:
                logging.debug("found in cache {}".format(self.enc_url))
                self.need_save = False
                self.content = content_file.read()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.content is not None and self.need_save:
            with open(self.cache_file, "w") as report:
                logging.debug("write to cache {}".format(self.enc_url))
                report.write(self.content)
        return False # process exceptions normally

