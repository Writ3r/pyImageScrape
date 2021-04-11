#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse

from scraper import Scraper

# ================================================================
#
# Main
#
# ================================================================


def main():
    '''
    Takes input for url + id
    Ex.  scraperCli.py "https://www.master-plan.me/" "masterplan" "F:/test stuff"
    '''
    parser = argparse.ArgumentParser(description='Crawls the url for all pics')

    # args
    parser.add_argument("url", help="url to crawl")
    parser.add_argument("urlId", help="unique url identifier")
    parser.add_argument("dataFolderPath", help="path for where the parsing data will end up")

    # parse
    args = parser.parse_args()

    # run
    Scraper(args.url, args.urlId, dataFolderPath=args.dataFolderPath).run()


if __name__ == '__main__':
    main()
