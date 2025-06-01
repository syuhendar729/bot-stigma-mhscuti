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
        self.my_name = None
        self.is_playing = True

    def join(self, preferred_board_id=1):
        url = f"{self.base_url}/join"
        payload = {"preferredBoardId": preferred_board_id}
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"Join response: {response.status_code}")
        try:
            data = response.json()
            # print(json.dumps(data, indent=4))  # Matikan print detail besar
        except Exception:
            print(response.text)
            return False

        self.game_objects = data.get("gameObjects", [])
        self.find_bot()
        return True

    def find_bot(self):
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
        base_pos = None
        inventory_count = 0
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
                base_pos = obj['properties']['base']
                inventory_count = obj['properties'].get('diamonds', 0)
                break
        return base_pos, inventory_count

    def get_inventory_limit(self):
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
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

    def get_teleport_pairs(self):
        pairs = {}
        for obj in self.game_objects:
            if obj.get("type") == "TeleportGameObject":
                pid = obj.get("properties", {}).get("pairId")
                if pid:
                    if pid not in pairs:
                        pairs[pid] = []
                    pairs[pid].append(obj["position"])
        return pairs

    @staticmethod
    def manhattan_distance(p1, p2):
        return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

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
            if response.status_code == 403:
                print("Bot is no longer playing on the board. Stopping moves.")
                self.is_playing = False
                return False

            data = response.json()
            # print(json.dumps(data, indent=4))  # Matikan print detail besar
            self.game_objects = data.get("gameObjects", [])
            self.find_bot()
            print(f"Bot current position: {self.bot_position}")
            return True
        except Exception:
            print(response.text)
            self.is_playing = False
            return False

    def follow_path(self, directions):
        for dir in directions:
            if not self.is_playing:
                print("Bot is no longer playing, stopping follow_path.")
                break
            success = self.move(dir)
            if not success:
                print("Move failed, stopping.")
                break
            time.sleep(0.5)

    def use_teleport_if_beneficial(self, current_pos, target_pos):
        pairs = self.get_teleport_pairs()
        direct_path = self.generate_path_to(current_pos, target_pos)
        direct_dist = len(direct_path)

        for pair_id, positions in pairs.items():
            if len(positions) != 2:
                continue

            pos_a, pos_b = positions[0], positions[1]

            dist_to_a = self.manhattan_distance(current_pos, pos_a)
            dist_from_b_to_target = self.manhattan_distance(pos_b, target_pos)
            total_dist_via_teleport_1 = dist_to_a + 1 + dist_from_b_to_target

            dist_to_b = self.manhattan_distance(current_pos, pos_b)
            dist_from_a_to_target = self.manhattan_distance(pos_a, target_pos)
            total_dist_via_teleport_2 = dist_to_b + 1 + dist_from_a_to_target

            if total_dist_via_teleport_1 < direct_dist:
                path_to_teleport = self.generate_path_to(current_pos, pos_a)
                return path_to_teleport, pos_b

            if total_dist_via_teleport_2 < direct_dist:
                path_to_teleport = self.generate_path_to(current_pos, pos_b)
                return path_to_teleport, pos_a

        return direct_path, target_pos

    def collect_all_diamonds(self):
        base_pos, inventory_count = self.get_my_base_and_inventory()
        inventory_limit = self.get_inventory_limit()

        if base_pos is None:
            print("Base position not found. Cannot proceed.")
            return

        print(f"Base position: {base_pos}, Inventory limit: {inventory_limit}")

        current_pos = copy.deepcopy(self.bot_position)

        while self.is_playing:
            diamonds = self.get_diamonds()
            if not diamonds:
                print("No diamonds left on the board.")
                break

            if current_pos is None:
                print("Current position is None. Bot might have been removed from board.")
                break

            for d in diamonds:
                d['distance'] = self.manhattan_distance(current_pos, d['position'])
            diamonds.sort(key=lambda d: (-d['points'], d['distance']))

            if inventory_count >= inventory_limit:
                print(f"Inventory full. Bot at {current_pos}. Returning to base at {base_pos}.")
                path_to_base = self.generate_path_to(current_pos, base_pos)
                self.follow_path(path_to_base)
                inventory_count = 0
                current_pos = copy.deepcopy(self.bot_position)
                continue

            target = diamonds[0]
            print(f"Bot at {current_pos}, moving to diamond at {target['position']} with points {target['points']}")

            path_to_target, pos_after_teleport = self.use_teleport_if_beneficial(current_pos, target['position'])

            self.follow_path(path_to_target)
            current_pos = copy.deepcopy(self.bot_position)

            if not self.is_playing:
                print("Stopping as bot is no longer playing.")
                break

            if pos_after_teleport != target['position']:
                print(f"Teleporting to {pos_after_teleport}")
                current_pos = pos_after_teleport

            if current_pos != target['position']:
                path_after_teleport = self.generate_path_to(current_pos, target['position'])
                self.follow_path(path_after_teleport)
                current_pos = copy.deepcopy(self.bot_position)

            inventory_count += 1

            if not self.is_playing:
                print("Stopping as bot is no longer playing.")
                break

        if self.is_playing and inventory_count > 0 and current_pos != base_pos:
            print(f"No more diamonds. Bot at {current_pos}, returning to base at {base_pos} to deposit inventory.")
            path_to_base = self.generate_path_to(current_pos, base_pos)
            self.follow_path(path_to_base)
            inventory_count = 0

