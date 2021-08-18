# Google Workspace API Interface

## Creation of client_secret.json
To use the Google API, it is necessary to define API under "APIs & Services".
You will require "Admin" level access to the Google G Suite workspace in order to setup this API.

<ol>
    <li>Login to Google G Suite as an Administrator privileged account</li>
    <li>Visit the 'Google Cloud Platform' (https://console.cloud.google.com/)</li>
    <li>Create a 'New Project'</li>
    <li>Select 'APIs & Services</li>
    <li>Select 'Library' and enable the 'Admin SDK API'</li>
    <li>Select 'OAuth consent screen'</li>
    <li>Configure OAuth as an 'External' application</li>
    <li>Add the test users that are permitted to utilise the APP</li>
    <li>Enter and App name, User support email, developer contact information</li>
    <li>Add the following scopes: .../auth/admin.reports.audit.readonly, .../auth/admin.reports.usage.readonly</li>
    <li>Select 'Credentials'</li>
    <li>Create an OAuth 2.0 credential.  Application type: Web</li>
    <li>Assign a name</li>
    <li>Add the URL 'http://localhost:8000/' as the authorised redirect URL</li>
    <li>Download the client secret JSON</li>
</ol>

## Using the Library
Note: Library supports LOGGING.

### Authenticating

````python
from digital_thought_commons.google import workspace

credentials = workspace.authenticate(client_secret_json='client_secret.json', 
                client_id='ID OF CLIENT', scopes=workspace.AUDIT_REPORTING_SCOPES)
````

### Running an Audit Report

````python
from digital_thought_commons.google import workspace

credentials = workspace.authenticate(client_secret_json='client_secret.json', 
                client_id='ID OF CLIENT', scopes=workspace.AUDIT_REPORTING_SCOPES)
report = workspace.obtain_audit_reports(credentials=credentials)
````

By default, the report will be run over the following Google G Suite Applications:

<ul>ACCESS_TRANSPARENCY, ADMIN, CALENDAR, CHAT, DRIVE, GCP, GPLUS, GROUPS, GROUPS_ENTERPRISE, 
JAMBOARD, LOGIN, MEET, MOBILE, RULES, SAML, TOKEN, USER_ACCOUNTS, CONTEXT_AWARE_ACCESS, CHROME, DATA_STUDIO</ul>

You can specify which applications to run the report over by:

````python
from digital_thought_commons.google import workspace

credentials = workspace.authenticate(client_secret_json='client_secret.json', 
                client_id='ID OF CLIENT', scopes=workspace.AUDIT_REPORTING_SCOPES)
report = workspace.obtain_audit_reports(credentials=credentials, application_names=['ACCESS_TRANSPARENCY', 'ADMIN'])
````

### Working with the Report