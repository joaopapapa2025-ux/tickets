import base64
import html
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo
from urllib.parse import quote
from streamlit_autorefresh import st_autorefresh

from pandas.tseries.holiday import AbstractHolidayCalendar, Holiday

import pandas as pd
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account


st.set_page_config(page_title="Papapa Tickets", layout="wide")


USUARIOS = {
    "comercial1@papapa.com.br": {"senha": "miojo123", "usuario": "joao.tadra", "nome": "João Tadra", "setor": "Comercial", "email": "comercial1@papapa.com.br", "telefone": "5541984959492"},
    "comercial3@papapa.com.br": {"senha": "miojo123", "usuario": "ana.christina", "nome": "Ana Christina", "setor": "Comercial", "email": "comercial3@papapa.com.br", "telefone": "554137976554"},
    "comercial5@papapa.com.br": {"senha": "miojo123", "usuario": "pedro.born", "nome": "Pedro Born", "setor": "Comercial", "email": "comercial5@papapa.com.br", "telefone": "554137976885"},
    "comercial2@papapa.com.br": {"senha": "miojo123", "usuario": "joao.paulo", "nome": "João Paulo", "setor": "Comercial", "email": "comercial2@papapa.com.br", "telefone": "5541992474213"},
    "comercial4@papapa.com.br": {"senha": "miojo123", "usuario": "rodrigo.sarlo", "nome": "Rodrigo Sarlo", "setor": "Comercial", "email": "comercial4@papapa.com.br", "telefone": "5541985027025"},
    "posvendas1@papapa.com.br": {"senha": "miojo123", "usuario": "thiago.cabral", "nome": "Thiago Cabral", "setor": "Pós-vendas", "email": "posvendas1@papapa.com.br", "telefone": "5541984703249"},
    "posvendas2@papapa.com.br": {"senha": "miojo123", "usuario": "bernardo.dallegrave", "nome": "Bernardo Dallegrave", "setor": "Pós-vendas", "email": "posvendas2@papapa.com.br", "telefone": "5541984703249"},
    "logistica4@papapa.com.br": {"senha": "miojo123", "usuario": "ronaldo.leidens", "nome": "Ronaldo Leidens", "setor": "Logística", "email": "logistica4@papapa.com.br", "telefone": "5541991917922"},
    "contasareceber@papapa.com.br": {"senha": "miojo123", "usuario": "luan.dornelis", "nome": "Luan Dornelis", "setor": "Financeiro", "email": "contasareceber@papapa.com.br", "telefone": "5541991361619"},
    "rh@papapa.com.br": {"senha": "miojo123", "usuario": "maria.julia", "nome": "Maria Julia", "setor": "RH", "email": "rh@papapa.com.br", "telefone": "5541984402434"},
    "crm@papapa.com.br": {"senha": "miojo123", "usuario": "victoria.gobbo", "nome": "Victoria Gobbo", "setor": "Marketing", "email": "crm@papapa.com.br", "telefone": "5541992761230"},
    "operacoes@papapa.com.br": {"senha": "miojo123", "usuario": "tatiane.vieira", "nome": "Tatiane Vieira", "setor": "Logística", "email": "operacoes@papapa.com.br", "telefone": "5541000000000"},
    "financeiro@papapa.com.br": {"senha": "miojo123", "usuario": "janaina.eller", "nome": "Janaina Eller", "setor": "Financeiro", "email": "financeiro@papapa.com.br", "telefone": "5541000000000"},
    "mariano@papapa.com.br": {"senha": "miojo123", "usuario": "mariano.mendez", "nome": "Mariano Mendez", "setor": "Comercial", "email": "mariano@papapa.com.br", "telefone": "5511994085130"},
}

