import os
from dotenv import load_dotenv

load_dotenv()

print("CLIENT_ID:", os.getenv("REDDIT_CLIENT_ID"))
print("SECRET:", "EXISTS" if os.getenv("REDDIT_CLIENT_SECRET") else "MISSING")
print("USER_AGENT:", os.getenv("REDDIT_USER_AGENT"))