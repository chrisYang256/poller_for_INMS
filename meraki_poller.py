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
def select_meraki_organization() -> list:
    orgs = dashboard.organizations.getOrganizations()

    org_id = ""
    for org in orgs:
        if org["id"] == "667095694804257754":
            org_id = dashboard.organizations.getOrganization(org["id"])["id"]

    network_id = dashboard.networks.getOrganizationNetworks(org_id)[0]["id"]

    if org_id or network_id is None:
        raise Exception("⛔ No data")

    print("🙋 Select meraki organization success!")

    return { "org_id": org_id, "network_id": network_id }

# devices 가져오고 db에 저장 -> organization id 필요
def upsert_meraki_device_to_sql(meraki_org_info):
    org_id = meraki_org_info["org_id"]

    meraki_device = dashboard.devices.getOrganizationDevices(org_id)

    meraki_device_list: list[list] = []
    for device in meraki_device:
        device = list(device.values())

        device.append(local_time)
        meraki_device_list.append(device)

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
            udate                  = values(udate)
    """
    cursor.executemany(create_or_update_device, meraki_device_list)

    db.commit()
    db.close()

    print("🙋 Upsert meraki device to sql success!")

# clients 가져오고 ES에 저장 -> network id 필요
def add_meraki_client_to_es(meraki_org_info):
    network_id = meraki_org_info["network_id"]

    meraki_client = dashboard.clients.getNetworkClients(network_id)

    index = f"ghyang-meraki-clients-{local_time.strftime('%Y%m%d')}"

    docs: list[dict] = []
    for client_data in meraki_client:
        docs.append({
            "_index"  : index,
            "_type"   : "doc",
            "_source" : {
                "id"                 : client_data["id"],
                "mac"                : client_data["mac"],
                "description"        : client_data["description"],
                "ip"                 : client_data["ip"],
                "ip6"                : client_data["ip6"],
                "ip6Local"           : client_data["ip6Local"],
                "user"               : client_data["user"],
                "firstSeen"          : client_data["firstSeen"],
                "lastSeen"           : client_data["lastSeen"],
                "manufacturer"       : client_data["manufacturer"],
                "os"                 : client_data["os"],
                "recentDeviceSerial" : client_data["recentDeviceSerial"],
                "recentDeviceName"   : client_data["recentDeviceName"],
                "recentDeviceMac"    : client_data["recentDeviceMac"],
                "ssid"               : client_data["ssid"],
                "vlan"               : client_data["vlan"],
                "switchport"         : client_data["switchport"],
                "usage_sent"         : client_data["usage"]["sent"],
                "usage_recv"         : client_data["usage"]["recv"],
                "status"             : client_data["status"],
                "notes"              : client_data["notes"],
                "smInstalled"        : client_data["smInstalled"],
                "groupPolicy8021x"   : client_data["groupPolicy8021x"],
                "utc_time"           : utc_time
            }
        })
    
    helpers.bulk(es, docs)

    print("🙋 Add meraki client to es success!")

org = select_meraki_organization()
upsert_meraki_device_to_sql(org)
add_meraki_client_to_es(org)