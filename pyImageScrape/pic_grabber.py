

import io
import hashlib
import requests
import os
import pathlib
import urllib
import time

from concurrent.futures import ThreadPoolExecutor, wait
from PIL import Image
from shared import get_current_folder, DataStore

CHROME_USER_AGENT = """Mozilla/5.0"""

def build_base_url(url: str):
    parsedUrl = urllib.parse.urlparse(url)
    return parsedUrl.scheme + "://" + parsedUrl.netloc

def get_url_filetype(url: str):
    return url.split("/")[-1].split("?")[0].split(".")[-1]

def mkdirs_if_needed(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

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
            fileRelFolder = filesha[0:2] + "/" +  filesha[2:4] + "/" + filesha[4:6]
            fileRelPath = fileRelFolder + "/"  + filename
            mkdirs_if_needed(str(output_dir / fileRelFolder))
            file_path = output_dir / fileRelPath
            image.save(file_path)
            self.dataStore.add_stored_pic_url(image_url, fileRelPath, filesha)
        raise Exception("Failed to parse url")

    def stop_image_scraping(self):
        self.continueScraping = False
