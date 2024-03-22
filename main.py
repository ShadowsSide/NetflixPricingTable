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
            fullName == 'US Dollar'
        for country in countries:
            if fullName.upper() in country["currency_name"].upper():
                return country["currency"]
    return "N/A"


try: 
    data = {
        "updateTime": datetime.now().strftime("%Y-%m-%d"),
        "pricing": []
    }

    with open("netflix.json", 'r', encoding="utf-8") as r:
        netflix = json.loads(r.read())
    url = "https://help.netflix.com/node/24926/"
    # netflix = [{"value":"BD"}]
    for i in netflix:
        r = requests.get(f'{url}{i["value"]}')
        print(i["value"])
        html = BeautifulSoup(r.text, 'html.parser')
        sectionList = html.find_all('h3', string=lambda text: 'Pricing' in text)

        if len(sectionList) == 0:
            pass
        struc = {
            "code": i["value"],
            "Currency": None,
            "Mobile": None,
            "Basic": None,
            "Standard with ads":None,
            "Standard": None,
            "Premium": None,
            "updateTime": datetime.now().strftime("%Y-%m-%d")
        }
        for section in sectionList:
            struc["Currency"] = getCurrency(re.search(r"\((.*?)\)", section.get_text()).group(1))
            ul = section.find_next_sibling('ul')
            for li in ul.find_all('li'):
                # labels - ['Basic', ' $3.99/month']
                labels = li.get_text().replace('\xa0', ' ').replace("\n","").split(":")
                plan = labels[0].replace("*","")
                if plan == "Standard with adverts":
                    plan == 'Standard with ads'
                price = labels[1].split('/')[0].replace(",","")
                price = re.search(r"\d+(\.\d+)?",price).group(0)
                if '.' in price:
                    price = float(price)
                else:
                    price = int(price)
                struc[plan] = price
        data["pricing"].append(struc)


    # Export Data to file
    with open('data.json', 'w', encoding='utf-8') as file:
        file.write(json.dumps(data))
        
    # Update Data to database
    with SSHTunnelForwarder(
        ssh_address_or_host=os.environ['SSHIP'],
        ssh_username='root',
        ssh_pkey=paramiko.RSAKey.from_private_key(io.StringIO(os.environ['SSHKEY'])),
        remote_bind_address= ('127.0.0.1', 27017)
    ) as ssh:
        ssh.start()
        mongoClient = pymongo.MongoClient(host='127.0.0.1',port=ssh.local_bind_port)
        myCol = mongoClient["daily"]["netflix"]

        updateTime = {'updateTime':data['updateTime']}
        hasData = myCol.find_one(updateTime)
        if hasData is not None:
            raise Exception("Data duplicated")
        # todo check pricing is changed
        r = myCol.insert_many(data['pricing'])


except Exception as error:
    print(error)
    exit(1)