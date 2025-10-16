import aiohttp
import logging
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

def parse_price(raw: str):
    if not raw:
        return None
    s = re.sub(r'[^0-9,\.]', '', raw)
    if s.count(',') == 1 and s.count('.') >= 1:
        s = s.replace('.', '').replace(',', '.')
    elif s.count(',') == 1 and s.count('.') == 0:
        s = s.replace(',', '.')
    else:
        s = s.replace(',', '')
    try:
        return float(s)
    except:
        return None

async def fetch_html(url, scrapeops_key=None, timeout=20):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36'}
    if scrapeops_key:
        proxy_url = 'https://proxy.scrapeops.io/v1/'
        params = {'api_key': scrapeops_key, 'url': url}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(proxy_url, params=params, headers=headers, timeout=timeout) as resp:
                    if resp.status != 200:
                        logger.warning("⚠️ ScrapeOps respondeu %s para %s", resp.status, url)
                        return None
                    return await resp.text()
            except Exception as e:
                logger.error("Erro ScrapeOps: %s", e)
                return None
    else:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status != 200:
                        logger.warning("⚠️ HTTP %s ao acessar %s", resp.status, url)
                        return None
                    return await resp.text()
            except Exception as e:
                logger.error("Erro HTTP: %s", e)
                return None

async def parse_offers_from_html(html, affiliate_tag):
    offers = []
    if not html:
        return offers
    soup = BeautifulSoup(html, 'html.parser')
    anchors = soup.find_all('a', href=True)
    seen = set()
    for a in anchors:
        href = a['href']
        if '/dp/' not in href:
            continue
        if href.startswith('/'):
            link = 'https://www.amazon.com.br' + href.split('?')[0]
        elif href.startswith('http'):
            link = href.split('?')[0]
        else:
            link = 'https://www.amazon.com.br' + href.split('?')[0]
        if link in seen:
            continue
        seen.add(link)
        title_tag = a.find('span') or a.find_next('span')
        title = title_tag.get_text(strip=True) if title_tag else None
        node = a
        price_new = None
        price_old = None
        for _ in range(4):
            node = node.parent if node.parent else node
            if not node:
                break
            new_sel = node.select_one('.a-price .a-offscreen')
            old_sel = node.select_one('.a-text-price .a-offscreen')
            if new_sel and not price_new:
                price_new = new_sel.get_text(strip=True)
            if old_sel and not price_old:
                price_old = old_sel.get_text(strip=True)
        if not price_old:
            old_sel = a.find_next(string=re.compile(r'R\$\s*[0-9]'))
            if old_sel:
                price_old = old_sel.strip()
        n_new = parse_price(price_new) if price_new else None
        n_old = parse_price(price_old) if price_old else None
        if n_new and n_old and n_old > 0:
            discount_pct = round((1 - (n_new / n_old)) * 100)
        else:
            discount_pct = 0
        if title and link and discount_pct >= 15:
            sep = '&' if '?' in link else '?'
            affiliate_link = f"{link}{sep}tag={affiliate_tag}"
            offers.append({
                'title': title,
                'price_new': n_new,
                'price_old': n_old,
                'discount_pct': discount_pct,
                'link': affiliate_link
            })
    return offers

async def buscar_ofertas_por_categorias(categorias, affiliate_tag, scrapeops_key=None):
    all_offers = []
    goldbox_url = f"https://www.amazon.com.br/gp/goldbox?tag={affiliate_tag}"
    html_goldbox = await fetch_html(goldbox_url, scrapeops_key)
    if html_goldbox:
        offers = await parse_offers_from_html(html_goldbox, affiliate_tag)
        for o in offers:
            title_lower = o['title'].lower()
            for cat in categorias:
                if cat.lower() in title_lower and o not in all_offers:
                    all_offers.append(o)
    for cat in categorias:
        search_url = f"https://www.amazon.com.br/s?k={cat.replace(' ', '+')}"
        html = await fetch_html(search_url, scrapeops_key)
        if not html:
            continue
        offers = await parse_offers_from_html(html, affiliate_tag)
        for o in offers:
            title_lower = o['title'].lower()
            if cat.lower() in title_lower and o not in all_offers:
                all_offers.append(o)
    return all_offers
