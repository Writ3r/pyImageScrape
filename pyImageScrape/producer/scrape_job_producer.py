#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import threading
import time

from shared import UrlScrapeJobConsumer, DataStore
from typing import List
from concurrent.futures import ThreadPoolExecutor, wait

class SimpleScrapeJobProducer:
    """
    Kicks off scrape jobs to the consumers to handle
    """

    def __init__(
        self,
        baseUrl: str,
        dataStore: DataStore,
        contentJobConsumer: UrlScrapeJobConsumer,
        picJobConsumer: UrlScrapeJobConsumer,
        maxPicScrapeThreads = 8
    ):
        self.baseUrl = baseUrl
        self.dataStore = dataStore
        self.contentJobConsumer = contentJobConsumer
        self.picJobConsumer = picJobConsumer
        self.continueScrapingImages = True
        self.maxPicScrapeThreads = maxPicScrapeThreads
        self._threadExec = ThreadPoolExecutor(max_workers=maxPicScrapeThreads)
    
    def run_producer(self):
        # put root URL into queue
        self.dataStore.add_to_visit_content_urls([self.baseUrl])
        # kick off threads to manage scraping
        logging.info("Starting image scraping")
        scrape_img_thread = threading.Thread(target=self.produce_pic_urls)
        scrape_img_thread.start()
        logging.info("Starting url content scraping")
        scrape_url_thread = threading.Thread(target=self.produce_content_urls)
        scrape_url_thread.start()
        scrape_url_thread.join()
        self.continueScrapingImages = False
        scrape_img_thread.join()
        logging.info("Scraping Producer is finished")
    
    def produce_content_urls(self):
         # run until there are no content urls left, or program ends
        contentLeft = True
        while contentLeft:
            newUrl = self.dataStore.get_next_content_to_visit()
            if newUrl is not None:
                self.contentJobConsumer.scrape_url(newUrl)
            else:
                contentLeft = False

    
    def produce_pic_urls(self):
        # run until there are no pics left or program ends
        picsStillExist = True
        while self.continueScrapingImages or picsStillExist:
            try:
                # grab all some image urls
                futures = []
                allToVisit = self.dataStore.get_all_pics_to_visit(self.maxPicScrapeThreads)

                # go back if nothing to visit
                if allToVisit is None or len(allToVisit) == 0:
                    time.sleep(1)
                    picsStillExist = False
                    continue

                for item in allToVisit:
                    try:
                        future = self._threadExec.submit(
                            self.picJobConsumer.scrape_url,
                            item,
                        )
                        futures.append(future)
                    except Exception as e:
                        print("Failed to download picture: " + str(item))
                        print(e)
                wait(futures)
            except Exception as e:
                print(e)