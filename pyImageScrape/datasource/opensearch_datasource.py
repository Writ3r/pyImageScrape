import logging

from opensearchpy import (
    OpenSearch,
    Document,
    Text,
    Boolean,
    Search,
    helpers
)

# https://opensearch.org/docs/latest/clients/python-high-level/
# https://github.com/opensearch-project/opensearch-py/blob/main/guides/document_lifecycle.md

# INDEX NAMES
# =======================================

URL_INDEX = "url"
PIC_URL_INDEX = "pic_url"
STORED_PIC_INDEX = "stored_pic"

# CREATE DOC CLASSES
# =======================================


class Url(Document):

    err = Text()
    visited = Boolean()

    class Index:
        name = URL_INDEX

    def save(self, **kwargs):
        return super(Url, self).save(**kwargs)


class PicUrl(Document):

    err = Text()
    visited = Boolean()

    class Index:
        name = PIC_URL_INDEX

    def save(self, **kwargs):
        return super(PicUrl, self).save(**kwargs)


class StoredPic(Document):

    filePath = Text()
    url = Text()

    class Index:
        name = STORED_PIC_INDEX

    def save(self, **kwargs):
        return super(StoredPic, self).save(**kwargs)


# CREATE Datastore
# =======================================


class SimpleOpenSearchDataStore:

    def __init__(self, conn: OpenSearch):
        self.conn = conn
        self._run_setup()

    def add_to_visit_content_urls(self, urlLocs):
        urls = []
        for url in urlLocs:
            urls.append(Url(meta={"id": url}, visited=False, err=None))
        actions = self._build_bulk_create(Url.Index.name, urls)
        helpers.bulk(self.conn, actions, refresh=True, raise_on_error=False)

    def add_to_visit_pic_urls(self, urlLocs):
        urls = []
        for url in urlLocs:
            urls.append(PicUrl(meta={"id": url}, visited=False, err=None))
        actions = self._build_bulk_create(PicUrl.Index.name, urls)
        helpers.bulk(self.conn, actions, refresh=True, raise_on_error=False)

    def add_visited_content_url(self, urlLoc, err=None):
        self.conn.update(
            index=URL_INDEX,
            id=urlLoc,
            body={"doc": {"visited": True, "err": err}},
            refresh=True,
        )

    def add_visited_pic_url(self, urlLoc, err=None):
        self.conn.update(
            index=PIC_URL_INDEX,
            id=urlLoc,
            body={"doc": {"visited": True, "err": err}},
            refresh=True,
        )

    def add_stored_pic_url(self, urlLoc, filePath, shaPicHash):
        doc = StoredPic(meta={"id": shaPicHash}, filePath=filePath, url=urlLoc)
        doc.save(using=self.conn)

    def get_next_pic_to_visit(self):
        search = self._get_next_to_visit_query(PIC_URL_INDEX)
        response = search.execute()
        for doc in response:
            return doc.meta.id

    def get_next_content_to_visit(self):
        search = self._get_next_to_visit_query(URL_INDEX)
        response = search.execute()
        for doc in response:
            return doc.meta.id

    def get_all_pics_to_visit(self, n=1000):
        urls = []
        search = (
            Search(using=self.conn, index=PIC_URL_INDEX)
            .query("match", visited=False)
            .extra(size=n)
        )
        response = search.execute()
        for doc in response:
            urls.append(doc.meta.id)
        return urls
    
    def _build_bulk_create(self, indexName, inputObjs):
        return [
            {
                "_op_type": "create", 
                "_index": indexName,
                "_id": url.meta.id,
                "_source": url.to_dict(),  # Convert the document to a dict
            }
            for url in inputObjs
        ]

    def _get_next_to_visit_query(self, index):
        return (
            Search(using=self.conn, index=index)
            .query("match", visited=False)
            .extra(size=25)
        )

    def _run_setup(self):
        index_body = {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1}}
        }
        logging.info("Setting Up OpenSearch Indices")
        if not self.conn.indices.exists(URL_INDEX):
            response = self.conn.indices.create(URL_INDEX, index_body)
            logging.info(response)
        if not self.conn.indices.exists(PIC_URL_INDEX):
            response = self.conn.indices.create(PIC_URL_INDEX, index_body)
            logging.info(response)
        if not self.conn.indices.exists(STORED_PIC_INDEX):
            response = self.conn.indices.create(STORED_PIC_INDEX, index_body)
            logging.info(response)
        Url.init(using=self.conn)
        PicUrl.init(using=self.conn)
        StoredPic.init(using=self.conn)
