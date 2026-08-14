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

# User language preference storage (in memory per chat)
USER_LANGUAGES = {}

def get_user_lang(user_id):
    return USER_LANGUAGES.get(user_id, 'en')

def set_user_lang(user_id, lang):
    USER_LANGUAGES[user_id] = lang

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

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

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
# Language Selection & Main Menus
# ===========================================================================

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Sends notification to all admin Telegram IDs."""
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Failed to send admin notification to {admin_id}: {e}")

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: Displays language selection first for clean UX."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "User"
    username = update.effective_user.username
    user_handle = f"@{username}" if username else "بدون يوزر"
    
    # Notify Admin about new user interaction
    if update.message:
        admin_note = (
            f"🔔 **إشعار مستخدم جديد على البوت!**\n\n"
            f"👤 **الاسم:** {user_name}\n"
            f"🏷️ **اليوزر:** {user_handle}\n"
            f"🆔 **Telegram ID:** `{user_id}`\n"
            f"⏱️ **الوقت:** {datetime.now(timezone.utc).strftime('%H:%M:%S %Y-%m-%d UTC')}"
        )
        await notify_admin(context, admin_note)

    welcome_text = (
        f"🌐 **Welcome {user_name} to LOVAEXTREME!**\n"
        f"🌐 **مرحباً بك يا {user_name} في LOVAEXTREME!**\n\n"
        "Please select your preferred language below:\n"
        "يرجى اختيار لغتك المفضلة من القائمة أدناه:"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            InlineKeyboardButton("🇪🇬 العربية", callback_data="lang_ar")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_main_menu(query, lang, user_name):
    """Displays localized ultra-professional main menu."""
    if lang == 'en':
        text = (
            f"⚡ **Welcome {user_name} to LOVAEXTREME** ⚡\n\n"
            "Supercharge your workflow on **Lovable AI** without credit throttling. Build fast, optimize prompts, and remove watermarks.\n\n"
            "📌 **Please select an option below:**"
        )
        keyboard = [
            [InlineKeyboardButton("⚡ Claim Free 15-Min Trial", callback_data="claim_trial")],
            [InlineKeyboardButton("💳 Plans & Pricing", callback_data="buy")],
            [InlineKeyboardButton("📥 Download Extension v12", callback_data="download")],
            [InlineKeyboardButton("📘 Installation Guide & FAQ", callback_data="faq")],
            [InlineKeyboardButton("💬 Human Support Queue", callback_data="support")],
            [InlineKeyboardButton("🌐 Change Language / تغيير اللغة", callback_data="change_lang")]
        ]
    else:
        text = (
            f"⚡ **مرحباً بك يا {user_name} في LOVAEXTREME** ⚡\n\n"
            "الإكستنشن الأقوى لتطوير وتسرع العمل على منصة **Lovable AI** بدون حدود للكريديت. أسرع 10 مرات في بناء المشاريع!\n\n"
            "📌 **يرجى اختيار خيار من القائمة أدناه:**"
        )
        keyboard = [
            [InlineKeyboardButton("⚡ طلب تجربة 15 دقيقة مجاناً", callback_data="claim_trial")],
            [InlineKeyboardButton("💳 أسعار الباقات والشراء", callback_data="buy")],
            [InlineKeyboardButton("📥 تحميل التحديث الأخير v12", callback_data="download")],
            [InlineKeyboardButton("📘 دليل التثبيت والأسئلة الشائعة", callback_data="faq")],
            [InlineKeyboardButton("💬 الدعم الفني المباشر", callback_data="support")],
            [InlineKeyboardButton("🌐 Change Language / تغيير اللغة", callback_data="change_lang")]
        ]
    
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ===========================================================================
# Channel Subscription & Force Join Helpers
# ===========================================================================

async def check_channel_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Verifies if the user is a member of the required Telegram channel."""
    if not config.REQUIRED_CHANNEL:
        return True
    try:
        chat = config.REQUIRED_CHANNEL.strip()
        if not chat.startswith("@") and not chat.startswith("-100"):
            chat = f"@{chat}"
        member = await context.bot.get_chat_member(chat_id=chat, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        logging.warning(f"Channel subscription check failed for user {user_id}: {e}")
        return False # Return False so non-members get prompted to join

async def send_force_sub_message(message_obj, lang='ar'):
    channel_url = f"https://t.me/{config.REQUIRED_CHANNEL.lstrip('@')}"
    if lang == 'en':
        text = (
            "📢 **REQUIRED CHANNEL SUBSCRIPTION**\n\n"
            f"You must join our official Telegram channel ({config.REQUIRED_CHANNEL}) to use LOVAEXTREME bot and claim your free trial!\n\n"
            "After joining, click **Check Subscription** below:"
        )
        keyboard = [
            [InlineKeyboardButton("📢 Join Official Channel", url=channel_url)],
            [InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")]
        ]
    else:
        text = (
            "📢 **الاشتراك الإجباري بالقناة الرسمية**\n\n"
            f"يجب الانضمام لقناتنا الرسمية ({config.REQUIRED_CHANNEL}) لاستخدام بوت LOVAEXTREME والحصول على التجربة المجانية!\n\n"
            "بعد الانضمام، اضغط على زر **تأكيد الاشتراك** بالأسفل:"
        )
        keyboard = [
            [InlineKeyboardButton("📢 الانضمام للقناة الرسمية", url=channel_url)],
            [InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="check_sub")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(message_obj, "edit_text"):
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await message_obj.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ===========================================================================
# Callback Query Button Router
# ===========================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name or "User"
    data = query.data
    
    # Handle Language Selection
    if data == "lang_en":
        set_user_lang(user_id, 'en')
        lang = 'en'
        if not await check_channel_subscription(context, user_id):
            await send_force_sub_message(query.message, lang)
            return
        await show_main_menu(query, 'en', user_name)
        return
    elif data == "lang_ar":
        set_user_lang(user_id, 'ar')
        lang = 'ar'
        if not await check_channel_subscription(context, user_id):
            await send_force_sub_message(query.message, lang)
            return
        await show_main_menu(query, 'ar', user_name)
        return
    elif data == "change_lang":
        await start(update, context)
        return
    elif data == "check_sub":
        lang = get_user_lang(user_id)
        if await check_channel_subscription(context, user_id):
            await show_main_menu(query, lang, user_name)
        else:
            await send_force_sub_message(query.message, lang)
        return
    elif data == "main_menu":
        lang = get_user_lang(user_id)
        if not await check_channel_subscription(context, user_id):
            await send_force_sub_message(query.message, lang)
            return
        await show_main_menu(query, lang, user_name)
        return

    lang = get_user_lang(user_id)

    # Force Sub Enforcement for feature buttons
    if data in ["claim_trial", "download", "buy", "faq", "support"]:
        if not await check_channel_subscription(context, user_id):
            await send_force_sub_message(query.message, lang)
            return

    # 1. Claim Trial
    if data == "claim_trial":
        tg_tag = f"TG_{user_id}_TRIAL"
        
        # Check if user already claimed trial
        check_res = supabase_request(f"licenses?user_name=eq.{tg_tag}&limit=1")
        if check_res and len(check_res) > 0:
            existing = check_res[0]
            if lang == 'en':
                text = (
                    "⚠️ **You have already claimed your 1-time 15-Minute Free Trial!**\n\n"
                    f"🔑 **Previous Trial Key:** `{existing.get('key')}`\n"
                    f"📌 **Status:** {existing.get('status')}\n\n"
                    "💡 To continue enjoying unlimited access, please upgrade to a pass."
                )
                keyboard = [
                    [InlineKeyboardButton("💳 View Pricing Plans", callback_data="buy")],
                    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
                ]
            else:
                text = (
                    "⚠️ **لقد حصلت على التجربة المجانية (15 دقيقة) مسبقاً لهذا الحساب!**\n\n"
                    f"🔑 **السيريال التجريبي السابق:** `{existing.get('key')}`\n"
                    f"📌 **الحالة:** {existing.get('status')}\n\n"
                    "💡 للاستمرار في الاستمتاع بجميع الخصائص يمكنك اختيار إحدى الباقات."
                )
                keyboard = [
                    [InlineKeyboardButton("💳 عرض الباقات والشراء", callback_data="buy")],
                    [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
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
            # Notify Admin about trial creation
            username_tag = f"@{query.from_user.username}" if query.from_user.username else "بدون يوزر"
            trial_note = (
                f"🎁 **إشعار إصدار سيريال تجريبي جديد!**\n\n"
                f"👤 **المستخدم:** {user_name} ({username_tag})\n"
                f"🆔 **Telegram ID:** `{user_id}`\n"
                f"🔑 **السيريال:** `{key}`\n"
                f"⏱️ **المدة:** 15 دقيقة (ينتهي: {exp_dt.strftime('%H:%M:%S UTC')})"
            )
            await notify_admin(context, trial_note)

            if lang == 'en':
                text = (
                    f"🎁 **Congratulations {user_name}! Your 15-Minute Trial Key is ready!**\n\n"
                    f"🔑 **Serial Key:** `{key}`\n"
                    f"⏱️ **Expires At:** {exp_dt.strftime('%H:%M:%S UTC')}\n\n"
                    "💡 Copy your key and paste it inside the extension popup or Download Portal to activate immediately!"
                )
                keyboard = [
                    [InlineKeyboardButton("📥 Download Extension", callback_data="download")],
                    [InlineKeyboardButton("💳 Upgrade to Full Pass", callback_data="buy")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
                ]
            else:
                text = (
                    f"🎁 **مبروك يا {user_name}! تم توليد سيريال تجريبي لمدة 15 دقيقة بنجاح!**\n\n"
                    f"🔑 **السيريال:** `{key}`\n"
                    f"⏱️ **ينتهي في:** {exp_dt.strftime('%H:%M:%S UTC')}\n\n"
                    "💡 قم بنسخ السيريال وتفعيله في نافذة الإكستنشن أو بوابة التحميل فوراً!"
                )
                keyboard = [
                    [InlineKeyboardButton("📥 تحميل الإضافة", callback_data="download")],
                    [InlineKeyboardButton("💳 شراء باقة كاملة", callback_data="buy")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
                ]
        else:
            text = "❌ Error generating trial key. Please try again later." if lang == 'en' else "❌ حدث خطأ أثناء إنشاء السيريال التجريبي. يرجى المحاولة لاحقاً."
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # 2. Buy / Plans
    elif data == "buy":
        if lang == 'en':
            text = (
                "💳 **LOVAEXTREME LICENSE PLANS & PRICING:**\n\n"
                f"🟢 **Monthly Pass (30-Day):** ${config.PRICES['monthly']['usd']} / {config.PRICES['monthly']['egp']} EGP\n"
                f"🟣 **Lifetime Pass (Unlimited):** ${config.PRICES['lifetime']['usd']} / {config.PRICES['lifetime']['egp']} EGP\n"
                f"👑 **Partner Structure (Wholesale):** ${config.PRICES['reseller']['usd']} / {config.PRICES['reseller']['egp']} EGP\n\n"
                "📌 **Accepted Payment Methods:**\n"
                f"📱 Vodafone Cash / InstaPay: `{config.PAYMENT_INFO['VODAFONE_CASH']}`\n"
                f"🌐 Binance / USDT (TRC20): `{config.PAYMENT_INFO['BINANCE_PAY']}`\n\n"
                "After payment, click **Send Payment Receipt** to receive your activation key instantly!"
            )
            keyboard = [
                [InlineKeyboardButton("📤 Send Payment Receipt", callback_data="send_receipt")],
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
            ]
        else:
            text = (
                "💳 **أسعار باقات سيريالات LOVAEXTREME:**\n\n"
                f"🟢 **الباقة الشهرية (30 يوم):** ${config.PRICES['monthly']['usd']} / {config.PRICES['monthly']['egp']} EGP\n"
                f"🟣 **باقة مدى الحياة (Lifetime):** ${config.PRICES['lifetime']['usd']} / {config.PRICES['lifetime']['egp']} EGP\n"
                f"👑 **باقة الشركاء والموزعين (Partner):** ${config.PRICES['reseller']['usd']} / {config.PRICES['reseller']['egp']} EGP\n\n"
                "📌 **وسائل الدفع المتاحة:**\n"
                f"📱 فودافون كاش / إنستا باي: `{config.PAYMENT_INFO['VODAFONE_CASH']}`\n"
                f"🌐 Binance / USDT (TRC20): `{config.PAYMENT_INFO['BINANCE_PAY']}`\n\n"
                "بعد الدفع، اضغط على زر **إرسال إيصال الدفع** ليتم إرسال السيريال لك فوراً!"
            )
            keyboard = [
                [InlineKeyboardButton("📤 إرسال إيصال الدفع للأدمن", callback_data="send_receipt")],
                [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
            ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "send_receipt":
        if lang == 'en':
            text = (
                "📩 **Please send your payment screenshot & requested plan name here in chat.**\n\n"
                f"Or contact Admin directly: {config.PAYMENT_INFO['ADMIN_CONTACT']}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Plans", callback_data="buy")]]
        else:
            text = (
                "📩 **يرجى كتابة اسم الباقة المطلوبة مع إرفاق صورة الإيصال هنا في الشات.**\n\n"
                f"أو يمكنك إرسال الإيصال مباشرة للأدمن: {config.PAYMENT_INFO['ADMIN_CONTACT']}"
            )
            keyboard = [[InlineKeyboardButton("🔙 العودة للباقات", callback_data="buy")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "download":
        if lang == 'en':
            text = (
                "📥 **OFFICIAL DOWNLOAD PORTAL:**\n\n"
                "You can validate your active serial key & download the extension zip package instantly via our official portal:\n"
                f"🔗 {config.DOWNLOAD_LINK}\n\n"
                "Enter your key on the site to download your build."
            )
            keyboard = [
                [InlineKeyboardButton("🌐 Open Website Download Portal", url="https://www.lovaextreme.online/download")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
        else:
            text = (
                "📥 **بوابة التحميل الرسمية للإكستنشن:**\n\n"
                "يمكنك فحص وتفعيل السيريال الخاص بك وتنزيل ملف الإكستنشن فورياً عبر موقعنا الرسمي:\n"
                f"🔗 {config.DOWNLOAD_LINK}\n\n"
                "أدخل السيريال في الموقع ليبدأ التحميل تلقائياً!"
            )
            keyboard = [
                [InlineKeyboardButton("🌐 فتح بوابة التحميل بالموقع", url="https://www.lovaextreme.online/download")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
            ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "faq":
        if lang == 'en':
            text = (
                "📘 **INSTALLATION & ACTIVATION GUIDE:**\n\n"
                "1️⃣ Download & unzip the extension package.\n"
                "2️⃣ Open `chrome://extensions` and enable Developer Mode.\n"
                "3️⃣ Click 'Load Unpacked' and select the unzipped folder.\n"
                "4️⃣ Enter your active key into the extension popup.\n\n"
                "⚠️ Each license key is bound to 1 PC/Device."
            )
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        else:
            text = (
                "📘 **دليل التثبيت والأسئلة الشائعة:**\n\n"
                "1️⃣ قم بفك الضغط عن ملف الإكستنشن.\n"
                "2️⃣ افتح `chrome://extensions` وفعّل Developer Mode.\n"
                "3️⃣ اضغط على Load Unpacked واختر المجلد.\n"
                "4️⃣ أدخل السيريال في نافذة الإكستنشن للبدء.\n\n"
                "⚠️ السيريال يعمل على جهاز واحد فقط."
            )
            keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "support":
        if lang == 'en':
            text = f"💬 **HUMAN SUPPORT & ASSISTANCE:**\n\nDirect contact with LOVAEXTREME Founder & Admin:\n👉 {config.PAYMENT_INFO['ADMIN_CONTACT']}"
            keyboard = [
                [InlineKeyboardButton("💬 Open Chat with Admin (@boodymasoud)", url="https://t.me/boodymasoud")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
        else:
            text = f"💬 **الدعم الفني والتواصل المباشر:**\n\nتواصل مباشر مع مؤسس وإدارة LOVAEXTREME:\n👉 {config.PAYMENT_INFO['ADMIN_CONTACT']}"
            keyboard = [
                [InlineKeyboardButton("💬 فتح شات مباشر مع الأدمن (@boodymasoud)", url="https://t.me/boodymasoud")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
            ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ===========================================================================
# Admin Commands Handlers
# ===========================================================================

async def admin_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    days = 30
    plan_type = "monthly"
    name = "Customer"

    if context.args:
        if context.args[0].isdigit():
            days = int(context.args[0])
            plan_type = f"custom_{days}d" if days != 0 else "lifetime"
        if len(context.args) > 1:
            name = " ".join(context.args[1:])

    key, exp_display = generate_serial_supabase(days=days, plan_type=plan_type, user_name=name)
    if key:
        msg = (
            f"✅ **Serial Key Generated Successfully!**\n\n"
            f"🔑 **Key:** `{key}`\n"
            f"👤 **User:** {name}\n"
            f"📅 **Expires:** {exp_display}\n"
            f"🏷️ **Plan:** {plan_type}"
        )
    else:
        msg = "❌ Error generating serial key in Supabase."

    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_groupgen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
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
        await update.message.reply_text("❌ Error generating group key.")
        return

    msg = (
        f"🚀 **Group Trial Serial Key Generated!**\n\n"
        f"🔑 **Key:** `{key}`\n"
        f"⏱️ **Duration:** {hours} hours (Expires: {exp_dt.strftime('%H:%M %d/%m/%Y UTC')})\n"
        f"💻 **Max Devices:** {max_dev} Devices\n"
        f"🏷️ **Group Name:** {name}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_devices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/devices GRP-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}&limit=1")

    if not res or len(res) == 0:
        await update.message.reply_text(f"❌ Key not found: `{key}`", parse_mode="Markdown")
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
        f"📊 **Group Serial Devices Status:**\n\n"
        f"🔑 **Key:** `{key}`\n"
        f"💻 **Active Devices:** {len(dev_list)} / {max_dev}\n"
        f"📌 **Status:** {item.get('status')}\n\n"
    )

    if dev_list:
        msg += "📋 **Device IDs:**\n"
        for idx, d in enumerate(dev_list[:20], 1):
            did = d.get('id') if isinstance(d, dict) else str(d)
            msg += f"{idx}. `{did[:15]}...`\n"
    else:
        msg += "ℹ️ No registered devices yet."

    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/check LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}&limit=1")

    if not res or len(res) == 0:
        await update.message.reply_text(f"❌ Key not found: `{key}`", parse_mode="Markdown")
        return

    item = res[0]
    hwid = item.get('device_id') or 'Unbound (Free)'
    msg = (
        f"📋 **Serial Key Details:**\n\n"
        f"🔑 **Key:** `{item.get('key')}`\n"
        f"📌 **Status:** {item.get('status')}\n"
        f"📅 **Expires:** {item.get('expires_at')}\n"
        f"🏷️ **Plan:** {item.get('plan')}\n"
        f"💻 **HWID Device:** `{hwid}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/reset LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}", method="PATCH", data={"device_id": ""})

    if res is not None:
        await update.message.reply_text(f"✅ Unbound device for key: `{key}` successfully!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Failed to unbind key: `{key}`", parse_mode="Markdown")

async def admin_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/revoke LOVA-XXXX-YYYY`", parse_mode="Markdown")
        return

    key = context.args[0].strip()
    encoded_key = urllib.parse.quote(key)
    res = supabase_request(f"licenses?key=eq.{encoded_key}", method="PATCH", data={"status": "revoked"})

    if res is not None:
        await update.message.reply_text(f"🛑 Key `{key}` revoked & frozen!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Failed to revoke key: `{key}`", parse_mode="Markdown")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin command only.")
        return

    res = supabase_request("licenses?select=user_name,plan,created_at,status")
    if res is None:
        await update.message.reply_text("❌ Supabase connection error.")
        return

    total_keys = len(res)
    trials = [r for r in res if r.get('plan') == 'trial_15m' or 'trial' in str(r.get('plan')).lower()]
    unique_tg_users = set(r.get('user_name') for r in trials if r.get('user_name'))
    paid_keys = [r for r in res if r.get('plan') != 'trial_15m' and 'trial' not in str(r.get('plan')).lower()]

    msg = (
        f"📊 **تقارير وإحصائيات مستخدمي البوت الإجمالية:**\n\n"
        f"👥 **عدد الأشخاص الذين طلبوا تجربة مجانية:** {len(unique_tg_users)} مستخدم\n"
        f"🎁 **إجمالي التجارب المجانية المصدرة:** {len(trials)} تجربة\n"
        f"💳 **إجمالي الاشتراكات المدفوعة:** {len(paid_keys)} سيريال\n"
        f"🔢 **إجمالي السيريالات المسجلة بالداتابيز:** {total_keys}\n\n"
        f"📋 **آخر مستخدمين طلبوا تجربة:**\n"
    )
    for r in list(trials)[-7:]:
        msg += f"• `{r.get('user_name')}` ({r.get('status')})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_stats(update, context)

# ===========================================================================
# Main Function
# ===========================================================================

def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("⚠️ Please set your TELEGRAM_BOT_TOKEN in config.py before running!")
        return

    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # User Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))

    # Admin Commands
    app.add_handler(CommandHandler("gen", admin_gen))
    app.add_handler(CommandHandler("groupgen", admin_groupgen))
    app.add_handler(CommandHandler("devices", admin_devices))
    app.add_handler(CommandHandler("check", admin_check))
    app.add_handler(CommandHandler("reset", admin_reset))
    app.add_handler(CommandHandler("revoke", admin_revoke))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))

    # Callback Query Router
    app.add_handler(CallbackQueryHandler(button_handler))

    print(f"🤖 LOVAEXTREME Telegram Bot is running & connected to Supabase ({config.SUPABASE_URL})...")
    app.run_polling()

if __name__ == "__main__":
    main()
