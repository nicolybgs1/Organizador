import streamlit as st
import pandas as pd
import openpyxl  # Agora você pode usar o openpyxl para ler arquivos Excel

# Função para carregar e exibir o arquivo Excel
def load_excel_file(file):
    try:
        # Carregar o arquivo Excel com pandas
        df = pd.read_excel(file, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar o arquivo: {e}")
        return None

# Interface do Streamlit
st.title("Carregar e Validar Dados do Excel")

# Botão para carregar o arquivo
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    # Carregar os dados do Excel
    df = load_excel_file(uploaded_file)
    if df is not None:
        # Exibir os dados carregados em um DataFrame
        st.write("Dados carregados do arquivo Excel:")
        st.dataframe(df)

        # Pedir ao usuário para validar os dados
        if st.button("Validar Dados"):
            st.success("Dados validados com sucesso! Agora você pode prosseguir.")
            # Aqui você pode adicionar lógica adicional para prosseguir com o restante do código
        else:
            st.warning("Por favor, valide os dados antes de prosseguir.")

