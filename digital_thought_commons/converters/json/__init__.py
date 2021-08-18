import csv
import json

import xlsxwriter


def read_fields(json_obj):
    fields = []
    if isinstance(json_obj, list):
        for obj in json_obj:
            if obj:
                for key in obj:
                    if key not in fields:
                        fields.append(key)
    else:
        for key in json_obj:
            if key not in fields:
                fields.append(key)

    return fields


def njson_to_csv(njson_lines, csv_file):
    data = flatten_njson(njson_lines)
    fields = read_fields(data)
    with open(csv_file, 'w', encoding='utf-8') as csv_fp:
        writer = csv.DictWriter(csv_fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def json_array_to_csv(json_array, csv_file):
    data = flatten_json(json_array)
    fields = read_fields(data)
    with open(csv_file, 'w', encoding='utf-8') as csv_fp:
        writer = csv.DictWriter(csv_fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)


def flatten_json_list(json_list, flattened_dict, key):
    value = ''
    for obj in json_list:
        if len(value) > 0:
            value = value + ',\r\n'
        if isinstance(obj, dict):
            value = value + json.dumps(obj, indent=4)
        else:
            value = value + str(obj)
    flattened_dict[key] = value


def flatten_json_dict(json_dict, flattened_dict, prior_level=""):
    for key in json_dict:
        if isinstance(json_dict[key], dict):
            flatten_json_dict(json_dict[key], flattened_dict, '{}{}.'.format(prior_level, key))
        elif isinstance(json_dict[key], list):
            flatten_json_list(json_dict[key], flattened_dict, '{}{}'.format(prior_level, key))
        else:
            flattened_dict['{}{}'.format(prior_level, key)] = json_dict[key]


def flatten_json(json_object):
    if isinstance(json_object, dict):
        flattened_dict = {}
        flatten_json_dict(json_object, flattened_dict=flattened_dict)
        return flattened_dict
    elif isinstance(json_object, list):
        flattened_objects = []
        for obj in json_object:
            flattened_dict = {}
            flatten_json_dict(obj, flattened_dict=flattened_dict)
            flattened_objects.append(flattened_dict)
        return flattened_objects


def flatten_njson(njson_lines):
    flattened_objects = []
    for line in njson_lines:
        flattened_objects.append(flatten_json(json.loads(line)))

    return flattened_objects


def json_list_to_excel(json_list: list, sheet_name: str, excel_file: str):
    workbook = xlsxwriter.Workbook(excel_file)
    worksheet = workbook.add_worksheet()
    worksheet.name = sheet_name
    flattened = flatten_json(json_list)
    headers = read_fields(flattened)

    row = 0
    col = 0

    for header in headers:
        worksheet.write(row, col, header)
        col += 1

    for entry in flattened:
        col = 0
        row += 1
        for header in headers:
            worksheet.write(row, col, entry.get(header, ''))
            col += 1

    workbook.close()


def to_file(json_object, csv_file_path: str):
    with open(csv_file_path, 'w', encoding='utf-8') as out_file:
        json.dump(json_object, out_file, indent=4)
