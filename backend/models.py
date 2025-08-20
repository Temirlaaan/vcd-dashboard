from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class IPAllocation(BaseModel):
    """Модель для занятого IP адреса"""
    ip_address: str
    org_name: str
    org_id: Optional[str] = None
    entity_name: Optional[str] = None
    allocation_type: str  # FLOATING_IP, EDGE, VM_ALLOCATED, NAT, etc.
    cloud_name: str  # vcd, vcd01, vcd02
    pool_name: str
    allocation_date: Optional[datetime] = None
    # Дополнительные поля для VM
    vapp_name: Optional[str] = None
    deployed: Optional[bool] = None

class IPConflict(BaseModel):
    """Модель для конфликта IP адресов"""
    ip_address: str
    clouds: List[str]  # Список облаков где используется IP
    pools: List[str]   # Список пулов где используется IP
    organizations: List[str]  # Список организаций
    conflict_type: str  # DUPLICATE_ALLOCATION, OVERLAPPING_SUBNET

class IPPool(BaseModel):
    """Модель для пула IP адресов"""
    name: str
    network: str  # например "87.255.215.0/24"
    cloud_name: str
    total_ips: int
    used_ips: int
    free_ips: int
    usage_percentage: float
    used_addresses: List[IPAllocation]
    free_addresses: List[str]
    # Новые поля для конфликтов
    has_overlaps: bool = False
    overlapping_clouds: List[str] = []
    conflicts: Optional[List[IPConflict]] = None

class CloudStats(BaseModel):
    """Статистика по облаку"""
    cloud_name: str
    total_pools: int
    total_ips: int
    used_ips: int
    free_ips: int
    usage_percentage: float
    pools: List[IPPool]

class DashboardData(BaseModel):
    """Общие данные для дашборда"""
    last_update: datetime
    total_clouds: int
    total_ips: int
    used_ips: int
    free_ips: int
    usage_percentage: float
    clouds: List[CloudStats]
    all_allocations: List[IPAllocation]
    conflicts: Dict[str, List[IPConflict]] = {}  # IP -> список конфликтов