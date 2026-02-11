# backend/app.py
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
import pytz
from pathlib import Path
import http.client
import ipaddress
from concurrent.futures import ThreadPoolExecutor

# Увеличиваем лимит заголовков для обработки больших ответов от VCD
http.client._MAXHEADERS = 1000

from vcd_client import VCDClient
from ip_calculator import IPCalculator
from models import DashboardData, CloudStats, IPPool, IPAllocation, IPConflict
from keycloak_auth import (
    get_current_active_user,
    login_user,
    refresh_token as refresh_keycloak_token,
    logout_user,
    KeycloakUser,
    exchange_code_for_token
)
from redis_cache import cache
from clouds_config import CLOUDS_CONFIG
from pydantic import BaseModel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(title="VCD IP Manager", version="2.1.0")

# Настройка часового пояса (Астана/Алматы)
LOCAL_TZ = pytz.timezone('Asia/Almaty')

# Thread pool для блокирующих вызовов (Keycloak, VCD API)
executor = ThreadPoolExecutor(max_workers=4)

# CORS — ограничиваем до фронтенд-домена
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "https://vcd-public-ips.t-cloud.kz,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    Проверяет конфликты IP адресов:
    1) Дубликаты внутри одного облака (DUPLICATE_IN_CLOUD)
    2) Дубликаты между облаками в shared/overlapping пулах (CROSS_CLOUD_CONFLICT)
    """
    conflicts = {}

    # --- 1. Конфликты внутри одного облака ---
    cloud_allocations: Dict[str, List[IPAllocation]] = {}
    for allocation in all_allocations:
        cloud_allocations.setdefault(allocation.cloud_name, []).append(allocation)

    for cloud_name, allocations in cloud_allocations.items():
        ip_usage: Dict[str, List[IPAllocation]] = {}
        for allocation in allocations:
            ip_usage.setdefault(allocation.ip_address, []).append(allocation)

        for ip, allocs in ip_usage.items():
            if len(allocs) > 1:
                conflicts.setdefault(ip, []).append(
                    IPConflict(
                        ip_address=ip,
                        clouds=[cloud_name],
                        pools=list({a.pool_name for a in allocs}),
                        organizations=list({a.org_name for a in allocs}),
                        conflict_type="DUPLICATE_IN_CLOUD"
                    )
                )

    # --- 2. Кросс-облачные конфликты в shared/overlapping пулах ---
    # Строим группы пересекающихся сетей
    pool_network_map = []  # [(cloud_name, pool_config, ip_network)]
    for cname, cfg in CLOUDS_CONFIG.items():
        for pool in cfg["pools"]:
            try:
                pool_network_map.append((cname, pool, ipaddress.ip_network(pool["network"])))
            except ValueError:
                continue

    # Собираем группы сетей, которые пересекаются или явно связаны через shared_with
    shared_groups: List[Set[str]] = []  # каждый элемент — множество (cloud_name, network)
    for i, (c1, p1, n1) in enumerate(pool_network_map):
        for j, (c2, p2, n2) in enumerate(pool_network_map):
            if i >= j or c1 == c2:
                continue
            is_shared = (c2 in p1.get("shared_with", []) or
                         c1 in p2.get("shared_with", []) or
                         n1.overlaps(n2))
            if is_shared:
                pair = {(c1, p1["network"]), (c2, p2["network"])}
                # Пробуем добавить в существующую группу
                merged = False
                for group in shared_groups:
                    if group & pair:
                        group |= pair
                        merged = True
                        break
                if not merged:
                    shared_groups.append(pair)

    # Для каждой группы проверяем кросс-облачные дубликаты
    for group in shared_groups:
        clouds_in_group = {cn for cn, _ in group}
        networks_in_group = {net for _, net in group}

        # Собираем аллокации из этих облаков и этих сетей
        group_allocs: Dict[str, List[IPAllocation]] = {}
        for alloc in all_allocations:
            if alloc.cloud_name in clouds_in_group:
                # Проверяем, что IP принадлежит одной из сетей группы
                for net_str in networks_in_group:
                    try:
                        net = ipaddress.ip_network(net_str)
                        if ipaddress.ip_address(alloc.ip_address) in net:
                            group_allocs.setdefault(alloc.ip_address, []).append(alloc)
                            break
                    except ValueError:
                        continue

        for ip, allocs in group_allocs.items():
            unique_clouds = {a.cloud_name for a in allocs}
            if len(unique_clouds) > 1:
                conflicts.setdefault(ip, []).append(
                    IPConflict(
                        ip_address=ip,
                        clouds=sorted(unique_clouds),
                        pools=list({a.pool_name for a in allocs}),
                        organizations=list({a.org_name for a in allocs}),
                        conflict_type="CROSS_CLOUD_CONFLICT"
                    )
                )

    return conflicts


def get_globally_used_ips_for_shared_pools() -> Dict[str, Set[str]]:
    """
    Получить ВСЕ занятые IP для общих пулов со всех облаков, включая пересекающиеся подсети.
    """
    shared_pool_ips = {}

    # Собираем все networks из всех clouds
    all_networks = {}
    for cloud_name, config in CLOUDS_CONFIG.items():
        for pool in config["pools"]:
            network = pool["network"]
            try:
                all_networks[network] = {
                    "cloud": cloud_name,
                    "pool_config": pool,
                    "ip_net": ipaddress.ip_network(network)
                }
            except ValueError as e:
                logger.error(f"Invalid network {network}: {e}")

    # Детектируем shared: explicit (shared_with) + overlaps
    shared_networks: Dict[str, Set[str]] = {}
    network_keys = list(all_networks.keys())
    for i, net1 in enumerate(network_keys):
        info1 = all_networks[net1]
        for net2 in network_keys[i + 1:]:
            info2 = all_networks[net2]
            # Проверяем только реальные пересечения или явные shared_with
            has_overlap = info1["ip_net"].overlaps(info2["ip_net"])
            explicitly_shared = (
                info2["cloud"] in info1["pool_config"].get("shared_with", []) or
                info1["cloud"] in info2["pool_config"].get("shared_with", [])
            )
            if has_overlap or explicitly_shared:
                # Группируем по наибольшей сети (детерминированно)
                larger = max(info1["ip_net"], info2["ip_net"],
                             key=lambda n: (n.num_addresses, int(n.network_address)))
                group_key = str(larger)
                shared_networks.setdefault(group_key, set()).update([net1, net2])

    logger.info(f"Found {len(shared_networks)} shared/overlapping network groups")

    # Для каждой группы собираем used_ips со всех clouds
    for group_key, networks in shared_networks.items():
        shared_pool_ips[group_key] = set()
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            for pool_config in config["pools"]:
                if pool_config["network"] in networks:
                    allocations = client.get_pool_used_ips(pool_config)
                    for alloc in allocations:
                        shared_pool_ips[group_key].add(alloc.ip_address)
                    logger.info(
                        f"Added {len(allocations)} IPs from "
                        f"{cloud_name}/{pool_config['name']} to group {group_key}"
                    )

    return shared_pool_ips


# Модели для API
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ================== АВТОРИЗАЦИЯ ==================

@app.post("/api/login", response_model=Token)
async def login(user_login: UserLogin):
    """Вход в систему через Keycloak"""
    try:
        loop = asyncio.get_event_loop()
        token_data = await loop.run_in_executor(
            executor, login_user, user_login.username, user_login.password
        )
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@app.post("/api/refresh", response_model=Token)
async def refresh(refresh_request: RefreshTokenRequest):
    """Обновление токена"""
    try:
        loop = asyncio.get_event_loop()
        token_data = await loop.run_in_executor(
            executor, refresh_keycloak_token, refresh_request.refresh_token
        )
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )

@app.post("/api/logout")
async def logout(
    refresh_request: RefreshTokenRequest,
    current_user: KeycloakUser = Depends(get_current_active_user)
):
    """Выход из системы"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, logout_user, refresh_request.refresh_token)
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "Logged out (with warnings)"}

