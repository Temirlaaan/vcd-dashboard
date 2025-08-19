import ipaddress
from typing import List, Set, Tuple

class IPCalculator:
    """Класс для расчета свободных IP адресов в пуле"""
    
    @staticmethod
    def get_all_ips_in_network(network: str) -> List[str]:
        """
        Получить все IP адреса в сети
        network: строка вида "87.255.215.0/24"
        """
        try:
            net = ipaddress.ip_network(network, strict=False)
            # Получаем все хосты (исключая network и broadcast адреса)
            all_ips = [str(ip) for ip in net.hosts()]
            return all_ips
        except Exception as e:
            print(f"Error parsing network {network}: {e}")
            return []
    
    @staticmethod
    def get_reserved_ips(network: str) -> List[str]:
        """
        Получить зарезервированные IP адреса (только gateway)
        """
        try:
            net = ipaddress.ip_network(network, strict=False)
            hosts = list(net.hosts())
            
            if not hosts:
                return []
            
            # Резервируем только первый IP (gateway)
            # Для /30 и меньше сетей может быть особая логика
            if net.prefixlen >= 30:
                # В /30 только 2 usable IP, оба могут использоваться для point-to-point
                # В /31 и /32 - специальные случаи
                return []
            
            # Возвращаем только gateway (первый IP)
            return [str(hosts[0])]
            
        except Exception as e:
            print(f"Error getting reserved IPs for {network}: {e}")
            return []
    
    @staticmethod
    def calculate_free_ips(network: str, used_ips: Set[str]) -> Tuple[List[str], int, int, int]:
        """
        Рассчитать свободные IP адреса
        Возвращает: (free_ips, total_count, used_count, free_count)
        """
        all_ips = IPCalculator.get_all_ips_in_network(network)
        reserved_ips = IPCalculator.get_reserved_ips(network)
        
        # Преобразуем в множества для быстрых операций
        all_ips_set = set(all_ips)
        reserved_ips_set = set(reserved_ips)
        
        # Доступные для использования IP = все IP минус зарезервированные
        usable_ips = all_ips_set - reserved_ips_set
        
        # Находим пересечение used_ips с usable_ips (исключаем IP не из этой сети)
        used_in_network = used_ips.intersection(usable_ips)
        
        # Свободные IP = доступные минус занятые
        free_ips = sorted(list(usable_ips - used_in_network))
        
        # Подсчет
        total_count = len(usable_ips)  # Общее количество доступных IP
        used_count = len(used_in_network)
        free_count = len(free_ips)
        
        return free_ips, total_count, used_count, free_count
    
    @staticmethod
    def get_network_info(network: str) -> dict:
        """Получить информацию о сети"""
        try:
            net = ipaddress.ip_network(network, strict=False)
            hosts = list(net.hosts())
            reserved = IPCalculator.get_reserved_ips(network)
            
            return {
                "network": str(net),
                "netmask": str(net.netmask),
                "broadcast": str(net.broadcast_address),
                "gateway": str(hosts[0]) if hosts else None,
                "first_usable": str(hosts[1]) if len(hosts) > 1 else (str(hosts[0]) if hosts else None),
                "last_usable": str(hosts[-1]) if hosts else None,
                "total_addresses": net.num_addresses,
                "total_hosts": net.num_addresses - 2 if net.num_addresses > 2 else net.num_addresses,
                "usable_hosts": len(hosts) - len(reserved),
                "reserved_ips": reserved
            }
        except Exception as e:
            print(f"Error getting network info for {network}: {e}")
            return {}