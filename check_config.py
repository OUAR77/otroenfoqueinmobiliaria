import config
print(f"SITE_NAME: {config.SITE_NAME}")
print(f"WHATSAPP: {config.WHATSAPP_NUMBER}")
print(f"GROQ: {'OK' if config.GROQ_API_KEY else 'MISSING'}")
