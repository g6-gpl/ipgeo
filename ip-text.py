from playwright.async_api import async_playwright, Playwright
import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class UnifiedIPData:
    """Унифицированная структура данных IP"""

    ip_address: str
    source: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    isp: Optional[str] = None
    asn: Optional[str] = None
    organization: Optional[str] = None
    asn_organization: Optional[str] = None
    hostname: Optional[str] = None
    ip_range: Optional[str] = None
    company: Optional[str] = None
    hosted_domains_count: Optional[int] = None
    is_private: Optional[bool] = None
    is_anycast: Optional[bool] = None
    asn_type: Optional[str] = None
    district: Optional[str] = None
    abuse_email: Optional[str] = None
    timezone: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            k: v
            for k, v in self.__dict__.items()
            if v is not None or k in ["ip_address", "source"]
        }

    def to_json(self) -> str:
        """Преобразование в JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

async def parse_ip_data(page) -> Dict[str, Any]:
    """Парсинг данных с IP-информацией"""
    data = {}
    
    try:
        # Ждем загрузки основных таблиц
        await page.wait_for_selector('.menu.results.shadow table', timeout=10000)
        
        # Парсим первую таблицу (сетевые данные)
        network_data = await parse_network_table(page)
        data.update(network_data)
        
        # Парсим вторую таблицу (угрозы)
        threat_data = await parse_threat_table(page)
        data.update(threat_data)
        
        # Парсим третью таблицу (географические данные)
        geo_data = await parse_geo_table(page)
        data.update(geo_data)
        
        # Парсим координаты из iframe
        coordinates = await parse_coordinates_from_iframe(page)
        if coordinates:
            data['latitude'], data['longitude'] = coordinates
        
    except Exception as e:
        print(f"Ошибка при парсинге: {e}")
    
    return data

async def parse_network_table(page) -> Dict[str, Any]:
    """Парсинг первой таблицы с сетевыми данными"""
    data = {}
    
    try:
        # Получаем все строки первой таблицы
        rows = await page.query_selector_all('.menu.results.shadow:first-child table tr')
        
        for row in rows:
            try:
                th = await row.query_selector('th')
                td = await row.query_selector('td')
                
                if th and td:
                    key = await th.text_content()
                    value = await td.text_content()
                    
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    # Обрабатываем специальные случаи
                    if key == 'asn':
                        # Извлекаем номер ASN и название
                        asn_parts = value.split(' - ')
                        if len(asn_parts) > 1:
                            data['asn_number'] = asn_parts[0].strip()
                            data['asn_organization'] = asn_parts[1].strip()
                        else:
                            data['asn'] = value
                    elif key == 'hostname':
                        data['hostname'] = value
                    elif key == 'isp':
                        data['isp'] = value
                    elif key == 'connection':
                        data['connection_type'] = value
                    elif key == 'organization':
                        data['organization'] = value
                    elif key == 'address_type':
                        data['ip_version'] = value.replace('&nbsp;', ' ').strip()
                        
            except Exception as e:
                print(f"Ошибка парсинга строки сети: {e}")
                continue
                
    except Exception as e:
        print(f"Ошибка парсинга сетевой таблицы: {e}")
    
    return data

async def parse_threat_table(page) -> Dict[str, Any]:
    """Парсинг таблицы с информацией об угрозах"""
    data = {}
    
    try:
        # Уровень угрозы
        threat_level_elem = await page.query_selector('.label.badge-success')
        if threat_level_elem:
            data['threat_level'] = await threat_level_elem.text_content()
        
        # Проверяем статусы угроз
        threat_selectors = {
            'is_crawler': 'td:nth-child(1) .fa-times.text-success',
            'is_proxy': 'td:nth-child(2) .fa-times.text-success',
            'is_attack_source': 'td:nth-child(3) .fa-times.text-success'
        }
        
        for key, selector in threat_selectors.items():
            element = await page.query_selector(selector)
            data[key] = element is not None  # True если элемент найден (значит "нет" угрозы)
            
    except Exception as e:
        print(f"Ошибка парсинга таблицы угроз: {e}")
    
    return data

async def parse_geo_table(page) -> Dict[str, Any]:
    """Парсинг географической таблицы"""
    data = {}
    
    try:
        # Получаем все строки географической таблицы (вторая таблица с shadow)
        geo_tables = await page.query_selector_all('.menu.results.shadow')
        if len(geo_tables) >= 3:
            geo_table = geo_tables[2]  # Третья таблица
            rows = await geo_table.query_selector_all('table tr')
            
            for row in rows:
                try:
                    th = await row.query_selector('th')
                    td = await row.query_selector('td')
                    
                    if th and td:
                        key = await th.text_content()
                        value = await td.text_content()
                        
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        
                        # Обрабатываем специальные случаи
                        if key == 'country':
                            # Извлекаем только название страны (без флага)
                            country_parts = value.split('\n')
                            data['country'] = country_parts[0].strip()
                        elif key == 'state_/_region':
                            # Берем только английское название
                            state_parts = value.split('\n')
                            data['region'] = state_parts[0].strip()
                        elif key == 'district_/_county':
                            county_parts = value.split('\n')
                            data['county'] = county_parts[0].strip()
                        elif key == 'city':
                            city_parts = value.split('\n')
                            data['city'] = city_parts[0].strip()
                        elif key == 'zip_/_postal_code':
                            data['postal_code'] = value
                        elif key == 'coordinates':
                            data['coordinates'] = value
                        elif key == 'timezone':
                            data['timezone'] = value.split('(')[0].strip()
                        elif key == 'local_time':
                            data['local_time'] = value
                        elif key == 'languages':
                            data['languages'] = value
                        elif key == 'currency':
                            data['currency'] = value
                        elif key == 'weather_station':
                            data['weather_station'] = value
                            
                except Exception as e:
                    print(f"Ошибка парсинга строки гео: {e}")
                    continue
                    
    except Exception as e:
        print(f"Ошибка парсинга географической таблицы: {e}")
    
    return data

async def parse_coordinates_from_iframe(page) -> Optional[tuple]:
    """Парсинг координат из iframe"""
    try:
        iframe = await page.query_selector('iframe[data-src*="openstreetmap"]')
        if iframe:
            src = await iframe.get_attribute('data-src') or await iframe.get_attribute('src')
            if src and 'marker=' in src:
                # Извлекаем координаты из URL
                marker_part = src.split('marker=')[1]
                coords = marker_part.split('&')[0].split(',')
                if len(coords) == 2:
                    return float(coords[0]), float(coords[1])
    except Exception as e:
        print(f"Ошибка парсинга координат из iframe: {e}")
    
    return None

def transform_ipapi_data(ipapi_data: Dict[str, Any], ip_address: str) -> UnifiedIPData:
    """Преобразование данных из ipapi.com"""
    if "error" in ipapi_data:
        return UnifiedIPData(
            ip_address=ip_address, source="ipapi.com", error=ipapi_data["error"]
        )

    # Преобразуем координаты в числа
    lat = None
    lon = None
    try:
        if "latitude" in ipapi_data and ipapi_data["latitude"]:
            lat = float(ipapi_data["latitude"])
        if "longitude" in ipapi_data and ipapi_data["longitude"]:
            lon = float(ipapi_data["longitude"])
    except (ValueError, TypeError):
        pass

    return UnifiedIPData(
        ip_address=ip_address,
        source="ipapi.com",
        country=ipapi_data.get("country"),
        city=ipapi_data.get("city"),
        zip_code=ipapi_data.get("zip"),
        latitude=lat,
        longitude=lon,
        isp=ipapi_data.get("isp"),
        asn=ipapi_data.get("asn"),
    )


def transform_ipinfo_data(
    ipinfo_data: Dict[str, Any], ip_address: str
) -> UnifiedIPData:
    """Преобразование данных из ipinfo.io"""
    if "error" in ipinfo_data:
        return UnifiedIPData(
            ip_address=ip_address, source="ipinfo.io", error=ipinfo_data["error"]
        )
    print(ipinfo_data)
    # Преобразуем количество доменов в число

    lon = None
    lat = None

    domains_count = None
    try:
        if (
            "hosted_domains_count" in ipinfo_data
            and ipinfo_data["hosted_domains_count"]
        ):
            domains_count = int(ipinfo_data["hosted_domains_count"])
    except (ValueError, TypeError):
        pass

    try:
        if "coordinates" in ipinfo_data and ipinfo_data["coordinates"]:
            coords = ipinfo_data["coordinates"].split(",")
            if len(coords) >= 2:
                lat = float(coords[0].strip())
                lon = float(coords[1].strip())
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Ошибка обработки координат: {e}")
        pass

    return UnifiedIPData(
        ip_address=ip_address,
        source="ipinfo.io",
        asn=ipinfo_data.get("asn_number"),
        asn_organization=ipinfo_data.get("asn_organization"),
        hostname=ipinfo_data.get("hostname"),
        ip_range=ipinfo_data.get("ip_range"),
        company=ipinfo_data.get("company"),
        hosted_domains_count=domains_count,
        is_private=ipinfo_data.get("is_private"),
        is_anycast=ipinfo_data.get("is_anycast"),
        asn_type=ipinfo_data.get("asn_type"),
        abuse_email=ipinfo_data.get("abuse_email"),
        latitude=lat,
        longitude=lon,
    )


def transform_db_ip_data(
    ipinfo_data: Dict[str, Any], ip_address: str
) -> UnifiedIPData:
    """Преобразование данных из ipinfo.io"""
    if "error" in ipinfo_data:
        return UnifiedIPData(
            ip_address=ip_address, source="db-ip.com", error=ipinfo_data["error"]
        )
    print(ipinfo_data)
    # Преобразуем количество доменов в число

    lon = None
    lat = None

    domains_count = None
    try:
        if (
            "hosted_domains_count" in ipinfo_data
            and ipinfo_data["hosted_domains_count"]
        ):
            domains_count = int(ipinfo_data["hosted_domains_count"])
    except (ValueError, TypeError):
        pass

    try:
        if "coordinates" in ipinfo_data and ipinfo_data["coordinates"]:
            coords = ipinfo_data["coordinates"].split(",")
            if len(coords) >= 2:
                lat = float(coords[0].strip())
                lon = float(coords[1].strip())
    except (ValueError, TypeError, AttributeError) as e:
        print(f"Ошибка обработки координат: {e}")
        pass

    return UnifiedIPData(
        ip_address=ip_address,
        source="db-ip.com",
        asn=ipinfo_data.get("asn_number"),
        asn_organization=ipinfo_data.get("asn_organization"),
        hostname=ipinfo_data.get("hostname"),
        ip_range=ipinfo_data.get("ip_range"),
        organization=ipinfo_data.get("organization"),
        country = ipinfo_data.get("country"),
        region = ipinfo_data.get("region"),
        company=ipinfo_data.get("isp"),
        city=ipinfo_data.get("city"),
        isp=ipinfo_data.get("isp"),
        zip_code = ipinfo_data.get("zip"),
        district=ipinfo_data.get("country"),
        hosted_domains_count=domains_count,
        is_private=ipinfo_data.get("is_private"),
        is_anycast=ipinfo_data.get("is_anycast"),
        asn_type=ipinfo_data.get("asn_type"),
        abuse_email=ipinfo_data.get("abuse_email"),
        latitude=lat,
        longitude=lon,
    )


def merge_ip_data(
    ipapi_data: UnifiedIPData, ipinfo_data: UnifiedIPData, dbip_data: UnifiedIPData
) -> UnifiedIPData:
    """Объединение данных из трех источников"""
    merged = UnifiedIPData(
        ip_address=ipapi_data.ip_address or ipinfo_data.ip_address or dbip_data.ip_address,
        source="combined",
        error=ipapi_data.error or ipinfo_data.error or dbip_data.error,
    )

    # Все поля через or с тремя источниками
    merged.country = ipapi_data.country or ipinfo_data.country or dbip_data.country
    merged.country_code = ipapi_data.country_code or ipinfo_data.country_code or dbip_data.country_code
    merged.region = ipapi_data.region or ipinfo_data.region or dbip_data.region
    merged.city = ipapi_data.city or ipinfo_data.city or dbip_data.city
    merged.zip_code = ipapi_data.zip_code or ipinfo_data.zip_code or dbip_data.zip_code
    merged.latitude = ipapi_data.latitude or ipinfo_data.latitude or dbip_data.latitude
    merged.longitude = ipapi_data.longitude or ipinfo_data.longitude or dbip_data.longitude
    merged.isp = ipapi_data.isp or ipinfo_data.isp or dbip_data.isp
    merged.asn = ipapi_data.asn or ipinfo_data.asn or dbip_data.asn
    merged.asn_organization = ipapi_data.asn_organization or ipinfo_data.asn_organization or dbip_data.asn_organization
    merged.hostname = ipapi_data.hostname or ipinfo_data.hostname or dbip_data.hostname
    merged.ip_range = ipapi_data.ip_range or ipinfo_data.ip_range or dbip_data.ip_range
    merged.company = ipapi_data.company or ipinfo_data.company or dbip_data.company
    merged.hosted_domains_count = ipapi_data.hosted_domains_count or ipinfo_data.hosted_domains_count or dbip_data.hosted_domains_count
    merged.is_private = ipinfo_data.is_private if ipinfo_data.is_private is not None else dbip_data.is_private if dbip_data.is_private is not None else ipapi_data.is_private
    merged.is_anycast = ipinfo_data.is_anycast if ipinfo_data.is_anycast is not None else dbip_data.is_anycast if dbip_data.is_anycast is not None else ipapi_data.is_anycast
    merged.asn_type = ipapi_data.asn_type or ipinfo_data.asn_type or dbip_data.asn_type
    merged.abuse_email = ipapi_data.abuse_email or ipinfo_data.abuse_email or dbip_data.abuse_email
    merged.timezone = ipapi_data.timezone or ipinfo_data.timezone or dbip_data.timezone

    return merged


async def get_ipapi_data(ip_address: str) -> Dict:
    """Получение данных с ipapi.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False)
        device = p.devices["Desktop Firefox"]
        page = await browser.new_page(**device)

        try:
            await page.goto("https://ipapi.com/")
            await page.wait_for_selector('input[name="ip_to_lookup"]', timeout=10000)

            input_ip_to_lookup = page.locator('input[name="ip_to_lookup"]')
            await input_ip_to_lookup.clear()
            await input_ip_to_lookup.type(ip_address, delay=200)
            await input_ip_to_lookup.press("Enter")

            await page.wait_for_selector('[data-demo-fill="latitude"]', timeout=10000)
            await page.wait_for_timeout(2000)

            ip_data = {"source": "ipapi.com"}

            # Location данные
            ip_data["latitude"] = await page.locator(
                '[data-demo-fill="latitude"]'
            ).text_content()
            ip_data["longitude"] = await page.locator(
                '[data-demo-fill="longitude"]'
            ).text_content()
            ip_data["country"] = await page.locator(
                '[data-demo-fill="country"]'
            ).text_content()
            ip_data["city"] = await page.locator(
                '[data-demo-fill="city"]'
            ).text_content()
            ip_data["zip"] = await page.locator('[data-demo-fill="zip"]').text_content()

            # Connection данные
            await page.locator('[data-demo-switch="connection"]').click()
            await page.wait_for_selector('[data-demo-fill="ip"]', timeout=5000)
            ip_data["isp"] = await page.locator('[data-demo-fill="isp"]').text_content()
            ip_data["asn"] = await page.locator('[data-demo-fill="asn"]').text_content()

            return ip_data

        except Exception as e:
            return {"source": "ipapi.com", "error": str(e)}
        finally:
            await browser.close()


