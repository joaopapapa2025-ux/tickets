import streamlit as st

st.set_page_config(
    page_title="Tickets Internos",
    layout="wide",
)

USUARIOS = {
    "joao": {
        "senha": "123",
        "nome": "João",
        "setor": "Comercial",
    },
    "ana": {
        "senha": "123",
        "nome": "Ana",
        "setor": "Logística",
    },
    "bruno": {
        "senha": "123",
        "nome": "Bruno",
        "setor": "Financeiro",
    },
}

STATUS = ["Aberto", "Em análise", "Aguardando retorno", "Em execução", "Resolvido"]
SETORES = ["Comercial", "Logística", "Financeiro", "Qualidade", "RH", "Marketing"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Urgente"]

if "logado" not in st.session_state:
    st.session_state.logado = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "tickets" not in st.session_state:
    st.session_state.tickets = []


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

    st.session_state.tickets.append(ticket)


def tickets_visiveis():
    usuario = st.session_state.usuario

    return [
        ticket
        for ticket in st.session_state.tickets
        if ticket["solicitante"] == usuario["nome"]
        or ticket["responsavel"] == usuario["nome"]
        or ticket["setor_destino"] == usuario["setor"]
    ]


if not st.session_state.logado:
    st.title("Tickets Internos")

    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

        if entrar:
            login(usuario, senha)

    st.info("Teste com: joao / 123, ana / 123 ou bruno / 123")
    st.stop()


usuario = st.session_state.usuario

st.sidebar.write(f"Logado como **{usuario['nome']}**")
st.sidebar.write(f"Setor: **{usuario['setor']}**")

pagina = st.sidebar.radio(
    "Menu",
    ["Kanban", "Novo ticket", "Meus tickets"],
)

if st.sidebar.button("Sair"):
    sair()

st.title("Tickets Internos")

tickets = tickets_visiveis()

if pagina == "Novo ticket":
    st.subheader("Abrir ticket")

    with st.form("novo_ticket"):
        titulo = st.text_input("Título")
        descricao = st.text_area("Descrição")
        setor_destino = st.selectbox("Setor destino", SETORES)
        prioridade = st.selectbox("Prioridade", PRIORIDADES)
        responsavel = st.selectbox(
            "Responsável",
            ["Não atribuído"] + [dados["nome"] for dados in USUARIOS.values()],
        )

        enviar = st.form_submit_button("Abrir ticket")

        if enviar:
            if not titulo or not descricao:
                st.error("Preencha título e descrição.")
            else:
                criar_ticket(titulo, descricao, setor_destino, prioridade, responsavel)
                st.success("Ticket criado com sucesso.")

elif pagina == "Kanban":
    st.subheader("Kanban")

    filtros1, filtros2, filtros3 = st.columns(3)

    with filtros1:
        filtro_setor = st.selectbox("Setor", ["Todos"] + SETORES)

    with filtros2:
        filtro_prioridade = st.selectbox("Prioridade", ["Todas"] + PRIORIDADES)

    with filtros3:
        busca = st.text_input("Buscar")

    if filtro_setor != "Todos":
        tickets = [t for t in tickets if t["setor_destino"] == filtro_setor]

    if filtro_prioridade != "Todas":
        tickets = [t for t in tickets if t["prioridade"] == filtro_prioridade]

    if busca:
        tickets = [
            t for t in tickets
            if busca.lower() in t["titulo"].lower()
            or busca.lower() in t["descricao"].lower()
        ]

    colunas = st.columns(len(STATUS))

    for indice, status in enumerate(STATUS):
        with colunas[indice]:
            st.markdown(f"### {status}")

            tickets_status = [t for t in tickets if t["status"] == status]

            if not tickets_status:
                st.caption("Nenhum ticket")

            for ticket in tickets_status:
                with st.container(border=True):
                    st.markdown(f"**#{ticket['id']} - {ticket['titulo']}**")
                    st.caption(f"{ticket['setor_origem']} → {ticket['setor_destino']}")
                    st.caption(f"Prioridade: {ticket['prioridade']}")
                    st.caption(f"Responsável: {ticket['responsavel']}")

                    if st.button("Abrir", key=f"abrir_{ticket['id']}"):
                        st.session_state.ticket_aberto = ticket["id"]

    if "ticket_aberto" in st.session_state:
        ticket = next(
            (t for t in st.session_state.tickets if t["id"] == st.session_state.ticket_aberto),
            None,
        )

        if ticket:
            st.divider()
            st.subheader(f"Ticket #{ticket['id']} - {ticket['titulo']}")

            st.write(ticket["descricao"])
            st.write(f"**Solicitante:** {ticket['solicitante']}")
            st.write(f"**Responsável:** {ticket['responsavel']}")
            st.write(f"**Setor destino:** {ticket['setor_destino']}")

            novo_status = st.selectbox(
                "Status",
                STATUS,
                index=STATUS.index(ticket["status"]),
                key=f"status_{ticket['id']}",
            )

            novo_responsavel = st.selectbox(
                "Responsável",
                ["Não atribuído"] + [dados["nome"] for dados in USUARIOS.values()],
                index=(["Não atribuído"] + [dados["nome"] for dados in USUARIOS.values()]).index(ticket["responsavel"]),
                key=f"responsavel_{ticket['id']}",
            )

            if st.button("Salvar alterações"):
                ticket["status"] = novo_status
                ticket["responsavel"] = novo_responsavel
                st.success("Ticket atualizado.")
                st.rerun()

            st.markdown("#### Comentários")

            for comentario in ticket["comentarios"]:
                st.write(f"**{comentario['autor']}:** {comentario['texto']}")

            novo_comentario = st.text_area("Novo comentário")

            if st.button("Enviar comentário"):
                if novo_comentario:
                    ticket["comentarios"].append(
                        {
                            "autor": usuario["nome"],
                            "texto": novo_comentario,
                        }
                    )
                    st.rerun()

elif pagina == "Meus tickets":
    st.subheader("Meus tickets")

    if not tickets:
        st.info("Nenhum ticket encontrado.")
    else:
        for ticket in tickets:
            with st.expander(f"#{ticket['id']} - {ticket['titulo']}"):
                st.write(ticket["descricao"])
                st.write(f"**Status:** {ticket['status']}")
                st.write(f"**Solicitante:** {ticket['solicitante']}")
                st.write(f"**Responsável:** {ticket['responsavel']}")
                st.write(f"**Setor destino:** {ticket['setor_destino']}")
