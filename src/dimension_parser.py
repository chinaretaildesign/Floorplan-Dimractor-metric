import re
import regex
from typing import Dict, List, Optional

class DimensionParser:
    """尺寸解析器：支持英制(inch / feet-inch / 分数) 与公制(mm / cm / m)。
    返回值统一以 mm 为主，并附带 meters / unit / raw。
    - 英制输入 -> 换算成 mm（inch*25.4）。
    - 公制输入 -> 识别单位后缀(mm/cm/m/公尺/公分/米)，无后缀时按 default_unit 处理。
    - bare_as_mm=True 时，无单位的纯数字也按 mm 处理（适合已知图纸全为公制 mm 的场景）。
    """

    def __init__(self, default_unit: str = "mm", bare_as_mm: bool = False):
        self.default_unit = default_unit.lower()
        self.bare_as_mm = bare_as_mm
        self.setup_patterns()

    def setup_patterns(self):
        # ---- 英制 ----
        self.simple_inches = re.compile(r'(\d+(?:\.\d+)?)\s*["\u2033]')
        self.feet_inches = re.compile(r'(\d+)\s*[\'\u2032]\s*(\d+(?:\.\d+)?)\s*["\u2033]')
        self.fraction_pattern = re.compile(r'(\d+)\s*[\(]?\s*(\d+)\s*/\s*(\d+)\s*[\)]?\s*["\u2033]')

        # ---- 公制（必须带单位后缀）----
        self.metric_explicit = re.compile(
            r'(\d+(?:\.\d+)?)\s*(mm|cm|m|公尺|公分|米)\b', re.IGNORECASE)

        # ---- 纯数字（仅在 bare_as_mm=True 时启用）----
        self.bare = re.compile(r'(\d+(?:\.\d+)?)')

        # ---- 组合（英制，用于兼容原逻辑）----
        self.combined_pattern = regex.compile(r'''
            (?:
                (\d+)\s*[\'\u2032]\s*(\d+(?:\.\d+)?)\s*["\u2033]|
                (\d+)\s*[\(]?\s*(\d+)\s*/\s*(\d+)\s*[\)]?\s*["\u2033]|
                (\d+(?:\.\d+)?)\s*["\u2033]
            )
        ''', regex.VERBOSE)

    # ---------- 单位换算 ----------
    def to_mm(self, value: float, unit: Optional[str]) -> float:
        unit = (unit or self.default_unit).lower()
        if unit in ("m", "\u516c\u5c3a", "\u7c73"):
            return value * 1000.0
        if unit in ("cm", "\u516c\u5206"):
            return value * 10.0
        return value  # mm 或默认 mm

    def parse_fraction(self, whole: str, numerator: str, denominator: str) -> float:
        try:
            return (float(whole) if whole else 0) + float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            return 0.0

    # ---------- 单条解析 ----------
    def parse_dimension(self, text: str) -> Optional[Dict]:
        text = text.strip()
        # 英制：feet-inch
        fm = self.feet_inches.search(text)
        if fm:
            inch = float(fm.group(1)) * 12 + float(fm.group(2))
            return self._pack(inch * 25.4, "ft-in")
        # 英制：分数 inch
        frac = self.fraction_pattern.search(text)
        if frac:
            inch = self.parse_fraction(frac.group(1), frac.group(2), frac.group(3))
            return self._pack(inch * 25.4, "inch-frac")
        # 英制：简单 inch
        inch = self.simple_inches.search(text)
        if inch:
            return self._pack(float(inch.group(1)) * 25.4, "inch")
        # 公制：带单位
        me = self.metric_explicit.search(text)
        if me:
            val = float(me.group(1))
            unit = me.group(2)
            return self._pack(self.to_mm(val, unit), unit or self.default_unit)
        # 公制：纯数字（仅在 bare_as_mm 时）
        if self.bare_as_mm:
            b = self.bare.search(text)
            if b:
                return self._pack(self.to_mm(float(b.group(1)), None), self.default_unit)
        return None

    def _pack(self, value_mm: float, unit: str) -> Dict:
        return {
            "raw": None,
            "value_mm": round(value_mm, 2),
            "meters": round(value_mm / 1000.0, 3),
            "unit": unit,
            "inches": round(value_mm / 25.4, 2),  # 兼容旧字段
        }

    # ---------- 从带 bbox 的文本中提取 ----------
    def extract_dimensions_from_text(self, text: str, bbox: List[float]) -> List[Dict]:
        dimensions = []
        # 英制组合匹配
        for match in self.combined_pattern.finditer(text):
            d = self.parse_dimension(match.group(0))
            if d:
                d["raw"] = match.group(0)
                d["bbox"] = bbox
                dimensions.append(d)
        # 公制（带单位 或 纯数字）
        metric_hits = list(self.metric_explicit.finditer(text))
        for m in metric_hits:
            d = self._pack(self.to_mm(float(m.group(1)), m.group(2)), m.group(2) or self.default_unit)
            d["raw"] = m.group(0)
            d["bbox"] = bbox
            dimensions.append(d)
        if self.bare_as_mm:
            for m in self.bare.finditer(text):
                seg = text[max(0, m.start()-1): m.end()+1]
                if self.metric_explicit.search(seg):
                    continue  # 已被公制带单位捕获
                d = self._pack(self.to_mm(float(m.group(1)), None), self.default_unit)
                d["raw"] = m.group(0)
                d["bbox"] = bbox
                dimensions.append(d)
        # 去重（同一文本同一数值只留一条）
        seen = set()
        uniq = []
        for d in dimensions:
            key = (round(d["value_mm"], 1), tuple(d["bbox"]))
            if key not in seen:
                seen.add(key)
                uniq.append(d)
        return uniq
