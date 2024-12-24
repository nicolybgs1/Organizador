import streamlit as st
import pandas as pd
import datetime
import os

# Dados de velocidades de envio por produto
RATE_BY_PRODUCT = {
    "GAS": 500,
    "S10": 600,
    "S500": 560,
    "QAV": 240,
    "QAV-A1": 240,
    "OC": 300
}

# Preferências de produtos por companhia
PRODUCT_PRIORITY = {
    "TSO": "S10", "DM": "S10", "FIC": "S10", "CJ": "S10", "TOR": "S10", "PTS": "S10",
    "CRS": "S500", "TCT": "S500", "TRR": "S500"
}

# Caminho do arquivo de dados históricos
HISTORICAL_DATA_PATH = "dados_revisados.csv"

# Função para calcular tempo de bombeio com base no produto e companhia
def calculate_bombeio_time(product, volume, company):
    rate = RATE_BY_PRODUCT.get(product, 500)
    if product == "S10" and company in ["POO", "PET"]:
        rate = 1200
    duration = volume / rate  # duração em horas
    return round(duration * 60)  # duração em minutos

# Função para ajustar prioridade do produto baseado nas preferências
def adjust_product_priority(data):
    def product_priority(row):
        company = row["Companhia"]
        product = row["Produto"]
        if company in PRODUCT_PRIORITY:
            preferred_product = PRODUCT_PRIORITY[company]
            return 0 if product == preferred_product else 1
        return 2  # Caso não haja preferência

    data["ProductPriority"] = data.apply(product_priority, axis=1)
    return data.sort_values(by=["ProductPriority"], ascending=True)

# Função para priorizar companhias
def rank_companies(data):
    def priority_score(row):
        score = 0
        # Regra 1: Estoque (Máxima prioridade)
        if row["Estoque"] == "Não":
            score -= 1000

        # Regra 2: Quantidade de tanques (Quanto menor, maior prioridade)
        score -= row["Tanques"] * 10

        # Regra 3: Prioridade Adicional (quanto maior o nível, maior prioridade negativa)
        score -= row["Prioridade Adicional (Nível)"] * 50

        return score

    data["Prioridade"] = data.apply(priority_score, axis=1)
    return data.sort_values(by=["Prioridade", "ProductPriority"], ascending=True)

# Função para carregar ou inicializar dados persistentes
def load_or_initialize_data():
    if os.path.exists(HISTORICAL_DATA_PATH):
        return pd.read_csv(HISTORICAL_DATA_PATH)
    return pd.DataFrame(columns=["Companhia", "Produto", "Volume", "Início", "Fim", "Prioridade Adicional", "Início Real", "Fim Real"])

# Função para salvar dados no arquivo persistente
def save_data(data):
    data.to_csv(HISTORICAL_DATA_PATH, index=False)

# Inicialização da interface
st.title("Organizador de Bombeios")

# Carregar dados persistentes
data = load_or_initialize_data()

# Entrada de dados do usuário
st.subheader("Insira os dados das companhias para o dia seguinte:")
num_companies = st.number_input("Quantas companhias irão receber produto?", min_value=1, step=1)

company_data = []
for i in range(int(num_companies)):
    st.markdown(f"### Companhia {i+1}")
    company = st.selectbox(f"Nome da Companhia {i+1}", ["POO", "PET", "SIM", "PTS", "FIC", "CJ", "TCT", "TRR", "TSO", "RM", "OPL", "CRS", "TOR", "DM", "SHE"], key=f"company_{i}")
    product = st.selectbox(f"Produto {i+1}", ["GAS", "S10", "S500", "QAV", "QAV-A1", "OC"], key=f"product_{i}")
    volume = st.number_input(f"Volume (m³) a ser enviado {i+1}", min_value=0, step=1, key=f"volume_{i}")
    stock = st.selectbox(f"Companhia tem estoque? {i+1}", ["Sim", "Não"], key=f"stock_{i}")
    tanks = st.number_input(f"Quantidade de tanques {i+1}", min_value=1, step=1, key=f"tanks_{i}")
    additional_priority = st.text_input(f"Prioridade Adicional {i+1} (Operacional ou Cliente)", key=f"add_priority_{i}")
    additional_priority_level = st.slider(f"Nível da Prioridade Adicional {i+1} (0-10)", min_value=0, max_value=10, key=f"priority_level_{i}")

    company_data.append({
        "Companhia": company,
        "Produto": product,
        "Volume": volume,
        "Estoque": stock,
        "Tanques": tanks,
        "Prioridade Adicional": additional_priority,
        "Prioridade Adicional (Nível)": additional_priority_level
    })

