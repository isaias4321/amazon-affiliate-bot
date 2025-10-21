import logging
import random
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientError, ClientTimeout
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.amazon.com.br"
URL_AMAZON_GOLDBOX = urljoin(BASE_URL, "/gp/goldbox")
URL_AMAZON_SEARCH = urljoin(BASE_URL, "/s")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.67",
]

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": f"{BASE_URL}/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

REQUEST_TIMEOUT = ClientTimeout(total=30)


@asynccontextmanager
async def _amazon_session():
    headers = BASE_HEADERS.copy()
    headers["User-Agent"] = random.choice(USER_AGENTS)

    async with aiohttp.ClientSession(headers=headers, timeout=REQUEST_TIMEOUT) as session:
        session.cookie_jar.update_cookies({"lc-main": "pt_BR", "i18n-prefs": "PT_BR"})
        await _warm_up_session(session)
        yield session


async def _warm_up_session(session: aiohttp.ClientSession) -> None:
    try:
        async with session.get(BASE_URL, params={"language": "pt_BR"}) as resp:
            if resp.status == 200:
                await resp.text()
    except ClientError as exc:  # pragma: no cover - log de rede
        logging.debug("Falha ao preparar sessão Amazon: %s", exc)


def _is_blocked_page(html: str) -> bool:
    lowered = html.lower()
    return (
        "/errors/validatecaptcha" in lowered
        or "api-services-support@amazon.com" in lowered
        or "automated access" in lowered
    )


async def _fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: Optional[Dict[str, str]] = None,
    log_context: str = "",
) -> Optional[str]:
    context = f" ({log_context})" if log_context else ""

    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                logging.warning("Erro HTTP %s ao acessar %s%s", resp.status, url, context)
                return None

            html = await resp.text()
    except ClientError as exc:  # pragma: no cover - log de rede
        logging.error("Erro de rede ao acessar %s%s: %s", url, context, exc)
        return None

    if _is_blocked_page(html):
        logging.warning("Amazon retornou uma página de bloqueio para %s", log_context or url)
        return None

    return html


def _extrair_preco(item: Tag) -> Optional[str]:
    preco_tag = item.select_one("span.a-offscreen")
    if preco_tag:
        preco_texto = preco_tag.get_text(strip=True)
        if preco_texto:
            return preco_texto

    parte_inteira = item.select_one("span.a-price-whole")
    if parte_inteira:
        parte_decimal = item.select_one("span.a-price-fraction")
        centavos = parte_decimal.get_text(strip=True) if parte_decimal else "00"
        return f"R$ {parte_inteira.get_text(strip=True)},{centavos}"

    return None


def _parse_goldbox(html: str, limit: int) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    resultados: List[Dict[str, str]] = []

    for item in soup.select("div.DealCard-module__card_1LZr9"):
        titulo = item.select_one("span.DealCard-module__truncate_2QPsL")
        link_tag = item.select_one("a.a-link-normal")

        if not titulo or not link_tag:
            continue

        link_href = link_tag.get("href", "").strip()
        if not link_href:
            continue

        preco = item.select_one("span.a-price-whole")
        imagem_tag = item.select_one("img")

        resultados.append(
            {
                "titulo": titulo.get_text(strip=True),
                "preco": preco.get_text(strip=True) if preco else "Ver preço",
                "link": urljoin(BASE_URL, link_href),
                "imagem": imagem_tag.get("src") if imagem_tag else None,
            }
        )

        if len(resultados) >= limit:
            break

    return resultados


def _parse_search_results(html: str, limit: int) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    resultados: List[Dict[str, str]] = []
    links_vistos = set()

    for item in soup.select("div[data-component-type='s-search-result'][data-asin]"):
        link_tag = item.select_one("h2 a")
        titulo_tag = link_tag.select_one("span") if link_tag else None

        if not link_tag or not titulo_tag:
            continue

        link_href = link_tag.get("href", "").strip()
        if not link_href:
            continue

        link = urljoin(BASE_URL, link_href)
        if link in links_vistos:
            continue

        links_vistos.add(link)

        imagem_tag = item.select_one("img.s-image")
        imagem = None
        if imagem_tag:
            imagem = imagem_tag.get("src") or imagem_tag.get("data-image-src")

        resultados.append(
            {
                "titulo": titulo_tag.get_text(strip=True),
                "preco": _extrair_preco(item) or "Ver preço",
                "link": link,
                "imagem": imagem,
            }
        )

        if len(resultados) >= limit:
            break

    return resultados


async def buscar_ofertas(limit: int = 10) -> List[Dict[str, str]]:
    """Busca ofertas na página Goldbox da Amazon Brasil."""

    async with _amazon_session() as session:
        html = await _fetch_html(session, URL_AMAZON_GOLDBOX, log_context="goldbox")
        if not html:
            return []

        ofertas = _parse_goldbox(html, limit)
        logging.info("%s ofertas coletadas no Goldbox", len(ofertas))
        return ofertas


async def buscar_ofertas_por_categoria(
    categoria: str, limit: int = 10
) -> List[Dict[str, str]]:
    """Busca ofertas diretamente na Amazon Brasil para uma categoria."""

    params = {
        "k": categoria,
        "__mk_pt_BR": "ÅMÅŽÕÑ",
        "ref": "nb_sb_noss",
        "s": "featured-rank",
        "language": "pt_BR",
    }

    async with _amazon_session() as session:
        html = await _fetch_html(
            session,
            URL_AMAZON_SEARCH,
            params=params,
            log_context=f"busca '{categoria}'",
        )
        if not html:
            return []

        produtos = _parse_search_results(html, limit)
        logging.info("%s produtos coletados para a categoria %s", len(produtos), categoria)
        return produtos
