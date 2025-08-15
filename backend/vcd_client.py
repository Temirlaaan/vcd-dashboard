import os
import time
import requests
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse
import urllib3
from cachetools import TTLCache
from threading import Lock
import logging
from datetime import datetime
from models import IPAllocation

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class VCDClient:
    """Клиент для работы с VMware vCloud Director API"""
    
    def __init__(self, base_url: str, api_version: str, api_token: str, cloud_name: str):
        self.base_url = base_url
        self.api_version = api_version
        self.api_token = api_token
        self.cloud_name = cloud_name
        self.token_cache = {'token': None, 'expires_at': 0}
        self.token_lock = Lock()
        
        # Настройка сессии с увеличенным лимитом заголовков
        self.session = requests.Session()
        self.session.verify = False
        
        # Увеличиваем лимит заголовков для обработки больших ответов
        import http.client
        http.client._MAXHEADERS = 1000
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Кэш для данных
        self.cache = TTLCache(maxsize=100, ttl=300)  # 5 минут кэш
    
    def get_bearer_token(self) -> str:
        """Получить или обновить Bearer токен"""
        with self.token_lock:
            now = time.time()
            if self.token_cache['token'] is None or now >= self.token_cache['expires_at'] - 300:
                parts = urlparse(self.base_url)
                token_url = f"{parts.scheme}://{parts.netloc}/oauth/provider/token"
                
                try:
                    r = self.session.post(
                        token_url,
                        params={'grant_type': 'refresh_token', 'refresh_token': self.api_token},
                        headers={'Accept': 'application/json'},
                        timeout=(5, 10)
                    )
                    r.raise_for_status()
                    data = r.json()
                    self.token_cache['token'] = data['access_token']
                    self.token_cache['expires_at'] = now + int(data.get('expires_in', 3600))
                    logger.info(f"Got new bearer token for {self.cloud_name}")
                except Exception as e:
                    logger.error(f"Failed to get bearer token for {self.cloud_name}: {e}")
                    raise
            
            return self.token_cache['token']
    
    def get_headers(self) -> Dict:
        """Получить заголовки для запросов"""
        return {
            'Accept': f'application/json;version={self.api_version}',
            'Authorization': f'Bearer {self.get_bearer_token()}'
        }
    
    def fetch_ip_space_allocations(self, ip_space_id: str, pool_name: str) -> List[IPAllocation]:
        """Получить занятые IP из IP Space (для vcd v38)"""
        cache_key = f"ipspace_{ip_space_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        allocations = []
        
        # Начинаем с первой страницы
        # Используем pageSize=128 для всех пулов для максимальной эффективности
        url = f"{self.base_url}/cloudapi/1.0.0/ipSpaces/{ip_space_id}/allocations?filter=(type==FLOATING_IP)&pageSize=128&page=1"
        
        logger.info(f"Fetching allocations for {pool_name} ({ip_space_id})")
        
        try:
            page_count = 0
            total_fetched = 0
            
            while url:
                page_count += 1
                logger.debug(f"Fetching page {page_count} for {pool_name}")
                
                try:
                    r = self.session.get(url, headers=self.get_headers(), timeout=(10, 30))
                    
                    if r.status_code == 200:
                        data = r.json()
                        values = data.get('values', [])
                        
                        if not values:
                            logger.debug(f"No more data on page {page_count} for {pool_name}")
                            break
                        
                        # Обрабатываем все записи на странице
                        page_items = 0
                        for alloc in values:
                            if alloc.get('type') == 'FLOATING_IP':
                                allocations.append(IPAllocation(
                                    ip_address=alloc.get('value', 'N/A'),
                                    org_name=alloc.get('orgRef', {}).get('name', 'unknown'),
                                    org_id=alloc.get('orgRef', {}).get('id'),
                                    entity_name=alloc.get('usedByRef', {}).get('name') if alloc.get('usedByRef') else None,
                                    allocation_type='FLOATING_IP',
                                    cloud_name=self.cloud_name,
                                    pool_name=pool_name,
                                    allocation_date=datetime.fromisoformat(alloc['allocationDate'].replace('+0500', '+05:00')) if alloc.get('allocationDate') else None
                                ))
                                page_items += 1
                        
                        total_fetched += page_items
                        logger.debug(f"Page {page_count}: fetched {page_items} items, total so far: {total_fetched}")
                        
                        # Проверяем наличие следующей страницы
                        next_link = data.get('nextPageLink')
                        if next_link:
                            url = next_link
                            logger.debug(f"Next page link found: {next_link}")
                        else:
                            # Проверяем, есть ли еще данные через результаты страницы
                            result_total = data.get('resultTotal', 0)
                            page_size = data.get('pageSize', 128)
                            current_page = data.get('page', page_count)
                            
                            if result_total > 0 and (current_page * page_size) < result_total:
                                # Есть еще страницы, формируем URL для следующей
                                next_page = current_page + 1
                                url = f"{self.base_url}/cloudapi/1.0.0/ipSpaces/{ip_space_id}/allocations?filter=(type==FLOATING_IP)&pageSize={page_size}&page={next_page}"
                                logger.debug(f"Constructed next page URL: page {next_page}")
                            else:
                                logger.debug(f"No more pages. Result total: {result_total}, fetched: {total_fetched}")
                                url = None
                    else:
                        logger.warning(f"Error response for {pool_name}: {r.status_code}")
                        if r.text:
                            logger.debug(f"Response text: {r.text[:500]}")
                        break
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout on page {page_count} for {pool_name}, retrying with smaller page size")
                    # Пробуем с меньшим размером страницы
                    if 'pageSize=128' in url:
                        url = url.replace('pageSize=128', 'pageSize=50')
                    elif 'pageSize=50' in url:
                        url = url.replace('pageSize=50', 'pageSize=25')
                    else:
                        logger.error(f"Failed after reducing page size for {pool_name}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error on page {page_count} for {pool_name}: {e}")
                    
                    # Особая обработка для ошибки с заголовками
                    if "got more than 100 headers" in str(e).lower():
                        logger.info(f"Headers limit error for {pool_name}, reducing page size")
                        if 'pageSize=128' in url:
                            url = url.replace('pageSize=128', 'pageSize=25')
                        elif 'pageSize=50' in url:
                            url = url.replace('pageSize=50', 'pageSize=10')
                        else:
                            break
                    else:
                        break
                
                # Защита от бесконечного цикла
                if page_count > 100:
                    logger.warning(f"Reached maximum page limit (100) for {pool_name}")
                    break
                    
        except Exception as e:
            logger.error(f"Critical error fetching IP Space {pool_name}: {e}")
        
        logger.info(f"{self.cloud_name}: Found {len(allocations)} IPs in {pool_name} after {page_count} pages")
        self.cache[cache_key] = allocations
        return allocations
    
    def fetch_external_network_used_ips(self, network_id: str, pool_name: str) -> List[IPAllocation]:
        """Получить занятые IP из External Network (для vcd01/vcd02 v37)"""
        cache_key = f"extnet_{network_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        allocations = []
        
        logger.info(f"Fetching used IPs for {pool_name} ({network_id})")
        
        try:
            page = 1
            total_fetched = 0
            
            while True:
                url = f"{self.base_url}/cloudapi/1.0.0/externalNetworks/{network_id}/usedIpAddresses?pageSize=128&page={page}"
                logger.debug(f"Fetching page {page} for {pool_name}")
                
                r = self.session.get(url, headers=self.get_headers(), timeout=(5, 30))
                
                if r.status_code == 200:
                    data = r.json()
                    
                    # Данные могут быть как list так и dict с values
                    if isinstance(data, dict):
                        items = data.get('values', [])
                        result_total = data.get('resultTotal', 0)
                    else:
                        items = data if isinstance(data, list) else []
                        result_total = len(items)
                    
                    if not items:
                        logger.debug(f"No more data on page {page} for {pool_name}")
                        break
                    
                    page_items = 0
                    for item in items:
                        # Обрабатываем разные типы allocation
                        allocation_type = item.get('allocationType', 'UNKNOWN')
                        entity_name = None
                        
                        # Определяем entity_name в зависимости от типа
                        if allocation_type == 'VM_ALLOCATED':
                            entity_name = item.get('entityName') or item.get('vappName')
                        elif allocation_type == 'EDGE':
                            entity_name = item.get('entityName')
                        elif allocation_type == 'NAT':
                            entity_name = f"NAT on {item.get('entityName', 'Unknown')}"
                        else:
                            entity_name = item.get('entityName')
                        
                        allocations.append(IPAllocation(
                            ip_address=item.get('ipAddress', 'N/A'),
                            org_name=item.get('orgRef', {}).get('name', 'unknown'),
                            org_id=item.get('orgRef', {}).get('id'),
                            entity_name=entity_name,
                            allocation_type=allocation_type,
                            cloud_name=self.cloud_name,
                            pool_name=pool_name,
                            allocation_date=None,  # В v37 нет даты аллокации
                            vapp_name=item.get('vappName') or item.get('vAppName'),
                            deployed=item.get('deployed')
                        ))
                        page_items += 1
                    
                    total_fetched += page_items
                    logger.debug(f"Page {page}: fetched {page_items} items, total so far: {total_fetched}")
                    
                    # Проверяем, есть ли следующая страница
                    # В API v37 если вернулось меньше pageSize элементов, значит это последняя страница
                    if len(items) < 128:
                        logger.debug(f"Last page reached (got {len(items)} items, less than 128)")
                        break
                    
                    # Также проверяем resultTotal если он есть
                    if isinstance(data, dict) and result_total > 0:
                        if total_fetched >= result_total:
                            logger.debug(f"All items fetched: {total_fetched}/{result_total}")
                            break
                    
                    page += 1
                    
                    # Защита от бесконечного цикла
                    if page > 100:
                        logger.warning(f"Reached maximum page limit (100) for {pool_name}")
                        break
                        
                else:
                    logger.warning(f"Error fetching page {page} for {pool_name}: {r.status_code}")
                    if r.text:
                        logger.debug(f"Response: {r.text[:500]}")
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching External Network {pool_name}: {e}")
        
        # Подсчитываем типы аллокаций для логирования
        type_counts = {}
        for alloc in allocations:
            type_counts[alloc.allocation_type] = type_counts.get(alloc.allocation_type, 0) + 1
        
        logger.info(f"{self.cloud_name}: Found {len(allocations)} total IPs in {pool_name}")
        if type_counts:
            logger.info(f"  Breakdown: {', '.join([f'{k}: {v}' for k, v in type_counts.items()])}")
        
        self.cache[cache_key] = allocations
        return allocations
    
    def get_all_used_ips(self, pools: List[Dict]) -> List[IPAllocation]:
        """Получить все занятые IP для списка пулов"""
        all_allocations = []
        
        for pool in pools:
            pool_id = pool['id']
            pool_name = pool['name']
            pool_type = pool['type']
            
            logger.info(f"Processing pool: {pool_name} (type: {pool_type})")
            
            if pool_type == 'ipSpace':
                allocations = self.fetch_ip_space_allocations(pool_id, pool_name)
            else:  # externalNetwork
                allocations = self.fetch_external_network_used_ips(pool_id, pool_name)
            
            all_allocations.extend(allocations)
        
        logger.info(f"{self.cloud_name}: Total {len(all_allocations)} IPs across all pools")
        return all_allocations