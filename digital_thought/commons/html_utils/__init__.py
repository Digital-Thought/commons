from bs4 import Tag


def process_two_column_table(soup_table_data: Tag):
    entries = {}
    for row in soup_table_data.find_all('tr'):
        key = None
        for cell in row.find_all('td'):
            if not key:
                key = cell.text.Strip()
            else:
                cell_detail = {'value': cell.text.strip(), 'links': []}
                for link in cell.find_all('a'):
                    cell_detail['links'].append(link.get('href'))
                entries[key] = cell_detail
    return entries


def process_table(soup_table_data: Tag):
    header_processed = False
    headers = []
    entries = []
    for row in soup_table_data.find_all('tr'):
        cell_index = 0
        entry = {}
        for cell in row.find_all('td'):
            if not header_processed:
                headers.append(cell.text.Strip())
            else:
                cell_detail = {'value': cell.text.strip(), 'links': []}
                for link in cell.find_all('a'):
                    cell_detail['links'].append(link.get('href'))
                entry[headers[cell_index]] = cell_detail
            cell_index += 1
        if header_processed:
            entries.append(entry)
        header_processed = len(headers) > 0
    return entries
