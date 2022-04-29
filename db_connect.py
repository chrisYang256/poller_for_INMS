import os, pymysql

from dotenv        import load_dotenv
from elasticsearch import Elasticsearch


load_dotenv(
    dotenv_path=".env",
    verbose=True
)

db = pymysql.connect(
    user    = os.getenv("DB_USER"),
    host    = os.getenv("DB_HOST"),
    db      = os.getenv("DB_NAME"),
    passwd  = os.getenv("DB_PASSWORD"),
    port    = int(os.getenv("DB_PORT")),
    charset = "utf8"
)
cursor = db.cursor(pymysql.cursors.DictCursor)

host, port = os.getenv("ES_HOST"), os.getenv("ES_PORT")
es = Elasticsearch(f"{host}:{port}")