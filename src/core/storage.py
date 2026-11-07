import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple


def get_project_root() -> Path:
    """Proje kök dizinini döndürür."""
    return Path(__file__).resolve().parents[2]


def get_now_timestamp() -> str:
    """YYYY-MM-DD_HH-MM formatında geçerli tarih ve saat damgası döndürür."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M")


def resolve_timestamp(time_str: Optional[str] = None) -> str:
    """
    Kullanıcıdan gelen zaman/tarih metnini doğrular.
    - YYYY-MM-DD_HH-MM formatında ise doğrudan döner.
    - YYYY-MM-DD formatında verilmişse o tarihin güncel saatiyle tamamlar veya kabul eder.
    - Boş ise o anın zaman damgasını (YYYY-MM-DD_HH-MM) döndürür.
    """
    if time_str:
        clean = time_str.strip().replace(":", "-").replace(" ", "_")
        # Tam format: 2026-10-30_14-12
        if re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}$", clean):
            return clean
        # Sadece tarih: 2026-10-30
        if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
            return clean
    return get_now_timestamp()


def get_date_dir(base_dir: Path, date_str: Optional[str] = None) -> Path:
    """
    base_dir altında tarih-saat klasör yolunu döndürür ve klasörü oluşturur.
    Örnek: data/simulations/2026-10-30_14-12/
    """
    d_str = resolve_timestamp(date_str)
    target_dir = base_dir / d_str
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def list_available_dates(base_dir: Path) -> List[str]:
    """
    base_dir altındaki arşiv klasörlerini (YYYY-MM-DD_HH-MM veya YYYY-MM-DD)
    en yeniden en eskiye sıralı döndürür.
    """
    if not base_dir.exists():
        return []
    dates = []
    for item in base_dir.iterdir():
        if item.is_dir():
            # Hem YYYY-MM-DD_HH-MM hem de YYYY-MM-DD ile başlayanları kabul et
            if re.match(r"^\d{4}-\d{2}-\d{2}(_\d{2}-\d{2})?$", item.name):
                dates.append(item.name)
    dates.sort(reverse=True)
    return dates


def find_matching_date_dir(base_dir: Path, query_str: Optional[str] = None) -> Optional[Path]:
    """
    Kullanıcının sorguladığı tarih/saat ile eşleşen en uygun klasörü bulur:
    - Tam eşleşme varsa onu döner (örn: 2026-10-30_14-12)
    - Sadece gün verilmişse (örn: 2026-10-30), o güne ait EN GÜNCEL klasörü döner.
    - Hiçbir şey verilmemişse en güncel klasörü döner.
    """
    available = list_available_dates(base_dir)
    if not available:
        return None

    if not query_str:
        return base_dir / available[0]

    q_clean = query_str.strip().replace(":", "-").replace(" ", "_")

    # 1. Tam eşleşme
    if q_clean in available:
        return base_dir / q_clean

    # 2. Ön ek / gün bazlı eşleşme (örn: '2026-10-30' verilmişse '2026-10-30_19-05'i yakala)
    for folder in available:
        if folder.startswith(q_clean):
            return base_dir / folder

    return None
