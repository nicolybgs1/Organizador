import streamlit as st
import pandas as pd
import datetime
import os
import sqlite3  # Usando SQLite como exemplo de banco de dados

# Configurações de arquivos e banco
PREDICTED_DATA_PATH = "dados_previstos.csv"
DB_PATH = "dados_reais.db"

# Função para salvar dados previstos em um arquivo CSV
def save_predicted_data(data):
    data.to_csv(PREDICTED_DATA_PATH, index=False)

# Função para carregar dados previstos de um arquivo CSV
def load_predicted_data():
    if os.path.exists(PREDICTED_DATA_PATH):
        return pd.read_csv(PREDICTED_DATA_PATH)
    return pd.DataFrame()

# Função para salvar dados reais no banco de dados
def save_real_data_to_db(data):
    with sqlite3.connect(DB_PATH) as conn:
        data.to_sql("dados_reais", conn, if_exists="append", index=False)

# Função para criar a tabela no banco de dados, se não existir
def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dados_reais (
                Companhia TEXT,
                Produto TEXT,
                Volume REAL,
                Inicio_Real TEXT,
                Fim_Real TEXT,
                Prioridade_Adicional TEXT
            )
        """)

# Inicialização
st.title("Organizador de Bombeios")
initialize_database()

# Carregar dados previstos, se existir
predicted_data = load_predicted_data()

# Entrada de novos dados para previsão
st.subheader("Insira os dados das companhias para o dia seguinte:")
num_companies = st.number_input("Quantas companhias irão receber produto?", min_value=1, step=1)

company_data = []
for i in range(int(num_companies)):
    st.markdown(f"### Companhia {i+1}")
    company = st.selectbox(f"Nome da Companhia {i+1}", ["POO", "PET", "SIM", "PTS", "FIC", "CJ", "TCT", "TRR", "TSO", "RM", "OPL", "CRS", "TOR", "DM", "SHE"], key=f"company_{i}")
    product = st.selectbox(f"Produto {i+1}", ["GAS", "S10", "S500", "QAV", "QAV-A1", "OC"], key=f"product_{i}")
    volume = st.number_input(f"Volume (m³) a ser enviado {i+1}", min_value=0, step=1, key=f"volume_{i}")
    company_data.append({"Companhia": company, "Produto": product, "Volume": volume})

# Processar dados e salvar previsão
if st.button("Organizar meu dia"):
    if len(company_data) > 0:
        df = pd.DataFrame(company_data)
        st.subheader("Bombeios organizados (Previsão)")
        st.dataframe(df)

        # Salvar previsão em arquivo
        save_predicted_data(df)
        st.success("Dados previstos salvos para próxima sessão!")
    else:
        st.warning("Por favor, insira os dados das companhias.")

# Exibir previsão carregada, se existir
if not predicted_data.empty:
    st.subheader("Dados Previstos Carregados")
    st.dataframe(predicted_data)

    # Entrada dos dados reais ao final do dia
    st.subheader("Entrada dos dados reais ao final do dia")
    real_data = []
    for i, row in predicted_data.iterrows():
        real_start = st.time_input(f"Horário real de início ({row['Companhia']})", key=f"real_start_{i}")
        real_end = st.time_input(f"Horário real de término ({row['Companhia']})", key=f"real_end_{i}")
        real_data.append({
            "Companhia": row["Companhia"],
            "Produto": row["Produto"],
            "Volume": row["Volume"],
            "Inicio_Real": real_start.strftime("%H:%M"),
            "Fim_Real": real_end.strftime("%H:%M"),
            "Prioridade_Adicional": row.get("Prioridade_Adicional", "N/A")
        })

    # Salvar dados reais no banco de dados
    if st.button("Salvar Dados Reais"):
        if real_data:
            real_data_df = pd.DataFrame(real_data)
            save_real_data_to_db(real_data_df)
            st.success("Dados reais salvos com sucesso no banco de dados!")
        else:
            st.warning("Por favor, insira os horários reais antes de salvar.")
