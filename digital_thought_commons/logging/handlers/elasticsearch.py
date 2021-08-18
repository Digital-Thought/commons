import logging
import traceback
from logging import LogRecord

from digital_thought_commons import elasticsearch


class ElasticsearchLogHandler(logging.Handler):

    def __init__(self, prefix, server, port, api_key):
        super().__init__()
        self.prefix = prefix
        self.server = server
        self.port = port
        self.api_key = api_key

        self.elastic = elasticsearch.ElasticsearchConnection(server=self.server, port=self.port, api_key=self.api_key)
        self.__initialise_index()
        self.bulk_indexer = self.elastic.bulk_processor(batch_size=2)

    def __initialise_index(self):
        template = self.elastic.default_index_templates()['event-logs-v1']
        self.elastic.install_index_template(template_name='event-logs-v1', template=template, prefix=self.prefix)

    def flush(self) -> None:
        super().flush()
        self.bulk_indexer.process_batch()

    def close(self) -> None:
        super().close()
        self.bulk_indexer.close()

    def emit(self, record: LogRecord) -> None:
        self.bulk_indexer.index(index='{}-event-logs'.format(self.prefix), entry=self.__build_record(record))

    def __build_exception_details(self, record):
        exception_stack = ""
        if record.exc_info is None:
            return None
        for ex in record.exc_info:
            try:
                exception_stack += str(traceback.format_tb(ex)) + '\n'
            except:
                exception_stack += str(ex) + '\n'
        return {'exception_text': None if record.exc_text is None else str(record.exc_text),
                'exception_info': None if record.exc_info is None else exception_stack.strip()}

    def __build_record_details(self, record):
        return {'filename': record.filename, 'function_name': record.funcName, 'level_number': record.levelno, 'line_number': record.lineno, 'module': record.module,
                'msecs': record.msecs, 'path_name': record.pathname, 'process': record.process, 'process_name': record.processName, 'relative_created': record.relativeCreated,
                'stack_info': None if record.stack_info is None else str(record.stack_info), 'thread': record.thread, 'thread_name': record.threadName,
                'exception': self.__build_exception_details(record)}

    def __build_record(self, record):
        elastic_record = {'event_timestamp': record.created * 1000, 'event_type': record.levelname, 'event_message': record.msg,
                          'event_source': record.name, 'details': self.__build_record_details(record)}

        try:
            elastic_record['user'] = record.user
        except:
            elastic_record['user'] = None

        try:
            elastic_record['extra'] = record.extra
        except:
            elastic_record['extra'] = None

        return elastic_record
