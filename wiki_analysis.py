# Copyright (c) 2019 Nikita Karamov <nick@karamoff.ru>

import sys
import time

from bs4 import BeautifulSoup as Bs
import numpy as np
import pandas as pd
import psycopg2
import requests
import yaml

if __name__ == '__main__':
    pass

LANG = input("Wikipedia language code: ")
TABLE_NAME = LANG
HOST = f"https://{LANG}.wikipedia.org"
ALL_PAGES = "/wiki/Special:AllPages"
HEADERS = {'User-Agent': 'wiki_analysis/0.3'}
TIMEOUT = 30
ITERATIONS = 20
TOP_PAGES_AMOUNT = 25

pages = []

print('=============')
print('wiki_analysis')
print('=============')
print()

# DATABASE CONNECTION
db_conf = yaml.load(open('config.yml').read())['database']
print("Connecting to database...")
try:
    CONN = psycopg2.connect(
        host=db_conf.get('host') or 'localhost',
        database=db_conf.get('dbname') or 'wiki_analysis',
        user=db_conf.get('username') or 'wiki',
        password=db_conf.get('password') or 'wiki',
        port=db_conf.get('port') or '5432'
    )
    CUR = CONN.cursor()
    print("Connected to database.")
except psycopg2.DatabaseError:
    sys.exit("Connection to database failed.")
print()

# TABLES DROP AND CREATION
drop_tables = input(f"The script is about to drop tables (if they exist):\n"
                    f"\t- {LANG}\n"
                    f"\t- {LANG}_links\n"
                    f"\t- {LANG}_urls\n\n"
                    "Do you wish to proceed? [y/n]: ")
if drop_tables.lower() == 'n':
    print("Please, drop or rename tables or choose a different language.")
    CONN.close()
    sys.exit(0)
print("Dropping old tables...")
CUR.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}_urls;")
CUR.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}_links;")
CUR.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
CONN.commit()
CUR.execute(f"CREATE TABLE {TABLE_NAME} ("
            "title VARCHAR(256) PRIMARY KEY);")
CUR.execute(f"CREATE TABLE {TABLE_NAME}_links ("
            f"from_title VARCHAR(256) REFERENCES {TABLE_NAME}(title) "
            "ON DELETE CASCADE,"
            f"to_title VARCHAR(256) REFERENCES {TABLE_NAME}(title) "
            "ON DELETE CASCADE);")
CUR.execute(f"CREATE TABLE {TABLE_NAME}_urls ("
            f"title VARCHAR(256) REFERENCES {TABLE_NAME}(title) "
            f"ON DELETE CASCADE,"
            "url VARCHAR(2047));")
CONN.commit()
print("New tables created.")
print()


def find_in_database(url):
    """
    Looks through database to find the article if it has been parsed before

    :param url: URL of the article
    :return: title of the article if it has been parsed; otherwise None
    """
    CUR.execute("SELECT title "
                f"FROM {TABLE_NAME}_urls "
                "WHERE url=%s;",
                (url,))
    titles = CUR.fetchall()
    CONN.commit()
    return titles[0] if len(titles) > 0 else None


def add_to_database(title):
    """
    Adds newly parsed article to the database

    :param title: title of the article
    """
    CUR.execute(f"INSERT INTO {TABLE_NAME}(title) "
                "VALUES (%s);",
                (title,))
    CONN.commit()


def add_url_to_database(title, url):
    """
    Adds article URL binding to the database

    :param title: title of the article
    :param url: URL of the article
    """
    CUR.execute(f"INSERT INTO {TABLE_NAME}_urls(title, url) "
                "VALUES (%s, %s);",
                (title, url))
    CONN.commit()


def add_link_to_database(from_title, to_title):
    """
    Adds the information about the link between two pages to the database

    :param from_title: title of the start article
    :param to_title: title of the end article
    """
    CUR.execute(f"INSERT INTO {TABLE_NAME}_links(from_title, to_title) "
                "VALUES (%s, %s);",
                (from_title, to_title))
    CONN.commit()


