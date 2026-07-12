import requests
import json
response= requests.get("http://jiaoshi.hee.gov.cn/")
print(response.text)