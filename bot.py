import os, sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = os.getenv("DB_PATH", "earnzone.db")

def init_db():
    with sqlite3.connect(DB) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, points INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, url TEXT NOT NULL, reward INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS claims(user_id INTEGER, task_id INTEGER, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(user_id, task_id));
        CREATE TABLE IF NOT EXISTS withdrawals(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT NOT NULL DEFAULT 'pending');
        """)

def user(uid):
    with sqlite3.connect(DB) as c:
        c.execute("INSERT OR IGNORE INTO users(id) VALUES (?)", (uid,))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user(update.effective_user.id)
    await update.message.reply_text(
        "স্বাগতম Earnzone12bot-এ!\n\n"
        "/balance — পয়েন্ট দেখুন\n/tasks — টাস্ক দেখুন\n"
        "/claim TASK_ID — টাস্ক শেষ করে রিভিউ চাইুন\n"
        "/withdraw POINTS — উত্তোলনের অনুরোধ\n/help — সাহায্য\n\n"
        "এটি ডেমো পয়েন্ট সিস্টেম। পয়েন্ট বাস্তব টাকা নয়; উত্তোলন অ্যাডমিন যাচাই করবেন।"
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; user(uid)
    with sqlite3.connect(DB) as c:
        points=c.execute("SELECT points FROM users WHERE id=?", (uid,)).fetchone()[0]
    await update.message.reply_text(f"আপনার পয়েন্ট: {points}")

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB) as c:
        rows=c.execute("SELECT id,title,url,reward FROM tasks WHERE active=1 ORDER BY id").fetchall()
    if not rows:
        await update.message.reply_text("এখন কোনো টাস্ক নেই। পরে আবার দেখুন।"); return
    await update.message.reply_text("\n".join(f"{i}. {title} — {reward} পয়েন্ট\n{url}\n/claim {i} দিয়ে রিভিউ চান" for i,title,url,reward in rows))

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; user(uid)
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("ব্যবহার: /claim TASK_ID"); return
    tid=int(context.args[0])
    with sqlite3.connect(DB) as c:
        task=c.execute("SELECT id FROM tasks WHERE id=? AND active=1",(tid,)).fetchone()
        if not task:
            await update.message.reply_text("টাস্ক আইডি পাওয়া যায়নি।"); return
        try:
            c.execute("INSERT INTO claims(user_id,task_id,status) VALUES(?,?,'pending')",(uid,tid))
        except sqlite3.IntegrityError:
            await update.message.reply_text("এই টাস্কের জন্য আপনার দাবি আগে জমা হয়েছে।"); return
    await update.message.reply_text("আপনার টাস্ক দাবি অ্যাডমিনের যাচাইয়ের জন্য জমা হয়েছে।")
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"টাস্ক দাবি: user={uid}, task={tid}\nApprove: /approveclaim {uid} {tid}")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; user(uid)
    if not context.args or not context.args[0].isdigit() or int(context.args[0]) < 1:
        await update.message.reply_text("ব্যবহার: /withdraw POINTS"); return
    amount=int(context.args[0])
    with sqlite3.connect(DB) as c:
        points=c.execute("SELECT points FROM users WHERE id=?",(uid,)).fetchone()[0]
        if amount > points:
            await update.message.reply_text("আপনার পয়েন্ট যথেষ্ট নয়।"); return
        c.execute("INSERT INTO withdrawals(user_id,amount) VALUES(?,?)",(uid,amount))
        wid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    await update.message.reply_text(f"উত্তোলনের অনুরোধ #{wid} জমা হয়েছে। অ্যাডমিন যাচাই করবেন; অনুমোদনের আগে টাকা পাঠানো নিশ্চিত নয়।")
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"উত্তোলন অনুরোধ #{wid}: user={uid}, points={amount}\nApprove: /approvewithdraw {wid}\nReject: /rejectwithdraw {wid}")

async def admin_addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("এই কমান্ড শুধু অ্যাডমিনের জন্য।"); return
    # /addtask REWARD | TITLE | URL
    raw=update.message.text.partition(" ")[2]
    parts=[p.strip() for p in raw.split("|",2)]
    if len(parts)!=3 or not parts[0].isdigit() or int(parts[0])<1:
        await update.message.reply_text("ব্যবহার: /addtask REWARD | TITLE | URL"); return
    with sqlite3.connect(DB) as c:
        c.execute("INSERT INTO tasks(title,url,reward) VALUES(?,?,?)",(parts[1],parts[2],int(parts[0])))
    await update.message.reply_text("টাস্ক যোগ হয়েছে।")

async def approveclaim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("এই কমান্ড শুধু অ্যাডমিনের জন্য।"); return
    if len(context.args)!=2 or not all(x.isdigit() for x in context.args):
        await update.message.reply_text("ব্যবহার: /approveclaim USER_ID TASK_ID"); return
    uid,tid=map(int,context.args)
    with sqlite3.connect(DB) as c:
        row=c.execute("SELECT status FROM claims WHERE user_id=? AND task_id=?",(uid,tid)).fetchone()
        reward=c.execute("SELECT reward FROM tasks WHERE id=?",(tid,)).fetchone()
        if not row or row[0]!="pending" or not reward:
            await update.message.reply_text("Pending দাবি পাওয়া যায়নি।"); return
        c.execute("UPDATE claims SET status='approved' WHERE user_id=? AND task_id=?",(uid,tid))
        c.execute("UPDATE users SET points=points+? WHERE id=?",(reward[0],uid))
    await update.message.reply_text("টাস্ক অনুমোদিত; পয়েন্ট যোগ হয়েছে।")
    await context.bot.send_message(uid, f"আপনার টাস্ক অনুমোদিত হয়েছে। +{reward[0]} পয়েন্ট।")

async def approvewithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await withdrawal_decision(update, context, "approved")

async def rejectwithdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await withdrawal_decision(update, context, "rejected")

async def withdrawal_decision(update, context, status):
    if update.effective_user.id != ADMIN_ID or not ADMIN_ID:
        await update.message.reply_text("এই কমান্ড শুধু অ্যাডমিনের জন্য।"); return
    if len(context.args)!=1 or not context.args[0].isdigit():
        await update.message.reply_text("ব্যবহার: /approvewithdraw ID অথবা /rejectwithdraw ID"); return
    wid=int(context.args[0])
    with sqlite3.connect(DB) as c:
        row=c.execute("SELECT user_id,amount,status FROM withdrawals WHERE id=?",(wid,)).fetchone()
        if not row or row[2]!="pending":
            await update.message.reply_text("Pending অনুরোধ পাওয়া যায়নি।"); return
        uid,amount,_=row
        if status=="approved":
            c.execute("UPDATE users SET points=points-? WHERE id=? AND points>=?",(amount,uid,amount))
            if c.total_changes==0:
                await update.message.reply_text("পয়েন্ট ব্যালেন্স পরিবর্তিত হয়েছে; আগে যাচাই করুন।"); return
        c.execute("UPDATE withdrawals SET status=? WHERE id=?",(status,wid))
    await update.message.reply_text(f"অনুরোধ #{wid} {status} করা হয়েছে।")
    await context.bot.send_message(uid, f"আপনার উত্তোলনের অনুরোধ #{wid} {status} হয়েছে। পেমেন্ট আলাদাভাবে যাচাই করুন।")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start /balance /tasks /claim TASK_ID /withdraw POINTS\nঅ্যাডমিন: /addtask REWARD | TITLE | URL, /approveclaim USER_ID TASK_ID, /approvewithdraw ID, /rejectwithdraw ID")

def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN environment variable সেট করুন।")
    init_db()
    app=Application.builder().token(TOKEN).build()
    for cmd,fn in [("start",start),("balance",balance),("tasks",tasks),("claim",claim),("withdraw",withdraw),("addtask",admin_addtask),("approveclaim",approveclaim),("approvewithdraw",approvewithdraw),("rejectwithdraw",rejectwithdraw),("help",help_cmd)]:
        app.add_handler(CommandHandler(cmd,fn))
    app.run_polling()

if __name__=="__main__":
    main()
