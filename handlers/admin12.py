"""
Módulo ADMIN — CONFIG + TEXTOS + BOTÕES (v2 — completo).
"""
import io
import json
import logging
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache

logger = logging.getLogger(__name__)

LABELS = {
    "store_name":    "🏪 Nome da loja",
    "cnpj":          "📄 CNPJ",
    "horario":       "🕐 Horário de atendimento",
    "whatsapp_link": "📱 Link do WhatsApp",
    "telegram_link": "💬 Link do Telegram",
    "bonus_rate":    "🎁 Bônus de recarga (%)",
    "topup_min":     "💵 Recarga mínima (R$)",
    "withdraw_min":  "💸 Saque mínimo (R$)",
    "commission":    "🧲 Comissão de afiliado (%)",
}

NUMERIC_FIELDS = {"bonus_rate", "topup_min", "withdraw_min", "commission"}


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
# CONFIG — MENU
# ═══════════════════════════════════════════════
async def admin_cfg_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    cfg = await db.admin_configs_all()

    def get(k, d="—"):
        return cfg.get(k, d)

    texto = (
        "⚙️ <b>Configurações do Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏪 Nome: <b>{get('store_name', 'Minha Loja')[:35]}</b>\n"
        f"📄 CNPJ: <code>{get('cnpj')[:25]}</code>\n"
        f"🕐 Horário: <b>{get('horario')[:30]}</b>\n"
        f"📱 WhatsApp: <code>{get('whatsapp_link')[:35]}</code>\n"
        f"💬 Telegram: <code>{get('telegram_link')[:35]}</code>\n\n"
        f"🎁 Bônus recarga: <b>{get('bonus_rate', '10')}%</b>\n"
        f"💵 Recarga mínima: <b>R$ {get('topup_min', '4.00')}</b>\n"
        f"💸 Saque mínimo: <b>R$ {get('withdraw_min', '20.00')}</b>\n"
        f"🧲 Comissão afiliado: <b>{get('commission', '20')}%</b>\n\n"
        "📊 <b>Outras:</b>\n"
        f"├ Total de configs: <b>{len(cfg)}</b>\n"
        f"└ Manutenção: <b>{'🔴 ON' if get('maintenance') == '1' else '🟢 OFF'}</b>\n\n"
        "👉 Toque em uma config para editar:"
    )

    await _edit_or_send(query, texto, menus.admin_cfg_v2_kb())


# ═══════════════════════════════════════════════
# CONFIG — EDITAR
# ═══════════════════════════════════════════════
async def admin_cfg_v2_edit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        key = query.data.split(":")[2]
    except IndexError:
        return

    cfg = await db.admin_configs_all()
    valor_atual = cfg.get(key, "—")

    context.user_data["admin_cfg2_edit"] = key
    context.user_data["_cfg_prompt_id"] = query.message.message_id
    context.user_data["_cfg_prompt_chat"] = query.message.chat_id

    dica = ""
    if key in NUMERIC_FIELDS:
        dica = "\n\n💡 <i>Envie apenas números (ex: 20 ou 4.50)</i>"
    elif "link" in key:
        dica = "\n\n💡 <i>Envie URL completa (ex: https://...)</i>"

    try:
        await query.edit_message_text(
            f"✏️ <b>Editar: {LABELS.get(key, key)}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Valor atual:\n<code>{str(valor_atual)[:200]}</code>"
            f"{dica}\n\n"
            "Envie o novo valor:",
            reply_markup=menus.admin_cfg_v2_edit_kb(key),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_cfg_v2_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("admin_cfg2_edit")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_cfg2_edit", None)
        await _delete_prompt(context, "_cfg_prompt_id", "_cfg_prompt_chat")
        return

    if not texto:
        return

    erro = None
    if key in NUMERIC_FIELDS:
        try:
            v = float(texto.replace(",", "."))
            if v < 0:
                raise ValueError
        except ValueError:
            erro = "❌ Valor inválido. Envie um número positivo."

    if erro:
        await _edit_prompt_error(
            context, "_cfg_prompt_id", "_cfg_prompt_chat",
            erro + f"\n\n✏️ <b>Editar: {LABELS.get(key, key)}</b>\n\nEnvie o novo valor:",
            menus.admin_cfg_v2_edit_kb(key),
        )
        return

    context.user_data.pop("admin_cfg2_edit", None)

    await db.set_config(key, texto)
    cache.set_config(key, texto)

    await db.log_admin_action(
        update.effective_user.id, "cfg_edit", key, texto[:60],
    )

    await _delete_prompt(context, "_cfg_prompt_id", "_cfg_prompt_chat")

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ <b>{LABELS.get(key, key)} atualizado!</b>\n\n"
                f"Novo valor: <code>{texto[:200]}</code>"
            ),
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# CONFIG — RESET
# ═══════════════════════════════════════════════
async def admin_cfg_v2_reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    await db.admin_config_reset(key)

    cfg = await db.admin_configs_all()
    cache.set_config(key, cfg.get(key, ""))

    await db.log_admin_action(update.effective_user.id, "cfg_reset", key)

    await query.answer("🔄 Config resetada!", show_alert=True)
    query.data = f"admin:cfg2_edit:{key}"
    await admin_cfg_v2_edit_cb(update, context)


