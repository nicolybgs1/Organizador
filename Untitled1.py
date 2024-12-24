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
        st.dataframe(schedule_df)

        # Salvar agendamento
        data = pd.concat([data, schedule_df], ignore_index=True)
        save_data(data)
        st.success("Dados salvos com sucesso!")

# Exibir dados salvos e permitir edição e exclusão
st.subheader("Dados Salvos")
if not data.empty:
    for i, row in data.iterrows():
        st.markdown(f"**Linha {i+1} - Companhia: {row['Companhia']}**")
        if st.button(f"Editar Linha {i+1}"):
            new_volume = st.number_input(f"Editar Volume (Linha {i+1})", value=row["Volume"], min_value=0)
            data.at[i, "Volume"] = new_volume
            save_data(data)
            st.success(f"Linha {i+1} atualizada com sucesso!")
        if st.button(f"Excluir Linha {i+1}"):
            data = data.drop(i).reset_index(drop=True)
            save_data(data)
            st.success(f"Linha {i+1} excluída com sucesso!")
else:
    st.info("Nenhum dado salvo ainda.")
