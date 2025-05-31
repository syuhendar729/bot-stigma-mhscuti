import requests

url = "http://localhost:3000/api/boards"  # Ganti dengan endpoint API yang ingin dipanggil

response = requests.get(url)

# Cek status code
if response.status_code == 200:
    data = response.json()  # Mengambil data JSON dari response
    print(data)
else:
    print(f"Request gagal dengan status: {response.status_code}")



# import requests
#
# url = "https://api.example.com/post-endpoint"
#
# payload = {
#     "key1": "value1",
#     "key2": "value2"
# }
#
# headers = {
#     "Content-Type": "application/json"
# }
#
# response = requests.post(url, json=payload, headers=headers)
#
# if response.status_code == 200 or response.status_code == 201:
#     data = response.json()
#     print(data)
# else:
#     print(f"Request gagal dengan status: {response.status_code}")


