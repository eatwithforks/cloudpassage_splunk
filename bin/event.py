#!/usr/bin/python
# -*- coding: utf-8 -*-
import multiprocessing
import copy_reg
import types
import datetime
import os
import signal
import json
from functools import partial
import settings as settings
import cloudpassage
import cputils as cputils

def _pickle_method(message):
    if message.im_self is None:
        return getattr, (message.im_class, message.im_func.func_name)
    else:
        return getattr, (message.im_self, message.im_func.func_name)

copy_reg.pickle(types.MethodType, _pickle_method)


class Event(object):
    """Initializing Event

        Args:
        key_id: Halo API key_id
        secret_key: Halo API secret key
    """

    def __init__(self, key_id, secret_key):
        self.event_id_exist = True
        self.key_id = key_id
        self.secret_key = secret_key
        self.base_url = 'https://api.cloudpassage.com'

    # def create_halo_session_object(self):
    #     """create halo session object"""
    #     api_con = cpapi.CPAPI()
    #     api_con.key_id = self.key_id
    #     api_con.secret = self.secret_key
    #     return api_con
    def create_halo_session_object(self):
        session = cloudpassage.HaloSession(self.key_id, self.secret_key)
        return session

    # def get(self, per_page, date, page):
    #     """get events from Halo"""

    #     api = self.create_halo_session_object()
    #     token = api.authenticateClient()
    #     url = "v1/events?per_page=%s&page=%s&since=%s" % (per_page,
    #                                                        page,
    #                                                        date)

    #     resp = api.doGetRequest("https://api.cloudpassage.com/%s" % (url), token)
    #     return json.loads(resp[0])

    def get(self, per_page, date, page):
        """HTTP GET events from Halo"""

        session = self.create_halo_session_object()
        api = cloudpassage.HttpHelper(session)
        url = "/v1/events?per_page=%s&page=%s&since=%s" % (per_page,
                                                           page,
                                                           date)
        return api.get(url)

    # def latest_event(self, per_page, date, page):
    #     """get the latest event from Halo"""

    #     api = self.create_halo_session_object()
    #     token = api.authenticateClient()
    #     url = "v1/events?sort_by=created_at.desc&per_page=%s&page=%s&since=%s" % (per_page,
    #                                                                                page,
    #                                                                                date)
    #     resp = api.doGetRequest("https://api.cloudpassage.com/%s" % (url), token)
    #     return json.loads(resp[0])
    def latest_event(self, per_page, date, page):
        """get the latest event from Halo"""

        session = self.create_halo_session_object()
        api = cloudpassage.HttpHelper(session)
        url = "/v1/events?sort_by=created_at.desc&per_page=%s&page=%s&since=%s" % (per_page,
                                                                                   page,
                                                                                   date)
        return api.get(url)

    def interrupt_handler(self, signum, frame):
        """interruptHandler"""

        print "Beginning shutdown..."

    def init_worker(self):
        """init_worker"""

        signal.signal(signal.SIGINT, self.interrupt_handler)

    def batch(self, date):
        """multiprocessing to get all the events"""

        batched = []
        mpool = multiprocessing.Pool(settings.threads(), self.init_worker)
        paginations = list(range(1, settings.pagination_limit() + 1))
        per_page = str(settings.per_page())

        try:
            partial_get = partial(self.get, per_page, date)
            data = mpool.map(partial_get, paginations)
            for i in data:
                batched.extend(i["events"])
            return batched
        except KeyboardInterrupt:
            print "Caught KeyboardInterrupt, terminating workers"
            mpool.terminate()
            mpool.join()

    def historical_limit_date(self):
        """get historical_limit_date (90 days)"""

        historical_limit = settings.historical_limit()
        temp = (datetime.datetime.now() - datetime.timedelta(days=historical_limit))
        date = temp.strftime('%Y-%m-%d')
        return date

    def sort_by(self, data, param):
        """ sorting the events data"""

        sort_data = sorted(data, key=lambda x: x[param])
        return sort_data

    def get_end_date(self, dates, end_date):
        """find the end date of each events batch"""

        if end_date != self.historical_limit_date:
            return dates[-1]["created_at"]
        date_obj = cputils.strToDate(dates[-1]["created_at"])
        return date_obj.strftime('%Y-%m-%d')

    def id_exists_check(self, data, event_id):
        """check event id exist"""
        return any(k['id'] == event_id for k in data)

    def loop_date(self, batched, end_date):
        """grab starting date for the next event batch"""

        sorted_data = self.sort_by(batched, "created_at")
        start_date = sorted_data[0]["created_at"]
        end_date = self.get_end_date(sorted_data, end_date)
        return start_date, end_date

    def retrieve_events(self, checkpoint_stamp):
        """retrieve events"""
        end_date = checkpoint_stamp
        initial_event_id = self.latest_event("1", "", "1")["events"][0]["id"]
        while self.event_id_exist:
            batched = self.batch(end_date)
            start_date, end_date = self.loop_date(batched, end_date)
            if self.id_exists_check(batched, initial_event_id):
                self.event_id_exist = False
                return self.event_id_exist
