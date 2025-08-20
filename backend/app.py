from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict, Set
from datetime import datetime
import pytz
from pathlib import Path
import http.client

# Увеличиваем лимит заголовков для обработки больших ответов от VCD
http.client._MAXHEADERS = 1000

from vcd_client import VCDClient
from ip_calculator import IPCalculator
from models import DashboardData, CloudStats, IPPool, IPAllocation, IPConflict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(title="VCD IP Manager", version="1.0.0")

# Настройка часового пояса (Астана/Алматы)
LOCAL_TZ = pytz.timezone('Asia/Almaty')  # UTC+6

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация облаков и пулов с перекрывающимися подсетями
CLOUDS_CONFIG = {
    "vcd": {
        "url": os.getenv("VCD_URL"),
        "api_version": os.getenv("VCD_API_VERSION", "38.0"),
        "api_token": os.getenv("VCD_API_TOKEN"),
        "pools": [
            {
                "id": "urn:vcloud:ipSpace:1bb7eae1-2d5c-4bb5-bfc4-ce82d7495c6a",
                "name": "176.98.235.0/24",
                "network": "176.98.235.0/24",
                "type": "ipSpace"
            },
            {
                "id": "urn:vcloud:ipSpace:8d23d064-2de6-41a3-9d23-8555599e9d10",
                "name": "87.255.215.0/24",
                "network": "87.255.215.0/24",
                "type": "ipSpace",
                "overlaps_with": ["vcd02"]  # Указываем перекрытие
            },
            {
                "id": "urn:vcloud:ipSpace:7315f883-a0e5-4c9c-860b-528c7830813a",
                "name": "91.185.21.224/27",
                "network": "91.185.21.224/27",
                "type": "ipSpace",
                "overlaps_with": ["vcd02"]  # Указываем перекрытие
            },
            {
                "id": "urn:vcloud:ipSpace:5f6a1f88-094d-4877-bb9d-ee01d79da29d",
                "name": "IPS-37.17.178.208/28-internet",
                "network": "37.17.178.208/28",
                "type": "ipSpace"
            }
        ]
    },
    "vcd01": {
        "url": os.getenv("VCD_URL_VCD01"),
        "api_version": os.getenv("VCD_API_VERSION_VCD01", "37.0"),
        "api_token": os.getenv("VCD_API_TOKEN_VCD01"),
        "pools": [
            {
                "id": "urn:vcloud:network:7eecf17f-838d-4348-936d-4099f860e52c",
                "name": "Internet",
                "network": "37.208.43.0/24",
                "type": "externalNetwork"
            },
            {
                "id": "urn:vcloud:network:516d858b-9549-4352-929b-d75ab300ad00",
                "name": "ALM01-Internet",
                "network": "91.185.11.0/24",
                "type": "externalNetwork"
            }
        ]
    },
    "vcd02": {
        "url": os.getenv("VCD_URL_VCD02"),
        "api_version": os.getenv("VCD_API_VERSION_VCD02", "37.0"),
        "api_token": os.getenv("VCD_API_TOKEN_VCD02"),
        "pools": [
            {
                "id": "urn:vcloud:network:2e11613a-8f32-41b6-9b76-6d3ff9e412e0",
                "name": "ExtNet-176.98.235.0m25-INTERNET",
                "network": "176.98.235.0/25",
                "type": "externalNetwork"
            },
            {
                "id": "urn:vcloud:network:88bfab4e-4dc7-4605-b0f9-d8648f785812",
                "name": "ExtNet-87.255.215.0m24-INTERNET",
                "network": "87.255.215.0/24",
                "type": "externalNetwork",
                "overlaps_with": ["vcd"]  # Указываем перекрытие
            },
            {
                "id": "urn:vcloud:network:08020a8d-eb23-4347-b434-72641e133836",
                "name": "ExtNet-87.255.216.128m26-INTERNET-ESHDI",
                "network": "87.255.216.128/26",
                "type": "externalNetwork"
            },
            {
                "id": "urn:vcloud:network:c054c18f-fbb1-4633-8d47-02fa431a5aab",
                "name": "ExtNet-91.185.21.224m27-INTERNET",
                "network": "91.185.21.224/27",
                "type": "externalNetwork",
                "overlaps_with": ["vcd"]  # Указываем перекрытие
            }
        ]
    }
}

