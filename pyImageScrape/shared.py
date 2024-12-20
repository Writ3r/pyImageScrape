#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pathlib
import io

from abc import ABC, abstractmethod

def get_current_folder(file):
    return str(pathlib.Path(file).parent.absolute())

class FileStorage(ABC):

    @abstractmethod
    def store_file(self, bytes:bytes, path:str):
        """stores files to some impl"""

class ScrapeJobProducer(ABC):

    @abstractmethod
    def run_producer(self):
        """runs the producer for Scrape jobs"""

class UrlScrapeJobConsumer(ABC):

    @abstractmethod
    def scrape_url(self, url):
        """executes a scrape attempt on the provided URL"""

class DataStore(ABC):

    @abstractmethod
    def add_to_visit_content_urls(self, urlLocs):
        """add multiple content urls to visit"""
        pass

    @abstractmethod
    def add_to_visit_pic_urls(self, urlLocs):
        """add multiple pic urls to visit"""
        pass

    @abstractmethod
    def add_visited_content_url(self, urlLoc, err = None):
        """tag content url as visited"""
        pass

    @abstractmethod
    def add_visited_pic_url(self, urlLoc, err = None):
        """tag pic url as visited"""
        pass

    @abstractmethod
    def add_stored_pic_url(self, urlLoc, filePath, shaPicHash):
        """store a picture from a url"""
        pass

    @abstractmethod
    def get_next_pic_to_visit(self):
        """get the next pic url to visit"""
        pass

    @abstractmethod
    def get_next_content_to_visit(self):
        """get the next content url to visit"""
        pass

    @abstractmethod
    def get_all_pics_to_visit(self, n=1000):
        """get all the next pic urls to visit"""
        pass
