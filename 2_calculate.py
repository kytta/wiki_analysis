#  Copyright (c) 2018 Nikita Karamov <nick@karamoff.ru>

import sys
import psycopg2
import numpy as np
import pandas as pd
import yaml

domain_prefix = input("Domain prefix: ")
table_name = domain_prefix + '_wiki'


def check_table(conn):
    print("Checking tables...")
    cur = conn.cursor()

    cur.execute(
        """SELECT exists(
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_name=%s)""",
        (table_name,)
    )
    table_exists = cur.fetchone()[0]

    cur.execute(
        """SELECT exists(
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema='public' AND table_name=%s)""",
        (table_name + '_rel',)
    )
    rel_table_exists = cur.fetchone()[0]

    if not (table_exists and rel_table_exists):
        sys.exit("Tables do not exist. Analyze the pages first")

    print("Tables are ok")
    print()


def get_rels(conn):
    print("Getting links info...")
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM %s;"
        % (table_name + '_rel',)
    )
    print("Got links info")
    print()
    return np.array(cur.fetchall())


def calculate(data):
    print("Calculating the highest PageRank...")
    dl = len(data)

    urls_fr = list(num[0] for num in data[np.ix_(range(dl), [0])].tolist())
    urls_to = list(num[0] for num in data[np.ix_(range(dl), [1])].tolist())

    all_urls = list(sorted(set(urls_fr + urls_to)))
    all_titles = list(url.split('title=')[1] for url in all_urls)

    n = len(all_urls)
    m = np.zeros((n, n), dtype=np.float)

    for pair in data:
        try:
            idx_fr = all_urls.index(pair[0])
            idx_to = all_urls.index(pair[1])
            m[idx_to][idx_fr] += 1
        except ValueError:
            continue

    for i in range(n):
        col_sum = np.sum(m[np.ix_(range(n), [i])], dtype=np.int)
        if col_sum != 0:
            m[np.ix_(range(n), [i])] /= col_sum

    b = 0.85
    e = np.ones((n, 1), dtype=np.int)
    v = np.full((n, 1), 1 / n, np.float)

    for i in range(20):
        v = (b * m).dot(v) + ((1 - b) / n) * e

    print("Calculation finished")
    print()
    pd.set_option('display.max_colwidth', -1)
    df = pd.DataFrame({'title': all_titles, 'rank': list(v), 'url': all_urls}) \
        .sort_values('rank', ascending=False) \
        .head(25)

    return df


def main():
    print(f"Let's calculate the PageRank of the {domain_prefix} Wikipedia")
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

    check_table(conn)
    data = get_rels(conn)
    top_25 = calculate(data)
    print("Top 25 pages:")
    print(top_25)

    if conn is not None:
        conn.close()


if __name__ == '__main__':
    main()
