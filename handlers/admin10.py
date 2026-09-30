"""
Módulo ADMIN — TRANSMISSÃO (v2 — completo).
Suporta: preview, agendamento, progresso, rascunhos, histórico.
"""
import asyncio
import logging
import io
from datetime import datetime, timedelta
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

SEGMENTOS = {
    "todos": "📢 Todos os usuários",
    "compradores": "🛒 Apenas compradores",
    "inativos": "💤 Inativos 7d+",
    "sem_saldo": "📭 Sem saldo",
}

# Progresso é atualizado a cada N envios (pra não floodar)
PROGRESS_EVERY = 25


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# MENU PRINCIPAL
# ═══════════════════════════════════════════════
async def admin_bc_v2_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    stats = await db.bc_stats()

    texto = (
        "📢 <b>Transmissão em Massa</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 <b>Resumo:</b>\n"
        f"├ 📝 Rascunhos: <b>{stats['rascunhos']}</b>\n"
        f"├ 📅 Agendadas: <b>{stats['agendadas']}</b>\n"
        f"├ ✅ Enviadas: <b>{stats['enviadas']}</b>\n"
        f"└ 📤 Total de mensagens entregues: <b>{stats['total_enviados']}</b>\n\n"
        "👇 O que você quer fazer?"
    )

    kb = menus.admin_bc_v2_menu_kb(stats["agendadas"], stats["rascunhos"])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# NOVA — escolher segmento
# ═══════════════════════════════════════════════
async def admin_bc_v2_nova_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    # limpa qualquer wizard anterior
    for k in ("bc_texto", "bc_midia_id", "bc_midia_tipo", "bc_segmento",
              "bc_botoes", "bc_preview_id"):
        context.user_data.pop(k, None)

    texto = (
        "📢 <b>Nova Transmissão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Passo <b>1/3</b> — Escolha o <b>público</b>:"
    )
    await _edit_or_send(query, texto, menus.admin_bc_v2_segment_kb())


async def admin_bc_v2_segment_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    seg = query.data.split(":")[2]
    context.user_data["bc_segmento"] = seg

    # Conta destinos
    try:
        ids = await db.bc_segment_user_ids(seg)
        total = len(ids)
    except Exception:
        total = 0

    seg_label = SEGMENTOS.get(seg, seg)

    texto = (
        "📢 <b>Nova Transmissão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Público: <b>{seg_label}</b>\n"
        f"📊 Destinatários: <b>{total}</b>\n\n"
        "Passo <b>2/3</b> — Envie o <b>conteúdo</b>:\n\n"
        "Você pode enviar:\n"
        "├ 📝 Só <b>texto</b> (aceita HTML)\n"
        "├ 🖼 <b>Foto</b> com legenda\n"
        "└ 🎥 <b>Vídeo</b> com legenda\n\n"
        "💡 Para adicionar botões, envie: <code>+botao|Texto do botão|acao</code>\n"
        "Exemplo: <code>+botao|Comprar agora|direct:catalog</code>\n\n"
        "Envie <code>/cancelar</code> para sair."
    )

    context.user_data["bc_aguardando_conteudo"] = True

    try:
        await query.edit_message_text(texto, parse_mode=ParseMode.HTML)
    except Exception:
        pass


