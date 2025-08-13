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
            # Исключаем первый (сеть) и последний (broadcast) адреса
            all_ips = [str(ip) for ip in net.hosts()]
            return all_ips
        except Exception as e:
            print(f"Error parsing network {network}: {e}")
            return []
    
    @staticmethod
    def calculate_free_ips(network: str, used_ips: Set[str]) -> Tuple[List[str], int, int, int]:
        """
        Рассчитать свободные IP адреса
        Возвращает: (free_ips, total_count, used_count, free_count)
        """
        all_ips = IPCalculator.get_all_ips_in_network(network)
        all_ips_set = set(all_ips)
        
        # Находим пересечение - какие из used_ips действительно в этой сети
        used_in_network = used_ips.intersection(all_ips_set)
        
        # Свободные IP - это разница между всеми и занятыми
        free_ips = sorted(list(all_ips_set - used_in_network))
        
        total_count = len(all_ips)
        used_count = len(used_in_network)
        free_count = len(free_ips)
        
        return free_ips, total_count, used_count, free_count
    
    @staticmethod
    def get_network_info(network: str) -> dict:
        """Получить информацию о сети"""
        try:
            net = ipaddress.ip_network(network, strict=False)
            return {
                "network": str(net),
                "netmask": str(net.netmask),
                "broadcast": str(net.broadcast_address),
                "first_host": str(list(net.hosts())[0]) if net.num_addresses > 2 else None,
                "last_host": str(list(net.hosts())[-1]) if net.num_addresses > 2 else None,
                "total_hosts": net.num_addresses - 2 if net.num_addresses > 2 else 0
            }
        except Exception as e:
            print(f"Error getting network info for {network}: {e}")
            return {}