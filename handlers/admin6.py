import logging
from telegram import Update, ForceReply, InputFile
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)


def is_admin_master(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════
# SUB-ADMINS — LISTA
# ═══════════════════════════════════════════════
async def admin_subadmins_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    subs = await db.admin_list_subadmins()

    if not subs:
        texto = (
            "🛡 <b>Sub-Admins</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Nenhum sub-admin cadastrado.</i>"
        )
    else:
        texto = (
            f"🛡 <b>Sub-Admins</b> ({len(subs)})\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            "Toque em um pra editar:"
        )

    await _edit_or_send(query, texto, menus.admin_subadmins_kb(subs))


# ═══════════════════════════════════════════════
# SUB-ADMINS — ADICIONAR (fluxo passo a passo)
# ═══════════════════════════════════════════════
async def admin_sub_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    context.user_data["admin_sub_add"] = {"step": "id"}

    try:
        await query.edit_message_text(
            "➕ <b>Adicionar Sub-Admin</b>\n\n"
            "Envie o <b>ID</b> do usuário que será sub-admin:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_sub_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("admin_sub_add")
    if not state:
        return
    if not is_admin_master(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    # Passo 1: ID
    if state["step"] == "id":
        if not texto.isdigit():
            await update.message.reply_text("❌ ID inválido. Envie só números.")
            return

        user_id = int(texto)
        u = await db.get_user(user_id)
        if not u:
            await update.message.reply_text(
                "❌ Usuário não encontrado. Ele precisa ter iniciado o bot primeiro."
            )
            return

        state["user_id"] = user_id
        state["step"] = "nome"

        await update.message.reply_text(
            f"✅ Usuário encontrado: <b>{u.get('first_name') or '—'}</b>\n\n"
            "Agora envie um <b>nome/apelido</b> pro sub-admin:",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
        return

    # Passo 2: Nome → Salva com permissão 'all' e depois abre o editor
    if state["step"] == "nome":
        nome = texto
        user_id = state["user_id"]
        context.user_data.pop("admin_sub_add", None)

        await db.admin_add_subadmin(user_id, nome, "all")
        await db.log_admin_action(
            update.effective_user.id, "subadmin_add", str(user_id), nome
        )

        await update.message.reply_text(
            f"✅ <b>Sub-admin adicionado!</b>\n\n"
            f"👤 Nome: <b>{nome}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"🔓 Permissões: <b>all</b>\n\n"
            "Edite as permissões abaixo se quiser:",
            reply_markup=menus.admin_sub_permissoes_kb(user_id),
            parse_mode=ParseMode.HTML,
        )
        return


# ═══════════════════════════════════════════════
# SUB-ADMINS — VER DETALHE
# ═══════════════════════════════════════════════
async def admin_sub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    user_id = int(query.data.split(":")[2])
    sub = await db.admin_get_subadmin(user_id)
    if not sub:
        await _edit_or_send(query, "❌ Sub-admin não encontrado.", menus.admin_back_kb())
        return

    u = await db.get_user(user_id)
    nome_telegram = (u or {}).get("first_name") or "—"

    texto = (
        f"🛡 <b>Sub-Admin</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🏷️ Apelido: <b>{sub.get('nome') or '—'}</b>\n"
        f"👤 Telegram: <b>{nome_telegram}</b>\n\n"
        f"🔓 <b>Permissões:</b>\n"
        f"<code>{sub.get('permissoes', 'all')}</code>\n\n"
        f"📅 Adicionado em: {str(sub.get('created_at') or '')[:16]}"
    )

    await _edit_or_send(query, texto, menus.admin_subadmin_kb(user_id))


# ═══════════════════════════════════════════════
# SUB-ADMINS — EDITAR PERMISSÕES
# ═══════════════════════════════════════════════
async def admin_sub_edit_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    user_id = int(query.data.split(":")[2])
    sub = await db.admin_get_subadmin(user_id)
    if not sub:
        return

    perms = sub.get("permissoes", "all")

    texto = (
        f"🔓 <b>Permissões de {sub.get('nome')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Atuais: <code>{perms}</code>\n\n"
        "Toque pra adicionar/remover permissão:"
    )
    await _edit_or_send(query, texto, menus.admin_sub_permissoes_kb(user_id))


async def admin_sub_toggle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    parts = query.data.split(":")
    user_id = int(parts[2])
    area = parts[3]

    sub = await db.admin_get_subadmin(user_id)
    if not sub:
        return

    perms = sub.get("permissoes", "") or ""

    if perms == "all":
        # Se era "all", vira só a área desejada
        perms = area
    else:
        atual = [p.strip() for p in perms.split(",") if p.strip()]
        if area in atual:
            atual.remove(area)
        else:
            atual.append(area)

        perms = ",".join(atual) if atual else ""

    await db.admin_add_subadmin(user_id, sub.get("nome") or "", perms)
    await db.log_admin_action(
        update.effective_user.id, "subadmin_perms", str(user_id), perms
    )

    await admin_sub_edit_cb(update, context)


async def admin_sub_all_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    user_id = int(query.data.split(":")[2])
    sub = await db.admin_get_subadmin(user_id)
    if not sub:
        return

    await db.admin_add_subadmin(user_id, sub.get("nome") or "", "all")
    await db.log_admin_action(
        update.effective_user.id, "subadmin_all", str(user_id)
    )

    await admin_sub_edit_cb(update, context)


# ═══════════════════════════════════════════════
# SUB-ADMINS — REMOVER
# ═══════════════════════════════════════════════
async def admin_sub_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    user_id = int(query.data.split(":")[2])
    await db.admin_remove_subadmin(user_id)
    await db.log_admin_action(
        update.effective_user.id, "subadmin_del", str(user_id)
    )

    await _edit_or_send(
        query,
        "🗑️ <b>Sub-admin removido.</b>",
        menus.admin_subadmins_kb(await db.admin_list_subadmins()),
    )


# ═══════════════════════════════════════════════
# EXPORTAR CSV
# ═══════════════════════════════════════════════
async def admin_export_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    texto = (
        "📤 <b>Exportar dados</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha o que exportar (formato CSV, abre no Excel):"
    )
    await _edit_or_send(query, texto, menus.admin_export_kb())


async def admin_export_run_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_master(update.effective_user.id):
        return

    tipo = query.data.split(":")[2]

    try:
        if tipo == "users":
            conteudo = await db.admin_export_users_csv()
            nome_arquivo = "usuarios.csv"
        elif tipo == "purchases":
            conteudo = await db.admin_export_purchases_csv()
            nome_arquivo = "vendas.csv"
        elif tipo == "withdrawals":
            conteudo = await db.admin_export_withdrawals_csv()
            nome_arquivo = "saques.csv"
        else:
            return

        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=InputFile(conteudo.encode("utf-8"), filename=nome_arquivo),
            caption=f"📤 <b>{nome_arquivo}</b>",
            parse_mode=ParseMode.HTML,
        )
        await db.log_admin_action(
            update.effective_user.id, "export", tipo
        )
    except Exception as e:
        logger.exception("Erro exportando: %s", e)
        await _edit_or_send(query, f"❌ Erro: {e}", menus.admin_back_kb())


# ═══════════════════════════════════════════════
# HELPERS — VERIFICAÇÃO DE PERMISSÃO
# ═══════════════════════════════════════════════
async def check_admin_perm(user_id: int, area: str) -> bool:
    """
    Helper pra ser usado nos outros handlers.
    Ex: if not await check_admin_perm(user_id, 'users'): return
    """
    ok, perms = await db.admin_is_admin_or_sub(user_id)
    if not ok:
        return False
    return db.sub_tem_permissao(perms, area)
