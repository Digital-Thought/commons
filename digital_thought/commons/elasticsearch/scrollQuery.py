class ScrollQuery:

    def __init__(self, request_session, root_url) -> None:
        super().__init__()
        self.request_session = request_session
        self.root_url = root_url
        self.scroll_ids = []

    def close(self):
        body = {"scroll_id": self.scroll_ids}
        r = self.request_session.delete(self.root_url + "_search/scroll", json=body)
        self.scroll_ids.clear()

    def clear(self):
        self.close()

    def query(self, index, query):
        scroll = "1m"
        body = query

        r = self.request_session.post(self.root_url + index + "/_search?scroll=1m", json=body)

        scroll_id = r.json()['_scroll_id']
        self.scroll_ids.append(scroll_id)
        hits = r.json()['hits']['hits']
        scroll_query = {"scroll": scroll, "scroll_id": scroll_id}

        while len(hits) > 0:
            for hit in hits:
                yield hit

            r = self.request_session.post(self.root_url + "_search/scroll", json=scroll_query)
            hits = r.json()['hits']['hits']

    def __enter__(self):
        """Return self object to use with "with" statement."""
        return self

    def __exit__(self, type, value, traceback):
        """Close workbook when exiting "with" statement."""
        self.close()
