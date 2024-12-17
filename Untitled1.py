#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import pandas as pd
import datetime

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

# Inicialização da interface
st.title("Organizador de Bombeios")

# Entrada de dados do usuário
st.subheader("Insira os dados das companhias para o dia seguinte:")
num_companies = st.number_input("Quantas companhias irão receber produto?", min_value=1, step=1)

# Use session_state to store the company data across page refreshes
if 'company_data' not in st.session_state:
    st.session_state.company_data = []

# Adiciona novos dados ao session_state
for i in range(int(num_companies)):
    st.markdown(f"### Companhia {i+1}")
    company = st.selectbox(f"Nome da Companhia {i+1}", ["POO", "PET", "SIM", "PTS", "FIC", "CJ", "TCT", "TRR", "TSO", "RM", "OPL", "CRS", "TOR", "DM", "SHE"], key=f"company_{i}")
    product = st.selectbox(f"Produto {i+1}", ["GAS", "S10", "S500", "QAV", "QAV-A1", "OC"], key=f"product_{i}")
    volume = st.number_input(f"Volume (m³) a ser enviado {i+1}", min_value=0, step=1, key=f"volume_{i}")
    stock = st.selectbox(f"Companhia tem estoque? {i+1}", ["Sim", "Não"], key=f"stock_{i}")
    tanks = st.number_input(f"Quantidade de tanques {i+1}", min_value=1, step=1, key=f"tanks_{i}")
    additional_priority = st.text_input(f"Prioridade Adicional {i+1} (Operacional ou Cliente)", key=f"add_priority_{i}")
    additional_priority_level = st.slider(f"Nível da Prioridade Adicional {i+1} (0-10)", min_value=0, max_value=10, key=f"priority_level_{i}")
    
    # Adiciona dados no session_state
    st.session_state.company_data.append({
        "Companhia": company, 
        "Produto": product, 
        "Volume": volume, 
        "Estoque": stock, 
        "Tanques": tanks,
        "Prioridade Adicional": additional_priority,
        "Prioridade Adicional (Nível)": additional_priority_level
    })

# Função para remover uma linha
def remove_row(df, index):
    return df.drop(index)

# Processamento dos dados
if st.button("Organizar meu dia"):
    if len(st.session_state.company_data) > 0:
        df = pd.DataFrame(st.session_state.company_data)
        # Ajustar a prioridade de produtos
        df = adjust_product_priority(df)
        # Ranqueamento final
        ranked_df = rank_companies(df)

        # Exibição dos resultados
        st.subheader("Bombeios Organizados por Prioridade e Horário")
        schedule_df = pd.DataFrame(ranked_df)
        st.dataframe(schedule_df)

        # Opção para remover uma linha
        row_to_remove = st.selectbox("Selecione uma linha para remover", schedule_df.index)
        if st.button("Remover Linha"):
            st.session_state.company_data = st.session_state.company_data[:row_to_remove] + st.session_state.company_data[row_to_remove+1:]
            st.success(f"Linha {row_to_remove} removida com sucesso!")
            st.experimental_rerun()  # Recarregar a página para refletir a remoção

    else:
        st.warning("Por favor, insira os dados das companhias.")
