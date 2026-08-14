import logging
import uuid
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
import config

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ===========================================================================
# Supabase REST API Helpers
# ===========================================================================

def supabase_request(endpoint, method="GET", data=None):
    url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/{endpoint}"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body) if res_body else []
    except Exception as e:
        logging.error(f"Supabase request error [{method} {endpoint}]: {e}")
        return None

def generate_serial_supabase(days=30, plan_type="monthly", user_name="Customer"):
    key = f"LOVA-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    
    if days > 0:
        exp_dt = datetime.now(timezone.utc) + timedelta(days=days)
        exp_str = exp_dt.isoformat()
        exp_display = exp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    else:
        exp_str = "2099-12-31T23:59:59Z"
        exp_display = "LIFETIME (مدى الحياة)"

    payload = {
        "key": key,
        "status": "active",
        "expires_at": exp_str,
        "plan": plan_type,
        "user_name": user_name,
        "user_email": f"{user_name.lower().replace(' ', '_')}@lovaextreme.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device_id": ""
    }

    res = supabase_request("licenses", method="POST", data=payload)
    if res is not None:
        return key, exp_display
    return None, None

# ===========================================================================
# Telegram Bot Handlers
# ===========================================================================

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🔥 **Welcome {user_name} to LOVAEXTREME Official Bot!** 🔥\n"
        f"🔥 **مرحباً بك يا {user_name} في بوت LOVAEXTREME الرسمي!** 🔥\n\n"
        "⚡ Supercharge your workflow & build on **Lovable AI** without credit limits 🚀\n"
        "⚡ الإكستنشن الأقوى لتطوير وتسرع العمل على منصة **Lovable** 🚀\n\n"
        "Select an option below / اختر خياراً من القائمة أدناه:"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚡ Claim Free 15-Min Trial | تجربة 15 دقيقة مجاناً", callback_data="claim_trial")],
        [InlineKeyboardButton("🛒 Buy License Key | شراء سيريال ترخيص", callback_data="buy")],
        [InlineKeyboardButton("📥 Download Extension | تحميل الإضافة", callback_data="download")],
        [InlineKeyboardButton("❓ FAQ & Activation | الأسئلة الشائعة والتفعيل", callback_data="faq")],
        [InlineKeyboardButton("💬 Contact Support | التواصل مع الدعم الفني", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# Handle Callback Buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "claim_trial":
        user_id = query.from_user.id
        user_name = query.from_user.first_name or "User"
        tg_tag = f"TG_{user_id}_TRIAL"
        
        # Check if user already claimed trial
        check_res = supabase_request(f"licenses?user_name=eq.{tg_tag}&limit=1")
        if check_res and len(check_res) > 0:
            existing = check_res[0]
            text = (
                "⚠️ **You have already claimed your 1-time 15-Minute Free Trial!**\n"
                "⚠️ **لقد حصلت على التجربة المجانية (15 دقيقة) مسبقاً لهذا الحساب!**\n\n"
                f"🔑 **Previous Trial Key:** `{existing.get('key')}`\n"
                f"📌 **Status:** {existing.get('status')}\n\n"
                "💡 To continue enjoying unlimited access, please select a plan below.\n"
                "💡 للاستمرار في الاستمتاع بجميع الخصائص يمكنك اختيار إحدى الباقات."
            )
            keyboard = [
                [InlineKeyboardButton("🛒 Buy License Key | شراء سيريال ترخيص", callback_data="buy")],
                [InlineKeyboardButton("🔙 Back to Main Menu | العودة للقائمة", callback_data="main_menu")]
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        # Generate 15-minute trial key
        key = f"TR15-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
        exp_dt = datetime.now(timezone.utc) + timedelta(minutes=15)
        exp_str = exp_dt.isoformat()
        
        payload = {
            "key": key,
            "status": "active",
            "expires_at": exp_str,
            "plan": "trial_15m",
            "user_name": tg_tag,
            "user_email": f"{user_id}_trial@lovaextreme.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device_id": ""
        }
        
        gen_res = supabase_request("licenses", method="POST", data=payload)
        if gen_res:
            text = (
                f"🎁 **Congratulations {user_name}! Your 15-Minute Trial Key is ready!**\n"
                f"🎁 **مبروك يا {user_name}! تم توليد سيريال تجريبي لمدة 15 دقيقة بنجاح!**\n\n"
                f"🔑 **Key / السيريال:** `{key}`\n"
                f"⏱️ **Expires / ينتهي في:** {exp_dt.strftime('%H:%M:%S UTC')}\n\n"
                "💡 Copy your key and activate it in the extension or Download Portal immediately!\n"
                "💡 قم بنسخ السيريال وتفعيله في الإكستنشن أو في بوابة التحميل فوراً!"
            )
        else:
            text = "❌ Error generating trial key. Please try again later.\n❌ حدث خطأ أثناء إنشاء السيريال التجريبي."

        keyboard = [
            [InlineKeyboardButton("📥 Download Extension | تحميل الإضافة", callback_data="download")],
            [InlineKeyboardButton("🛒 Buy Full Pass | شراء باقة كاملة", callback_data="buy")],
            [InlineKeyboardButton("🔙 Main Menu | القائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "buy":
        text = (
            "💳 **LOVAEXTREME License Plans & Prices / أسعار باقات سيريالات:**\n\n"
            f"🟢 **Monthly Pass (30-Day / 30 يوم):** ${config.PRICES['monthly']['usd']} / {config.PRICES['monthly']['egp']} EGP\n"
            f"🟣 **Lifetime Pass (مدى الحياة):** ${config.PRICES['lifetime']['usd']} / {config.PRICES['lifetime']['egp']} EGP\n"
            f"👑 **Partner Structure (الشركاء والموزعين):** ${config.PRICES['reseller']['usd']} / {config.PRICES['reseller']['egp']} EGP\n\n"
            "📌 **Accepted Payment Methods / وسائل الدفع المتاحة:**\n"
            f"📱 Vodafone Cash / InstaPay: `{config.PAYMENT_INFO['VODAFONE_CASH']}`\n"
            f"🌐 Binance / USDT (TRC20): `{config.PAYMENT_INFO['BINANCE_PAY']}`\n\n"
            "After payment, click 'Send Payment Receipt' to receive your activation key instantly!\n"
            "بعد الدفع، اضغط على زر 'إرسال إيصال الدفع' ليتم إرسال السيريال لك فوراً!"
        )
        keyboard = [
            [InlineKeyboardButton("📤 Send Payment Receipt | إرسال إيصال الدفع للأدمن", callback_data="send_receipt")],
            [InlineKeyboardButton("🔙 Main Menu | العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "send_receipt":
        text = (
            "📩 **Please send your payment screenshot & requested plan name in chat.**\n"
            "📩 **يرجى كتابة اسم الباقة المطلوبة مع إرفاق صورة الإيصال هنا في الشات.**\n\n"
            f"Or contact Admin directly / أو تواصل مع الأدمن مباشرة: {config.PAYMENT_INFO['ADMIN_CONTACT']}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back | العودة", callback_data="buy")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "download":
        text = (
            "📥 **Download LOVAEXTREME Extension v12.0 / تحميل إكستنشن:**\n\n"
            "Download the latest official signed build v12.0 via our official channel:\n"
            "يمكنك تنزيل الإصدار الأخير v12 والمشروح في دليل التثبيت عبر قناتنا الرسمية:\n"
            f"🔗 {config.DOWNLOAD_LINK}\n\n"
            "Requires an active license key to unlock unlimited AI features."
        )
        keyboard = [[InlineKeyboardButton("🔙 Main Menu | القائمة الرئيسية", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "faq":
        text = (
            "📘 **Installation & Activation Guide / دليل التثبيت والتفعيل:**\n\n"
            "1️⃣ Download & unzip the extension package.\n"
            "2️⃣ Open `chrome://extensions` and enable Developer Mode.\n"
            "3️⃣ Click 'Load Unpacked' and select the unzipped folder.\n"
            "4️⃣ Enter your active key into the extension popup.\n\n"
            "⚠️ Each license key is bound to 1 PC/Device."
        )
        keyboard = [[InlineKeyboardButton("🔙 Main Menu | القائمة الرئيسية", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "support":
        text = f"💬 For direct human support / للدعم الفني والتواصل المباشر:\n👉 {config.PAYMENT_INFO['ADMIN_CONTACT']}"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu | القائمة الرئيسية", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "main_menu":
        await start(update, context)

# ===========================================================================
# Admin Commands (Supabase Connected)
# ===========================================================================

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

# /gen <days> [plan_name]
async def admin_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    days = 30
    plan = "monthly"
    if context.args:
        arg0 = context.args[0].lower()
        if arg0 in ["lifetime", "forever", "0"]:
            days = 0
            plan = "lifetime"
        elif arg0.isdigit():
            days = int(arg0)
        
        if len(context.args) > 1:
            plan = context.args[1]

    key, exp = generate_serial_supabase(days=days, plan_type=plan)
    if not key:
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء السيريال في Supabase.")
        return

    msg = (
        f"✅ **تم توليد سيريال جديد وحفظه في Supabase بنجاح!**\n\n"
        f"🔑 **السيريال:** `{key}`\n"
        f"📅 **تاريخ الانتهاء:** {exp}\n"
        f"🏷️ **الباقة:** {plan}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# /groupgen <hours> <max_devices> [name]
async def admin_groupgen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    hours = 2
    max_dev = 50
    name = "Live Demo Group"

    if context.args:
        if context.args[0].isdigit():
            hours = int(context.args[0])
        if len(context.args) > 1 and context.args[1].isdigit():
            max_dev = int(context.args[1])
        if len(context.args) > 2:
            name = " ".join(context.args[2:])

    key = f"GRP-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    exp_dt = datetime.now(timezone.utc) + timedelta(hours=hours)
    exp_str = exp_dt.isoformat()
    plan_name = f"GROUP_{hours}h_{max_dev}dev"

    payload = {
        "key": key,
        "status": "active",
        "expires_at": exp_str,
        "plan": plan_name,
        "user_name": name,
        "user_email": "group@lovaextreme.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device_id": "",
        "max_devices": max_dev
    }

    res = supabase_request("licenses", method="POST", data=payload)
    if not res:
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء السيريال الجماعي.")
        return

    msg = (
        f"🚀 **تم إنشاء سيريال تجريبي جماعي (Live Demo / Group Trial)!**\n\n"
        f"🔑 **السيريال:** `{key}`\n"
        f"⏱️ **المدة:** {hours} ساعات (ينتهي: {exp_dt.strftime('%H:%M %d/%m/%Y UTC')})\n"
        f"💻 **الحد الأقصى للأجهزة:** {max_dev} جهاز\n"
        f"🏷️ **اسم المجموعة:** {name}\n\n"
        f"💡 يمكنك مشاركة هذا السيريال الآن في القناة/المجموعة ليستمتع به الجميع في نفس الوقت!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# /devices <key>
async def admin_devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة السيريال بعد الأمر.\nمثال: `/devices GRP-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}&limit=1")

    if not res or len(res) == 0:
        await update.message.reply_text(f"❌ السيريال غير موجود: `{key}`", parse_mode="Markdown")
        return

    item = res[0]
    raw_dev = item.get('device_id') or ''
    max_dev = item.get('max_devices') or 1

    dev_list = []
    if typeof_str := isinstance(raw_dev, str) and raw_dev.strip().startswith('['):
        try: dev_list = json.loads(raw_dev)
        except: dev_list = []
    elif raw_dev:
        dev_list = [{"id": raw_dev}]

    msg = (
        f"📊 **فحص أجهزة السيريال الجماعي:**\n\n"
        f"🔑 **السيريال:** `{key}`\n"
        f"💻 **الأجهزة النشطة حالياً:** {len(dev_list)} / {max_dev} جهاز\n"
        f"📌 **الحالة:** {item.get('status')}\n\n"
    )

    if dev_list:
        msg += "📋 **قائمة معرّفات الأجهزة:**\n"
        for idx, d in enumerate(dev_list[:20], 1):
            did = d.get('id') if isinstance(d, dict) else str(d)
            msg += f"{idx}. `{did[:15]}...`\n"
        if len(dev_list) > 20:
            msg += f"... بالإضافة إلى {len(dev_list) - 20} أجهزة أخرى."
    else:
        msg += "ℹ️ لم يقم أي جهاز بالتسجيل حتى الآن."

    await update.message.reply_text(msg, parse_mode="Markdown")

# /check <key>
async def admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة السيريال بعد الأمر.\nمثال: `/check LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}&limit=1")

    if not res or len(res) == 0:
        await update.message.reply_text(f"❌ السيريال غير موجود: `{key}`", parse_mode="Markdown")
        return

    item = res[0]
    hwid = item.get('device_id') or 'غير مربط بجهاز حتى الآن (Free)'
    msg = (
        f"📋 **تفاصيل السيريال:**\n\n"
        f"🔑 **السيريال:** `{item.get('key')}`\n"
        f"📌 **الحالة:** {item.get('status')}\n"
        f"📅 **الانتهاء:** {item.get('expires_at')}\n"
        f"🏷️ **الباقة:** {item.get('plan')}\n"
        f"💻 **الجهاز (HWID):** `{hwid}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# /reset <key>  (Resets device binding)
async def admin_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة السيريال بعد الأمر.\nمثال: `/reset LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}", method="PATCH", data={"device_id": ""})

    if res is not None:
        await update.message.reply_text(f"✅ تم فك ربط الجهاز للسيريال: `{key}` بنجاح!\nيمكن للعميل الآن تفعيله على جهاز جديد.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ فشل فك ربط السيريال: `{key}`", parse_mode="Markdown")

# /revoke <key>  (Revokes key immediately)
async def admin_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة السيريال بعد الأمر.\nمثال: `/revoke LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}", method="PATCH", data={"status": "revoked"})

    if res is not None:
        await update.message.reply_text(f"🛑 تم إلغاء وتجميد السيريال: `{key}` فوراً!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ فشل تجميد السيريال: `{key}`", parse_mode="Markdown")

# /stats (Summary of licenses in Supabase)
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر مخصص للأدمن فقط.")
        return

    res = supabase_request("licenses?select=status")
    if res is None:
        await update.message.reply_text("❌ تعذر الاتصال بـ Supabase.")
        return

    total = len(res)
    active = sum(1 for r in res if r.get('status') == 'active')
    revoked = sum(1 for r in res if r.get('status') == 'revoked')

    msg = (
        f"📊 **إحصائيات السيريالات في Supabase:**\n\n"
        f"🔢 **إجمالي السيريالات:** {total}\n"
        f"🟢 **السيريالات النشطة:** {active}\n"
        f"🛑 **السيريالات المجمّدة:** {revoked}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ===========================================================================
# Main Function
# ===========================================================================

def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("⚠️ Please set your TELEGRAM_BOT_TOKEN in config.py before running!")
        return

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gen", admin_gen))
    app.add_handler(CommandHandler("genserial", admin_gen))
    app.add_handler(CommandHandler("groupgen", admin_groupgen))
    app.add_handler(CommandHandler("devices", admin_devices))
    app.add_handler(CommandHandler("check", admin_check))
    app.add_handler(CommandHandler("reset", admin_reset))
    app.add_handler(CommandHandler("revoke", admin_revoke))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CallbackQueryHandler(button_handler))

    print(f"🤖 LOVAEXTREME Telegram Bot is running & connected to Supabase ({config.SUPABASE_URL})...")
    app.run_polling()

if __name__ == "__main__":
    main()
