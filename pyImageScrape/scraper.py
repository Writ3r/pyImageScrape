#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading

from shared import get_current_folder, DataStore
from datasource.sqlliteDatasource import get_sqllite_datastore
from scrapers.content_scraper import URLScraper
from scrapers.pic_grabber import ImageScraper


class Scraper:
    """
    crawls a website, and scrapes all images.
    saves them to output dir
    """

    def __init__(
        self,
        baseUri: str,
        dataFolderPath=get_current_folder(__file__) + "/data",
        urlscraper: URLScraper = None,
        imgScraper: ImageScraper = None,
        dataStore: DataStore = None,
    ):
        # use sqllite datasource if not given
        self.dataStore = (
            dataStore
            if dataStore is not None
            else get_sqllite_datastore(dataFolderPath)
        )

        # setup url scraper
        self.urlscraper = (
            urlscraper
            if urlscraper is not None
            else URLScraper(self.dataStore, baseUri)
        )

        # setup img scraper
        self.imgScraper = (
            imgScraper
            if imgScraper is not None
            else ImageScraper(self.dataStore, dataFolderPath=dataFolderPath)
        )

    def run(self):
        # startup image scraping
        scrape_img_thread = threading.Thread(target=self.imgScraper.scrape_images)
        scrape_img_thread.start()
        # startup url scraping
        scrape_url_thread = threading.Thread(target=self.urlscraper.scrape_urls)
        scrape_url_thread.start()
        # finish out threads
        scrape_url_thread.join()
        self.imgScraper.can_stop_image_scraping()
        scrape_img_thread.join()
