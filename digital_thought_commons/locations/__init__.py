import pathlib
import _sqlite3
import csv
import logging
import re
from digital_thought_commons.digests import Digest

__locations_database = "{}/../_resources/locations/locations.sqlite".format(str(pathlib.Path(__file__).parent.absolute()))


def __initialise():
    global __locations_database
    connection = _sqlite3.connect(__locations_database, check_same_thread=False)
    create_country_table = """ CREATE TABLE IF NOT EXISTS countries (
                                                    id integer PRIMARY KEY,
                                                    country_hash text,
                                                    country_name text,
                                                    iso_alpha2 text
                                                ); """
    create_world_cities_table = """ CREATE TABLE IF NOT EXISTS world_cities (
                                                        id integer PRIMARY KEY,
                                                        city_hash text,
                                                        city_name text,
                                                        country_hash text,
                                                        country_name text,
                                                        sub_country_hash text,
                                                        sub_country_name text,
                                                        geoname_id text
                                                    ); """
    connection.execute(create_country_table)
    connection.execute(create_world_cities_table)
    return connection


__db_connection = __initialise()


def __calculate_hash(value: str):
    digest = Digest()
    digest.update_from_string(re.sub(r'[^a-zA-Z]', '', value.lower()))
    return digest.sha256()


def load_world_cities(input_csv: str, purge_current: bool = True):
    cursor = __db_connection.cursor()
    if purge_current:
        logging.warning(f'Purging current entries')
        cursor.execute(""" DELETE FROM world_cities; """)
    count = 0
    with open(input_csv, encoding="utf-8", mode="r") as in_file:
        logging.info(f'Loading World Cities from: {input_csv}')
        csv_dict = csv.DictReader(in_file)
        for row in csv_dict:
            cursor.execute("INSERT INTO world_cities(city_hash, city_name, country_hash, country_name, sub_country_hash, sub_country_name, geoname_id)"
                           " VALUES(?,?,?,?,?,?,?)",
                           (__calculate_hash(row['name']), row['name'], __calculate_hash(row['country']), row['country'], __calculate_hash(row['subcountry']),
                            row['subcountry'], row['geonameid']))
            count += 1

        __db_connection.commit()
    logging.info(f'Completed Loading World Cities from: {input_csv}. {str(count)} entries loaded.')


def load_countries(input_csv: str, purge_current: bool = True):
    cursor = __db_connection.cursor()
    if purge_current:
        logging.warning(f'Purging current entries')
        cursor.execute(""" DELETE FROM countries; """)
    count = 0
    with open(input_csv, encoding="utf-8", mode="r") as in_file:
        logging.info(f'Loading Countries from: {input_csv}')
        csv_dict = csv.DictReader(in_file)
        for row in csv_dict:
            cursor.execute("INSERT INTO countries(country_hash, country_name, iso_alpha2)"
                           " VALUES(?,?,?)",
                           (__calculate_hash(row['Name']), row['Name'], row['Code']))
            count += 1

        __db_connection.commit()
    logging.info(f'Completed Loading Countries from: {input_csv}. {str(count)} entries loaded.')


def lookup_country_hash(country_hash: str, country: str):
    cursor = __db_connection.cursor()
    cursor.execute('SELECT country_name, iso_alpha2 FROM countries WHERE country_hash="' + country_hash + '";')
    records = cursor.fetchall()
    if len(records) > 1:
        raise IndexError(f'Country lookup {country} returned {str(len(records))}.  Should only have 0 or 1 match.')
    elif len(records) == 0:
        return None
    else:
        return {'type': 'country', 'name': records[0][0], 'iso_alpha2': records[0][1]}


def lookup_country(country: str):
    return lookup_country_hash(__calculate_hash(country), country)


def lookup_city(city: str):
    cursor = __db_connection.cursor()
    cursor.execute('SELECT city_name, country_name, sub_country_name, geoname_id FROM world_cities WHERE city_hash="' + __calculate_hash(city) + '";')
    records = cursor.fetchall()
    if len(records) == 0:
        return None
    else:
        entries = []
        for record in records:
            entries.append({'type': 'city', 'name': record[0], 'country': record[1], 'sub_country': record[2],
                            'geoname_id': record[3]})
        return entries


def lookup_sub_country(sub_country: str):
    cursor = __db_connection.cursor()
    cursor.execute('SELECT country_name, sub_country_name FROM world_cities WHERE sub_country_hash="' + __calculate_hash(sub_country) + '";')
    records = cursor.fetchall()
    if len(records) == 0:
        return None
    else:
        for record in records:
            return {'type': 'sub_country', 'name': record[1], 'country': record[0]}


def lookup(name: str) -> dict:
    for look in [lookup_country, lookup_city, lookup_sub_country]:
        value = look(name)
        if value:
            return value
    return None