STATUS = ["Aberto", "Em análise", "Aguardando retorno", "Em execução", "Resolvido"]
SETORES = ["Comercial", "Pós-vendas", "Logística", "Financeiro"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Urgente"]

ADMIN_DELETE_EMAILS = ["comercial1@papapa.com.br"]
ADMIN_VIEW_ALL_EMAILS = ["comercial1@papapa.com.br", "operacoes@papapa.com.br"]
ADMIN_COMMENT_EMAILS = ["comercial1@papapa.com.br", "operacoes@papapa.com.br"]
COLLECTION_TICKETS = "tickets_internos"
COLLECTION_SESSIONS = "tickets_sessoes"
COLLECTION_ATTACHMENTS = "tickets_anexos_chunks"

TIPOS_ANEXOS = ["png", "jpg", "jpeg", "mp4", "mov", "avi", "pdf", "xlsx", "xls", "docx", "txt"]
MAX_ATTACHMENT_MB = 20
CHUNK_SIZE = 650_000


st.markdown(
    """
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 100%;
}

[data-testid="stSidebar"] {
    background-color: #082b57;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: #ffffff !important;
}

[data-testid="stSidebar"] a {
    color: #9cc8ff !important;
}

[data-testid="stSidebar"] button {
    background-color: #ffffff !important;
    color: #082b57 !important;
    border: 1px solid #ffffff !important;
    font-weight: 800 !important;
}

[data-testid="stSidebar"] button p {
    color: #082b57 !important;
}

[data-testid="stSidebarCollapseButton"] {
    background-color: #ffffff !important;
    color: #082b57 !important;
    border: 1px solid #ffffff !important;
    border-radius: 8px !important;
    width: 36px !important;
    height: 36px !important;
    margin-left: 8px !important;
    margin-top: 8px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12) !important;
    position: relative !important;
}

[data-testid="stSidebarCollapseButton"] svg {
    display: none !important;
}

[data-testid="stSidebarCollapseButton"]::after {
    content: "←" !important;
    color: #082b57 !important;
    font-size: 22px !important;
    font-weight: 900 !important;
    line-height: 1 !important;
    position: absolute !important;
    top: 5px !important;
    left: 10px !important;
}

.ticket-card {
    background: #ffffff;
    border: 1px solid #e4e8f0;
    border-left: 5px solid #1f6feb;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    min-height: 150px;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.07);
}

.ticket-title {
    font-weight: 850;
    color: #102a43;
    margin-bottom: 8px;
    line-height: 1.25;
}

.ticket-meta {
    font-size: 12px;
    color: #56657a;
    margin-bottom: 2px;
}

.ticket-pill {
    display: inline-block;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 999px;
    margin-right: 4px;
    margin-bottom: 8px;
    color: white;
}

.priority-urgente { border-left-color: #dc2626; }
.priority-alta { border-left-color: #f97316; }
.priority-media { border-left-color: #2563eb; }
.priority-baixa { border-left-color: #16a34a; }

.pill-urgente { background: #dc2626; }
.pill-alta { background: #f97316; }
.pill-media { background: #2563eb; }
.pill-baixa { background: #16a34a; }

.age-green { background: #16a34a; }
.age-yellow { background: #eab308; color: #111827; }
.age-red { background: #dc2626; }

.kanban-empty {
    border: 1px dashed #d7dde8;
    background: #f8fafc;
    color: #8492a6;
    border-radius: 8px;
    padding: 18px 10px;
    text-align: center;
    font-size: 12px;
}

.comment-box {
    background: #eef5ff;
    border: 1px solid #dbeafe;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
}

.comment-author {
    font-weight: 850;
    color: #0f3a73;
    margin-bottom: 3px;
}

.comment-text {
    color: #1f2937;
    font-size: 14px;
}

.history-box {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 9px 11px;
    margin-bottom: 7px;
    font-size: 13px;
}

.attach-box {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 6px;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def conectar_firestore():
    try:
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        return firestore.Client(credentials=creds)
    except Exception as erro:
        st.error("Não consegui conectar ao Firestore. Confira os secrets do Streamlit Cloud.")
        st.exception(erro)
        st.stop()


db = conectar_firestore()


def agora():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)


def agora_formatado():
    return agora().strftime("%d/%m/%Y %H:%M")


def token_diario():
    return f"access_{agora().strftime('%Y%m%d')}"


def formatar_numero_ticket(ticket_id):
    return f"#{int(ticket_id):05d}"

def limpar_id_origem(valor):
    if not valor:
        return None

    texto = str(valor)

    if "#" in texto:
        texto = texto.split("#", 1)[1]

    digitos = "".join(ch for ch in texto if ch.isdigit())

    if not digitos:
        return None

    return int(digitos)


def parse_data(valor):
    if not valor:
        return None

    for formato in ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(str(valor), formato)
        except ValueError:
            pass

    return None


def prioridade_classe(prioridade):
    return {"Baixa": "baixa", "Média": "media", "Alta": "alta", "Urgente": "urgente"}.get(prioridade, "media")


def idade_ticket(ticket):
    criado = parse_data(ticket.get("criado_em", ""))

    if not criado:
        return 0

    return max((agora().date() - criado.date()).days, 0)


def classe_idade_ticket(dias):
    if dias == 0:
        return "age-green"

    if dias <= 2:
        return "age-yellow"

    return "age-red"


def texto_idade_ticket(dias):
    if dias == 0:
        return "Aberto hoje"

    if dias == 1:
        return "Aberto há 1 dia"

    return f"Aberto há {dias} dias"

class FeriadosBrasil(AbstractHolidayCalendar):
    rules = [
        Holiday("Confraternização Universal", month=1, day=1),
        Holiday("Tiradentes", month=4, day=21),
        Holiday("Dia do Trabalho", month=5, day=1),
        Holiday("Corpus Christi", month=6, day=4),
        Holiday("Independência", month=9, day=7),
        Holiday("Nossa Sra Aparecida", month=10, day=12),
        Holiday("Finados", month=11, day=2),
        Holiday("Proclamação da República", month=11, day=15),
        Holiday("Natal", month=12, day=25),
    ]


def feriados_brasil(inicio, fim):
    if not inicio or not fim:
        return set()

    calendario = FeriadosBrasil()
    feriados = calendario.holidays(
        start=inicio.date() - timedelta(days=1),
        end=fim.date() + timedelta(days=1),
    )

    return {data.date() for data in feriados}


def eh_dia_util(data, feriados):
    return data.weekday() < 5 and data.date() not in feriados


def horas_uteis_entre(inicio, fim):
    if not inicio or not fim or fim <= inicio:
        return None

    feriados = feriados_brasil(inicio, fim)
    total_horas = 0.0
    cursor = inicio

    while cursor < fim:
        proximo_dia = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
        limite = min(proximo_dia, fim)

        if eh_dia_util(cursor, feriados):
            total_horas += (limite - cursor).total_seconds() / 3600

        cursor = limite

    return max(total_horas, 0)


def horas_corridas_entre(inicio, fim):
    if not inicio or not fim or fim <= inicio:
        return None

    return max((fim - inicio).total_seconds() / 3600, 0)


def formatar_tempo_duplo(horas_corridas, horas_uteis):
    def _fmt(valor):
        if valor is None or pd.isna(valor):
            return "Sem dado"
        if valor < 1:
            return f"{valor * 60:.0f} min"
        if valor < 24:
            return f"{valor:.1f} h"
        return f"{valor / 24:.1f} dias"

    return f"{_fmt(horas_corridas)} corridos | {_fmt(horas_uteis)} úteis"


def usuarios_do_setor(setor):
    return [dados["nome"] for dados in USUARIOS.values() if dados["setor"] == setor]


def usuario_por_nome(nome):
    for email, dados in USUARIOS.items():
        if dados["nome"] == nome:
            item = dados.copy()
            item["login"] = email
            return item

    return None

def usuario_por_login(login):
    dados = USUARIOS.get(login)

    if not dados:
        return None

    item = dados.copy()
    item["login"] = login
    return item


def nome_para_notificacao(ticket, responsavel_anterior=None, novo_responsavel=None):
    usuario_atual = st.session_state.usuario
    solicitante_nome = ticket.get("solicitante", "")
    solicitante_login = ticket.get("solicitante_login", "")
    responsavel_nome = ticket.get("responsavel", "")

    if novo_responsavel and novo_responsavel != responsavel_anterior:
        return novo_responsavel

    if usuario_atual["nome"] == solicitante_nome or usuario_atual["login"] == solicitante_login:
        return responsavel_nome

    return solicitante_nome

def lista_responsaveis(setor=None):
    nomes = usuarios_do_setor(setor) if setor else [dados["nome"] for dados in USUARIOS.values()]
    return ["Não atribuído"] + nomes


def telefone_whatsapp_por_nome(nome):
    dados = usuario_por_nome(nome)

    if not dados:
        return ""

    telefone = "".join(ch for ch in dados.get("telefone", "") if ch.isdigit())

    if not telefone:
        return ""

    if not telefone.startswith("55"):
        telefone = f"55{telefone}"

    return telefone


def link_whatsapp(telefone, mensagem):
    if not telefone:
        return ""

    return f"https://web.whatsapp.com/send/?phone={telefone}&text={quote(mensagem)}"


def montar_mensagem(ticket, tipo):
    numero = formatar_numero_ticket(ticket["id"])
    titulo = ticket["titulo"]
    base_url = "https://tickets-papapa.streamlit.app"
    link_ticket = f"{base_url}/?auth={token_diario()}&sid={st.session_state.get('sid', '')}&ticket={ticket['id']}"

    return (
        f"Olá! Houve uma atualização na Central de Tickets Papapa.\n\n"
        f"Tipo: {tipo}\n"
        f"Ticket: {numero} - {titulo}\n"
        f"NF/Pedido: {ticket.get('nf_pedido', '') or 'Não informado'}\n"
        f"CNPJ: {ticket.get('cnpj', '') or 'Não informado'}\n"
        f"Status: {ticket.get('status', '')}\n"
        f"Prioridade: {ticket.get('prioridade', '')}\n"
        f"Solicitante: {ticket.get('solicitante', '')}\n"
        f"Responsável: {ticket.get('responsavel', '')}\n"
        f"Origem: {ticket.get('setor_origem', '')}\n"
        f"Destino: {ticket.get('setor_destino', '')}\n\n"
        f"Acesse o ticket aqui:\n{link_ticket}"
    )

def preparar_notificacao(ticket, tipo, destinatario_nome=None):
    nome = destinatario_nome or nome_para_notificacao(ticket)
    telefone = telefone_whatsapp_por_nome(nome)

    if not telefone:
        return

    st.session_state.notificacao_whatsapp = {
        "label": f"Notificar {nome} no WhatsApp",
        "url": link_whatsapp(telefone, montar_mensagem(ticket, tipo)),
    }

    st.session_state.notificacao_whatsapp = {
        "label": f"Notificar {nome} no WhatsApp",
        "url": link_whatsapp(telefone, montar_mensagem(ticket, tipo)),
    }

def registrar_historico(ticket, acao, detalhe=""):
    historico = ticket.setdefault("historico", [])
    historico.append(
        {
            "autor": st.session_state.usuario["nome"] if st.session_state.get("usuario") else "Sistema",
            "acao": acao,
            "detalhe": detalhe,
            "criado_em": agora_formatado(),
        }
    )

def salvar_arquivo_em_chunks(arquivo):
    conteudo = arquivo.getvalue()
    tamanho_mb = len(conteudo) / (1024 * 1024)

    if tamanho_mb > MAX_ATTACHMENT_MB:
        st.warning(f"{arquivo.name} tem {tamanho_mb:.1f} MB. O limite atual é {MAX_ATTACHMENT_MB} MB.")
        return None

    attachment_id = uuid.uuid4().hex
    encoded = base64.b64encode(conteudo).decode("utf-8")
    chunks = [encoded[i:i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE)]

    batch = db.batch()

    for seq, chunk in enumerate(chunks):
        ref = db.collection(COLLECTION_ATTACHMENTS).document(f"{attachment_id}_{seq:04d}")
        batch.set(
            ref,
            {
                "attachment_id": attachment_id,
                "seq": seq,
                "data": chunk,
                "criado_em": agora_formatado(),
            },
        )

    batch.commit()

    return {
        "id": attachment_id,
        "nome": arquivo.name,
        "tipo": arquivo.type or "application/octet-stream",
        "tamanho": len(conteudo),
        "partes": len(chunks),
        "autor": st.session_state.usuario["nome"],
        "criado_em": agora_formatado(),
    }


def salvar_uploads(arquivos):
    anexos = []

    for arquivo in arquivos or []:
        anexo = salvar_arquivo_em_chunks(arquivo)

        if anexo:
            anexos.append(anexo)

    return anexos


def carregar_bytes_anexo(anexo):
    docs = db.collection(COLLECTION_ATTACHMENTS).where("attachment_id", "==", anexo["id"]).stream()
    partes = sorted([doc.to_dict() for doc in docs], key=lambda item: item.get("seq", 0))
    encoded = "".join(item.get("data", "") for item in partes)

    if not encoded:
        return b""

    return base64.b64decode(encoded)


def render_anexos(anexos, prefixo):
    if not anexos:
        st.caption("Nenhum anexo.")
        return

    for idx, anexo in enumerate(anexos):
        tamanho_mb = anexo.get("tamanho", 0) / (1024 * 1024)
        st.markdown(
            f"""
            <div class="attach-box">
                <b>{html.escape(anexo.get("nome", ""))}</b><br>
                <span class="ticket-meta">{tamanho_mb:.2f} MB | {html.escape(anexo.get("autor", ""))} | {html.escape(anexo.get("criado_em", ""))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        try:
            dados = carregar_bytes_anexo(anexo)
            st.download_button(
                "Baixar arquivo",
                data=dados,
                file_name=anexo.get("nome", "arquivo"),
                mime=anexo.get("tipo", "application/octet-stream"),
                key=f"{prefixo}_download_{anexo.get('id', idx)}",
                use_container_width=True,
            )
        except Exception as erro:
            st.error(f"Não consegui carregar o anexo {anexo.get('nome', '')}.")
            st.caption(str(erro))


def meses_disponiveis(tickets):
    meses = set()

    for ticket in tickets:
        criado = parse_data(ticket.get("criado_em", ""))

        if criado:
            meses.add(criado.strftime("%Y-%m"))

    meses_ordenados = sorted(meses, reverse=True)

    return ["Mês atual"] + [mes for mes in meses_ordenados if mes != agora().strftime("%Y-%m")] + ["Todos"]


def ticket_no_mes(ticket, filtro_mes):
    if ticket.get("status") != "Resolvido":
        return True

    if filtro_mes == "Todos":
        return True

    criado = parse_data(ticket.get("criado_em", ""))

    if not criado:
        return False

    if filtro_mes == "Mês atual":
        return criado.strftime("%Y-%m") == agora().strftime("%Y-%m")

    return criado.strftime("%Y-%m") == filtro_mes


def normalizar_ticket(ticket):
    ticket.setdefault("id", 0)
    ticket.setdefault("titulo", "")
    ticket.setdefault("descricao", "")
    ticket.setdefault("nf_pedido", "")
    ticket.setdefault("cnpj", "")
    ticket.setdefault("anexos", [])
    ticket.setdefault("setor_origem", "")
    ticket.setdefault("setor_destino", "")
    ticket.setdefault("solicitante", "")
    ticket.setdefault("solicitante_login", "")
    ticket.setdefault("responsavel", "Não atribuído")
    ticket.setdefault("prioridade", "Média")
    ticket.setdefault("status", "Aberto")
    ticket.setdefault("comentarios", [])
    ticket.setdefault("historico", [])
    ticket.setdefault("criado_em", "")
    ticket.setdefault("atualizado_em", "")
    ticket.setdefault("ticket_origem_id", None)

    for comentario in ticket["comentarios"]:
        comentario.setdefault("anexos", [])
        comentario.setdefault("excluido", False)
        comentario.setdefault("editado_por", "")
        comentario.setdefault("editado_em", "")
        comentario.setdefault("excluido_por", "")
        comentario.setdefault("excluido_em", "")

    return ticket


def carregar_tickets_nuvem():
    try:
        docs = db.collection(COLLECTION_TICKETS).order_by("id", direction=firestore.Query.DESCENDING).stream()
        tickets = []

        for doc in docs:
            item = normalizar_ticket(doc.to_dict())
            item["doc_id"] = doc.id
            tickets.append(item)

        return tickets
    except Exception as erro:
        st.error("Erro ao carregar tickets.")
        st.exception(erro)
        return []


def gerar_id_ticket():
    docs = db.collection(COLLECTION_TICKETS).stream()
    ids = [doc.to_dict().get("id", 0) for doc in docs]

    return max(ids, default=0) + 1


def salvar_ticket_nuvem(ticket):
    db.collection(COLLECTION_TICKETS).add(ticket)


def atualizar_ticket_nuvem(ticket):
    doc_id = ticket.get("doc_id")

    if not doc_id:
        return

    dados = ticket.copy()
    dados.pop("doc_id", None)

    db.collection(COLLECTION_TICKETS).document(doc_id).set(dados)

def sincronizar_ticket_local(ticket_atualizado):
    for indice, item in enumerate(st.session_state.tickets):
        if item.get("id") == ticket_atualizado.get("id"):
            st.session_state.tickets[indice] = ticket_atualizado
            return

    st.session_state.tickets.insert(0, ticket_atualizado)

def excluir_ticket_nuvem(ticket):
    doc_id = ticket.get("doc_id")

    if doc_id:
        db.collection(COLLECTION_TICKETS).document(doc_id).delete()


def criar_sessao(login):
    sid = uuid.uuid4().hex
    dados = {
        "login": login,
        "auth": token_diario(),
        "criado_em": agora_formatado(),
        "expira_em": (agora() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
    }

    db.collection(COLLECTION_SESSIONS).document(sid).set(dados)

    return sid


def validar_sessao(sid, auth):
    if not sid or auth != token_diario():
        return None

    doc = db.collection(COLLECTION_SESSIONS).document(sid).get()

    if not doc.exists:
        return None

    dados = doc.to_dict()
    expira = parse_data(dados.get("expira_em", ""))

    if not expira or expira < agora():
        return None

    login = dados.get("login")

    if login not in USUARIOS:
        return None

    return login


def encerrar_sessao(sid):
    if sid:
        db.collection(COLLECTION_SESSIONS).document(sid).delete()


if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "tickets" not in st.session_state:
    st.session_state.tickets = carregar_tickets_nuvem()

if "ticket_aberto" not in st.session_state:
    st.session_state.ticket_aberto = None

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Kanban"

if "proxima_pagina" not in st.session_state:
    st.session_state.proxima_pagina = None

if "sid" not in st.session_state:
    st.session_state.sid = st.query_params.get("sid", "")

if "notificacao_whatsapp" not in st.session_state:
    st.session_state.notificacao_whatsapp = None

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 1

if "ticket_url_aplicado" not in st.session_state:
    st.session_state.ticket_url_aplicado = False

def aplicar_proxima_pagina():
    if st.session_state.proxima_pagina:
        st.session_state.pagina_atual = st.session_state.proxima_pagina
        st.session_state.proxima_pagina = None


def setar_usuario_logado(login):
    dados = USUARIOS[login]
    st.session_state.logado = True
    st.session_state.usuario = {
        "login": login,
        "usuario": dados["usuario"],
        "nome": dados["nome"],
        "setor": dados["setor"],
        "email": dados["email"],
        "telefone": dados["telefone"],
    }


def restaurar_login_por_url():
    if st.session_state.logado:
        return

    sid = st.query_params.get("sid", "")
    auth = st.query_params.get("auth", "")
    login_valido = validar_sessao(sid, auth)

    if login_valido:
        st.session_state.sid = sid
        setar_usuario_logado(login_valido)


def login(usuario, senha):
    usuario = usuario.strip().lower()
    dados = USUARIOS.get(usuario)

    if dados and dados["senha"] == senha:
        sid = criar_sessao(usuario)
        st.session_state.sid = sid
        setar_usuario_logado(usuario)
        st.query_params["auth"] = token_diario()
        st.query_params["sid"] = sid
        st.rerun()

    st.error("Usuário ou senha inválidos.")


def sair():
    encerrar_sessao(st.session_state.get("sid", ""))
    st.query_params.clear()
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.ticket_aberto = None
    st.session_state.sid = ""
    st.rerun()


def criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel, nf_pedido="", anexos=None, cnpj="", origem_id=None):
    usuario = st.session_state.usuario
    ticket = {
        "id": gerar_id_ticket(),
        "titulo": titulo,
        "descricao": descricao,
        "nf_pedido": nf_pedido,
        "cnpj": cnpj,
        "anexos": anexos or [],
        "setor_origem": usuario["setor"],
        "setor_destino": setor_destino,
        "solicitante": usuario["nome"],
        "solicitante_login": usuario["login"],
        "responsavel": responsavel,
        "prioridade": prioridade,
        "status": "Aberto",
        "comentarios": [],
        "historico": [],
        "criado_em": agora_formatado(),
        "atualizado_em": agora_formatado(),
        "ticket_origem_id": origem_id,
    }

    detalhe = f"Ticket aberto para {setor_destino}."
    if nf_pedido:
        detalhe += f" NF/Pedido: {nf_pedido}."

    registrar_historico(ticket, "Ticket criado", detalhe)
    salvar_ticket_nuvem(ticket)
    st.session_state.tickets = carregar_tickets_nuvem()
    preparar_notificacao(ticket, "Novo ticket atribuído")

    return ticket


def tickets_visiveis():
    usuario = st.session_state.usuario

    if usuario["login"] in ADMIN_VIEW_ALL_EMAILS:
        return st.session_state.tickets

    return [
        ticket
        for ticket in st.session_state.tickets
        if ticket["solicitante"] == usuario["nome"]
        or ticket.get("solicitante_login") == usuario["login"]
        or ticket["responsavel"] == usuario["nome"]
        or ticket["setor_destino"] == usuario["setor"]
        or ticket["setor_origem"] == usuario["setor"]
    ]


def aplicar_filtros(tickets, prefixo, incluir_filtro_mes=True):
    col1, col2, col3, col4, col5, col6 = st.columns([1, 1.1, 1.2, 1.2, 1.1, 1.7])

    with col1:
        filtro_numero = st.text_input("Número", placeholder="00001", key=f"{prefixo}_numero")

    with col2:
        filtro_setor = st.selectbox("Setor destino", ["Todos"] + SETORES, key=f"{prefixo}_setor")

    with col3:
        filtro_responsavel = st.selectbox("Responsável", ["Todos"] + lista_responsaveis(), key=f"{prefixo}_responsavel")

    with col4:
        filtro_prioridade = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES, key=f"{prefixo}_prioridade")

    with col5:
        filtro_mes = "Mês atual"
        if incluir_filtro_mes:
            filtro_mes = st.selectbox("Resolvidos", meses_disponiveis(tickets), key=f"{prefixo}_mes_resolvido")

    with col6:
        busca = st.text_input("Buscar", placeholder="Título, descrição, NF, pedido ou CNPJ", key=f"{prefixo}_busca")

    if filtro_numero:
        numero_limpo = filtro_numero.replace("#", "").strip()
        if numero_limpo.isdigit():
            tickets = [t for t in tickets if int(t["id"]) == int(numero_limpo)]

    if filtro_setor != "Todos":
        tickets = [t for t in tickets if t["setor_destino"] == filtro_setor]

    if filtro_responsavel != "Todos":
        tickets = [t for t in tickets if t.get("responsavel") == filtro_responsavel]

    if filtro_prioridade != "Todas":
        tickets = [t for t in tickets if t["prioridade"] == filtro_prioridade]

    if incluir_filtro_mes:
        tickets = [t for t in tickets if ticket_no_mes(t, filtro_mes)]

    if busca:
        tickets = [
            t
            for t in tickets
            if busca.lower() in t["titulo"].lower()
            or busca.lower() in t["descricao"].lower()
            or busca.lower() in str(t.get("nf_pedido", "")).lower()
            or busca.lower() in str(t.get("cnpj", "")).lower()
        ]

    return tickets

def render_card(ticket):
    prioridade = prioridade_classe(ticket["prioridade"])
    dias = idade_ticket(ticket)
    classe_idade = classe_idade_ticket(dias)

    titulo = html.escape(ticket["titulo"])
    origem = html.escape(ticket["setor_origem"])
    destino = html.escape(ticket["setor_destino"])
    responsavel = html.escape(ticket["responsavel"])
    solicitante = html.escape(ticket["solicitante"])
    criado_em = html.escape(ticket.get("criado_em", ""))
    nf_pedido = html.escape(ticket.get("nf_pedido", ""))
    cnpj = html.escape(ticket.get("cnpj", ""))
    origem_id = limpar_id_origem(ticket.get("ticket_origem_id"))

    linhas_meta = [
        f"{origem} para {destino}",
        f"Responsável: {responsavel}",
        f"Solicitante: {solicitante}",
        f"Criado em: {criado_em}",
    ]

    if nf_pedido:
        linhas_meta.append(f"NF/Pedido: {nf_pedido}")

    if cnpj:
        linhas_meta.append(f"CNPJ: {cnpj}")

    if ticket.get("anexos"):
        linhas_meta.append(f"Anexos: {len(ticket.get('anexos', []))}")

    if origem_id:
        linhas_meta.append(f"Originado do {formatar_numero_ticket(origem_id)}")

    linhas_meta_html = "\n".join(
        f'<div class="ticket-meta">{linha}</div>'
        for linha in linhas_meta
        if linha
    )

    if ticket.get("status") == "Resolvido":
        pills_html = '<span class="ticket-pill age-green">Resolvido</span>'
    else:
        pills_html = f"""
            <span class="ticket-pill pill-{prioridade}">{ticket["prioridade"]}</span>
            <span class="ticket-pill {classe_idade}">{texto_idade_ticket(dias)}</span>
        """

    st.markdown(
        f"""
        <div class="ticket-card priority-{prioridade}">
            {pills_html}
            <div class="ticket-title">{formatar_numero_ticket(ticket["id"])} - {titulo}</div>
            {linhas_meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.button(
        "Abrir",
        key=f"abrir_{ticket['id']}",
        on_click=abrir_ticket,
        args=(ticket["id"],),
        use_container_width=True,
    )

def abrir_ticket(ticket_id):
    st.session_state.ticket_aberto = ticket_id
    st.rerun()


def abrir_ticket_no_kanban(ticket_id):
    st.session_state.ticket_aberto = ticket_id
    st.session_state.proxima_pagina = "Kanban"
    st.rerun()

def manter_expander_aberto(chave):
    st.session_state[chave] = True

def mostrar_logo():
    try:
        st.image("Papapa-azul.png", use_container_width=True)
    except Exception:
        st.markdown("### Papapa")


def render_notificacao_whatsapp():
    aviso = st.session_state.get("notificacao_whatsapp")

    if not aviso:
        return

    st.success("Ação salva. Você pode avisar a pessoa responsável pelo WhatsApp.")
    st.link_button(aviso["label"], aviso["url"], use_container_width=False)

    if st.button("Dispensar aviso"):
        st.session_state.notificacao_whatsapp = None
        st.rerun()

def painel_ticket():
    ticket = next((t for t in st.session_state.tickets if t["id"] == st.session_state.ticket_aberto), None)

    if not ticket:
        return

    st.divider()
    dias = idade_ticket(ticket)
    classe_idade = classe_idade_ticket(dias)

    topo1, topo2 = st.columns([4, 1])

    with topo1:
        st.subheader(f"{formatar_numero_ticket(ticket['id'])} - {ticket['titulo']}")
        
        if ticket.get("status") == "Resolvido":
            st.markdown(
                '<span class="ticket-pill age-green">Resolvido</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <span class="ticket-pill pill-{prioridade_classe(ticket['prioridade'])}">{ticket['prioridade']}</span>
                <span class="ticket-pill {classe_idade}">{texto_idade_ticket(dias)}</span>
                """,
                unsafe_allow_html=True,
            )
        st.caption(f"{ticket['setor_origem']} para {ticket['setor_destino']} | Criado em {ticket.get('criado_em', '')}")

    with topo2:
        if st.button("Fechar painel", use_container_width=True):
            st.session_state.ticket_aberto = None
            st.rerun()

    col_tratativa, col_comentarios = st.columns([1.15, 1])

    with col_tratativa:
        st.markdown("#### Tratativa")
        st.write(ticket["descricao"])

        if ticket.get("nf_pedido"):
            st.write(f"**NF/Pedido:** {ticket['nf_pedido']}")

        if ticket.get("cnpj"):
            st.write(f"**CNPJ:** {ticket['cnpj']}")

        st.markdown("#### Anexos do ticket")
        render_anexos(ticket.get("anexos", []), f"ticket_{ticket['id']}")

        status_anterior = ticket["status"]
        responsavel_anterior = ticket["responsavel"]
        prioridade_anterior = ticket["prioridade"]
        setor_anterior = ticket["setor_destino"]

        novo_status = st.selectbox(
            "Status",
            STATUS,
            index=STATUS.index(ticket["status"]) if ticket["status"] in STATUS else 0,
            key=f"status_{ticket['id']}",
        )

        novo_setor_destino = st.selectbox(
            "Setor destino",
            SETORES,
            index=SETORES.index(ticket["setor_destino"]) if ticket["setor_destino"] in SETORES else 0,
            key=f"setor_destino_{ticket['id']}",
        )

        responsaveis_destino = lista_responsaveis(novo_setor_destino)

        novo_responsavel = st.selectbox(
            "Responsável",
            responsaveis_destino,
            index=responsaveis_destino.index(ticket["responsavel"]) if ticket["responsavel"] in responsaveis_destino else 0,
            key=f"responsavel_{ticket['id']}",
        )

        nova_prioridade = st.selectbox(
            "Prioridade",
            PRIORIDADES,
            index=PRIORIDADES.index(ticket["prioridade"]) if ticket["prioridade"] in PRIORIDADES else 1,
            key=f"prioridade_{ticket['id']}",
        )
        
        st.write(f"**Solicitante:** {ticket['solicitante']}")
        st.write(f"**Origem:** {ticket['setor_origem']}")
        st.write(f"**Destino atual:** {ticket['setor_destino']}")

        if st.button("Salvar alterações", type="primary", use_container_width=True):
            mudancas = []

            if status_anterior != novo_status:
                mudancas.append(f"status de {status_anterior} para {novo_status}")

            if responsavel_anterior != novo_responsavel:
                mudancas.append(f"responsável de {responsavel_anterior} para {novo_responsavel}")

            if prioridade_anterior != nova_prioridade:
                mudancas.append(f"prioridade de {prioridade_anterior} para {nova_prioridade}")

            if setor_anterior != novo_setor_destino:
                mudancas.append(f"setor destino de {setor_anterior} para {novo_setor_destino}")

            ticket["status"] = novo_status
            ticket["setor_destino"] = novo_setor_destino
            ticket["responsavel"] = novo_responsavel
            ticket["prioridade"] = nova_prioridade
            ticket["atualizado_em"] = agora_formatado()

            if mudancas:
                registrar_historico(ticket, "Ticket atualizado", "; ".join(mudancas))
                destinatario = nome_para_notificacao(
                    ticket,
                    responsavel_anterior=responsavel_anterior,
                    novo_responsavel=novo_responsavel,
                )

                preparar_notificacao(ticket, "Atualização de ticket", destinatario)

            atualizar_ticket_nuvem(ticket)
            st.session_state.tickets = carregar_tickets_nuvem()
            st.success("Ticket atualizado.")
            st.rerun()

        st.markdown("#### Resolver e encaminhar")

        chave_expander = f"expander_encaminhar_{ticket['id']}"

        with st.expander(
            "Encaminhar para outro setor após resolver",
            expanded=st.session_state.get(chave_expander, False),
        ):
            novo_setor = st.selectbox(
                "Novo setor destino",
                SETORES,
                key=f"enc_setor_{ticket['id']}",
                on_change=manter_expander_aberto,
                args=(chave_expander,),
            )
            novo_resp = st.selectbox(
                "Novo responsável",
                lista_responsaveis(novo_setor),
                key=f"enc_resp_{ticket['id']}",
                on_change=manter_expander_aberto,
                args=(chave_expander,),
            )
            novo_titulo = st.text_input(
                "Título do novo ticket",
                value=f"Continuação de {formatar_numero_ticket(ticket['id'])} - {ticket['titulo']}",
                key=f"enc_titulo_{ticket['id']}",
                on_change=manter_expander_aberto,
                args=(chave_expander,),
            )
            nova_desc = st.text_area(
                "Descrição do encaminhamento",
                value=f"Ticket originado do {formatar_numero_ticket(ticket['id'])}.\n\nContexto anterior:\n{ticket['descricao']}",
                height=120,
                key=f"enc_desc_{ticket['id']}",
                on_change=manter_expander_aberto,
                args=(chave_expander,),
            )

            if st.button("Resolver atual e criar encaminhamento", use_container_width=True):
                ticket["status"] = "Resolvido"
                ticket["atualizado_em"] = agora_formatado()
                registrar_historico(ticket, "Ticket resolvido e encaminhado", f"Novo encaminhamento para {novo_setor}.")
                atualizar_ticket_nuvem(ticket)

                novo_ticket = criar_ticket(
                    novo_titulo.strip(),
                    nova_desc.strip(),
                    novo_setor,
                    ticket["prioridade"],
                    novo_resp,
                    ticket.get("nf_pedido", ""),
                    [],
                    origem_id=ticket["id"],
                )

                st.session_state.ticket_aberto = novo_ticket["id"]
                st.session_state.tickets = carregar_tickets_nuvem()
                st.success("Ticket atual resolvido e novo ticket criado.")
                st.rerun()

        if st.session_state.usuario["login"] in ADMIN_DELETE_EMAILS:
            st.warning("Ação administrativa disponível apenas para João Tadra.")
            confirmar = st.checkbox("Confirmo que quero excluir este ticket", key=f"confirmar_exclusao_{ticket['id']}")

            if st.button("Excluir ticket", type="secondary", use_container_width=True):
                if confirmar:
                    excluir_ticket_nuvem(ticket)
                    st.session_state.ticket_aberto = None
                    st.session_state.tickets = carregar_tickets_nuvem()
                    st.success("Ticket excluído.")
                    st.rerun()
                else:
                    st.error("Marque a confirmação antes de excluir.")

    with col_comentarios:
        st.markdown("#### Comentários")

        if not ticket["comentarios"]:
            st.caption("Nenhum comentário ainda.")

        comentarios_ordenados = list(reversed(list(enumerate(ticket["comentarios"]))))

        for idx, comentario in comentarios_ordenados:
            autor = html.escape(comentario.get("autor", ""))
            texto = html.escape(comentario.get("texto", ""))
            criado_em = html.escape(comentario.get("criado_em", ""))

            if comentario.get("excluido"):
                st.markdown(
                    f"""
                    <div class="comment-box">
                        <div class="comment-author">Comentário excluído</div>
                        <div class="ticket-meta">
                            Excluído por {html.escape(comentario.get("excluido_por", ""))} em {html.escape(comentario.get("excluido_em", ""))}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                continue

            st.markdown(
                f"""
                <div class="comment-box">
                    <div class="comment-author">{autor}</div>
                    <div class="comment-text">{texto}</div>
                    <div class="ticket-meta">{criado_em}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if comentario.get("editado_em"):
                st.caption(f"Editado por {comentario.get('editado_por', '')} em {comentario.get('editado_em', '')}")

            if comentario.get("anexos"):
                render_anexos(comentario["anexos"], f"comentario_{ticket['id']}_{idx}")

            pode_editar = (
                comentario.get("autor") == st.session_state.usuario["nome"]
                or st.session_state.usuario["login"] in ADMIN_COMMENT_EMAILS
            )

            if pode_editar:
                chave_editando = f"editando_comentario_{ticket['id']}_{idx}"
                chave_excluindo = f"excluindo_comentario_{ticket['id']}_{idx}"

                col_op1, col_op2, col_op3 = st.columns([1, 1, 5])

                with col_op1:
                    if st.button("Editar", key=f"btn_editar_{ticket['id']}_{idx}"):
                        st.session_state[chave_editando] = True
                        st.session_state[chave_excluindo] = False
                        st.rerun()

                with col_op2:
                    if st.button("Excluir", key=f"btn_excluir_{ticket['id']}_{idx}"):
                        st.session_state[chave_excluindo] = True
                        st.session_state[chave_editando] = False
                        st.rerun()

                if st.session_state.get(chave_editando, False):
                    texto_editado = st.text_area(
                        "Editar comentário",
                        value=comentario.get("texto", ""),
                        key=f"editar_comentario_{ticket['id']}_{idx}",
                        height=110,
                    )

                    col_salvar, col_cancelar = st.columns(2)

                    with col_salvar:
                        if st.button("Salvar", key=f"salvar_comentario_{ticket['id']}_{idx}", use_container_width=True):
                            ticket["comentarios"][idx]["texto"] = texto_editado.strip()
                            ticket["comentarios"][idx]["editado_por"] = st.session_state.usuario["nome"]
                            ticket["comentarios"][idx]["editado_em"] = agora_formatado()
                            ticket["atualizado_em"] = agora_formatado()
                            registrar_historico(ticket, "Comentário editado", f"Comentário de {comentario.get('autor', '')} editado.")
                            atualizar_ticket_nuvem(ticket)
                            sincronizar_ticket_local(ticket)
                            st.session_state[chave_editando] = False
                            st.rerun()

                    with col_cancelar:
                        if st.button("Cancelar", key=f"cancelar_edicao_{ticket['id']}_{idx}", use_container_width=True):
                            st.session_state[chave_editando] = False
                            st.rerun()

                if st.session_state.get(chave_excluindo, False):
                    st.warning("Tem certeza que deseja excluir este comentário?")

                    col_confirmar, col_cancelar = st.columns(2)

                    with col_confirmar:
                        if st.button("Confirmar exclusão", key=f"confirmar_excluir_comentario_{ticket['id']}_{idx}", use_container_width=True):
                            ticket["comentarios"][idx]["excluido"] = True
                            ticket["comentarios"][idx]["texto"] = ""
                            ticket["comentarios"][idx]["excluido_por"] = st.session_state.usuario["nome"]
                            ticket["comentarios"][idx]["excluido_em"] = agora_formatado()
                            ticket["atualizado_em"] = agora_formatado()
                            registrar_historico(ticket, "Comentário excluído", f"Comentário de {comentario.get('autor', '')} excluído.")
                            atualizar_ticket_nuvem(ticket)
                            sincronizar_ticket_local(ticket)
                            st.session_state[chave_excluindo] = False
                            st.rerun()

                    with col_cancelar:
                        if st.button("Cancelar", key=f"cancelar_exclusao_{ticket['id']}_{idx}", use_container_width=True):
                            st.session_state[chave_excluindo] = False
                            st.rerun()

        st.markdown("#### Novo comentário")

        arquivos_comentario = st.file_uploader(
            "Anexar arquivos ao comentário:",
            type=TIPOS_ANEXOS,
            accept_multiple_files=True,
            key=f"anexos_comentario_{ticket['id']}_{st.session_state.uploader_key}",
        )

        novo_comentario = st.chat_input(
            "Digite um comentário e pressione Enter",
            key=f"chat_comentario_{ticket['id']}",
        )

        if novo_comentario:
            anexos_comentario = salvar_uploads(arquivos_comentario)
            ticket["comentarios"].append(
                {
                    "autor": st.session_state.usuario["nome"],
                    "texto": novo_comentario.strip(),
                    "anexos": anexos_comentario,
                    "criado_em": agora_formatado(),
                    "excluido": False,
                    "editado_por": "",
                    "editado_em": "",
                    "excluido_por": "",
                    "excluido_em": "",
                }
            )
            ticket["atualizado_em"] = agora_formatado()
            registrar_historico(ticket, "Comentário adicionado", novo_comentario.strip()[:120] or "Comentário com anexo.")
            atualizar_ticket_nuvem(ticket)
            preparar_notificacao(ticket, "Novo comentário", nome_para_notificacao(ticket))
            sincronizar_ticket_local(ticket)
            st.session_state.uploader_key += 1
            st.rerun()

        if arquivos_comentario and not novo_comentario:
            st.caption("Digite uma mensagem e pressione Enter para enviar junto com os anexos.")

        st.markdown("#### Histórico")
        historico = ticket.get("historico", [])

        if not historico:
            st.caption("Nenhum histórico ainda.")

        for item in reversed(historico[-12:]):
            autor = html.escape(item.get("autor", ""))
            acao = html.escape(item.get("acao", ""))
            detalhe = html.escape(item.get("detalhe", ""))
            criado_em = html.escape(item.get("criado_em", ""))
            st.markdown(f"<div class='history-box'><b>{acao}</b><br>{detalhe}<br><span class='ticket-meta'>{autor} em {criado_em}</span></div>", unsafe_allow_html=True)


restaurar_login_por_url()
aplicar_proxima_pagina()

if st.session_state.logado and not st.session_state.ticket_url_aplicado:
    ticket_url = st.query_params.get("ticket", "")

    if ticket_url and str(ticket_url).isdigit():
        st.session_state.ticket_aberto = int(ticket_url)
        st.session_state.pagina_atual = "Kanban"

    st.session_state.ticket_url_aplicado = True

if not st.session_state.logado:
    left, center, right = st.columns([1, 1.15, 1])

    with center:
        mostrar_logo()
        st.title("Central de Tickets")
        st.caption("Atendimento interno Papapa")

        with st.form("login"):
            usuario_login = st.text_input("E-mail")
            senha_login = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary")

            if entrar:
                login(usuario_login, senha_login)

    st.stop()

if st.session_state.pagina_atual == "Kanban" and st.session_state.ticket_aberto is None:
    st_autorefresh(interval=60000, key="tickets_autorefresh")
    st.session_state.tickets = carregar_tickets_nuvem()

usuario = st.session_state.usuario

with st.sidebar:
    mostrar_logo()
    st.write(f"**{usuario['nome']}**")
    st.caption(usuario["setor"])
    st.caption(usuario["email"])
    st.caption(f"Auth diária: {token_diario()}")

    st.radio("Menu", ["Kanban", "Novo ticket", "Meus tickets", "Tickets atribuídos a mim", "Dashboard"], key="pagina_atual")

    st.divider()

    if st.button("Sair", use_container_width=True):
        sair()


pagina = st.session_state.pagina_atual

st.title("Central de Tickets")
st.caption("Gestão interna de solicitações entre áreas")

render_notificacao_whatsapp()

tickets = tickets_visiveis()
meus_tickets_abertos = [t for t in tickets if t["solicitante"] == usuario["nome"] or t.get("solicitante_login") == usuario["login"]]
tickets_atribuidos = [t for t in tickets if t["responsavel"] == usuario["nome"]]

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Tickets visíveis", len(tickets))
m2.metric("Abertos por mim", len(meus_tickets_abertos))
m3.metric("Atribuídos a mim", len(tickets_atribuidos))
m4.metric("Em andamento", len([t for t in tickets if t["status"] in ["Em análise", "Em execução"]]))
m5.metric("Resolvidos", len([t for t in tickets if t["status"] == "Resolvido"]))

st.divider()

if pagina == "Novo ticket":
    st.subheader("Abrir novo ticket")

    titulo = st.text_input("Título")
    descricao = st.text_area("Descrição", height=160)
    nf_pedido = st.text_input("Número da NF ou Pedido:", key="input_nf_pedido")
    cnpj = st.text_input("CNPJ:", key="input_cnpj")
    
    arquivos_ticket = st.file_uploader(
        "Anexar fotos/vídeos/documentos:",
        type=TIPOS_ANEXOS,
        accept_multiple_files=True,
        key=f"input_midia_ticket_{st.session_state.uploader_key}",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        setor_destino = st.selectbox("Setor destino", SETORES, key="novo_setor_destino")

    with col2:
        prioridade = st.selectbox("Prioridade", PRIORIDADES, index=1, key="novo_prioridade")

    with col3:
        responsavel = st.selectbox("Responsável", lista_responsaveis(setor_destino), key="novo_responsavel")

    if st.button("Abrir ticket", type="primary"):
        if not titulo.strip() or not descricao.strip():
            st.error("Preencha título e descrição.")
        else:
            anexos_ticket = salvar_uploads(arquivos_ticket)
            novo_ticket = criar_ticket(
                titulo.strip(),
                descricao.strip(),
                setor_destino,
                prioridade,
                responsavel,
                nf_pedido.strip(),
                anexos_ticket,
                cnpj.strip(),
            )
            
            st.success(f"Ticket {formatar_numero_ticket(novo_ticket['id'])} criado com sucesso.")
            st.session_state.ticket_aberto = novo_ticket["id"]
            st.session_state.proxima_pagina = "Kanban"
            st.session_state.uploader_key += 1
            st.rerun()

elif pagina == "Kanban":
    st.subheader("Todos os tickets")
    st.caption("O filtro de mês afeta apenas tickets resolvidos. Tickets abertos ou em andamento continuam aparecendo mesmo virando o mês.")

    tickets_filtrados = aplicar_filtros(tickets, "kanban", incluir_filtro_mes=True)
    st.write("")

    colunas = st.columns(len(STATUS), gap="small")

    for indice, status in enumerate(STATUS):
        with colunas[indice]:
            tickets_status = [t for t in tickets_filtrados if t["status"] == status]
            st.markdown(f"#### {status}")
            st.caption(f"{len(tickets_status)} ticket(s)")

            if not tickets_status:
                st.markdown('<div class="kanban-empty">Nenhum ticket</div>', unsafe_allow_html=True)

            for ticket in tickets_status:
                render_card(ticket)

    painel_ticket()

elif pagina == "Meus tickets":
    st.subheader("Meus tickets")
    st.caption("Aqui ficam os tickets que você abriu como solicitante.")

    meus_tickets = aplicar_filtros(meus_tickets_abertos, "meus_tickets", incluir_filtro_mes=True)

    if not meus_tickets:
        st.info("Nenhum ticket aberto por você.")
    else:
        for ticket in meus_tickets:
            with st.expander(f"{formatar_numero_ticket(ticket['id'])} - {ticket['titulo']} | {ticket['status']}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(ticket["descricao"])
                    if ticket.get("nf_pedido"):
                        st.write(f"**NF/Pedido:** {ticket['nf_pedido']}")
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Prioridade:** {ticket['prioridade']}")
                    st.write(f"**Solicitante:** {ticket['solicitante']}")
                    st.write(f"**Responsável:** {ticket['responsavel']}")
                    st.write(f"**Setor destino:** {ticket['setor_destino']}")
                    st.write(f"**Criado em:** {ticket.get('criado_em', '')}")

                with col2:
                    st.button("Abrir / comentar", key=f"ir_kanban_meus_{ticket['id']}", on_click=abrir_ticket_no_kanban, args=(ticket["id"],), use_container_width=True)

elif pagina == "Tickets atribuídos a mim":
    st.subheader("Tickets atribuídos a mim")
    st.caption("Aqui ficam os tickets em que você é o responsável direto.")

    atribuidos = aplicar_filtros(tickets_atribuidos, "atribuidos", incluir_filtro_mes=True)

    if not atribuidos:
        st.info("Nenhum ticket atribuído a você.")
    else:
        for ticket in atribuidos:
            with st.expander(f"{formatar_numero_ticket(ticket['id'])} - {ticket['titulo']} | {ticket['status']}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(ticket["descricao"])
                    if ticket.get("nf_pedido"):
                        st.write(f"**NF/Pedido:** {ticket['nf_pedido']}")
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Prioridade:** {ticket['prioridade']}")
                    st.write(f"**Solicitante:** {ticket['solicitante']}")
                    st.write(f"**Setor destino:** {ticket['setor_destino']}")
                    st.write(f"**Criado em:** {ticket.get('criado_em', '')}")

                with col2:
                    st.button("Tratar ticket", key=f"ir_kanban_atribuidos_{ticket['id']}", on_click=abrir_ticket_no_kanban, args=(ticket["id"],), use_container_width=True)

elif pagina == "Dashboard":
    st.subheader("Dashboard")

    st.markdown(
        """
        <style>
            .dash-hero {
                background: linear-gradient(135deg, #082b57 0%, #0f4c81 58%, #ff4b4b 100%);
                color: white;
                padding: 22px 24px;
                border-radius: 14px;
                margin: 6px 0 18px 0;
                box-shadow: 0 14px 32px rgba(8, 43, 87, 0.16);
            }
            .dash-hero h3 {
                margin: 0 0 6px 0;
                color: white;
                font-size: 24px;
            }
            .dash-hero p {
                margin: 0;
                opacity: 0.88;
                font-size: 14px;
            }
            .insight-card {
                border: 1px solid #e7edf5;
                background: #ffffff;
                border-radius: 12px;
                padding: 14px 16px;
                min-height: 92px;
                box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            }
            .insight-label {
                color: #64748b;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                margin-bottom: 6px;
            }
            .insight-value {
                color: #0f172a;
                font-size: 22px;
                font-weight: 800;
                margin-bottom: 3px;
            }
            .insight-note {
                color: #64748b;
                font-size: 13px;
                line-height: 1.35;
            }
            .alert-line {
                border-left: 4px solid #ff4b4b;
                background: #fff6f6;
                border-radius: 10px;
                padding: 10px 12px;
                margin-bottom: 8px;
                color: #172033;
            }
            .ok-line {
                border-left: 4px solid #16a34a;
                background: #f0fdf4;
                border-radius: 10px;
                padding: 10px 12px;
                margin-bottom: 8px;
                color: #172033;
            }
            .data-table table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
            }
            .data-table th {
                text-align: left;
                background: #f8fafc;
                color: #475569;
                font-weight: 700;
                padding: 10px 9px;
                border-bottom: 1px solid #e5e7eb;
            }
            .data-table td {
                padding: 9px;
                border-bottom: 1px solid #edf2f7;
                color: #172033;
                vertical-align: top;
            }
            .data-table tr:hover td {
                background: #f8fbff;
            }
            .ticket-link {
                color: #0f4c81 !important;
                font-weight: 800;
                text-decoration: none !important;
            }
            .ticket-link:hover {
                text-decoration: underline !important;
            }
        </style>
        <div class="dash-hero">
            <h3>Central de performance dos tickets</h3>
            <p>Visão executiva de volume, gargalos, tempo de resposta, tempo por etapa e resolução.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    def parse_dt_dashboard(valor):
        return parse_data(valor) if valor else None

    def horas_entre(inicio, fim):
        if not inicio or not fim:
            return None
        return max((fim - inicio).total_seconds() / 3600, 0)

    def formatar_horas(valor):
        if valor is None or pd.isna(valor):
            return "Sem dado"
        if valor < 1:
            return f"{valor * 60:.0f} min"
        if valor < 24:
            return f"{valor:.1f} h"
        return f"{valor / 24:.1f} dias"

    def media_segura(serie):
        serie = pd.Series(serie).dropna()
        return float(serie.mean()) if not serie.empty else None

    def link_ticket_dashboard(ticket_id):
        auth = st.query_params.get("auth", token_diario())
        sid = st.query_params.get("sid", st.session_state.get("sid", ""))
        return f"?auth={auth}&sid={sid}&ticket={ticket_id}"

    def ticket_anchor(ticket_id):
        numero = formatar_numero_ticket(ticket_id)
        url = link_ticket_dashboard(ticket_id)
        return f'<a class="ticket-link" href="{url}" target="_self">{numero}</a>'

    def status_extraido_do_detalhe(detalhe):
        if not detalhe:
            return None

        for linha in str(detalhe).splitlines():
            if "Status" not in linha:
                continue

            encontrados = []
            for status in STATUS:
                posicao = linha.rfind(status)
                if posicao >= 0:
                    encontrados.append((posicao, status))

            if encontrados:
                return sorted(encontrados, key=lambda item: item[0])[-1][1]

        return None

    def eventos_status_ticket(ticket):
        eventos = []

        criado = parse_dt_dashboard(ticket.get("criado_em", ""))
        if criado:
            eventos.append(
                {
                    "quando": criado,
                    "status": "Aberto",
                    "origem": "Criação",
                }
            )

        for item in ticket.get("historico", []):
            quando = parse_dt_dashboard(item.get("criado_em", ""))
            status_novo = status_extraido_do_detalhe(
                f"{item.get('acao', '')}\n{item.get('detalhe', '')}"
            )

            if quando and status_novo:
                eventos.append(
                    {
                        "quando": quando,
                        "status": status_novo,
                        "origem": item.get("acao", ""),
                    }
                )

        eventos = sorted(eventos, key=lambda item: item["quando"])

        eventos_limpos = []
        for evento in eventos:
            if not eventos_limpos or eventos_limpos[-1]["status"] != evento["status"]:
                eventos_limpos.append(evento)

        return eventos_limpos

    def metricas_tempo_ticket(ticket):
        criado = parse_dt_dashboard(ticket.get("criado_em", ""))
        atualizado = parse_dt_dashboard(ticket.get("atualizado_em", ""))
        agora_ref = agora()

        comentarios_validos = [
            c for c in ticket.get("comentarios", [])
            if not c.get("excluido")
        ]

        primeira_resposta = None
        for comentario in comentarios_validos:
            autor = comentario.get("autor", "")
            quando = parse_dt_dashboard(comentario.get("criado_em", ""))

            if (
                criado
                and quando
                and autor
                and autor != ticket.get("solicitante", "")
                and quando >= criado
            ):
                if primeira_resposta is None or quando < primeira_resposta:
                    primeira_resposta = quando

        eventos = eventos_status_ticket(ticket)
        status_atual = ticket.get("status", "Aberto")

        data_resolucao = None
        for evento in eventos:
            if evento["status"] == "Resolvido":
                data_resolucao = evento["quando"]

        if not data_resolucao and status_atual == "Resolvido":
            data_resolucao = atualizado or agora_ref

        fim_geral = data_resolucao if status_atual == "Resolvido" and data_resolucao else agora_ref

        tempo_por_status_corrido = {status: 0.0 for status in STATUS}
        tempo_por_status_util = {status: 0.0 for status in STATUS}

        if eventos:
            for indice, evento in enumerate(eventos):
                inicio = evento["quando"]

                if indice + 1 < len(eventos):
                    fim = eventos[indice + 1]["quando"]
                else:
                    fim = fim_geral

                duracao_corrida = horas_corridas_entre(inicio, fim)
                duracao_util = horas_uteis_entre(inicio, fim)

                if duracao_corrida is not None and evento["status"] in tempo_por_status_corrido:
                    tempo_por_status_corrido[evento["status"]] += duracao_corrida

                if duracao_util is not None and evento["status"] in tempo_por_status_util:
                    tempo_por_status_util[evento["status"]] += duracao_util

        return {
            "tempo_resolucao_h": horas_corridas_entre(criado, data_resolucao) if data_resolucao else None,
            "tempo_resolucao_util_h": horas_uteis_entre(criado, data_resolucao) if data_resolucao else None,
            "tempo_primeiro_retorno_h": horas_corridas_entre(criado, primeira_resposta) if primeira_resposta else None,
            "tempo_primeiro_retorno_util_h": horas_uteis_entre(criado, primeira_resposta) if primeira_resposta else None,
            "tempo_total_h": horas_corridas_entre(criado, fim_geral) if criado else None,
            "tempo_total_util_h": horas_uteis_entre(criado, fim_geral) if criado else None,
            "tempo_aberto_h": tempo_por_status_corrido.get("Aberto", 0),
            "tempo_aberto_util_h": tempo_por_status_util.get("Aberto", 0),
            "tempo_em_analise_h": tempo_por_status_corrido.get("Em análise", 0),
            "tempo_em_analise_util_h": tempo_por_status_util.get("Em análise", 0),
            "tempo_aguardando_h": tempo_por_status_corrido.get("Aguardando retorno", 0),
            "tempo_aguardando_util_h": tempo_por_status_util.get("Aguardando retorno", 0),
            "tempo_em_execucao_h": tempo_por_status_corrido.get("Em execução", 0),
            "tempo_em_execucao_util_h": tempo_por_status_util.get("Em execução", 0),
            "tempo_resolvido_h": tempo_por_status_corrido.get("Resolvido", 0),
            "tempo_resolvido_util_h": tempo_por_status_util.get("Resolvido", 0),
        }

    def render_tabela_clicavel(df_tabela, colunas):
        if df_tabela.empty:
            st.caption("Nenhum registro encontrado.")
            return

        tabela = df_tabela[colunas].copy()

        if "Ticket" in tabela.columns:
            tabela["Ticket"] = tabela["Ticket"].astype(str)

        html_tabela = tabela.to_html(
            index=False,
            escape=False,
            classes="data-table-inner",
        )

        st.markdown(
            f'<div class="data-table">{html_tabela}</div>',
            unsafe_allow_html=True,
        )

    colf1, colf2, colf3, colf4 = st.columns(4)

    with colf1:
        filtro_periodo = st.selectbox(
            "Período",
            ["Mês atual", "Últimos 7 dias", "Últimos 30 dias", "Período específico", "Todos"],
            key="dash_periodo",
        )

    with colf2:
        filtro_setor_dash = st.selectbox(
            "Setor destino",
            ["Todos"] + SETORES,
            key="dash_setor",
        )

    with colf3:
        filtro_responsavel_dash = st.selectbox(
            "Responsável",
            ["Todos"] + lista_responsaveis(),
            key="dash_responsavel",
        )

    with colf4:
        filtro_status_dash = st.selectbox(
            "Status",
            ["Todos"] + STATUS,
            key="dash_status",
        )

    data_inicio = None
    data_fim = None

    if filtro_periodo == "Período específico":
        col_data1, col_data2 = st.columns(2)

        with col_data1:
            data_inicio = st.date_input(
                "Data inicial",
                value=agora().date().replace(day=1),
                key="dash_data_inicio",
            )

        with col_data2:
            data_fim = st.date_input(
                "Data final",
                value=agora().date(),
                key="dash_data_fim",
            )

    tickets_dashboard = tickets.copy()
    hoje = agora().date()

    if filtro_periodo == "Mês atual":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if parse_dt_dashboard(t.get("criado_em", ""))
            and parse_dt_dashboard(t.get("criado_em", "")).strftime("%Y-%m") == agora().strftime("%Y-%m")
        ]

    elif filtro_periodo == "Últimos 7 dias":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if parse_dt_dashboard(t.get("criado_em", ""))
            and (hoje - parse_dt_dashboard(t.get("criado_em", "")).date()).days <= 7
        ]

    elif filtro_periodo == "Últimos 30 dias":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if parse_dt_dashboard(t.get("criado_em", ""))
            and (hoje - parse_dt_dashboard(t.get("criado_em", "")).date()).days <= 30
        ]

    elif filtro_periodo == "Período específico":
        if data_inicio > data_fim:
            st.error("A data inicial não pode ser maior que a data final.")
            tickets_dashboard = []
        else:
            tickets_dashboard = [
                t for t in tickets_dashboard
                if parse_dt_dashboard(t.get("criado_em", ""))
                and data_inicio <= parse_dt_dashboard(t.get("criado_em", "")).date() <= data_fim
            ]

    if filtro_setor_dash != "Todos":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if t.get("setor_destino") == filtro_setor_dash
        ]

    if filtro_responsavel_dash != "Todos":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if t.get("responsavel") == filtro_responsavel_dash
        ]

    if filtro_status_dash != "Todos":
        tickets_dashboard = [
            t for t in tickets_dashboard
            if t.get("status") == filtro_status_dash
        ]

    if not tickets_dashboard:
        st.info("Nenhum ticket encontrado para os filtros selecionados.")
    else:
        registros = []

        for ticket in tickets_dashboard:
            criado = parse_dt_dashboard(ticket.get("criado_em", ""))
            atualizado = parse_dt_dashboard(ticket.get("atualizado_em", ""))

            comentarios = ticket.get("comentarios", [])
            comentarios_validos = [
                c for c in comentarios
                if not c.get("excluido")
            ]

            tempos = metricas_tempo_ticket(ticket)

            registros.append(
                {
                    "id": ticket.get("id"),
                    "Ticket": ticket_anchor(ticket.get("id")),
                    "ticket_numero": formatar_numero_ticket(ticket.get("id")),
                    "Título": html.escape(ticket.get("titulo", "")),
                    "NF/Pedido": html.escape(ticket.get("nf_pedido", "")),
                    "CNPJ": html.escape(ticket.get("cnpj", "")),
                    "Status": ticket.get("status", ""),
                    "Prioridade": ticket.get("prioridade", ""),
                    "Setor origem": ticket.get("setor_origem", ""),
                    "Setor destino": ticket.get("setor_destino", ""),
                    "Solicitante": ticket.get("solicitante", ""),
                    "Responsável": ticket.get("responsavel", ""),
                    "Dias aberto": idade_ticket(ticket),
                    "Comentários": len(comentarios_validos),
                    "Tem anexo": "Sim" if len(ticket.get("anexos", [])) > 0 else "Não",
                    "Criado em": ticket.get("criado_em", ""),
                    "Atualizado em": ticket.get("atualizado_em", ""),
                    "data_criacao": criado.date() if criado else None,
                    "data_resolucao": atualizado.date() if atualizado and ticket.get("status") == "Resolvido" else None,
                    "Tempo resolução h": tempos["tempo_resolucao_h"],
                    "Tempo resolução útil h": tempos["tempo_resolucao_util_h"],
                    "Tempo primeiro retorno h": tempos["tempo_primeiro_retorno_h"],
                    "Tempo primeiro retorno útil h": tempos["tempo_primeiro_retorno_util_h"],
                    "Tempo total h": tempos["tempo_total_h"],
                    "Tempo total útil h": tempos["tempo_total_util_h"],
                    "Aberto h": tempos["tempo_aberto_h"],
                    "Aberto útil h": tempos["tempo_aberto_util_h"],
                    "Em análise h": tempos["tempo_em_analise_h"],
                    "Em análise útil h": tempos["tempo_em_analise_util_h"],
                    "Aguardando retorno h": tempos["tempo_aguardando_h"],
                    "Aguardando retorno útil h": tempos["tempo_aguardando_util_h"],
                    "Em execução h": tempos["tempo_em_execucao_h"],
                    "Em execução útil h": tempos["tempo_em_execucao_util_h"],
                    "Resolvido h": tempos["tempo_resolvido_h"],
                    "Resolvido útil h": tempos["tempo_resolvido_util_h"],
                }
            )

        df = pd.DataFrame(registros)

        total = len(df)
        abertos = len(df[df["Status"] == "Aberto"])
        em_andamento = len(df[df["Status"].isin(["Em análise", "Em execução"])])
        aguardando = len(df[df["Status"] == "Aguardando retorno"])
        resolvidos = len(df[df["Status"] == "Resolvido"])
        urgentes_abertos = len(df[(df["Prioridade"] == "Urgente") & (df["Status"] != "Resolvido")])
        criticos = len(df[(df["Dias aberto"] >= 3) & (df["Status"] != "Resolvido")])
        sem_responsavel = len(df[(df["Responsável"] == "Não atribuído") & (df["Status"] != "Resolvido")])
        taxa_resolucao = (resolvidos / total * 100) if total else 0

        abertos_df = df[df["Status"] != "Resolvido"]
        resolvidos_df = df[df["Status"] == "Resolvido"]

        idade_media_abertos = abertos_df["Dias aberto"].mean() if not abertos_df.empty else 0
        media_comentarios = df["Comentários"].mean() if total else 0
        tempo_medio_resolucao = media_segura(resolvidos_df["Tempo resolução h"]) if not resolvidos_df.empty else None
        tempo_medio_primeiro_retorno = media_segura(df["Tempo primeiro retorno h"])
        tempo_medio_total_aberto = media_segura(abertos_df["Tempo total h"]) if not abertos_df.empty else None
        tempo_medio_resolucao_util = media_segura(resolvidos_df["Tempo resolução útil h"]) if not resolvidos_df.empty else None
        tempo_medio_primeiro_retorno_util = media_segura(df["Tempo primeiro retorno útil h"])
        tempo_medio_total_aberto_util = media_segura(abertos_df["Tempo total útil h"]) if not abertos_df.empty else None
        
        st.markdown("#### Resumo executivo")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total filtrado", total)
        m2.metric("Resolvidos", resolvidos)
        m3.metric("Taxa de resolução", f"{taxa_resolucao:.0f}%")
        m4.metric("Críticos 3+ dias", criticos)
        m5.metric("Sem responsável", sem_responsavel)

        m6, m7, m8, m9, m10 = st.columns(5)
        m6.metric("Abertos", abertos)
        m7.metric("Em andamento", em_andamento)
        m8.metric("Aguardando", aguardando)
        m9.metric("Urgentes abertos", urgentes_abertos)
        m10.metric("Idade média aberto", f"{idade_media_abertos:.1f} dias")

        st.caption(f"Média de comentários por ticket: {media_comentarios:.1f}")

        st.divider()

        st.markdown("#### Indicadores de tempo")

        col_t1, col_t2, col_t3, col_t4 = st.columns(4)

        with col_t1:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-label">Tempo médio de resolução</div>
                    <div class="insight-value">{formatar_tempo_duplo(tempo_medio_resolucao, tempo_medio_resolucao_util)}</div>
                    <div class="insight-note">Entre abertura e status resolvido.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_t2:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-label">Tempo médio de retorno</div>
                    <div class="insight-value">{formatar_tempo_duplo(tempo_medio_primeiro_retorno, tempo_medio_primeiro_retorno_util)}</div>
                    <div class="insight-note">Da abertura até o primeiro comentário de outra pessoa.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_t3:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-label">Tempo médio em aberto</div>
                    <div class="insight-value">{formatar_tempo_duplo(tempo_medio_total_aberto, tempo_medio_total_aberto_util)}</div>
                    <div class="insight-note">Tickets ainda não resolvidos.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_t4:
            gargalos_status = {
                "Aberto": media_segura(df["Aberto h"]),
                "Em análise": media_segura(df["Em análise h"]),
                "Aguardando retorno": media_segura(df["Aguardando retorno h"]),
                "Em execução": media_segura(df["Em execução h"]),
            }

            gargalos_status_validos = {
                k: v for k, v in gargalos_status.items()
                if v is not None and v > 0
            }

            if gargalos_status_validos:
                etapa_gargalo = max(gargalos_status_validos, key=gargalos_status_validos.get)
                tempo_gargalo = gargalos_status_validos[etapa_gargalo]
            else:
                etapa_gargalo = "Sem dado"
                tempo_gargalo = None

            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-label">Principal gargalo</div>
                    <div class="insight-value">{etapa_gargalo}</div>
                    <div class="insight-note">Tempo médio: {formatar_horas(tempo_gargalo)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown("#### Tempo médio por etapa do funil")

        etapas_tempo = pd.DataFrame(
            [
                {
                    "Etapa": "Aberto",
                    "Horas corridas médias": media_segura(df["Aberto h"]) or 0,
                    "Horas úteis médias": media_segura(df["Aberto útil h"]) or 0,
                },
                {
                    "Etapa": "Em análise",
                    "Horas corridas médias": media_segura(df["Em análise h"]) or 0,
                    "Horas úteis médias": media_segura(df["Em análise útil h"]) or 0,
                },
                {
                    "Etapa": "Aguardando retorno",
                    "Horas corridas médias": media_segura(df["Aguardando retorno h"]) or 0,
                    "Horas úteis médias": media_segura(df["Aguardando retorno útil h"]) or 0,
                },
                {
                    "Etapa": "Em execução",
                    "Horas corridas médias": media_segura(df["Em execução h"]) or 0,
                    "Horas úteis médias": media_segura(df["Em execução útil h"]) or 0,
                },
            ]
        )

        col_funil1, col_funil2 = st.columns([1.2, 1])

        with col_funil1:
            st.bar_chart(
                etapas_tempo.set_index("Etapa")[["Horas corridas médias", "Horas úteis médias"]],
                use_container_width=True,
            )

        with col_funil2:
            tabela_etapas = etapas_tempo.copy()
            tabela_etapas["Tempo corrido médio"] = tabela_etapas["Horas corridas médias"].apply(formatar_horas)
            tabela_etapas["Tempo útil médio"] = tabela_etapas["Horas úteis médias"].apply(formatar_horas)
            tabela_etapas = tabela_etapas[["Etapa", "Tempo corrido médio", "Tempo útil médio"]]

            st.dataframe(
                tabela_etapas,
                use_container_width=True,
                hide_index=True,
            )

            st.dataframe(
                tabela_etapas,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        st.markdown("#### Insights rápidos")

        insights = []

        if criticos > 0:
            insights.append(f"{criticos} ticket(s) em aberto há 3 dias ou mais precisam de atenção.")

        if sem_responsavel > 0:
            insights.append(f"{sem_responsavel} ticket(s) em aberto ainda estão sem responsável definido.")

        if urgentes_abertos > 0:
            insights.append(f"{urgentes_abertos} ticket(s) urgente(s) ainda não foram resolvidos.")

        if tempo_medio_primeiro_retorno and tempo_medio_primeiro_retorno > 24:
            insights.append(f"O tempo médio de primeiro retorno está acima de 1 dia: {formatar_horas(tempo_medio_primeiro_retorno)}.")

        if tempo_medio_resolucao and tempo_medio_resolucao > 72:
            insights.append(f"O tempo médio de resolução está acima de 3 dias: {formatar_horas(tempo_medio_resolucao)}.")

        if not df.empty:
            setor_top = df["Setor destino"].value_counts().idxmax()
            qtd_setor_top = df["Setor destino"].value_counts().max()
            insights.append(f"O setor mais acionado no filtro atual é {setor_top}, com {qtd_setor_top} ticket(s).")

        if not abertos_df.empty:
            responsavel_top = abertos_df["Responsável"].value_counts().idxmax()
            qtd_resp_top = abertos_df["Responsável"].value_counts().max()
            insights.append(f"O maior volume em aberto está com {responsavel_top}, com {qtd_resp_top} ticket(s).")

        if insights:
            for insight in insights:
                st.markdown(
                    f'<div class="alert-line">{html.escape(insight)}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="ok-line">Nenhum ponto crítico encontrado nos filtros selecionados.</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Tickets por status")
            st.bar_chart(df["Status"].value_counts())

        with col2:
            st.markdown("#### Tickets por prioridade")
            st.bar_chart(df["Prioridade"].value_counts())

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("#### Tickets por setor destino")
            st.bar_chart(df["Setor destino"].value_counts())

        with col4:
            st.markdown("#### Tickets por responsável")
            st.bar_chart(df["Responsável"].value_counts())

        st.divider()

        st.markdown("#### Evolução diária")

        df_datas = df.dropna(subset=["data_criacao"]).copy()

        if df_datas.empty:
            st.caption("Não há datas suficientes para montar a evolução diária.")
        else:
            criados_por_dia = df_datas.groupby("data_criacao").size().rename("Criados")
            resolvidos_por_dia = df_datas[df_datas["Status"] == "Resolvido"].groupby("data_criacao").size().rename("Resolvidos")

            evolucao = pd.concat([criados_por_dia, resolvidos_por_dia], axis=1).fillna(0)
            evolucao = evolucao.sort_index()

            st.line_chart(evolucao)

        st.divider()

        col5, col6 = st.columns(2)

        with col5:
            st.markdown("#### Solicitantes que mais abriram tickets")
            ranking_solicitantes = df["Solicitante"].value_counts().reset_index()
            ranking_solicitantes.columns = ["Solicitante", "Tickets"]
            st.dataframe(ranking_solicitantes.head(10), use_container_width=True, hide_index=True)

        with col6:
            st.markdown("#### CNPJs mais recorrentes")
            df_cnpj = df[df["CNPJ"].astype(str).str.strip() != ""]

            if df_cnpj.empty:
                st.caption("Nenhum CNPJ informado nos tickets filtrados.")
            else:
                ranking_cnpj = df_cnpj["CNPJ"].value_counts().reset_index()
                ranking_cnpj.columns = ["CNPJ", "Tickets"]
                st.dataframe(ranking_cnpj.head(10), use_container_width=True, hide_index=True)

        col7, col8 = st.columns(2)

        with col7:
            st.markdown("#### Tickets por setor de origem")
            st.bar_chart(df["Setor origem"].value_counts())

        with col8:
            st.markdown("#### Tickets com mais comentários")
            mais_comentados = df.sort_values("Comentários", ascending=False).head(10)

            render_tabela_clicavel(
                mais_comentados,
                ["Ticket", "Título", "Status", "Responsável", "Comentários"],
            )

        st.divider()

        st.markdown("#### Listas de ação")

        aba1, aba2, aba3, aba4, aba5 = st.tabs(
            [
                "Críticos",
                "Urgentes abertos",
                "Sem responsável",
                "Mais antigos",
                "Sem retorno",
            ]
        )

        with aba1:
            criticos_df = df[
                (df["Dias aberto"] >= 3)
                & (df["Status"] != "Resolvido")
            ].sort_values("Dias aberto", ascending=False)

            if criticos_df.empty:
                st.success("Nenhum ticket crítico.")
            else:
                render_tabela_clicavel(
                    criticos_df,
                    ["Ticket", "Título", "NF/Pedido", "CNPJ", "Status", "Prioridade", "Setor destino", "Responsável", "Dias aberto"],
                )

        with aba2:
            urgentes_df = df[
                (df["Prioridade"] == "Urgente")
                & (df["Status"] != "Resolvido")
            ].sort_values("Dias aberto", ascending=False)

            if urgentes_df.empty:
                st.success("Nenhum ticket urgente em aberto.")
            else:
                render_tabela_clicavel(
                    urgentes_df,
                    ["Ticket", "Título", "Status", "Setor destino", "Responsável", "Dias aberto"],
                )

        with aba3:
            sem_resp_df = df[
                (df["Responsável"] == "Não atribuído")
                & (df["Status"] != "Resolvido")
            ].sort_values("Dias aberto", ascending=False)

            if sem_resp_df.empty:
                st.success("Nenhum ticket sem responsável.")
            else:
                render_tabela_clicavel(
                    sem_resp_df,
                    ["Ticket", "Título", "Status", "Prioridade", "Setor destino", "Dias aberto"],
                )

        with aba4:
            antigos = df[df["Status"] != "Resolvido"].sort_values("Dias aberto", ascending=False).head(15)

            if antigos.empty:
                st.success("Nenhum ticket em aberto.")
            else:
                render_tabela_clicavel(
                    antigos,
                    ["Ticket", "Título", "NF/Pedido", "CNPJ", "Status", "Prioridade", "Setor destino", "Responsável", "Dias aberto"],
                )

        with aba5:
            sem_retorno_df = df[
                (df["Status"] != "Resolvido")
                & (df["Tempo primeiro retorno h"].isna())
            ].sort_values("Dias aberto", ascending=False)

            if sem_retorno_df.empty:
                st.success("Todos os tickets em aberto filtrados já têm retorno registrado.")
            else:
                render_tabela_clicavel(
                    sem_retorno_df,
                    ["Ticket", "Título", "Status", "Prioridade", "Setor destino", "Responsável", "Dias aberto"],
                )

        st.divider()

        st.markdown("#### Base analítica")

        base_exportacao = df.copy()
        base_exportacao["Tempo resolução"] = base_exportacao["Tempo resolução h"].apply(formatar_horas)
        base_exportacao["Tempo resolução útil"] = base_exportacao["Tempo resolução útil h"].apply(formatar_horas)
        base_exportacao["Tempo primeiro retorno"] = base_exportacao["Tempo primeiro retorno h"].apply(formatar_horas)
        base_exportacao["Tempo primeiro retorno útil"] = base_exportacao["Tempo primeiro retorno útil h"].apply(formatar_horas)
        base_exportacao["Tempo total"] = base_exportacao["Tempo total h"].apply(formatar_horas)
        base_exportacao["Tempo total útil"] = base_exportacao["Tempo total útil h"].apply(formatar_horas)

        buffer_excel = BytesIO()

        colunas_excel = [
            "ticket_numero",
            "Título",
            "NF/Pedido",
            "CNPJ",
            "Status",
            "Prioridade",
            "Setor origem",
            "Setor destino",
            "Solicitante",
            "Responsável",
            "Dias aberto",
            "Comentários",
            "Tem anexo",
            "Criado em",
            "Atualizado em",
            "Tempo primeiro retorno",
            "Tempo primeiro retorno útil",
            "Tempo resolução",
            "Tempo resolução útil",
            "Tempo total",
            "Tempo total útil",
        ]

        with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
            base_exportacao[colunas_excel].to_excel(
                writer,
                index=False,
                sheet_name="Base de tickets",
            )

            etapas_tempo.to_excel(
                writer,
                index=False,
                sheet_name="Tempo por etapa",
            )

        st.download_button(
            "Baixar Excel",
            data=buffer_excel.getvalue(),
            file_name=f"relatorio_tickets_{agora().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        render_tabela_clicavel(
            base_exportacao.sort_values("id", ascending=False).head(100),
            [
                "Ticket",
                "Título",
                "NF/Pedido",
                "CNPJ",
                "Status",
                "Prioridade",
                "Setor destino",
                "Responsável",
                "Dias aberto",
                "Tempo primeiro retorno",
                "Tempo primeiro retorno útil",
                "Tempo resolução",
                "Tempo resolução útil",
            ],
        )
