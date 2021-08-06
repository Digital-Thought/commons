import csv


def csv_to_json_list(csv_file) -> list:
    json_list = []
    with open(csv_file, 'r', encoding='utf-8') as in_file:
        for row in csv.DictReader(in_file):
            row_entry = {}
            for key in row:
                row_entry[key.strip().replace('\ufeff','')] = row[key]
            json_list.append(row_entry)

    return json_list
