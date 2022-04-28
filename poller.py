# -*- coding: utf-8 -*-

import os, pymysql

from datetime      import datetime
from dotenv        import load_dotenv
from elasticsearch import Elasticsearch, helpers

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

utc_time   = datetime.utcnow()
local_time = datetime.now()

# snmp 장비 ip 가져오기
def select_snmp_devices_ip():
    db.connect()
    
    snmp_devices_ip = """
        select ip
        from snmp_devices
    """
    cursor.execute(snmp_devices_ip)
    snmp_devices_ip = cursor.fetchall()

    db.close()

    print("🙋 select devices ip success!")
    return { "snmp_devices_ip": snmp_devices_ip }
    
# maria: snmp_devices cpu, memory 컬럼 "update"
def update_snmp_data_for_maria(devices_data):
    db.connect()

    prepared_devices_data = []
    for device_data in devices_data["snmp_devices_data"]:
        device_data = list(device_data.values())

        device_data.insert(0, local_time)
        prepared_devices_data.append(device_data)

    update_info = """
        update snmp_devices
        set udate=%s, memory=%s, cpu=%s 
        where ip=%s
    """
    cursor.executemany(update_info, (prepared_devices_data))

    db.commit()
    db.close()

    print("🙋 devices data update for Maria success!")

# es: ghyang-snmp-yyyymmdd 에 "insert"
def insert_snmp_data_to_es(snmp_devices_data):
    index = os.getenv("ES_INDEX")

    docs = []
    for device_data in snmp_devices_data["snmp_devices_data"]:
        docs.append({
            "_index"  : index,
            "_type"   : "doc",
            "_source" : {
                "ip"         : device_data["ip"],
                "cpu"        : device_data["cpu"],
                "memory"     : device_data["memory"],
                "utc_time"   : utc_time
            }
        })

    helpers.bulk(es, docs)

    print("🙋 devices data insert to ES success!")

# ip 정보로 데이터 수집 / db에 넣을 수 있도록 가공
def process_snmp_devices_data(hosts):
    def trim_data(command):
        return int(os.popen(command).read().split("=")[1].strip().split(" ")[1])
    
    snmp_devices_data = []
    SNMP_PORT = os.getenv("SNMP_PORT") # port 임시 하드코딩. db 데이터로 다루게 되면 바꿔야함.
    for host in hosts["snmp_devices_ip"]:
        host = f"{host['ip']}:{SNMP_PORT}" 

        cpu_idle     = trim_data(f"snmpwalk -v 2c -c public {host} ssCpuIdle")
        memory_total = trim_data(f"snmpwalk -v 2c -c public {host} memTotalReal")
        memory_free  = trim_data(f"snmpwalk -v 2c -c public {host} memTotalFree")

        cpu_usage_percentage    = 100 - cpu_idle
        memory_usage_kilobyte   = round(memory_total - memory_free, 2)
        memory_usage_percentage = "%.2f" % (memory_usage_kilobyte / round(memory_total, 2) * 100)
        
        snmp_devices_data.append({
            "memory" : int(float(memory_usage_percentage)),
            "cpu"    : cpu_usage_percentage, 
            "ip"     : host.split(":")[0], 
        })
    
    print("🙋 process snmp devices data success!")
    return { "snmp_devices_data": snmp_devices_data }

snmp_devices_ip = select_snmp_devices_ip()
snmp_devices_data = process_snmp_devices_data(snmp_devices_ip)
update_snmp_data_for_maria(snmp_devices_data)
insert_snmp_data_to_es(snmp_devices_data)
print("Now local time is", local_time)




""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

"""es data 1개만 넣을 때 로직, 벌크로 단독/여러개 데이터 모두 수용 가능하여 일단 제외
es.index(index=index, doc_type="doc", body={
    "ip"     : snmp_devices_data["ip"],
    "cpu"    : snmp_devices_data["cpu"],
    "memory" : snmp_devices_data["memory"],
    "utc_time" : now_datetime
})
"""