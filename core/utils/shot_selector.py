import random

class ShotZoneSelector:
    def __init__(self, grid_size=5):
        self.grid_size = grid_size
        self.max_section = grid_size * grid_size
        self.probability_settings = {
            0: (0.6, 0.4, 0.0, 0.0),  # 難度 0：簡單
            1: (0.3, 0.4, 0.2, 0.1),  # 難度 1：中間偏簡單
            2: (0.1, 0.3, 0.4, 0.2),  # 難度 2：中間偏困難
            3: (0.0, 0.2, 0.3, 0.5),  # 難度 3：困難
        }

    def get_neighbors(self, row, col, layer, used):
        """取得以 row,col 為中心的第 layer 層（環狀一圈）的所有鄰居座標。"""
        neighbors = []
        bound = layer  # 例如 layer = 1 時，就是 5x5 扣掉 3x3 的邊緣

        for r in range(row - bound, row + bound + 1):
            for c in range(col - bound, col + bound + 1):
                if not (0 <= r < self.grid_size and 0 <= c < self.grid_size):
                    continue
                if (r, c) == (row, col):
                    continue
                if (r, c) in used:
                    continue

                # 只取這一層的「邊界」
                if layer == 0 or abs(r - row) == bound or abs(c - col) == bound:
                    sec_num = r * self.grid_size + c + 1
                    neighbors.append(f"sec{sec_num}")
        return neighbors

    def get_available_targets(self, current_sec, difficulty):
        if difficulty not in self.probability_settings:
            raise ValueError("Difficulty must be 0 ~ 3")

        # 把 'sec12' 中的 'sec' 字串移除，變成 '12'
        try:
            sec_num = int(current_sec.replace('sec', ''))
        except:
            raise ValueError("Invalid section format. Expected 'sec<number>'")

        #檢查是否在合法範圍（1 ~ 25）：
        if not (1 <= sec_num <= self.max_section):
            raise ValueError("Section number out of range.")

        # 計算該sec的(col,row)座標 ex. sec12 = (1,2)
        row = (sec_num - 1) // self.grid_size
        col = (sec_num - 1) % self.grid_size

        # 預先建立 Level 0~3 的所有鄰居集合
        area_levels = []
        used = set()

        # 計算以當前sec塊為中心，距離為 1 到 4 格範圍內的鄰居區塊(空檔區)
        for layer in range(1, 5):  # 第 0~3 層
            neighbors = self.get_neighbors(row, col, layer, used) #used用來存儲已經處理過的區塊，避免重複計算
            area_levels.append(neighbors) #好幾個list

            # 這樣4x4就不包含3x3，以此類推(25宮格元難度策略)
            used.update(((int(n.replace("sec", "")) - 1) // self.grid_size,
                         (int(n.replace("sec", "")) - 1) % self.grid_size) for n in neighbors)


        probs = self.probability_settings[difficulty]
        valid_levels = [(i, area_levels[i]) for i in range(4) if area_levels[i]]
        if not valid_levels:
            return []

        level_indices, level_neighbors = zip(*valid_levels)
        valid_probs = [probs[i] for i in level_indices]

        selected_index = random.choices(range(len(level_indices)), weights=valid_probs)[0]
        return level_neighbors[selected_index]
