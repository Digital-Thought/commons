import glob
import json
import logging
import pathlib
import re

from .. import internet
from .bulkProcessor import BulkProcessor
from .scrollQuery import ScrollQuery
from elasticsearch import Elasticsearch

import base64


class ElasticsearchConnection:

    def __init__(self, server, port, api_key):
        self.api_key = api_key
        self.root_url = 'https://{}:{}/'.format(server, port)
        self.root_directory = str(pathlib.Path(__file__).parent.absolute()) + '/../_resources/elasticsearch'
        self.request_session = internet.retry_request_session(
            headers={'Authorization': 'ApiKey {}'.format(self.api_key)})
        self.api_key_id = base64.b64decode(api_key.encode(encoding='utf-8')).decode("utf-8").split(':')[0]
        self.api_key_instance = base64.b64decode(api_key.encode(encoding='utf-8')).decode("utf-8").split(':')[1]
        self.elasticsearch_client = Elasticsearch('https://{}:{}/'.format(server, port), api_key=self.api_key)

        response = self.request_session.get(self.root_url)
        if response.status_code != 200 or not self.is_cluster_healthy():
            raise Exception(
                "Failed to connect to Elasticsearch server or cluster status is not healthy: {}".format(self.root_url))

        logging.getLogger('elastic').info("Successfully connected to: {}".format(self.root_url))

    def __enter__(self):
        return self

    def close(self):
        self.request_session.close()
        self.elasticsearch_client.close()

    def __exit__(self, type, value, traceback):
        self.close()

    def get_client(self) -> Elasticsearch:
        return self.elasticsearch_client

    def flush_index(self, index: str) -> dict:
        return self.request_session.post(self.root_url + index + '/_flush').json()

    def delete_by_id(self, index: str, _id: str):
        return self.elasticsearch_client.delete(index=index, id=_id)

    def install_component_template(self, template_name, template, description=None, version=None, requires_prefix=None):
        if template_name not in self.loaded_component_templates():
            if '_meta' not in template and (description is None or version is None or requires_prefix is None):
                raise Exception("Template does not contain all required _meta fields [description, version, requires_prefix]")
            elif '_meta' not in template:
                template['_meta'] = {'description': description, 'version': version, 'requires_prefix': requires_prefix}

            logging.getLogger('elastic').info('Creating Component Template: {}'.format(template_name))
            resp = self.request_session.put(self.root_url + '_component_template/' + template_name, json=template).json()
            if not resp['acknowledged']:
                logging.getLogger('elastic').error(
                    'Failed to create Component Template {}.  Error: {}'.format(template_name, str(resp)))
                raise Exception(
                    'Failed to create Component Template {}.  Error: {}'.format(template_name, str(resp)))

            return {'status': 'created'}
        return {'status': 'already_present'}

    def install_lifecycle_policy(self, policy_name, policy, description=None, version=None, requires_prefix=None):
        if policy_name not in self.loaded_lifecycle_policies():
            if '_meta' not in policy and (description is None or version is None or requires_prefix is None):
                raise Exception("Policy does not contain all required _meta fields [description, version, requires_prefix]")
            elif '_meta' not in policy:
                policy['_meta'] = {'description': description, 'version': version, 'requires_prefix': requires_prefix}

            logging.getLogger('elastic').info('Creating Lifecycle Policy: {}'.format(policy_name))
            resp = self.request_session.put(self.root_url + '_ilm/policy/' + policy_name, json=policy).json()
            if not resp['acknowledged']:
                logging.getLogger('elastic').error('Failed to create ILM Policy {}.  Error: {}'.format(policy_name, str(resp)))
                raise Exception('Failed to create ILM Policy {}.  Error: {}'.format(policy_name, str(resp)))

            return {'status': 'created'}
        return {'status': 'already_present'}

    def install_index_template(self, template_name, template, prefix=None, description=None, version=None, requires_prefix=None):
        if '_meta' not in template and (description is None or version is None or requires_prefix is None):
            raise Exception("Index Template does not contain all required _meta fields [description, version, requires_prefix]")
        elif '_meta' not in template:
            template['_meta'] = {'description': description, 'version': version, 'requires_prefix': requires_prefix}

        if template['_meta']['requires_prefix']:
            if prefix is None:
                logging.getLogger('elastic').error('Failed to Index Template {}.  Missing required prefix'.format(template_name))
                raise Exception('Failed to Index Template {}.  Missing required prefix'.format(template_name))
            if not re.compile('^[a-z0-9-]+$').match(prefix) or prefix.endswith('-') or not re.compile('^[a-z]+$').match(prefix[0]):
                logging.getLogger('elastic').error(
                    'Invalid Prefix {}.  Can only contain lowercase letters, numbers and -.  Must not end with - and must start with letter'.format(prefix))
                raise Exception('Invalid Prefix {}.  Can only contain lowercase letters, numbers and -.  Must not end with - and must start with letter'.format(prefix))

            template_name = '{}-{}'.format(prefix, template_name)
            index_patterns = []
            for pattern in template['index_patterns']:
                index_patterns.append(pattern.replace('<prefix>', prefix))
            template['index_patterns'] = index_patterns
            template['template']['settings']['index.lifecycle.rollover_alias'] = template['template']['settings']['index.lifecycle.rollover_alias'].replace('<prefix>', prefix)

        if template_name not in self.loaded_index_templates():
            missing_components = []
            if 'composed_of' in template:
                for component in template['composed_of']:
                    if component not in self.loaded_component_templates() and component not in self.default_component_templates():
                        missing_components.append(component)
                if len(missing_components) > 0:
                    logging.getLogger('elastic').error('Missing required template component: {}'.format(str(missing_components)))
                    raise Exception('Missing required template component: {}'.format(str(missing_components)))

                for component in template['composed_of']:
                    if component not in self.loaded_component_templates():
                        self.install_component_template(component, self.default_component_templates()[component])

            if 'index.lifecycle.name' in template['template']['settings']:
                required_lcp = template['template']['settings']['index.lifecycle.name']
                if required_lcp not in self.loaded_lifecycle_policies() and required_lcp not in self.default_lifecycle_policies():
                    logging.getLogger('elastic').error('Missing required Lifecycle Policy: {}'.format(required_lcp))
                    raise Exception('Missing required Lifecycle Policy: {}'.format(required_lcp))

                self.install_lifecycle_policy(required_lcp, self.default_lifecycle_policies()[required_lcp])

            resp = self.request_session.put(self.root_url + '_index_template/' + template_name, json=template).json()
            if not resp['acknowledged']:
                logging.getLogger('elastic').error('Failed to create Template {}.  Error: {}'.format(template_name, str(resp)))
                raise Exception('Failed to create Template {}.  Error: {}'.format(template_name, str(resp)))

            alias_name = template['template']['settings']['index.lifecycle.rollover_alias']
            create_index_json = {'aliases': {alias_name: {'is_write_index': True}}}
            logging.getLogger('elastic').info('Creating Initial Index for Template: {}'.format(template_name))
            resp = self.request_session.put(self.root_url + template_name + '-000001', json=create_index_json)
            logging.getLogger('elastic').info(resp.content)

            return {'status': 'created'}

        return {'status': 'already_present'}

    def default_component_templates(self):
        component_templates = {}
        for template_file in glob.glob(self.root_directory + "/component_templates/*.json"):
            template_name = template_file.replace('.json', '').replace(self.root_directory, '') \
                .replace('\\', '').replace('/', '').replace('component_templates', '')
            with open(template_file) as template_json_file:
                template_json = json.load(template_json_file)
            component_templates[template_name] = template_json
        return component_templates

    def default_index_templates(self):
        index_templates = {}
        for template_file in glob.glob(self.root_directory + "/index_templates/*.json"):
            template_name = template_file.replace('.json', '').replace(self.root_directory, '') \
                .replace('\\', '').replace('/', '').replace('index_templates', '')
            with open(template_file) as template_json_file:
                template_json = json.load(template_json_file)
            index_templates[template_name] = template_json
        return index_templates

    def default_lifecycle_policies(self):
        lifecycle_policies = {}
        for ilm_file in glob.glob(self.root_directory + "/lifecycles/*.json"):
            ilm_name = ilm_file.replace('.json', '').replace(self.root_directory, '') \
                .replace('\\', '').replace('/', '').replace('lifecycles', '')
            with open(ilm_file) as ilm_json_file:
                _json = json.load(ilm_json_file)
            lifecycle_policies[ilm_name] = _json
        return lifecycle_policies

    def loaded_component_templates(self):
        component_templates = []
        for c_temp in self.request_session.get(self.root_url + '_component_template').json()['component_templates']:
            component_templates.append(c_temp['name'])
        return component_templates

    def loaded_index_templates(self):
        index_templates = []
        for i_temp in self.request_session.get(self.root_url + '_index_template').json()['index_templates']:
            index_templates.append(i_temp['name'])
        return index_templates

    def loaded_lifecycle_policies(self):
        lifecycle_policies = []
        for lc_temp in self.request_session.get(self.root_url + '_ilm/policy').json():
            lifecycle_policies.append(lc_temp)
        return lifecycle_policies

    def get_cluster_health(self):
        return self.request_session.get(self.root_url + '_cluster/health').json()

    def is_cluster_healthy(self):
        try:
            json = self.get_cluster_health()
            if json['status'] == 'yellow':
                logging.getLogger('elastic').warning("Cluster is healthy.  However, it is in a YELLOW state. Recommend a check of the cluster.")
            return json['status'] != 'red'
        except Exception as ex:
            logging.getLogger('elastic').exception()
            logging.getLogger("elastic").exception()
            return False

    def bulk_processor(self, batch_size=1000, batch_max_size_bytes=5000000):
        return BulkProcessor(request_session=self.request_session, root_url=self.root_url, batch_size=batch_size, batch_max_size_bytes=batch_max_size_bytes)

    def index_document(self, index, document, _id=None):
        if _id is None:
            _id = ''
        index_url = self.root_url + '{}/_doc/{}'.format(index, _id)
        response = self.request_session.post(index_url, json=document)

        index_resp = {'status_code': response.status_code, 'elastic': response.json()}
        return index_resp

    def find_by_term(self, index, term, value):
        query = {'query': {'terms': {term: value}}}
        response = self.request_session.get(self.root_url + '{}/_search'.format(index), json=query)
        search_resp = {'status_code': response.status_code, 'elastic': response.json()}
        return search_resp

    def find_by_id(self, index, _id, alias_index=True):
        if not alias_index:
            return self.request_session.get('{}{}/_doc/{}'.format(self.root_url, index, _id)).json()
        else:
            query = {"query": {"bool": {"filter": {"term": {"_id": _id}}}}}
            response = self.request_session.get(self.root_url + '{}/_search'.format(index), json=query).json()
            if response['hits']['total']['value'] > 1:
                raise Exception(f'ID: {_id} has returned {response["hits"]["total"]["value"]} result.  Expected only 1 or 0 entries.')
            elif response['hits']['total']['value'] == 0:
                return {'_index': index, '_type': '_doc', '_id': _id, 'found': False}
            else:
                return {'_index': response['hits']['hits'][0]['_index'], '_type': '_doc', '_id': _id, 'found': True, '_source': response['hits']['hits'][0]['_source']}

    def get_scroller(self):
        return ScrollQuery(request_session=self.request_session, root_url=self.root_url)

    def aggregation(self, index, query, aggregation_name):
        json_data = self.raw_aggregation(index, query)
        if "aggregations" in json_data and aggregation_name in json_data['aggregations']:
            return json_data['aggregations'][aggregation_name]['buckets']

        return []

    def raw_aggregation(self, index, query):
        response = self.request_session.get(self.root_url + '{}/_search'.format(index), json=query)
        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()
