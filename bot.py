import sqlite3, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, filters, ContextTypes)
from config import BOT_TOKEN, ADMIN_CHAT_ID, WALLETS, RATES

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("orders.db", check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, username TEXT,
    amount_usd REAL, crypto TEXT, network TEXT,
    tx_hash TEXT, payment_method TEXT, payment_details TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()

IMG_SELL   = "https://i.ibb.co/RGFzwXtW/sell-crypto.jpg"
IMG_AMOUNT = "https://i.ibb.co/n87syS5S/amount.jpg"
IMG_BTC    = "https://i.ibb.co/9Hzs6FQ8/btc.jpg"
IMG_ETH    = "https://i.ibb.co/9HDXYhN3/eth.jpg"
IMG_USDT   = "https://i.ibb.co/7dLGsgNY/usdt.jpg"
IMG_WALLET = "https://i.ibb.co/LzKpGhLQ/wallet.jpg"
IMG_TXHASH = "https://i.ibb.co/HTXQCd5s/txhash.jpg"
IMG_UPI    = "https://i.ibb.co/Ps5FDwrp/upi.jpg"

def get_rate(amount):
    for low, high, rate in RATES:
        if low <= amount <= high:
            return rate
    return RATES[-1][2]

def get_inr(amount_usd):
    return round(amount_usd * get_rate(amount_usd), 2)

def validate_tx_hash(tx_hash, network):
    tx_hash = tx_hash.strip()
    if "ERC20" in network or "BEP20" in network or network == "ETH":
        return tx_hash.startswith("0x") and len(tx_hash) == 66
    elif "TRC20" in network or network == "BTC":
        return len(tx_hash) == 64
    elif "TON" in network or "SOL" in network:
        return len(tx_hash) >= 40
    else:
        return len(tx_hash) >= 40

def validate_upi(upi_id):
    upi_id = upi_id.strip()
    if "@" not in upi_id:
        return False
    parts = upi_id.split("@")
    if len(parts) != 2:
        return False
    if len(parts[0]) < 3 or len(parts[1]) < 2:
        return False
    return True

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💰 Sell Crypto", callback_data="sell"),
         InlineKeyboardButton("👥 Referral", callback_data="referral")],
        [InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
         InlineKeyboardButton("⚠️ Raise Dispute", callback_data="dispute")],
        [InlineKeyboardButton("🏦 Saved Payment", callback_data="payment"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🔧 Support", callback_data="support")],
    ]
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Welcome, {name}!\n\n"
        f"💱 VK Exchange Bot\n"
        f"Your trusted platform to sell crypto and receive INR instantly!\n\n"
        f"Choose an option below 👇",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "sell":
        ctx.user_data.clear()
        ctx.user_data["step"] = "amount"
        kb = [
            [InlineKeyboardButton("📊 Conversion Rates", callback_data="rates")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
        ]
        await q.message.reply_photo(
            photo=IMG_SELL,
            caption="💰 SELL CRYPTO\n\n"
                    "Fast, Safe and Secure\n\n"
                    "Enter the amount in USD 💵\n\n"
                    "Type your amount below 👇",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await q.message.delete()

    elif data == "rates":
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="sell")]]
        await q.edit_message_caption(
            caption="📊 Conversion Rates\n\n"
                    "━━━━━━━━━━━━━━━\n"
                    "💠 $10 - $580       =  Rs.98 per dollar\n"
                    "💠 $581 - $2300     =  Rs.99 per dollar\n"
                    "💠 $2301 - $5700    =  Rs.99 per dollar\n"
                    "💠 $5701 and above  =  Rs.100 per dollar\n"
                    "━━━━━━━━━━━━━━━\n\n"
                    "Rates are updated regularly",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "back_start":
        kb = [
            [InlineKeyboardButton("💰 Sell Crypto", callback_data="sell"),
             InlineKeyboardButton("👥 Referral", callback_data="referral")],
            [InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
             InlineKeyboardButton("⚠️ Raise Dispute", callback_data="dispute")],
            [InlineKeyboardButton("🏦 Saved Payment", callback_data="payment"),
             InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("🔧 Support", callback_data="support")],
        ]
        await q.edit_message_text(
            "💱 VK Exchange Bot\n\n"
            "Your trusted platform to sell crypto and receive INR instantly!\n\n"
            "Choose an option below 👇",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data.startswith("crypto_"):
        crypto = data.replace("crypto_", "")
        ctx.user_data["crypto"] = crypto
        if crypto == "USDT":
            kb = [
                [InlineKeyboardButton("USDT BEP20", callback_data="net_USDT_BEP20"),
                 InlineKeyboardButton("USDT TRC20", callback_data="net_USDT_TRC20")],
                [InlineKeyboardButton("USDT ERC20", callback_data="net_USDT_ERC20"),
                 InlineKeyboardButton("USDT TON", callback_data="net_USDT_TON")],
                [InlineKeyboardButton("USDT SOL", callback_data="net_USDT_SOL")],
                [InlineKeyboardButton("🔙 Back", callback_data="sell")]
            ]
            await q.message.reply_photo(
                photo=IMG_USDT,
                caption="🌐 SELECT NETWORK\n\n"
                        "Choose your USDT network carefully\n\n"
                        "⚠️ Sending on wrong network will result in loss of funds!",
                reply_markup=InlineKeyboardMarkup(kb)
            )
            await q.message.delete()
        elif crypto == "BTC":
            await show_wallet_photo(q, ctx, "BTC", IMG_BTC)
        elif crypto == "ETH":
            await show_wallet_photo(q, ctx, "ETH", IMG_ETH)

    elif data.startswith("net_"):
        network = data.replace("net_", "")
        ctx.user_data["network"] = network
        await show_wallet_photo(q, ctx, network, IMG_WALLET)

    elif data == "payment_upi":
        ctx.user_data["payment_method"] = "UPI"
        ctx.user_data["step"] = "awaiting_upi"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="sell")]]
        await q.message.reply_photo(
            photo=IMG_UPI,
            caption="📱 UPI PAYMENT\n\n"
                    "Enter your UPI ID below\n\n"
                    "Example: name@upi or 9999999999@paytm\n\n"
                    "Type your UPI ID 👇",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await q.message.delete()

    elif data == "payment_imps":
        ctx.user_data["payment_method"] = "IMPS"
        ctx.user_data["step"] = "awaiting_account"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="sell")]]
        await q.message.reply_photo(
            photo=IMG_UPI,
            caption="🏦 BANK TRANSFER IMPS\n\n"
                    "Enter your Bank Account Number below\n\n"
                    "Type your Account Number 👇",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        await q.message.delete()

    elif data == "my_orders":
        uid = q.from_user.id
        rows = conn.execute(
            "SELECT id, amount_usd, crypto, status, created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (uid,)
        ).fetchall()
        if not rows:
            await q.edit_message_text(
                "📋 My Orders\n\n"
                "You have no orders yet.\n\n"
                "Type /start to go back."
            )
        else:
            text = "📋 My Orders\n\n━━━━━━━━━━━━━━━\n"
            for r in rows:
                status_icon = "✅" if r[3] == "paid" else "❌" if r[3] == "rejected" else "⏳"
                text += f"{status_icon} #{r[0]} | ${r[1]} {r[2]} | {r[4][:10]}\n"
            text += "━━━━━━━━━━━━━━━\n\nType /start to go back."
            await q.edit_message_text(text)

    elif data == "support":
        await q.edit_message_text(
            "🔧 Support\n\n"
            "Having issues? We are here to help!\n\n"
            "📞 Contact: @ContactHandle\n\n"
            "Type /start to go back."
        )

    elif data == "dispute":
        await q.edit_message_text(
            "⚠️ Raise a Dispute\n\n"
            "If you have an issue with your order contact us with your Order ID\n\n"
            "📞 Contact: @ContactHandle\n\n"
            "Type /start to go back."
        )

    elif data == "referral":
        await q.edit_message_text(
            "👥 Referral Program\n\n"
            "Coming Soon!\n\n"
            "Stay tuned for exciting rewards 🎁\n\n"
            "Type /start to go back."
        )

    elif data == "stats":
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        paid = conn.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
        await q.edit_message_text(
            "📊 Stats\n\n"
            "━━━━━━━━━━━━━━━\n"
            f"📦 Total Orders:  {total}\n"
            f"✅ Completed:     {paid}\n"
            f"⏳ Pending:       {pending}\n"
            "━━━━━━━━━━━━━━━\n\n"
            "Type /start to go back."
        )

    elif data == "payment":
        await q.edit_message_text(
            "🏦 Saved Payment Details\n\n"
            "Coming Soon!\n\n"
            "Type /start to go back."
        )

async def show_wallet_photo(q, ctx, key, image):
    wallet = WALLETS.get(key)
    amount = ctx.user_data.get("amount_usd", 0)
    inr = get_inr(amount)
    ctx.user_data["network"] = key
    ctx.user_data["step"] = "awaiting_hash"

    caption = (
        f"👛 WALLET ADDRESS\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🪙 Crypto:  {key}\n"
        f"💵 Amount:  ${amount}\n"
        f"💰 You Get: Rs.{inr}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📋 Send to this address:\n\n"
        f"{wallet}\n\n"
        f"⚠️ Only send {key} to this address!\n\n"
        f"After payment paste your Transaction Hash here 👇"
    )
    kb = [[InlineKeyboardButton("🔙 Back", callback_data="sell")]]
    await q.message.reply_photo(
        photo=image,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(kb)
    )
    await q.message.delete()

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    step = ctx.user_data.get("step")
    text = update.message.text.strip()

    if step == "amount":
        try:
            amount = float(text)
            if amount < 10:
                await update.message.reply_text(
                    "❌ Minimum amount is $10\n\n"
                    "Please enter a higher amount."
                )
                return
            ctx.user_data["amount_usd"] = amount
            ctx.user_data["step"] = "crypto"
            rate = get_rate(amount)
            inr = get_inr(amount)
            kb = [
                [InlineKeyboardButton("₿ BTC", callback_data="crypto_BTC"),
                 InlineKeyboardButton("Ξ ETH", callback_data="crypto_ETH"),
                 InlineKeyboardButton("₮ USDT", callback_data="crypto_USDT")],
                [InlineKeyboardButton("🔙 Back", callback_data="sell")]
            ]
            await update.message.reply_photo(
                photo=IMG_AMOUNT,
                caption=f"💵 AMOUNT\n\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"💲 Amount:  ${amount}\n"
                        f"📈 Rate:    Rs.{rate} per dollar\n"
                        f"💰 You Get: Rs.{inr}\n"
                        f"━━━━━━━━━━━━━━━\n\n"
                        f"Select your Crypto 👇",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid Amount!\n\n"
                "Please enter a valid number like 100 or 500"
            )

    elif step == "awaiting_hash":
        network = ctx.user_data.get("network", "")
        if not validate_tx_hash(text, network):
            await update.message.reply_text(
                "❌ Invalid Transaction Hash!\n\n"
                "The hash you entered does not look correct.\n\n"
                "Please check your wallet transaction history and paste the correct hash 👇"
            )
            return
        ctx.user_data["tx_hash"] = text
        ctx.user_data["step"] = "awaiting_payment_method"
        kb = [
            [InlineKeyboardButton("📱 UPI", callback_data="payment_upi"),
             InlineKeyboardButton("🏦 Bank Transfer IMPS", callback_data="payment_imps")]
        ]
        await update.message.reply_photo(
            photo=IMG_TXHASH,
            caption="✅ TX HASH VERIFIED!\n\n"
                    "Your transaction hash looks valid\n\n"
                    "💳 How would you like to receive INR?\n\n"
                    "Choose your payment method below 👇",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif step == "awaiting_upi":
        if not validate_upi(text):
            await update.message.reply_text(
                "❌ Invalid UPI ID!\n\n"
                "UPI ID must be in format: name@upi\n\n"
                "Examples:\n"
                "✅ 9999999999@paytm\n"
                "✅ yourname@upi\n"
                "✅ yourname@okaxis\n\n"
                "Please enter a valid UPI ID 👇"
            )
            return
        ctx.user_data["payment_details"] = text
        await save_order(update, ctx)

    elif step == "awaiting_account":
        if not text.isdigit() or len(text) < 9 or len(text) > 18:
            await update.message.reply_text(
                "❌ Invalid Account Number!\n\n"
                "Account number must be 9 to 18 digits only\n\n"
                "Please enter a valid account number 👇"
            )
            return
        ctx.user_data["account_number"] = text
        ctx.user_data["step"] = "awaiting_ifsc"
        await update.message.reply_text(
            "✅ Account Number Saved!\n\n"
            "🏦 Now enter your IFSC Code 👇\n\n"
            "Example: SBIN0001234"
        )

    elif step == "awaiting_ifsc":
        if len(text) != 11 or not text[:4].isalpha():
            await update.message.reply_text(
                "❌ Invalid IFSC Code!\n\n"
                "IFSC must be 11 characters\n\n"
                "Example: SBIN0001234\n\n"
                "Please enter a valid IFSC Code 👇"
            )
            return
        ctx.user_data["ifsc"] = text.upper()
        ctx.user_data["step"] = "awaiting_holder"
        await update.message.reply_text(
            "✅ IFSC Code Saved!\n\n"
            "🏦 Now enter Account Holder Name 👇"
        )

    elif step == "awaiting_holder":
        if len(text) < 3:
            await update.message.reply_text(
                "❌ Invalid Name!\n\n"
                "Please enter your full name 👇"
            )
            return
        ctx.user_data["payment_details"] = (
            f"Account: {ctx.user_data.get('account_number')} | "
            f"IFSC: {ctx.user_data.get('ifsc')} | "
            f"Name: {text}"
        )
        await save_order(update, ctx)

async def save_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ud = ctx.user_data
    user = update.effective_user
    cursor = conn.execute(
        "INSERT INTO orders (user_id, username, amount_usd, crypto, network, tx_hash, payment_method, payment_details) VALUES (?,?,?,?,?,?,?,?)",
        (user.id, user.username, ud.get("amount_usd"), ud.get("crypto"),
         ud.get("network"), ud.get("tx_hash"), ud.get("payment_method"), ud.get("payment_details"))
    )
    conn.commit()
    order_id = cursor.lastrowid
    inr = get_inr(ud.get("amount_usd", 0))

    admin_text = (
        f"🔔 New Order #{order_id}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 User: @{user.username} ({user.id})\n"
        f"💵 Amount: ${ud.get('amount_usd')}\n"
        f"🪙 Crypto: {ud.get('network')}\n"
        f"🔗 TX Hash: {ud.get('tx_hash')}\n"
        f"💳 Payment: {ud.get('payment_method')}\n"
        f"📋 Details: {ud.get('payment_details')}\n"
        f"💰 INR to Pay: Rs.{inr}\n"
        f"━━━━━━━━━━━━━━━"
    )
    kb = [[
        InlineKeyboardButton("✅ Mark Paid", callback_data=f"paid_{order_id}_{user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}_{user.id}")
    ]]
    await ctx.bot.send_message(
        ADMIN_CHAT_ID, admin_text,
        reply_markup=InlineKeyboardMarkup(kb)
    )

    await update.message.reply_text(
        f"🧾 ORDER RECEIPT\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 Order ID:  #{order_id}\n"
        f"🪙 Crypto:    {ud.get('network')}\n"
        f"💵 Amount:    ${ud.get('amount_usd')}\n"
        f"💰 INR:       Rs.{inr}\n"
        f"💳 Payment:   {ud.get('payment_method')}\n"
        f"⏳ Status:    Pending\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"✅ Order Submitted Successfully!\n"
        f"We will verify and send Rs.{inr} within 30 minutes\n\n"
        f"Type /start to go back to menu."
    )
    ctx.user_data.clear()

async def admin_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_CHAT_ID:
        await q.answer("Not authorized.")
        return
    await q.answer()
    parts = q.data.split("_")
    action = parts[0]
    order_id = int(parts[1])
    user_id = int(parts[2])

    if action == "paid":
        conn.execute("UPDATE orders SET status='paid' WHERE id=?", (order_id,))
        conn.commit()
        await ctx.bot.send_message(
            user_id,
            f"🎉 Order #{order_id} Complete!\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ INR has been sent to your account!\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"Thank you for using VK Exchange Bot!\n"
            f"Come back anytime to sell more crypto 💰"
        )
        await q.edit_message_text(
            q.message.text + "\n\n✅ PAID - INR Sent"
        )

    elif action == "reject":
        conn.execute("UPDATE orders SET status='rejected' WHERE id=?", (order_id,))
        conn.commit()
        await ctx.bot.send_message(
            user_id,
            f"❌ Order #{order_id} Rejected\n\n"
            f"Your order could not be processed.\n\n"
            f"Please contact support: @YourSupportHandle"
        )
        await q.edit_message_text(
            q.message.text + "\n\n❌ REJECTED"
        )

def main():
    import asyncio
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(paid|reject)_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()