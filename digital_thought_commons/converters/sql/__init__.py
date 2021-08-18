import csv
import logging
import re
import sys

import xlsxwriter

from digital_thought_commons.converters import json as json_converter

csv.field_size_limit(sys.maxsize)


def convert_to_csv(sql_file, output_dir, tables=None):
    logging.info(f'Converting {sql_file} to CSV')
    tables = list_tables(sql_file)
    for table in tables:
        if tables is None or table in tables:
            table_json = convert_sql_table_to_json(sql_file, table, tables[table])
            json_converter.json_array_to_csv(table_json, f'{output_dir}/{table}.csv')


def __value(dict_obj, key):
    if key not in dict_obj:
        return ""
    return dict_obj[key]


def convert_to_excel(sql_file, excel_file):
    logging.info(f'Converting {sql_file} to Excel')
    tables = list_tables(sql_file)
    workbook = xlsxwriter.Workbook(excel_file)
    for table in tables:
        if tables is None or table in tables:
            table_json = convert_sql_table_to_json(sql_file, table, tables[table])
            worksheet = workbook.add_worksheet()
            worksheet.name = table

            flattened = json_converter.flatten_json(table_json)
            headers = json_converter.read_fields(flattened)
            row = 0
            col = 0

            for header in headers:
                worksheet.write(row, col, header)
                col += 1

            for entry in flattened:
                col = 0
                row += 1
                for header in headers:
                    worksheet.write(row, col, __value(entry, header))
                    col += 1
    workbook.close()


def convert_to_json(sql_file) -> dict:
    logging.info(f'Converting {sql_file} to JSON')
    tables = list_tables(sql_file)
    json_dump = {}
    for table in tables:
        json_dump[table] = convert_sql_table_to_json(sql_file, table, tables[table])

    return json_dump


def convert_sql_table_to_json(sql_file, table, columns):
    logging.info(f'Converting {sql_file}::{table} to JSON')
    rows = []
    insert_pattern = re.compile('INSERT\sINTO\s' + table + '\sVALUES\s.*;$')
    with open(sql_file, 'r', encoding='UTF-8') as in_file:
        for line in in_file.readlines():
            matches = insert_pattern.match(line)
            if matches:
                t = matches.string[matches.string.find('(') + 1:].strip()
                t = t[:len(t) - 2]
                element = 0
                table_json = {}
                try:
                    for row in csv.reader([t], quotechar="'"):
                        for col in row:
                            if element < len(columns):
                                table_json[columns[element]] = col
                                element += 1
                except Exception as ex:
                    logging.exception(str(ex))
                    continue
                rows.append(table_json)
    return rows


def list_tables(sql_file):
    logging.info(f'List tables from {sql_file}')
    create_Table_patter = re.compile('CREATE\sTABLE\s([a-z_A-Z-0-9]*)[.\s\(]*$')
    tables = {}
    table = None
    columns = []
    with open(sql_file, 'r', encoding='UTF-8') as in_file:
        for line in in_file.readlines():
            matches = create_Table_patter.match(line)
            if matches:
                table = matches.group(1)
                columns = []
            elif table is not None and not line.strip().endswith(';'):
                column = line.strip().split(' ')[0]
                if column not in ['PRIMARY', 'KEY']:
                    columns.append(column)
            elif line.strip().endswith(';'):
                if table is not None:
                    tables[table] = columns
                    columns = []
                    table = None

    logging.info(f'Found {str(len(tables))} in {sql_file}')
    return tables
