#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 بوت تيليجرام بالذكاء الاصطناعي - المتقدم
مدعوم بـ OpenRouter API + python-telegram-bot
"""

import os
import sys
import json
import logging
import requests
import asyncio
import threading
import subprocess
import time
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from telegram.constants import ParseMode, ChatAction

# ==================== ⚙️ الإعدادات ====================

BOT_TOKEN = "8665130508:AAGEyEejfZKHhqlH3uIIuGt2Nf9Bl2X6eKM"
ADMIN_ID = 8206539702

OPENROUTER_KEYS = [
    "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",
    "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",
]
current_key_index = 0

# ==================== 🔄 نظام التحديث ====================
WAITING_FOR_UPDATE = {}   # user_id -> True إذا كان ينتظر ملف التحديث
BOT_FILENAME = os.path.basename(__file__)  # اسم ملف البوت الحالي

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# النماذج المتاحة
MODELS = {
    "claude_sonnet": {
        "id": "anthropic/claude-sonnet-4-5",
        "name": "🟣 Claude Sonnet 4.5",
        "desc": "ذكي وسريع - الأفضل للاستخدام اليومي"
    },
    "claude_opus": {
        "id": "anthropic/claude-opus-4-5",
        "name": "💜 Claude Opus 4.5",
        "desc": "الأقوى على الإطلاق"
    },
    "gpt4o": {
        "id": "openai/gpt-4o",
        "name": "🟢 GPT-4o",
        "desc": "نموذج OpenAI المتقدم"
    },
    "gemini": {
        "id": "google/gemini-2.5-pro",
        "name": "🔵 Gemini 2.5 Pro",
        "desc": "نموذج Google القوي"
    },
    "llama": {
        "id": "meta-llama/llama-3.3-70b-instruct",
        "name": "🦙 Llama 3.3 70B",
        "desc": "نموذج Meta المفتوح"
    },
    "mistral_free": {
        "id": "mistralai/mistral-7b-instruct:free",
        "name": "🆓 Mistral 7B (مجاني)",
        "desc": "سريع ومجاني"
    },
}

# الشخصيات
PERSONAS = {
    "assistant": "أنت مساعد ذكاء اصطناعي متقدم وذكي جداً. تجيب بالعربية الفصحى بشكل واضح ومنظم وشامل.",
    "teacher": "أنت معلم خبير ومتحمس. تشرح المفاهيم بطريقة بسيطة ومبتكرة مع أمثلة واقعية. تشجع على التعلم.",
    "programmer": "أنت مبرمج خبير متخصص في جميع لغات البرمجة. تكتب كوداً نظيفاً وموثقاً مع شرح مفصل.",
    "writer": "أنت كاتب إبداعي موهوب. تكتب بأسلوب أدبي رائع وتساعد في الكتابة الإبداعية والتحرير.",
    "analyst": "أنت محلل بيانات وأعمال خبير. تحلل المواقف بعمق وتقدم رؤى استراتيجية قيمة.",
}

# ==================== 📊 قاعدة البيانات البسيطة ====================

DB_FILE = "bot_data.json"

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}, "stats": {"total_messages": 0, "total_users": 0}}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_user(db, user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "model": "claude_sonnet",
            "persona": "assistant",
            "history": [],
            "messages_count": 0,
            "joined": datetime.now().isoformat(),
            "name": "",
            "lang": "ar",
            "max_history": 20,
        }
    return db["users"][uid]

# ==================== 🔑 إدارة API ====================

def get_api_key():
    global current_key_index
    return OPENROUTER_KEYS[current_key_index % len(OPENROUTER_KEYS)]

def rotate_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(OPENROUTER_KEYS)
    logging.warning(f"🔄 تم تغيير API key إلى #{current_key_index}")

def ask_ai(messages: list, model_id: str, max_tokens: int = 2048) -> dict:
    """إرسال طلب للذكاء الاصطناعي"""
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram-ai-bot.app",
        "X-Title": "Telegram AI Bot Arabic",
    }
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code in (401, 402, 429):
            rotate_key()
            # إعادة المحاولة بالـ key الجديد
            headers["Authorization"] = f"Bearer {get_api_key()}"
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return {
            "text": data["choices"][0]["message"]["content"],
            "tokens": data.get("usage", {}).get("total_tokens", 0),
            "model": data.get("model", model_id),
        }
    except requests.exceptions.Timeout:
        return {"error": "⏱️ انتهت مهلة الانتظار، حاول مرة أخرى"}
    except Exception as e:
        return {"error": f"❌ خطأ: {str(e)[:200]}"}

# ==================== 🎨 تنسيق الرسائل ====================

def escape_md(text: str) -> str:
    """تحويل النص لـ MarkdownV2"""
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text

def format_response(text: str) -> str:
    """تنسيق الرد بشكل جميل"""
    # الحد الأقصى لرسالة تيليجرام
    if len(text) > 4000:
        text = text[:3990] + "\n\n✂️ *تم اختصار الرد...*"
    return text

# ==================== 📋 الأوامر ====================

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    db = load_db()
    u = get_user(db, user.id)
    u["name"] = user.full_name
    if user.id not in [int(k) for k in db["users"].keys() if k != str(user.id)]:
        db["stats"]["total_users"] += 1
    save_db(db)

    keyboard = [
        [
            InlineKeyboardButton("🤖 اختر النموذج", callback_data="menu_models"),
            InlineKeyboardButton("🎭 الشخصية", callback_data="menu_personas"),
        ],
        [
            InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
        ],
        [InlineKeyboardButton("❓ المساعدة", callback_data="help_menu")],
    ]

    welcome = f"""
