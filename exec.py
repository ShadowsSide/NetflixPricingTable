import json

with open("countries.json", 'r', encoding="utf-8") as r:
    cData = json.loads(r.read())

def Countryconvert(code):
    for i in cData:
        if code == i['iso2']:
            return i['translations']['cn'], i['emoji']
                
def Currencyconvert(code):
    for i in cData:
        if code == i['currency']:
            return i['currency_symbol']


with open("origin.json", 'r', encoding="utf-8") as r:
    j = json.loads(r.read())
    countryList = {}
    for i in j:
        countryList[i['Code']] = i
        c,e = Countryconvert(i['Code'])
        countryList[i['Code']]['country'] = c
        countryList[i['Code']]['emoji'] = e
        countryList[i['Code']]['symbol'] = Currencyconvert(i['Currency'])
    jsObj = json.dumps(countryList)
    fileObject = open('data.json', 'w', encoding='utf-8')
    fileObject.write(jsObj)
    fileObject.close()
