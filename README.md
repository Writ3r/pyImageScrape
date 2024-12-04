# pyImageScrape
Crawls the input url for all images on the site. Great for creating machine learning datasets. Make sure to get permission from the site before use. <br />

## Supported OS
Wrote all the code on windows, but the code should be OS independent. Let me know if it fails to run in linux.

## Setup
At minimum, need to pass into the CLI:
- baseUrl - [url that all images will start to be scraped from, and all child urls must start with]
- urlId - [folder name to store this url's data]
- dataFolderPath - [path to where you want the images/db data stored]

## Note
Built this as a personal project to look into how web crawlers work since I was curious, so this likely isn't completely fleshed out of bugs.<br />
As of right now, I don't have plans to expand upon this, it's more of just an interesting proof of concept. 
