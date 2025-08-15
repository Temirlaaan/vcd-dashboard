#!/usr/bin/env python3
"""
Скрипт для тестирования поиска IP адреса во всех местах VCD
Использование: python test_ip_search.py 91.185.28.166
"""

import sys
import json
import requests
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()

def search_ip(ip_address, cloud=None):
    """Поиск IP через API"""
    base_url = "http://localhost:8000"
    
    # Проверяем, что сервер запущен
    try:
        health = requests.get(f"{base_url}/api/health")
        if health.status_code != 200:
            print("❌ Backend сервер не запущен! Запустите его командой: python app.py")
            return
    except:
        print("❌ Backend сервер не доступен! Запустите его командой: python app.py")
        return
    
    # Выполняем поиск
    print(f"🔍 Поиск IP адреса: {ip_address}")
    if cloud:
        print(f"   В облаке: {cloud}")
    print("-" * 60)
    
    url = f"{base_url}/api/search-ip/{ip_address}"
    if cloud:
        url += f"?cloud_name={cloud}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Найдено вхождений: {data['total_occurrences']}")
            print(f"   Облака проверены: {', '.join(data['clouds_searched'])}")
            print()
            
            # Выводим результаты по облакам
            for cloud_name, cloud_results in data['results'].items():
                print(f"☁️  {cloud_name.upper()}")
                print("=" * 40)
                
                for location_type, locations in cloud_results.items():
                    if locations:
                        print(f"\n📍 {location_type.replace('_', ' ').title()} ({len(locations)} найдено):")
                        for idx, loc in enumerate(locations, 1):
                            print(f"   {idx}. ", end="")
                            
                            if location_type == 'external_networks':
                                print(f"Network: {loc.get('network_name')}")
                                print(f"      Entity: {loc.get('entity_name')} ({loc.get('entity_type')})")
                                print(f"      Org: {loc.get('org_name')}")
                                print(f"      Deployed: {loc.get('deployed')}")
                                
                            elif location_type == 'nat_rules':
                                print(f"Edge: {loc.get('edge_name')}")
                                print(f"      Rule: {loc.get('rule_name')} ({loc.get('rule_type')})")
                                print(f"      External IPs: {', '.join(loc.get('external_ips', []))}")
                                print(f"      Internal IPs: {', '.join(loc.get('internal_ips', []))}")
                                print(f"      Enabled: {loc.get('enabled')}")
                                
                            elif location_type == 'firewall_rules':
                                print(f"Edge: {loc.get('edge_name')}")
                                print(f"      Rule: {loc.get('rule_name')}")
                                print(f"      Action: {loc.get('action')}")
                                print(f"      Enabled: {loc.get('enabled')}")
                                
                            elif location_type == 'edge_interfaces':
                                print(f"Edge: {loc.get('edge_name')}")
                                print(f"      Network: {loc.get('network_name')}")
                                print(f"      Primary IP: {loc.get('primary_ip')}")
                                print(f"      Gateway: {loc.get('gateway')}")
                                
                            elif location_type == 'load_balancers':
                                print(f"Edge: {loc.get('edge_name')}")
                                print(f"      Service: {loc.get('service_name')}")
                                print(f"      Virtual IP: {loc.get('virtual_ip')}")
                                print(f"      Enabled: {loc.get('enabled')}")
                                
                            elif location_type == 'ipsec_vpn':
                                print(f"Edge: {loc.get('edge_name')}")
                                print(f"      Tunnel: {loc.get('tunnel_name')}")
                                print(f"      Local IP: {loc.get('local_ip')}")
                                print(f"      Peer IP: {loc.get('peer_ip')}")
                                
                            elif location_type == 'ip_sets':
                                print(f"IP Set: {loc.get('ip_set_name')}")
                                print(f"      Org: {loc.get('org_name')}")
                                print(f"      Member: {loc.get('member')}")
                                
                            else:
                                # Общий формат для других типов
                                for key, value in loc.items():
                                    if key not in ['details', 'location']:
                                        print(f"      {key}: {value}")
                            print()
                
                print()
            
            # Сохраняем полный JSON для анализа
            filename = f"ip_search_{ip_address.replace('.', '_')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"💾 Полные результаты сохранены в: {filename}")
            
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")

def check_duplicates():
    """Проверка дублирующихся IP"""
    base_url = "http://localhost:8000"
    
    print("🔍 Проверка дублирующихся IP адресов...")
    print("-" * 60)
    
    try:
        response = requests.get(f"{base_url}/api/check-duplicate-ips")
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Статистика:")
            print(f"   Всего уникальных IP: {data['total_unique_ips']}")
            print(f"   Найдено дубликатов: {data['duplicate_count']}")
            print()
            
            if data['duplicates']:
                print("⚠️  Дублирующиеся IP адреса:")
                print("=" * 60)
                
                for dup in data['duplicates']:
                    print(f"\n🔴 IP: {dup['ip_address']}")
                    print(f"   Встречается: {dup['occurrence_count']} раз")
                    print(f"   Облака: {', '.join(dup['clouds'])}")
                    print(f"   Организации: {', '.join(dup['organizations'])}")
                    print("   Места использования:")
                    
                    for loc in dup['locations']:
                        print(f"      - {loc['cloud']}: {loc['org']} / {loc['pool']} ({loc['type']})")
                        if loc.get('entity'):
                            print(f"        Entity: {loc['entity']}")
                
                # Сохраняем результаты
                filename = "duplicate_ips_report.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"\n💾 Отчет сохранен в: {filename}")
            else:
                print("✅ Дублирующихся IP не найдено!")
                
        else:
            print(f"❌ Ошибка: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check-duplicates":
            check_duplicates()
        else:
            ip = sys.argv[1]
            cloud = sys.argv[2] if len(sys.argv) > 2 else None
            search_ip(ip, cloud)
    else:
        print("Использование:")
        print("  python test_ip_search.py <IP_ADDRESS> [CLOUD_NAME]")
        print("  python test_ip_search.py --check-duplicates")
        print()
        print("Примеры:")
        print("  python test_ip_search.py 91.185.28.166")
        print("  python test_ip_search.py 91.185.28.166 vcd02")
        print("  python test_ip_search.py --check-duplicates")