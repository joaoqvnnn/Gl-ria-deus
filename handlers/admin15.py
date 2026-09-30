"""
Módulo ADMIN — EXTRAS (backup, logs, manutenção, sistema, restart).
"""
import io
import os
import sys
import platform
import logging
import asyncio
from datetime import datetime
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS, DB_PATH
from database import db
from keyboards import menus
from texts import cache

logger = logging.getLogger(__name__)

BOOT_TIME = datetime.now()

MAINT_DEFAULT_MSG = (
    "🚧 <b>Bot em manutenção</b>\n\n"
    "Estamos fazendo melhorias para te atender ainda melhor!\n"
    "Volte em alguns minutos."
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        try:
            await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass


async def _delete_prompt(context, id_key, chat_key):
    pid = context.user_data.pop(id_key, None)
    chat = context.user_data.pop(chat_key, None)
    if pid and chat:
        try:
            await context.bot.delete_message(chat_id=chat, message_id=pid)
        except Exception:
            pass


async def _edit_prompt_error(context, id_key, chat_key, text, kb=None):
    pid = context.user_data.get(id_key)
    chat = context.user_data.get(chat_key)
    if pid and chat:
        try:
            await context.bot.edit_message_text(
                chat_id=chat, message_id=pid,
                text=text, reply_markup=kb, parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# MENU PRINCIPAL
# ═══════════════════════════════════════════════
async def admin_extras_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    manut = await db.get_maintenance()
    ultimo_backup = await db.backup_last()

    uptime = datetime.now() - BOOT_TIME
    h, m = divmod(int(uptime.total_seconds() // 60), 60)

    backup_txt = "—"
    if ultimo_backup:
        backup_txt = str(ultimo_backup.get("created_at") or "")[:16]

    texto = (
        "🔧 <b>Extras e Sistema</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚧 Manutenção: <b>{'🔴 LIGADA' if manut else '🟢 Desligada'}</b>\n"
        f"⏱️ Uptime: <b>{h}h {m}min</b>\n"
        f"💾 Último backup: <b>{backup_txt}</b>\n\n"
        "👇 Escolha uma opção:"
    )
    await _edit_or_send(query, texto, menus.admin_extras_kb())


# ═══════════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════════
async def admin_extras_backup_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    ultimo = await db.backup_last()
    ligado = (await db.get_config("backup_auto", "0")) == "1"
    horas = int(await db.get_config("backup_horas", "24"))

    ultimo_txt = "—"
    if ultimo:
        ultimo_txt = (
            f"{str(ultimo.get('created_at') or '')[:16]} "
            f"({(ultimo.get('tamanho') or 0) // 1024} KB)"
        )

    texto = (
        "💾 <b>Backup</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Último backup: <b>{ultimo_txt}</b>\n"
        f"⚙️ Automático: <b>{'🟢 LIGADO' if ligado else '🔴 Desligado'}</b>\n"
        f"⏰ Frequência: <b>a cada {horas}h</b>\n\n"
        "👇 Escolha uma opção:"
    )
    await _edit_or_send(query, texto, menus.admin_extras_backup_kb())


async def admin_extras_backup_do_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        conteudo = await db.admin_backup_bytes()
        filename = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(io.BytesIO(conteudo), filename=filename),
            caption=(
                "💾 <b>Backup gerado</b>\n\n"
                f"📦 Arquivo: <code>{filename}</code>\n"
                f"📊 Tamanho: <b>{len(conteudo) // 1024} KB</b>\n\n"
                "Guarde em local seguro."
            ),
            parse_mode=ParseMode.HTML,
        )

        await db.backup_register(filename, len(conteudo), update.effective_user.id)
        await db.log_admin_action(update.effective_user.id, "backup_manual", filename)
    except Exception as e:
        logger.exception("Erro backup: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


async def admin_extras_backup_hist_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    items = await db.backup_list(limit=15)

    if not items:
        texto = "📂 <b>Histórico de Backups</b>\n\n<i>Nenhum backup registrado.</i>"
    else:
        linhas = ["📂 <b>Últimos 15 backups</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"]
        for it in items:
            data = str(it.get("created_at") or "")[:16]
            kb = (it.get("tamanho") or 0) // 1024
            linhas.append(
                f"🕐 <code>{data}</code>\n"
                f"├ 📦 <code>{it['filename']}</code>\n"
                f"└ 💾 {kb} KB\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras_backup")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_extras_backup_auto_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    ligado = (await db.get_config("backup_auto", "0")) == "1"
    horas = int(await db.get_config("backup_horas", "24"))

    texto = (
        "⚙️ <b>Backup Automático</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Status: <b>{'🟢 LIGADO' if ligado else '🔴 Desligado'}</b>\n"
        f"⏰ Frequência: <b>a cada {horas}h</b>\n\n"
        "💡 O backup é enviado pro canal de estoque (STOCK_CHANNEL_ID).\n"
        "Se não tiver canal configurado, é enviado pro admin."
    )
    await _edit_or_send(query, texto, menus.admin_extras_backup_auto_kb(ligado, horas))


async def admin_extras_backup_auto_toggle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    atual = await db.get_config("backup_auto", "0")
    novo = "0" if atual == "1" else "1"
    await db.set_config("backup_auto", novo)
    await db.log_admin_action(update.effective_user.id, "backup_auto_toggle", novo)

    await query.answer(f"{'🟢 Ligado' if novo == '1' else '🔴 Desligado'}", show_alert=True)
    await admin_extras_backup_auto_cb(update, context)


async def admin_extras_backup_auto_h_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        horas = int(query.data.split(":")[2])
    except (ValueError, IndexError):
        return

    await db.set_config("backup_horas", str(horas))
    await db.log_admin_action(update.effective_user.id, "backup_horas", str(horas))

    await query.answer(f"⏰ a cada {horas}h", show_alert=True)
    await admin_extras_backup_auto_cb(update, context)


async def admin_extras_backup_restore_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_backup_restore"] = True

    try:
        await query.edit_message_text(
            "📥 <b>Restaurar Backup</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>ATENÇÃO:</b> isso vai SUBSTITUIR o banco atual.\n\n"
            "Envie um arquivo <b>.db</b> gerado pelo backup.\n\n"
            "💡 Recomendado: faça um backup ANTES de restaurar.\n\n"
            "Envie <code>/cancelar</code> para sair.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_extras_backup_restore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_backup_restore"):
        return
    if not is_admin(update.effective_user.id):
        return

    doc = update.message.document
    if not doc:
        return

    if not doc.file_name.endswith(".db"):
        await update.message.reply_text(
            "❌ Envie um arquivo <b>.db</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop("admin_backup_restore", None)

    try:
        file = await context.bot.get_file(doc.file_id)
        data = await file.download_as_bytearray()

        try:
            await db._db.close()
        except Exception:
            pass

        with open(DB_PATH, "wb") as f:
            f.write(data)

        await db.init_db()

        await db.log_admin_action(update.effective_user.id, "backup_restore", doc.file_name)

        await update.message.reply_text(
            "✅ <b>Backup restaurado!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📦 Arquivo: <code>{doc.file_name}</code>\n"
            f"📊 Tamanho: <b>{len(data) // 1024} KB</b>\n\n"
            "💡 Recomendado reiniciar o bot para garantir."
        )
    except Exception as e:
        logger.exception("Erro restore: %s", e)
        await update.message.reply_text(f"❌ Erro ao restaurar: {e}")


# ═══════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════
async def admin_extras_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["logs_v2_filtro"] = {"admin_id": None, "action": None, "periodo": "todos"}
    await _render_logs(query, context)


async def admin_logs2_filter_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        periodo = query.data.split(":")[2]
    except IndexError:
        periodo = "todos"

    filtro = context.user_data.get("logs_v2_filtro") or {}
    filtro["periodo"] = periodo
    context.user_data["logs_v2_filtro"] = filtro

    await _render_logs(query, context)


async def _render_logs(query, context):
    filtro = context.user_data.get("logs_v2_filtro") or {}
    admin_id = filtro.get("admin_id")
    action = filtro.get("action")
    periodo = filtro.get("periodo", "todos")

    total = await db.logs_v2_count(admin_id, action, periodo)
    logs = await db.logs_v2_filter(admin_id, action, periodo, limit=15)

    periodo_label = {
        "hoje": "Hoje", "7d": "7 dias", "30d": "30 dias", "todos": "Tudo",
    }.get(periodo, periodo)

    extras = []
    if admin_id:
        extras.append(f"👤 admin={admin_id}")
    if action:
        extras.append(f"⚡ action~{action}")

    filtros_txt = " · ".join(extras) if extras else "Nenhum"

    if not logs:
        linhas = [
            "📋 <b>Logs de Administração</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Período: <b>{periodo_label}</b>\n"
            f"🔍 Filtros: <b>{filtros_txt}</b>\n\n"
            "<i>Nenhum log encontrado.</i>"
        ]
    else:
        linhas = [
            "📋 <b>Logs de Administração</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 Período: <b>{periodo_label}</b>\n"
            f"🔍 Filtros: <b>{filtros_txt}</b>\n"
            f"📊 Total: <b>{total}</b>\n\n"
        ]
        for l in logs[:15]:
            data = str(l.get("created_at") or "")[:16]
            admin = l.get("admin_id") or "—"
            act = l.get("action") or "—"
            target = (l.get("target") or "")[:30]
            details = (l.get("details") or "")[:40]

            linhas.append(
                f"🕐 <code>{data}</code> · 👤 <code>{admin}</code>\n"
                f"├ ⚡ <b>{act}</b>\n"
                f"├ 🎯 <code>{target}</code>\n"
                f"└ 📝 {details}\n"
            )
        if total > 15:
            linhas.append(f"\n<i>... mostrando 15 de {total}</i>")

    texto = "\n".join(linhas)
    kb = menus.admin_extras_logs_kb(admin_id, action, periodo)
    await _edit_or_send(query, texto, kb)


async def admin_logs2_search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["logs2_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar log por ação</b>\n\n"
            "Envie o termo (ex: <code>user</code>, <code>product</code>, <code>refund</code>):",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_logs2_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("logs2_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("logs2_search", None)

    if term.startswith("/"):
        return

    if not term:
        return

    filtro = context.user_data.get("logs_v2_filtro") or {}
    filtro["action"] = term
    context.user_data["logs_v2_filtro"] = filtro

    class FakeQuery:
        def __init__(self, message):
            self.message = message
        async def answer(self):
            pass

    await _render_logs(FakeQuery(update.message), context)


async def admin_logs2_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    stats = await db.logs_v2_stats()

    linhas = [
        "📊 <b>Estatísticas de Logs</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total de logs: <b>{stats['total']}</b>\n"
        f"📅 Hoje: <b>{stats['hoje']}</b>\n\n"
    ]

    if stats["top_admins"]:
        linhas.append("👤 <b>Top admins:</b>")
        for a in stats["top_admins"]:
            linhas.append(f"├ <code>{a['admin_id']}</code> — {a['c']} ações")
        linhas.append("")

    if stats["top_actions"]:
        linhas.append("⚡ <b>Top ações:</b>")
        for a in stats["top_actions"]:
            linhas.append(f"├ <b>{a['action']}</b> — {a['c']}x")

    texto = "\n".join(linhas)
    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras_logs")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_logs2_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        csv_text = await db.logs_v2_export_csv()
        if not csv_text or len(csv_text.splitlines()) <= 1:
            await query.answer("📭 Nenhum log.", show_alert=True)
            return

        filename = f"logs-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(csv_text.encode("utf-8"), filename=filename),
            caption="📤 <b>Logs exportados</b>",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "logs_export")
    except Exception as e:
        logger.exception("Erro export logs: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


# ═══════════════════════════════════════════════
# MANUTENÇÃO
# ═══════════════════════════════════════════════
async def admin_extras_maint_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    ativo = await db.get_maintenance()
    agendada = await db.maintenance_get_agendada()

    texto = (
        "🚧 <b>Modo Manutenção</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Status: <b>{'🔴 LIGADO' if ativo else '🟢 Desligado'}</b>\n"
    )

    if agendada:
        texto += f"📅 Agendada: <b>{agendada[:16]}</b>\n"

    texto += (
        "\n💡 Quando <b>LIGADO</b>:\n"
        "├ Usuários veem a mensagem de manutenção\n"
        "├ Admins e subs continuam com acesso\n"
        "└ Bot continua recebendo pagamentos\n\n"
        "👇 Escolha uma opção:"
    )

    await _edit_or_send(query, texto, menus.admin_extras_maint_kb(ativo, agendada))


async def admin_extras_maint_toggle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    atual = await db.get_maintenance()
    novo = not atual
    await db.set_maintenance(novo)
    await db.log_admin_action(
        update.effective_user.id, "maintenance_toggle", f"novo={novo}",
    )

    await query.answer(f"{'🔴 LIGADA' if novo else '🟢 Desligada'}", show_alert=True)
    await admin_extras_maint_cb(update, context)


async def admin_extras_maint_msg_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    atual = await db.get_config("maintenance_msg", "") or MAINT_DEFAULT_MSG

    context.user_data["maint_msg_edit"] = True
    context.user_data["_maint_prompt_id"] = query.message.message_id
    context.user_data["_maint_prompt_chat"] = query.message.chat_id

    preview = atual[:400] + ("..." if len(atual) > 400 else "")

    try:
        await query.edit_message_text(
            "📝 <b>Mensagem de manutenção</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📄 <b>Mensagem atual:</b>\n"
            "╭─────────────────╮\n"
            f"{preview}\n"
            "╰─────────────────╯\n\n"
            "Envie o novo texto.\n\n"
            "💡 Envie <code>resetar</code> para voltar ao padrão.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_extras_maint_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("maint_msg_edit"):
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or ""

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("maint_msg_edit", None)
        await _delete_prompt(context, "_maint_prompt_id", "_maint_prompt_chat")
        return

    if not texto.strip():
        return

    if texto.strip().lower() == "resetar":
        await db.set_config("maintenance_msg", "")
        msg = "🔄 Mensagem resetada para o padrão!"
    else:
        await db.set_config("maintenance_msg", texto)
        msg = "✅ Mensagem atualizada!"

    context.user_data.pop("maint_msg_edit", None)
    await _delete_prompt(context, "_maint_prompt_id", "_maint_prompt_chat")
    await db.log_admin_action(update.effective_user.id, "maintenance_msg")

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_extras_maint_sched_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "📅 <b>Agendar Manutenção</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Em quanto tempo a manutenção deve ligar?\n\n"
        "💡 Você será avisado(a) e poderá cancelar antes."
    )
    await _edit_or_send(query, texto, menus.admin_extras_maint_sched_kb())


async def admin_extras_maint_sched_set_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        minutos = int(query.data.split(":")[2])
    except (ValueError, IndexError):
        return

    await db.maintenance_set_agendada(minutos)
    await db.log_admin_action(
        update.effective_user.id, "maintenance_sched", f"{minutos} min",
    )

    await query.answer(f"📅 Agendada em {minutos} min", show_alert=True)
    await admin_extras_maint_cb(update, context)


async def admin_extras_maint_sched_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    await db.maintenance_set_agendada(None)
    await db.log_admin_action(update.effective_user.id, "maintenance_sched_cancel")

    await query.answer("❌ Agendamento cancelado!", show_alert=True)
    await admin_extras_maint_cb(update, context)


# ═══════════════════════════════════════════════
# SISTEMA
# ═══════════════════════════════════════════════
async def admin_extras_system_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    info = await db.system_info()
    uptime = datetime.now() - BOOT_TIME
    h, resto = divmod(int(uptime.total_seconds()), 3600)
    m = resto // 60

    texto = (
        "🖥️ <b>Status do Sistema</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏱️ <b>Runtime:</b>\n"
        f"├ Uptime: <b>{h}h {m}min</b>\n"
        f"├ Python: <b>{info['python']}</b>\n"
        f"└ OS: <b>{info['plataforma'][:50]}</b>\n\n"
        "💾 <b>Banco:</b>\n"
        f"├ Tamanho: <b>{info['tamanho_db_mb']:.2f} MB</b>\n"
        f"├ 👥 Usuários: <b>{info['users']}</b>\n"
        f"├ 🛒 Compras: <b>{info['compras']}</b>\n"
        f"├ 📦 Produtos: <b>{info['produtos']}</b>\n"
        f"└ 📥 Itens estoque: <b>{info['estoque']}</b>\n\n"
        "🏥 <b>Saúde:</b>\n"
        f"└ Status geral: {'🟢 OK' if info['tamanho_db_mb'] < 100 else '🟡 DB grande'}"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🔄 Atualizar", callback_data="admin:extras_system")],
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:extras")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# RESTART
# ═══════════════════════════════════════════════
async def admin_extras_restart_soft_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        await query.edit_message_text(
            "🔁 <b>Restart soft</b>\n\n"
            "Recarrega o cache do bot (textos, botões, configs).\n\n"
            "Não derruba usuários conectados.\n\n"
            "🔄 Recarregando...",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await asyncio.sleep(1)

    try:
        await cache.load_all()

        await db.log_admin_action(update.effective_user.id, "restart_soft")

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "✅ <b>Restart soft concluído!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "├ 🔄 Cache recarregado\n"
                "├ 📝 Textos atualizados\n"
                "├ 🔘 Botões atualizados\n"
                "└ ⚙️ Configs atualizadas\n\n"
                "🟢 Sistema online"
            ),
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro restart soft: %s", e)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"⚠️ Restart soft com avisos: {e}",
            reply_markup=menus.admin_back_kb(),
        )


async def admin_extras_restart_hard_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "⚡ <b>RESTART HARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ <b>ATENÇÃO:</b> isso vai matar o processo do bot.\n\n"
        "▶️ O Render reinicia o serviço automaticamente em ~30s.\n"
        "▶️ Usuários perdem o estado de conversa atual.\n"
        "▶️ Novos comandos vão esperar o bot voltar.\n\n"
        "Tem certeza?"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⚡ SIM, MATAR PROCESSO", callback_data="admin:extras_restart_hard_yes")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data="admin:extras")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_extras_restart_hard_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        await query.edit_message_text(
            "⚡ <b>Reiniciando o bot...</b>\n\n"
            "O processo vai ser encerrado agora.\n"
            "Aguarde ~30s e o bot volta sozinho.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await db.log_admin_action(update.effective_user.id, "restart_hard")

    await asyncio.sleep(2)

    logger.warning("🛑 RESTART HARD solicitado por %s", update.effective_user.id)

    os._exit(0)


# ═══════════════════════════════════════════════
# LIMPAR SESSÕES
# ═══════════════════════════════════════════════
async def admin_extras_clear_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "🧹 <b>Limpar sessões</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Isso vai limpar o <code>user_data</code> de todos os usuários.\n\n"
        "⚠️ Quem estiver no meio de uma conversa (compra, saque, gift) "
        "vai ter que começar de novo.\n\n"
        "Confirma?"
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🧹 Sim, limpar", callback_data="admin:extras_clear_yes")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data="admin:extras")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_extras_clear_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        from handlers import _state
        app = context.application
        if hasattr(app, "user_data") and app.user_data:
            for uid in list(app.user_data.keys()):
                if uid != update.effective_user.id:
                    _state.clear_all(app.user_data[uid])
    except Exception as e:
        logger.warning("Erro limpando user_data: %s", e)

    await db.log_admin_action(update.effective_user.id, "clear_sessions")

    await _edit_or_send(
        query,
        "🧹 <b>Sessões limpas!</b>\n\n"
        "Todos os estados de conversa foram resetados.",
        menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# JOBS AUTOMÁTICOS
# ═══════════════════════════════════════════════
async def job_backup_auto(context: ContextTypes.DEFAULT_TYPE):
    try:
        ligado = (await db.get_config("backup_auto", "0")) == "1"
        if not ligado:
            return

        conteudo = await db.admin_backup_bytes()
        filename = f"auto-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"

        from config import STOCK_CHANNEL_ID, NOTIF_CHANNEL_ID
        destino = STOCK_CHANNEL_ID or NOTIF_CHANNEL_ID

        if destino:
            try:
                await context.bot.send_document(
                    chat_id=destino,
                    document=InputFile(io.BytesIO(conteudo), filename=filename),
                    caption=f"💾 Backup automático — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                )
            except Exception as e:
                logger.warning("Falha env backup pro canal: %s", e)
                if ADMIN_IDS:
                    try:
                        await context.bot.send_document(
                            chat_id=ADMIN_IDS[0],
                            document=InputFile(io.BytesIO(conteudo), filename=filename),
                            caption="💾 Backup automático (fallback)",
                        )
                    except Exception:
                        pass
        else:
            if ADMIN_IDS:
                try:
                    await context.bot.send_document(
                        chat_id=ADMIN_IDS[0],
                        document=InputFile(io.BytesIO(conteudo), filename=filename),
                        caption="💾 Backup automático",
                    )
                except Exception:
                    pass

        await db.backup_register(filename, len(conteudo), None)
        logger.info("Backup automático gerado: %s", filename)
    except Exception as e:
        logger.exception("Erro backup auto: %s", e)


async def job_maintenance_check(context: ContextTypes.DEFAULT_TYPE):
    try:
        ativou = await db.maintenance_check_agendada()
        if ativou:
            logger.info("Manutenção agendada ATIVADA")
            if ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_IDS[0],
                        text="🚧 <b>Manutenção agendada ativada!</b>\n\n"
                             "O bot está em manutenção agora.",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass
    except Exception as e:
        logger.exception("Erro maint check: %s", e)
