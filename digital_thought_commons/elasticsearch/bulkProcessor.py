import json
import logging
from typing import List


class BulkProcessedItem:

    def __init__(self, result: str, index: str, id_: str, error: dict = None) -> None:
        self.result: str = result
        self.index: str = index
        self.id_: str = id_
        self.error: dict = error

    @classmethod
    def build(cls, response: dict):
        if 'result' not in response:
            item = cls(result='error', index=response['_index'], id_=response['_id'])
            item.error = response['error']
        else:
            item = cls(result=response['result'], index=response['_index'], id_=response['_id'])

        return item


class BulkProcessorListener:

    def created(self, entries: List[BulkProcessedItem]):
        raise NotImplementedError

    def updated(self, entries: List[BulkProcessedItem]):
        raise NotImplementedError

    def errors(self, entries: List[BulkProcessedItem]):
        raise NotImplementedError

    def no_changes(self, entries: List[BulkProcessedItem]):
        raise NotImplementedError


class BulkProcessor:

    def __init__(self, request_session, root_url, batch_size, batch_max_size_bytes) -> None:
        super().__init__()
        self.request_session = request_session
        self.entries = ""
        self.batch_size = batch_size
        self.batch_max_size_bytes = batch_max_size_bytes
        self.root_url = root_url
        self.current_batch_size = 0
        self.listeners: List[BulkProcessorListener] = []
        self.results = {"created": 0, "updated": 0, "errors": 0, "error_entries": []}

    def __enter__(self):
        return self

    def add_listener(self, listener: BulkProcessorListener):
        self.listeners.append(listener)

    def remove_listener(self, listener: BulkProcessorListener):
        self.listeners.remove(listener)

    def __process_listeners(self, resp: dict):
        created = []
        updated = []
        errors = []
        noops = []

        for item in resp['items']:
            for key in item:
                entry = BulkProcessedItem.build(item[key])
                if entry.result == 'updated':
                    updated.append(entry)
                elif entry.result == 'created':
                    created.append(entry)
                elif entry.result == 'error':
                    errors.append(entry)
                elif entry.result == 'noop':
                    noops.append(entry)
                else:
                    logging.error(f'Unexpected response for item in BulkProcessor while processing listeners: {json.dumps(item)}')

        for listener in self.listeners:
            if len(created) > 0:
                listener.created(created)
            if len(updated) > 0:
                listener.updated(updated)
            if len(errors) > 0:
                listener.errors(errors)
            if len(noops) > 0:
                listener.no_changes(noops)

    def process_batch(self):
        if self.current_batch_size == 0:
            logging.getLogger('elastic').warning("Request to process batch was made.  But batch is currently empty.")
            return

        logging.getLogger('elastic').info("Processing Bulk Index Batch. Size: {}".format(str(self.current_batch_size)))
        headers = self.request_session.headers
        headers['Content-Type'] = 'application/x-ndjson'
        r = self.request_session.post(self.root_url + "/_bulk", data=self.entries, headers=headers)
        if r.status_code >= 400:
            logging.getLogger('elastic').error("Bulk index returned Error Code: {} [{}]".format(str(r.status_code), r.content))

        self.entries = ""
        self.current_batch_size = 0

        try:
            resp_json = r.json()
            self.__process_listeners(resp_json)
            took = resp_json['took']
            errors = resp_json['errors']
            stats = {'errors': 0}

            if errors:
                logging.getLogger('elastic').error('An Error occurred while performing the bulk index')

            for item in resp_json['items']:
                if "index" in item:
                    if 'error' in item['index']:
                        stats['errors'] = stats['errors'] + 1
                        error_msg = "Error of Type: {}.  Caused by: {}. For Document ID: {}, in Index: {}" \
                            .format(item['index']['error']['type'], item['index']['error']['reason']
                                    , item['index']['_id'], item['index']['_index'])
                        logging.getLogger('elastic').error(error_msg)
                    else:
                        if item['index']['result'] not in stats:
                            stats[item['index']['result']] = 0

                        stats[item['index']['result']] = stats[item['index']['result']] + 1

            msg = ''
            for key, value in stats.items():
                if len(msg) > 0:
                    msg = msg + ',\t'
                msg = msg + key + ': ' + str(value)
            logging.getLogger('elastic').info("Bulk index took: {}, with the following results: {}".format(str(took), msg))

        except Exception as ex:
            logging.getLogger('elastic').exception("Error: {}.  Response: {}".format(str(ex), str(r.json)))
            raise ex

    def _check_for_processing(self):
        if len(self.entries.encode('utf-8')) > self.batch_max_size_bytes:
            logging.getLogger('elastic').warning("Length of entries exceeds {} bytes.  Processing current batch before adding new entry.".format(self.batch_max_size_bytes))
            self.process_batch()
        elif self.current_batch_size >= self.batch_size:
            if len(self.entries) <= 5:
                logging.getLogger('elastic').warning("Batch size is {}, but length of content is {}. Content: {}"
                                                     .format(str(self.batch_size), str(len(self.entries)), self.entries))
            self.process_batch()

    def delete(self, index, _id):
        self._check_for_processing()
        self.entries = self.entries + json.dumps({"delete": {"_index": index, "_id": _id}}) + "\n"
        self.current_batch_size += 1
        self._check_for_processing()

    def update(self, index, entry, _id):
        self._check_for_processing()
        self.entries = self.entries + json.dumps({"update": {"_index": index, "_id": _id}}) + "\n"
        self.entries = self.entries + json.dumps({"doc": entry}) + "\n"
        self.current_batch_size += 1
        self._check_for_processing()

    def index(self, index, entry, _id=None):
        self._check_for_processing()

        if _id is not None:
            self.entries = self.entries + json.dumps({"index": {"_index": index, "_id": _id}}) + "\n"
        else:
            self.entries = self.entries + json.dumps({"index": {"_index": index}}) + "\n"
        self.entries = self.entries + json.dumps(entry) + "\n"
        self.current_batch_size += 1
        self._check_for_processing()

    def create(self, index, entry, _id=None):
        self._check_for_processing()

        if _id is not None:
            self.entries = self.entries + json.dumps({"create": {"_index": index, "_id": _id}}) + "\n"
        else:
            self.entries = self.entries + json.dumps({"create": {"_index": index}}) + "\n"
        self.entries = self.entries + json.dumps(entry) + "\n"
        self.current_batch_size += 1
        self._check_for_processing()

    def close(self):
        self.process_batch()
        return self.results

    def __exit__(self, type, value, traceback):
        self.process_batch()
