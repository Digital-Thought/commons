import json
import logging
import multiprocessing
import os
import pathlib
import sys
import threading
import time
from datetime import datetime

from digital_thought_commons import internet
from digital_thought_commons.utils import bytes


class DownloadConfig:

    def __init__(self, source_url=None, worker_count=None, source_name=None, file_length=None, supports_range=None,
                 segments=None, dest_dir=None, full_destination_name=None, partial_name=None) -> None:
        self.source_url = source_url
        self.worker_count = worker_count
        self.source_name = source_name
        self.file_length = file_length
        self.supports_range = supports_range
        self.segments = segments
        self.dest_dir = dest_dir
        self.full_destination_name = full_destination_name
        self.partial_name = partial_name

    def as_json(self):
        return {'source_url': self.source_url, 'worker_count': self.worker_count, 'source_name': self.source_name, 'file_length': self.file_length,
                'supports_range': self.supports_range, 'segments': self.segments, 'dest_dir': self.dest_dir, 'full_destination_name': self.full_destination_name,
                'partial_name': self.partial_name}

    def write_to(self, file):
        with open(file, 'w', encoding='utf-8') as partial_file:
            json.dump(self.as_json(), partial_file, indent=4)

    @classmethod
    def load_from(cls, file):
        with open(file, 'r', encoding='utf-8') as partial_file:
            config = json.load(partial_file)

            cls.source_url = config['source_url']
            cls.worker_count = config['worker_count']
            cls.source_name = config['source_name']
            cls.file_length = config['file_length']
            cls.supports_range = config['supports_range']
            cls.segments = config['segments']
            cls.dest_dir = config['dest_dir']
            cls.full_destination_name = config['full_destination_name']
            cls.partial_name = config['partial_name']

            return cls


class DownloadProgress:

    def __init__(self, config: DownloadConfig, log_every=5) -> None:
        self.source_url = None
        self.config = config
        self.__start_time = datetime.now().timestamp()
        self.__last_update = self.__start_time
        self.__size_at_start = 0
        self.__amount_downloaded = 0
        self.__restarts_after_interruption = 0
        self.__log_every = log_every
        self.__prior_perc = 0
        self.__max_download_rate = None
        self.__min_download_rate = None
        self.__lock = threading.Lock()

    def __time_remaining(self, download_rate):
        return (self.config.file_length - (self.__amount_downloaded + self.__size_at_start)) / download_rate

    @staticmethod
    def __time_remaining_friendly(time_remaining):
        delta = time_remaining
        day = delta // (24 * 3600)
        time = delta % (24 * 3600)
        hour = time // 3600
        time %= 3600
        minutes = time // 60
        time %= 60
        seconds = time
        return f'{str(round(day))} days, {str(round(hour))} hours, {str(round(minutes))} minutes, {str(round(seconds))} seconds'

    def __download_rate(self):
        return round(self.__amount_downloaded / (datetime.now().timestamp() - self.__start_time))

    def log_progress(self, force=False):

        progress_details = self.progress()

        if force or (progress_details['percentage_complete'] % self.__log_every == 0 and 0 < progress_details['percentage_complete'] != self.__prior_perc and progress_details[
            'percentage_complete'] != 100) or (self.config.file_length <= 0 and (datetime.now().timestamp() - self.__last_update) >= self.__log_every * 60):
            self.__prior_perc = progress_details['percentage_complete']
            self.__last_update = datetime.now().timestamp()

            logging.info(
                f'Download of {self.config.source_url} is {str(progress_details["percentage_complete"]) if progress_details["percentage_complete"] > 0 else "UNKNOWN"}% complete. '
                f'Estimated time remaining {progress_details["time_remaining_friendly"] if progress_details["percentage_complete"] > 0 else "UNKNOWN"}. '
                f'Average Download speed: {progress_details["download_rate_friendly"]} [Max: {bytes.bytes_to_readable_unit(self.__max_download_rate)}, '
                f'Min: {bytes.bytes_to_readable_unit(self.__min_download_rate)}]. '
                f'Downloading of segments has been restarted {progress_details["restarts_after_interruption_friendly"]}.')

    def progress(self):
        perc_downloaded = 0
        if self.config.file_length > 0:
            perc_downloaded = round(((self.__size_at_start + self.__amount_downloaded) / self.config.file_length) * 100)

        download_rate = self.__download_rate()
        if self.__max_download_rate is None or download_rate > self.__max_download_rate:
            self.__max_download_rate = download_rate

        if self.__min_download_rate is None or download_rate < self.__min_download_rate:
            self.__min_download_rate = download_rate

        if download_rate > 0:
            time_remaining = self.__time_remaining(download_rate)
        else:
            time_remaining = sys.maxsize

        return {'config': self.config.as_json(), 'percentage_complete': perc_downloaded, 'download_rate_bytes': download_rate, 'time_remaining_seconds': time_remaining,
                'restarts_after_interruption': self.__restarts_after_interruption, 'download_rate_friendly': f'{bytes.bytes_to_readable_unit(download_rate)} per second',
                'time_remaining_friendly': self.__time_remaining_friendly(time_remaining),
                'restarts_after_interruption_friendly': f'{self.__restarts_after_interruption} {"times" if self.__restarts_after_interruption > 1 else "time"}'}

    def data_on_commencement(self, size_bytes: int):
        self.__lock.acquire()
        try:
            self.__size_at_start += size_bytes
        finally:
            self.__lock.release()

    def update_amount_downloaded(self, size_bytes: int):
        self.__lock.acquire()
        try:
            self.__amount_downloaded += size_bytes
            self.log_progress()
        finally:
            self.__lock.release()

    def increment_restarts_after_interruption(self):
        self.__lock.acquire()
        try:
            self.__restarts_after_interruption += 1
        finally:
            self.__lock.release()


