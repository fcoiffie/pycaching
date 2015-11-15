#!/usr/bin/env python3

# import os
import unittest
import pycaching
import itertools
import tempfile
import os
import json
from geopy.distance import great_circle
from pycaching import Geocaching, Point, Rectangle
from pycaching.errors import NotLoggedInException, LoginFailedException, PMOnlyException


# please DO NOT CHANGE!
_username, _password = "cache-map", "pGUgNw59"


class TestMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.g = Geocaching()
        cls.g.login(_username, _password)

    def test_search(self):
        with self.subTest("normal"):
            expected = ["GC41FJC", "GC17E8Y", "GC5ND9F"]
            caches = self.g.search(Point(49.733867, 13.397091), 3)
            for cache in caches:
                self.assertIn(cache.wp, expected)

        with self.subTest("pagging"):
            caches = list(self.g.search(Point(49.733867, 13.397091), 100))
            self.assertNotEqual(caches[0], caches[50])

    def test_search_quick(self):
        """Perform search and check found caches"""
        # at time of writing, there were exactly 16 caches in this area + one PM only
        expected_cache_num = 16
        rect = Rectangle(Point(49.73, 13.38), Point(49.74, 13.40))

        with self.subTest("normal"):
            res = [c.wp for c in self.g.search_quick(rect)]
            for wp in ["GC41FJC", "GC17E8Y", "GC5ND9F"]:
                self.assertIn(wp, res)
            # but 108 caches larger tile
            self.assertLess(len(res), 130)
            self.assertGreater(len(res), 90)

        with self.subTest("strict handling of cache coordinates"):
            res = list(self.g.search_quick(rect, strict=True))
            self.assertLess(len(res), expected_cache_num + 5)
            self.assertGreater(len(res), expected_cache_num - 5)

        with self.subTest("larger zoom - more precise"):
            res1 = list(self.g.search_quick(rect, strict=True, zoom=15))
            res2 = list(self.g.search_quick(rect, strict=True, zoom=14))
            for res in res1, res2:
                self.assertLess(len(res), expected_cache_num + 5)
                self.assertGreater(len(res), expected_cache_num - 5)
            for c1, c2 in itertools.product(res1, res2):
                self.assertLess(c1.location.precision, c2.location.precision)

    def test_search_quick_match_load(self):
        """Test if search results matches exact cache locations."""
        rect = Rectangle(Point(49.73, 13.38), Point(49.74, 13.39))
        caches = list(self.g.search_quick(rect, strict=True, zoom=15))
        for cache in caches:
            try:
                cache.load()
                self.assertIn(cache.location, rect)
            except PMOnlyException:
                pass


class TestLoginOperations(unittest.TestCase):

    def setUp(self):
        self.g = Geocaching()

    def test_request(self):
        with self.subTest("login needed"):
            with self.assertRaises(NotLoggedInException):
                self.g._request("/")

    def test_login(self):
        with self.subTest("bad username"):
            with self.assertRaises(LoginFailedException):
                self.g.login("0", "0")

        with self.subTest("good username"):
            self.g.login(_username, _password)

        with self.subTest("good username already logged"):
            self.g.login(_username, _password)

        with self.subTest("bad username automatic logout"):
            with self.assertRaises(LoginFailedException):
                self.g.login("0", "0")

    def test_get_logged_user(self):
        self.g.login(_username, _password)
        self.assertEqual(self.g.get_logged_user(), _username)

    def test_logout(self):
        self.g.login(_username, _password)
        self.g.logout()
        self.assertIsNone(self.g.get_logged_user())

    def test_load_credentials(self):
        filename_backup = self.g._credentials_file
        credentials = {"username": _username, "password": _password}
        empty_valid_json = {}
        nonsense_str = b"ss{}ef"        

        with self.subTest("Try to load nonexistent file from current directory"):
            self.g._credentials_file = "this_file_doesnt_exist.json"
            with self.assertRaises(LoginFailedException):
                username, password = self.g._load_credentials()

        with self.subTest("Try to load valid credentials from current directory"):
            valid = tempfile.NamedTemporaryFile(suffix='.json', prefix='gc_cred_valid_', dir='./', delete=False)
            valid.write(json.dumps(credentials).encode())
            valid.close()
            self.g._credentials_file = os.path.basename(valid.name)
            username, password = self.g._load_credentials()
            self.assertEqual(_username, username)
            self.assertEqual(_password, password)
        try:
            os.remove(valid.name)
        except:
            pass

        with self.subTest("Try to load empty file from current directory"):
            empty = tempfile.NamedTemporaryFile(suffix='.json', prefix='gc_cred_empty_', dir='./', delete=False)
            empty.write(json.dumps(empty_valid_json).encode())
            empty.close()
            self.g._credentials_file = os.path.basename(empty.name)
            with self.assertRaises(LoginFailedException):
                username, password = self.g._load_credentials()
        try:
            os.remove(empty.name)
        except:
            pass

        with self.subTest("Try to load nonsense file from current directory"):
            nonsense = tempfile.NamedTemporaryFile(suffix='.json', prefix='gc_cred_nonsense_', dir='./', delete=False)
            nonsense.write(nonsense_str)
            nonsense.close()
            self.g._credentials_file = os.path.basename(nonsense.name)
            with self.assertRaises(LoginFailedException):
                username, password = self.g._load_credentials()
        try:
            os.remove(nonsense.name)
        except:
            pass

        with self.subTest("Try to load valid credentials from home directory"):
            home_file = tempfile.NamedTemporaryFile(suffix='.json', prefix='gc_cred_', dir=os.path.expanduser("~"), delete=False)
            home_file.write(json.dumps(credentials).encode())
            home_file.close()
            self.g._credentials_file = os.path.basename(home_file.name)
            username, password = self.g._load_credentials()
            self.assertEqual(_username, username)
            self.assertEqual(_password, password)
        try:
            os.remove(home_file.name)
        except:
            pass

        self.g._credentials_file = filename_backup

class TestShortcuts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.g = Geocaching()
        cls.g.login(_username, _password)

    def test_login(self):
        pycaching.login(_username, _password)

    def test_geocode(self):
        ref_point = Point(49.74774, 13.37752)
        self.assertLess(great_circle(self.g.geocode("Pilsen"), ref_point).miles, 10)

    def test_get_cache(self):
        c = self.g.get_cache("GC4808G")
        self.assertEqual("Nekonecne ticho", c.name)

    def test_get_trackable(self):
        t = self.g.get_trackable("TB1KEZ9")
        self.assertEqual("Lilagul #2: SwedenHawk Geocoin", t.name)

    def test_post_log(self):
        # I refuse to write 30 lines of tests (mocking etc.) because of simple 2 lines of code
        pass
