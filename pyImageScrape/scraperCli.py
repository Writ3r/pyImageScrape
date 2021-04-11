#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse

from scraper import Scraper

# ================================================================
#
# Program specific parts.
#
# ================================================================


def main():
    '''
    Takes input for url + id
    Ex.  scraperCli.py "https://www.master-plan.me/" "masterplan"
    '''
    parser = argparse.ArgumentParser(description='Crawls the url for all pics')

    # arg for url
    def _check_url(url):
        if len(url) <= 0:
            raise argparse.ArgumentTypeError("%s is an invalid url" % url)
        return url

    parser.add_argument("url",
                        type=_check_url,
                        help="url to crawl")

    # arg for urlId
    def _check_urlId(urlId):
        if len(urlId) <= 0:
            raise argparse.ArgumentTypeError("%s is an invalid url id" % urlId)
        return urlId

    parser.add_argument("urlId",
                        type=_check_urlId,
                        help="unique url identifier")

    # arg for dataFolderPath
    def _check_dataFolderPath(dataFolderPath):
        if len(dataFolderPath) <= 0:
            raise argparse.ArgumentTypeError("%s is an invalid dataFolderPath" % dataFolderPath)
        return dataFolderPath

    parser.add_argument("dataFolderPath",
                        type=_check_dataFolderPath,
                        help="path for where the parsing data will end up")

    args = parser.parse_args()

    # run
    Scraper(args.url, args.urlId, dataFolderPath=args.dataFolderPath).run()


if __name__ == '__main__':
    main()