class DownloadWorker(threading.Thread):

    def __init__(self, source_url, partial_name, segment_range, worker_number, tor_proxy, internet_proxy, continue_retrying_on_interruption, range_supported,
                 download_progress: DownloadProgress) -> None:
        threading.Thread.__init__(self, name=f'DownloadWorker:{str(worker_number)}:[{partial_name}]')
        self.name = f'DownloadWorker:{str(worker_number)}:[{partial_name}]'
        self.source_url = source_url
        self.partial_name = partial_name
        self.segment_range = segment_range
        self.range_supported = range_supported
        self.worker_number = worker_number
        self.abort = False
        self.complete = False
        self.error = False
        self.tor_proxy = tor_proxy
        self.internet_proxy = internet_proxy
        self.download_progress = download_progress
        self.continue_retrying_on_interruption = continue_retrying_on_interruption

    def abort_download(self):
        logging.warning(self.name)
        self.abort = True

    def run(self) -> None:
        try:
            segment_partial_name = f'{self.partial_name}.{str(self.worker_number)}'
            if os.path.exists(segment_partial_name):
                self.download_progress.data_on_commencement(pathlib.Path(segment_partial_name).stat().st_size)

            while not self.complete:
                try:
                    resume_headers = {}
                    segment_size = int(self.segment_range.split(':')[0])
                    logging.info(f'Segment expected size: {bytes.bytes_to_readable_unit(segment_size)}')

                    if len(self.segment_range.split(':')) > 1:
                        start_range = self.segment_range.split(':')[1]
                        if os.path.exists(segment_partial_name):
                            start_range = int(start_range) + pathlib.Path(segment_partial_name).stat().st_size
                            logging.info(f'Existing segment file size is: {bytes.bytes_to_readable_unit(pathlib.Path(segment_partial_name).stat().st_size)}')

                            if segment_size == pathlib.Path(segment_partial_name).stat().st_size:
                                logging.info(f'Segment {segment_partial_name} is already complete')
                                self.complete = True
                                break

                        end_range = ''
                        if len(self.segment_range.split(':')) > 2:
                            end_range = self.segment_range.split(':')[2]

                        size_remaining = (int(self.segment_range.split(':')[1]) + segment_size) - int(start_range)
                        logging.info(f'Requested start_range: {start_range}, original start_range: {self.segment_range.split(":")[1]}, end_range: {end_range}. '
                                     f'Estimated size of segment remaining to download: {bytes.bytes_to_readable_unit(size_remaining)}')
                        resume_headers = {'Range': f'bytes={start_range}-{end_range}'}

                    try:
                        with internet.new_requester(tor_proxy=self.tor_proxy, internet_proxy=self.internet_proxy) as requester:
                            with requester.get(self.source_url, stream=True, timeout=120, headers=resume_headers, allow_redirects=True) as resp_stream:
                                with open(segment_partial_name, 'ab') as out_file:
                                    for chunk in resp_stream.iter_content(chunk_size=1024 * 512):
                                        out_file.write(chunk)
                                        out_file.flush()
                                        self.download_progress.update_amount_downloaded(len(chunk))

                                        if self.abort:
                                            break
                    except Exception as ex:
                        logging.exception(str(ex))
                        logging.warning(f'Interrupted while downloading chunks from stream to: {segment_partial_name}')
                        continue

                    if pathlib.Path(segment_partial_name).stat().st_size < segment_size:
                        raise internet.IncompleteDownload(f'Destination file is {bytes.bytes_to_readable_unit(pathlib.Path(segment_partial_name).stat().st_size)}, '
                                                          f'expected {bytes.bytes_to_readable_unit(segment_size)}.')
                    elif 0 < segment_size < pathlib.Path(segment_partial_name).stat().st_size:
                        self.continue_retrying_on_interruption = False
                        message = f'Expected segment to be {bytes.bytes_to_readable_unit(segment_size)}, but downloaded data is greater: ' \
                                  f'{bytes.bytes_to_readable_unit(pathlib.Path(segment_partial_name).stat().st_size)}.  Aborting download.'
                        logging.error(message)
                        raise internet.IncompleteDownload(message)
                    else:
                        self.complete = True
                        logging.info(f'Completed downloading of segment: {segment_partial_name}. '
                                     f'Size: {bytes.bytes_to_readable_unit(pathlib.Path(segment_partial_name).stat().st_size)}')

                except Exception as ex:
                    logging.exception(str(ex))
                    if not self.continue_retrying_on_interruption or not self.range_supported:
                        self.complete = True
                        self.error = True
                        raise internet.IncompleteDownload(str(ex))
                    else:
                        logging.warning('Attempting to resume download from last point')
                        self.download_progress.increment_restarts_after_interruption()
        except Exception as ex:
            logging.exception(str(ex))