async def get_ipinfo_data(ip_address: str) -> Dict:
    """Получение данных с ipinfo.io"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False)
        page = await browser.new_page()

        try:
            await page.goto(
                f"https://ipinfo.io/{ip_address}",
                wait_until="domcontentloaded",
                timeout=3000,
            )

            data = {}

            # Ждем загрузки таблицы
            await page.wait_for_selector("tbody tr", timeout=10000)

            # Получаем все строки таблицы
            rows = await page.query_selector_all("tbody tr")
            print(rows)
            for row in rows:
                try:
                    # Получаем название поля
                    field_name_elem = await row.query_selector("td:first-child")
                    field_name = await field_name_elem.text_content()
                    field_name = field_name.strip()

                    # Получаем значение поля
                    value_elem = await row.query_selector("td:last-child")
                    value = await value_elem.text_content()
                    value = value.strip()

                    # Очищаем и нормализуем названия полей
                    field_name = field_name.lower().replace(" ", "_")

                    # Обрабатываем специальные случаи
                    if field_name == "asn":
                        # Извлекаем ASN номер и название компании
                        asn_parts = value.split(" - ")
                        if len(asn_parts) > 1:
                            data["asn_number"] = asn_parts[0].strip()
                            data["asn_organization"] = asn_parts[1].strip()
                        else:
                            data["asn"] = value

                    elif field_name == "range":
                        # Извлекаем CIDR диапазон
                        data["ip_range"] = value

                    elif field_name == "company":
                        data["company"] = value

                    elif field_name == "hosted_domains":
                        # Преобразуем число в integer (убираем запятые)
                        data["hosted_domains_count"] = int(value.replace(",", ""))

                    elif field_name == "privacy":
                        # Преобразуем в boolean
                        data["is_private"] = "true" in value.lower()

                    elif field_name == "anycast":
                        # Преобразуем в boolean
                        data["is_anycast"] = "true" in value.lower()

                    elif field_name == "asn_type":
                        data["asn_type"] = value.lower()

                    elif field_name == "abuse_contact":
                        # Извлекаем email
                        email_elem = await value_elem.query_selector(
                            'a[href^="mailto:"]'
                        )
                        if email_elem:
                            data["abuse_email"] = await email_elem.text_content()
                        else:
                            data["abuse_contact"] = value

                    elif field_name == "hostname":
                        data["hostname"] = value

                    else:
                        # Для остальных полей сохраняем как есть
                        data[field_name] = value

                except Exception as e:
                    print(f"Ошибка при парсинге строки: {e}")
                    continue

            return data

        except Exception as e:
            return {"source": "ipinfo.io", "error": str(e)}
        finally:
            await browser.close()


async def get_dbip_data(ip_address: str) -> Dict:
    """Получение данных с db-ip.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False)
        page = await browser.new_page()

        try:
            await page.goto(
                f"https://db-ip.com/{ip_address}",
                wait_until="domcontentloaded",
                timeout=3000,
            )
            
            data = {}
            
            await page.wait_for_selector('.menu.results.shadow table', timeout=10000)

            try:
                   # Ждем загрузки основных таблиц
                   await page.wait_for_selector('.menu.results.shadow table', timeout=10000)

                   # Парсим первую таблицу (сетевые данные)
                   network_data = await parse_network_table(page)
                   data.update(network_data)

                   # Парсим вторую таблицу (угрозы)
                   threat_data = await parse_threat_table(page)
                   data.update(threat_data)

                   # Парсим третью таблицу (географические данные)
                   geo_data = await parse_geo_table(page)
                   data.update(geo_data)

                   # Парсим координаты из iframe
                   coordinates = await parse_coordinates_from_iframe(page)
                   if coordinates:
                       data['latitude'], data['longitude'] = coordinates
            except Exception as e:
                   print(f"Ошибка при парсинге: {e}")
            return data
        except Exception as e:
            return {"source": "db-ip.com", "error": str(e)}
        finally:
            await browser.close()


