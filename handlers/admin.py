import logging
import asyncio
from telegram import Update, ForceReply, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import db
from keyboards import menus
from texts import cache

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _edit_or_send(query, text: str, kb=None):
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)
    except Exception:
        await query.message.reply_text(text, reply_markup=kb, parse_mode=ParseMode.HTML)


def _dashboard_text(stats: dict) -> str:
    manut = "🔴 Em manutenção" if stats["manutencao"] else "🟢 Online"
    return (
        "🛠️ <b>PAINEL ADMINISTRADOR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"⚙️ <b>Status do Bot:</b> {manut}\n\n"

        "📊 <b>Visão Geral:</b>\n"
        f"├ 👥 Usuários: <b>{stats['total_users']}</b>\n"
        f"├ 🚫 Banidos: <b>{stats['total_banned']}</b>\n"
        f"├ 📦 Produtos ativos: <b>{stats['total_produtos']}</b>\n"
        f"└ 🛒 Carrinhos abandonados: <b>{stats['carrinhos_abandonados']}</b>\n\n"

        "💰 <b>Movimentação Financeira:</b>\n"
        f"├ Saldo em circulação: <b>R$ {stats['saldo_circulacao']:.2f}</b>\n"
        f"├ Receita total: <b>R$ {stats['receita_total']:.2f}</b>\n"
        f"├ Receita hoje: <b>R$ {stats['receita_hoje']:.2f}</b>\n"
        f"├ Receita 7 dias: <b>R$ {stats['receita_semana']:.2f}</b>\n"
        f"└ Receita do mês: <b>R$ {stats['receita_mes']:.2f}</b>\n\n"

        "🛒 <b>Vendas:</b>\n"
        f"├ Total de pedidos: <b>{stats['total_vendas']}</b>\n"
        f"└ Vendas hoje: <b>{stats['vendas_hoje']}</b>"
    )


