import html
from datetime import datetime, timedelta

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account


st.set_page_config(
    page_title="Papapa Tickets",
    layout="wide",
)


USUARIOS = {
    "joao.tadra": {"senha": "miojo123", "nome": "João Tadra", "setor": "Comercial"},
    "ana.christina": {"senha": "miojo123", "nome": "Ana Christina", "setor": "Comercial"},
    "pedro.born": {"senha": "miojo123", "nome": "Pedro Born", "setor": "Comercial"},
    "joao.paulo": {"senha": "miojo123", "nome": "João Paulo", "setor": "Comercial"},
    "rodrigo.sarlo": {"senha": "miojo123", "nome": "Rodrigo Sarlo", "setor": "Comercial"},
    "thiago.cabral": {"senha": "miojo123", "nome": "Thiago Cabral", "setor": "Pós-vendas"},
    "bernardo.dallegrave": {"senha": "miojo123", "nome": "Bernardo Dallegrave", "setor": "Pós-vendas"},
    "ronaldo.leidens": {"senha": "miojo123", "nome": "Ronaldo Leidens", "setor": "Logística"},
    "luan.dornelis": {"senha": "miojo123", "nome": "Luan Dornelis", "setor": "Financeiro"},
    "maria.julia": {"senha": "miojo123", "nome": "Maria Julia", "setor": "RH"},
    "victoria.gobbo": {"senha": "miojo123", "nome": "Victoria Gobbo", "setor": "Marketing"},
}

STATUS = ["Aberto", "Em análise", "Aguardando retorno", "Em execução", "Resolvido"]
SETORES = ["Comercial", "Pós-vendas", "Logística", "Financeiro", "Qualidade", "RH", "Marketing"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Urgente"]

COOKIE_LOGIN = "papapa_tickets_login"
COLLECTION_TICKETS = "tickets_internos"


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
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #ffffff;
}

[data-testid="stSidebar"] button {
    background-color: #ffffff !important;
    color: #082b57 !important;
    border: 1px solid #ffffff !important;
    font-weight: 700 !important;
}

[data-testid="stSidebar"] button p {
    color: #082b57 !important;
}

.ticket-card {
    background: #ffffff;
    border: 1px solid #e4e8f0;
    border-left: 5px solid #1f6feb;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    min-height: 136px;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.07);
}

.ticket-title {
    font-weight: 800;
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
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 999px;
    margin-bottom: 8px;
    color: white;
}

.priority-urgente {
    border-left-color: #dc2626;
}

.priority-alta {
    border-left-color: #f97316;
}

.priority-media {
    border-left-color: #2563eb;
}

.priority-baixa {
    border-left-color: #16a34a;
}

.pill-urgente {
    background: #dc2626;
}

.pill-alta {
    background: #f97316;
}

.pill-media {
    background: #2563eb;
}

.pill-baixa {
    background: #16a34a;
}

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
    font-weight: 800;
    color: #0f3a73;
    margin-bottom: 3px;
}

.comment-text {
    color: #1f2937;
    font-size: 14px;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def conectar_firestore():
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        return firestore.Client(credentials=creds)
    except Exception as erro:
        st.error("Não consegui conectar ao Firestore. Confira os secrets do Streamlit Cloud.")
        st.exception(erro)
        st.stop()


db = conectar_firestore()
cookie_manager = stx.CookieManager()


def prioridade_classe(prioridade):
    mapa = {
        "Baixa": "baixa",
        "Média": "media",
        "Alta": "alta",
        "Urgente": "urgente",
    }
    return mapa.get(prioridade, "media")


def agora_formatado():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def lista_responsaveis():
    return ["Não atribuído"] + [dados["nome"] for dados in USUARIOS.values()]


def normalizar_ticket(ticket):
    ticket.setdefault("id", 0)
    ticket.setdefault("titulo", "")
    ticket.setdefault("descricao", "")
    ticket.setdefault("setor_origem", "")
    ticket.setdefault("setor_destino", "")
    ticket.setdefault("solicitante", "")
    ticket.setdefault("responsavel", "Não atribuído")
    ticket.setdefault("prioridade", "Média")
    ticket.setdefault("status", "Aberto")
    ticket.setdefault("comentarios", [])
    ticket.setdefault("criado_em", "")
    return ticket


def carregar_tickets_nuvem():
    try:
        docs = (
            db.collection(COLLECTION_TICKETS)
            .order_by("id", direction=firestore.Query.DESCENDING)
            .stream()
        )

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


def restaurar_login_por_cookie():
    if st.session_state.logado:
        return

    login_salvo = cookie_manager.get(COOKIE_LOGIN)

    if login_salvo and login_salvo in USUARIOS:
        dados = USUARIOS[login_salvo]
        st.session_state.logado = True
        st.session_state.usuario = {
            "login": login_salvo,
            "nome": dados["nome"],
            "setor": dados["setor"],
        }


def login(usuario, senha):
    usuario = usuario.strip().lower()
    dados = USUARIOS.get(usuario)

    if dados and dados["senha"] == senha:
        st.session_state.logado = True
        st.session_state.usuario = {
            "login": usuario,
            "nome": dados["nome"],
            "setor": dados["setor"],
        }
        cookie_manager.set(
            COOKIE_LOGIN,
            usuario,
            expires_at=datetime.now() + timedelta(days=1),
        )
        st.rerun()

    st.error("Usuário ou senha inválidos.")


def sair():
    cookie_manager.delete(COOKIE_LOGIN)
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.ticket_aberto = None
    st.rerun()


def criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel):
    usuario = st.session_state.usuario

    ticket = {
        "id": gerar_id_ticket(),
        "titulo": titulo,
        "descricao": descricao,
        "setor_origem": usuario["setor"],
        "setor_destino": setor_destino,
        "solicitante": usuario["nome"],
        "responsavel": responsavel,
        "prioridade": prioridade,
        "status": "Aberto",
        "comentarios": [],
        "criado_em": agora_formatado(),
    }

    salvar_ticket_nuvem(ticket)
    st.session_state.tickets = carregar_tickets_nuvem()


