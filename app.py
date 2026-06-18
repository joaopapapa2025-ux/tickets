import html
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote

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
    "contasareceber@papapa.com.br": {"senha": "miojo123", "usuario": "luan.dornelis", "nome": "Luan Dornelis", "setor": "Financeiro", "email": "contasareceber@papapa.com.br", "telefone": "5541996071551"},
    "rh@papapa.com.br": {"senha": "miojo123", "usuario": "maria.julia", "nome": "Maria Julia", "setor": "RH", "email": "rh@papapa.com.br", "telefone": "5541984402434"},
    "crm@papapa.com.br": {"senha": "miojo123", "usuario": "victoria.gobbo", "nome": "Victoria Gobbo", "setor": "Marketing", "email": "crm@papapa.com.br", "telefone": "5541992761230"},
}

STATUS = ["Aberto", "Em análise", "Aguardando retorno", "Em execução", "Resolvido"]
SETORES = ["Comercial", "Pós-vendas", "Logística", "Financeiro", "Qualidade", "RH", "Marketing"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Urgente"]

ADMIN_DELETE_EMAILS = ["comercial1@papapa.com.br"]
COLLECTION_TICKETS = "tickets_internos"
COLLECTION_SESSIONS = "tickets_sessoes"


st.markdown(
    """
<style>
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 100%; }
[data-testid="stSidebar"] { background-color: #082b57; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #ffffff; }
[data-testid="stSidebar"] button { background-color: #ffffff !important; color: #082b57 !important; border: 1px solid #ffffff !important; font-weight: 800 !important; }
[data-testid="stSidebar"] button p { color: #082b57 !important; }

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
.ticket-title { font-weight: 850; color: #102a43; margin-bottom: 8px; line-height: 1.25; }
.ticket-meta { font-size: 12px; color: #56657a; margin-bottom: 2px; }
.ticket-pill { display: inline-block; font-size: 11px; font-weight: 800; padding: 3px 8px; border-radius: 999px; margin-right: 4px; margin-bottom: 8px; color: white; }
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
.kanban-empty { border: 1px dashed #d7dde8; background: #f8fafc; color: #8492a6; border-radius: 8px; padding: 18px 10px; text-align: center; font-size: 12px; }
.comment-box { background: #eef5ff; border: 1px solid #dbeafe; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.comment-author { font-weight: 850; color: #0f3a73; margin-bottom: 3px; }
.comment-text { color: #1f2937; font-size: 14px; }
.history-box { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 9px 11px; margin-bottom: 7px; font-size: 13px; }
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
    return datetime.now()


def agora_formatado():
    return agora().strftime("%d/%m/%Y %H:%M")


def token_diario():
    return f"access_{agora().strftime('%Y%m%d')}"


def formatar_numero_ticket(ticket_id):
    return f"#{int(ticket_id):05d}"


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


def usuarios_do_setor(setor):
    return [dados["nome"] for dados in USUARIOS.values() if dados["setor"] == setor]


def usuario_por_nome(nome):
    for email, dados in USUARIOS.items():
        if dados["nome"] == nome:
            item = dados.copy()
            item["login"] = email
            return item
    return None


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
    return (
        f"Olá! Houve uma atualização na Central de Tickets Papapa.\n\n"
        f"Tipo: {tipo}\n"
        f"Ticket: {numero} - {titulo}\n"
        f"Status: {ticket.get('status', '')}\n"
        f"Prioridade: {ticket.get('prioridade', '')}\n"
        f"Solicitante: {ticket.get('solicitante', '')}\n"
        f"Responsável: {ticket.get('responsavel', '')}\n"
        f"Origem: {ticket.get('setor_origem', '')}\n"
        f"Destino: {ticket.get('setor_destino', '')}\n\n"
        f"Acesse a Central de Tickets para tratar ou acompanhar o caso."
    )


def preparar_notificacao(ticket, tipo, destinatario_nome=None):
    nome = destinatario_nome or ticket.get("responsavel", "")
    telefone = telefone_whatsapp_por_nome(nome)
    if not telefone:
        return
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
if "sid" not in st.session_state:
    st.session_state.sid = st.query_params.get("sid", "")
if "notificacao_whatsapp" not in st.session_state:
    st.session_state.notificacao_whatsapp = None


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


def criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel, origem_id=None):
    usuario = st.session_state.usuario
    ticket = {
        "id": gerar_id_ticket(),
        "titulo": titulo,
        "descricao": descricao,
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
    registrar_historico(ticket, "Ticket criado", f"Ticket aberto para {setor_destino}.")
    salvar_ticket_nuvem(ticket)
    st.session_state.tickets = carregar_tickets_nuvem()
    preparar_notificacao(ticket, "Novo ticket atribuído")
    return ticket


def tickets_visiveis():
    usuario = st.session_state.usuario
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
    col1, col2, col3, col4, col5 = st.columns([1.1, 1.1, 1.2, 1.1, 1.7])
    with col1:
        filtro_numero = st.text_input("Número", placeholder="00001", key=f"{prefixo}_numero")
    with col2:
        filtro_setor = st.selectbox("Setor destino", ["Todos"] + SETORES, key=f"{prefixo}_setor")
    with col3:
        filtro_prioridade = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES, key=f"{prefixo}_prioridade")
    with col4:
        filtro_mes = "Mês atual"
        if incluir_filtro_mes:
            filtro_mes = st.selectbox("Resolvidos", meses_disponiveis(tickets), key=f"{prefixo}_mes_resolvido")
    with col5:
        busca = st.text_input("Buscar", placeholder="Título ou descrição", key=f"{prefixo}_busca")

    if filtro_numero:
        numero_limpo = filtro_numero.replace("#", "").strip()
        if numero_limpo.isdigit():
            tickets = [t for t in tickets if int(t["id"]) == int(numero_limpo)]
    if filtro_setor != "Todos":
        tickets = [t for t in tickets if t["setor_destino"] == filtro_setor]
    if filtro_prioridade != "Todas":
        tickets = [t for t in tickets if t["prioridade"] == filtro_prioridade]
    if incluir_filtro_mes:
        tickets = [t for t in tickets if ticket_no_mes(t, filtro_mes)]
    if busca:
        tickets = [t for t in tickets if busca.lower() in t["titulo"].lower() or busca.lower() in t["descricao"].lower()]
    return tickets


def abrir_ticket(ticket_id):
    st.session_state.ticket_aberto = ticket_id
    st.rerun()


def abrir_ticket_no_kanban(ticket_id):
    st.session_state.ticket_aberto = ticket_id
    st.session_state.pagina_atual = "Kanban"
    st.rerun()


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

    origem_txt = ""
    if ticket.get("ticket_origem_id"):
        origem_txt = f"<div class='ticket-meta'>Originado do {formatar_numero_ticket(ticket['ticket_origem_id'])}</div>"

    st.markdown(
        f"""
        <div class="ticket-card priority-{prioridade}">
            <span class="ticket-pill pill-{prioridade}">{ticket["prioridade"]}</span>
            <span class="ticket-pill {classe_idade}">{texto_idade_ticket(dias)}</span>
            <div class="ticket-title">{formatar_numero_ticket(ticket["id"])} - {titulo}</div>
            <div class="ticket-meta">{origem} para {destino}</div>
            <div class="ticket-meta">Responsável: {responsavel}</div>
            <div class="ticket-meta">Solicitante: {solicitante}</div>
            <div class="ticket-meta">Criado em: {criado_em}</div>
            {origem_txt}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button("Abrir", key=f"abrir_{ticket['id']}", on_click=abrir_ticket, args=(ticket["id"],), use_container_width=True)


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

        status_anterior = ticket["status"]
        responsavel_anterior = ticket["responsavel"]
        prioridade_anterior = ticket["prioridade"]

        novo_status = st.selectbox("Status", STATUS, index=STATUS.index(ticket["status"]) if ticket["status"] in STATUS else 0, key=f"status_{ticket['id']}")
        responsaveis_destino = lista_responsaveis(ticket["setor_destino"])
        novo_responsavel = st.selectbox(
            "Responsável",
            responsaveis_destino,
            index=responsaveis_destino.index(ticket["responsavel"]) if ticket["responsavel"] in responsaveis_destino else 0,
            key=f"responsavel_{ticket['id']}",
        )
        nova_prioridade = st.selectbox("Prioridade", PRIORIDADES, index=PRIORIDADES.index(ticket["prioridade"]) if ticket["prioridade"] in PRIORIDADES else 1, key=f"prioridade_{ticket['id']}")

        st.write(f"**Solicitante:** {ticket['solicitante']}")
        st.write(f"**Origem:** {ticket['setor_origem']}")
        st.write(f"**Destino:** {ticket['setor_destino']}")

        if st.button("Salvar alterações", type="primary", use_container_width=True):
            mudancas = []
            if status_anterior != novo_status:
                mudancas.append(f"status de {status_anterior} para {novo_status}")
            if responsavel_anterior != novo_responsavel:
                mudancas.append(f"responsável de {responsavel_anterior} para {novo_responsavel}")
            if prioridade_anterior != nova_prioridade:
                mudancas.append(f"prioridade de {prioridade_anterior} para {nova_prioridade}")

            ticket["status"] = novo_status
            ticket["responsavel"] = novo_responsavel
            ticket["prioridade"] = nova_prioridade
            ticket["atualizado_em"] = agora_formatado()

            if mudancas:
                registrar_historico(ticket, "Ticket atualizado", "; ".join(mudancas))
                preparar_notificacao(ticket, "Atualização de ticket")

            atualizar_ticket_nuvem(ticket)
            st.session_state.tickets = carregar_tickets_nuvem()
            st.success("Ticket atualizado.")
            st.rerun()

        st.markdown("#### Resolver e encaminhar")
        with st.expander("Encaminhar para outro setor após resolver"):
            novo_setor = st.selectbox("Novo setor destino", SETORES, key=f"enc_setor_{ticket['id']}")
            novo_resp = st.selectbox("Novo responsável", lista_responsaveis(novo_setor), key=f"enc_resp_{ticket['id']}")
            novo_titulo = st.text_input("Título do novo ticket", value=f"Continuação de {formatar_numero_ticket(ticket['id'])} - {ticket['titulo']}", key=f"enc_titulo_{ticket['id']}")
            nova_desc = st.text_area("Descrição do encaminhamento", value=f"Ticket originado do {formatar_numero_ticket(ticket['id'])}.\n\nContexto anterior:\n{ticket['descricao']}", height=120, key=f"enc_desc_{ticket['id']}")

            if st.button("Resolver atual e criar encaminhamento", use_container_width=True):
                ticket["status"] = "Resolvido"
                ticket["atualizado_em"] = agora_formatado()
                registrar_historico(ticket, "Ticket resolvido e encaminhado", f"Novo encaminhamento para {novo_setor}.")
                atualizar_ticket_nuvem(ticket)
                novo_ticket = criar_ticket(novo_titulo.strip(), nova_desc.strip(), novo_setor, ticket["prioridade"], novo_resp, origem_id=ticket["id"])
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

        for comentario in ticket["comentarios"]:
            autor = html.escape(comentario.get("autor", ""))
            texto = html.escape(comentario.get("texto", ""))
            criado_em = html.escape(comentario.get("criado_em", ""))
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

        novo_comentario = st.text_area("Novo comentário", key=f"comentario_{ticket['id']}", height=130)
        if st.button("Enviar comentário", key=f"enviar_comentario_{ticket['id']}", use_container_width=True):
            if novo_comentario.strip():
                ticket["comentarios"].append({"autor": st.session_state.usuario["nome"], "texto": novo_comentario.strip(), "criado_em": agora_formatado()})
                ticket["atualizado_em"] = agora_formatado()
                registrar_historico(ticket, "Comentário adicionado", novo_comentario.strip()[:120])
                atualizar_ticket_nuvem(ticket)
                preparar_notificacao(ticket, "Novo comentário")
                st.session_state.tickets = carregar_tickets_nuvem()
                st.rerun()

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
            criar_ticket(titulo.strip(), descricao.strip(), setor_destino, prioridade, responsavel)
            st.success("Ticket criado com sucesso.")
            st.session_state.pagina_atual = "Kanban"
            st.rerun()

elif pagina == "Kanban":
    st.subheader("Kanban executivo")
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
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Prioridade:** {ticket['prioridade']}")
                    st.write(f"**Solicitante:** {ticket['solicitante']}")
                    st.write(f"**Setor destino:** {ticket['setor_destino']}")
                    st.write(f"**Criado em:** {ticket.get('criado_em', '')}")
                with col2:
                    st.button("Tratar ticket", key=f"ir_kanban_atribuidos_{ticket['id']}", on_click=abrir_ticket_no_kanban, args=(ticket["id"],), use_container_width=True)

elif pagina == "Dashboard":
    st.subheader("Dashboard")
    tickets_dashboard = [t for t in tickets if ticket_no_mes(t, "Mês atual")]

    if not tickets_dashboard:
        st.info("Ainda não há tickets para exibir.")
    else:
        df = pd.DataFrame(tickets_dashboard)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Tickets por status")
            st.bar_chart(df["status"].value_counts())
        with col2:
            st.markdown("#### Tickets por setor destino")
            st.bar_chart(df["setor_destino"].value_counts())

        col3, col4 = st.columns(2)
        with col3:
            st.markdown("#### Tickets por prioridade")
            st.bar_chart(df["prioridade"].value_counts())
        with col4:
            st.markdown("#### Tickets por responsável")
            st.bar_chart(df["responsavel"].value_counts())

        st.markdown("#### Tickets mais antigos em aberto")
        antigos = sorted([t for t in tickets_dashboard if t["status"] != "Resolvido"], key=lambda item: idade_ticket(item), reverse=True)[:10]

        if not antigos:
            st.caption("Nenhum ticket em aberto.")
        else:
            tabela = pd.DataFrame(
                [
                    {
                        "Ticket": formatar_numero_ticket(t["id"]),
                        "Título": t["titulo"],
                        "Status": t["status"],
                        "Prioridade": t["prioridade"],
                        "Responsável": t["responsavel"],
                        "Dias aberto": idade_ticket(t),
                    }
                    for t in antigos
                ]
            )
            st.dataframe(tabela, use_container_width=True, hide_index=True)
