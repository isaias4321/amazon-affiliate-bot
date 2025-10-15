async def fetch_html(url: str) -> str:
    """Faz requisição assíncrona com cabeçalhos realistas e tratamento de erro aprimorado"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao acessar {url}")
                    text = await resp.text()
                    if "Bot Check" in text or "captcha" in text.lower():
                        logger.warning("⚠️ Amazon retornou CAPTCHA — bloqueio de bot detectado.")
                    return ""
                return await resp.text()
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout ao acessar {url}")
        return ""
    except aiohttp.ClientError as e:
        logger.error(f"Erro de conexão ao acessar {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Erro inesperado em fetch_html({url}): {e}")
        return ""
