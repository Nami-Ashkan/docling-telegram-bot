# Docling Telegram PDF-to-AI Bot

A Telegram bot that receives PDF files, extracts their content using [Docling](https://github.com/DS4SD/docling), and returns clean text or Markdown suitable for AI tools.

The extracted output is easier for large language models to read, summarize, search, and analyze than the original PDF.

Typical use cases include:

* Preparing research papers for ChatGPT, Claude, Gemini, or local LLMs
* Converting PDFs into structured Markdown
* Extracting headings, lists, tables, and document sections
* Preparing documents for RAG pipelines
* Creating searchable text versions of PDFs
* Archiving uploaded PDFs separately for each Telegram user

---

## Features

* Accepts PDF documents through Telegram
* Converts PDFs using Docling
* Returns extracted content as `.txt` or `.md`
* Stores uploaded files separately for each Telegram user
* Stores the extracted output beside the original PDF
* Uses timestamped filenames to prevent overwriting
* Supports public or restricted access
* Reads bot settings from `config.json`
* Supports normal command-line PDF conversion
* Uses a project-local Python virtual environment
* Can run automatically at Ubuntu startup using `systemd`

---

## Folder Structure

The project structure should look like this:

```text
docling-telegram-bot/
├── .venv/
├── config.json
├── config.json.example
├── main.py
├── requirements.txt
├── run.sh
├── .gitignore
└── output/
```

After users send PDFs, the output structure will look similar to:

```text
output/
├── user_123456789/
│   ├── user_info.json
│   ├── 20260731_120501_msg45_document.pdf
│   └── 20260731_120501_msg45_document.txt
│
└── user_987654321/
    ├── user_info.json
    ├── 20260731_121030_msg18_report.pdf
    └── 20260731_121030_msg18_report.txt
```

Each Telegram user receives a separate folder based on their numeric Telegram user ID.

---

# 1. Requirements

You need:

* Ubuntu or another Linux distribution
* Python 3
* `python3-venv`
* Internet access
* A Telegram account
* A Telegram bot token from BotFather

Install the required Ubuntu packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

---

# 2. Clone the Repository

Clone the project:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/docling-telegram-bot.git
```

Enter the project directory:

```bash
cd docling-telegram-bot
```

Replace `YOUR_GITHUB_USERNAME` with your GitHub username.

---

# 3. Create the Python Virtual Environment

Create a virtual environment inside the project:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Upgrade Python packaging tools:

```bash
python3 -m pip install --upgrade pip setuptools wheel
```

---

# 4. Install Dependencies

Install the required packages:

```bash
python3 -m pip install docling "python-telegram-bot>=22,<23"
```

Alternatively, install from `requirements.txt`:

```bash
python3 -m pip install -r requirements.txt
```

Example `requirements.txt`:

```text
docling
python-telegram-bot>=22,<23
```

Verify the installation:

```bash
python3 -c "import docling, telegram; print('Docling installed'); print('Telegram version:', telegram.__version__)"
```

Deactivate the virtual environment when finished:

```bash
deactivate
```

The `run.sh` script uses `.venv/bin/python3` automatically, so manual activation is not required when running the bot.

---

# 5. Make the Shell Script Executable

Run:

```bash
chmod +x run.sh
```

The script should use the Python interpreter inside the project virtual environment.

Example `run.sh`:

```bash
#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python3"
MAIN="$SCRIPT_DIR/main.py"

if [[ ! -x "$PYTHON" ]]; then
    echo "Virtual environment Python was not found:"
    echo "$PYTHON"
    echo
    echo "Create the virtual environment with:"
    echo "  cd \"$SCRIPT_DIR\""
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/python3 -m pip install --upgrade pip"
    echo "  .venv/bin/python3 -m pip install -r requirements.txt"
    exit 1
fi

exec "$PYTHON" "$MAIN" "$@"
```

---

# 6. Test Command-Line PDF Conversion

Before setting up Telegram, confirm that Docling conversion works.

Run:

```bash
./run.sh /full/path/to/document.pdf
```

Example:

```bash
./run.sh /home/yourusername/Documents/example.pdf
```

The script should create:

```text
/home/yourusername/Documents/example.txt
```

To create Markdown output:

```bash
./run.sh /home/yourusername/Documents/example.pdf --format md
```

To specify a custom output path:

```bash
./run.sh /home/yourusername/Documents/example.pdf \
    --output /home/yourusername/Documents/example_extracted.txt
```

---

# 7. Create a Telegram Bot

Open Telegram and search for:

```text
@BotFather
```

Send:

```text
/newbot
```

BotFather will ask for a display name.

Example:

```text
Docling PDF AI Bot
```

Then choose a username ending in `bot`.

Example:

```text
DoclingPDFReaderBot
```

BotFather will return a bot token similar to:

```text
1234567890:AAExampleSecretTelegramToken
```

The number before the colon is the bot ID.

Example:

```text
Bot ID:
1234567890
```

The complete value is the bot token:

```text
Bot token:
1234567890:AAExampleSecretTelegramToken
```

Keep the bot token private. Anyone with this token can control your bot.

---

# 8. Create the Configuration File

Copy the example configuration:

```bash
cp config.json.example config.json
```

Open it:

```bash
nano config.json
```

Example configuration:

```json
{
  "bot_id": 1234567890,
  "bot_token": "1234567890:AA_REPLACE_WITH_YOUR_REAL_TOKEN",
  "allowed_user_ids": [],
  "max_pdf_mb": 20,
  "output_format": "txt",
  "output_directory": "output",
  "log_level": "INFO"
}
```

Protect the configuration file:

```bash
chmod 600 config.json
```

---

## Configuration Options

### `bot_id`

The numeric Telegram bot ID.

It must match the numeric part at the beginning of the bot token.

Example:

```json
"bot_id": 1234567890
```

### `bot_token`

The full token received from BotFather.

Example:

```json
"bot_token": "1234567890:AAExampleToken"
```

### `allowed_user_ids`

Controls who can use the bot.

To allow everyone:

```json
"allowed_user_ids": []
```

An empty list means that any Telegram user may use the bot.

To allow only specific users:

```json
"allowed_user_ids": [
  123456789,
  987654321
]
```

Telegram user IDs must be numeric values without quotation marks.

### `max_pdf_mb`

Maximum accepted PDF size in megabytes.

Example:

```json
"max_pdf_mb": 20
```

### `output_format`

Use `txt`:

```json
"output_format": "txt"
```

Or Markdown:

```json
"output_format": "md"
```

### `output_directory`

Relative output directory:

```json
"output_directory": "output"
```

Or an absolute path:

```json
"output_directory": "/home/yourusername/Documents/docling-output"
```

### `log_level`

Recommended value:

```json
"log_level": "INFO"
```

For more detailed debugging:

```json
"log_level": "DEBUG"
```

---

# 9. Start the Telegram Bot

Run:

```bash
./run.sh --bot
```

The bot should start using the settings from:

```text
config.json
```

Keep the terminal open while testing.

---

# 10. Start the Bot in Telegram

Open the bot in Telegram and press **Start**.

You can also send:

```text
/start
```

The bot should respond with instructions.

Send:

```text
/id
```

The bot will return your Telegram user ID.

Example:

```text
Your Telegram user ID is: 123456789
```

This is your personal user ID, not the bot ID.

---

# 11. Restrict the Bot to Specific Users

Initially, you can allow everyone:

```json
"allowed_user_ids": []
```

After finding your Telegram user ID, stop the bot with:

```text
Ctrl+C
```

Edit `config.json`:

```bash
nano config.json
```

Add your Telegram user ID:

```json
"allowed_user_ids": [
  123456789
]
```

Restart the bot:

```bash
./run.sh --bot
```

To allow multiple users:

```json
"allowed_user_ids": [
  123456789,
  987654321,
  112233445
]
```

Telegram bots cannot search for arbitrary Telegram users.

A user must first interact with the bot. After that, the bot can access:

* User ID
* Username
* First name
* Last name

The `/id` command is the easiest way for each user to retrieve their numeric ID.

---

# 12. Send a PDF

Send a PDF to the bot as a Telegram document.

The bot will:

1. Identify the Telegram user
2. Create a user-specific directory
3. Save the original PDF
4. Extract the document using Docling
5. Save the extracted text
6. Return the extracted file to the user

Example output directory:

```text
output/user_123456789/
```

Example saved files:

```text
20260731_120501_msg45_research_paper.pdf
20260731_120501_msg45_research_paper.txt
```

The generated `user_info.json` may look like:

```json
{
  "telegram_user_id": 123456789,
  "username": "example_username",
  "first_name": "Example",
  "last_name": "User",
  "last_seen_utc": "2026-07-31T09:05:01+00:00"
}
```

---

# 13. Add Telegram Bot Commands

Open BotFather and send:

```text
/setcommands
```

Select your bot and enter:

```text
start - Show bot instructions
help - Show usage information
id - Show your Telegram user ID
```

Telegram will then display these commands in the bot menu.

---

# 14. Configure the Bot Description

In BotFather, use:

```text
/setdescription
```

Example description:

```text
Prepare PDF documents for AI. Send a PDF and receive clean, structured text or Markdown optimized for ChatGPT, Claude, Gemini, local LLMs, RAG systems, summarization, search, and document analysis.
```

For the shorter About field, use:

```text
Convert PDFs into clean, structured, AI-ready text or Markdown using Docling.
```

---

# 15. Run Automatically on Ubuntu Startup

You can run the Telegram bot as a `systemd` service.

This allows the bot to:

* Start automatically when Ubuntu boots
* Run without an open terminal
* Restart automatically after a crash
* Write logs to the system journal

Assume the project is located here:

```text
/home/yourusername/scripts/docling-telegram-bot
```

Replace `yourusername` with the Linux account that will run the service.

---

## Create the Service File

Run:

```bash
sudo nano /etc/systemd/system/docling-telegram-bot.service
```

Paste:

```ini
[Unit]
Description=Docling Telegram PDF-to-AI Bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=yourusername
Group=yourusername

WorkingDirectory=/home/yourusername/scripts/docling-telegram-bot
ExecStart=/home/yourusername/scripts/docling-telegram-bot/run.sh --bot

Environment=PYTHONUNBUFFERED=1

Restart=on-failure
RestartSec=10

NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Replace every occurrence of:

```text
yourusername
```

with your actual Linux username.

Example:

```ini
User=yourusername
Group=yourusername
WorkingDirectory=/home/yourusername/scripts/docling-telegram-bot
ExecStart=/home/yourusername/scripts/docling-telegram-bot/run.sh --bot
```

Save the file in Nano:

```text
Ctrl+O
Enter
Ctrl+X
```

---

## Enable and Start the Service

Reload systemd:

```bash
sudo systemctl daemon-reload
```

Enable automatic startup and start the bot immediately:

```bash
sudo systemctl enable --now docling-telegram-bot.service
```

The `enable` command configures automatic startup.

The `--now` option starts the service immediately.

---

## Check the Service

Check whether automatic startup is enabled:

```bash
systemctl is-enabled docling-telegram-bot.service
```

Expected output:

```text
enabled
```

Check whether the bot is running:

```bash
systemctl is-active docling-telegram-bot.service
```

Expected output:

```text
active
```

View the full status:

```bash
systemctl status docling-telegram-bot.service
```

Press `q` to exit the status screen.

---

## View Service Logs

Show recent logs:

```bash
journalctl -u docling-telegram-bot.service -n 100
```

Follow logs live:

```bash
journalctl -u docling-telegram-bot.service -f
```

Press `Ctrl+C` to stop following the logs.

This does not stop the bot.

Show logs from the current boot:

```bash
journalctl -u docling-telegram-bot.service -b
```

---

## Manage the Service

Start:

```bash
sudo systemctl start docling-telegram-bot.service
```

Stop:

```bash
sudo systemctl stop docling-telegram-bot.service
```

Restart:

```bash
sudo systemctl restart docling-telegram-bot.service
```

Disable automatic startup:

```bash
sudo systemctl disable docling-telegram-bot.service
```

Disable automatic startup and stop the bot:

```bash
sudo systemctl disable --now docling-telegram-bot.service
```

---

## After Editing the Python Code

After changing:

* `main.py`
* `run.sh`
* `config.json`

restart the service:

```bash
sudo systemctl restart docling-telegram-bot.service
```

You do not need to run `daemon-reload` for normal Python or configuration changes.

---

## After Editing the Service File

Run:

```bash
sudo systemctl daemon-reload
sudo systemctl restart docling-telegram-bot.service
```

---

# 16. Security Recommendations

## Never Commit `config.json`

Your real bot token must not be uploaded to GitHub.

Add the following to `.gitignore`:

```gitignore
.venv/
config.json
output/
__pycache__/
*.pyc
*.log
```

Commit only:

```text
config.json.example
```

The example file should not contain a real token.

Example:

```json
{
  "bot_id": 1234567890,
  "bot_token": "REPLACE_WITH_YOUR_BOT_TOKEN",
  "allowed_user_ids": [],
  "max_pdf_mb": 20,
  "output_format": "txt",
  "output_directory": "output",
  "log_level": "INFO"
}
```

---

## Restrict Public Access

To allow everyone:

```json
"allowed_user_ids": []
```

This means that anyone who finds the bot can send files.

For a personal or private bot, restrict access:

```json
"allowed_user_ids": [
  123456789
]
```

This helps prevent:

* Unauthorized CPU usage
* Disk space abuse
* Unknown file uploads
* Excessive Docling processing
* Unwanted storage of third-party documents

---

## Protect the Configuration File

Run:

```bash
chmod 600 config.json
```

This limits access to the file owner.

---

## Revoke an Exposed Bot Token

If your token is accidentally uploaded to GitHub or shared publicly:

1. Open BotFather
2. Select your bot
3. Revoke or regenerate the token
4. Update `config.json`
5. Restart the bot

```bash
sudo systemctl restart docling-telegram-bot.service
```

Do not continue using an exposed token.

---

# 17. Useful File Commands

Show all user directories:

```bash
find output -maxdepth 1 -type d
```

Show all stored PDFs:

```bash
find output -type f -name "*.pdf"
```

Show extracted text files:

```bash
find output -type f -name "*.txt"
```

Show extracted Markdown files:

```bash
find output -type f -name "*.md"
```

Check output directory size:

```bash
du -sh output
```

Check each user directory size:

```bash
du -sh output/user_*
```

---

# 18. Troubleshooting

## Virtual Environment Not Found

Error:

```text
Virtual environment Python was not found
```

Create it:

```bash
python3 -m venv .venv
```

Install dependencies:

```bash
./.venv/bin/python3 -m pip install --upgrade pip
./.venv/bin/python3 -m pip install -r requirements.txt
```

---

## `python-telegram-bot` Not Installed

Run:

```bash
./.venv/bin/python3 -m pip install "python-telegram-bot>=22,<23"
```

---

## Docling Not Installed

Run:

```bash
./.venv/bin/python3 -m pip install docling
```

---

## `config.json` Not Found

Confirm it exists:

```bash
ls -l config.json
```

Create it from the example:

```bash
cp config.json.example config.json
```

---

## Invalid Bot Token

Confirm that the complete BotFather token is present:

```json
"bot_token": "1234567890:AAExampleToken"
```

The number before the colon should match:

```json
"bot_id": 1234567890
```

---

## Bot Does Not Respond

Run manually:

```bash
./run.sh --bot
```

For a systemd installation:

```bash
systemctl status docling-telegram-bot.service
```

Check logs:

```bash
journalctl -u docling-telegram-bot.service -n 100 --no-pager
```

---

## Another Bot Instance Is Running

Do not run the same Telegram bot manually and through systemd at the same time.

Stop the manually running instance with:

```text
Ctrl+C
```

Or locate it:

```bash
pgrep -af "main.py.*--bot"
```

Restart the service:

```bash
sudo systemctl restart docling-telegram-bot.service
```

---

## Permission Denied for `run.sh`

Run:

```bash
chmod +x run.sh
```

---

## Permission Denied While Saving Files

Ensure the project belongs to the correct Linux user:

```bash
sudo chown -R "$USER":"$USER" .
```

Ensure the output directory is writable:

```bash
mkdir -p output
chmod -R u+rwX output
```

---

## Service Error `status=203/EXEC`

Check that `run.sh` exists:

```bash
ls -l /full/path/to/docling-telegram-bot/run.sh
```

Make it executable:

```bash
chmod +x /full/path/to/docling-telegram-bot/run.sh
```

Check the `ExecStart` path in the service file.

---

## Service Starts but Cannot Find `config.json`

Ensure the service contains the correct working directory:

```ini
WorkingDirectory=/home/yourusername/scripts/docling-telegram-bot
```

The bot should be started with:

```ini
ExecStart=/home/yourusername/scripts/docling-telegram-bot/run.sh --bot
```

---

## Large PDFs Fail

Reduce or increase the configured limit:

```json
"max_pdf_mb": 20
```

Remember that Telegram’s hosted Bot API has its own file download limits.

Large PDFs may also require substantial:

* RAM
* CPU time
* Disk space

---

## Bot Stops When Laptop Sleeps

The bot runs only while the computer is awake and connected to the internet.

The bot is unavailable when the laptop is:

* Powered off
* Suspended
* Hibernating
* Disconnected from the internet

For continuous availability, deploy the bot on:

* A VPS
* A home server
* A Raspberry Pi
* A cloud virtual machine
* An always-on Linux computer

---

# 19. Development Workflow

Start manually during development:

```bash
./run.sh --bot
```

Stop with:

```text
Ctrl+C
```

After making changes:

```bash
./run.sh --bot
```

For production with systemd:

```bash
sudo systemctl restart docling-telegram-bot.service
```

View logs:

```bash
journalctl -u docling-telegram-bot.service -f
```

---

# 20. Example Complete Setup

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/docling-telegram-bot.git
cd docling-telegram-bot

python3 -m venv .venv

./.venv/bin/python3 -m pip install --upgrade pip
./.venv/bin/python3 -m pip install -r requirements.txt

chmod +x run.sh

cp config.json.example config.json
nano config.json

./run.sh --bot
```

After confirming that the bot works, configure systemd:

```bash
sudo nano /etc/systemd/system/docling-telegram-bot.service

sudo systemctl daemon-reload
sudo systemctl enable --now docling-telegram-bot.service

systemctl status docling-telegram-bot.service
```

---

# Privacy Notice

This bot stores uploaded PDFs and extracted content on the machine where it runs.

The bot administrator is responsible for:

* Protecting stored documents
* Restricting filesystem access
* Managing retention and deletion
* Informing users that files are stored
* Avoiding processing confidential documents without authorization
* Complying with applicable privacy and data-protection requirements

Do not operate the bot publicly without considering file storage, user consent, and server security.

---

# License

Choose a license before publishing the project.

A common permissive choice is the MIT License.

Create a `LICENSE` file containing the MIT License text and replace the copyright holder and year.

Example:

```text
MIT License

Copyright (c) 2026 NOT ASHKAN
```

---

# Acknowledgements

This project uses:

* Docling for PDF document conversion
* python-telegram-bot for Telegram integration
* systemd for automatic Linux service management
