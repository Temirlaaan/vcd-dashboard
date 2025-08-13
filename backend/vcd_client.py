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
        url = f"{self.base_url}/cloudapi/1.0.0/ipSpaces/{ip_space_id}/allocations?filter=(type==FLOATING_IP)&pageSize=128"
        
        try:
            # Для проблемных пулов уменьшаем размер страницы
            if "8d23d064-2de6-41a3-9d23-8555599e9d10" in ip_space_id:  # 87.255.215.0/24
                url = f"{self.base_url}/cloudapi/1.0.0/ipSpaces/{ip_space_id}/allocations?filter=(type==FLOATING_IP)&pageSize=50"
                logger.info(f"Using reduced page size for {pool_name}")
            
            while url:
                r = self.session.get(url, headers=self.get_headers(), timeout=(5, 30))
                if r.status_code == 200:
                    data = r.json()
                    
                    for alloc in data.get('values', []):
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
                    
                    url = data.get('nextPageLink')
                    # Для проблемных пулов корректируем pageSize в следующих ссылках
                    if url and "8d23d064-2de6-41a3-9d23-8555599e9d10" in url and "pageSize=128" in url:
                        url = url.replace("pageSize=128", "pageSize=50")
                else:
                    logger.warning(f"Error fetching IP Space allocations: {r.status_code}")
                    break
        except Exception as e:
            logger.error(f"Error fetching IP Space {ip_space_id}: {e}")
            # Пробуем еще раз с меньшим размером страницы
            if "got more than 100 headers" in str(e):
                logger.info(f"Retrying with smaller page size for {pool_name}")
                try:
                    url = f"{self.base_url}/cloudapi/1.0.0/ipSpaces/{ip_space_id}/allocations?filter=(type==FLOATING_IP)&pageSize=25"
                    r = self.session.get(url, headers=self.get_headers(), timeout=(5, 30))
                    if r.status_code == 200:
                        data = r.json()
                        for alloc in data.get('values', []):
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
                except Exception as retry_error:
                    logger.error(f"Retry failed for {pool_name}: {retry_error}")
        
        self.cache[cache_key] = allocations
        return allocations
    
    def fetch_external_network_used_ips(self, network_id: str, pool_name: str) -> List[IPAllocation]:
        """Получить занятые IP из External Network (для vcd01/vcd02 v37)"""
        cache_key = f"extnet_{network_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        allocations = []
        url = f"{self.base_url}/cloudapi/1.0.0/externalNetworks/{network_id}/usedIpAddresses"
        
        try:
            r = self.session.get(url, headers=self.get_headers(), timeout=(5, 15))
            if r.status_code == 200:
                data = r.json()
                
                # В API v37 данные могут быть прямо в ответе или в values
                items = data if isinstance(data, list) else data.get('values', [])
                
                for item in items:
                    allocations.append(IPAllocation(
                        ip_address=item.get('ipAddress', 'N/A'),
                        org_name=item.get('orgRef', {}).get('name', 'unknown'),
                        org_id=item.get('orgRef', {}).get('id'),
                        entity_name=item.get('entityName'),
                        allocation_type=item.get('allocationType', 'EDGE'),
                        cloud_name=self.cloud_name,
                        pool_name=pool_name,
                        allocation_date=None  # В v37 нет даты аллокации
                    ))
            else:
                logger.warning(f"Error fetching External Network IPs: {r.status_code}")
        except Exception as e:
            logger.error(f"Error fetching External Network {network_id}: {e}")
        
        self.cache[cache_key] = allocations
        return allocations
    
    def get_all_used_ips(self, pools: List[Dict]) -> List[IPAllocation]:
        """Получить все занятые IP для списка пулов"""
        all_allocations = []
        
        for pool in pools:
            pool_id = pool['id']
            pool_name = pool['name']
            pool_type = pool['type']
            
            if pool_type == 'ipSpace':
                allocations = self.fetch_ip_space_allocations(pool_id, pool_name)
            else:  # externalNetwork
                allocations = self.fetch_external_network_used_ips(pool_id, pool_name)
            
            all_allocations.extend(allocations)
            logger.info(f"{self.cloud_name}: Found {len(allocations)} IPs in {pool_name}")
        
        return all_allocations