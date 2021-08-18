import logging
import os
import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from digital_thought_commons.google.workspace import audit_report

AUDIT_REPORTING_SCOPES = SCOPES = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
USER_TOKENS_DIRECTORY = f'{str(Path.home())}/.google_tokens/'

APPLICATION_NAMES = ['ACCESS_TRANSPARENCY', 'ADMIN', 'CALENDAR', 'CHAT', 'DRIVE', 'GCP', 'GPLUS', 'GROUPS', 'GROUPS_ENTERPRISE', 'JAMBOARD', 'LOGIN', 'MEET', 'MOBILE', 'RULES',
                     'SAML', 'TOKEN', 'USER_ACCOUNTS', 'CONTEXT_AWARE_ACCESS', 'CHROME', 'DATA_STUDIO']


def authenticate(client_secret_json, client_id, scopes, local_server_port=8000):
    os.makedirs(USER_TOKENS_DIRECTORY, exist_ok=True)
    client_token_file = f'{USER_TOKENS_DIRECTORY}{client_id}.json'
    creds = None

    logging.info(f'Attempting authentication for {client_id} with scopes: {scopes}')
    if os.path.exists(client_token_file):
        logging.info(f'Using previous token file: {client_token_file}')
        try:
            creds = Credentials.from_authorized_user_file(client_token_file, scopes)
        except Exception as ex:
            logging.error(str(ex))
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.warning(f'Previous authentication token {client_token_file} has expired.  Refreshing authentication.')
            creds.refresh(Request())
        else:
            logging.info(f'No previous authentication token.  Attempting authentication.')
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_json, scopes)
            logging.info(f'Starting flow server on: http://localhost:{local_server_port}/')
            creds = flow.run_local_server(port=local_server_port)

        with open(client_token_file, 'w') as token:
            logging.info(f'Updating authentication token: {client_token_file}')
            token.write(creds.to_json())

    return creds


def obtain_audit_reports(credentials, application_names=None) -> audit_report.AuditReport:
    if application_names is None:
        application_names = APPLICATION_NAMES

    report = audit_report.AuditReport()
    service = build('admin', 'reports_v1', credentials=credentials)
    for application_name in application_names:
        logging.info(f'Obtaining audit reports for: {application_name}')
        results = service.activities().list(userKey='all', applicationName=application_name.lower()).execute()
        report.add(application_name, results.get('items', []))

    return report