def tickets_visiveis():
    usuario = st.session_state.usuario

    return [
        ticket
        for ticket in st.session_state.tickets
        if ticket["solicitante"] == usuario["nome"]
        or ticket["responsavel"] == usuario["nome"]
        or ticket["setor_destino"] == usuario["setor"]
        or ticket["setor_origem"] == usuario["setor"]
    ]


def aplicar_filtros(tickets, prefixo):
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 2])

    with col1:
        filtro_setor = st.selectbox("Setor destino", ["Todos"] + SETORES, key=f"{prefixo}_setor")

    with col2:
        filtro_prioridade = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES, key=f"{prefixo}_prioridade")

    with col3:
        filtro_responsavel = st.selectbox("Responsável", ["Todos"] + lista_responsaveis(), key=f"{prefixo}_responsavel")

    with col4:
        busca = st.text_input("Buscar por título ou descrição", key=f"{prefixo}_busca")

    if filtro_setor != "Todos":
        tickets = [t for t in tickets if t["setor_destino"] == filtro_setor]

    if filtro_prioridade != "Todas":
        tickets = [t for t in tickets if t["prioridade"] == filtro_prioridade]

    if filtro_responsavel != "Todos":
        tickets = [t for t in tickets if t["responsavel"] == filtro_responsavel]

    if busca:
        tickets = [
            t
            for t in tickets
            if busca.lower() in t["titulo"].lower()
            or busca.lower() in t["descricao"].lower()
        ]

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