🌟 *أهلاً {user.first_name}!*

أنا بوت الذكاء الاصطناعي المتقدم 🤖
مدعوم بأقوى نماذج AI في العالم!

🔥 *النموذج الحالي:* {MODELS[u['model']]['name']}
🎭 *الشخصية:* {get_persona_name(u['persona'])}
💬 *رسائلك:* {u['messages_count']}

✨ *ابدأ بكتابة أي رسالة أو استخدم القائمة:*
"""

    await update.message.reply_text(
        welcome,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    text = """
📚 *دليل استخدام البوت*

*الأوامر المتاحة:*
• /start - الصفحة الرئيسية
• /help - هذه المساعدة
• /model - تغيير نموذج AI
• /persona - تغيير شخصية البوت
• /clear - مسح سجل المحادثة
• /stats - إحصائياتك
• /ask [سؤال] - سؤال مباشر

*طريقة الاستخدام:*
فقط اكتب رسالتك وسيرد البوت فوراً! 💬

*مميزات البوت:*
✅ يتذكر سياق المحادثة
✅ 6+ نماذج AI مختلفة
✅ 5 شخصيات مختلفة
✅ يدعم العربية والإنجليزية
✅ يكتب الكود البرمجي
✅ يحلل ويترجم النصوص
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def clear_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """مسح سجل المحادثة"""
    db = load_db()
    u = get_user(db, update.effective_user.id)
    count = len(u["history"])
    u["history"] = []
    save_db(db)
    await update.message.reply_text(
        f"🗑️ تم مسح {count} رسالة من السجل!\n✨ المحادثة الجديدة جاهزة.",
        parse_mode=ParseMode.MARKDOWN,
    )

