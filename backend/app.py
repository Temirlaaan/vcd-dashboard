from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import http.client

# Увеличиваем лимит заголовков для обработки больших ответов от VCD
http.client._MAXHEADERS = 1000

from vcd_client import VCDClient
from ip_calculator import IPCalculator
from models import DashboardData, CloudStats, IPPool, IPAllocation

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(title="VCD IP Manager", version="1.0.0")

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация облаков и пулов
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
                "type": "ipSpace"
            },
            {
                "id": "urn:vcloud:ipSpace:7315f883-a0e5-4c9c-860b-528c7830813a",
                "name": "91.185.21.224/27",
                "network": "91.185.21.224/27",
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
                "network": "37.208.43.0/24",  # Исправленная сеть
                "type": "externalNetwork"
            },
            {
                "id": "urn:vcloud:network:516d858b-9549-4352-929b-d75ab300ad00",
                "name": "ALM01-Internet",
                "network": "91.185.11.0/24",  # Исправленная сеть
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
                "id": "urn:vcloud:network:41dc5ea7-043a-4f78-b530-98641393fa90",
                "name": "ExtNet-91.185.28.128m26-INTERNET-AST",
                "network": "91.185.28.128/26",
                "type": "externalNetwork"
            },
            {
                "id": "urn:vcloud:network:88bfab4e-4dc7-4605-b0f9-d8648f785812",
                "name": "ExtNet-87.255.215.0m24-INTERNET",
                "network": "87.255.215.0/24",
                "type": "externalNetwork"
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
                "type": "externalNetwork"
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

@app.get("/")
async def root():
    """Возвращает HTML страницу"""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "VCD IP Manager API"}

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    """Получить все данные для дашборда"""
    try:
        all_clouds_stats = []
        all_allocations = []
        total_ips_count = 0
        used_ips_count = 0
        free_ips_count = 0
        
        # Обрабатываем каждое облако
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]
            
            # Получаем все занятые IP для этого облака
            cloud_allocations = client.get_all_used_ips(pools)
            all_allocations.extend(cloud_allocations)
            
            # Группируем занятые IP по пулам
            cloud_pools = []
            cloud_total_ips = 0
            cloud_used_ips = 0
            cloud_free_ips = 0
            
            for pool_config in pools:
                # Получаем занятые IP для этого пула
                pool_allocations = [a for a in cloud_allocations if a.pool_name == pool_config["name"]]
                used_ips_set = set(a.ip_address for a in pool_allocations)
                
                # Рассчитываем свободные IP
                free_ips, total, used, free = IPCalculator.calculate_free_ips(
                    pool_config["network"],
                    used_ips_set
                )
                
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
                    free_addresses=free_ips[:100] if len(free_ips) > 100 else free_ips  # Ограничиваем для производительности
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
        
        # Формируем итоговый ответ
        dashboard = DashboardData(
            last_update=datetime.now(),
            total_clouds=len(all_clouds_stats),
            total_ips=total_ips_count,
            used_ips=used_ips_count,
            free_ips=free_ips_count,
            usage_percentage=round((used_ips_count / total_ips_count * 100) if total_ips_count > 0 else 0, 2),
            clouds=all_clouds_stats,
            all_allocations=all_allocations
        )
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cloud/{cloud_name}", response_model=CloudStats)
async def get_cloud_data(cloud_name: str):
    """Получить данные конкретного облака"""
    if cloud_name not in vcd_clients:
        raise HTTPException(status_code=404, detail=f"Cloud {cloud_name} not found")
    
    try:
        client = vcd_clients[cloud_name]
        config = CLOUDS_CONFIG[cloud_name]
        pools = config["pools"]
        
        # Получаем все занятые IP
        allocations = client.get_all_used_ips(pools)
        
        # Обрабатываем каждый пул
        cloud_pools = []
        total_ips = 0
        used_ips = 0
        free_ips = 0
        
        for pool_config in pools:
            pool_allocations = [a for a in allocations if a.pool_name == pool_config["name"]]
            used_ips_set = set(a.ip_address for a in pool_allocations)
            
            free_ips_list, total, used, free = IPCalculator.calculate_free_ips(
                pool_config["network"],
                used_ips_set
            )
            
            pool = IPPool(
                name=pool_config["name"],
                network=pool_config["network"],
                cloud_name=cloud_name,
                total_ips=total,
                used_ips=used,
                free_ips=free,
                usage_percentage=round((used / total * 100) if total > 0 else 0, 2),
                used_addresses=pool_allocations,
                free_addresses=free_ips_list[:100]
            )
            
            cloud_pools.append(pool)
            total_ips += total
            used_ips += used
            free_ips += free
        
        return CloudStats(
            cloud_name=cloud_name,
            total_pools=len(pools),
            total_ips=total_ips,
            used_ips=used_ips,
            free_ips=free_ips,
            usage_percentage=round((used_ips / total_ips * 100) if total_ips > 0 else 0, 2),
            pools=cloud_pools
        )
        
    except Exception as e:
        logger.error(f"Error getting cloud data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pool/{cloud_name}/{pool_name}", response_model=IPPool)
async def get_pool_data(cloud_name: str, pool_name: str):
    """Получить данные конкретного пула"""
    if cloud_name not in vcd_clients:
        raise HTTPException(status_code=404, detail=f"Cloud {cloud_name} not found")
    
    try:
        client = vcd_clients[cloud_name]
        config = CLOUDS_CONFIG[cloud_name]
        
        # Находим конфигурацию пула
        pool_config = next((p for p in config["pools"] if p["name"] == pool_name), None)
        if not pool_config:
            raise HTTPException(status_code=404, detail=f"Pool {pool_name} not found")
        
        # Получаем занятые IP для пула
        allocations = client.get_all_used_ips([pool_config])
        used_ips_set = set(a.ip_address for a in allocations)
        
        # Рассчитываем свободные IP
        free_ips_list, total, used, free = IPCalculator.calculate_free_ips(
            pool_config["network"],
            used_ips_set
        )
        
        return IPPool(
            name=pool_config["name"],
            network=pool_config["network"],
            cloud_name=cloud_name,
            total_ips=total,
            used_ips=used,
            free_ips=free,
            usage_percentage=round((used / total * 100) if total > 0 else 0, 2),
            used_addresses=allocations,
            free_addresses=free_ips_list  # Возвращаем все свободные IP для детального просмотра
        )
        
    except Exception as e:
        logger.error(f"Error getting pool data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/free-ips")
async def get_all_free_ips():
    """Получить все свободные IP адреса"""
    try:
        free_ips_by_pool = {}
        
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            allocations = client.get_all_used_ips(config["pools"])
            
            for pool_config in config["pools"]:
                pool_key = f"{cloud_name}_{pool_config['name']}"
                pool_allocations = [a for a in allocations if a.pool_name == pool_config["name"]]
                used_ips_set = set(a.ip_address for a in pool_allocations)
                
                free_ips_list, total, used, free = IPCalculator.calculate_free_ips(
                    pool_config["network"],
                    used_ips_set
                )
                
                free_ips_by_pool[pool_key] = {
                    "cloud": cloud_name,
                    "pool": pool_config["name"],
                    "network": pool_config["network"],
                    "total_free": free,
                    "free_ips": free_ips_list
                }
        
        return free_ips_by_pool
        
    except Exception as e:
        logger.error(f"Error getting free IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "clouds_configured": list(vcd_clients.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("EXPORTER_PORT", 8000)))