# wiki_analysis

[![](https://img.shields.io/travis/NickKaramoff/wiki_analysis.svg)](https://travis-ci.org/NickKaramoff/wiki_analysis/)
[![](https://img.shields.io/codeclimate/maintainability/NickKaramoff/wiki_analysis.svg)](https://codeclimate.com/github/NickKaramoff/wiki_analysis)
[![](https://img.shields.io/codecov/c/github/NickKaramoff/wiki_analysis.svg)](https://codecov.io/gh/NickKaramoff/wiki_analysis)

This project analyzes pages of a chosen Wikipedia to find the most valuable page
using the PageRank algorithm.

## How it works

This program analyzes all pages on Wikipedia of a certain language, scraping the
urls from _Special:AllPages_. It then analyzes all the crosslinks between pages
and calculates the rank of every page using the PageRank algorithm (20 
iterations).

## Speed

Speed of the algorithm depends on data size and your internet connection.
On my 60 Mbit/s network fetching and analyzing the
[Greenlandic Wikipedia](https://kl.wikipedia.org) with 1756 unique pages took an
hour. Calculating rank takes about 2 seconds on a MacBook Pro 15 2016.

## How to Run

1. Create database named `wiki_analysis` and role `wiki` with password `wiki` on
   port 55432 or change the code in `conn.connect(...)` part
2. Launch the `1_fetch_analyze.py`
3. Enter the domain prefix (the one you see in the Wikipedia URL, like 'en' for
   English)
4. Wait patiently. It might break on some pages because of the Internet 
   connection
5. After finished launch the `2_calculate.py`
6. Enter the previously entered domain prefix
7. The app will present you top 25 most valuable pages based on rank

## Troubleshooting

This project is very raw and problems may occur. Here's what you should better
do after analyzing the pages (after step 4)

### NULL values

If a request failed on some crosslink it will record NULL value to the database.
To fix, run

```sql
DELETE FROM LCODE_wiki_rel
WHERE from_url ISNULL or to_url ISNULL;
```

where `LCODE` is the language code of analyzed Wikipedia.

### Non-articles

The algorithm currently records links for images and other files. If you only
want articles, run:

```sql
DELETE FROM LCODE_wiki_rel
WHERE from_url NOT ILIKE '%index.php%' or to_url NOT ILIKE '%index.php%';

DELETE FROM LCODE_wiki
WHERE page_url NOT ILIKE '%index.php%';
```

where `LCODE` is the language code of analyzed Wikipedia.