# ═══════════════════════════════════════════════
# CONFIG — DELETAR
# ═══════════════════════════════════════════════
async def admin_cfg_v2_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    await db.admin_config_delete(key)
    cache.set_config(key, "")
    await db.log_admin_action(update.effective_user.id, "cfg_del", key)

    await _edit_or_send(
        query,
        f"🗑️ <b>Config removida:</b> <code>{key}</code>",
        menus.admin_back_kb(),
    )


# ═══════════════════════════════════════════════
# CONFIG — ADICIONAR CUSTOM
# ═══════════════════════════════════════════════
async def admin_cfg_v2_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_cfg2_add"] = {"step": "key"}
    context.user_data["_cfg_prompt_id"] = query.message.message_id
    context.user_data["_cfg_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            "➕ <b>Nova Config Custom</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Passo <b>1/2</b> — Nome da config\n\n"
            "Envie a <b>chave</b> (só letras, números e _):\n\n"
            "Exemplos: <code>meu_titulo</code>, <code>sla_dias</code>\n\n"
            "Envie <code>/cancelar</code> para sair.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_cfg_v2_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("admin_cfg2_add")
    if not state:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_cfg2_add", None)
        await _delete_prompt(context, "_cfg_prompt_id", "_cfg_prompt_chat")
        return

    if state["step"] == "key":
        key = texto.replace(" ", "_").lower()
        if not key.replace("_", "").isalnum():
            await _edit_prompt_error(
                context, "_cfg_prompt_id", "_cfg_prompt_chat",
                "❌ Chave inválida.\n\nUse apenas letras, números e _ (underline).\n\n"
                "Envie a nova chave:",
            )
            return

        cfg = await db.admin_configs_all()
        if key in cfg:
            await _edit_prompt_error(
                context, "_cfg_prompt_id", "_cfg_prompt_chat",
                f"❌ A chave <code>{key}</code> já existe.\n\nEscolha outra:",
            )
            return

        state["key"] = key
        state["step"] = "value"
        await _edit_prompt_error(
            context, "_cfg_prompt_id", "_cfg_prompt_chat",
            f"Passo <b>2/2</b> — Valor\n\n"
            f"Chave: <code>{key}</code>\n\n"
            "Envie o <b>valor</b> dessa config:",
        )
        return

    if state["step"] == "value":
        key = state["key"]
        valor = texto

        await db.set_config(key, valor)
        cache.set_config(key, valor)
        context.user_data.pop("admin_cfg2_add", None)
        await _delete_prompt(context, "_cfg_prompt_id", "_cfg_prompt_chat")

        await db.log_admin_action(update.effective_user.id, "cfg_add", key, valor[:60])

        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"✅ <b>Config criada!</b>\n\n"
                    f"🔑 Chave: <code>{key}</code>\n"
                    f"📝 Valor: <code>{valor[:100]}</code>"
                ),
                reply_markup=menus.admin_back_kb(),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# TEXTOS — LISTA
# ═══════════════════════════════════════════════
async def admin_texts_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    textos = await db.admin_texts_all()
    visiveis = [t for t in textos if not t["key"].startswith("__")]

    texto = (
        f"📝 <b>Textos do Bot</b> ({len(visiveis)})\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um texto pra ver/editar:"
    )
    await _edit_or_send(query, texto, menus.admin_texts_v2_kb(textos))


# ═══════════════════════════════════════════════
# TEXTOS — VISUALIZAR
# ═══════════════════════════════════════════════
async def admin_text_v2_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        key = query.data.split(":", 2)[2]
    except IndexError:
        return

    valor = await db.admin_get_text(key)
    if valor is None:
        await _edit_or_send(query, "❌ Texto não encontrado.", menus.admin_back_kb())
        return

    if len(valor) > 900:
        preview = valor[:900] + "\n\n<i>... (mostrando 900 chars)</i>"
    else:
        preview = valor

    template_vars = ""
    if "{" in valor:
        import re
        vars_encontradas = set(re.findall(r"\{(\w+)\}", valor))
        if vars_encontradas:
            template_vars = "\n\n🔧 <b>Variáveis disponíveis:</b>\n" + ", ".join(
                f"<code>{{{v}}}</code>" for v in sorted(vars_encontradas)
            )

    texto = (
        f"📝 <b>{key}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{preview}"
        f"{template_vars}"
    )

    kb = menus.admin_text_v2_view_kb(key)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# TEXTOS — EDITAR
