#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import pathlib
import hashlib
import requests
import os
import urllib
import pathlib

from concurrent.futures import ThreadPoolExecutor, wait
from bs4 import BeautifulSoup
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlite3 import Error
from shared import get_current_folder
from sqlliteDatasource import get_sqllite_datastore

from abc import ABC, abstractmethod


# ================================================================
#
# Module scope variables.
#
# ================================================================


CHROME_USER_AGENT = """Mozilla/5.0"""

# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
IMG_FILE_TYPES = ['jpg', 'jpeg', 'jfif', 'pjpeg', 'pjp', 'png', 'webp']


# ================================================================
#
# Module scope functions
#
# ================================================================


def build_base_url(url):
    parsedUrl = urllib.parse.urlparse(url)
    return parsedUrl.scheme + '://' + parsedUrl.netloc

def get_url_filetype(url:str):
    return url.split("/")[-1].split("?")[0].split(".")[-1]


# ================================================================
#
# Module scope classes
#
# ================================================================


class DataStore(ABC):

    @abstractmethod
    def add_to_visit_urls(self, urlLocs, table):
        """add multiple urls to visit"""
        pass

    @abstractmethod
    def add_visited_urls(self, urlLocs, table):
        """tag multiple urls as visited"""
        pass

    @abstractmethod
    def get_next_to_visit(self, table):
        """get the next url to visit"""
        pass

    @abstractmethod
    def get_all_to_visit(self, table):
        """get all the next urls to visit"""
        pass


class Scraper:
    """
    crawls a website, and scrapes all images.
    saves them to output dir
    chrome drivers: https://chromedriver.chromium.org/downloads
    """

    def __init__(self,
                 baseUrl="https://www.master-plan.me/Example/",
                 urlId="testboi",
                 redriectRetries=3,
                 imageMinWidth=512,
                 imageMinHeight=512,
                 outputType='png',
                 maxThreads=8,
                 dataFolderPath=get_current_folder()+"/data",
                 dataStore:DataStore=None):

        # set vals
        self.urlId = urlId
        self.baseUrl = baseUrl
        self.redriectRetries = redriectRetries
        self.imageMinWidth = imageMinWidth
        self.imageMinHeight = imageMinHeight
        self.outputType = outputType
        self.dataPath = dataFolderPath + "/" + self.urlId
        self.imageSaveLoc = self.dataPath + "/images"

        # build objs
        self.imageSavePath = pathlib.Path(self.imageSaveLoc)
        self.strippedBaseUrl = build_base_url(self.baseUrl)
        self.driver = self.build_driver()
        self._threadExec = ThreadPoolExecutor(max_workers=maxThreads)

        # use sqllite datasource if not given
        self.dataStore = dataStore if dataStore is not None else get_sqllite_datastore(self.dataPath)

        # mkdir img loc
        if not os.path.exists(self.imageSaveLoc):
            os.makedirs(self.imageSaveLoc)

    def build_driver(self):
        """ builds a headless browser with downloads turned off """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option(
            "prefs", {
                "download_restrictions": 3,
            }
        )
        return webdriver.Chrome(options=chrome_options)

    def get_content_from_url(self, url):
        """ grabs page content from url. allows retries if the site attempts redirects."""
        tries = 0
        currentUrl = None
        page_content = None
        # get content
        while tries <= self.redriectRetries and not(currentUrl == url):
            self.driver.get(url)
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            except Exception:
                pass
            page_content = self.driver.page_source
            currentUrl = self.driver.current_url
            tries += 1
        return currentUrl, page_content

    def parse_urls(self, content, locations, sources, urlLoc):
        """ parses urls out of page content """
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
                                if not(src.lower().startswith('http')):
                                    src = urllib.parse.urljoin(urlLoc, src)
                                results.add(src)
                            except Exception as e:
                                print(e)
        return results

    def get_and_save_image_to_file(self, image_url, output_dir):
        """ grabes image, checks it, and saves image to output directory """
        response = requests.get(image_url, headers={"User-agent": CHROME_USER_AGENT})
        image_content = response.content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")
        width, height = image.size
        if width >= self.imageMinWidth and height >= self.imageMinHeight:
            urlType = self.outputType if self.outputType else get_url_filetype(image_url)
            filename = hashlib.sha1(image_content).hexdigest()[:15] + '.' + urlType
            file_path = output_dir / filename
            image.save(file_path)

    def run(self):
        """
        runs the scraper until it runs out of content urls
        - works in a way that you can stop/restart at any time without missing images
        """

        # put root URL into queue
        self.dataStore.add_to_visit_urls([self.baseUrl], self.dataStore.CONTENT_URL_TB)

        def cleanContentUrls(urls):
            """ cleans out all content urls of 'bad' ones """
            cleanList = []
            for url in urls:
                if url and url.startswith(self.baseUrl):
                    cleanList.append(url)
            return cleanList

        def appendPicContentUrls(urls):
            """ checks content urls for pic references """
            cleanList = []
            for url in urls:
                if url:
                    urlType = url.split("/")[-1]
                    if "." in urlType:
                        for typee in IMG_FILE_TYPES:
                            if urlType.lower().endswith(typee):
                                cleanList.append(url)
            return cleanList

        # run until there are no pages left, or program ends
        while True:

            # grab next URL
            newUrl = self.dataStore.get_next_to_visit(self.dataStore.CONTENT_URL_TB)
            if newUrl is None:
                break

            try:
                # parse all content
                changedUrl, content = self.get_content_from_url(newUrl)

                # get + save content URLs
                content_urls = self.parse_urls(
                    content=content, locations=["a"], sources=["href"], urlLoc=changedUrl
                )
                self.dataStore.add_to_visit_urls(cleanContentUrls(content_urls),
                                                 self.dataStore.CONTENT_URL_TB)
                # get + save image URLs
                image_urls = self.parse_urls(
                    content=content, locations=["img"], sources=["src"], urlLoc=changedUrl
                )
                image_urls.update(appendPicContentUrls(content_urls))
                self.dataStore.add_to_visit_urls(image_urls,
                                                 self.dataStore.PIC_URL_TB)

                # walk all image urls on the page
                futures = []
                allToVisit = self.dataStore.get_all_to_visit(self.dataStore.PIC_URL_TB)
                for item in allToVisit:
                    try:
                        future = self._threadExec.submit(self.get_and_save_image_to_file,
                                                         item,
                                                         output_dir=self.imageSavePath)
                        futures.append(future)
                    except Exception as e:
                        print('Failed to download picture: ' + str(item))
                        print(e)
                wait(futures)

                # blacklist all photo urls visited
                self.dataStore.add_visited_urls(allToVisit, self.dataStore.PIC_URL_TB)

            except Exception as e:
                print(e)

            # blacklist current content url
            self.dataStore.add_visited_urls([newUrl], self.dataStore.CONTENT_URL_TB)

            # remake driver if too many tabs (need better way to do this)
            if len(self.driver.window_handles) > 10:
                self.driver.quit()
                self.driver = self.build_driver()

        # exit
        self.driver.quit()