# ═══════════════════════════════════════════════
# RECEBE CONTEÚDO (texto ou mídia)
# ═══════════════════════════════════════════════
async def admin_bc_v2_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("bc_aguardando_conteudo"):
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or update.message.caption or ""

    if texto.startswith("/"):
        context.user_data.pop("bc_aguardando_conteudo", None)
        context.user_data.pop("bc_segmento", None)
        await update.message.reply_text("❌ Cancelado.")
        return

    midia_id = None
    midia_tipo = None

    if update.message.photo:
        midia_id = update.message.photo[-1].file_id
        midia_tipo = "photo"
    elif update.message.video:
        midia_id = update.message.video.file_id
        midia_tipo = "video"

    # Guarda
    context.user_data["bc_texto"] = texto
    context.user_data["bc_midia_id"] = midia_id
    context.user_data["bc_midia_tipo"] = midia_tipo

    # Cria rascunho no banco pra preview
    try:
        bc_id = await db.bc_create(
            segmento=context.user_data.get("bc_segmento", "todos"),
            texto=texto,
            midia_id=midia_id,
            midia_tipo=midia_tipo,
            botoes=context.user_data.get("bc_botoes") or [],
            created_by=update.effective_user.id,
        )
        context.user_data["bc_preview_id"] = bc_id
    except Exception as e:
        logger.exception("Erro criando rascunho: %s", e)

    context.user_data.pop("bc_aguardando_conteudo", None)

    await _mostrar_preview(update, context)


