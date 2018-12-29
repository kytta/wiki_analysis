# wiki_analysis

[![CodeClimate Maintainability](https://img.shields.io/codeclimate/maintainability/NickKaramoff/wiki_analysis.svg)](https://codeclimate.com/github/NickKaramoff/wiki_analysis)
[![Dependency status via Libraries.io](https://img.shields.io/librariesio/github/NickKaramoff/wiki_analysis.svg)](https://libraries.io/github/NickKaramoff/wiki_analysis)  
![GitHub License](https://img.shields.io/github/license/NickKaramoff/wiki_analysis.svg)
![GitHub last commit date](https://img.shields.io/github/last-commit/NickKaramoff/wiki_analysis.svg)
![GitHub latest (pre-)release](https://img.shields.io/github/release-pre/NickKaramoff/wiki_analysis.svg)

This project analyzes pages of a chosen Wikipedia to find the most valuable page
using the PageRank algorithm.

## How it works

This program analyzes all pages on Wikipedia of a certain language, scraping the
urls from _Special:AllPages_. It then analyzes all the crosslinks between pages
and calculates the rank of every page using the PageRank algorithm (20
iterations).

## Speed

The speed of the algorithm depends on data size and your internet connection.
On my 60 Mbit/s network fetching and analyzing the
[Greenlandic Wikipedia](https://kl.wikipedia.org) with 1756 unique pages (blank
included) took ~60 minutes. Calculating rank took about 2 seconds on a MacBook
Pro 15 2016.

## How to Run

1. Make sure you have Python 3.x installed
2. Download and unpack wiki_analysis
3. Run `python3 -m pip install -r requirements.txt` to install dependencies
4. Create database named `wiki_analysis` and role/user `wiki` with password
   `wiki` on port 55432 or change the code in `conn.connect(...)` part
5. Run `1_fetch_analyze.py`
6. Enter the domain prefix (the one you see in the Wikipedia URL, e.g. 'en' for
   English)
7. Wait patiently. Note that some pages may not be downloaded because of the
   Internet connection
8. After download is finished run `2_calculate.py`
9. Enter the previously entered domain prefix
10. The app will present you top 25 most valuable pages based on PageRank
