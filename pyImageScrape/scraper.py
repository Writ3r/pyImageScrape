#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from shared import get_current_folder, DataStore, ScrapeJobProducer
from datasource.sqllite_datasource import get_sqllite_datastore
from data_scraper.content_scraper import URLScraper
from data_scraper.pic_scraper import ImageScraper
from producer.scrape_job_producer import SimpleScrapeJobProducer

logging.basicConfig(level=logging.INFO, format="{asctime} - {levelname} - {message}", style="{", datefmt="%Y-%m-%d %H:%M",)

class Scraper:
    """
    crawls a website, and scrapes all images.
    saves them to output dir
    """

    def __init__(
        self,
        baseUrl: str,
        dataFolderPath=get_current_folder(__file__) + "/data",
        urlscraper: URLScraper = None,
        imgScraper: ImageScraper = None,
        dataStore: DataStore = None,
        scrapeJobProducer: ScrapeJobProducer = None
    ):
        # setup datastore, use sqllite datasource if not given
        self.dataStore = (
            dataStore
            if dataStore is not None
            else get_sqllite_datastore(dataFolderPath)
        )

        # setup url scraper
        self.urlscraper = (
            urlscraper
            if urlscraper is not None
            else URLScraper(self.dataStore, baseUrl)
        )

        # setup img scraper
        self.imgScraper = (
            imgScraper
            if imgScraper is not None
            else ImageScraper(self.dataStore, dataFolderPath=dataFolderPath)
        )

        # setup scrape job producer
        self.scrapeJobProducer = (
            scrapeJobProducer
            if scrapeJobProducer is not None
            else SimpleScrapeJobProducer(baseUrl, self.dataStore, self.urlscraper,self.imgScraper)
        )

    def run(self):
        logging.info("Running Scrape Job Producer")
        self.scrapeJobProducer.run_producer()
        logging.info("Scraping is finished, exiting program")
