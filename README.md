# Earnzone12bot (starter)

Telegram task/reward points bot with admin-reviewed task claims and withdrawal requests.

## Setup
1. Create a bot with Telegram's `@BotFather`; keep its token secret.
2. Set environment variables `BOT_TOKEN` and `ADMIN_ID` (your numeric Telegram user ID).
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Run: `python bot.py`

## Commands
Users: `/start`, `/balance`, `/tasks`, `/claim TASK_ID`, `/withdraw POINTS`, `/help`
Admin: `/addtask REWARD | TITLE | URL`, `/approveclaim USER_ID TASK_ID`, `/approvewithdraw ID`, `/rejectwithdraw ID`

This starter awards demo points for tasks that an admin manually verifies. It does not verify ad views automatically, make payments, or guarantee earnings. Only list ads/tasks whose providers explicitly allow incentivized traffic. Before real payouts, add stronger transaction handling, logs, abuse prevention, a clear points-to-money policy, privacy notice, and payment-provider integration. Never request passwords, email OTPs, or account credentials. Do not commit bot tokens to GitHub.