async def _mostrar_preview(update, context):
    """Mostra preview do que vai ser enviado."""
    texto = context.user_data.get("bc_texto") or ""
    midia = context.user_data.get("bc_midia_id")
    tipo = context.user_data.get("bc_midia_tipo")
    seg = context.user_data.get("bc_segmento") or "todos"

    try:
        ids = await db.bc_segment_user_ids(seg)
        total = len(ids)
    except Exception:
        total = 0

    seg_label = SEGMENTOS.get(seg, seg)
    tipo_txt = (
        "🖼 Foto" if tipo == "photo"
        else "🎥 Vídeo" if tipo == "video"
        else "📝 Texto"
    )

    preview_text = (
        "👁 <b>Pré-visualização</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Público: <b>{seg_label}</b>\n"
        f"📊 Destinatários: <b>{total}</b>\n"
        f"📦 Formato: <b>{tipo_txt}</b>\n\n"
        "📄 <b>Conteúdo:</b>\n"
        "╭─────────────────╮\n"
        f"{texto or '<i>(sem texto)</i>'}\n"
        "╰─────────────────╯\n\n"
        "Passo <b>3/3</b> — Confirme:"
    )

    chat_id = update.effective_chat.id

    # Se tem mídia, manda a mídia primeiro
    if midia and tipo == "photo":
        try:
            await context.bot.send_photo(
                chat_id=chat_id, photo=midia,
                caption="<i>Prévia da foto acima</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
    elif midia and tipo == "video":
        try:
            await context.bot.send_video(
                chat_id=chat_id, video=midia,
                caption="<i>Prévia do vídeo acima</i>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=preview_text,
        reply_markup=menus.admin_bc_v2_preview_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# ENVIAR AGORA
# ═══════════════════════════════════════════════
async def admin_bc_v2_send_now_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = context.user_data.get("bc_preview_id")
    if not bc_id:
        await query.answer("Preview expirado.", show_alert=True)
        return

    # Dispara em background
    asyncio.create_task(_executar_transmissao(context.bot, bc_id, query.message.chat_id))

    try:
        await query.edit_message_text(
            "📤 <b>Transmissão iniciada!</b>\n\n"
            "Você vai receber atualizações de progresso aqui.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# EXECUTAR TRANSMISSÃO (background)
# ═══════════════════════════════════════════════
async def _executar_transmissao(bot, bc_id: str, chat_id: int):
    """Roda em background. Atualiza progresso periodicamente."""
    bc = await db.bc_get(bc_id)
    if not bc:
        return

    seg = bc.get("segmento") or "todos"
    texto = bc.get("texto") or ""
    midia = bc.get("midia_id")
    tipo = bc.get("midia_tipo")

    try:
        ids = await db.bc_segment_user_ids(seg)
    except Exception as e:
        logger.exception("Erro buscando destinatários: %s", e)
        ids = []

    total = len(ids)

    await db.bc_update(
        bc_id,
        status="sending",
        total_destinos=total,
        iniciado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        enviados=0,
        falhas=0,
    )

    # Mensagem de progresso
    try:
        progress_msg = await bot.send_message(
            chat_id=chat_id,
            text=f"⏳ <b>Enviando...</b> 0/{total}",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        progress_msg = None

    enviados = 0
    falhas = 0

    for i, uid in enumerate(ids):
        try:
            if tipo == "photo":
                await bot.send_photo(
                    chat_id=uid, photo=midia, caption=texto,
                    parse_mode=ParseMode.HTML,
                )
            elif tipo == "video":
                await bot.send_video(
                    chat_id=uid, video=midia, caption=texto,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await bot.send_message(
                    chat_id=uid, text=texto, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
            enviados += 1
        except Exception:
            falhas += 1

        # Atualiza progresso a cada N
        if progress_msg and (i + 1) % PROGRESS_EVERY == 0:
            pct = ((i + 1) / total) * 100 if total else 0
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_msg.message_id,
                    text=(
                        f"⏳ <b>Enviando...</b>\n\n"
                        f"├ ✅ Enviados: <b>{enviados}</b>\n"
                        f"├ ❌ Falhas: <b>{falhas}</b>\n"
                        f"├ 📊 Progresso: <b>{i + 1}/{total}</b> ({pct:.0f}%)\n"
                        f"└ ⏰ {datetime.now().strftime('%H:%M:%S')}"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass

        # Delay pra não estourar rate limit (30 msgs/seg)
        await asyncio.sleep(0.05)

    # Final
    await db.bc_update(
        bc_id,
        status="done",
        enviados=enviados,
        falhas=falhas,
        terminado_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    if progress_msg:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg.message_id,
                text=(
                    "✅ <b>Transmissão concluída!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"├ ✅ Enviados: <b>{enviados}</b>\n"
                    f"├ ❌ Falhas: <b>{falhas}</b>\n"
                    f"├ 📊 Total: <b>{total}</b>\n"
                    f"└ ⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ),
                reply_markup=menus.admin_back_kb(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    # Limpa wizard
    try:
        await bot.send_message(
            chat_id=chat_id,
            text="🔄 Rascunho removido automaticamente.",
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# AGENDAR
# ═══════════════════════════════════════════════
async def admin_bc_v2_schedule_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = context.user_data.get("bc_preview_id")
    if not bc_id:
        await query.answer("Preview expirado.", show_alert=True)
        return

    texto = (
        "📅 <b>Agendar Transmissão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha quando enviar:"
    )
    try:
        await query.edit_message_text(
            texto, reply_markup=menus.admin_bc_v2_schedule_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_bc_v2_sch_choice_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = context.user_data.get("bc_preview_id")
    if not bc_id:
        return

    escolha = query.data.split(":")[2]

    if escolha == "custom":
        context.user_data["bc_sch_custom"] = True
        try:
            await query.edit_message_text(
                "✏️ <b>Agendamento customizado</b>\n\n"
                "Envie o <b>tempo</b> no formato:\n"
                "<code>30 min</code> · <code>2h</code> · <code>1d 4h</code>\n\n"
                "Envie <code>/cancelar</code> para sair.",
                reply_markup=ForceReply(selective=True),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    minutos = {"5min": 5, "30min": 30, "1h": 60, "6h": 360, "1d": 1440}[escolha]

    agendado = (datetime.now() + timedelta(minutes=minutos)).strftime("%Y-%m-%d %H:%M:%S")
    await db.bc_update(bc_id, status="scheduled", agendado_para=agendado)

    await db.log_admin_action(
        update.effective_user.id, "bc_schedule", bc_id, f"em {escolha}",
    )

    context.user_data.pop("bc_preview_id", None)

    try:
        await query.edit_message_text(
            f"✅ <b>Transmissão agendada!</b>\n\n"
            f"⏰ Será enviada em: <b>{escolha}</b>\n"
            f"📅 Data: <b>{agendado[:16]}</b>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_bc_v2_sch_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("bc_sch_custom"):
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip().lower()
    context.user_data.pop("bc_sch_custom", None)

    if texto.startswith("/"):
        return

    # Parse simples
    import re
    total_min = 0
    for m in re.finditer(r"(\d+)\s*(d|h|min|m)?", texto):
        n = int(m.group(1))
        u = m.group(2) or "min"
        if u == "d":
            total_min += n * 1440
        elif u == "h":
            total_min += n * 60
        else:
            total_min += n

    if total_min <= 0:
        await update.message.reply_text(
            "❌ Formato inválido.\n\nExemplos: <code>30 min</code>, <code>2h</code>, <code>1d</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    bc_id = context.user_data.get("bc_preview_id")
    if not bc_id:
        return

    agendado = (datetime.now() + timedelta(minutes=total_min)).strftime("%Y-%m-%d %H:%M:%S")
    await db.bc_update(bc_id, status="scheduled", agendado_para=agendado)

    await db.log_admin_action(
        update.effective_user.id, "bc_schedule_custom", bc_id, f"{total_min} min",
    )

    context.user_data.pop("bc_preview_id", None)

    await update.message.reply_text(
        f"✅ <b>Agendada!</b>\n\n"
        f"⏰ Em: <b>{total_min} minutos</b>\n"
        f"📅 Data: <b>{agendado[:16]}</b>",
        reply_markup=menus.admin_back_kb(),
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════
# SALVAR RASCUNHO
# ═══════════════════════════════════════════════
async def admin_bc_v2_save_draft_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = context.user_data.get("bc_preview_id")
    if not bc_id:
        await query.answer("Preview expirado.", show_alert=True)
        return

    context.user_data.pop("bc_preview_id", None)

    await db.log_admin_action(update.effective_user.id, "bc_save_draft", bc_id)

    try:
        await query.edit_message_text(
            "📝 <b>Rascunho salvo!</b>\n\n"
            "Você pode acessá-lo depois em <b>📝 Rascunhos</b>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_bc_v2_cancel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = context.user_data.pop("bc_preview_id", None)
    if bc_id:
        try:
            await db.bc_delete(bc_id)
        except Exception:
            pass

    for k in ("bc_texto", "bc_midia_id", "bc_midia_tipo", "bc_segmento",
              "bc_botoes", "bc_aguardando_conteudo", "bc_sch_custom"):
        context.user_data.pop(k, None)

    try:
        await query.edit_message_text(
            "❌ <b>Transmissão cancelada.</b>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# LISTAS (agendadas, rascunhos, histórico)
# ═══════════════════════════════════════════════
async def admin_bc_v2_agendadas_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    items = await db.bc_list(status="scheduled", limit=15)

    if not items:
        texto = "📅 <b>Agendadas</b>\n\n<i>Nenhuma transmissão agendada.</i>"
    else:
        texto = f"📅 <b>Agendadas ({len(items)})</b>\n\n👉 Toque para gerenciar:"

    await _edit_or_send(query, texto, menus.admin_bc_v2_list_kb(items, "agendada"))


async def admin_bc_v2_rascunhos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    items = await db.bc_list(status="draft", limit=15)

    if not items:
        texto = "📝 <b>Rascunhos</b>\n\n<i>Nenhum rascunho.</i>"
    else:
        texto = f"📝 <b>Rascunhos ({len(items)})</b>\n\n👉 Toque para gerenciar:"

    await _edit_or_send(query, texto, menus.admin_bc_v2_list_kb(items, "rascunho"))


async def admin_bc_v2_historico_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    items = await db.bc_list(status="done", limit=15)

    if not items:
        texto = "📊 <b>Histórico</b>\n\n<i>Nenhuma transmissão enviada ainda.</i>"
    else:
        texto = f"📊 <b>Histórico ({len(items)})</b>\n\n👉 Toque para ver detalhes:"

    await _edit_or_send(query, texto, menus.admin_bc_v2_list_kb(items, "historico"))


# ═══════════════════════════════════════════════
# VISUALIZAR ITEM
# ═══════════════════════════════════════════════
async def admin_bc_v2_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = query.data.split(":", 2)[2]
    bc = await db.bc_get(bc_id)
    if not bc:
        await query.answer("Não encontrado.", show_alert=True)
        return

    status = bc.get("status", "draft")
    seg_label = SEGMENTOS.get(bc.get("segmento") or "?", "?")

    texto_preview = (bc.get("texto") or "")[:300]
    tipo_txt = (
        "🖼 Foto" if bc.get("midia_tipo") == "photo"
        else "🎥 Vídeo" if bc.get("midia_tipo") == "video"
        else "📝 Texto"
    )

    status_icon = {
        "draft": "📝 Rascunho",
        "scheduled": "📅 Agendada",
        "sending": "⏳ Enviando...",
        "done": "✅ Enviada",
        "cancelled": "❌ Cancelada",
    }.get(status, status)

    texto = (
        "📢 <b>Transmissão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{bc_id[:8]}</code>\n"
        f"📡 Status: <b>{status_icon}</b>\n"
        f"🎯 Público: <b>{seg_label}</b>\n"
        f"📦 Formato: <b>{tipo_txt}</b>\n\n"
        f"📄 <b>Conteúdo:</b>\n<i>{texto_preview}</i>\n"
    )

    if status == "scheduled":
        texto += f"\n📅 Agendada para: <b>{str(bc.get('agendado_para') or '')[:16]}</b>"

    if status == "done":
        en = bc.get("enviados", 0)
        fa = bc.get("falhas", 0)
        td = bc.get("total_destinos", 0)
        tx = (en / td * 100) if td else 0
        texto += (
            f"\n📊 <b>Estatísticas:</b>\n"
            f"├ ✅ Enviados: <b>{en}</b>\n"
            f"├ ❌ Falhas: <b>{fa}</b>\n"
            f"├ 📊 Total: <b>{td}</b>\n"
            f"├ 📈 Taxa: <b>{tx:.1f}%</b>\n"
            f"└ ⏰ {str(bc.get('terminado_em') or '')[:16]}"
        )

    kb = menus.admin_bc_v2_view_kb(bc_id, status)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# FORÇAR ENVIO / CANCELAR / DELETAR
# ═══════════════════════════════════════════════
async def admin_bc_v2_force_send_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = query.data.split(":", 2)[2]

    asyncio.create_task(_executar_transmissao(context.bot, bc_id, query.message.chat_id))

    try:
        await query.edit_message_text(
            "📤 <b>Enviando...</b>\n\nVocê vai ver o progresso aqui.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_bc_v2_cancel_sched_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = query.data.split(":", 2)[2]
    await db.bc_update(bc_id, status="cancelled")
    await db.log_admin_action(update.effective_user.id, "bc_cancel", bc_id)

    await _edit_or_send(
        query, "❌ <b>Agendamento cancelado.</b>", menus.admin_back_kb(),
    )


async def admin_bc_v2_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    bc_id = query.data.split(":", 2)[2]
    await db.bc_delete(bc_id)
    await db.log_admin_action(update.effective_user.id, "bc_del", bc_id)

    await _edit_or_send(
        query, "🗑️ <b>Rascunho apagado.</b>", menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# JOB — RODA A CADA 30s CHECANDO AGENDADAS
# ═══════════════════════════════════════════════
async def check_scheduled_broadcasts(context: ContextTypes.DEFAULT_TYPE):
    """Job que roda a cada 30s."""
    try:
        devidos = await db.bc_scheduled_due()
    except Exception as e:
        logger.exception("Erro checando agendadas: %s", e)
        return

    for bc in devidos:
        try:
            bc_id = bc["id"]
            created_by = bc.get("created_by") or (ADMIN_IDS[0] if ADMIN_IDS else None)
            if not created_by:
                continue

            logger.info("Disparando transmissão agendada %s", bc_id)
            asyncio.create_task(
                _executar_transmissao(context.bot, bc_id, int(created_by))
            )
        except Exception as e:
            logger.exception("Erro disparando bc %s: %s", bc.get("id"), e)
