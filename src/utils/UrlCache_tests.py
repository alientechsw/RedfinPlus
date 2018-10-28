#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import logging
import json
import csv
import unittest
from UrlCache import UrlCache, CheckCache

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CACHE_PATH = os.path.join(SCRIPT_DIR, '.cache')

class UrlCache_tests(unittest.TestCase):
    def test_google_dot_com_forced(self):
        url = "http://www.google.com"
        urlCache = UrlCache(cache_time_format="")
        results = urlCache.GetWithErrorHandling(url, force=True)
        self.assertIsNotNone(results)
        self.assertNotEqual(len(results), 0)

    def test_google_dot_com_cached(self):
        url = "http://www.google.com"
        urlCache = UrlCache(cache_time_format="")
        forced_results = urlCache.GetWithErrorHandling(url, force=True)
        self.assertIsNotNone(forced_results)
        self.assertNotEqual(len(forced_results), 0)

        cached_results = urlCache.GetWithErrorHandling(url, force=False)
        self.assertIsNotNone(cached_results)
        self.assertNotEqual(len(cached_results), 0)
        self.assertEqual(cached_results, forced_results)

class CheckCache_tests(unittest.TestCase):
    def test_simple(self):
        with CheckCache("test", forced=True, cahe_folder=CACHE_PATH, cache_time_format="") as cache_check_forced:
            if cache_check_forced.content is not None:
                self.fail("forced is turned on, content should be None")

            cache_check_forced.content = "test"
        with CheckCache("test", forced=False, cahe_folder=CACHE_PATH, cache_time_format="") as cache_check:
            if cache_check.content is None:
                self.fail("\"test\" Should be in cache")

    def test_UrlCache_integration(self):
        url = "http://www.google.com"
        urlCache = UrlCache(cache_time_format="")
        with CheckCache(url, forced=True, cahe_folder=CACHE_PATH, cache_time_format="") as cache_check_forced:
            if cache_check_forced.content is not None:
                self.fail("forced is turned on, content should be None")

            cache_check_forced.content = urlCache.GetWithErrorHandling(url, force=True)
        with CheckCache(url, forced=False, cahe_folder=CACHE_PATH, cache_time_format="") as cache_check:
            if cache_check.content is None:
                self.fail("\"{}\" Should be in cache".format(url))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.exists(CACHE_PATH):
        os.mkdir(CACHE_PATH)
    unittest.main()