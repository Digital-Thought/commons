import re
from typing import Tuple, List

FFF = re.compile(r'FBI\s*Friday', re.I)
LULZ = re.compile(r'(lulzsec|antisec)', re.I)
CISCO_HASH = re.compile(r'enable\s+secret', re.I)
CISCO_PWD = re.compile(r'enable\s+password', re.I)
GOOGLE_API = re.compile(r'\W(AIza.{35})')
HONEYPOT = re.compile(r'<dionaea\.capture>', re.I)
PGP_PRIV = re.compile(r'BEGIN PGP PRIVATE', re.I)
SSH_PRIV = re.compile(r'BEGIN RSA PRIVATE', re.I)
URL = re.compile(r"(?:http|ftp|https|hXXp|fXp|hXXps|hxxp|fxp|hxxps)://(?:[\w_-]+(?:(?:(?:\.|\[\.\]|\(\.\)|\{\.\})[\w_-]+)+))(?:[(\w.,'!)@?^=%&:/~+#-]*[\w@?^=%&/~+)])?",
                 re.IGNORECASE | re.MULTILINE)
IPV4 = re.compile(r'\b(?:(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(?:\.|\[\.\]|\(\.\)|\{\.\})){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))\b',
                  re.IGNORECASE | re.MULTILINE)
IPV6 = re.compile(r'(?<![:.\w])(?:[A-F0-9]{1,4}(?::|\[:\]|\{:\}|\(:\))){7}[A-F0-9]{1,4}(?![:.\w])', re.IGNORECASE | re.MULTILINE)
EMAIL = re.compile(r'[A-Z0-9._%+-]+(?:@|\[@\]|\(@\)|\{@\})(?:[A-Z0-9]|(?:\.|\[.\]|\(.\)|\{.\})|-)+(?:\.|\[.\]|\(.\)|\{.\})[A-Z]{2,4}', re.IGNORECASE | re.MULTILINE)
MD5 = re.compile(r'\b[a-f0-9]{32}\b', re.IGNORECASE | re.MULTILINE)
SHA1 = re.compile(r'\b[a-f0-9]{40}\b', re.IGNORECASE | re.MULTILINE)
SHA256 = re.compile(r'\b[a-f0-9]{64}\b', re.IGNORECASE | re.MULTILINE)

DOT_DEFANG_PATTERN = re.compile(r'\.|\[\.\]|\(\.\)|\{\.\}', re.IGNORECASE | re.MULTILINE)
COLON_DEFANG_PATTERN = re.compile(r':|\[:\]|\{:\}|\(:\)', re.IGNORECASE | re.MULTILINE)
AT_DEFANG_PATTERN = re.compile(r'@|\[@\]|\(@\)|\{@\}', re.IGNORECASE | re.MULTILINE)
HTTP_DEFANG = re.compile(r'hXXp:', re.IGNORECASE | re.MULTILINE)
HTTPS_DEFANG = re.compile(r'hXXps:', re.IGNORECASE | re.MULTILINE)
FTP_DEFANG = re.compile(r'fXp:', re.IGNORECASE | re.MULTILINE)


def get_email_addresses(text: str, defang: bool = True) -> List[Tuple[str, str]]:
    for match in EMAIL.findall(text):
        raw_value: str = match
        defanged: str = raw_value
        if defang:
            defanged = AT_DEFANG_PATTERN.sub('@', DOT_DEFANG_PATTERN.sub('.', raw_value))
        yield raw_value, defanged


def get_urls(text: str, defang: bool = True) -> List[Tuple[str, str]]:
    for match in URL.findall(text):
        raw_value: str = match
        defanged: str = raw_value
        if defang:
            defanged = FTP_DEFANG.sub('ftp:', HTTPS_DEFANG.sub('https:', HTTP_DEFANG.sub('http:', DOT_DEFANG_PATTERN.sub('.', raw_value))))
        yield raw_value, defanged


def get_ipv4s(text: str, defang: bool = True) -> List[Tuple[str, str]]:
    for match in IPV4.findall(text):
        raw_value: str = match
        defanged: str = raw_value
        if defang:
            defanged = DOT_DEFANG_PATTERN.sub('.', raw_value)
        yield raw_value, defanged


def get_ipv6s(text: str, defang: bool = True) -> List[Tuple[str, str]]:
    for match in IPV6.findall(text):
        raw_value: str = match
        defanged: str = raw_value
        if defang:
            defanged = COLON_DEFANG_PATTERN.sub(':', raw_value)
        yield raw_value, defanged
