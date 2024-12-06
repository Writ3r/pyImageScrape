#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import hashlib
import requests
import os
import pathlib
import urllib
import logging

from concurrent.futures import ThreadPoolExecutor, wait
from PIL import Image
from shared import get_current_folder, DataStore


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
        maxThreads: int = 8,
        imageMinWidth=400,
        imageMinHeight=300,
        outputType="png",
        dataFolderPath=get_current_folder(__file__) + "/data",
    ):
        self.dataStore = dataStore
        self._threadExec = ThreadPoolExecutor(max_workers=maxThreads)
        self.imageMinWidth = imageMinWidth
        self.imageMinHeight = imageMinHeight
        self.outputType = outputType
        self.imageSaveLoc = dataFolderPath + "/images"
        self.imageSavePath = pathlib.Path(self.imageSaveLoc)
        self.continueScraping = True

    def scrape_url(self, url):
        """grabes image, checks it, and saves image to output directory"""
        try:
            self._get_and_save_image_to_file_impl(url, self.imageSavePath)
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

    def _get_and_save_image_to_file(self, image_url, output_dir):
        """grabes image, checks it, and saves image to output directory"""
        try:
            self._get_and_save_image_to_file_impl(image_url, output_dir)
        except ImgReqFailed as e:
            self.dataStore.add_visited_pic_url(
                image_url, "HTTP_STATUS: " + str(e.statusCode)
            )
        except ImgTooSmall as e:
            self.dataStore.add_visited_pic_url(
                image_url,
                "IMG_TOO_SMALL: width=" + str(e.width) + " height=" + str(e.height),
            )
        except requests.exceptions.Timeout:
            self.dataStore.add_visited_pic_url(image_url, "TIMEOUT")
        except requests.exceptions.TooManyRedirects:
            self.dataStore.add_visited_pic_url(image_url, "TOO_MANY_REDIRECT")
        except requests.exceptions.RequestException as e:
            self.dataStore.add_visited_pic_url(image_url, "UNKNOWN_REQ_FAILURE")
        except Exception as e:
            self.dataStore.add_visited_pic_url(image_url, "UNKNOWN_FAILURE")

    def _get_and_save_image_to_file_impl(self, image_url, output_dir):
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

        urlType = self.outputType if self.outputType else get_url_filetype(image_url)
        filesha = hashlib.sha1(image_content).hexdigest()[:15]
        filename = filesha + "." + urlType
        fileRelFolder = filesha[0:2] + "/" + filesha[2:4] + "/" + filesha[4:6]
        fileRelPath = fileRelFolder + "/" + filename
        mkdirs_if_needed(str(output_dir / fileRelFolder))
        image.save(output_dir / fileRelPath)
        self.dataStore.add_stored_pic_url(image_url, fileRelPath, filesha)
        self.dataStore.add_visited_pic_url(image_url)
        logging.info(f"Grabbed pic {image_url=}")

    def set_can_stop_image_scraping(self):
        self.continueScraping = False