# Processamento dos dados
if st.button("Organizar meu dia"):
    if len(company_data) > 0:
        df = pd.DataFrame(company_data)
        # Ajustar a prioridade de produtos
        df = adjust_product_priority(df)
        # Ranqueamento final
        ranked_df = rank_companies(df)

        # Planejamento do horário dos bombeios
        start_time = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
        end_of_day = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 59))
        schedule = []
        for _, row in ranked_df.iterrows():
            duration = calculate_bombeio_time(row["Produto"], row["Volume"], row["Companhia"])
            end_time = start_time + datetime.timedelta(minutes=duration)

            if end_time > end_of_day:
                st.warning(f"Não foi possível programar o bombeio para a companhia {row['Companhia']} devido ao limite de tempo diário.")
                break

            schedule.append({
                "Companhia": row["Companhia"],
                "Produto": row["Produto"],
                "Volume": row["Volume"],
                "Início": start_time.strftime("%H:%M"),
                "Fim": end_time.strftime("%H:%M"),
                "Prioridade Adicional": row["Prioridade Adicional"]
            })
            # Adiciona intervalo de 10 minutos entre bombeios
            start_time = end_time + datetime.timedelta(minutes=10)

        # Exibição dos resultados
        st.subheader("Bombeios Organizados por Prioridade e Horário")
        schedule_df = pd.DataFrame(schedule)

        # Lista de IDs das linhas para interagir
        schedule_df["ID"] = schedule_df.index

        # Exibir dados e botões para edição e remoção
        for index, row in schedule_df.iterrows():
            cols = st.columns([4, 1, 1])  # Ajuste a proporção conforme necessário
            with cols[0]:
                st.write(row.to_frame().T)  # Exibe a linha do DataFrame
            with cols[1]:
                if st.button(f"Remover", key=f"remove_{index}"):
                    schedule_df = schedule_df.drop(index).reset_index(drop=True)
                    save_data(schedule_df)  # Salva os dados no CSV
                    st.success(f"Bombeio da companhia {row['Companhia']} removido com sucesso!")
            with cols[2]:
                if st.button(f"Editar", key=f"edit_{index}"):
                    st.session_state.edit_index = index

        # Verifica se há uma linha em edição
        if "edit_index" in st.session_state and st.session_state.edit_index is not None:
            edit_index = st.session_state.edit_index
            st.subheader("Editar Bombeio")

            # Preenche os campos com os dados atuais da linha selecionada
            edit_company = st.text_input("Companhia", value=schedule_df.loc[edit_index, "Companhia"])
            edit_product = st.text_input("Produto", value=schedule_df.loc[edit_index, "Produto"])
            edit_volume = st.number_input("Volume (m³)", min_value=0, step=1, value=int(schedule_df.loc[edit_index, "Volume"]))
            edit_start_time = st.text_input("Hora de Início (HH:MM)", value=schedule_df.loc[edit_index, "Início"])

            # Botão para salvar a edição
            if st.button("Salvar Edição"):
                schedule_df.loc[edit_index, "Companhia"] = edit_company
                schedule_df.loc[edit_index, "Produto"] = edit_product
                schedule_df.loc[edit_index, "Volume"] = edit_volume
                schedule_df.loc[edit_index, "Início"] = edit_start_time

                save_data(schedule_df)
                st.success("Bombeio editado com sucesso!")
                st.session_state.edit_index = None

        # Exibir e salvar o agendamento atualizado
        st.write("Tabela de Bombeios Atualizada:", schedule_df)
        st.success("Dados atualizados com sucesso!")