class DownloadJob(threading.Thread):

    def __init__(self, config: DownloadConfig, tor_proxy, internet_proxy, continue_retrying_on_interruption) -> None:
        threading.Thread.__init__(self, name=f'DownloadJob:{config.full_destination_name}')
        self.config = config
        self.errors = False
        self.complete = False
        self.tor_proxy = tor_proxy
        self.internet_proxy = internet_proxy
        self.continue_retrying_on_interruption = continue_retrying_on_interruption
        self.download_progress = DownloadProgress(config)
        self.__lock = threading.Lock()
        self.__workers = []

    def __merge_completed(self):
        with open(self.config.partial_name, 'wb') as fout:
            for n in range(self.config.worker_count):
                with open(f'{self.config.partial_name}.{str(n)}', 'rb') as fin:
                    fin.seek(0)
                    while True:
                        read_bytes = fin.read(1024 * 1024 * 10)
                        if read_bytes:
                            fout.write(read_bytes)
                        else:
                            break
                os.remove(f'{self.config.partial_name}.{str(n)}')
        os.rename(self.config.partial_name, self.config.full_destination_name)
        logging.info(f'Completed download of {self.config.full_destination_name} from {self.config.source_url}. '
                     f'Total size: {bytes.bytes_to_readable_unit(pathlib.Path(self.config.full_destination_name).stat().st_size)}')

    def run(self) -> None:
        logging.info(f'Staring download of {self.config.source_url}. Size is: {bytes.bytes_to_readable_unit(self.config.file_length)}')
        self.__lock.acquire()
        for n in range(self.config.worker_count):
            logging.info(f'Starting download worker: {str(n)}.')
            self.__workers.append(DownloadWorker(source_url=self.config.source_url, partial_name=self.config.partial_name, segment_range=self.config.segments[n], worker_number=n,
                                                 tor_proxy=self.tor_proxy, internet_proxy=self.internet_proxy,
                                                 continue_retrying_on_interruption=self.continue_retrying_on_interruption,
                                                 range_supported=self.config.supports_range, download_progress=self.download_progress))

            self.__workers[n].start()

        for worker in self.__workers:
            worker.join()
            self.errors = self.errors or worker.error

        self.complete = True
        if not self.errors:
            self.__merge_completed()
        else:
            logging.error(f'Unable to complete download of {self.config.source_url} as a worker encountered an error')
        self.__lock.release()

    def wait_to_complete(self):
        logging.info("Waiting until complete...")
        self.__lock.acquire()
        logging.info("Wait to complete, reached")
        self.__lock.release()

    def abort(self):
        logging.info('Aborting download workers...')
        for worker in self.__workers:
            worker.abort_download()

    def downloaded_file(self):
        return self.config.full_destination_name


