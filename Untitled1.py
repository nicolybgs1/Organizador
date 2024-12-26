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
        if row["Estoque"] == "Não":
            score -= 1000
        score -= row["Tanques"] * 10
        score -= row["Prioridade Adicional (Nível)"] * 50
        return score

    data["Prioridade"] = data.apply(priority_score, axis=1)
    return data.sort_values(by=["Prioridade", "ProductPriority"], ascending=True)

# Inicialização da interface
st.title("Organizador de Bombeios")

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
        df = adjust_product_priority(df)
        ranked_df = rank_companies(df)

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
            start_time = end_time + datetime.timedelta(minutes=10)

        # Exibição dos resultados
        st.subheader("Bombeios Organizados por Prioridade e Horário")
        schedule_df = pd.DataFrame(schedule)

        # Exibição dinâmica com botões de editar e remover
        edited_schedule = schedule_df.copy()
        for index, row in schedule_df.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(f"{row['Companhia']} | {row['Produto']} | {row['Volume']} m³")
            with col2:
                if st.button(f"Editar {index}", key=f"edit_{index}"):
                    # Permitir editar os valores
                    new_volume = st.number_input(f"Volume para {row['Companhia']}", value=row["Volume"], step=1, key=f"volume_edit_{index}")
                    edited_schedule.at[index, "Volume"] = new_volume
            with col3:
                if st.button(f"Remover {index}", key=f"remove_{index}"):
                    edited_schedule = edited_schedule.drop(index)

        st.subheader("Tabela Atualizada")
        st.dataframe(edited_schedule.reset_index(drop=True))
    else:
        st.warning("Por favor, insira os dados das companhias.")