# ═══════════════════════════════════════════════
# /admin — ABRIR PAINEL
# ═══════════════════════════════════════════════
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return

    try:
        stats = await db.admin_stats()
        await update.message.reply_text(
            _dashboard_text(stats),
            reply_markup=menus.admin_dashboard_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro abrindo painel: %s", e)
        await update.message.reply_text(f"❌ Erro ao abrir painel: {e}")


async def admin_home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Volta ao dashboard."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        stats = await db.admin_stats()
        await _edit_or_send(query, _dashboard_text(stats), menus.admin_dashboard_kb())
    except Exception as e:
        logger.exception("Erro no dashboard: %s", e)


# ═══════════════════════════════════════════════
# USUÁRIOS
# ═══════════════════════════════════════════════
async def admin_users_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        users = await db.list_users(limit=10)
        total = await db.count_users()

        texto = (
            "👥 <b>Usuários Cadastrados</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Total: <b>{total}</b>\n"
            f"📋 Mostrando: <b>{len(users)}</b> mais recentes\n\n"
            "👉 Toque em um usuário para ver detalhes:"
        )
        await _edit_or_send(query, texto, menus.admin_users_kb(users))
    except Exception as e:
        logger.exception("Erro listando usuários: %s", e)


async def admin_user_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede o termo de busca."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["admin_await_search"] = True

    # 1) Edita a mensagem atual
    try:
        await query.edit_message_text(
            "🔍 <b>Buscar Usuário</b>\n\n"
            "Use o campo abaixo para enviar o <b>ID</b>, <b>nome</b> ou <b>@username</b>:",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    # 2) Envia mensagem com ForceReply (mais confiável que no edit)
    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 <b>Digite aqui:</b>",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro enviando ForceReply de busca: %s", e)


async def admin_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("admin_await_search"):
        return
    if not is_admin(update.effective_user.id):
        return

    term = (update.message.text or "").strip()
    context.user_data.pop("admin_await_search", None)

    if not term:
        await update.message.reply_text("❌ Termo vazio. Tente novamente.")
        return

    try:
        usuarios = await db.search_users(term)
    except Exception as e:
        logger.exception("Erro na busca: %s", e)
        await update.message.reply_text(f"❌ Erro na busca: {e}")
        return

    if not usuarios:
        await update.message.reply_text(
            f"❌ Nenhum usuário encontrado com <code>{term}</code>.",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
        return

    texto = (
        "🔍 <b>Resultado da Busca</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Termo: <code>{term}</code>\n"
        f"📋 Encontrados: <b>{len(usuarios)}</b>"
    )
    await update.message.reply_text(
        texto,
        reply_markup=menus.admin_users_kb(usuarios),
        parse_mode=ParseMode.HTML,
    )


async def admin_user_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    try:
        u = await db.get_user(target_id)
        if not u:
            await _edit_or_send(query, "❌ Usuário não encontrado.", menus.admin_back_kb())
            return

        stats = await db.user_stats(target_id)
        banned = bool(u.get("banned"))
        ban_icon = "🚫 Banido" if banned else "✅ Ativo"

        texto = (
            "👤 <b>Detalhes do Usuário</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: <code>{u['user_id']}</code>\n"
            f"📛 Nome: <b>{u.get('first_name') or '—'}</b>\n"
            f"🔗 Username: @{u.get('username') or '—'}\n"
            f"📊 Status: {ban_icon}\n\n"

            "💰 <b>Saldos:</b>\n"
            f"├ Bot: <b>R$ {float(u.get('balance') or 0):.2f}</b>\n"
            f"└ Loja Web: <b>R$ {float(u.get('balance_web') or 0):.2f}</b>\n\n"

            f"📱 WhatsApp: <code>{u.get('whatsapp') or '—'}</code>\n\n"

            "📈 <b>Movimentações:</b>\n"
            f"├ 🛒 Compras: <b>{stats['compras']}</b>\n"
            f"├ 💰 Gasto: <b>R$ {stats['gasto']:.2f}</b>\n"
            f"├ 💠 PIX Inseridos: <b>R$ {stats['pix_inseridos']:.2f}</b>\n"
            f"└ 🎁 Gifts: <b>R$ {stats['gifts_valor']:.2f}</b>"
        )

        await _edit_or_send(query, texto, menus.admin_user_kb(target_id, banned))
    except Exception as e:
        logger.exception("Erro mostrando usuário: %s", e)


# ─── Adicionar / Remover saldo
async def admin_add_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    context.user_data["admin_balance"] = {"target": target_id, "tipo": "add"}

    try:
        await query.edit_message_text(
            "➕ <b>Adicionar Saldo</b>\n\n"
            f"👤 Usuário: <code>{target_id}</code>\n\n"
            "Envie o valor no campo abaixo (ex: <code>10.50</code>):",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 <b>Digite o valor:</b>",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_rem_balance_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
    except (IndexError, ValueError):
        return

    context.user_data["admin_balance"] = {"target": target_id, "tipo": "rem"}

    try:
        await query.edit_message_text(
            "➖ <b>Remover Saldo</b>\n\n"
            f"👤 Usuário: <code>{target_id}</code>\n\n"
            "Envie o valor no campo abaixo (ex: <code>10.50</code>):",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 <b>Digite o valor:</b>",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def admin_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = context.user_data.get("admin_balance")
    if not info:
        return
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip().replace(",", ".")

    try:
        valor = float(text)
        if valor <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Envie um número positivo.")
        return

    target = info["target"]
    tipo = info["tipo"]
    context.user_data.pop("admin_balance", None)

    try:
        u = await db.get_user(target)
        if not u:
            await update.message.reply_text("❌ Usuário não encontrado.")
            return

        delta = valor if tipo == "add" else -valor
        await db.update_balance(target, delta)

        u2 = await db.get_user(target)
        await db.log_admin_action(
            update.effective_user.id,
            f"{'add' if tipo == 'add' else 'rem'}_balance",
            str(target),
            f"R$ {valor:.2f}",
        )

        acao = "adicionado" if tipo == "add" else "removido"
        emoji = "➕" if tipo == "add" else "➖"

        await update.message.reply_text(
            f"✅ <b>Saldo {acao}!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Usuário: <code>{target}</code>\n"
            f"{emoji} Valor: <b>R$ {valor:.2f}</b>\n"
            f"💰 Saldo atual: <b>R$ {float(u2['balance']):.2f}</b>",
            reply_markup=menus.admin_back_kb(),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("Erro add/rem balance: %s", e)
        await update.message.reply_text(f"❌ Erro: {e}")


# ─── Banir / Desbanir
async def admin_ban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
        await db.ban_user(target_id)
        await db.log_admin_action(update.effective_user.id, "ban", str(target_id))
    except Exception as e:
        logger.exception("Erro banindo: %s", e)

    await admin_user_cb(update, context)


async def admin_unban_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        target_id = int(query.data.split(":")[2])
        await db.unban_user(target_id)
        await db.log_admin_action(update.effective_user.id, "unban", str(target_id))
    except Exception as e:
        logger.exception("Erro desbanindo: %s", e)

    await admin_user_cb(update, context)


# ═══════════════════════════════════════════════
# TRANSMISSÃO (BROADCAST)
# ═══════════════════════════════════════════════
async def admin_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    texto = (
        "📢 <b>Transmissão em Massa</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Escolha para qual <b>público</b> você quer enviar a mensagem:\n\n"
        "📢 <b>Todos os usuários</b> — envia pra todos\n"
        "🛒 <b>Apenas compradores</b> — quem já comprou\n"
        "💤 <b>Inativos (7d+)</b> — quem não usa há 7 dias"
    )
    await _edit_or_send(query, texto, menus.admin_broadcast_kb())


async def admin_bc_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    tipo = query.data.split(":")[1]  # bc_all / bc_buyers / bc_inactive
    context.user_data["admin_bc"] = tipo

    labels = {
        "bc_all": "📢 Todos os usuários",
        "bc_buyers": "🛒 Apenas compradores",
        "bc_inactive": "💤 Inativos (7d+)",
    }

    try:
        await query.edit_message_text(
            f"📢 <b>Transmissão: {labels.get(tipo, tipo)}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envie a mensagem que será enviada.\n\n"
            "💡 Você pode usar <b>HTML</b>: <code>&lt;b&gt;negrito&lt;/b&gt;</code>, "
            "<code>&lt;i&gt;itálico&lt;/i&gt;</code>.\n"
            "🖼️ Também aceita <b>foto</b> ou <b>vídeo</b> com legenda.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 <b>Digite a mensagem:</b>",
            reply_markup=ForceReply(selective=True),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# MANUTENÇÃO
# ═══════════════════════════════════════════════
async def admin_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        ativo = await db.get_maintenance()
        status = "🔴 LIGADO (bloqueando usuários)" if ativo else "🟢 DESLIGADO"

        texto = (
            "🚧 <b>Modo Manutenção</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Status atual: <b>{status}</b>\n\n"
            "Quando <b>LIGADO</b>:\n"
            "• Todos os usuários veem mensagem de manutenção\n"
            "• Admins e sub-admins continuam com acesso total\n"
            "• Bot continua recebendo pagamentos normalmente"
        )
        await _edit_or_send(query, texto, menus.admin_maintenance_kb(ativo))
    except Exception as e:
        logger.exception("Erro manutenção: %s", e)


async def admin_toggle_maintenance_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        ativo = await db.get_maintenance()
        novo = not ativo
        await db.set_maintenance(novo)
        await db.log_admin_action(
            update.effective_user.id, "toggle_maintenance", "global", f"novo={novo}",
        )
    except Exception as e:
        logger.exception("Erro toggling manutenção: %s", e)

    await admin_maintenance_cb(update, context)


# ═══════════════════════════════════════════════
# LOGS
# ═══════════════════════════════════════════════
async def admin_logs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        logs = await db.list_admin_logs(20)

        if not logs:
            texto = (
                "📋 <b>Logs de Administração</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "<i>Nenhuma ação registrada ainda.</i>"
            )
        else:
            linhas = [
                "📋 <b>Últimas 20 Ações</b>",
                "━━━━━━━━━━━━━━━━━━━━━━━\n",
            ]
            for l in logs:
                data = str(l.get("created_at") or "")[:16]
                target = l.get("target") or "—"
                details = l.get("details") or ""
                linhas.append(
                    f"🕐 <code>{data}</code>\n"
                    f"├ 👤 Admin: <code>{l['admin_id']}</code>\n"
                    f"├ ⚡ Ação: <b>{l['action']}</b>\n"
                    f"├ 🎯 Alvo: <code>{target}</code>\n"
                    f"└ 📝 {details}\n"
                )
            texto = "\n".join(linhas)

        await _edit_or_send(query, texto, menus.admin_back_kb())
    except Exception as e:
        logger.exception("Erro logs: %s", e)


# ═══════════════════════════════════════════════
# REINICIAR BOT
# ═══════════════════════════════════════════════
async def admin_restart_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        await query.edit_message_text(
            "🔁 <b>Reiniciando o Bot...</b>\n\n"
            "Aguarde alguns segundos.\n"
            "O bot vai recarregar dados e voltar ao ar automaticamente.",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass

    await db.log_admin_action(update.effective_user.id, "restart")

    logger.info("🔁 Reinício solicitado pelo admin %s", update.effective_user.id)

    # ─── Recarrega o cache (recarrega textos/botões do banco)
    try:
        await asyncio.sleep(1)
        await cache.load_all()
        await asyncio.sleep(1)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ <b>Bot reiniciado com sucesso!</b>\n\n"
                 "• Cache recarregado\n"
                 "• Textos e botões atualizados\n"
                 "• Sistema online",
            parse_mode=ParseMode.HTML,
            reply_markup=menus.admin_back_kb(),
        )
    except Exception as e:
        logger.exception("Erro recarregando cache: %s", e)
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"⚠️ Cache recarregado com avisos: {e}",
                reply_markup=menus.admin_back_kb(),
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════
# PRODUTOS (lista básica)
# ═══════════════════════════════════════════════
async def admin_products_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista produtos. Delegação pra admin4 se existir."""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        # Se admin4 existir e tiver products_v2, delega
        try:
            from handlers import admin4
            if hasattr(admin4, "admin_products_v2_cb"):
                await admin4.admin_products_v2_cb(update, context)
                return
        except Exception:
            pass

        produtos = await db.get_products()
        texto = (
            "📦 <b>Produtos</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Total ativos: <b>{len(produtos)}</b>\n\n"
            "👉 Toque em um produto para gerenciar:"
        )
        await _edit_or_send(query, texto, menus.admin_products_kb_v2(produtos))
    except Exception as e:
        logger.exception("Erro listando produtos: %s", e)


# ═══════════════════════════════════════════════
# TOGGLE PRODUTO (ativar/desativar)
# ═══════════════════════════════════════════════
async def admin_toggle_product_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    try:
        pid = int(query.data.split(":")[2])
        p = await db.get_product(pid)
        if not p:
            return

        novo_status = 0 if p.get("active") else 1
        await db._db.execute("UPDATE products SET active = ? WHERE id = ?", (novo_status, pid))
        await db._db.commit()
        await db.log_admin_action(
            update.effective_user.id, "toggle_product", str(pid), f"active={novo_status}",
        )
    except Exception as e:
        logger.exception("Erro toggle produto: %s", e)

    # Re-renderiza via admin4 se possível
    try:
        from handlers import admin4
        if hasattr(admin4, "admin_product_v2_cb"):
            await admin4.admin_product_v2_cb(update, context)
            return
    except Exception:
        pass

    await admin_products_cb(update, context)
