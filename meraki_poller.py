# -*- coding: utf-8 -*-

import os

from db_connect    import db, cursor, es
from elasticsearch import helpers
from datetime      import datetime

import meraki


local_time = datetime.now()
utc_time   = datetime.utcnow()

dashboard = meraki.DashboardAPI(
    api_key=os.getenv("MERAKI_DASHBOARD_API_KEY"),
    base_url = 'https://api.meraki.com/api/v0/',
    output_log=False,
    print_console=False
)

# meraki api 다루는 연습 / 구조 파악을 위해 의도적으로 여러 template들을 써봄
def select_meraki_organization() -> dict:
    orgs = dashboard.organizations.getOrganizations()

    org_id = ""
    for org in orgs:
        if org["id"] == "667095694804257754":
            org_id = dashboard.organizations.getOrganization(org["id"])["id"]

    network_id = dashboard.networks.getOrganizationNetworks(org_id)[0]["id"]

    print("🙋 Select meraki organization success!")

    return { "org_id": org_id, "network_id": network_id }

# devices 가져오고 db에 저장 -> organization id 필요
def upsert_meraki_device_to_sql(meraki_org_info):
    org_id = meraki_org_info["org_id"]

    meraki_devices = dashboard.devices.getOrganizationDevices(org_id)
    meraki_devices_status = dashboard.organizations.getOrganizationDeviceStatuses(org_id)

    meraki_device_list: list[list] = []
    for meraki_device in meraki_devices:
        for meraki_device_status in  meraki_devices_status:
            if meraki_device["serial"] == meraki_device_status["serial"]:
                meraki_device["status"] = meraki_device_status["status"]

        meraki_device = list(meraki_device.values())

        meraki_device.append(local_time)
        meraki_device_list.append(meraki_device)
    
    db.connect()
    # on duplicate key update 내용 끝에 쉼표(,) 넣지 말것(4시간 날림)
    create_or_update_device = f"""
        insert into meraki_devices (
            name, 
            serial, 
            mac, 
            networkId, 
            model, 
            address,
            lat, 
            lng, 
            notes, 
            tags, 
            lanIp, 
            configurationUpdatedAt, 
            firmware, 
            url, 
            status,
            udate
        )
        values ({",".join(["%s"] * len(meraki_device_list[0]))})
        on duplicate key update
            name                   = values(name), 
            mac                    = values(mac), 
            networkId              = values(networkId), 
            model                  = values(model), 
            address                = values(address),
            lat                    = values(lat), 
            lng                    = values(lng), 
            notes                  = values(notes), 
            tags                   = values(tags), 
            lanIp                  = values(lanIp), 
            configurationUpdatedAt = values(configurationUpdatedAt), 
            firmware               = values(firmware), 
            url                    = values(url),
            status                 = values(status),
            udate                  = values(udate)
    """
    cursor.executemany(create_or_update_device, meraki_device_list)

    db.commit()
    db.close()

    print("🙋 Upsert meraki device to sql success!")

# clients 가져오고 ES에 저장 -> network id 필요
def add_meraki_client_to_es(meraki_org_info):
    network_id = meraki_org_info["network_id"]

    meraki_clients = dashboard.clients.getNetworkClients(network_id)

    index = f"ghyang-meraki-clients-{local_time.strftime('%Y%m%d')}"

    docs: list[dict] = []
    for meraki_client in meraki_clients:
        docs.append({
            "_index"  : index,
            "_type"   : "doc",
            "_source" : {
                "id"                 : meraki_client["id"],
                "mac"                : meraki_client["mac"],
                "description"        : meraki_client["description"],
                "ip"                 : meraki_client["ip"],
                "ip6"                : meraki_client["ip6"],
                "ip6Local"           : meraki_client["ip6Local"],
                "user"               : meraki_client["user"],
                "firstSeen"          : meraki_client["firstSeen"],
                "lastSeen"           : meraki_client["lastSeen"],
                "manufacturer"       : meraki_client["manufacturer"],
                "os"                 : meraki_client["os"],
                "recentDeviceSerial" : meraki_client["recentDeviceSerial"],
                "recentDeviceName"   : meraki_client["recentDeviceName"],
                "recentDeviceMac"    : meraki_client["recentDeviceMac"],
                "ssid"               : meraki_client["ssid"],
                "vlan"               : meraki_client["vlan"],
                "switchport"         : meraki_client["switchport"],
                "usage_sent"         : meraki_client["usage"]["sent"],
                "usage_recv"         : meraki_client["usage"]["recv"],
                "status"             : meraki_client["status"],
                "notes"              : meraki_client["notes"],
                "smInstalled"        : meraki_client["smInstalled"],
                "groupPolicy8021x"   : meraki_client["groupPolicy8021x"],
                "utc_time"           : utc_time
            }
        })
    
    helpers.bulk(es, docs)

    print("🙋 Add meraki client to es success!")

org = select_meraki_organization()
upsert_meraki_device_to_sql(org)
add_meraki_client_to_es(org)