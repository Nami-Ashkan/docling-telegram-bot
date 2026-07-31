#!/usr/bin/env python3
"""Convert PDFs with Docling from the CLI or through a Telegram bot.

CLI examples:
    ./run.sh document.pdf
    ./run.sh document.pdf --format md
    ./run.sh document.pdf -o /tmp/result.txt

Telegram bot:
    ./run.sh --bot
    ./run.sh --bot --config /path/to/config.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from docling.document_converter import DocumentConverter

LOGGER = logging.getLogger("docling_bot")
PDF_SIGNATURE: Final[bytes] = b"%PDF-"
DEFAULT_MAX_PDF_MB: Final[int] = 20
SCRIPT_DIR: Final[Path] = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH: Final[Path] = SCRIPT_DIR / "config.json"

# Initializing Docling can be expensive, so reuse one converter. The lock also
# prevents concurrent Telegram requests from using the converter simultaneously.
_CONVERTER: DocumentConverter | None = None
_CONVERTER_LOCK = threading.Lock()


@dataclass(frozen=True)
class BotConfig:
    """Validated Telegram bot configuration."""

    bot_id: int
    bot_token: str
    allowed_user_ids: set[int]
    max_pdf_mb: int
    output_format: str
    output_directory: Path
    log_level: str


class ConfigError(ValueError):
    """Raised when config.json is missing or invalid."""


def configure_logging(log_level: str = "INFO") -> None:
    """Configure console logging."""
    normalized_level = log_level.strip().upper()
    logging.basicConfig(
        level=getattr(logging, normalized_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ConfigError(f"Configuration file was not found: {path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: "
            f"{exc.msg}"
        ) from exc
    except OSError as exc:
        raise ConfigError(f"Could not read configuration file: {path}") from exc

    if not isinstance(raw_data, dict):
        raise ConfigError("The top level of config.json must be a JSON object.")
    return raw_data


def require_positive_int(data: dict[str, Any], key: str, default: int | None = None) -> int:
    """Read and validate a positive integer configuration field."""
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f'"{key}" must be an integer.')
    if value <= 0:
        raise ConfigError(f'"{key}" must be greater than zero.')
    return value


def parse_allowed_user_ids(value: Any) -> set[int]:
    """Validate allowed_user_ids from config.json."""
    if value is None:
        return set()
    if not isinstance(value, list):
        raise ConfigError('"allowed_user_ids" must be a JSON list of numeric IDs.')

    result: set[int] = set()
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
            raise ConfigError(
                'Every item in "allowed_user_ids" must be a positive integer.'
            )
        result.add(item)
    return result


def load_bot_config(config_path: Path) -> BotConfig:
    """Load and validate Telegram settings from config.json."""
    config_path = config_path.expanduser().resolve()
    data = read_json_object(config_path)

    bot_id = require_positive_int(data, "bot_id")

    bot_token = data.get("bot_token")
    if not isinstance(bot_token, str) or not bot_token.strip():
        raise ConfigError('"bot_token" must contain the full token from BotFather.')
    bot_token = bot_token.strip()

    token_prefix, separator, _secret = bot_token.partition(":")
    if not separator or not token_prefix.isdigit():
        raise ConfigError(
            '"bot_token" does not look valid. Expected: numeric_id:secret'
        )
    if int(token_prefix) != bot_id:
        raise ConfigError(
            '"bot_id" must match the numeric part before the colon in "bot_token".'
        )

    allowed_user_ids = parse_allowed_user_ids(data.get("allowed_user_ids", []))

    max_pdf_mb = require_positive_int(data, "max_pdf_mb", DEFAULT_MAX_PDF_MB)
    # Telegram's hosted Bot API currently limits bot downloads to 20 MB.
    max_pdf_mb = min(max_pdf_mb, DEFAULT_MAX_PDF_MB)

    output_format = data.get("output_format", "txt")
    if not isinstance(output_format, str):
        raise ConfigError('"output_format" must be "txt" or "md".')
    output_format = output_format.strip().lower()
    if output_format not in {"txt", "md"}:
        raise ConfigError('"output_format" must be "txt" or "md".')

    output_directory_value = data.get("output_directory", "output")
    if not isinstance(output_directory_value, str) or not output_directory_value.strip():
        raise ConfigError('"output_directory" must be a non-empty path string.')

    output_directory = Path(output_directory_value).expanduser()
    if not output_directory.is_absolute():
        # Resolve relative output paths from the config file's directory.
        output_directory = config_path.parent / output_directory
    output_directory = output_directory.resolve()

    log_level = data.get("log_level", "INFO")
    if not isinstance(log_level, str):
        raise ConfigError('"log_level" must be a string.')
    log_level = log_level.strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError(
            '"log_level" must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.'
        )

    return BotConfig(
        bot_id=bot_id,
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
        max_pdf_mb=max_pdf_mb,
        output_format=output_format,
        output_directory=output_directory,
        log_level=log_level,
    )


def is_pdf_file(path: Path) -> bool:
    """Check both the extension and the PDF signature."""
    if path.suffix.lower() != ".pdf" or not path.is_file():
        return False

    try:
        with path.open("rb") as file_handle:
            return file_handle.read(len(PDF_SIGNATURE)) == PDF_SIGNATURE
    except OSError:
        return False


def safe_stem(filename: str) -> str:
    """Create a safe and reasonably short filename stem."""
    stem = Path(filename).stem.strip()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    stem = stem.strip("._-")
    return (stem or "document")[:100]


def get_converter() -> DocumentConverter:
    """Create the shared Docling converter when first needed."""
    global _CONVERTER
    if _CONVERTER is None:
        LOGGER.info("Initializing Docling DocumentConverter")
        _CONVERTER = DocumentConverter()
    return _CONVERTER


def convert_pdf(
    input_pdf: Path,
    output_file: Path | None = None,
    output_format: str = "txt",
) -> Path:
    """Convert one PDF to Markdown-formatted text and return the output path."""
    input_pdf = input_pdf.expanduser().resolve()

    if not input_pdf.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_pdf}")
    if not is_pdf_file(input_pdf):
        raise ValueError(f"The input is not a valid PDF file: {input_pdf}")
    if output_format not in {"txt", "md"}:
        raise ValueError("Output format must be 'txt' or 'md'.")

    if output_file is None:
        output_file = input_pdf.with_suffix(f".{output_format}")
    else:
        output_file = output_file.expanduser().resolve()

    output_file.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Converting PDF: %s", input_pdf)
    with _CONVERTER_LOCK:
        converter = get_converter()
        conversion_result = converter.convert(str(input_pdf))
        extracted_text = conversion_result.document.export_to_markdown()

    output_file.write_text(extracted_text, encoding="utf-8")
    LOGGER.info("Saved extracted text: %s", output_file)
    return output_file


def make_user_directory(output_root: Path, user_id: int) -> Path:
    """Create and return output/user_<telegram_id>."""
    user_directory = output_root / f"user_{user_id}"
    user_directory.mkdir(parents=True, exist_ok=True)
    return user_directory


def save_user_metadata(user_directory: Path, user: Any) -> None:
    """Store the latest public Telegram user details alongside their files."""
    metadata = {
        "telegram_user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "last_seen_utc": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path = user_directory / "user_info.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def command_start(update, context) -> None:  # type: ignore[no-untyped-def]
    """Explain how to use the Telegram bot."""
    if update.effective_message is None:
        return

    await update.effective_message.reply_text(
        "Send me a PDF as a document. I will save the PDF, extract its contents "
        "with Docling, and return a text file.\n\n"
        "Use /id to display your Telegram user ID."
    )


async def command_id(update, context) -> None:  # type: ignore[no-untyped-def]
    """Return the sender's Telegram user ID."""
    if update.effective_message is None or update.effective_user is None:
        return

    await update.effective_message.reply_text(
        f"Your Telegram user ID is: {update.effective_user.id}"
    )


