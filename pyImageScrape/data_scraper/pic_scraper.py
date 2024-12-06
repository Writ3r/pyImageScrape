#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import hashlib
import requests
import os
import urllib
import logging

from PIL import Image
from shared import DataStore, FileStorage


def build_base_url(url: str):
    parsedUrl = urllib.parse.urlparse(url)
    return parsedUrl.scheme + "://" + parsedUrl.netloc


def get_url_filetype(url: str):
    return url.split("/")[-1].split("?")[0].split(".")[-1]


def mkdirs_if_needed(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


class ImgReqFailed(Exception):
    def __init__(self, statusCode):
        self.statusCode = statusCode


class ImgTooSmall(Exception):
    def __init__(self, width, height):
        self.width = width
        self.height = height


class ImageScraper:

    def __init__(
        self,
        dataStore: DataStore,
        fileStorage: FileStorage,
        imageMinWidth=400,
        imageMinHeight=300,
        outputType="png",
    ):
        self.dataStore = dataStore
        self.imageMinWidth = imageMinWidth
        self.imageMinHeight = imageMinHeight
        self.outputType = outputType
        self.fileStorage = fileStorage
        self.continueScraping = True

    def scrape_url(self, url):
        """grabes image, checks it, and saves image to output directory"""
        try:
            self._get_and_save_image_to_file(url)
        except ImgReqFailed as e:
            self.dataStore.add_visited_pic_url(
                url, "HTTP_STATUS: " + str(e.statusCode)
            )
        except ImgTooSmall as e:
            self.dataStore.add_visited_pic_url(
                url,
                "IMG_TOO_SMALL: width=" + str(e.width) + " height=" + str(e.height),
            )
        except requests.exceptions.Timeout:
            self.dataStore.add_visited_pic_url(url, "TIMEOUT")
        except requests.exceptions.TooManyRedirects:
            self.dataStore.add_visited_pic_url(url, "TOO_MANY_REDIRECT")
        except requests.exceptions.RequestException as e:
            self.dataStore.add_visited_pic_url(url, "UNKNOWN_REQ_FAILURE")
        except Exception as e:
            self.dataStore.add_visited_pic_url(url, "UNKNOWN_FAILURE")

    def _get_and_save_image_to_file(self, image_url):
        # make the request
        session = requests.Session()
        session.max_redirects = 5
        response = session.get(
            image_url, headers={"User-agent": """Mozilla/5.0"""}, timeout=30
        )

        # throw err if failed
        if not response.status_code == requests.codes.ok:
            raise ImgReqFailed(response.status_code)

        image_content = response.content
        image_file = io.BytesIO(image_content)
        image = Image.open(image_file).convert("RGB")

        # throw err if img is too small to care about
        width, height = image.size
        if width <= self.imageMinWidth or height <= self.imageMinHeight:
            raise ImgTooSmall(width, height)

        # calc out filename
        urlType = self.outputType if self.outputType else get_url_filetype(image_url)
        filesha = hashlib.sha1(image_content).hexdigest()[:15]
        filename = filesha + "." + urlType
        # calc out path
        fileRelPath = filesha[0:2] + "/" + filesha[2:4] + "/" + filesha[4:6] + "/" + filename
        # save img to buffer
        buffer = io.BytesIO()
        image.save(buffer, format=urlType)
        # store file in provider
        buffer.seek(0)
        image_bytes = buffer.read()
        self.fileStorage.store_file(image_bytes, fileRelPath)
        # mark pic as scraped
        self.dataStore.add_stored_pic_url(image_url, fileRelPath, filesha)
        self.dataStore.add_visited_pic_url(image_url)
        logging.info(f"Scraped pic {image_url=}")

    def set_can_stop_image_scraping(self):
        self.continueScraping = False