def analyze(article_url):
    """
    Analyzes the article, adds it to database if needed and registers links

    :param article_url: URL of the article
    :return: title of the article; None if there were errors
    """
    in_database = find_in_database(article_url)
    if in_database:
        return in_database
    try:
        a = requests.get(article_url,
                         headers=HEADERS,
                         timeout=TIMEOUT)
        if '"wgCanonicalNamespace":""' not in a.text:
            return None
        a_soup = Bs(a.content, 'lxml')
        title = a_soup.select('#firstHeading')[0].get_text()
        if title not in pages:
            add_to_database(title)
            pages.append(title)
            print(f"\r{len(pages) - 1} analyzed. Parsing {title}...", end='')

            links = a_soup.select(".mw-parser-output > p > a")
            for link in links:
                if link.has_attr('href') and link['href'][0] == '/':
                    if link.has_attr('class') and 'new' in link.attrs['class']:
                        continue
                    link_url = HOST + link['href']
                    link_title = analyze(link_url)
                    if link_title:
                        add_link_to_database(title, link_title)
        add_url_to_database(title, article_url)
        return title

    except requests.exceptions.Timeout:
        print(f"\r{article_url} timed out")
        return None
    except requests.exceptions.ConnectionError:
        print(f"\rCouldn't connect to {article_url}")
        return None


# PAGES FETCHING
print("Getting all pages urls...")
finished = False
next_url = HOST + ALL_PAGES
start = time.perf_counter()
while not finished:
    page = requests.get(next_url,
                        headers=HEADERS,
                        timeout=TIMEOUT)
    soup = Bs(page.content, 'lxml')

    if len(soup.select('.mw-allpages-nav')) > 0 \
            and len(pages) == 0 \
            and len(list(soup.select('.mw-allpages-nav')[0].children)) != 1:
        next_url = HOST + \
                   list(soup.select('.mw-allpages-nav')[0].children)[-1]['href']
    else:
        finished = True

    article_list = soup.select(".mw-allpages-chunk")[0].children
    for article in article_list:
        if article == '\n':
            continue
        analyze(HOST + next(article.children)['href'])
end = time.perf_counter()
print("\r ", end='')
print(f"\rAll {len(pages)} pages analyzed! Took {round(end - start, 4)} ms.")
print()

# DATASET FETCHING
print("Preparing data for analysis...")
CUR.execute("SELECT from_title, to_title "
            f"FROM {TABLE_NAME}_links;")
data = np.array(CUR.fetchall())
CONN.commit()
link_count = len(data)
if link_count == 0:
    CONN.close()
    print("There are no links; can't analyze.")
    sys.exit(0)
from_titles = list(n[0] for n in data[np.ix_(range(link_count), [0])].tolist())
to_titles = list(n[0] for n in data[np.ix_(range(link_count), [1])].tolist())
all_titles = list(sorted(set(from_titles + to_titles)))
print("Data prepared.")
print()

# CALCULATING
print("Calculating...")
n = len(all_titles)
m = np.zeros((n, n), dtype=np.float)
b = 0.85
e = np.ones((n, 1), dtype=np.int)
v = np.full((n, 1), 1 / n, np.float)
for pair in data:
    try:
        idx_fr = all_titles.index(pair[0])
        idx_to = all_titles.index(pair[1])
        m[idx_to][idx_fr] += 1
    except ValueError:
        continue
for i in range(n):
    col_sum = np.sum(m[np.ix_(range(n), [i])], dtype=np.int)
    if col_sum != 0:
        m[np.ix_(range(n), [i])] /= col_sum
for i in range(ITERATIONS):
    v = (b * m).dot(v) + ((1 - b) / n) * e
print("Calculation finished.")
print()

# DATA OUTPUT
print(f"Top {TOP_PAGES_AMOUNT} pages")
pd.set_option('display.max_colwidth', -1)
df = pd.DataFrame({'title': all_titles, 'rank': list(v)}) \
    .sort_values('rank', ascending=False) \
    .head(TOP_PAGES_AMOUNT)
print(df)
print()

# EXITING
print("Closing connection...")
CONN.close()
print("Connection closed.")
