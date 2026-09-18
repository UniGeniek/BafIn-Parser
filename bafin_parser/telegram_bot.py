from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .cache import CacheStore
from .config import settings
from .logging import logger
from .parser_factory import get_parser
from .ss04_generator import render_ss04_document


class TelegramBot:
    def __init__(self) -> None:
        self.application = Application.builder().token(settings.telegram_token).build()
        self.cache = CacheStore()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def _cleanup(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE, also_delete_msg_id: int = None):
        """Wipe the old bot spam so the chat stays clean, damn it."""
        old_ids = context.user_data.get("bot_msg_ids", [])
        if also_delete_msg_id:
            old_ids.append(also_delete_msg_id)
        for mid in old_ids:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
        context.user_data["bot_msg_ids"] = []

    async def _track(self, context: ContextTypes.DEFAULT_TYPE, message):
        """Track a sent message so we can delete it later, no cap."""
        if "bot_msg_ids" not in context.user_data:
            context.user_data["bot_msg_ids"] = []
        context.user_data["bot_msg_ids"].append(message.message_id)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        await self._cleanup(chat_id, context, also_delete_msg_id=update.message.message_id)
        
        keyboard = [
            [InlineKeyboardButton("🇩🇪 BaFin (Germany)", callback_data="set_country:DE")],
            [InlineKeyboardButton("🇫🇷 ORIAS (France)", callback_data="set_country:FR")],
            [InlineKeyboardButton("🇪🇸 CNMV (Spain)", callback_data="set_country:ES")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg = await update.message.reply_text(
            "Welcome to the registry parser, boss!\n"
            "Pick a country to search:",
            reply_markup=reply_markup
        )
        await self._track(context, msg)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        query = update.message.text or ""
        
        # Wipe the old bot messages + the user's dumb text, damn it.
        await self._cleanup(chat_id, context, also_delete_msg_id=update.message.message_id)
        
        msg = await update.message.reply_text("🔍 Scanning the registry for data...")
        await self._track(context, msg)
        
        country = context.user_data.get("country", "DE")
        parser_client = get_parser(country)
        if not parser_client:
            await msg.edit_text(f"❌ The parser for {country} is not implemented yet, damn it.")
            return

        result = await parser_client.search(query)
        if not result.success or not result.record:
            await msg.edit_text("❌ Nothing found in the registry.")
            return
            
        record = result.record.__dict__ if not isinstance(result.record, dict) else result.record
        context.user_data["current_record"] = record
        
        await self._render_detail_menu(msg, record, context)

    async def _render_detail_menu(self, msg_or_query, record_dict, context: ContextTypes.DEFAULT_TYPE):
        g2rs = record_dict.get("g2rs_eligible", False)
        status_icon = "✅ G2RS eligible" if g2rs else "⚠️ Check G2RS status"
        text = (
            f"🏢 *{record_dict.get('name')}*\n"
            f"Registry: `{record_dict.get('registry_name')} ({record_dict.get('country_code')})`\n"
            f"Registry ID: `{record_dict.get('registry_id')}`\n"
            f"💼 License: {record_dict.get('activity')}\n"
            f"📈 Status: {record_dict.get('license_status')}\n\n"
            f"{status_icon}\n"
            f"{record_dict.get('g2rs_notes', '')}"
        )
        keyboard = [
            [InlineKeyboardButton("Download PDF (SS04)", callback_data="download_pdf")]
        ]
        
        if "search_results" in context.user_data and context.user_data["search_results"]:
            keyboard.append([InlineKeyboardButton("🔙 Back to list", callback_data="back_to_list")])
            
        keyboard.append([InlineKeyboardButton("🏠 Main menu", callback_data="menu_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        if hasattr(msg_or_query, "edit_text"):
            await msg_or_query.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await msg_or_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "menu_main":
            keyboard = [
                [InlineKeyboardButton("🇩🇪 BaFin (Germany)", callback_data="set_country:DE")],
                [InlineKeyboardButton("🇫🇷 ORIAS (France)", callback_data="set_country:FR")],
                [InlineKeyboardButton("🇪🇸 CNMV (Spain)", callback_data="set_country:ES")],
            ]
            await query.edit_message_text("Main menu (pick a registry):", reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        if data.startswith("set_country:"):
            country = data.split(":")[1]
            context.user_data["country"] = country
            keyboard = [
                [InlineKeyboardButton("🔍 Search by company name / ID", callback_data="menu_search")],
            ]
            if country == "DE":
                keyboard.append([InlineKeyboardButton("📋 G2RS scanner (Banks)", callback_data="g2rs_scan:30")])
                keyboard.append([InlineKeyboardButton("📋 G2RS scanner (Fin. services)", callback_data="g2rs_scan:50")])
                keyboard.append([InlineKeyboardButton("📋 G2RS scanner (Crypto registry)", callback_data="g2rs_scan:160")])
                
            await query.edit_message_text(f"Selected registry: {country}\nChoose an action:", reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        if data == "menu_search":
            await query.edit_message_text("Send me a company name or BaFin ID in a text message.")
            return
            
        if data.startswith("g2rs_scan:"):
            cat_id = data.split(":")[1]
            await query.edit_message_text("⏳ Scanning the BaFin registry — this can take a bit, so buckle up...")
            
            country = context.user_data.get("country", "DE")
            parser_client = get_parser(country)
            if not parser_client:
                return

            # Small categories (crypto, MiCAR, etc.) have few entries — search without letter filter, no drama.
            small_categories = {"145", "150", "155", "160", "170", "175"}
            letter = "" if cat_id in small_categories else "A"
            list_res = await parser_client.search_list(category_id=cat_id, letter=letter)
            if not list_res.success or not list_res.results:
                await query.edit_message_text("Nothing found or something blew up. Damn.")
                return
                
            context.user_data["search_results"] = [r.__dict__ for r in list_res.results]
            context.user_data["current_page"] = 0
            await self._render_list_page(query, context, 0)
            return

        if data.startswith("page:"):
            page_idx = int(data.split(":")[1])
            context.user_data["current_page"] = page_idx
            await self._render_list_page(query, context, page_idx)
            return
            
        if data == "back_to_list":
            page_idx = context.user_data.get("current_page", 0)
            await self._render_list_page(query, context, page_idx)
            return
            
        if data.startswith("detail:"):
            idx = int(data.split(":")[1])
            results = context.user_data.get("search_results", [])
            if idx >= len(results):
                return
            target_url = results[idx]["detail_url"]
            await query.edit_message_text("⏳ Pulling company details...")
            
            country = context.user_data.get("country", "DE")
            parser_client = get_parser(country)
            res = await parser_client.get_details(target_url)
            if not res.success or not res.record:
                await query.edit_message_text("Failed to fetch the details, damn it.")
                return
                
            record = res.record.__dict__ if not isinstance(res.record, dict) else res.record
            context.user_data["current_record"] = record
            await self._render_detail_menu(query, record, context)
            return
            
        if data == "download_pdf":
            record_dict = context.user_data.get("current_record")
            if not record_dict:
                return
            status_msg = await query.message.reply_text("⏳ Generating PDF / Generating PDF...")
            from .models import CompanyRecord
            record_obj = CompanyRecord(**record_dict)
            output_dir = Path("outputs") / str(update.effective_user.id)
            pdf_path, html_path = await render_ss04_document(record_obj, output_dir=output_dir)
            with open(pdf_path, "rb") as doc:
                pdf_msg = await query.message.reply_document(document=doc, filename=pdf_path.name)
            await self._track(context, pdf_msg)
            try:
                await status_msg.delete()
            except Exception:
                pass
            logger.info("telegram_document_sent", user_id=update.effective_user.id)

    async def _render_list_page(self, query, context, page_idx: int):
        results = context.user_data.get("search_results", [])
        per_page = 5
        total_pages = (len(results) - 1) // per_page + 1
        
        start = page_idx * per_page
        end = start + per_page
        page_items = results[start:end]
        
        keyboard = []
        for i, item in enumerate(page_items):
            idx = start + i
            btn_text = f"{item['name']} ({item.get('registry_id', '')})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"detail:{idx}")])
            
        nav = []
        if page_idx > 0:
            nav.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page:{page_idx-1}"))
        if page_idx < total_pages - 1:
            nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page_idx+1}"))
            
        if nav:
            keyboard.append(nav)
            
        keyboard.append([InlineKeyboardButton("🔙 Main menu", callback_data="menu_main")])
        
        text = f"📑 Companies found (Page {page_idx+1}/{total_pages}):\nChoose a company for details."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    def run(self) -> None:
        self.application.run_polling()

if __name__ == "__main__":
    TelegramBot().run()
