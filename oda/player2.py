import requests
import time
import copy

class BotClient:
    def __init__(self, base_url):
        # Inisialisasi URL base API dan header HTTP
        self.base_url = base_url
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        self.bot_position = None      # Posisi bot saat ini di board (x,y)
        self.game_objects = []        # Semua objek di board terbaru dari server
        self.my_name = None           # Nama bot kita, untuk identifikasi
        self.is_playing = True        # Flag apakah bot masih aktif di board

    def join(self, preferred_board_id=1):
        # """
        # Bergabung ke board permainan dengan ID preferred_board_id.
        # Mendapatkan snapshot awal kondisi board dan gameObjects.
        # """
        url = f"{self.base_url}/join"
        payload = {"preferredBoardId": preferred_board_id}
        response = requests.post(url, json=payload, headers=self.headers)
        print(f"Join response: {response.status_code}")
        try:
            data = response.json()
        except Exception:
            print(response.text)
            return False

        # Simpan gameObjects dan cari posisi bot kita
        self.game_objects = data.get("gameObjects", [])
        self.find_bot()
        return True

    def find_bot(self):
        # """
        # Cari objek BotGameObject yang sesuai dengan bot kita di gameObjects,
        # lalu update posisi bot dan nama bot.
        # """
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
        # """
        # Cari posisi base bot kita dan jumlah diamond di inventory bot.
        # Mengambil dari gameObjects BotGameObject milik kita.
        # """
        base_pos = None
        inventory_count = 0
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
                base_pos = obj['properties']['base']
                inventory_count = obj['properties'].get('diamonds', 0)
                break
        return base_pos, inventory_count

    def get_inventory_limit(self):
        # """
        # Ambil kapasitas maksimal inventory bot dari properties bot kita.
        # Default 5 jika tidak ditemukan.
        # """
        for obj in self.game_objects:
            if obj['type'] == 'BotGameObject' and obj.get('properties', {}).get('name') == self.my_name:
                return obj['properties'].get('inventorySize', 5)
        return 5

    def get_diamonds(self):
        # """
        # Kumpulkan semua objek diamond (DiamondGameObject) di board,
        # dengan posisi dan poinnya.
        # """
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
        # """
        # Temukan semua teleporter yang ada di board dan kelompokkan berdasarkan pairId.
        # Setiap pairId berisi dua posisi teleport yang saling terhubung.
        # """
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
        # """
        # Hitung jarak Manhattan (jumlah langkah horisontal + vertikal)
        # antara dua titik p1 dan p2 (dictionary x,y).
        # """
        return abs(p1['x'] - p2['x']) + abs(p1['y'] - p2['y'])

    def generate_path_to(self, start, target):
        # """
        # Generate list langkah arah ("NORTH", "SOUTH", "EAST", "WEST")
        # dari posisi start ke posisi target berdasarkan perbedaan koordinat.
        # Path dibuat langkah horisontal dulu, lalu vertikal.
        # """
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
        # """
        # Kirim request move ke server untuk arah tertentu.
        # Jika response status 403 berarti bot sudah keluar board, set flag is_playing ke False.
        # Update gameObjects dan posisi bot dari response jika move berhasil.
        # """
        url = f"{self.base_url}/move"
        payload = {"direction": direction}
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Move {direction} response: {response.status_code}")
            if response.status_code == 403:
                print("Bot is no longer playing on the board. Stopping moves.")
                self.is_playing = False
                return False

            data = response.json()
            # print(json.dumps(data, indent=4))  # Disable print detail besar
            self.game_objects = data.get("gameObjects", [])
            self.find_bot()
            print(f"Bot current position: {self.bot_position}")
            return True
        except Exception as e:
            print(f'Error move: {e}')
            self.is_playing = False
            return False

    def follow_path(self, directions):
        # """
        # Ikuti list langkah arah yang diberikan, berhenti jika move gagal
        # atau bot sudah tidak aktif.
        # """
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
        # """
        # Cek apakah lewat teleport membuat jarak perjalanan jadi lebih pendek.
        # Jika iya, kembalikan path ke teleport dan posisi setelah teleport.
        # Jika tidak, kembalikan path langsung ke target dan posisi target.
        # """
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
        # """
        # Loop utama pengambilan diamond:
        # - Ambil info base dan inventory
        # - Loop selama bot aktif dan diamond masih ada
        # - Sort diamond berdasarkan poin dan jarak
        # - Jika inventory penuh, kembali ke base dulu
        # - Pilih diamond terbaik, cek teleport, lalu follow path
        # - Update posisi bot dan inventory secara realtime dari response server
        # """
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

            # Hitung jarak dan sort diamond berdasarkan poin desc, jarak asc
            for d in diamonds:
                d['distance'] = self.manhattan_distance(current_pos, d['position'])
            diamonds.sort(key=lambda d: (-d['points'], d['distance']))

            # Jika inventory penuh, kembali ke base untuk deposit
            if inventory_count >= inventory_limit:
                print(f"Inventory full. Bot at {current_pos}. Returning to base at {base_pos}.")
                path_to_base = self.generate_path_to(current_pos, base_pos)
                self.follow_path(path_to_base)
                inventory_count = 0
                current_pos = copy.deepcopy(self.bot_position)
                continue

            target = diamonds[0]
            print(f"Bot at {current_pos}, moving to diamond at {target['position']} with points {target['points']}")

            # Cek teleport untuk efisiensi perjalanan
            path_to_target, pos_after_teleport = self.use_teleport_if_beneficial(current_pos, target['position'])

            self.follow_path(path_to_target)
            current_pos = copy.deepcopy(self.bot_position)

            if not self.is_playing:
                print("Stopping as bot is no longer playing.")
                break

            # Jika teleport digunakan, update posisi bot sesuai teleport tujuan
            if pos_after_teleport != target['position']:
                print(f"Teleporting to {pos_after_teleport}")
                current_pos = pos_after_teleport

            # Jika belum sampai target, lanjutkan berjalan
            if current_pos != target['position']:
                path_after_teleport = self.generate_path_to(current_pos, target['position'])
                self.follow_path(path_after_teleport)
                current_pos = copy.deepcopy(self.bot_position)

            inventory_count += 1

            if not self.is_playing:
                print("Stopping as bot is no longer playing.")
                break

        # Setelah diamond habis, deposit sisa inventory jika ada
        if self.is_playing and inventory_count > 0 and current_pos != base_pos:
            print(f"No more diamonds. Bot at {current_pos}, returning to base at {base_pos} to deposit inventory.")
            path_to_base = self.generate_path_to(current_pos, base_pos)
            self.follow_path(path_to_base)
            inventory_count = 0

if __name__ == "__main__":
    base_url = "http://localhost:3000/api/bots/d41b9e9a-97ee-480c-9670-5ccec6edf1b7"
    # base_url = "https://rnpmd-182-253-63-43.a.free.pinggy.link/api/bots/4b4cbd72-0a3a-482d-86e2-ddac2e94445b"
    bot_client = BotClient(base_url)

    if bot_client.join(preferred_board_id=2):
        bot_client.collect_all_diamonds()
    else:
        print("Failed to join the board.")


# {
#   "name": "sr",
#   "email": "sr@mail.com",
#   "id": "d41b9e9a-97ee-480c-9670-5ccec6edf1b7"
# }
