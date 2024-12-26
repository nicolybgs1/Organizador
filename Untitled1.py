import streamlit as st
import pandas as pd
import datetime
import os

# Dados de velocidades de envio por produto
RATE_BY_PRODUCT = {
    "GASOLINA": 500,
    "DIESEL S10": 600,
    "DIESEL S500": 560,
    "QAV-1 JET": 240,
    "OCB1": 300
}

# Preferências de produtos por companhia
PRODUCT_PRIORITY = {
    "TRANSO": "DIESEL S10", "D'MAIS": "DIESEL S10", "FIC": "DIESEL S10", "RUFF/CJ": "DIESEL S10", "TORRÃO": "DIESEL S10", "PETROSUL": "DIESEL S10",
    "CROSS": "DIESEL S500", "TCT": "DIESEL S500", "TERRANA": "DIESEL S500"
}

# Caminho do arquivo de dados históricos
HISTORICAL_DATA_PATH = "dados_revisados.csv"

# Função para calcular tempo de bombeio com base no produto e companhia
def calculate_bombeio_time(product, volume, company):
    rate = RATE_BY_PRODUCT.get(product, 500)
    if product == "DIESEL S10" and company in ["POOL", "VIBRA"]:
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

# Função para atualizar dados históricos
def update_historical_data(new_data):
    if os.path.exists(HISTORICAL_DATA_PATH):
        historical_data = pd.read_csv(HISTORICAL_DATA_PATH)
        historical_data = pd.concat([historical_data, new_data], ignore_index=True)
    else:
        historical_data = new_data
    historical_data.to_csv(HISTORICAL_DATA_PATH, index=False)

# Função para carregar dados históricos
def load_historical_data():
    if os.path.exists(HISTORICAL_DATA_PATH):
        return pd.read_csv(HISTORICAL_DATA_PATH)
    return pd.DataFrame()

# Função para ajustar taxas com base em dados históricos
def adjust_rates_with_historical_data(historical_data):
    if not historical_data.empty:
        global RATE_BY_PRODUCT
        avg_rates = historical_data.groupby("Produto").apply(
            lambda x: (x["Volume"].sum() / ((x["Fim"] - x["Início"]).dt.total_seconds().sum() / 3600))
        )
        for product, rate in avg_rates.items():
            RATE_BY_PRODUCT[product] = rate

# Inicialização da interface
st.title("Organizador de Bombeios")

# Entrada de dados do usuário
st.subheader("Insira os dados das companhias para o dia seguinte:")
num_companies = st.number_input("Quantas companhias irão receber produto?", min_value=1, step=1)

company_data = []
for i in range(int(num_companies)):
    st.markdown(f"### Companhia {i+1}")
    company = st.selectbox(f"Nome da Companhia {i+1}", ["POOL", "VIBRA", "SIMARELLI", "PETROSUL", "FIC", "RUFF/CJ", "TCT", "TERRANA", "TRANSO", "RM", "OPLA", "CROSS", "TORRÃO", "D'MAIS", "RAIZEN"], key=f"company_{i}")
    product = st.selectbox(f"Produto {i+1}", ["GASOLINA", "DIESEL S10", "DIESEL S500", "QAV-1 JET", "OCB1"], key=f"product_{i}")
    volume = st.number_input(f"Volume (m³) a ser enviado {i+1}", min_value=0, step=1, key=f"volume_{i}")
    stock = st.selectbox(f"Companhia tem estoque? {i+1}", ["Sim", "Não"], key=f"stock_{i}")
    additional_priority = st.text_input(f"Prioridade Adicional {i+1} (Operacional ou Cliente)", key=f"add_priority_{i}")
    additional_priority_level = st.slider(f"Nível da Prioridade Adicional {i+1} (0-10)", min_value=0, max_value=10, key=f"priority_level_{i}")

    company_data.append({
        "Companhia": company,
        "Produto": product,
        "Volume": volume,
        "Estoque": stock,
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

        # Entrada dos dados reais
        st.subheader("Entrada dos dados reais ao final do dia")
        for i, row in schedule_df.iterrows():
            real_start = st.time_input(f"Horário real de início ({row['Companhia']})", key=f"real_start_{i}")
            real_end = st.time_input(f"Horário real de término ({row['Companhia']})", key=f"real_end_{i}")

        if st.button("Salvar Dados Reais"):
            schedule_df["Início Real"] = schedule_df["Início"]
            schedule_df["Fim Real"] = schedule_df["Fim"]
            update_historical_data(schedule_df)
            st.success("Dados reais salvos com sucesso!")

    else:
        st.warning("Por favor, insira os dados das companhias.")
