import requests
import time
import json
import copy

class BotClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        self.bot_position = None
        self.game_objects = []
        self.my_name = None  # Nama bot kita, diambil dari gameObjects

    def join(self, preferred_board_id=1):
        url = f"{self.base_url}/join"
        payload = {"preferredBoardId": preferred_board_id}
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"Join response: {response.status_code}")
        try:
            data = response.json()
            print(json.dumps(data, indent=4))
        except Exception:
            print(response.text)
            return False

        self.game_objects = data.get("gameObjects", [])
        self.find_bot()
        return True

    def find_bot(self):
        # Cari bot kita sendiri dan simpan posisi serta nama
        for obj in self.game_objects:
            if obj.get("type") == "BotGameObject":
                self.bot_position = obj.get("position")
                self.my_name = obj.get("properties", {}).get("name")
                print(f"Bot found at position: {self.bot_position} with name: {self.my_name}")
                return
        print("Bot not found in game objects.")
        self.bot_position = None
        self.my_name = None

    def get_my_base_and_inventory(self):
        # Cari base dan inventory count dari bot kita sendiri
        base_pos = None
        inventory_count = 0
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
                base_pos = obj['properties']['base']
                inventory_count = obj['properties'].get('diamonds', 0)
                break
        return base_pos, inventory_count

    def get_inventory_limit(self):
        # Dapatkan kapasitas inventory dari BotProvider config jika ada, default 5
        # Bisa ambil dari fitur atau properties bot di gameObjects
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
                # Jika tersedia bisa disesuaikan
                return obj['properties'].get('inventorySize', 5)
        return 5

    def get_diamonds(self):
        diamonds = []
        for obj in self.game_objects:
            if obj.get("type") == "DiamondGameObject":
                diamonds.append({
                    "id": obj["id"],
                    "position": obj["position"],
                    "points": obj.get("properties", {}).get("points", 0)
                })
        return diamonds

    @staticmethod
    def manhattan_distance(p1, p2):
        return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

    def get_diamonds_sorted(self):
        diamonds = self.get_diamonds()
        for d in diamonds:
            d['distance'] = self.manhattan_distance(self.bot_position, d['position'])
        # Sort diamond by points desc, then distance asc
        diamonds.sort(key=lambda d: (-d['points'], d['distance']))
        return diamonds

    def generate_path_to(self, start, target):
        directions = []
        x, y = start['x'], start['y']
        tx, ty = target['x'], target['y']

        while x != tx:
            if x < tx:
                directions.append("EAST")
                x += 1
            else:
                directions.append("WEST")
                x -= 1

        while y != ty:
            if y < ty:
                directions.append("SOUTH")
                y += 1
            else:
                directions.append("NORTH")
                y -= 1

        return directions

    def move(self, direction):
        url = f"{self.base_url}/move"
        payload = {"direction": direction}
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"Move {direction} response: {response.status_code}")
        try:
            # Update game state setelah move agar posisi bot dan gameObjects update
            data = response.json()
            print(json.dumps(data, indent=4))
            self.game_objects = data.get("gameObjects", [])
            self.find_bot()  # Update posisi bot terbaru
            return True
        except Exception:
            print(response.text)
            return False

    def follow_path(self, directions):
        for dir in directions:
            success = self.move(dir)
            if not success:
                print("Move failed, stopping.")
                break
            time.sleep(0.2)

    def collect_all_diamonds(self):
        base_pos, inventory_count = self.get_my_base_and_inventory()
        inventory_limit = self.get_inventory_limit()

        if base_pos is None:
            print("Base position not found. Cannot proceed.")
            return

        print(f"Base position: {base_pos}, Inventory limit: {inventory_limit}")

        current_pos = copy.deepcopy(self.bot_position)

        while True:
            diamonds = self.get_diamonds()
            if not diamonds:
                print("No diamonds left on the board.")
                break

            # Hitung ulang jarak dan sort dengan prioritas poin + jarak
            for d in diamonds:
                d['distance'] = self.manhattan_distance(current_pos, d['position'])
            diamonds.sort(key=lambda d: (-d['points'], d['distance']))

            # Kalau inventory penuh, balik dulu ke base
            if inventory_count >= inventory_limit:
                print("Inventory full, returning to base.")
                path_to_base = self.generate_path_to(current_pos, base_pos)
                self.follow_path(path_to_base)
                inventory_count = 0
                current_pos = base_pos
                continue

            # Pilih diamond target pertama (paling prioritas)
            target = diamonds[0]

            # Generate path ke diamond
            path_to_diamond = self.generate_path_to(current_pos, target['position'])
            print(f"Moving to diamond {target['id']} at {target['position']} with points {target['points']}")

            self.follow_path(path_to_diamond)
            inventory_count += 1
            current_pos = target['position']

        # Setelah tidak ada diamond lagi, pastikan inventory dikosongkan ke base
        if inventory_count > 0 and current_pos != base_pos:
            print("No more diamonds, returning to base to deposit remaining inventory.")
            path_to_base = self.generate_path_to(current_pos, base_pos)
            self.follow_path(path_to_base)
            inventory_count = 0
