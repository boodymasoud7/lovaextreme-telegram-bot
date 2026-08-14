import os

# Telegram Bot Token (مستخرج من @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8615819499:AAGnzAgQKAtOLHA-RwhDWwoS9Um9pHtu9Os")

# معرف الأدمن في تليجرام (Admin Telegram ID)
ADMIN_IDS = [int(id_str) for id_str in os.getenv("ADMIN_IDS", "7268672117").split(",") if id_str.strip()]

# معلومات وسائل الدفع
PAYMENT_INFO = {
    "VODAFONE_CASH": os.getenv("VODAFONE_CASH", "01099666940"),
    "INSTAPAY": os.getenv("INSTAPAY", "01099666940"),
    "BINANCE_PAY": os.getenv("BINANCE_PAY", "USDT (TRC20): TXXXXXXXXXXXXXXXXXXXXXXXXX"),
    "ADMIN_CONTACT": os.getenv("ADMIN_CONTACT", "@boodymasoud")
}

# أسعار الباقات بالدولار / الجنيه المصري
PRICES = {
    "monthly": {"usd": 10, "egp": 500, "name": "الباقة الشهرية (30 يوم)"},
    "lifetime": {"usd": 70, "egp": 3500, "name": "باقة مدى الحياة (Lifetime)"},
    "reseller": {"usd": 100, "egp": 5000, "name": "اشتراك الشركاء والموزعين (Partner)"}
}

# رابط تحميل الإكستنشن وبوابة التحميل الرسمية بالموقع
DOWNLOAD_LINK = os.getenv("DOWNLOAD_LINK", "https://www.lovaextreme.online/download")

# القناة المطلوبة للاشتراك الإجباري
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@LovaExtreme_Official")

# إعدادات Supabase مع المفتاح الإداري service_role
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ysrjlpuozvemuzulsoxt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlzcmpscHVvenZlbXV6dWxzb3h0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NjcxNDAwMSwiZXhwIjoyMTAyMjkwMDAxfQ.-q2K_K8e4M3Fg8poI9BTZzaHddAIY3o6XODieQocFmg")
