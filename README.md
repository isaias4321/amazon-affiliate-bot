# Amazon Ofertas Brasil - Webhook version

## Quickstart (Railway)
1. Upload project to Railway.
2. Set environment variables in Railway project settings:
   - TELEGRAM_TOKEN
   - GROUP_ID
   - AFFILIATE_TAG
   - SCRAPEOPS_API_KEY (optional)
   - WEBHOOK_BASE (default: https://amazon-ofertas-api.up.railway.app)
3. Deploy. The app will register webhook automatically and send a "bot started" message to the group.

## Notes
- Uses ScrapeOps (proxy) to render JS-heavy pages and avoid blocks. If you don't have ScrapeOps key, leave SCRAPEOPS_API_KEY empty.
- The scraper filters offers with >= 15% discount and sends to the configured GROUP_ID.
- Logs are printed to console (Railway) so you can monitor cycles.
