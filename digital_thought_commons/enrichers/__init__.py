from digital_thought_commons import logging as logger
from digital_thought_commons.enrichers.ip_address_domain_details import IPAddressDomainInfo
from digital_thought_commons.converters import json as json_flattener
import logging
import argparse
import pathlib
import os
import json
import xlsxwriter


def value(dict_obj, key):
    if key not in dict_obj:
        return ""
    return dict_obj[key]


def save_reports(data, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(name=output_folder, exist_ok=True)

    logging.info("Saving JSON report")
    with open(output_folder + '/ip_address_report.json', 'w', encoding="UTF-8") as report_json:
        json.dump(data, report_json, indent=4)

    logging.info("Saving Excel report")
    workbook = xlsxwriter.Workbook(output_folder + '/ip_address_report_report.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.name = 'IP Addresses'
    flattened = json_flattener.flatten_json(data)
    headers = json_flattener.read_fields(flattened)
    row = 0
    col = 0

    for header in headers:
        worksheet.write(row, col, header)
        col += 1

    for entry in flattened:
        col = 0
        row += 1
        for header in headers:
            worksheet.write(row, col, value(entry, header))
            col += 1

    workbook.close()


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

def main():
    logger.init(app_name='digital-thought-ip-enrichment')
    version_info = "Unknown"
    with open("{}/../version".format(str(pathlib.Path(__file__).parent.absolute())), "r") as fh:
        version_info = fh.read()

    arg_parser = argparse.ArgumentParser(prog='python -m digital_thought_commons.enrichers',
                                         description='Enrich details for a list of IP addresses')
    arg_parser.add_argument('--input', action='store', type=str, required=True, help="Path to TXT file with list of "
                                                                                     "IP Addresses.  One IP Address "
                                                                                     "per line.")
    arg_parser.add_argument('--output', action='store', type=str, required=True, help="The directory to save report")
    arg_parser.add_argument('--ipabusedb', action='store', type=str, required=False, help="AbuseIPDB API Key")
    arg_parser.add_argument('--ipstack', action='store', type=str, required=False, help="IPStack API Key")
    arg_parser.add_argument('--viewdns', action='store', type=str, required=False, help="ViewDNS API Key")
    arg_parser.add_argument('--maxmind', action='store', type=str, required=False, help="Maxmind API Key")
    arg_parser.add_argument('--virustotal', action='store', type=str, required=False, help="VirusTotal API Key")

    args = arg_parser.parse_args()

    logging.info(f"IP Address Enrichment Processor, version: {version_info}")

    if os.path.exists(args.input) and os.path.isfile(args.input):
        api_keys = {}
        if args.ipabusedb:
            api_keys["ipabusedb"] = args.ipabusedb
        if args.ipstack:
            api_keys["ipstack"] = args.ipstack
        if args.viewdns:
            api_keys["viewdns"] = args.viewdns
        if args.ipabusedb:
            api_keys["maxmind"] = args.maxmind
        if args.virustotal:
            api_keys["virustotal"] = args.virustotal
        enricher = IPAddressDomainInfo(api_keys=api_keys)
        details = []
        with open(args.input, encoding="utf-8", mode='r') as input_txt_file:
            for ip in input_txt_file.readlines():
                logging.info(f'Enriching IP Address: {ip.strip()}')
                try:
                    details.append(enricher.lookup_ip_address(ip_address=ip.strip(), advanced=True))
                except Exception as ex:
                    logging.exception(f'Error encountered while enriching IP Address: {ip}.  Error: {str(ex)}')

        save_reports(details, output_folder=args.output)

    else:
        logging.error(f'The input file {args.input} does not exist or is not a file.')


if __name__ == '__main__':
    main()