# Инициализация клиентов
vcd_clients = {}
for cloud_name, config in CLOUDS_CONFIG.items():
    if config["url"] and config["api_token"]:
        vcd_clients[cloud_name] = VCDClient(
            base_url=config["url"],
            api_version=config["api_version"],
            api_token=config["api_token"],
            cloud_name=cloud_name
        )
        logger.info(f"Initialized client for {cloud_name}")
    else:
        logger.warning(f"Missing configuration for {cloud_name}")

def get_local_time():
    """Получить текущее локальное время"""
    return datetime.now(LOCAL_TZ)

def check_ip_conflicts(all_allocations: List[IPAllocation]) -> Dict[str, List[IPConflict]]:
    """
    Проверяет конфликты IP адресов между облаками
    Возвращает словарь с конфликтующими IP
    """
    ip_usage = {}
    conflicts = {}
    
    # Собираем все использования IP
    for allocation in all_allocations:
        ip = allocation.ip_address
        if ip not in ip_usage:
            ip_usage[ip] = []
        ip_usage[ip].append(allocation)
    
    # Находим конфликты
    for ip, allocations in ip_usage.items():
        if len(allocations) > 1:
            conflicts[ip] = [
                IPConflict(
                    ip_address=ip,
                    clouds=[a.cloud_name for a in allocations],
                    pools=[a.pool_name for a in allocations],
                    organizations=[a.org_name for a in allocations],
                    conflict_type="DUPLICATE_ALLOCATION"
                )
            ]
    
    return conflicts

def get_globally_used_ips(all_allocations: List[IPAllocation]) -> Set[str]:
    """Получить множество всех занятых IP адресов во всех облаках"""
    return set(allocation.ip_address for allocation in all_allocations)

