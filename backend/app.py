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

# Конфигурация облаков и пулов с общими подсетями
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
                "type": "ipSpace",
                "shared_with": []  # Не общий пул
            },
            {
                "id": "urn:vcloud:ipSpace:8d23d064-2de6-41a3-9d23-8555599e9d10",
                "name": "87.255.215.0/24",
                "network": "87.255.215.0/24",
                "type": "ipSpace",
                "shared_with": ["vcd02"]  # Общий пул с vcd02
            },
            {
                "id": "urn:vcloud:ipSpace:7315f883-a0e5-4c9c-860b-528c7830813a",
                "name": "91.185.21.224/27",
                "network": "91.185.21.224/27",
                "type": "ipSpace",
                "shared_with": ["vcd02"]  # Общий пул с vcd02
            },
            {
                "id": "urn:vcloud:ipSpace:5f6a1f88-094d-4877-bb9d-ee01d79da29d",
                "name": "IPS-37.17.178.208/28-internet",
                "network": "37.17.178.208/28",
                "type": "ipSpace",
                "shared_with": []  # Не общий пул
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
                "type": "externalNetwork",
                "shared_with": []
            },
            {
                "id": "urn:vcloud:network:516d858b-9549-4352-929b-d75ab300ad00",
                "name": "ALM01-Internet",
                "network": "91.185.11.0/24",
                "type": "externalNetwork",
                "shared_with": []
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
                "type": "externalNetwork",
                "shared_with": []  # Это подсеть, но не общий пул
            },
            {
                "id": "urn:vcloud:network:88bfab4e-4dc7-4605-b0f9-d8648f785812",
                "name": "ExtNet-87.255.215.0m24-INTERNET",
                "network": "87.255.215.0/24",
                "type": "externalNetwork",
                "shared_with": ["vcd"]  # Общий пул с vcd
            },
            {
                "id": "urn:vcloud:network:08020a8d-eb23-4347-b434-72641e133836",
                "name": "ExtNet-87.255.216.128m26-INTERNET-ESHDI",
                "network": "87.255.216.128/26",
                "type": "externalNetwork",
                "shared_with": []
            },
            {
                "id": "urn:vcloud:network:c054c18f-fbb1-4633-8d47-02fa431a5aab",
                "name": "ExtNet-91.185.21.224m27-INTERNET",
                "network": "91.185.21.224/27",
                "type": "externalNetwork",
                "shared_with": ["vcd"]  # Общий пул с vcd
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
    Проверяет конфликты IP адресов в рамках одного облака
    Возвращает словарь с конфликтующими IP
    """
    conflicts = {}
    
    # Группируем аллокации по облакам
    cloud_allocations = {}
    for allocation in all_allocations:
        if allocation.cloud_name not in cloud_allocations:
            cloud_allocations[allocation.cloud_name] = []
        cloud_allocations[allocation.cloud_name].append(allocation)
    
    # Проверяем конфликты внутри каждого облака
    for cloud_name, allocations in cloud_allocations.items():
        ip_usage = {}
        for allocation in allocations:
            ip = allocation.ip_address
            if ip not in ip_usage:
                ip_usage[ip] = []
            ip_usage[ip].append(allocation)
        
        # Находим дубликаты в рамках одного облака
        for ip, allocs in ip_usage.items():
            if len(allocs) > 1:
                if ip not in conflicts:
                    conflicts[ip] = []
                conflicts[ip].append(
                    IPConflict(
                        ip_address=ip,
                        clouds=[cloud_name],  # Конфликт только в одном облаке
                        pools=[a.pool_name for a in allocs],
                        organizations=[a.org_name for a in allocs],
                        conflict_type="DUPLICATE_IN_CLOUD"
                    )
                )
    
    return conflicts

def get_globally_used_ips_for_shared_pools() -> Dict[str, Set[str]]:
    """
    Получить занятые IP для общих пулов со всех облаков
    Возвращает словарь: network -> set of used IPs
    """
    shared_pool_ips = {}
    
    # Определяем все общие пулы
    shared_networks = set()
    for cloud_config in CLOUDS_CONFIG.values():
        for pool in cloud_config["pools"]:
            if pool.get("shared_with"):
                shared_networks.add(pool["network"])
    
    logger.info(f"Found shared networks: {shared_networks}")
    
    # Собираем занятые IP для каждой общей сети
    for network in shared_networks:
        shared_pool_ips[network] = set()
    
    # Получаем занятые IP со всех облаков для общих пулов
    for cloud_name, client in vcd_clients.items():
        config = CLOUDS_CONFIG[cloud_name]
        try:
            for pool_config in config["pools"]:
                if pool_config["network"] in shared_networks:
                    # Это общий пул, собираем его занятые IP
                    allocations = client.get_pool_used_ips(pool_config)
                    for allocation in allocations:
                        shared_pool_ips[pool_config["network"]].add(allocation.ip_address)
                    logger.info(f"Cloud {cloud_name}, pool {pool_config['name']}: "
                              f"{len(allocations)} IPs used in shared pool")
        except Exception as e:
            logger.error(f"Error collecting shared pool IPs from {cloud_name}: {e}")
    
    return shared_pool_ips

@app.get("/")
async def root():
    """Возвращает HTML страницу"""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "VCD IP Manager API"}

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    """Получить все данные для дашборда с учетом общих пулов"""
    try:
        all_clouds_stats = []
        all_allocations = []
        total_ips_count = 0
        used_ips_count = 0
        free_ips_count = 0
        
        # Сначала собираем занятые IP для общих пулов
        logger.info("Collecting used IPs for shared pools...")
        shared_pool_used_ips = get_globally_used_ips_for_shared_pools()
        
        # Собираем все аллокации для проверки конфликтов
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]
            
            try:
                cloud_allocations = client.get_all_used_ips(pools)
                all_allocations.extend(cloud_allocations)
            except Exception as e:
                logger.error(f"Error collecting allocations from {cloud_name}: {e}")
        
        # Проверяем конфликты (только в рамках одного облака)
        conflicts = check_ip_conflicts(all_allocations)
        if conflicts:
            logger.warning(f"Found {len(conflicts)} IP conflicts!")
            for ip, conflict_list in conflicts.items():
                for conflict in conflict_list:
                    logger.warning(f"Conflict in {conflict.clouds[0]}: IP {ip} used in pools: {', '.join(conflict.pools)}")
        
        # Обрабатываем каждое облако
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]
            
            try:
                # Получаем аллокации только для этого облака
                cloud_allocations = [a for a in all_allocations if a.cloud_name == cloud_name]
                
                cloud_pools = []
                cloud_total_ips = 0
                cloud_used_ips = 0
                cloud_free_ips = 0
                
                for pool_config in pools:
                    # Получаем аллокации для этого пула
                    pool_allocations = [a for a in cloud_allocations if a.pool_name == pool_config["name"]]
                    
                    # Определяем занятые IP
                    if pool_config.get("shared_with"):
                        # Для общего пула используем глобальные занятые IP
                        used_ips_set = shared_pool_used_ips.get(pool_config["network"], set())
                        logger.info(f"Shared pool {pool_config['name']} in {cloud_name}: "
                                  f"{len(used_ips_set)} total used IPs across all clouds")
                    else:
                        # Для независимого пула только локальные IP
                        used_ips_set = set(a.ip_address for a in pool_allocations)
                    
                    # Рассчитываем свободные IP
                    free_ips, total, used, free = IPCalculator.calculate_free_ips(
                        pool_config["network"],
                        used_ips_set
                    )
                    
                    # Проверяем конфликты для этого пула
                    pool_conflicts = []
                    for allocation in pool_allocations:
                        if allocation.ip_address in conflicts:
                            pool_conflicts.extend(conflicts[allocation.ip_address])
                    
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
                        has_overlaps=len(pool_config.get("shared_with", [])) > 0,
                        overlapping_clouds=pool_config.get("shared_with", []),
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
                
                # Для общей статистики учитываем только независимые пулы
                # чтобы не считать общие пулы дважды
                for pool_config in pools:
                    if not pool_config.get("shared_with"):
                        pool_stats = next(p for p in cloud_pools if p.name == pool_config["name"])
                        total_ips_count += pool_stats.total_ips
                        used_ips_count += pool_stats.used_ips
                        free_ips_count += pool_stats.free_ips
                    elif cloud_name == "vcd":  # Считаем общие пулы только один раз (от vcd)
                        pool_stats = next(p for p in cloud_pools if p.name == pool_config["name"])
                        total_ips_count += pool_stats.total_ips
                        used_ips_count += pool_stats.used_ips
                        free_ips_count += pool_stats.free_ips
                
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