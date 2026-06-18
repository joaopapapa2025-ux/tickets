import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from google.cloud import firestore
from google.oauth2 import service_account
import extra_streamlit_components as stx

st.set_page_config(
    page_title="Papapá Tickets",
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

@st.cache_resource
def conectar_firestore():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    return firestore.Client(credentials=creds)


db = conectar_firestore()


def carregar_tickets_nuvem():
    docs = (
        db.collection("tickets_internos")
        .order_by("id", direction=firestore.Query.DESCENDING)
        .stream()
    )

    tickets = []
    for doc in docs:
        item = doc.to_dict()
        item["doc_id"] = doc.id
        tickets.append(item)

    return tickets


def salvar_ticket_nuvem(ticket):
    db.collection("tickets_internos").add(ticket)


def atualizar_ticket_nuvem(ticket):
    doc_id = ticket.get("doc_id")
    if not doc_id:
        return

    dados = ticket.copy()
    dados.pop("doc_id", None)

    db.collection("tickets_internos").document(doc_id).set(dados)


def gerar_id_ticket():
    docs = db.collection("tickets_internos").stream()
    ids = [doc.to_dict().get("id", 0) for doc in docs]
    return max(ids, default=0) + 1

st.markdown("""
<style>
.main {
    background-color: #f6f8fb;
}
.block-container {
    padding-top: 1.5rem;
}
[data-testid="stSidebar"] {
    background-color: #082b57;
}
[data-testid="stSidebar"] * {
    color: white;
}
.ticket-card {
    background: white;
    border: 1px solid #e4e8f0;
    border-left: 5px solid #1f6feb;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}
.ticket-title {
    font-weight: 700;
    color: #102a43;
    margin-bottom: 6px;
}
.ticket-meta {
    font-size: 12px;
    color: #62748e;
}
.priority-Urgente {
    border-left-color: #dc2626;
}
.priority-Alta {
    border-left-color: #f97316;
}
.priority-Média {
    border-left-color: #2563eb;
}
.priority-Baixa {
    border-left-color: #16a34a;
}
.kanban-column {
    background: #eef3f8;
    border-radius: 8px;
    padding: 10px;
    min-height: 520px;
}
</style>
""", unsafe_allow_html=True)


if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "tickets" not in st.session_state:
    st.session_state.tickets = carregar_tickets_nuvem()

if "ticket_aberto" not in st.session_state:
    st.session_state.ticket_aberto = None


def lista_responsaveis():
    return ["Não atribuído"] + [dados["nome"] for dados in USUARIOS.values()]


def login(usuario, senha):
    dados = USUARIOS.get(usuario)

    if dados and dados["senha"] == senha:
        st.session_state.logado = True
        st.session_state.usuario = {
            "login": usuario,
            "nome": dados["nome"],
            "setor": dados["setor"],
        }
        st.rerun()

    st.error("Usuário ou senha inválidos.")


def sair():
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.ticket_aberto = None
    st.rerun()


def criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel):
    usuario = st.session_state.usuario

    ticket = {
        "id": len(st.session_state.tickets) + 1,
        "titulo": titulo,
        "descricao": descricao,
        "setor_origem": usuario["setor"],
        "setor_destino": setor_destino,
        "solicitante": usuario["nome"],
        "responsavel": responsavel,
        "prioridade": prioridade,
        "status": "Aberto",
        "comentarios": [],
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


def aplicar_filtros(tickets):
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 2])

    with col1:
        filtro_setor = st.selectbox("Setor destino", ["Todos"] + SETORES)

    with col2:
        filtro_prioridade = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES)

    with col3:
        filtro_responsavel = st.selectbox("Responsável", ["Todos"] + lista_responsaveis())

    with col4:
        busca = st.text_input("Buscar por título ou descrição")

    if filtro_setor != "Todos":
        tickets = [t for t in tickets if t["setor_destino"] == filtro_setor]

    if filtro_prioridade != "Todas":
        tickets = [t for t in tickets if t["prioridade"] == filtro_prioridade]

    if filtro_responsavel != "Todos":
        tickets = [t for t in tickets if t["responsavel"] == filtro_responsavel]

    if busca:
        tickets = [
            t for t in tickets
            if busca.lower() in t["titulo"].lower()
            or busca.lower() in t["descricao"].lower()
        ]

    return tickets


def abrir_ticket(ticket_id):
    st.session_state.ticket_aberto = ticket_id
    st.rerun()


