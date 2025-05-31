import requests
import time
import json

def manhattan_distance(p1, p2):
    return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

BASE_URL = "http://localhost:3000/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"

join_url = f"{BASE_URL}/join"
join_payload = {"preferredBoardId": 1}
headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

response = requests.post(join_url, json=join_payload, headers=headers)
print(f"Join response: {response.status_code}")

try:
    data = response.json()
    print(json.dumps(data, indent=4))
except Exception:
    print(response.text)
    data = None

if data:
    # Cari posisi bot
    bot_obj = None
    for obj in data.get("gameObjects", []):
        if obj.get("type") == "BotGameObject":
            bot_obj = obj
            break

    if bot_obj is None:
        print("Bot tidak ditemukan di response join.")
    else:
        bot_pos = bot_obj["position"]

        # Ambil semua diamond dan hitung jarak
        diamonds = []
        for obj in data.get("gameObjects", []):
            if obj.get("type") == "DiamondGameObject":
                diamond_pos = obj["position"]
                points = obj.get("properties", {}).get("points", 0)
                dist = manhattan_distance(bot_pos, diamond_pos)
                diamonds.append({
                    "id": obj["id"],
                    "position": diamond_pos,
                    "points": points,
                    "distance": dist
                })

        diamonds.sort(key=lambda d: d["distance"])

        # Tampilkan hasil
        print(f"\nPosisi bot: x={bot_pos['x']}, y={bot_pos['y']}")
        print("Diamond terdekat berdasarkan jarak:")
        for d in diamonds:
            print(f"Diamond ID {d['id']} at ({d['position']['x']}, {d['position']['y']}) - Points: {d['points']} - Distance: {d['distance']}")

# directions = ["WEST", "SOUTH", "SOUTH", "SOUTH", "WEST"]
# move_url = f"{BASE_URL}/move"
#
# for direction in directions:
#     move_payload = {"direction": direction}
#     response = requests.post(move_url, json=move_payload, headers=headers)
#     print(f"Move {direction} response: {response.status_code}")
#     try:
#         print(json.dumps(response.json(), indent=4))
#     except Exception:
#         print(response.text)
#     time.sleep(0.5)
