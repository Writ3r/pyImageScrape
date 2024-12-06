#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pathlib

from abc import ABC, abstractmethod

def get_current_folder(file):
    return str(pathlib.Path(file).parent.absolute())

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
    def add_visited_content_urls(self, urlLocs):
        """tag multiple content urls as visited"""
        pass

    @abstractmethod
    def add_visited_pic_url(self, urlLoc, err = None):
        """tag multiple pic urls as visited"""
        pass

    @abstractmethod
    def add_stored_pic_url(self, urlLoc, filePath, shaPicHash):
        """tag multiple pic urls as visited"""
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
    def get_all_pics_to_visit(self):
        """get all the next pic urls to visit"""
        pass
