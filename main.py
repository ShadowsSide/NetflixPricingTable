import os
import io
import re
import json
import pymongo
import requests
import paramiko
from bs4 import BeautifulSoup
from datetime import datetime
from sshtunnel import SSHTunnelForwarder


def getCurrency(fullName:str) -> str: 
    with open("countries.json", 'r', encoding="utf-8") as r:
        countries = json.loads(r.read())
        if fullName == 'US Dollars':
            fullName = 'US Dollar'
        for country in countries:
            if fullName.upper() in country["currency_name"].upper():
                return country["currency"]
    return "N/A"


try: 
    with open("changelog.json", 'r', encoding="utf-8") as r:
        changelog = json.loads(r.read())
    r = requests.get('https://raw.githubusercontent.com/DyAxy/ExchangeRatesTable/main/data.json',timeout=5)
    j = r.json()['rates']

    curLog = len(changelog)
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://help.netflix.com/node/24926/"
    with SSHTunnelForwarder(
        ssh_address_or_host=os.environ['SSHIP'],
        ssh_username='root',
        ssh_pkey=paramiko.RSAKey.from_private_key(io.StringIO(os.environ['SSHKEY'])),
        remote_bind_address= ('127.0.0.1', 27017)
    ) as ssh:
        ssh.start()
        mongoClient = pymongo.MongoClient(host='127.0.0.1',port=ssh.local_bind_port)
        myCol = mongoClient["api"]["netflix"]
        newData = []

        data = myCol.find()
        for i in data:
            r = requests.get(f'{url}{i["code"]}')
            html = BeautifulSoup(r.text, 'html.parser')
            sectionList = html.find_all('h3', string=lambda text: 'Pricing' in text)
    
            if len(sectionList) == 0:
                pass
            isChanged = False
            for section in sectionList:
                currency = getCurrency(re.search(r"\((.*?)\)", section.get_text()).group(1))
                if currency != i['Currency']:
                    changelog.append({
                        'code':i['code'],
                        'message': f'Old {i["Currency"]}, New {currency}',
                        'updateTime': today
                        })
                    myCol.update_one({'code':i['code']},{"$set":{'Currency':currency,'updateTime': today}})
                    i['Currency'] = currency
    
                ul = section.find_next_sibling('ul')
                for li in ul.find_all('li'):
                    # labels - ['Basic', ' $3.99/month']
                    labels = li.get_text().replace('\xa0', ' ').replace("\n","").split(":")
                    plan = labels[0].replace("*","")
                    if plan == "Standard with adverts":
                        plan = 'Standard with ads'
                    price = labels[1].split('/')[0].replace(",","")
                    price = re.search(r"\d+(\.\d+)?",price).group(0)
                    if '.' in price:
                        price = float(price)
                    else:
                        price = int(price)
                    i[f"{plan}_CNY"] = round(price / j[currency] * j['CNY'],4)
                    myCol.update_one({'code':i['code']},{"$set":{f'{plan}_CNY':i[f"{plan}_CNY"],'updateTime': today}})
                    if price != i[plan]:
                        changelog.append({
                            'code':i['code'],
                            'message': f'Old {plan}:{i[plan]}, New {plan}:{price}, Currency {currency}',
                            'updateTime': today
                            })
                        myCol.update_one({'code':i['code']},{"$set":{plan:price,'updateTime': today}})
                        i[plan] = price
            i.pop('_id', None)
            newData.append(i)

    # Export Data to file
    with open('data.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(newData))
    if len(changelog) > curLog:
        with open('changelog.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(changelog))



except Exception as error:
    print(error)
    exit(1)