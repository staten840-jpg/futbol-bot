import os
import logging
import requests
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from groq import Groq

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)

HOME_TEAM, AWAY_TEAM = range(2)

SPORTAPI_HOST = "sportapi7.p.rapidapi.com"
SPORTAPI_BASE = "https://sportapi7.p.rapidapi.com/api/v1"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": SPORTAPI_HOST
}

def search_team(team_name):
    try:
        url = f"{SPORTAPI_BASE}/search/teams/{team_name}/sport/football"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("teams"):
            team = data["teams"][0]
            return team["id"], team["name"]
    except Exception as e:
        logger.error(f"Team search error: {e}")
    return None, None

def get_recent_matches(team_id):
    try:
        url = f"{SPORTAPI_BASE}/team/{team_id}/events/last/0"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        matches = data.get("events", [])[:5]
        results = []
        for m in matches:
            home = m.get("homeTeam", {}).get("name", "")
            away = m.get("awayTeam", {}).get("name", "")
            hs = m.get("homeScore", {}).get("current", 0)
            as_ = m.get("awayScore", {}).get("current", 0)
            results.append(f"{home} {hs}-{as_} {away}")
        return results
    except Exception as e:
        logger.error(f"Recent matches error: {e}")
    return []

def analyze_match(home_team, away_team, home_form, away_form):
    home_form_str = "\n".join(home_form) if home_form else "Ma'lumot yo'q"
    away_form_str = "\n".join(away_form) if away_form else "Ma'lumot yo'q"

    prompt = f"""Siz professional futbol analitikiсиз. Quyidagi real ma'lumotlar asosida SofaScore Analyst uslubida to'liq o'yin tahlili bering. O'zbek tilida javob bering.

UYDA O'YNAYDIGAN JAMOA: {home_team}
SO'NGI 5 O'YIN:
{home_form_str}

MEHMON JAMOA: {away_team}
SO'NGI 5 O'YIN:
{away_form_str}

Quyidagi bo'limlarni yozing:

⚽ **UMUMIY PROGNOZ**
- G'olib ehtimoli: {home_team} ?% | Durang ?% | {away_team} ?%
- Eng ehtimoliy natija: ?-?
- Ikki jamoa ham gol uradi: Ha/Yo'q (?%)

📊 **JORIY FORMA**

⚔️ **YUZMA-YUZ STATISTIKA**

🎯 **TAKTIKA VA ASOSIY O'YINCHILAR**

🟨 **KARTOCHKALAR VA BURCHAKLAR**

📝 **YAKUNIY PROGNOZ**"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7
    )
    return response.choices[0].message.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏟️ *Futbol AI Analitika Bot*\n\nO'yin tahlili uchun /tahlil yuboring.",
        parse_mode="Markdown"
    )

async def tahlil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 *Uy egasi jamoasi* nomini yozing:\n_(Masalan: Real Madrid)_",
        parse_mode="Markdown"
    )
    return HOME_TEAM

async def get_home_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    team_name = update.message.text.strip()
    await update.message.reply_text("🔍 Qidirilmoqda...")
    team_id, found_name = search_team(team_name)
    if not team_id:
        await update.message.reply_text(f"❌ '{team_name}' topilmadi. Qayta yozing:")
        return HOME_TEAM
    context.user_data['home_id'] = team_id
    context.user_data['home_name'] = found_name
    await update.message.reply_text(
        f"✅ *{found_name}* topildi!\n\n✈️ *Mehmon jamoasi* nomini yozing:",
        parse_mode="Markdown"
    )
    return AWAY_TEAM

async def get_away_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    team_name = update.message.text.strip()
    await update.message.reply_text("🔍 Qidirilmoqda...")
    team_id, found_name = search_team(team_name)
    if not team_id:
        await update.message.reply_text(f"❌ '{team_name}' topilmadi. Qayta yozing:")
        return AWAY_TEAM
    context.user_data['away_id'] = team_id
    context.user_data['away_name'] = found_name
    home_name = context.user_data['home_name']
    home_id = context.user_data['home_id']
    await update.message.reply_text(
        f"⏳ *{home_name} vs {found_name}* tahlil qilinmoqda...",
        parse_mode="Markdown"
    )
    try:
        home_form = get_recent_matches(home_id)
        away_form = get_recent_matches(team_id)
        analysis = analyze_match(home_name, found_name, home_form, away_form)
        await update.message.reply_text(
            f"🔍 *{home_name} vs {found_name}*\n\n{analysis}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi. /tahlil bilan qayta urinib ko'ring.")
    await update.message.reply_text("🔄 Yangi tahlil: /tahlil")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("tahlil", tahlil_start)],
        states={
            HOME_TEAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_team)],
            AWAY_TEAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_away_team)],
        },
        fallbacks=[CommandHandler("bekor", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

