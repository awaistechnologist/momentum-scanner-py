# Setting Up Telegram Notifications

The Momentum Scanner can send real-time alerts to your Telegram app. Here is how to set it up.

## 1. Create a Bot (Get Bot Token)

1.  Open Telegram and search for **@BotFather**.
2.  Start a chat and send the command `/newbot`.
3.  Follow the instructions to name your bot (e.g., `MyScannerBot`).
4.  **BotFather** will give you a **HTTP API Token**. It looks like this:
    `123456789:ABCdefGHIjklMNOpqrsTUVwxYZ`
    *   **Copy this token.** This is your `bot_token`.

## 2. Get Your Chat ID

1.  Search for your new bot in Telegram and click **Start**.
2.  Send a message (e.g., "Hello") to your bot.
3.  Visit the following URL in your browser (replace `<YOUR_BOT_TOKEN>` with the token you just got):
    `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4.  Look for a JSON response. Find the `"chat"` object inside `"result"`.
5.  The `id` number inside `"chat"` is your `chat_id` (e.g., `987654321`).

## 3. Configure the Scanner

Open your `config.json` file and add the `notifications` section:

```json
{
  "notifications": {
    "telegram": {
      "bot_token": "YOUR_BOT_TOKEN_HERE",
      "chat_id": "YOUR_CHAT_ID_HERE"
    }
  }
}
```

Now, when you run the scanner or click "Send to Telegram" in the UI, you will receive alerts!
