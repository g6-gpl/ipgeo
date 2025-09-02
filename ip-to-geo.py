from playwright.async_api import async_playwright, Playwright
import asyncio
import json
from typing import Dict, List
import time

async def get_ipapi_data(ip_address: str) -> Dict:
    """Получение данных с ipapi.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=False)
        device = p.devices['Desktop Firefox']
        page = await browser.new_page(**device)
        
        try:
            await page.goto('https://ipapi.com/')
            await page.wait_for_selector('input[name="ip_to_lookup"]', timeout=10000)
            
            input_ip_to_lookup = page.locator('input[name="ip_to_lookup"]')
            await input_ip_to_lookup.clear()
            await input_ip_to_lookup.type(ip_address, delay=200)
            await input_ip_to_lookup.press('Enter')
            
            await page.wait_for_selector('[data-demo-fill="latitude"]', timeout=10000)
            await page.wait_for_timeout(2000)

            ip_data = {"source": "ipapi.com"}
            
            # Location данные
            ip_data['latitude'] = await page.locator('[data-demo-fill="latitude"]').text_content()
            ip_data['longitude'] = await page.locator('[data-demo-fill="longitude"]').text_content()
            ip_data['country'] = await page.locator('[data-demo-fill="country"]').text_content()
            ip_data['city'] = await page.locator('[data-demo-fill="city"]').text_content()
            ip_data['zip'] = await page.locator('[data-demo-fill="zip"]').text_content()
            
            # Connection данные
            await page.locator('[data-demo-switch="connection"]').click()
            await page.wait_for_selector('[data-demo-fill="ip"]', timeout=5000)
            ip_data['isp'] = await page.locator('[data-demo-fill="isp"]').text_content()
            ip_data['asn'] = await page.locator('[data-demo-fill="asn"]').text_content()

            return ip_data
            
        except Exception as e:
            return {"source": "ipapi.com", "error": str(e)}
        finally:
            await browser.close()

async def get_ipinfo_data(ip_address: str) -> Dict:
    """Получение данных с ipinfo.io"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(f'https://ipinfo.io/{ip_address}')
            await page.wait_for_selector('.card', timeout=10000)
            
            ip_data = {"source": "ipinfo.io"}
            
            # Извлекаем основные данные
            elements = await page.query_selector_all('.card .p-4 div')
            for element in elements:
                text = await element.text_content()
                if text and ':' in text:
                    key, value = text.split(':', 1)
                    ip_data[key.strip().lower()] = value.strip()
            
            return ip_data
            
        except Exception as e:
            return {"source": "ipinfo.io", "error": str(e)}
        finally:
            await browser.close()

async def get_dbip_data(ip_address: str) -> Dict:
    """Получение данных с db-ip.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(f'https://db-ip.com/{ip_address}')
            await page.wait_for_selector('.ip-info-table', timeout=10000)
            
            ip_data = {"source": "db-ip.com"}
            
            # Извлекаем данные из таблицы
            rows = await page.query_selector_all('.ip-info-table tr')
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    key = await cells[0].text_content()
                    value = await cells[1].text_content()
                    if key and value:
                        ip_data[key.strip().lower()] = value.strip()
            
            return ip_data
            
        except Exception as e:
            return {"source": "db-ip.com", "error": str(e)}
        finally:
            await browser.close()

async def get_whatismyipaddress_data(ip_address: str) -> Dict:
    """Получение данных с whatismyipaddress.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome', headless=False)
        page = await browser.new_page()
        
        try:
            await page.goto(f'https://whatismyipaddress.com/ip/{ip_address}')
            await page.wait_for_selector('#section_left_3rd', timeout=10000)
            
            ip_data = {"source": "whatismyipaddress.com"}
            
            # Извлекаем данные
            details = await page.query_selector_all('#section_left_3rd .card div')
            for detail in details:
                text = await detail.text_content()
                if text and ':' in text:
                    key, value = text.split(':', 1)
                    ip_data[key.strip().lower()] = value.strip()
            
            return ip_data
            
        except Exception as e:
            return {"source": "whatismyipaddress.com", "error": str(e)}
        finally:
            await browser.close()
            
async def get_combined_ip_data(ip_address: str) -> Dict:
    """Сбор данных из всех источников"""
    results = {
        "ip_address": ip_address,
        "timestamp": time.time(),
        "sources": {}
    }
    
    # Создаем задачи для всех источников
    tasks = [
        get_ipapi_data(ip_address),
        get_ipinfo_data(ip_address),
        get_dbip_data(ip_address),
        get_whatismyipaddress_data(ip_address)
    ]
    
    # Запускаем все задачи параллельно
    sources_data = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Обрабатываем результаты
    for data in sources_data:
        if isinstance(data, Exception):
            continue
        source_name = data.get("source", "unknown")
        results["sources"][source_name] = data
    
    return results

async def get_consistent_ip_data(ip_address: str) -> Dict:
    """Альтернатива: последовательный сбор данных"""
    results = {
        "ip_address": ip_address,
        "timestamp": time.time(),
        "sources": {}
    }
    
    # Последовательно получаем данные из каждого источника
    sources = [
        ("ipapi.com", get_ipapi_data),
        ("ipinfo.io", get_ipinfo_data),
        ("db-ip.com", get_dbip_data),
        ("whatismyipaddress.com", get_whatismyipaddress_data)
    ]
    
    for source_name, source_func in sources:
        try:
            data = await source_func(ip_address)
            results["sources"][source_name] = data
            print(f"Данные от {source_name} получены")
        except Exception as e:
            print(f"Ошибка от {source_name}: {e}")
            results["sources"][source_name] = {"error": str(e)}
    
    return results


def compare_sources(combined_data: Dict) -> Dict:
    """Сравнение данных из разных источников"""
    comparison = {}
    ip_address = combined_data["ip_address"]
    
    # Ключи для сравнения
    keys_to_compare = ["country", "city", "isp", "latitude", "longitude"]
    
    for key in keys_to_compare:
        comparison[key] = {}
        for source, data in combined_data["sources"].items():
            if key in data and data[key] not in [None, "", "N/A"]:
                comparison[key][source] = data[key]
    
    # Анализ согласованности
    consistency = {}
    for key, values in comparison.items():
        unique_values = set(values.values())
        consistency[key] = {
            "unique_values": len(unique_values),
            "values": values,
            "is_consistent": len(unique_values) == 1
        }
    
    return {
        "ip_address": ip_address,
        "comparison": comparison,
        "consistency": consistency,
        "summary": {
            "total_sources": len(combined_data["sources"]),
            "consistent_fields": sum(1 for c in consistency.values() if c["is_consistent"]),
            "total_fields": len(consistency)
        }
    }
    
    
async def main():
    ip_addresses = ["8.8.8.8", "1.1.1.1", "77.88.8.8"]
    
    for ip in ip_addresses:
        print(f"\n=== Сбор данных для {ip} ===")
        
        # Параллельный сбор данных
        combined_data = await get_combined_ip_data(ip)
        
        # Сравнение данных
        comparison = compare_sources(combined_data)
        
        # Сохраняем результаты
        filename = f"ip_data_{ip.replace('.', '_')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "combined_data": combined_data,
                "comparison": comparison
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Данные сохранены в {filename}")
        print(f"Согласованность данных: {comparison['summary']['consistent_fields']}/{comparison['summary']['total_fields']}")

# Запуск
if __name__ == "__main__":
    asyncio.run(main())