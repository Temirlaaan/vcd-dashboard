import ipaddress
import logging
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)


class IPCalculator:
    """Класс для расчета свободных IP адресов в пуле"""

    @staticmethod
    def get_all_ips_in_network(network: str) -> List[str]:
        """Получить все IP адреса в сети (исключая network и broadcast)."""
        try:
            net = ipaddress.ip_network(network, strict=False)
            return [str(ip) for ip in net.hosts()]
        except Exception as e:
            logger.error(f"Error parsing network {network}: {e}")
            return []

    @staticmethod
    def get_reserved_ips(network: str) -> List[str]:
        """Получить зарезервированные IP адреса (gateway = первый IP)."""
        try:
            net = ipaddress.ip_network(network, strict=False)
            hosts = list(net.hosts())

            if not hosts:
                return []

            # /31 — point-to-point, оба IP usable (RFC 3021)
            # /32 — единственный хост, нет gateway
            if net.prefixlen >= 31:
                return []

            # Для всех остальных сетей (включая /30) — резервируем gateway
            return [str(hosts[0])]

        except Exception as e:
            logger.error(f"Error getting reserved IPs for {network}: {e}")
            return []

    @staticmethod
    def calculate_free_ips(network: str, used_ips: Set[str]) -> Tuple[List[str], int, int, int]:
        """
        Рассчитать свободные IP адреса.
        Возвращает: (free_ips, total_count, used_count, free_count)
        """
        all_ips = IPCalculator.get_all_ips_in_network(network)
        reserved_ips = IPCalculator.get_reserved_ips(network)

        all_ips_set = set(all_ips)
        reserved_ips_set = set(reserved_ips)

        # Доступные IP = все хосты минус зарезервированные
        usable_ips = all_ips_set - reserved_ips_set

        # Используемые IP = пересечение used_ips с usable_ips (только IP из этой сети)
        used_in_network = used_ips.intersection(usable_ips)

        # Свободные IP
        free_ips = sorted(list(usable_ips - used_in_network))

        total_count = len(usable_ips)
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
                "total_hosts": len(hosts),
                "usable_hosts": len(hosts) - len(reserved),
                "reserved_ips": reserved
            }
        except Exception as e:
            logger.error(f"Error getting network info for {network}: {e}")
            return {}
