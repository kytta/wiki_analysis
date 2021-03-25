# wiki_analysis

![NOT MAINTAINED](https://badgen.net/badge/maintained/no/red)

> Python script that ranks Wikipedia pages using PageRank algorithm

## How it works

This program analyzes all pages on Wikipedia of a certain language, scraping the
urls from _Special:AllPages_. It then analyzes all the crosslinks between pages
and calculates the rank of every page using the PageRank algorithm (20
iterations).

## Speed

The speed of the algorithm depends on data size and your internet connection.
On my 60 Mbit/s network fetching and analyzing takes around 0.65 seconds per
page. Calculating rank takes about 1 millisecond per page on a MacBook Pro 15
2016.

## How to Run

1. Make sure you have Python 3.6 or higher installed
2. Download and unpack wiki_analysis
3. Run `python3 -m pip install -r requirements.txt` to install dependencies
4. Put the database credentials into `config.yml`
5. Run `wiki_analysis.py LANG` where `LANG` is the language prefix of Wikipedia
6. Wait patiently. Sometimes it may break; the reason being the Internet
   connection. You will be notified if that happens
7. The app will present you top 25 most valuable pages based on rank
