import datetime
import datetime as dt
import logging
import iso8601
import pytz

DATE_FORMATS = ['%d. %b %Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%B %d, %Y', '%d %B, %Y', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%B %d, %Y',
                '%Y-%m-%d %H:%M:%S', '%d%B %Y %H:%M:%S', '%b %d, %Y.', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%B %d, %Y',
                '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y', '%m/%d/%Y %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d', '%Y-%m-%d', '%a %b %d %Y',
                '%Y-%m-%d', '%a, %d %b %Y %H:%M:%S', '%A, %B %d, %Y %H:%M', '%Y-%m-%d %H:%M:%S.%f', '%a, %d %b %Y %H:%M:%S',
                '%B %d, %Y at %H:%M %p', '%B %d, %Y at %H:%M %p', '%A, %d %B %Y %H:%M:%S', '%a, %d %b %Y %H:%M:%S %z']

TZ_ABR_OFFSETS = {'ACDT': '+1030', 'ACST': '+0930', 'ACT': '−0500', 'ACWST': '+0845', 'ADT': '−0300', 'AEDT': '+1100',
                  'AEST': '+1000', 'AFT': '+0430', 'AKDT': '−0800', 'AKST': '−0900', 'ALMT': '+0600', 'AMST': '−0300',
                  'AMT': '−0400', 'AMT': '+0400', 'ANAT': '+1200', 'AQTT': '+0500', 'ART': '−0300', 'AST': '+0300',
                  'AST': '−0400', 'AWST': '+0800', 'AZOT': '−0100', 'AZT': '+0400', 'BNT': '+0800', 'BIOT': '+0600',
                  'BIT': '−1200', 'BOT': '−0400', 'BRST': '−0200', 'BRT': '−0300', 'BST': '+0600', 'BST': '+1100',
                  'BST': '+0100', 'BTT': '+0600', 'CAT': '+0200', 'CCT': '+0630', 'CDT': '−0500', 'CDT': '−0400',
                  'CEST': '+0200', 'CET': '+0100', 'CHADT': '+1345', 'CHAST': '+1245', 'CHOT': '+0800',
                  'CHOST': '+0900', 'CHST': '+1000', 'CHUT': '+1000', 'CIST': '−0800', 'CKT': '−1000', 'CLST':
                      '−0300', 'CLT': '−0400', 'COST': '−0400', 'COT': '−0500', 'CST': '−0600', 'CST': '+0800',
                  'CST': '−0500', 'CVT': '−0100', 'CWST': '+0845', 'CXT': '+0700', 'DAVT': '+0700', 'DDUT': '+1000',
                  'DFT': '+0100', 'EASST': '−0500', 'EAST': '−0600', 'EAT': '+0300', 'ECT': '−0400', 'ECT': '−0500',
                  'EDT': '−0400', 'EEST': '+0300', 'EET': '+0200', 'EGST': '±0000', 'EGT': '−0100', 'EST': '−0500',
                  'FET': '+0300', 'FJT': '+1200', 'FKST': '−0300', 'FKT': '−0400', 'FNT': '−0200', 'GALT': '−0600',
                  'GAMT': '−0900', 'GET': '+0400', 'GFT': '−0300', 'GILT': '+1200', 'GIT': '−0900', 'GMT': '±0000',
                  'GST': '−0200', 'GST': '+0400', 'GYT': '−0400', 'HDT': '−0900', 'HAEC': '+0200', 'HST': '−1000',
                  'HKT': '+0800', 'HMT': '+0500', 'HOVST': '+0800', 'HOVT': '+0700', 'ICT': '+0700', 'IDLW': '−1200',
                  'IDT': '+0300', 'IOT': '+0300', 'IRDT': '+0430', 'IRKT': '+0800', 'IRST': '+0330', 'IST': '+0530',
                  'IST': '+0100', 'IST': '+0200', 'JST': '+0900', 'KALT': '+0200', 'KGT': '+0600', 'KOST': '+1100',
                  'KRAT': '+0700', 'KST': '+0900', 'LHST': '+1030', 'LHST': '+1100', 'LINT': '+1400', 'MAGT': '+1200',
                  'MART': '−0930', 'MAWT': '+0500', 'MDT': '−0600', 'MET': '+0100', 'MEST': '+0200', 'MHT': '+1200',
                  'MIST': '+1100', 'MIT': '−0930', 'MMT': '+0630', 'MSK': '+0300', 'MST': '+0800', 'MST': '−0700',
                  'MUT': '+0400', 'MVT': '+0500', 'MYT': '+0800', 'NCT': '+1100', 'NDT': '−0230', 'NFT': '+1100',
                  'NOVT': '+0700', 'NPT': '+0545', 'NST': '−0330', 'NT': '−0330', 'NUT': '−1100', 'NZDT': '+1300',
                  'NZST': '+1200', 'OMST': '+0600', 'ORAT': '+0500', 'PDT': '−0700', 'PET': '−0500', 'PETT': '+1200',
                  'PGT': '+1000', 'PHOT': '+1300', 'PHT': '+0800', 'PHST': '+0800', 'PKT': '+0500', 'PMDT': '−0200',
                  'PMST': '−0300', 'PONT': '+1100', 'PST': '−0800', 'PWT': '+0900', 'PYST': '−0300', 'PYT': '−0400',
                  'RET': '+0400', 'ROTT': '−0300', 'SAKT': '+1100', 'SAMT': '+0400', 'SAST': '+0200', 'SBT': '+1100',
                  'SCT': '+0400', 'SDT': '−1000', 'SGT': '+0800', 'SLST': '+0530', 'SRET': '+1100', 'SRT': '−0300',
                  'SST': '−1100', 'SST': '+0800', 'SYOT': '+0300', 'TAHT': '−1000', 'THA': '+0700', 'TFT': '+0500',
                  'TJT': '+0500', 'TKT': '+1300', 'TLT': '+0900', 'TMT': '+0500', 'TRT': '+0300', 'TOT': '+1300',
                  'TVT': '+1200', 'ULAST': '+0900', 'ULAT': '+0800', 'UTC': '±0000', 'UYST': '−0200', 'UYT': '−0300',
                  'UZT': '+0500', 'VET': '−0400', 'VLAT': '+1000', 'VOLT': '+0400', 'VOST': '+0600', 'VUT': '+1100',
                  'WAKT': '+1200', 'WAST': '+0200', 'WAT': '+0100', 'WEST': '+0100', 'WET': '±0000', 'WIB': '+0700',
                  'WIT': '+0900', 'WITA': '+0800', 'WGST': '−0200', 'WGT': '−0300', 'WST': '+0800', 'YAKT': '+0900',
                  'YEKT': '+0500'}