@app.get("/api/verify")
async def verify_token(current_user: KeycloakUser = Depends(get_current_active_user)):
    """Проверка токена"""
    return {
        "valid": True,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles
    }

@app.get("/api/callback", response_model=Token)
async def keycloak_callback(code: str = Query(...)):
    """Обмен code на token после редиректа от Keycloak"""
    try:
        loop = asyncio.get_event_loop()
        token_data = await loop.run_in_executor(executor, exchange_code_for_token, code)
        return token_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Callback error: {e}")
        raise HTTPException(status_code=401, detail="Authorization failed")


# ================== ПУБЛИЧНЫЕ ЭНДПОИНТЫ ==================

@app.get("/")
async def root():
    """Возвращает HTML страницу (публичный)"""
    html_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "VCD IP Manager API v2.1"}

@app.get("/api/health")
async def health_check():
    """Проверка состояния API (публичный)"""
    redis_stats = cache.get_stats()

    return {
        "status": "healthy",
        "timestamp": get_local_time().isoformat(),
        "timezone": str(LOCAL_TZ),
        "clouds_configured": list(vcd_clients.keys()),
        "redis": redis_stats
    }


# ================== ЗАЩИЩЕННЫЕ ЭНДПОИНТЫ ==================

@app.get("/api/dashboard", response_model=DashboardData)
async def get_dashboard_data(current_user: KeycloakUser = Depends(get_current_active_user)):
    """Получить все данные для дашборда (требует авторизации)"""

    # Пытаемся получить из кеша и валидировать как Pydantic-модель
    cache_key = "dashboard_data"
    cached_data = cache.get(cache_key)

    if cached_data:
        try:
            dashboard = DashboardData(**cached_data)
            logger.info(f"Dashboard data loaded from cache for user {current_user.username}")
            return dashboard
        except Exception as e:
            logger.warning(f"Invalid cached data, refreshing: {e}")

    try:
        all_clouds_stats = []
        all_allocations = []
        total_ips_count = 0
        used_ips_count = 0
        free_ips_count = 0

        # Собираем занятые IP для shared/overlapping пулов
        logger.info("Collecting used IPs for shared pools across all clouds...")
        loop = asyncio.get_event_loop()
        shared_pool_used_ips = await loop.run_in_executor(
            executor, get_globally_used_ips_for_shared_pools
        )

        # Собираем все аллокации для проверки конфликтов
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]

            try:
                cloud_allocations = client.get_all_used_ips(pools)
                all_allocations.extend(cloud_allocations)
            except Exception as e:
                logger.error(f"Error collecting allocations from {cloud_name}: {e}")

        # Проверяем конфликты (внутри облака + кросс-облачные)
        conflicts = check_ip_conflicts(all_allocations)
        if conflicts:
            logger.warning(f"Found {len(conflicts)} IP conflicts!")
            for ip, conflict_list in conflicts.items():
                for conflict in conflict_list:
                    logger.warning(
                        f"Conflict [{conflict.conflict_type}]: IP {ip} "
                        f"in clouds: {conflict.clouds}, pools: {conflict.pools}"
                    )

        # Обрабатываем каждое облако
        for cloud_name, client in vcd_clients.items():
            config = CLOUDS_CONFIG[cloud_name]
            pools = config["pools"]

            try:
                cloud_allocs = [a for a in all_allocations if a.cloud_name == cloud_name]

                cloud_pools = []
                cloud_total_ips = 0
                cloud_used_ips = 0
                cloud_free_ips = 0

                for pool_config in pools:
                    pool_allocations = [a for a in cloud_allocs if a.pool_name == pool_config["name"]]

                    network = pool_config["network"]
                    used_ips_set = set(a.ip_address for a in pool_allocations)

                    # Если пул shared/overlapping — берем глобальные used IPs
                    for group_key, ips in shared_pool_used_ips.items():
                        try:
                            pool_net = ipaddress.ip_network(network)
                            group_net = ipaddress.ip_network(group_key)
                            if pool_net.subnet_of(group_net) or network == group_key:
                                used_ips_set = ips
                                break
                        except ValueError:
                            continue

                    free_ips_list, total, used, free = IPCalculator.calculate_free_ips(
                        network, used_ips_set
                    )

                    # Конфликты для этого пула
                    pool_conflicts = []
                    for allocation in pool_allocations:
                        if allocation.ip_address in conflicts:
                            pool_conflicts.extend(conflicts[allocation.ip_address])

                    pool = IPPool(
                        name=pool_config["name"],
                        network=network,
                        cloud_name=cloud_name,
                        total_ips=total,
                        used_ips=used,
                        free_ips=free,
                        usage_percentage=round((used / total * 100) if total > 0 else 0, 2),
                        used_addresses=pool_allocations,
                        free_addresses=free_ips_list[:100],
                        has_overlaps=any(
                            network in nets for nets in shared_pool_used_ips.values()
                        ),
                        overlapping_clouds=pool_config.get("shared_with", []),
                        conflicts=pool_conflicts if pool_conflicts else None
                    )

                    cloud_pools.append(pool)
                    cloud_total_ips += total
                    cloud_used_ips += used
                    cloud_free_ips += free

                cloud_stats = CloudStats(
                    cloud_name=cloud_name,
                    total_pools=len(pools),
                    total_ips=cloud_total_ips,
                    used_ips=cloud_used_ips,
                    free_ips=cloud_free_ips,
                    usage_percentage=round(
                        (cloud_used_ips / cloud_total_ips * 100) if cloud_total_ips > 0 else 0, 2
                    ),
                    pools=cloud_pools
                )

                all_clouds_stats.append(cloud_stats)

                # Считаем общую статистику (уникальные сети)
                counted_networks = set()
                for pool_config in pools:
                    network = pool_config["network"]
                    if network not in counted_networks:
                        pool_stats = next(p for p in cloud_pools if p.name == pool_config["name"])
                        total_ips_count += pool_stats.total_ips
                        used_ips_count += pool_stats.used_ips
                        free_ips_count += pool_stats.free_ips
                        counted_networks.add(network)

            except Exception as e:
                logger.error(f"Error processing cloud {cloud_name}: {e}")
                continue

        dashboard = DashboardData(
            last_update=get_local_time(),
            total_clouds=len(all_clouds_stats),
            total_ips=total_ips_count,
            used_ips=used_ips_count,
            free_ips=free_ips_count,
            usage_percentage=round(
                (used_ips_count / total_ips_count * 100) if total_ips_count > 0 else 0, 2
            ),
            clouds=all_clouds_stats,
            all_allocations=all_allocations,
            conflicts=conflicts if conflicts else {}
        )

        # Кешируем JSON-сериализованные данные через Pydantic
        cache.set(cache_key, dashboard.dict(), ttl=300)
        logger.info(f"Dashboard data cached for user {current_user.username}")

        return dashboard

    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conflicts")
async def get_ip_conflicts(current_user: KeycloakUser = Depends(get_current_active_user)):
    """Получить список конфликтующих IP адресов (требует авторизации)"""
    try:
        all_allocations = []

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


@app.post("/api/cache/clear")
async def clear_cache(current_user: KeycloakUser = Depends(get_current_active_user)):
    """Очистить кеш (требует авторизации)"""
    try:
        cache.clear_pattern("dashboard_data*")
        logger.info(f"Cache cleared by user {current_user.username}")
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
