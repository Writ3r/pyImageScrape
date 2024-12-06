#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import pathlib
import hashlib
import requests
import os
import urllib
import pathlib
import time

from typing import List
from concurrent.futures import ThreadPoolExecutor, wait
import threading
from bs4 import BeautifulSoup
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlite3 import Error
from shared import get_current_folder
from sqlliteDatasource import get_sqllite_datastore
from selenium.webdriver.remote.webdriver import WebDriver

from abc import ABC, abstractmethod


# ================================================================
#
# Module scope variables.
#
# ================================================================


CHROME_USER_AGENT = """Mozilla/5.0"""

# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
IMG_FILE_TYPES = ["jpg", "jpeg", "jfif", "pjpeg", "pjp", "png", "webp"]


# ================================================================
#
# Module scope functions
#
# ================================================================


def build_base_url(url: str):
    parsedUrl = urllib.parse.urlparse(url)
    return parsedUrl.scheme + "://" + parsedUrl.netloc


def get_url_filetype(url: str):
    return url.split("/")[-1].split("?")[0].split(".")[-1]


# ================================================================
#
# Module scope classes
#
# ================================================================


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
    def add_visited_pic_urls(self, urlLocs):
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


class ImageScraper:

    def __init__(
        self,
        dataStore: DataStore,
        maxThreads: int = 8,
        imageMinWidth=400,
        imageMinHeight=300,
        outputType="png",
        dataFolderPath=get_current_folder() + "/data",
    ):
        self.dataStore = dataStore
        self._threadExec = ThreadPoolExecutor(max_workers=maxThreads)
        self.imageMinWidth = imageMinWidth
        self.imageMinHeight = imageMinHeight
        self.outputType = outputType
        self.imageSaveLoc = dataFolderPath + "/images"
        self.imageSavePath = pathlib.Path(self.imageSaveLoc)
        self.continueScraping = True
        # mkdir img loc
        if not os.path.exists(self.imageSaveLoc):
            os.makedirs(self.imageSaveLoc)

    def scrape_images(self):
        # run until there are no pics left or program ends
        while self.continueScraping:
            try:
                # walk all image urls on the page
                futures = []
                allToVisit = self.dataStore.get_all_pics_to_visit()

                # go back if nothing to visit
                if allToVisit is None or len(allToVisit) == 0:
                    time.sleep(1)
                    continue

                for item in allToVisit:
                    try:
                        future = self._threadExec.submit(
                            self.get_and_save_image_to_file,
                            item,
                            output_dir=self.imageSavePath,
                        )
                        futures.append(future)
                    except Exception as e:
                        print("Failed to download picture: " + str(item))
                        print(e)
                wait(futures)
            except Exception as e:
                print(e)

    def get_and_save_image_to_file(self, image_url, output_dir):
        """grabes image, checks it, and saves image to output directory"""
        try:
            self._get_and_save_image_to_file(image_url, output_dir)
        except:
            pass
        self.dataStore.add_visited_pic_urls([image_url])
    
    def _get_and_save_image_to_file(self, image_url, output_dir):
        response = requests.get(
            image_url, headers={"User-agent": CHROME_USER_AGENT}, timeout=30
        )
        image_content = response.content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")
        width, height = image.size
        if width >= self.imageMinWidth and height >= self.imageMinHeight:
            urlType = (
                self.outputType if self.outputType else get_url_filetype(image_url)
            )
            filesha = hashlib.sha1(image_content).hexdigest()[:15]
            filename = filesha + "." + urlType
            fileRelPath = filename
            file_path = output_dir / fileRelPath
            image.save(file_path)
            self.dataStore.add_stored_pic_url(image_url, fileRelPath, filesha)
        raise Exception("Failed to parse url")

    def stop_image_scraping(self):
        self.continueScraping = False


class Scraper:
    """
    crawls a website, and scrapes all images.
    saves them to output dir
    """

    def __init__(
        self,
        baseUri: str,
        dataFolderPath=get_current_folder() + "/data",
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
        self.imgScraper.stop_image_scraping()
        scrape_img_thread.join()