async def user_is_authorized(update, context) -> bool:  # type: ignore[no-untyped-def]
    """Apply the optional Telegram user allowlist."""
    allowed_user_ids: set[int] = context.application.bot_data["allowed_user_ids"]
    user = update.effective_user

    if not allowed_user_ids:
        return True
    if user is not None and user.id in allowed_user_ids:
        return True

    if update.effective_message is not None:
        await update.effective_message.reply_text(
            "This bot is private and your Telegram user ID is not authorized. "
            "Use /id to see your ID."
        )
    return False


async def handle_pdf(update, context) -> None:  # type: ignore[no-untyped-def]
    """Save a Telegram PDF, convert it, and return the extracted text."""
    message = update.effective_message
    user = update.effective_user
    if message is None or message.document is None or user is None:
        return
    if not await user_is_authorized(update, context):
        return

    document = message.document
    original_name = document.file_name or "document.pdf"
    max_pdf_bytes: int = context.application.bot_data["max_pdf_bytes"]
    output_format: str = context.application.bot_data["output_format"]
    output_root: Path = context.application.bot_data["output_root"]
    conversion_semaphore: asyncio.Semaphore = context.application.bot_data[
        "conversion_semaphore"
    ]

    if document.file_size is not None and document.file_size > max_pdf_bytes:
        max_pdf_mb = max_pdf_bytes // (1024 * 1024)
        await message.reply_text(f"The PDF is too large. Maximum size: {max_pdf_mb} MB.")
        return

    status_message = await message.reply_text("PDF received. Saving and extracting...")
    user_directory = make_user_directory(output_root, user.id)
    save_user_metadata(user_directory, user)

    # UTC timestamp + Telegram message ID prevents repeated filenames from being
    # overwritten when a user sends the same document more than once.
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    message_id = message.message_id
    stem = safe_stem(original_name)
    base_name = f"{timestamp}_msg{message_id}_{stem}"
    input_path = user_directory / f"{base_name}.pdf"
    output_path = user_directory / f"{base_name}.{output_format}"

    try:
        telegram_file = await context.bot.get_file(document.file_id)
        await telegram_file.download_to_drive(custom_path=input_path)
        LOGGER.info(
            "Saved Telegram PDF user_id=%s path=%s",
            user.id,
            input_path,
        )

        if not is_pdf_file(input_path):
            await status_message.edit_text(
                "The uploaded document does not appear to be a valid PDF. "
                "The received file was kept for inspection."
            )
            return

        async with conversion_semaphore:
            await asyncio.to_thread(
                convert_pdf,
                input_path,
                output_path,
                output_format,
            )

        with output_path.open("rb") as output_handle:
            await message.reply_document(
                document=output_handle,
                filename=output_path.name,
                caption="Text extracted successfully.",
            )

        await status_message.delete()
        LOGGER.info(
            "Converted Telegram PDF user_id=%s input=%s output=%s",
            user.id,
            input_path,
            output_path,
        )

    except Exception:
        LOGGER.exception(
            "Telegram conversion failed user_id=%s filename=%s",
            user.id,
            original_name,
        )
        try:
            await status_message.edit_text(
                "I could not convert this PDF. The uploaded PDF was kept in your "
                "server folder. Check the bot logs for details."
            )
        except Exception:
            LOGGER.exception("Could not update the Telegram error message")


