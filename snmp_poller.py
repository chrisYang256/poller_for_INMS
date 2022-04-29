# -*- coding: utf-8 -*-

import os

from db_connect    import db, cursor, es
from elasticsearch import helpers
from datetime      import datetime


class MakeData:
    def _select_device(self) -> list:
        db.connect()
        
        snmp_device = """
            select ip, port
            from snmp_devices
        """
        cursor.execute(snmp_device)
        snmp_device = cursor.fetchall()

        db.close()
        
        print("🙋 Select device data success!")

        return { "snmp_devices_ip": snmp_device }
        
    def process_device_data(self) -> list:
        def trim_data(command: str):
            return int(os.popen(command).read().split("=")[1].strip().split(" ")[1])
        
        hosts = self._select_device()

        snmp_devices_data: list[dict] = []
        for host in hosts["snmp_devices_ip"]:
            host = f"{host['ip']}:{host['port']}" 

            cpu_idle     = trim_data(f"snmpwalk -v 2c -c public {host} ssCpuIdle")
            memory_free  = trim_data(f"snmpwalk -v 2c -c public {host} memTotalFree")
            memory_total = trim_data(f"snmpwalk -v 2c -c public {host} memTotalReal")

            cpu_usage_percentage    = 100 - cpu_idle
            memory_usage_kilobyte   = round(memory_total - memory_free, 2)
            memory_usage_percentage = "%.2f" % (memory_usage_kilobyte / round(memory_total, 2) * 100)
            
            snmp_devices_data.append({
                "memory" : int(float(memory_usage_percentage)),
                "cpu"    : cpu_usage_percentage, 
                "ip"     : host.split(":")[0], 
            })
        
        print("🙋 Process snmp device data success!")

        return { "snmp_devices_data": snmp_devices_data }

class SendData:
    def __init__(self):
        self.local_time = datetime.now()
        self.utc_time   = datetime.utcnow()

    def update_sql(self, devices_data: list) -> None:
        db.connect()

        prepared_devices_data: list[dict] = []
        for device_data in devices_data["snmp_devices_data"]:
            device_data = list(device_data.values())

            device_data.insert(0, self.local_time)
            prepared_devices_data.append(device_data)

        update_info = """
            update snmp_devices
            set udate=%s, memory=%s, cpu=%s 
            where ip=%s
        """
        cursor.executemany(update_info, (prepared_devices_data))
        
        db.commit()
        db.close()

        print("🙋 Device data update in sql success!")

    def insert_to_es(self, snmp_devices_data: list) -> None:
        index = os.getenv("ES_INDEX")

        docs: list[dict] = []
        for device_data in snmp_devices_data["snmp_devices_data"]:
            docs.append({
                "_index"  : index,
                "_type"   : "doc",
                "_source" : {
                    "ip"         : device_data["ip"],
                    "cpu"        : device_data["cpu"],
                    "memory"     : device_data["memory"],
                    "utc_time"   : self.utc_time
                }
            })

        helpers.bulk(es, docs)
        
        print("🙋 Device data insert to ES success!")

make_data = MakeData()
data      = make_data.process_device_data()

send_data = SendData()
send_data.update_sql(data)
send_data.insert_to_es(data)

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

"""es data 1개만 넣을 때 로직, 벌크로 단독/여러개 데이터 모두 수용 가능하여 일단 제외
es.index(index=index, doc_type="doc", body={
    "ip"     : snmp_devices_data["ip"],
    "cpu"    : snmp_devices_data["cpu"],
    "memory" : snmp_devices_data["memory"],
    "utc_time" : now_datetime
})
"""