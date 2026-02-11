# backend/clouds_config.py
"""
Конфигурация облаков и IP-пулов.
Вынесена из app.py для удобства поддержки.
"""
import os

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
                "shared_with": []
            },
            {
                "id": "urn:vcloud:ipSpace:8d23d064-2de6-41a3-9d23-8555599e9d10",
                "name": "87.255.215.0/24",
                "network": "87.255.215.0/24",
                "type": "ipSpace",
                "shared_with": ["vcd02"]
            },
            {
                "id": "urn:vcloud:ipSpace:7315f883-a0e5-4c9c-860b-528c7830813a",
                "name": "91.185.21.224/27",
                "network": "91.185.21.224/27",
                "type": "ipSpace",
                "shared_with": ["vcd02"]
            },
            {
                "id": "urn:vcloud:ipSpace:5f6a1f88-094d-4877-bb9d-ee01d79da29d",
                "name": "IPS-37.17.178.208/28-internet",
                "network": "37.17.178.208/28",
                "type": "ipSpace",
                "shared_with": []
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
                "shared_with": []
            },
            {
                "id": "urn:vcloud:network:88bfab4e-4dc7-4605-b0f9-d8648f785812",
                "name": "ExtNet-87.255.215.0m24-INTERNET",
                "network": "87.255.215.0/24",
                "type": "externalNetwork",
                "shared_with": ["vcd"]
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
                "shared_with": ["vcd"]
            }
        ]
    }
}
