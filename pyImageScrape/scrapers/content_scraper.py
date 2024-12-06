#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib

from shared import DataStore
from typing import List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from shared import DataStore

# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
IMG_FILE_TYPES = ["jpg", "jpeg", "jfif", "pjpeg", "pjp", "png", "webp"]

class URLScraper:

    def __init__(self, dataStore: DataStore, baseUrl: str, redriectRetries: int = 3):
        self.dataStore = dataStore
        self.driver = self.build_driver()
        self.redriectRetries = redriectRetries
        self.baseUrl = baseUrl

    def scrape_urls(self):
        # put root URL into queue
        self.dataStore.add_to_visit_content_urls([self.baseUrl])

        """ scrapes urls of all img content & links to other pages """
        # run until there are no pages left, or program ends
        while True:

            # grab next URL
            newUrl = self.dataStore.get_next_content_to_visit()
            if newUrl is None:
                break
            try:
                # parse all content
                changedUrl, content = self.get_content_from_url(newUrl)

                # get + save content URLs
                content_urls = self.parse_urls(
                    content=content,
                    locations=["a"],
                    sources=["href"],
                    urlLoc=changedUrl,
                )
                self.dataStore.add_to_visit_content_urls(
                    self.cleanContentUrls(content_urls)
                )
                # get + save image URLs
                image_urls = self.parse_urls(
                    content=content,
                    locations=["img"],
                    sources=["src"],
                    urlLoc=changedUrl,
                )
                image_urls.update(self.appendPicContentUrls(content_urls))
                self.dataStore.add_to_visit_pic_urls(image_urls)

            except Exception as e:
                print(e)

            # mark current content url as visited
            self.dataStore.add_visited_content_urls([newUrl])

            # remake driver if too many tabs (need better way to do this, possibly keep track of current tab and close all others)
            if len(self.driver.window_handles) > 10:
                self.driver.quit()
                self.driver = self.build_driver()

        # exit since finished
        self.driver.quit()

    def get_content_from_url(self, url):
        """grabs page content from url. allows retries if the site attempts redirects."""
        tries = 0
        currentUrl = None
        page_content = None
        # get content
        while tries <= self.redriectRetries and not (currentUrl == url):
            self.driver.get(url)
            try:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
            except Exception:
                pass
            page_content = self.driver.page_source
            currentUrl = self.driver.current_url
            tries += 1
        return currentUrl, page_content

    def parse_urls(self, content, locations, sources, urlLoc):
        """parses urls out of page content"""
        soup = BeautifulSoup(content, features="html.parser")
        results = set()
        for location in locations:
            allLocations = soup.findAll(location)
            for a in allLocations:
                if a not in results:
                    for source in sources:
                        src = a.get(source)
                        if src:
                            try:
                                if not (src.lower().startswith("http")):
                                    src = urllib.parse.urljoin(urlLoc, src)
                                results.add(src)
                            except Exception as e:
                                print(e)
        return results

    # TODO: remove element id from links (ex. http://localhost/hi#test)
    def cleanContentUrls(self, urls: List[str]):
        """cleans out all content urls of 'bad' ones"""
        cleanList = []
        for url in urls:
            if url and url.startswith(self.baseUrl):
                cleanList.append(url)
        return cleanList

    def appendPicContentUrls(self, urls: List[str]):
        """checks content urls for pic references"""
        cleanList = []
        for url in urls:
            if url:
                urlType = url.split("/")[-1]
                if "." in urlType:
                    for typee in IMG_FILE_TYPES:
                        if urlType.lower().endswith(typee):
                            cleanList.append(url)
        return cleanList

    def build_driver(self):
        """builds a headless browser with downloads turned off"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download_restrictions": 3,
            },
        )
        return webdriver.Chrome(options=chrome_options)