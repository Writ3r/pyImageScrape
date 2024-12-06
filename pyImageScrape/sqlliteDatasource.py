
import sqlite3
import os
import threading

from shared import get_current_folder

class DatabaseConnector:

    def __init__(self, dataFolder, dbSetupFolder=get_current_folder()):
        self.setupFileLoc = dbSetupFolder + "/tableSetup.sql"
        self.dbPath = dataFolder + "/sqllite.db"
        self._run_setup()

    def _create_connection(self):
        """ create db conn """
        conn = sqlite3.connect(self.dbPath)
        conn.row_factory = sqlite3.Row
        return conn

    def _run_setup(self):
        """ sets up database tables """
        with self._create_connection() as conn:
            cursor = conn.cursor()
            sql_file = open(self.setupFileLoc)
            sql_as_string = sql_file.read()
            cursor.executescript(sql_as_string)

    def execute(self, query, args):
        """Executes sql statements, and maps response to objects"""
        with self._create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, args)
            conn.commit()
            dictList = [dict(row) for row in cursor.fetchall()]
            return dictList

    def executeBatch(self, query, argsList):
        """Executes sql statements, and maps response to objects"""
        with self._create_connection() as conn:
            cursor = conn.cursor()
            for arg in argsList:
                cursor.execute(query, arg)
            conn.commit()
            dictList = [dict(row) for row in cursor.fetchall()]
            return dictList


class SqlLiteDataStore:

    CONTENT_URL_TB = "urls"
    PIC_URL_TB = "picUrls"

    CREATE = "INSERT OR IGNORE INTO TB_URL (urlLoc, visited) VALUES (?,?);"
    READ_ONE_LIMIT = "SELECT * FROM TB_URL WHERE visited = ? LIMIT 1;"
    READ_ALL = "SELECT * FROM TB_URL WHERE visited = ?;"
    UPDATE_URL = "UPDATE TB_URL SET urlLoc = ?, visited = ? WHERE urlLoc = ?;"
    CREATE_STORED_PIC_URL = "INSERT OR IGNORE INTO storedPics (urlLoc, filePath, shaPicHash) VALUES (?,?,?);"
    CHECK_VISITED = "SELECT * FROM TB_URL WHERE urlLoc = ? AND visited = 1;"
    CHECK_EXISTS = "SELECT * FROM TB_URL WHERE urlLoc = ?;"

    def __init__(self, dbConn: DatabaseConnector):
        self.dbConn = dbConn
    
    def add_to_visit_content_urls(self, urlLocs):
        self._add_to_visit_urls(urlLocs, SqlLiteDataStore.CONTENT_URL_TB)

    def add_to_visit_pic_urls(self, urlLocs):
        self._add_to_visit_urls(urlLocs, SqlLiteDataStore.PIC_URL_TB)

    def add_visited_content_urls(self, urlLocs):
        self._add_visited_urls(urlLocs, SqlLiteDataStore.CONTENT_URL_TB)

    def add_visited_pic_urls(self, urlLocs):
        self._add_visited_urls(urlLocs, SqlLiteDataStore.PIC_URL_TB)

    def get_next_pic_to_visit(self):
        return self._get_next_to_visit(SqlLiteDataStore.PIC_URL_TB)

    def get_next_content_to_visit(self):
        return self._get_next_to_visit(SqlLiteDataStore.CONTENT_URL_TB)

    def get_all_pics_to_visit(self):
        return self._get_all_to_visit(SqlLiteDataStore.PIC_URL_TB)

    def add_stored_pic_url(self, urlLoc, filePath, shaPicHash):
        # would also be good to save off timestamp of grab & alt data
        self.dbConn.execute(SqlLiteDataStore.CREATE_STORED_PIC_URL, (urlLoc, filePath, shaPicHash))

    def _add_to_visit_urls(self, urlLocs, table):
        """ add multiple urls to visit """
        argsList = []
        for url in urlLocs:
            argsList.append((url, 0))
        query = SqlLiteDataStore.CREATE.replace('TB_URL', table)
        self.dbConn.executeBatch(query, argsList)

    def _add_visited_urls(self, urlLocs, table):
        """ tag multiple urls as visited """
        argsList = []
        for url in urlLocs:
            argsList.append((url, 1, url))
        query = SqlLiteDataStore.UPDATE_URL.replace('TB_URL', table)
        self.dbConn.executeBatch(query, argsList)

    def _get_next_to_visit(self, table):
        """ get the next url to visit """
        query = SqlLiteDataStore.READ_ONE_LIMIT.replace('TB_URL', table)
        resp = self.dbConn.execute(query, (0,))
        if len(resp) > 0:
            return resp[0]['urlLoc']
        else:
            return None

    def _get_all_to_visit(self, table):
        """ get all the next urls to visit """
        query = SqlLiteDataStore.READ_ALL.replace('TB_URL', table)
        resp = self.dbConn.execute(query, (0,))
        visitList = []
        for item in resp:
            visitList.append(item['urlLoc'])
        return visitList

def get_sqllite_datastore(dataPath: str):
    """ gets an sqllite impl of the datasource"""
    return SqlLiteDataStore(DatabaseConnector(dataPath))