# ═══════════════════════════════════════════════
async def admin_text_v2_edit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        key = query.data.split(":", 2)[2]
    except IndexError:
        return

    context.user_data["admin_text2_edit"] = key
    context.user_data["_txt_prompt_id"] = query.message.message_id
    context.user_data["_txt_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            f"✏️ <b>Editando: {key}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie o novo texto. Pode usar HTML:\n"
            "├ <code>&lt;b&gt;negrito&lt;/b&gt;</code>\n"
            "├ <code>&lt;i&gt;itálico&lt;/i&gt;</code>\n"
            "├ <code>&lt;code&gt;mono&lt;/code&gt;</code>\n"
            "└ <code>&lt;a href=\"url\"&gt;link&lt;/a&gt;</code>\n\n"
            "💡 Variáveis tipo <code>{user_id}</code>, <code>{balance}</code>, "
            "<code>{store_name}</code> também funcionam.\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=menus.admin_text_v2_view_kb(key),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_text_v2_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("admin_text2_edit")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = update.message.text or update.message.caption or ""

    if texto.startswith("/"):
        context.user_data.pop("admin_text2_edit", None)
        await _delete_prompt(context, "_txt_prompt_id", "_txt_prompt_chat")
        return

    if not texto.strip():
        return

    await db.admin_update_text(key, texto)
    cache.set_text(key, texto)
    context.user_data.pop("admin_text2_edit", None)

    await db.log_admin_action(update.effective_user.id, "text_edit", key)

    await _delete_prompt(context, "_txt_prompt_id", "_txt_prompt_chat")

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ <b>Texto atualizado!</b>\n\n"
                f"📝 Chave: <code>{key}</code>\n"
                f"📊 Tamanho: <b>{len(texto)} caracteres</b>"
            ),
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# TEXTOS — RESET
# ═══════════════════════════════════════════════
async def admin_text_v2_reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    ok = await db.admin_text_reset(key)

    if not ok:
        await query.answer("⚠️ Este texto não tem versão padrão.", show_alert=True)
        return

    novo_valor = await db.admin_get_text(key)
    cache.set_text(key, novo_valor or "")

    await db.log_admin_action(update.effective_user.id, "text_reset", key)
    await query.answer("🔄 Texto resetado!", show_alert=True)

    query.data = f"admin:text2_view:{key}"
    await admin_text_v2_view_cb(update, context)


