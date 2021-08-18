import json
import logging

import xlsxwriter

from digital_thought_commons.converters import json as json_converters
from digital_thought_commons.enrichers import ip_address_domain_details


class AuditReport:

    def __init__(self) -> None:
        self.application_reports = {}
        self.ip_addresses = []
        self.enriched_ip_addresses = []

    def add(self, application_name, report):
        self.application_reports[application_name] = report
        for activity in report:
            if 'ipAddress' in activity and activity['ipAddress'] not in self.ip_addresses:
                self.ip_addresses.append(activity['ipAddress'])

    def enrich_ip_addresses(self, api_keys):
        enricher = ip_address_domain_details.IPAddressDomainInfo(api_keys=api_keys)
        for ip_address in self.ip_addresses:
            logging.info(f'Enriching IP Address: {ip_address}')
            self.enriched_ip_addresses.append(enricher.lookup_ip_address(ip_address=ip_address))
        return self.enriched_ip_addresses

    def get_application_report(self, application_name) -> list:
        return self.application_reports.get(application_name, [])

    def json(self) -> dict:
        return self.application_reports

    def json_dump(self, out_file):
        with open(out_file, 'w', encoding='utf-8') as of:
            json.dump(self.application_reports, of, indent=4)

    @staticmethod
    def __build_flat_activity(activity) -> dict:
        return {'kind': activity.get('kind', ''), 'time': activity['id'].get('time', ''), 'uniqueQualifier': activity['id'].get('uniqueQualifier', ''),
                'applicationName': activity['id'].get('applicationName', ''), 'customerId': activity['id'].get('customerId', ''), 'etag': activity.get('etag', ''),
                'callerType': activity['actor'].get('callerType', ''), 'email': activity['actor'].get('email', ''), 'profileId': activity['actor'].get('profileId', ''),
                'ipAddress': activity.get('ipAddress', '')}

    @staticmethod
    def __build_flat_event(event) -> dict:
        f_event = {}
        try:
            f_event = {'type': event.get('type', ''), 'name': event.get('name', '')}

            for parameter in event.get('parameters', []):
                f_event[parameter['name']] = parameter.get('value', parameter.get('boolValue', parameter.get('intValue', str(parameter.get('multiValue', '')))))

        except Exception as ex:
            logging.exception(str(ex))

        return f_event

    def flat_json(self) -> dict:
        flattened = {}
        for key in self.application_reports:
            flattened[key] = []
            logging.info(f'Flattening: {key}')
            for activity in self.application_reports[key]:
                f_activity = self.__build_flat_activity(activity)
                if len(activity['events']) > 0:
                    for event in activity['events']:
                        event_dict = self.__build_flat_event(event)
                        event_dict.update(f_activity)
                        flattened[key].append(event_dict)
                else:
                    flattened[key].append(f_activity)

        return flattened

    def flat_json_dump(self, out_file):
        with open(out_file, 'w', encoding='utf-8') as of:
            json.dump(self.flat_json(), of, indent=4)

    def excel(self, workbook_path):
        workbook = xlsxwriter.Workbook(workbook_path)
        flat_j = self.flat_json()

        worksheet = workbook.add_worksheet()
        worksheet.name = 'Summary'

        worksheet.write(0, 0, 'Application')
        worksheet.write(0, 1, 'Event Count')
        row = 1
        for key in flat_j:
            worksheet.write(row, 0, key)
            worksheet.write(row, 1, len(flat_j[key]))
            row += 1

        worksheet = workbook.add_worksheet()
        worksheet.name = 'IP Addresses'

        if len(self.enriched_ip_addresses) > 0:
            logging.info('Writing IP Address Details')
            flattened = json_converters.flatten_json(self.enriched_ip_addresses)
            headers = json_converters.read_fields(flattened)
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

        for key in flat_j:
            logging.info(f'Writing application name {key} to Excel Workbook')
            worksheet = workbook.add_worksheet()
            worksheet.name = key
            headers = json_converters.read_fields(flat_j[key])

            row = 0
            col = 0

            for header in headers:
                worksheet.write(row, col, header)
                col += 1

            for entry in flat_j[key]:
                col = 0
                row += 1
                for header in headers:
                    worksheet.write(row, col, entry.get(header, ''))
                    col += 1

        logging.info(f'Saving Workbook: {workbook_path}')
        workbook.close()

    def to_elasticsearch(self, server, port, api_key, index, use_etag_for_id=False):
        # TODO: To Implement
        raise NotImplemented('To Be Implemented')