def lookup_abbreviated_timezone(datetime, abbreviation):
    for tz in pytz.all_timezones:
        if abbreviation == pytz.timezone(tz).tzname(datetime):
            return pytz.timezone(tz)


def convert_date_time_zscaler(datetime_str):
    try:
        timezone = datetime_str.split(' ')[-1].strip()
        datetime_str = datetime_str[:len(datetime_str) - len(timezone)].strip()
        datetime = dt.datetime.strptime(datetime_str, '%B %d, %Y %I:%M:%S %p')
        timezone = lookup_abbreviated_timezone(datetime, timezone)
        return timezone.localize(datetime)
    except Exception as ex:
        logging.error("Error processing date: {} - {}".format(datetime_str, ex))
        raise ex


def convert_string_datetime(string: str, timezone=pytz.UTC, before_current_datetime=True) -> dt.datetime:
    """
    Attempts to convert a string representation of date or date/time into a datetime.datetime object.

    If a timezone is not determined from the conversion, the timezone will be assumed & set as 'timezone'.
    (e.g. '2021-07-10T06:28:59' will be returned as a datetime object of the value '2021-07-10T06:28:59+00:00' if timezone is set to UTC)

    If a timezone is determined from the converted string, it will be converted to a date/time for the provided 'timezone'
    (e.g. '2021-07-10T06:28:59+1000' will be returned as a datetime object of the value '2021-07-09T20:28:59+00:00' if timezone is set to UTC)

    :param string: the string version of a date/time.
    :type string: str
    :param timezone: the timezone to assume if one not determined.  The timezone to convert to. Defaults to UTC.
    :type timezone: tzinfo
    :param before_current_datetime: if True and a converted datetime is found to be after the current datetime, it will assume is incorrect and try other formats.  Defaults to True
    :type before_current_datetime: bool
    :return: the converted datetime.datetime object
    :rtype: dt.datetime
    """
    date_time = None
    try:
        date_time = iso8601.parse_date(string, default_timezone=timezone)
    except:
        for key in TZ_ABR_OFFSETS:
            if key in string:
                string = string.replace(key, f'{TZ_ABR_OFFSETS[key].replace("−", "-")}')
                break
        if not date_time:
            for format in DATE_FORMATS:
                try:
                    date_time = dt.datetime.strptime(string, format)
                    if date_time > dt.datetime.now() and before_current_datetime:
                        date_time = None
                except:
                    continue
                if date_time:
                    break

        if not date_time:
            raise Exception(f"Unable to convert {string} to datetime")

    if not date_time.tzname():
        date_time = timezone.localize(date_time)
    else:
        date_time = date_time.astimezone(timezone)

    return date_time


def convert_to_utc(datetime):
    return datetime.astimezone(pytz.UTC)


def convert_to_epoch_mills(datetime):
    return int(round(datetime.timestamp() * 1000))


def utc_epoch_mills_now():
    return convert_to_epoch_mills(convert_to_utc(dt.datetime.now()))


def epoch_mills_to_date_time(mills: int, timezone=pytz.UTC):
    return datetime.datetime.fromtimestamp(mills / 1000.0, tz=timezone)



