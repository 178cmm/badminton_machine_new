"""
Program Registry

載入 training_programs.json 與文本描述，提供以名稱為主的比對能力。
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from core.nlu.normalizer import normalize_query, strip_suffix, apply_synonyms
import re


class ProgramRegistry:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
        self.programs_path = os.path.join(self.project_root, "training_programs.json")
        self.description_path = os.path.join(self.project_root, "discription.txt")
        self.programs: Dict[str, Any] = {}
        self.name_to_id: Dict[str, str] = {}
        self.aliases: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        # programs
        try:
            with open(self.programs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        # 假設結構：{"programs": [{"id":..., "name":..., "shots": [...]}, ...]}
        # 支援現有 JSON 結構：training_programs 字典
        training_programs = data.get("training_programs") or {}
        for pid, p in training_programs.items():
            name = p.get("name") or pid
            p["id"] = pid
            p["category"] = p.get("difficulty")
            # 基本別名：含原名
            p["aliases"] = list(set(p.get("aliases", []) + [name]))
            p["normalized_name"] = normalize_query(name)
            p["tokens"] = [strip_suffix(apply_synonyms(name))]
            # 從 shots 描述補充別名（例如 正手平抽球、正手高遠球）
            for shot in p.get("shots", []) or []:
                desc = shot.get("description")
                if not desc:
                    continue
                p["aliases"].append(desc)
                # 去尾綴/同義詞的變體也加入
                p["aliases"].append(strip_suffix(apply_synonyms(desc)))
            self.programs[pid] = p
            # 僅非課程（排除 levelX 或 名稱以「第N級」開頭）才納入名稱索引
            if not self._is_course_program(pid, name):
                self.name_to_id[p["normalized_name"]] = pid

        # descriptions → 產生可能的別名（簡單規則：去除「球」「訓練」尾綴）
        try:
            with open(self.description_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
        except Exception:
            lines = []

        candidates: List[str] = []
        for line in lines:
            # 只收中文詞條
            if len(line) <= 1:
                continue
            candidates.append(line)

        # 建立別名映射（加入去尾綴、描述關鍵詞）
        for pid, p in self.programs.items():
            base = strip_suffix(p["normalized_name"])
            if base and base != p["normalized_name"]:
                self.aliases.setdefault(pid, []).append(base)

        # 也納入描述中可能的短名作為候選（無對應 id，僅供模糊比對）
        self.free_terms = list(set(strip_suffix(x) for x in candidates))

        # 為基礎訓練的16個球路建立個別索引
        self._create_individual_shot_programs()
        
        # 內建最小 alias 補丁（不改檔案）：
        # 確保能命中「基礎訓練」「正手平抽球」「正手高遠球」「反手平抽球」
        alias_injections = {
            "basic_training": ["基礎訓練", "正手平抽球", "反手平抽球", "正手高遠球", "反手高遠球", "正手平抽", "反手平抽", "正手高遠", "反手高遠"],
        }
        for pid, aliases in alias_injections.items():
            if pid in self.programs:
                self.aliases.setdefault(pid, []).extend(aliases)

    def _normalize(self, s: str) -> str:
        return (s or "").strip().lower().replace(" ", "")

    def _strip_suffix(self, s: str) -> str:
        t = self._normalize(s)
        for suf in ["球", "訓練", "套餐"]:
            if t.endswith(suf):
                t = t[: -len(suf)]
        return t

    def list_program_names(self) -> List[Tuple[str, str]]:
        return [(pid, self.programs[pid].get("name", pid)) for pid in self.programs]

    def find_best_match(self, query_text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        回傳 (program_id, program_name, candidates)
        - 多筆相近時 candidates 會有多個名稱
        - 找不到則三者皆空或 candidates 空
        """
        q = strip_suffix(normalize_query(query_text))
        # 1) 完全比對
        if q in self.name_to_id:
            pid = self.name_to_id[q]
            return pid, self.programs[pid].get("name", pid), []

        # 2) token 包含（如 正手平抽 == 正手平抽球）
        contain_hits: List[Tuple[str, str]] = []
        # 優先檢查個別球路程序
        individual_shots = [(pid, p) for pid, p in self.programs.items() 
                           if p.get("category") == "individual_shot"]
        regular_programs = [(pid, p) for pid, p in self.programs.items() 
                           if not self._is_course_program(pid, p.get("name", "")) 
                           and p.get("category") != "individual_shot"]
        
        # 先檢查個別球路程序
        for pid, p in individual_shots:
            name_norm = strip_suffix(normalize_query(p.get("name", "")))
            if q and q in name_norm:
                contain_hits.append((pid, p.get("name", pid)))
            # 檢查 aliases
            for a in p.get("aliases", []):
                if not a:
                    continue
                if q in strip_suffix(normalize_query(a)):
                    contain_hits.append((pid, p.get("name", pid)))
        
        # 如果個別球路程序有匹配，直接返回
        if contain_hits:
            return contain_hits[0][0], contain_hits[0][1], []
        
        # 再檢查一般程序
        for pid, p in regular_programs:
            name_norm = strip_suffix(normalize_query(p.get("name", "")))
            if q and q in name_norm:
                contain_hits.append((pid, p.get("name", pid)))
            # 檢查 aliases
            for a in p.get("aliases", []) + self.aliases.get(pid, []):
                if not a:
                    continue
                if q in strip_suffix(normalize_query(a)):
                    contain_hits.append((pid, p.get("name", pid)))
        
        # 去重
        contain_hits = list(dict.fromkeys(contain_hits))
        if len(contain_hits) == 1:
            return contain_hits[0][0], contain_hits[0][1], []
        if len(contain_hits) > 1:
            return None, None, [n for _, n in contain_hits]

        # 3) 簡單模糊（不引入外部依賴，改用最長公共子序列近似）
        def similarity(a: str, b: str) -> float:
            from difflib import SequenceMatcher
            return SequenceMatcher(a=a, b=b).ratio()

        scored: List[Tuple[float, str, str]] = []
        for pid, p in self.programs.items():
            if self._is_course_program(pid, p.get("name", "")):
                continue
            name = p.get("name", pid)
            score = similarity(q, strip_suffix(normalize_query(name)))
            scored.append((score, pid, name))
        scored.sort(reverse=True)

        if scored and scored[0][0] >= 0.85:
            return scored[0][1], scored[0][2], []
        elif scored and scored[0][0] >= 0.75:
            # 視為多筆相近，回傳前幾個候選
            candidates = [name for _, _, name in scored[:3]]
            return None, None, candidates

        return None, None, []

    def _create_individual_shot_programs(self):
        """為基礎訓練的16個球路建立個別程序"""
        basic_training = self.programs.get("basic_training")
        if not basic_training:
            return
            
        shots = basic_training.get("shots", [])
        for i, shot in enumerate(shots):
            description = shot.get("description", "")
            if not description:
                continue
                
            # 建立個別球路程序ID
            shot_id = f"shot_{i+1:02d}_{description.replace(' ', '_')}"
            
            # 建立個別球路程序
            shot_program = {
                "id": shot_id,
                "name": description,
                "description": f"單一球路訓練：{description}",
                "difficulty": "beginner",
                "duration_minutes": 5,
                "shots": [shot],  # 只包含這一個球路
                "repeat_times": 1,
                "aliases": [description],
                "normalized_name": normalize_query(description),
                "tokens": [strip_suffix(apply_synonyms(description))],
                "category": "individual_shot"
            }
            
            # 加入程序字典
            self.programs[shot_id] = shot_program
            
            # 加入名稱索引
            self.name_to_id[shot_program["normalized_name"]] = shot_id
            
            # 建立別名
            aliases = self._generate_aliases(description)
            for alias in aliases:
                self.name_to_id[alias] = shot_id

    def _generate_aliases(self, name: str) -> List[str]:
        """為名稱生成別名"""
        aliases = []
        
        # 去尾綴版本
        stripped = strip_suffix(name)
        if stripped != name:
            aliases.append(stripped)
            
        # 同義詞替換版本
        synonymed = apply_synonyms(name)
        if synonymed != name:
            aliases.append(synonymed)
            
        # 去尾綴+同義詞版本
        both = strip_suffix(apply_synonyms(name))
        if both != name and both not in aliases:
            aliases.append(both)
            
        return aliases

    def _is_course_program(self, program_id: str, name: str) -> bool:
        # 規則：id 以 level 開頭 或 名稱以「第N級」開頭都視為課程
        if program_id and program_id.lower().startswith("level"):
            return True
        try:
            return bool(re.match(r"^第\d+級", name))
        except Exception:
            return False