def render_card(ticket):
    st.markdown(
        f"""
        <div class="ticket-card priority-{ticket['prioridade']}">
            <div class="ticket-title">#{ticket['id']} - {ticket['titulo']}</div>
            <div class="ticket-meta">{ticket['setor_origem']} para {ticket['setor_destino']}</div>
            <div class="ticket-meta">Prioridade: {ticket['prioridade']}</div>
            <div class="ticket-meta">Responsável: {ticket['responsavel']}</div>
            <div class="ticket-meta">Solicitante: {ticket['solicitante']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.button("Abrir ticket", key=f"abrir_{ticket['id']}", on_click=abrir_ticket, args=(ticket["id"],))


def painel_ticket():
    ticket = next(
        (t for t in st.session_state.tickets if t["id"] == st.session_state.ticket_aberto),
        None,
    )

    if not ticket:
        return

    st.divider()
    st.subheader(f"Ticket #{ticket['id']} - {ticket['titulo']}")

    col1, col2 = st.columns([1.3, 1])

    with col1:
        st.write(ticket["descricao"])

        st.markdown("#### Comentários")

        if not ticket["comentarios"]:
            st.caption("Nenhum comentário ainda.")

        for comentario in ticket["comentarios"]:
            st.info(f"{comentario['autor']}: {comentario['texto']}")

        novo_comentario = st.text_area("Novo comentário", key=f"comentario_{ticket['id']}")

        if st.button("Enviar comentário", key=f"enviar_comentario_{ticket['id']}"):
            if novo_comentario:
                ticket["comentarios"].append(
                    {
                        "autor": st.session_state.usuario["nome"],
                        "texto": novo_comentario,
                    }
                )
                st.rerun()

    with col2:
        st.markdown("#### Tratativa")

        novo_status = st.selectbox(
            "Status",
            STATUS,
            index=STATUS.index(ticket["status"]),
            key=f"status_{ticket['id']}",
        )

        novo_responsavel = st.selectbox(
            "Responsável",
            lista_responsaveis(),
            index=lista_responsaveis().index(ticket["responsavel"]),
            key=f"responsavel_{ticket['id']}",
        )

        nova_prioridade = st.selectbox(
            "Prioridade",
            PRIORIDADES,
            index=PRIORIDADES.index(ticket["prioridade"]),
            key=f"prioridade_{ticket['id']}",
        )

        st.write(f"**Solicitante:** {ticket['solicitante']}")
        st.write(f"**Origem:** {ticket['setor_origem']}")
        st.write(f"**Destino:** {ticket['setor_destino']}")

        if st.button("Salvar alterações", type="primary"):
            ticket["status"] = novo_status
            ticket["responsavel"] = novo_responsavel
            ticket["prioridade"] = nova_prioridade
            st.success("Ticket atualizado.")
            st.rerun()

        if st.button("Fechar painel"):
            st.session_state.ticket_aberto = None
            st.rerun()


if not st.session_state.logado:
    left, center, right = st.columns([1, 1.2, 1])

    with center:
        st.image("Papapa-azul.png", use_container_width=True)
        st.title("Central de Tickets")
        st.caption("Atendimento interno Papapá")

        with st.form("login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary")

            if entrar:
                login(usuario, senha)

    st.stop()


usuario = st.session_state.usuario

with st.sidebar:
    st.image("Papapa-azul.png", use_container_width=True)
    st.write(f"**{usuario['nome']}**")
    st.caption(usuario["setor"])

    pagina = st.radio(
        "Menu",
        ["Kanban", "Novo ticket", "Meus tickets", "Dashboard"],
    )

    st.divider()

    if st.button("Sair"):
        sair()


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
        descricao = st.text_area("Descrição")
        col1, col2, col3 = st.columns(3)

        with col1:
            setor_destino = st.selectbox("Setor destino", SETORES)

        with col2:
            prioridade = st.selectbox("Prioridade", PRIORIDADES, index=1)

        with col3:
            responsavel = st.selectbox("Responsável", lista_responsaveis())

        enviar = st.form_submit_button("Abrir ticket", type="primary")

        if enviar:
            if not titulo or not descricao:
                st.error("Preencha título e descrição.")
            else:
                criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel)
                st.success("Ticket criado com sucesso.")

elif pagina == "Kanban":
    st.subheader("Kanban executivo")

    tickets_filtrados = aplicar_filtros(tickets)
    colunas = st.columns(len(STATUS))

    for indice, status in enumerate(STATUS):
        with colunas[indice]:
            st.markdown(f"### {status}")
            st.markdown('<div class="kanban-column">', unsafe_allow_html=True)

            tickets_status = [t for t in tickets_filtrados if t["status"] == status]

            if not tickets_status:
                st.caption("Nenhum ticket")

            for ticket in tickets_status:
                render_card(ticket)

            st.markdown("</div>", unsafe_allow_html=True)

    painel_ticket()

elif pagina == "Meus tickets":
    st.subheader("Meus tickets")

    meus_tickets = aplicar_filtros(tickets)

    if not meus_tickets:
        st.info("Nenhum ticket encontrado.")
    else:
        for ticket in meus_tickets:
            with st.expander(f"#{ticket['id']} - {ticket['titulo']}"):
                st.write(ticket["descricao"])
                st.write(f"**Status:** {ticket['status']}")
                st.write(f"**Prioridade:** {ticket['prioridade']}")
                st.write(f"**Solicitante:** {ticket['solicitante']}")
                st.write(f"**Responsável:** {ticket['responsavel']}")
                st.write(f"**Setor destino:** {ticket['setor_destino']}")

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