async def handle_non_pdf_document(update, context) -> None:  # type: ignore[no-untyped-def]
    """Reject unsupported document types."""
    if update.effective_message is None:
        return
    if not await user_is_authorized(update, context):
        return
    await update.effective_message.reply_text("Please send a PDF file as a document.")


async def telegram_error_handler(update, context) -> None:  # type: ignore[no-untyped-def]
    """Log uncaught errors from python-telegram-bot."""
    LOGGER.error("Unhandled Telegram update error", exc_info=context.error)


def run_bot(config_path: Path) -> None:
    """Start the Telegram bot using long polling."""
    try:
        from telegram.ext import (
            ApplicationBuilder,
            CommandHandler,
            MessageHandler,
            filters,
        )
    except ImportError as exc:
        raise RuntimeError(
            "python-telegram-bot is not installed. Run: "
            "./.venv/bin/python3 -m pip install 'python-telegram-bot>=22,<23'"
        ) from exc

    config = load_bot_config(config_path)
    configure_logging(config.log_level)
    config.output_directory.mkdir(parents=True, exist_ok=True)

    application = ApplicationBuilder().token(config.bot_token).build()
    application.bot_data["allowed_user_ids"] = config.allowed_user_ids
    application.bot_data["max_pdf_bytes"] = config.max_pdf_mb * 1024 * 1024
    application.bot_data["output_format"] = config.output_format
    application.bot_data["output_root"] = config.output_directory
    application.bot_data["conversion_semaphore"] = asyncio.Semaphore(1)

    application.add_handler(CommandHandler("start", command_start))
    application.add_handler(CommandHandler("help", command_start))
    application.add_handler(CommandHandler("id", command_id))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    application.add_handler(
        MessageHandler(filters.Document.ALL, handle_non_pdf_document)
    )
    application.add_error_handler(telegram_error_handler)

    access_mode = "restricted" if config.allowed_user_ids else "public"
    LOGGER.info(
        "Starting Telegram bot bot_id=%s mode=%s max_pdf=%sMB output=%s root=%s",
        config.bot_id,
        access_mode,
        config.max_pdf_mb,
        config.output_format,
        config.output_directory,
    )
    application.run_polling(drop_pending_updates=False)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert a PDF with Docling or run a Telegram PDF-to-text bot."
    )
    parser.add_argument(
        "input_pdf",
        nargs="?",
        type=Path,
        help="PDF to convert in command-line mode.",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Run as a Telegram bot.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Bot configuration file (default: {DEFAULT_CONFIG_PATH}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file path in command-line mode.",
    )
    parser.add_argument(
        "--format",
        choices=("txt", "md"),
        default="txt",
        help="Output extension. The extracted content is Markdown-formatted text.",
    )
    return parser


def main() -> int:
    """Application entry point."""
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.bot:
        if args.input_pdf is not None or args.output is not None:
            parser.error("Do not provide input/output files together with --bot.")
        try:
            run_bot(args.config)
        except (ConfigError, RuntimeError, OSError) as exc:
            configure_logging("INFO")
            LOGGER.error("%s", exc)
            return 1
        except Exception:
            configure_logging("INFO")
            LOGGER.exception("Telegram bot failed")
            return 1
        return 0

    configure_logging("INFO")

    if args.input_pdf is None:
        parser.print_help(sys.stderr)
        print("\nError: provide a PDF path or use --bot.", file=sys.stderr)
        return 2

    try:
        result_path = convert_pdf(
            input_pdf=args.input_pdf,
            output_file=args.output,
            output_format=args.format,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        LOGGER.error("%s", exc)
        return 1
    except Exception:
        LOGGER.exception("PDF conversion failed")
        return 1

    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
