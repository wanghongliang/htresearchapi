# Python requests示例
import requests
import json

# url = "http://localhost:5000/api/trader/login"
# headers = {"Content-Type": "application/json"}
# data = {
#     "user": "666627203023",
#     "password": "050201",
#     "comm_password": "23234",
#     "exe_path": "C:\\htwt\\xiadan.exe"
# }
#
# response = requests.post(url, headers=headers, json=data)
# result = json.loads(response.text)
# print("登录结果：", result)
# # 提取session_id（后续接口需使用）
# session_id = result["data"]["session_id"] if result["code"] == 200 else None

session_id = 1
# Python示例（使用上一步获取的session_id）
url = f"http://localhost:5000/api/trader/balance"
response = requests.get(url)
print("资金余额：", json.loads(response.text))



# Python示例
url = f"http://localhost:5000/api/trader/buy"
data = {
    "security": "600000",
    "price": 8.75,
    "amount": 100
}
response = requests.post(url, json=data)
print("买入结果：", json.loads(response.text))


# Python示例
url = f"http://localhost:5000/api/trader/position"
response = requests.get(url)
print("持仓信息：", json.loads(response.text))