async def get_whatismyipaddress_data(ip_address: str) -> Dict:
    """Получение данных с whatismyipaddress.com"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=False)
        page = await browser.new_page()

        try:
            await page.goto(f"https://whatismyipaddress.com/ip/{ip_address}")
            await page.wait_for_selector("#section_left_3rd", timeout=10000)

            ip_data = {"source": "whatismyipaddress.com"}

            # Извлекаем данные
            details = await page.query_selector_all("#section_left_3rd .card div")
            for detail in details:
                text = await detail.text_content()
                if text and ":" in text:
                    key, value = text.split(":", 1)
                    ip_data[key.strip().lower()] = value.strip()

            return ip_data

        except Exception as e:
            return {"source": "whatismyipaddress.com", "error": str(e)}
        finally:
            await browser.close()


async def get_unified_ip_data(ip_address: str) -> Dict[str, Any]:
    """Получение унифицированных данных IP из всех источников"""
    # Получаем данные из обоих источников
    ipapi_raw = await get_ipapi_data(ip_address)
    ipinfo_raw = await get_ipinfo_data(ip_address)
    

    dbip_raw = await get_dbip_data(ip_address)
    # whatismyipaddress_raw = await get_whatismyipaddress_data(ip_address)

    # Преобразуем к единому формату
    ipapi_unified = transform_ipapi_data(ipapi_raw, ip_address)
    ipinfo_unified = transform_ipinfo_data(ipinfo_raw, ip_address)
    dbip_unified = transform_db_ip_data(dbip_raw,ip_address)

    print(f"Source 'dbip' {dbip_raw}")
    # print(f"Source 'whatismyipaddress' {whatismyipaddress_raw}")
    
    # Объединяем данные
    combined_data = merge_ip_data(ipapi_unified, ipinfo_unified,dbip_unified)

    # Возвращаем результат в виде словаря
    return {
        'sources': {
            'ipapi.com': ipapi_unified.to_dict(),
            'ipinfo.io': ipinfo_unified.to_dict(),
            'db-ip.com': dbip_unified.to_dict()
        },
        'combined': combined_data.to_dict()
    }


async def main():
    ip_address = "169.46.64.41"
    result = await get_unified_ip_data(ip_address)

    print("Унифицированные данные IP:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Можно также получить отдельные источники
    print("\nДанные из ipapi.com:")
    print(json.dumps(result["sources"]["ipapi.com"], indent=2))

    print("\nДанные из ipinfo.io:")
    print(json.dumps(result["sources"]["ipinfo.io"], indent=2))
    
    print("\nДанные из db-ip.com:")
    print(json.dumps(result["sources"]["db-ip.com"], indent=2))

    print("\nОбъединенные данные:")
    print(json.dumps(result["combined"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
