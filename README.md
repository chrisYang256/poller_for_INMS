# poller_for_INMS

</br>

## > 프로젝트 개요

- "Integrated Network Monitoring Service" 중 poller 파트의 기본 프레임 입니다.
- 연동된 grafana에서 데이터 시각화를 할 수 있도록 web service 파트를 통해 장비정보(ip 등)를 획득합니다.
- 획득한 장비 정보를 기반으로 현재 관리 중인 장비들의 데이터를 수집합니다.
- 수집한 데이터를 연동된 grafana가 시각화할 수 있도록 다시 정형/비정형 데이터베이스로 전송합니다.
- 수집 대상은 snmp, meraki 입니다.

</br>

## > 프로젝트 실행 환경

- centos 7.9
- python 3.6.2
- grafana 7.5.3
- mariadb 10.2.43(mysql 15.1)
- elastic search 6.8.6(lucene 7.7.2)

</br>

## > dotenv

```py
# 문자열에 따옴표("")를 쓰지 않으셔도 됩니다.

# Mariadb
DB_USER     =
DB_PASSWORD =
DB_HOST     =
DB_NAME     =
DB_PORT     =

# ES
ES_HOST  =
ES_PORT  =
ES_INDEX =
```

## > 가상환경 세팅

- /ect/ 경로에 Repository clone 후 project root 경로에 venv를 설치합니다.

```terminal
python3 -m venv venv
```

- 가상환경을 실행합니다.

```
. .venv/bin/activate
```

- 패키지를 설치합니다.

```
pip install -r requirements.txt
```

</br>

## > Crontab 설정

- `crontab -e` 명령어를 통해 crontab에 진입 후 crontab_setting.txt의 내용을 붙여넣습니다.

- poller가 /etc/ 경로에 있지 않다면 poller가 위치한 절대경로로 수정해줘야 합니다.

- `service crond status` 명령어로 crontab이 실행 중인지 확인합니다.

</br>

## > 시연

![ezgif com-gif-maker](https://user-images.githubusercontent.com/89192083/165771234-e9ef5d44-3b62-4575-8058-c43ee1c57ff5.gif)