@app.get("/")
async def root():
    """Возвращает HTML страницу"""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "VCD IP Manager API"}

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    """Получить все данные для дашборда с проверкой конфликтов"""
    try:
        all_clouds_stats = []
        all_allocations = []
        global_used_ips = set()
        total_ips_count = 0
        used_ips_count = 0
        free_ips_count = 0
        
        # Сначала собираем ВСЕ занятые IP со всех облаков
        logger.info("Collecting all used IPs from all clouds...")
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]
            
            try:
                cloud_allocations = client.get_all_used_ips(pools)
                all_allocations.extend(cloud_allocations)
                
                # Добавляем IP в глобальный набор
                for allocation in cloud_allocations:
                    global_used_ips.add(allocation.ip_address)
                    
            except Exception as e:
                logger.error(f"Error collecting IPs from {cloud_name}: {e}")
        
        logger.info(f"Total globally used IPs: {len(global_used_ips)}")
        
        # Проверяем конфликты
        conflicts = check_ip_conflicts(all_allocations)
        if conflicts:
            logger.warning(f"Found {len(conflicts)} IP conflicts between clouds!")
            for ip, conflict_list in conflicts.items():
                for conflict in conflict_list:
                    logger.warning(f"Conflict: IP {ip} used in clouds: {', '.join(conflict.clouds)}")
        
        # Теперь обрабатываем каждое облако с учетом глобальных IP
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]
            
            try:
                # Получаем занятые IP только для этого облака
                cloud_allocations = [a for a in all_allocations if a.cloud_name == cloud_name]
                
                cloud_pools = []
                cloud_total_ips = 0
                cloud_used_ips = 0
                cloud_free_ips = 0
                
                for pool_config in pools:
                    # Получаем занятые IP для этого пула
                    pool_allocations = [a for a in cloud_allocations if a.pool_name == pool_config["name"]]
                    used_ips_in_pool = set(a.ip_address for a in pool_allocations)
                    
                    # Проверяем перекрывающиеся подсети
                    overlaps = pool_config.get("overlaps_with", [])
                    if overlaps:
                        logger.info(f"Pool {pool_config['name']} in {cloud_name} overlaps with {overlaps}")
                        
                        # Для перекрывающихся подсетей учитываем глобально занятые IP
                        all_ips_in_network = set(IPCalculator.get_all_ips_in_network(pool_config["network"]))
                        
                        # Добавляем глобально занятые IP которые попадают в эту подсеть
                        globally_used_in_network = global_used_ips.intersection(all_ips_in_network)
                        used_ips_set = used_ips_in_pool.union(globally_used_in_network)
                        
                        logger.info(f"Pool {pool_config['name']}: {len(used_ips_in_pool)} locally used, "
                                  f"{len(globally_used_in_network)} globally used, "
                                  f"{len(used_ips_set)} total used")
                    else:
                        # Для неперекрывающихся подсетей используем только локальные IP
                        used_ips_set = used_ips_in_pool
                    
                    # Рассчитываем свободные IP
                    free_ips, total, used, free = IPCalculator.calculate_free_ips(
                        pool_config["network"],
                        used_ips_set
                    )
                    
                    # Проверяем конфликты для этого пула
                    pool_conflicts = []
                    for ip in used_ips_in_pool:
                        if ip in conflicts:
                            pool_conflicts.extend(conflicts[ip])
                    
                    # Создаем объект пула
                    pool = IPPool(
                        name=pool_config["name"],
                        network=pool_config["network"],
                        cloud_name=cloud_name,
                        total_ips=total,
                        used_ips=used,
                        free_ips=free,
                        usage_percentage=round((used / total * 100) if total > 0 else 0, 2),
                        used_addresses=pool_allocations,
                        free_addresses=free_ips[:100] if len(free_ips) > 100 else free_ips,
                        has_overlaps=len(overlaps) > 0,
                        overlapping_clouds=overlaps,
                        conflicts=pool_conflicts if pool_conflicts else None
                    )
                    
                    cloud_pools.append(pool)
                    cloud_total_ips += total
                    cloud_used_ips += used
                    cloud_free_ips += free
                
                # Создаем статистику облака
                cloud_stats = CloudStats(
                    cloud_name=cloud_name,
                    total_pools=len(pools),
                    total_ips=cloud_total_ips,
                    used_ips=cloud_used_ips,
                    free_ips=cloud_free_ips,
                    usage_percentage=round((cloud_used_ips / cloud_total_ips * 100) if cloud_total_ips > 0 else 0, 2),
                    pools=cloud_pools
                )
                
                all_clouds_stats.append(cloud_stats)
                total_ips_count += cloud_total_ips
                used_ips_count += cloud_used_ips
                free_ips_count += cloud_free_ips
                
            except Exception as e:
                logger.error(f"Error processing cloud {cloud_name}: {e}")
                continue
        
        # Формируем итоговый ответ
        dashboard = DashboardData(
            last_update=get_local_time(),
            total_clouds=len(all_clouds_stats),
            total_ips=total_ips_count,
            used_ips=used_ips_count,
            free_ips=free_ips_count,
            usage_percentage=round((used_ips_count / total_ips_count * 100) if total_ips_count > 0 else 0, 2),
            clouds=all_clouds_stats,
            all_allocations=all_allocations,
            conflicts=conflicts if conflicts else {}
        )
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conflicts")
async def get_ip_conflicts():
    """Получить список конфликтующих IP адресов"""
    try:
        all_allocations = []
        
        # Собираем все аллокации
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            allocations = client.get_all_used_ips(config["pools"])
            all_allocations.extend(allocations)
        
        conflicts = check_ip_conflicts(all_allocations)
        
        return {
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "timestamp": get_local_time()
        }
        
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": get_local_time().isoformat(),
        "timezone": str(LOCAL_TZ),
        "clouds_configured": list(vcd_clients.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("EXPORTER_PORT", 8000)))