def render_card(ticket):
    prioridade = prioridade_classe(ticket["prioridade"])

    titulo = html.escape(ticket["titulo"])
    origem = html.escape(ticket["setor_origem"])
    destino = html.escape(ticket["setor_destino"])
    responsavel = html.escape(ticket["responsavel"])
    solicitante = html.escape(ticket["solicitante"])
    criado_em = html.escape(ticket.get("criado_em", ""))

    st.markdown(
        f"""
        <div class="ticket-card priority-{prioridade}">
            <div class="ticket-pill pill-{prioridade}">{ticket["prioridade"]}</div>
            <div class="ticket-title">#{ticket["id"]} - {titulo}</div>
            <div class="ticket-meta">{origem} para {destino}</div>
            <div class="ticket-meta">Responsável: {responsavel}</div>
            <div class="ticket-meta">Solicitante: {solicitante}</div>
            <div class="ticket-meta">Criado em: {criado_em}</div>
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


def painel_ticket():
    ticket = next(
        (t for t in st.session_state.tickets if t["id"] == st.session_state.ticket_aberto),
        None,
    )

    if not ticket:
        return

    st.divider()

    topo1, topo2 = st.columns([4, 1])
    with topo1:
        st.subheader(f"Ticket #{ticket['id']} - {ticket['titulo']}")
        st.caption(f"{ticket['setor_origem']} para {ticket['setor_destino']} | Criado em {ticket.get('criado_em', '')}")

    with topo2:
        if st.button("Fechar painel", use_container_width=True):
            st.session_state.ticket_aberto = None
            st.rerun()

    col_tratativa, col_comentarios = st.columns([1.15, 1])

    with col_tratativa:
        st.markdown("#### Tratativa")
        st.write(ticket["descricao"])

        novo_status = st.selectbox(
            "Status",
            STATUS,
            index=STATUS.index(ticket["status"]) if ticket["status"] in STATUS else 0,
            key=f"status_{ticket['id']}",
        )

        novo_responsavel = st.selectbox(
            "Responsável",
            lista_responsaveis(),
            index=lista_responsaveis().index(ticket["responsavel"])
            if ticket["responsavel"] in lista_responsaveis()
            else 0,
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
        st.write(f"**Destino:** {ticket['setor_destino']}")

        if st.button("Salvar alterações", type="primary", use_container_width=True):
            ticket["status"] = novo_status
            ticket["responsavel"] = novo_responsavel
            ticket["prioridade"] = nova_prioridade
            atualizar_ticket_nuvem(ticket)
            st.session_state.tickets = carregar_tickets_nuvem()
            st.success("Ticket atualizado.")
            st.rerun()

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

        novo_comentario = st.text_area(
            "Novo comentário",
            key=f"comentario_{ticket['id']}",
            height=130,
        )

        if st.button("Enviar comentário", key=f"enviar_comentario_{ticket['id']}", use_container_width=True):
            if novo_comentario.strip():
                ticket["comentarios"].append(
                    {
                        "autor": st.session_state.usuario["nome"],
                        "texto": novo_comentario.strip(),
                        "criado_em": agora_formatado(),
                    }
                )
                atualizar_ticket_nuvem(ticket)
                st.session_state.tickets = carregar_tickets_nuvem()
                st.rerun()


restaurar_login_por_cookie()

if not st.session_state.logado:
    left, center, right = st.columns([1, 1.15, 1])

    with center:
        mostrar_logo()
        st.title("Central de Tickets")
        st.caption("Atendimento interno Papapa")

        with st.form("login"):
            usuario_login = st.text_input("Usuário")
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

    st.radio(
        "Menu",
        ["Kanban", "Novo ticket", "Meus tickets", "Dashboard"],
        key="pagina_atual",
    )

    st.divider()

    if st.button("Sair", use_container_width=True):
        sair()


pagina = st.session_state.pagina_atual

st.title("Central de Tickets")
st.caption("Gestão interna de solicitações entre áreas")

tickets = tickets_visiveis()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Tickets visíveis", len(tickets))
m2.metric("Abertos", len([t for t in tickets if t["status"] == "Aberto"]))
m3.metric("Em andamento", len([t for t in tickets if t["status"] in ["Em análise", "Em execução"]]))
m4.metric("Resolvidos", len([t for t in tickets if t["status"] == "Resolvido"]))

st.divider()

if pagina == "Novo ticket":
    st.subheader("Abrir novo ticket")

    with st.form("novo_ticket"):
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição", height=160)

        col1, col2, col3 = st.columns(3)

        with col1:
            setor_destino = st.selectbox("Setor destino", SETORES)

        with col2:
            prioridade = st.selectbox("Prioridade", PRIORIDADES, index=1)

        with col3:
            responsavel = st.selectbox("Responsável", lista_responsaveis())

        enviar = st.form_submit_button("Abrir ticket", type="primary")

        if enviar:
            if not titulo.strip() or not descricao.strip():
                st.error("Preencha título e descrição.")
            else:
                criar_ticket(titulo.strip(), descricao.strip(), setor_destino, prioridade, responsavel)
                st.success("Ticket criado com sucesso.")

elif pagina == "Kanban":
    st.subheader("Kanban executivo")

    tickets_filtrados = aplicar_filtros(tickets, "kanban")
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

    meus_tickets = aplicar_filtros(tickets, "meus_tickets")

    if not meus_tickets:
        st.info("Nenhum ticket encontrado.")
    else:
        for ticket in meus_tickets:
            with st.expander(f"#{ticket['id']} - {ticket['titulo']} | {ticket['status']}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(ticket["descricao"])
                    st.write(f"**Status:** {ticket['status']}")
                    st.write(f"**Prioridade:** {ticket['prioridade']}")
                    st.write(f"**Solicitante:** {ticket['solicitante']}")
                    st.write(f"**Responsável:** {ticket['responsavel']}")
                    st.write(f"**Setor destino:** {ticket['setor_destino']}")

                with col2:
                    st.button(
                        "Abrir / comentar",
                        key=f"ir_kanban_{ticket['id']}",
                        on_click=abrir_ticket_no_kanban,
                        args=(ticket["id"],),
                        use_container_width=True,
                    )

elif pagina == "Dashboard":
    st.subheader("Dashboard")

    if not tickets:
        st.info("Ainda não há tickets para exibir.")
    else:
        df = pd.DataFrame(tickets)

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
