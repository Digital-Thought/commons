import csv
import logging
import random

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from digital_thought_commons import elasticsearch as es


class UrlAnalyser:
    index_name = "malicious-urls"

    def __init__(self, elastic_server, elastic_port, elastic_api_key):
        self.elastic = es.ElasticsearchConnection(server=elastic_server, port=elastic_port,
                                  api_key=elastic_api_key)

    def learn(self):
        self.vectorizer, self.lgs = self.tl()

    def load_csv(self, path_to_csv):
        logging.info("Processing CSV: {}".format(path_to_csv))
        bulk_indexer = self.elastic.bulk_processor()
        with open(path_to_csv, 'r', encoding="UTF-8") as _csv_file:
            csv_reader = csv.reader(_csv_file, delimiter=',')
            for row in csv_reader:
                bulk_indexer.index(index=self.index_name, entry={'url': row[0], 'status': row[1]})

        bulk_indexer.close()

    def getTokens(self, input):
        tokensBySlash = str(input.encode('utf-8')).split('/')  # get tokens after splitting by slash
        allTokens = []
        for i in tokensBySlash:
            tokens = str(i).split('-')  # get tokens after splitting by dash
            tokensByDot = []
            for j in range(0, len(tokens)):
                tempTokens = str(tokens[j]).split('.')  # get tokens after splitting by dot
                tokensByDot = tokensByDot + tempTokens
            allTokens = allTokens + tokens + tokensByDot
        allTokens = list(set(allTokens))  # remove redundant tokens
        if 'com' in allTokens:
            allTokens.remove(
                'com')  # removing .com since it occurs a lot of times and it should not be included in our features
        if 'www' in allTokens:
            allTokens.remove(
                'www')
        return allTokens

    def tl(self):
        logging.info("Reading base data")
        data = []
        scroll_query = self.elastic.get_scroller()
        for entry in scroll_query.query(self.index_name, {"size": 1000}):
            data.append({'url': entry['_source']['url'], 'status': entry['_source']['status']})
        scroll_query.clear()

        logging.info("Building Vectors")
        url_data = pd.DataFrame(data)
        url_data = np.array(url_data)
        random.shuffle(url_data)

        y = [d[1] for d in url_data]
        corpus = [d[0] for d in url_data]
        vectorizer = TfidfVectorizer(tokenizer=self.getTokens)

        X = vectorizer.fit_transform(corpus)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        lgs = LogisticRegression(max_iter=10000)  # using logistic regression
        lgs.fit(X_train, y_train)
        logging.info('Logistic Regression Score: {}'.format(lgs.score(X_test, y_test)))

        return vectorizer, lgs

    def is_suspicious(self, url):
        logging.debug("Analysing URL: {}".format(url))
        X_predict = self.vectorizer.transform([url])
        y_Predict = self.lgs.predict(X_predict)
        return 'bad' in y_Predict
