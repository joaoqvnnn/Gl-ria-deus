"""
Módulo ADMIN — SUB-ADMINS (v2 — completo).

Funcionalidades:
  • Lista com filtros (todos / ativos / expirados)
  • Adicionar com apelido e tempo de expiração
  • Editar permissões granulares (8 áreas)
  • Tornar permanente / mudar expiração
  • Ver histórico de ações do sub
  • Logs globais
  • Remover com confirmação
  • Notifica o sub ao ganhar/perder cargo
"""
import logging
from datetime import datetime
from telegram import Update, ForceReply
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus

logger = logging.getLogger(__name__)

PERMS_LABEL = {
    "users":       "👥 Usuários",
    "products":    "📦 Produtos",
    "purchases":   "🛒 Vendas",
    "gifts":       "🎁 Gift Cards",
    "withdrawals": "💸 Saques",
    "affiliates":  "🤝 Afiliados",
    "broadcast":   "📢 Transmissão",
    "config":      "⚙️ Config",
}


def is_master(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


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
# LISTA
# ═══════════════════════════════════════════════
async def admin_sub_v2_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return
    await _render_subs(query, filtro="todos")


async def admin_sub_v2_filtro_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return
    try:
        filtro = query.data.split(":")[2]
    except IndexError:
        filtro = "todos"
    await _render_subs(query, filtro=filtro)


async def _render_subs(query, filtro: str = "todos"):
    subs = await db.admin_sub_v2_list(filtro)
    stats = await db.admin_sub_v2_stats()

    filtro_label = {
        "todos": "📋 Todos", "ativos": "🟢 Ativos", "expirados": "⚫ Expirados",
    }.get(filtro, filtro)

    texto = (
        "🛡 <b>Sub-Admins</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 Filtro: <b>{filtro_label}</b>\n\n"
        "📊 <b>Resumo:</b>\n"
        f"├ 📦 Total: <b>{stats['total']}</b>\n"
        f"├ 🟢 Ativos: <b>{stats['ativos']}</b>\n"
        f"└ ⚫ Expirados: <b>{stats['expirados']}</b>\n\n"
        f"📋 Mostrando: <b>{len(subs)}</b>\n\n"
        "🟢 Ativo   ⚫ Expirado\n"
        "👉 Toque em um sub-admin:"
    )

    kb = menus.admin_sub_v2_kb(subs, filtro)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# DETALHE
# ═══════════════════════════════════════════════
async def admin_sub_v2_view_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        await _edit_or_send(query, "❌ Sub-admin não encontrado.", menus.admin_back_kb())
        return

    u = await db.get_user(user_id)
    nome_tg = (u or {}).get("first_name") or "—"
    username = (u or {}).get("username") or "—"

    exp = sub.get("expires_at")
    exp_line = "♾️ Permanente"
    exp_status = ""

    if exp:
        try:
            exp_dt = datetime.strptime(str(exp)[:19], "%Y-%m-%d %H:%M:%S")
            exp_line = exp_dt.strftime("%d/%m/%Y %H:%M")
            if exp_dt < datetime.now():
                exp_status = " <b>(EXPIRADO)</b>"
            else:
                dias_rest = (exp_dt - datetime.now()).days
                exp_status = f" <i>({dias_rest}d restantes)</i>"
        except Exception:
            exp_line = str(exp)

    perms = sub.get("permissoes", "")
    if perms == "all":
        perms_txt = "✅ <b>TODAS as permissões</b>"
    elif not perms:
        perms_txt = "❌ <b>Nenhuma permissão</b>"
    else:
        linhas = []
        for p in perms.split(","):
            p = p.strip()
            if p:
                linhas.append(f"├ {PERMS_LABEL.get(p, p)}")
        if linhas:
            linhas[-1] = linhas[-1].replace("├", "└")
        perms_txt = "\n".join(linhas)

    total_acoes = await db.sub_count_actions(user_id)

    texto = (
        "🛡 <b>Sub-Admin</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🏷️ Apelido: <b>{sub.get('nome') or '—'}</b>\n"
        f"👤 Telegram: <b>{nome_tg}</b> (@{username})\n\n"
        f"⏰ Expira: <b>{exp_line}</b>{exp_status}\n"
        f"📅 Adicionado: <b>{str(sub.get('created_at') or '')[:16]}</b>\n\n"
        f"🔓 <b>Permissões:</b>\n{perms_txt}\n\n"
        f"📊 <b>Ações registradas:</b> <b>{total_acoes}</b>"
    )

    has_exp = bool(exp)
    kb = menus.admin_sub_v2_view_kb(user_id, has_exp)
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# ADICIONAR (wizard)
# ═══════════════════════════════════════════════
async def admin_sub_v2_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    context.user_data["sub_wizard"] = {"step": "id"}
    context.user_data["_sub_prompt_id"] = query.message.message_id
    context.user_data["_sub_prompt_chat"] = query.message.chat_id

    try:
        await query.edit_message_text(
            "➕ <b>Adicionar Sub-Admin</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Passo <b>1/3</b> — ID\n\n"
            "Envie o <b>ID do Telegram</b> do sub-admin:\n\n"
            "💡 Ele precisa ter iniciado o bot primeiro.\n\n"
            "Envie <code>/cancelar</code> para sair.",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_sub_v2_add_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("sub_wizard")
    if not state:
        return
    if not is_master(update.effective_user.id):
        return

    texto = (update.message.text or "").strip()

    try:
        await update.message.delete()
    except Exception:
        pass

    if texto.startswith("/"):
        context.user_data.pop("sub_wizard", None)
        await _delete_prompt(context, "_sub_prompt_id", "_sub_prompt_chat")
        return

    step = state["step"]

    # ─── PASSO 1: ID
    if step == "id":
        if not texto.isdigit():
            await _edit_prompt_error(
                context, "_sub_prompt_id", "_sub_prompt_chat",
                "❌ ID inválido. Envie apenas números:",
                ForceReply(selective=True),
            )
            return

        user_id = int(texto)
        if user_id in ADMIN_IDS:
            await _edit_prompt_error(
                context, "_sub_prompt_id", "_sub_prompt_chat",
                "❌ Esse user já é admin master.",
                ForceReply(selective=True),
            )
            return

        u = await db.get_user(user_id)
        if not u:
            await _edit_prompt_error(
                context, "_sub_prompt_id", "_sub_prompt_chat",
                "❌ Usuário não encontrado.\n\n"
                "Ele precisa iniciar o bot primeiro (/start).\n\n"
                "Envie outro ID:",
                ForceReply(selective=True),
            )
            return

        state["user_id"] = user_id
        state["tg_name"] = u.get("first_name") or "—"
        state["step"] = "nome"

        await _edit_prompt_error(
            context, "_sub_prompt_id", "_sub_prompt_chat",
            f"✅ Usuário encontrado!\n"
            f"👤 <b>{state['tg_name']}</b> — <code>{user_id}</code>\n\n"
            "Passo <b>2/3</b> — Apelido\n\n"
            "Envie um <b>apelido</b> pro sub-admin (ex: <code>João</code>):",
            ForceReply(selective=True),
        )
        return

    # ─── PASSO 2: nome
    if step == "nome":
        if len(texto) < 2 or len(texto) > 30:
            await _edit_prompt_error(
                context, "_sub_prompt_id", "_sub_prompt_chat",
                "❌ Apelido deve ter entre 2 e 30 caracteres.\n\nTente novamente:",
                ForceReply(selective=True),
            )
            return

        state["nome"] = texto
        state["step"] = "expira"

        await _edit_prompt_error(
            context, "_sub_prompt_id", "_sub_prompt_chat",
            f"📅 <b>Passo 3/3</b> — Expiração\n\n"
            f"Quanto tempo o sub-admin ficará ativo?\n\n"
            f"Envie o número de <b>dias</b> (ex: <code>30</code>)\n"
            f"ou <code>0</code> para <b>permanente</b>:",
            ForceReply(selective=True),
        )
        return

    # ─── PASSO 3: expiração
    if step == "expira":
        if texto == "0":
            expires_days = None
        else:
            try:
                expires_days = int(texto)
                if expires_days <= 0 or expires_days > 3650:
                    raise ValueError
            except ValueError:
                await _edit_prompt_error(
                    context, "_sub_prompt_id", "_sub_prompt_chat",
                    "❌ Valor inválido.\n\n"
                    "Envie um número de 1 a 3650, ou <code>0</code> para permanente:",
                    ForceReply(selective=True),
                )
                return

        user_id = state["user_id"]
        nome = state["nome"]

        await db.admin_sub_add_full(
            user_id=user_id,
            nome=nome,
            permissoes="all",
            expires_days=expires_days,
            created_by=update.effective_user.id,
        )

        context.user_data.pop("sub_wizard", None)
        await _delete_prompt(context, "_sub_prompt_id", "_sub_prompt_chat")

        await db.log_admin_action(
            update.effective_user.id, "subadmin_add", str(user_id),
            f"nome={nome} expires={expires_days}",
        )

        # Notifica o sub
        try:
            exp_txt = "permanente" if expires_days is None else f"por {expires_days} dias"
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 <b>Você virou Sub-Admin!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🏷️ Apelido: <b>{nome}</b>\n"
                    f"⏰ Duração: <b>{exp_txt}</b>\n"
                    "🔓 Permissões: <b>TODAS</b>\n\n"
                    "Use <code>/admin</code> para abrir o painel."
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        exp_txt_2 = "Permanente" if expires_days is None else f"{expires_days} dias"

        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"✅ <b>Sub-admin adicionado!</b>\n\n"
                    f"👤 Nome: <b>{nome}</b>\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"⏰ Expira: <b>{exp_txt_2}</b>\n"
                    f"🔓 Permissões: <b>TODAS</b>"
                ),
                reply_markup=menus.admin_sub_v2_perms_kb(user_id, "all"),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# PERMISSÕES
# ═══════════════════════════════════════════════
async def admin_sub_v2_perm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    perms = sub.get("permissoes", "")

    texto = (
        f"🔓 <b>Permissões de {sub.get('nome')}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<code>{perms or '(nenhuma)'}</code>\n\n"
        "Toque para adicionar/remover permissão:"
    )

    await _edit_or_send(query, texto, menus.admin_sub_v2_perms_kb(user_id, perms))


async def admin_sub_v2_tog_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        _, _, user_id_s, area = query.data.split(":")
        user_id = int(user_id_s)
    except (ValueError, IndexError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    perms = sub.get("permissoes", "") or ""
    expires_original = sub.get("expires_at")

    # Toggle
    if perms == "all":
        todas = list(PERMS_LABEL.keys())
        if area in todas:
            todas.remove(area)
        perms = ",".join(todas)
    else:
        atual = [p.strip() for p in perms.split(",") if p.strip()]
        if area in atual:
            atual.remove(area)
        else:
            atual.append(area)
        perms = ",".join(atual) if atual else ""

    # Calcula dias restantes pra preservar expiração
    expires_days = None
    if expires_original:
        try:
            exp_dt = datetime.strptime(str(expires_original)[:19], "%Y-%m-%d %H:%M:%S")
            restantes = (exp_dt - datetime.now()).days
            expires_days = max(restantes, 1)
        except Exception:
            expires_days = None

    await db.admin_sub_add_full(
        user_id=user_id,
        nome=sub.get("nome") or "",
        permissoes=perms,
        expires_days=expires_days,
        created_by=update.effective_user.id,
    )

    await db.sub_log_action(
        update.effective_user.id, "perms_change", str(user_id), perms,
    )

    # Re-renderiza
    query.data = f"admin:sub2_perm:{user_id}"
    await admin_sub_v2_perm_cb(update, context)


async def admin_sub_v2_all_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    # Preserva expiração
    expires_days = None
    if sub.get("expires_at"):
        try:
            exp_dt = datetime.strptime(str(sub["expires_at"])[:19], "%Y-%m-%d %H:%M:%S")
            restantes = (exp_dt - datetime.now()).days
            expires_days = max(restantes, 1)
        except Exception:
            expires_days = None

    await db.admin_sub_add_full(
        user_id, sub.get("nome") or "", "all", expires_days, update.effective_user.id,
    )
    await db.sub_log_action(update.effective_user.id, "perms_all", str(user_id))

    await query.answer("✅ Todas as permissões dadas!", show_alert=True)
    query.data = f"admin:sub2_perm:{user_id}"
    await admin_sub_v2_perm_cb(update, context)


async def admin_sub_v2_none_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    expires_days = None
    if sub.get("expires_at"):
        try:
            exp_dt = datetime.strptime(str(sub["expires_at"])[:19], "%Y-%m-%d %H:%M:%S")
            restantes = (exp_dt - datetime.now()).days
            expires_days = max(restantes, 1)
        except Exception:
            expires_days = None

    await db.admin_sub_add_full(
        user_id, sub.get("nome") or "", "", expires_days, update.effective_user.id,
    )
    await db.sub_log_action(update.effective_user.id, "perms_none", str(user_id))

    await query.answer("❌ Permissões removidas!", show_alert=True)
    query.data = f"admin:sub2_perm:{user_id}"
    await admin_sub_v2_perm_cb(update, context)


# ═══════════════════════════════════════════════
# EXPIRAÇÃO
# ═══════════════════════════════════════════════
async def admin_sub_v2_exp_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    exp = sub.get("expires_at")
    exp_line = "♾️ Permanente"
    if exp:
        try:
            exp_dt = datetime.strptime(str(exp)[:19], "%Y-%m-%d %H:%M:%S")
            exp_line = exp_dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            exp_line = str(exp)

    texto = (
        f"📅 <b>Expiração de {sub.get('nome')}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Atual: <b>{exp_line}</b>\n\n"
        "Escolha a nova duração:"
    )

    await _edit_or_send(query, texto, menus.admin_sub_v2_exp_kb(user_id))


async def admin_sub_v2_exp_set_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        _, _, user_id_s, dur = query.data.split(":")
        user_id = int(user_id_s)
    except (ValueError, IndexError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    if dur == "perm":
        await db.admin_sub_set_expira(user_id, None)
        txt = "Permanente"
    else:
        dias = int(dur)
        await db.admin_sub_set_expira(user_id, dias)
        txt = f"{dias} dias"

    await db.sub_log_action(update.effective_user.id, "exp_change", str(user_id), txt)

    await query.answer(f"✅ Expiração: {txt}", show_alert=True)
    query.data = f"admin:sub2:{user_id}"
    await admin_sub_v2_view_cb(update, context)


async def admin_sub_v2_perm_forever_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_sub_set_expira(user_id, None)
    await db.sub_log_action(update.effective_user.id, "exp_forever", str(user_id))

    await query.answer("♾️ Agora é permanente!", show_alert=True)
    query.data = f"admin:sub2:{user_id}"
    await admin_sub_v2_view_cb(update, context)


# ═══════════════════════════════════════════════
# HISTÓRICO
# ═══════════════════════════════════════════════
async def admin_sub_v2_hist_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    logs = await db.sub_list_logs(user_id, limit=20)
    por_acao = await db.sub_stats_por_acao(user_id)

    if not logs:
        texto = (
            f"📜 <b>Histórico de {sub.get('nome')}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>Nenhuma ação registrada.</i>"
        )
    else:
        linhas = [f"📜 <b>Histórico de {sub.get('nome')}</b>\n"
                  "━━━━━━━━━━━━━━━━━━━━━━━\n"]

        if por_acao:
            linhas.append("📊 <b>Top ações:</b>")
            for p in por_acao[:5]:
                linhas.append(f"├ <b>{p['action']}</b> — {p['total']}x")
            linhas.append("")

        linhas.append("📋 <b>Últimas 20 ações:</b>\n")
        for l in logs[:20]:
            data = str(l.get("created_at") or "")[:16]
            target = l.get("target") or "—"
            details = (l.get("details") or "")[:40]
            linhas.append(
                f"🕐 <code>{data}</code>\n"
                f"├ ⚡ <b>{l['action']}</b>\n"
                f"├ 🎯 <code>{target}</code>\n"
                f"└ 📝 {details}\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data=f"admin:sub2:{user_id}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_sub_v2_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    logs = await db.sub_list_logs(None, limit=30)

    if not logs:
        texto = (
            "📋 <b>Logs Globais dos Subs</b>\n\n"
            "<i>Nenhuma ação registrada ainda.</i>"
        )
    else:
        linhas = ["📋 <b>Últimas 30 ações dos subs</b>\n"
                  "━━━━━━━━━━━━━━━━━━━━━━━\n"]
        for l in logs:
            data = str(l.get("created_at") or "")[:16]
            admin_id = l["admin_id"]
            target = l.get("target") or "—"
            details = (l.get("details") or "")[:40]
            linhas.append(
                f"🕐 <code>{data}</code> · 👤 <code>{admin_id}</code>\n"
                f"├ ⚡ {l['action']}\n"
                f"├ 🎯 <code>{target}</code>\n"
                f"└ 📝 {details}\n"
            )
        texto = "\n".join(linhas)

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("⬅️ Voltar", callback_data="admin:subadmins")],
    ])
    await _edit_or_send(query, texto, kb)


# ═══════════════════════════════════════════════
# REMOVER
# ═══════════════════════════════════════════════
async def admin_sub_v2_del_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    sub = await db.admin_sub_get_full(user_id)
    if not sub:
        return

    u = await db.get_user(user_id)
    nome_tg = (u or {}).get("first_name") or "—"

    texto = (
        "🗑️ <b>Remover Sub-Admin?</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Nome: <b>{sub.get('nome')}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📛 Telegram: <b>{nome_tg}</b>\n\n"
        "⚠️ O sub-admin perderá acesso ao painel imediatamente."
    )

    kb = menus.InlineKeyboardMarkup([
        [menus.InlineKeyboardButton("🗑️ Sim, remover", callback_data=f"admin:sub2_del_yes:{user_id}")],
        [menus.InlineKeyboardButton("❌ Cancelar", callback_data=f"admin:sub2:{user_id}")],
    ])
    await _edit_or_send(query, texto, kb)


async def admin_sub_v2_del_yes_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_master(update.effective_user.id):
        return

    try:
        user_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    await db.admin_sub_remove_full(user_id)

    await db.log_admin_action(
        update.effective_user.id, "subadmin_remove", str(user_id),
    )

    # Notifica
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⚠️ <b>Você foi removido do cargo de Sub-Admin</b>\n\n"
                "Você não tem mais acesso ao painel administrativo."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await _edit_or_send(
        query,
        "🗑️ <b>Sub-admin removido.</b>",
        menus.admin_back_kb(),
    )
