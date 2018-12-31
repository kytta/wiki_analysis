#  Copyright (c) 2018 Nikita Karamov <nick@karamoff.ru>

import time
import psycopg2
import requests
import sys
from bs4 import BeautifulSoup as Bs
import re
import yaml

domain_prefix = input("Domain prefix: ")
prefix = "https://" + domain_prefix + ".wikipedia.org"
table_name = domain_prefix


def create_tables(conn):
    print("Creating tables...")
    cur = conn.cursor()

    # check rel table - drop if exists
    cur.execute(
        """SELECT exists(
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_name=%s)""",
        (table_name + '_links',)
    )
    table_exists = cur.fetchone()[0]
    if table_exists:
        print("Old table exists, dropping...")
        cur.execute(
            "DROP TABLE " + table_name + '_links'
        )

    # check pages table - drop if exists
    cur.execute(
        """SELECT exists(
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_name=%s)""",
        (table_name,)
    )
    table_exists = cur.fetchone()[0]
    if table_exists:
        print("Old table exists, dropping...")
        cur.execute(
            "DROP TABLE " + table_name
        )

    # create pages table
    cur.execute(
        "CREATE TABLE "
        + table_name
        + " ("
          "title VARCHAR(256) PRIMARY KEY,"
          "unique_url VARCHAR(2047)"
          ")"
    )
    conn.commit()
    print("Table for pages created")

    # create and bind rel table
    cur.execute(
        "CREATE TABLE "
        + table_name + '_links'
        + " ("
          "from_title VARCHAR(256) REFERENCES "
        + table_name + "(title),"
        + "to_title VARCHAR(256) REFERENCES "
        + table_name + "(title)"
                       ")"
    )
    conn.commit()
    print("Table for pages relations created")
    print()


def add_to_database(conn, page_url, page_title):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO " + table_name
        + "(unique_url, title) "
          "VALUES(%s, %s)"
          "ON CONFLICT (title) DO NOTHING",
        (page_url, page_title)
    )
    conn.commit()


def unique(soup, url):
    try:
        unique_url = list(soup.select('#t-permalink')[0].children)[0]['href']
        unique_url = re.sub(r'&oldid=\d*', '', unique_url)
        unique_url = prefix + unique_url
    except IndexError:
        unique_url = url
    name = soup.select('#firstHeading')[0].get_text()
    return unique_url, name


def register_link(conn, from_title, to_title):
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO " + table_name + "_links (from_title, to_title)" +
        " VALUES (%s, %s)",
        (from_title, to_title)
    )

    conn.commit()


def analyze(conn, url, all_pages):
    try:
        p = requests.get(url,
                         headers={'User-Agent': 'wiki_analysis/0.3'},
                         timeout=30)
        soup = Bs(p.content, 'html.parser')
        unique_url, unique_name = unique(soup, url)

        if 'index.php' in unique_url:
            if unique_name not in all_pages:
                add_to_database(conn, unique_url, unique_name)
                all_pages.append(unique_name)

                links = soup.select(
                    "#mw-content-text > .mw-parser-output > p > a")

                print(f"{soup.select('#firstHeading')[0].get_text()}")

                for link in links:
                    if link.has_attr('href') and link['href'][0] == '/':
                        if link.has_attr('class') and 'new' in link.attrs['class']:
                            continue
                        link_url = prefix + link['href']
                        link_unique_name = analyze(conn, link_url, all_pages)
                        if link_unique_name:
                            register_link(conn, unique_name, link_unique_name)

            return unique_name
        else:
            return None

    except requests.exceptions.Timeout:
        print(url + " timed out")
        return None
    except requests.exceptions.ConnectionError:
        print("Couldn't connect to " + url)
        return None


def get_and_write_pages(conn):
    print("Getting all pages...")
    all_pages = []
    finished = False
    counter = 1
    next_link = prefix + "/wiki/Special:AllPages"

    start = time.perf_counter()
    while not finished:
        print(f"Indexing part {counter}")
        list_part = requests.get(next_link)
        soup = Bs(list_part.content, 'html.parser')

        if len(soup.select('.mw-allpages-nav')) > 0:
            if len(all_pages) > 0 and \
                    len(list(soup.select('.mw-allpages-nav')[0].children)) == 1:
                finished = True
            else:
                next_link = prefix + \
                            list(soup.select('.mw-allpages-nav')[0].children)[
                                -1]['href']
        else:
            finished = True

        pages = list(
            soup.select(".mw-allpages-body > .mw-allpages-chunk")[0].children)

        for page in pages:
            if page != '\n':
                analyze(conn, prefix + list(page.children)[0]['href'],
                        all_pages)
        counter += 1
    print(f"Analyzed {len(all_pages)} pages!")
    print(f"It took {time.perf_counter() - start}s")
    print()


def main():
    print(f"Let's analyze the {domain_prefix} Wikipedia")
    print()

    print("Checking connection...")
    try:
        requests.get(prefix)
        print("Internet is working")
    except ConnectionError:
        sys.exit("Connection failed.")
    print()

    print("Loading config...")
    config = yaml.load(open('config.yml').read())
    db_conf = config['database']
    print()

    print("Connecting to database...")
    conn = None

    try:
        conn = psycopg2.connect(
            host=db_conf.get('host') or 'localhost',
            database=db_conf.get('dbname') or 'wiki_analysis',
            user=db_conf.get('username') or 'wiki',
            password=db_conf.get('password') or 'wiki',
            port=db_conf.get('port') or '5432'
        )
        print("Connected to database")
    except psycopg2.DatabaseError:
        sys.exit("Connection to database failed.")
    print()

    create_tables(conn)
    get_and_write_pages(conn)

    if conn is not None:
        conn.close()


if __name__ == '__main__':
    main()