# ═══════════════════════════════════════════════
# TEXTOS — BUSCAR
# ═══════════════════════════════════════════════
async def admin_text_v2_search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_text2_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar texto</b>\n\n"
            "Envie a <b>chave</b> ou parte do <b>conteúdo</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_text_v2_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_text2_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("admin_text2_search", None)

    if not term:
        return

    resultados = await db.admin_texts_search(term)

    if not resultados:
        await update.message.reply_text(
            f"❌ Nada encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados ({len(resultados)}):</b>"
    kb = menus.admin_texts_v2_kb(resultados)
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# BOTÕES — LISTA
# ═══════════════════════════════════════════════
async def admin_buttons_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    botoes = await db.admin_buttons_all()

    texto = (
        f"🔘 <b>Botões do Bot</b> ({len(botoes)})\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Toque em um botão pra ver/editar:"
    )
    await _edit_or_send(query, texto, menus.admin_buttons_v2_kb(botoes))


# ═══════════════════════════════════════════════
# BOTÕES — VISUALIZAR
# ═══════════════════════════════════════════════
async def admin_btn_v2_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        key = query.data.split(":", 2)[2]
    except IndexError:
        return

    valor = await db.admin_get_button(key)
    if valor is None:
        await _edit_or_send(query, "❌ Botão não encontrado.", menus.admin_back_kb())
        return

    texto = (
        f"🔘 <b>Botão</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔑 Chave: <code>{key}</code>\n"
        f"📝 Valor: <b>{valor}</b>"
    )

    kb = menus.admin_button_v2_view_kb(key)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# BOTÕES — EDITAR
# ═══════════════════════════════════════════════
async def admin_btn_v2_edit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        key = query.data.split(":", 2)[2]
    except IndexError:
        return

    context.user_data["admin_btn2_edit"] = key
    context.user_data["_btn_prompt_id"] = query.message.message_id
    context.user_data["_btn_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            f"✏️ <b>Editando botão: {key}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie o novo texto do botão (com emoji se quiser):\n\n"
            "💡 Exemplo: <code>🛒 Comprar Agora</code>\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=menus.admin_button_v2_view_kb(key),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_btn_v2_edit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("admin_btn2_edit")
    if not key:
        return
    if not is_admin(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("admin_btn2_edit", None)
        await _delete_prompt(context, "_btn_prompt_id", "_btn_prompt_chat")
        return

    if not texto:
        return

    await db.admin_update_button(key, texto)
    cache.set_button(key, texto)
    context.user_data.pop("admin_btn2_edit", None)

    await db.log_admin_action(update.effective_user.id, "button_edit", key, texto)

    await _delete_prompt(context, "_btn_prompt_id", "_btn_prompt_chat")

    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ <b>Botão atualizado!</b>\n\n"
                f"🔑 Chave: <code>{key}</code>\n"
                f"📝 Novo: <b>{texto}</b>"
            ),
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# BOTÕES — RESET
# ═══════════════════════════════════════════════
async def admin_btn_v2_reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    key = query.data.split(":", 2)[2]
    ok = await db.admin_button_reset(key)

    if not ok:
        await query.answer("⚠️ Este botão não tem versão padrão.", show_alert=True)
        return

    novo = await db.admin_get_button(key)
    cache.set_button(key, novo or "")
    await db.log_admin_action(update.effective_user.id, "button_reset", key)

    await query.answer("🔄 Botão resetado!", show_alert=True)
    query.data = f"admin:btn2_view:{key}"
    await admin_btn_v2_view_cb(update, context)


# ═══════════════════════════════════════════════
# BOTÕES — BUSCAR
# ═══════════════════════════════════════════════
async def admin_btn_v2_search_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_btn2_search"] = True

    try:
        await query.edit_message_text(
            "🔍 <b>Buscar botão</b>\n\n"
            "Envie a <b>chave</b> ou parte do <b>texto</b>:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_btn_v2_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_btn2_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data.pop("admin_btn2_search", None)

    if not term:
        return

    resultados = await db.admin_buttons_search(term)

    if not resultados:
        await update.message.reply_text(
            f"❌ Nada encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = f"🔍 <b>Resultados ({len(resultados)}):</b>"
    kb = menus.admin_buttons_v2_kb(resultados)
    await update.message.reply_text(texto, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# EXPORTAR / IMPORTAR JSON
# ═══════════════════════════════════════════════
async def admin_cfg_v2_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        json_text = await db.admin_configs_export()
        from datetime import datetime
        filename = f"config-backup-{datetime.now().strftime('%Y%m%d-%H%M')}.json"

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(
                io.BytesIO(json_text.encode("utf-8")),
                filename=filename,
            ),
            caption=(
                "📤 <b>Backup de configurações</b>\n\n"
                "Inclui configs, textos e botões.\n"
                "Guarde em local seguro."
            ),
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(update.effective_user.id, "cfg_export")
    except Exception as e:
        logger.exception("Erro export config: %s", e)
        await query.answer(f"❌ Erro: {e}", show_alert=True)


async def admin_cfg_v2_import_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_cfg2_import"] = True

    try:
        await query.edit_message_text(
            "📥 <b>Importar configurações</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>Atenção:</b> isso vai <b>sobrescrever</b> as configs, "
            "textos e botões atuais.\n\n"
            "Envie o arquivo <b>JSON</b> gerado pelo Exportar.\n\n"
            "Envie <code>/cancelar</code> para sair.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_cfg_v2_import_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_cfg2_import"):
        return
    if not is_admin(update.effective_user.id):
        return

    doc = update.message.document
    if not doc:
        return

    try:
        file = await context.bot.get_file(doc.file_id)
        data = await file.download_as_bytearray()
        conteudo = json.loads(data.decode("utf-8"))
    except Exception as e:
        await update.message.reply_text(f"❌ JSON inválido: {e}")
        return

    context.user_data.pop("admin_cfg2_import", None)

    try:
        resumo = await db.admin_configs_import(conteudo)
        await cache.load_all()

        await db.log_admin_action(
            update.effective_user.id, "cfg_import",
            f"cfg={resumo['config']} txt={resumo['texts']} btn={resumo['buttons']}",
        )

        await update.message.reply_text(
            "✅ <b>Importação concluída!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"├ ⚙️ Configs: <b>{resumo['config']}</b>\n"
            f"├ 📝 Textos: <b>{resumo['texts']}</b>\n"
            f"├ 🔘 Botões: <b>{resumo['buttons']}</b>\n"
            "└ 🔄 Cache recarregado",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro import cfg: %s", e)
        await update.message.reply_text(f"❌ Erro: {e}")