class DownloadManager:

    def __init__(self, tor_proxy=None, internet_proxy=None, continue_retrying_on_interruption=True, attempt_resume_partial=True) -> None:
        self.tor_proxy = tor_proxy
        self.internet_proxy = internet_proxy
        self.continue_retrying_on_interruption = continue_retrying_on_interruption
        self.attempt_resume_partial = attempt_resume_partial
        self.start_time = 0

    @staticmethod
    def __define_segments(file_length, worker_count):
        segments = []
        segment_size = round(file_length / worker_count)
        while len(segments) < worker_count - 1:
            start_offset = len(segments) * segment_size
            end_offset = ((len(segments) + 1) * segment_size) - 1
            segments.append(f'{str(segment_size)}:{str(start_offset)}:{str(end_offset)}')

        start_offset = len(segments) * segment_size
        segments.append(f'{str(file_length - start_offset)}:{str(start_offset)}:')
        return segments

    def __determine_config(self, url, dest_dir, override_worker_count) -> DownloadConfig:
        with internet.new_requester(tor_proxy=self.tor_proxy, internet_proxy=self.internet_proxy) as requester:
            source_name, file_length = internet.source_details(requester_session=requester, source_url=url)
            supports_range = internet.check_supports_range(requester_session=requester, source_url=url)
            worker_count = 1 if file_length == -1 or not supports_range else (multiprocessing.cpu_count() if override_worker_count is None else override_worker_count)
            segments = self.__define_segments(file_length=file_length, worker_count=worker_count) if worker_count > 1 else [f'{file_length}']

            full_destination_name = f'{dest_dir}/{source_name}'
            partial_name = f'{full_destination_name}.partial'

            return DownloadConfig(source_url=url, worker_count=worker_count, source_name=source_name, file_length=file_length,
                                  supports_range=supports_range, segments=segments, dest_dir=dest_dir, full_destination_name=full_destination_name, partial_name=partial_name)

    def download(self, url, dest_dir, async_download=False, override_worker_count=None) -> DownloadJob:
        logging.info(f'Downloading {url} to {dest_dir}')
        os.makedirs(dest_dir, exist_ok=True)

        config = self.__determine_config(url=url, dest_dir=dest_dir, override_worker_count=override_worker_count)

        if os.path.exists(config.full_destination_name):
            raise internet.DownloadException(f'Destination file {config.full_destination_name} already exists')

        partial_exists = os.path.exists(config.partial_name)

        if partial_exists:
            config = DownloadConfig.load_from(config.partial_name)

        if partial_exists and (not config.supports_range or not self.attempt_resume_partial):
            if not config.supports_range:
                logging.warning(f'Source server for URL {url} does not support ranges.  Deleting partial download and starting again.')

            logging.warning(f'Removing prior partial download: {config.partial_name}.')
            os.remove(config.partial_name)

            for n in range(config.worker_count):
                if os.path.exists(f'{config.partial_name}.{str(n)}'):
                    logging.warning(f'Deleting partial segment: {config.partial_name}.{str(n)}')
                    os.remove(f'{config.partial_name}.{str(n)}')

        elif partial_exists:
            logging.info(f'Resuming a partially completed download of {url}')

        config.write_to(config.partial_name)

        download_job = DownloadJob(config=config, tor_proxy=self.tor_proxy, internet_proxy=self.internet_proxy,
                                   continue_retrying_on_interruption=self.continue_retrying_on_interruption)

        if async_download:
            download_job.start()
            # Give it a moment to start before passing the job back
            time.sleep(5)
        else:
            download_job.run()

        return download_job