async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """إحصائيات المستخدم"""
    db = load_db()
    u = get_user(db, update.effective_user.id)
    joined = u.get("joined", "—")[:10]

    text = f"""
📊 *إحصائياتك الشخصية*

👤 *الاسم:* {u.get('name', 'غير محدد')}
💬 *إجمالي رسائلك:* {u['messages_count']}
🔄 *الرسائل في السجل:* {len(u['history']) // 2}
🤖 *النموذج المستخدم:* {MODELS[u['model']]['name']}
🎭 *الشخصية:* {get_persona_name(u['persona'])}
📅 *تاريخ الانضمام:* {joined}

📈 *إحصائيات البوت:*
👥 *إجمالي المستخدمين:* {len(db['users'])}
💌 *إجمالي الرسائل:* {db['stats']['total_messages']}
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def model_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """اختيار النموذج"""
    keyboard = build_models_keyboard()
    await update.message.reply_text(
        "🤖 *اختر نموذج الذكاء الاصطناعي:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )

async def persona_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """اختيار الشخصية"""
    keyboard = build_personas_keyboard()
    await update.message.reply_text(
        "🎭 *اختر شخصية البوت:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )

async def ask_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """سؤال مباشر /ask"""
    if not ctx.args:
        await update.message.reply_text("💡 الاستخدام: /ask [سؤالك هنا]")
        return
    question = " ".join(ctx.args)
    update.message.text = question
    await handle_message(update, ctx)

# ==================== 💬 معالج الرسائل ====================

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """معالجة كل رسالة نصية"""
    # أولاً: تحقق إذا كان ينتظر ملف تحديث (للأدمن)
    if update.message and update.message.document:
        handled = await handle_update_file(update, ctx)
        if handled:
            return

    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()

    if not text:
        return

    # إظهار "يكتب..."
    await ctx.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    db = load_db()
    u = get_user(db, user.id)

    # بناء رسائل المحادثة
    model_key = u.get("model", "claude_sonnet")
    model_id = MODELS[model_key]["id"]
    persona_key = u.get("persona", "assistant")
    system_prompt = PERSONAS[persona_key]

    # إضافة رسالة المستخدم للتاريخ
    u["history"].append({"role": "user", "content": text})

    # الحفاظ على التاريخ في حدود معقولة
    max_hist = u.get("max_history", 20)
    if len(u["history"]) > max_hist:
        u["history"] = u["history"][-max_hist:]

    messages = [{"role": "system", "content": system_prompt}] + u["history"]

    # إرسال للـ AI
    start_time = datetime.now()
    result = ask_ai(messages, model_id)
    elapsed = (datetime.now() - start_time).total_seconds()

    if "error" in result:
        await update.message.reply_text(result["error"])
        return

    ai_text = result["text"]
    tokens = result.get("tokens", 0)

    # حفظ رد AI في التاريخ
    u["history"].append({"role": "assistant", "content": ai_text})
    u["messages_count"] += 1
    db["stats"]["total_messages"] += 1
    save_db(db)

    # تنسيق الرد
    response = format_response(ai_text)

    # إضافة معلومات صغيرة
    info_line = f"\n\n`⚡ {elapsed:.1f}ث | 🎯 {tokens} token | {MODELS[model_key]['name']}`"

    final = response + info_line

    # إرسال الرد
    keyboard = [
        [
            InlineKeyboardButton("🔄 إعادة توليد", callback_data=f"regen_{update.message.message_id}"),
            InlineKeyboardButton("🗑️ مسح السجل", callback_data="clear_history"),
        ]
    ]

    try:
        await update.message.reply_text(
            final,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception:
        # في حالة فشل Markdown، أرسل كنص عادي
        await update.message.reply_text(
            response + f"\n\n⚡ {elapsed:.1f}ث | 🎯 {tokens} token",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

# ==================== 🔘 معالج الأزرار ====================

def build_models_keyboard():
    keyboard = []
    for key, model in MODELS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{model['name']} - {model['desc']}",
                callback_data=f"setmodel_{key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return keyboard

def build_personas_keyboard():
    names = {
        "assistant": "🤖 مساعد ذكي",
        "teacher": "📚 معلم خبير",
        "programmer": "💻 مبرمج محترف",
        "writer": "✍️ كاتب إبداعي",
        "analyst": "📊 محلل أعمال",
    }
    keyboard = []
    for key, name in names.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"setpersona_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return keyboard

def get_persona_name(key):
    names = {
        "assistant": "🤖 مساعد ذكي",
        "teacher": "📚 معلم خبير",
        "programmer": "💻 مبرمج محترف",
        "writer": "✍️ كاتب إبداعي",
        "analyst": "📊 محلل أعمال",
    }
    return names.get(key, "🤖 مساعد")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع الأزرار"""
    query = update.callback_query
    data = query.data

    # أزرار الأدمن
    if data.startswith("admin_"):
        await handle_admin_buttons(update, ctx)
        return

    await query.answer()
    user_id = query.from_user.id
    db = load_db()
    u = get_user(db, user_id)

    # ===== القوائم الرئيسية =====
    if data == "menu_models":
        keyboard = build_models_keyboard()
        await query.edit_message_text(
            "🤖 *اختر نموذج الذكاء الاصطناعي:*\n\nكل نموذج له مميزاته الخاصة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "menu_personas":
        keyboard = build_personas_keyboard()
        await query.edit_message_text(
            "🎭 *اختر شخصية البوت:*\n\nالشخصية تحدد أسلوب الرد:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "my_stats":
        joined = u.get("joined", "—")[:10]
        text = f"""
📊 *إحصائياتك*

💬 *رسائلك:* {u['messages_count']}
🔄 *الرسائل المحفوظة:* {len(u['history']) // 2}
🤖 *النموذج:* {MODELS[u['model']]['name']}
🎭 *الشخصية:* {get_persona_name(u['persona'])}
📅 *الانضمام:* {joined}

👥 *مستخدمو البوت:* {len(db['users'])}
💌 *إجمالي الرسائل:* {db['stats']['total_messages']}
"""
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "settings":
        text = f"""
⚙️ *الإعدادات الحالية*

🤖 النموذج: {MODELS[u['model']]['name']}
🎭 الشخصية: {get_persona_name(u['persona'])}
📝 حجم السجل: {u.get('max_history', 20)} رسالة
"""
        keyboard = [
            [
                InlineKeyboardButton("🤖 تغيير النموذج", callback_data="menu_models"),
                InlineKeyboardButton("🎭 تغيير الشخصية", callback_data="menu_personas"),
            ],
            [
                InlineKeyboardButton("📝 سجل قصير (10)", callback_data="hist_10"),
                InlineKeyboardButton("📝 سجل طويل (30)", callback_data="hist_30"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "help_menu":
        text = """
❓ *كيف تستخدم البوت؟*

1️⃣ اكتب أي رسالة مباشرة
2️⃣ غير النموذج حسب احتياجك
3️⃣ اختر الشخصية المناسبة
4️⃣ البوت يتذكر سياق المحادثة

*أمثلة:*
• "اشرح لي الخوارزميات"
• "اكتب كود Python لـ..."
• "ترجم هذا النص..."
• "حلل هذه البيانات..."
"""
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

    # ===== تغيير النموذج =====
    elif data.startswith("setmodel_"):
        model_key = data.replace("setmodel_", "")
        if model_key in MODELS:
            u["model"] = model_key
            save_db(db)
            keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_models")]]
            await query.edit_message_text(
                f"✅ *تم تغيير النموذج إلى:*\n{MODELS[model_key]['name']}\n\n{MODELS[model_key]['desc']}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
            )

    # ===== تغيير الشخصية =====
    elif data.startswith("setpersona_"):
        persona_key = data.replace("setpersona_", "")
        if persona_key in PERSONAS:
            u["persona"] = persona_key
            save_db(db)
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_personas")]]
            await query.edit_message_text(
                f"✅ *تم تغيير الشخصية إلى:*\n{get_persona_name(persona_key)}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
            )

    # ===== مسح السجل =====
    elif data == "clear_history":
        count = len(u["history"])
        u["history"] = []
        save_db(db)
        await query.edit_message_text(
            f"🗑️ تم مسح {count} رسالة!\n✨ ابدأ محادثة جديدة.",
            parse_mode=ParseMode.MARKDOWN,
        )

    # ===== إعادة توليد =====
    elif data.startswith("regen_"):
        if len(u["history"]) >= 2:
            # حذف آخر رد AI وإعادة الطلب
            last_user_msg = None
            for msg in reversed(u["history"]):
                if msg["role"] == "user":
                    last_user_msg = msg["content"]
                    break

            if last_user_msg:
                # إزالة آخر رد
                u["history"] = [m for m in u["history"] if not (m["role"] == "assistant" and m == u["history"][-1])]
                save_db(db)

                await query.edit_message_text("⏳ جاري إعادة التوليد...")

                model_id = MODELS[u["model"]]["id"]
                system_prompt = PERSONAS[u.get("persona", "assistant")]
                messages = [{"role": "system", "content": system_prompt}] + u["history"]

                result = ask_ai(messages, model_id)
                if "error" in result:
                    await query.edit_message_text(result["error"])
                    return

                ai_text = result["text"]
                u["history"].append({"role": "assistant", "content": ai_text})
                save_db(db)

                keyboard = [
                    [
                        InlineKeyboardButton("🔄 إعادة توليد", callback_data=f"regen_new"),
                        InlineKeyboardButton("🗑️ مسح السجل", callback_data="clear_history"),
                    ]
                ]
                await query.edit_message_text(
                    format_response(ai_text),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

    # ===== حجم السجل =====
    elif data == "hist_10":
        u["max_history"] = 10
        save_db(db)
        await query.answer("✅ تم: سجل 10 رسائل")

    elif data == "hist_30":
        u["max_history"] = 30
        save_db(db)
        await query.answer("✅ تم: سجل 30 رسالة")

    # ===== رجوع للرئيسية =====
    elif data == "back_main":
        keyboard = [
            [
                InlineKeyboardButton("🤖 اختر النموذج", callback_data="menu_models"),
                InlineKeyboardButton("🎭 الشخصية", callback_data="menu_personas"),
            ],
            [
                InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
            ],
            [InlineKeyboardButton("❓ المساعدة", callback_data="help_menu")],
        ]
        await query.edit_message_text(
            f"🏠 *القائمة الرئيسية*\n\n🤖 النموذج: {MODELS[u['model']]['name']}\n🎭 الشخصية: {get_persona_name(u['persona'])}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
        )

# ==================== 👑 أوامر الأدمن ====================

def build_admin_keyboard():
    return [
        [
            InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton("📢 رسالة جماعية", callback_data="admin_broadcast_btn"),
            InlineKeyboardButton("🔑 حالة API", callback_data="admin_api"),
        ],
        [
            InlineKeyboardButton("🔄 تحديث البوت", callback_data="admin_update"),
        ],
    ]

async def admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الأدمن"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر للمشرف فقط!")
        return

    db = load_db()
    users = db["users"]

    text = f"""
👑 *لوحة تحكم الأدمن*

📊 إجمالي المستخدمين: *{len(users)}*
💬 إجمالي الرسائل: *{db['stats']['total_messages']}*
📁 ملف البوت: `{BOT_FILENAME}`
🕐 الوقت: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

اختر من القائمة:
"""
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(build_admin_keyboard()),
        parse_mode=ParseMode.MARKDOWN,
    )

async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة لجميع المستخدمين"""
    if update.effective_user.id != ADMIN_ID:
        return

    if not ctx.args:
        await update.message.reply_text("الاستخدام: /broadcast [الرسالة]")
        return

    msg = " ".join(ctx.args)
    db = load_db()
    count = 0
    failed = 0

    await update.message.reply_text(f"📤 جاري الإرسال لـ {len(db['users'])} مستخدم...")

    for uid in db["users"]:
        try:
            await ctx.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *رسالة من المشرف:*\n\n{msg}",
                parse_mode=ParseMode.MARKDOWN,
            )
            count += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ تم الإرسال!\n📤 ناجح: {count}\n❌ فشل: {failed}"
    )

async def userlist_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """قائمة المستخدمين"""
    if update.effective_user.id != ADMIN_ID:
        return

    db = load_db()
    text = "👥 *قائمة المستخدمين:*\n\n"

    for uid, u in list(db["users"].items())[:20]:
        text += f"• {u.get('name', 'مجهول')} | ID: `{uid}` | رسائل: {u['messages_count']}\n"

    if len(db["users"]) > 20:
        text += f"\n... و {len(db['users']) - 20} مستخدم آخر"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ==================== 🔄 نظام التحديث ====================

async def handle_update_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """استقبال ملف التحديث من الأدمن"""
    user_id = update.effective_user.id

    # تجاهل إذا لم يكن ينتظر تحديث
    if not WAITING_FOR_UPDATE.get(user_id):
        return False

    # تحقق أن المرسل أدمن
    if user_id != ADMIN_ID:
        return False

    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ أرسل ملف Python فقط!")
        return True

    # تحقق من اسم الملف
    if doc.file_name != BOT_FILENAME:
        await update.message.reply_text(
            f"❌ *اسم الملف غلط!*\n\n"
            f"المطلوب: `{BOT_FILENAME}`\n"
            f"المرسل: `{doc.file_name}`\n\n"
            f"أرسل الملف باسم صح أو اضغط /admin للإلغاء",
            parse_mode=ParseMode.MARKDOWN,
        )
        return True

    # تحقق امتداد .py
    if not doc.file_name.endswith(".py"):
        await update.message.reply_text("❌ يجب أن يكون الملف بامتداد .py")
        return True

    msg = await update.message.reply_text("⏳ *جاري تحميل الملف...*", parse_mode=ParseMode.MARKDOWN)

    try:
        # تحميل الملف من تيليجرام
        file = await ctx.bot.get_file(doc.file_id)
        new_code = await file.download_as_bytearray()
        new_code_str = new_code.decode("utf-8")

        # تحقق أن الملف يحتوي كود Python صالح
        try:
            compile(new_code_str, BOT_FILENAME, "exec")
        except SyntaxError as e:
            await msg.edit_text(
                f"❌ *خطأ في الكود!*\n\n`{str(e)}`\n\nتحقق من الكود وأعد الإرسال.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return True

        # نسخ احتياطي للملف القديم
        backup_name = f"{BOT_FILENAME}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_file = os.path.abspath(__file__)
        with open(current_file, "r", encoding="utf-8") as f:
            old_code = f.read()
        with open(backup_name, "w", encoding="utf-8") as f:
            f.write(old_code)

        await msg.edit_text("✅ *تم التحقق من الكود...*\n⚙️ جاري تطبيق التحديث...", parse_mode=ParseMode.MARKDOWN)

        # كتابة الكود الجديد
        with open(current_file, "w", encoding="utf-8") as f:
            f.write(new_code_str)

        # مسح حالة الانتظار
        WAITING_FOR_UPDATE.pop(user_id, None)

        await msg.edit_text(
            f"✅ *تم التحديث بنجاح!*\n\n"
            f"📁 الملف: `{BOT_FILENAME}`\n"
            f"💾 النسخة الاحتياطية: `{backup_name}`\n\n"
            f"🔄 *جاري إعادة تشغيل البوت...*",
            parse_mode=ParseMode.MARKDOWN,
        )

        await asyncio.sleep(2)

        # إعادة التشغيل
        logging.info("🔄 إعادة تشغيل البوت بعد التحديث...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        await msg.edit_text(
            f"❌ *فشل التحديث!*\n\n`{str(e)}`",
            parse_mode=ParseMode.MARKDOWN,
        )
        WAITING_FOR_UPDATE.pop(user_id, None)

    return True


async def handle_admin_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة الأدمن"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        await query.answer("⛔ للمشرف فقط!", show_alert=True)
        return

    db = load_db()

    if data == "admin_stats":
        text = f"""
📊 *إحصائيات مفصلة*

👥 المستخدمين: *{len(db['users'])}*
💬 إجمالي الرسائل: *{db['stats']['total_messages']}*
🕐 الآن: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
📁 الملف: `{BOT_FILENAME}`
🐍 Python: `{sys.version.split()[0]}`
"""
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_users":
        text = "👥 *آخر المستخدمين:*\n\n"
        for uid, u in list(db["users"].items())[:15]:
            text += f"• `{u.get('name','مجهول')}` | رسائل: {u['messages_count']}\n"
        if len(db["users"]) > 15:
            text += f"\n_...و {len(db['users'])-15} آخرين_"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_api":
        text = f"""
🔑 *حالة API Keys*

• Key 1: `...{OPENROUTER_KEYS[0][-8:]}`
• Key 2: `...{OPENROUTER_KEYS[1][-8:]}`
• ✅ النشط الآن: *Key #{current_key_index + 1}*
"""
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_broadcast_btn":
        text = "📢 *إرسال رسالة جماعية*\n\nاستخدم الأمر:\n`/broadcast رسالتك هنا`"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_update":
        # تفعيل وضع انتظار الملف
        WAITING_FOR_UPDATE[user_id] = True
        text = f"""
🔄 *تحديث البوت*

أرسل الآن ملف البوت الجديد بنفس الاسم:

📁 الاسم المطلوب: `{BOT_FILENAME}`

⚠️ *ملاحظات:*
• الملف لازم يكون بنفس الاسم بالضبط
• سيتم عمل نسخة احتياطية تلقائياً
• البوت سيُعاد تشغيله بعد التحديث

اضغط /admin لإلغاء العملية
"""
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="admin_update_cancel")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_update_cancel":
        WAITING_FOR_UPDATE.pop(user_id, None)
        text = "❌ *تم إلغاء التحديث*"
        keyboard = [[InlineKeyboardButton("🔙 رجوع للوحة", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "admin_back":
        db2 = load_db()
        text = f"""
👑 *لوحة تحكم الأدمن*

📊 إجمالي المستخدمين: *{len(db2['users'])}*
💬 إجمالي الرسائل: *{db2['stats']['total_messages']}*
📁 ملف البوت: `{BOT_FILENAME}`
🕐 الوقت: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

اختر من القائمة:
"""
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(build_admin_keyboard()),
            parse_mode=ParseMode.MARKDOWN,
        )

# ==================== 🚀 تشغيل البوت ====================

async def post_init(application):
    """إعداد أوامر البوت"""
    commands = [
        BotCommand("start", "الصفحة الرئيسية"),
        BotCommand("help", "المساعدة"),
        BotCommand("model", "تغيير النموذج"),
        BotCommand("persona", "تغيير الشخصية"),
        BotCommand("clear", "مسح سجل المحادثة"),
        BotCommand("stats", "إحصائياتي"),
        BotCommand("ask", "سؤال مباشر"),
    ]
    await application.bot.set_my_commands(commands)
    logging.info("✅ تم إعداد الأوامر")

def main():
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )

    logging.info("🚀 جاري تشغيل البوت...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # أوامر عامة
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("model", model_cmd))
    app.add_handler(CommandHandler("persona", persona_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))

    # أوامر الأدمن
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("userlist", userlist_cmd))

    # معالج ملفات التحديث (الأدمن فقط)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_update_file))

    # الأزرار
    app.add_handler(CallbackQueryHandler(button_handler))

    # الرسائل النصية
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("✅ البوت يعمل! اضغط Ctrl+C للإيقاف")
    print("\n" + "="*50)
    print("🤖 بوت الذكاء الاصطناعي يعمل الآن!")
    print(f"👑 الأدمن ID: {ADMIN_ID}")
    print(f"🔑 عدد API Keys: {len(OPENROUTER_KEYS)}")
    print("="*50 + "\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
