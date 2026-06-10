import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from groq import Groq

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

client = Groq(api_key=GROQ_API_KEY)

HOME_TEAM, AWAY_TEAM, HOME_STATS, AWAY_STATS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏟 Futbol AI Bot\n\nTahlil uchun /tahlil yozing")

async def tahlil_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏠 Uy egasi jamoasi nomini yozing:")
    return HOME_TEAM

async def get_home_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["home"] = update.message.text
    await update.message.reply_text("✈️ Mehmon jamoasi nomini yozing:")
    return AWAY_TEAM

async def get_away_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["away"] = update.message.text
    await update.message.reply_text(f"📋 {context.user_data['home']} haqida ma'lumot yozing:\n(forma, o'rin, asosiy o'yinchilar)")
    return HOME_STATS

async def get_home_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["home_stats"] = update.message.text
    await update.message.reply_text(f"📋 {context.user_data['away']} haqida ma'lumot yozing:")
    return AWAY_STATS

async def get_away_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["away_stats"] = update.message.text
    home = context.user_data["home"]
    away = context.user_data["away"]
    await update.message.reply_text(f"⏳ {home} vs {away} tahlil qilinmoqda...")
    
    prompt = f"""Sen professional futbol analitikisen. O'zbek tilida SofaScore uslubida tahlil ber.

Uy egasi: {home}
Ma'lumot: {context.user_data['home_stats']}

Mehmon: {away}
Ma'lumot: {context.user_data['away_stats']}

Quyidagi bo'limlarni yoz:
⚽ UMUMIY PROGNOZ (g'olib ehtimoli %, eng ehtimoliy natija, ikki jamoa gol urish ehtimoli)
📊 JORIY FORMA
⚔️ TAKTIKA VA ASOSIY O'YINCHILAR
🟨 KARTOCHKALAR VA BURCHAKLAR
📝 YAKUNIY XULOSA"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500
    )
    
    await update.message.reply_text(response.choices[0].message.content)
    await update.message.reply_text("🔄 Yangi tahlil: /tahlil")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. /tahlil bilan qayta boshlang")
    return ConversationHandler.END

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("tahlil", tahlil_start)],
        states={
            HOME_TEAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_team)],
            AWAY_TEAM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_away_team)],
            HOME_STATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_home_stats)],
            AWAY_STATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_away_stats)],
        },
        fallbacks=[CommandHandler("bekor", cancel)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
