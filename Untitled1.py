import streamlit as st
import pandas as pd
import openpyxl

# Função para carregar o arquivo Excel e exibir os dados
def load_and_display_excel():
    uploaded_file = st.file_uploader("Carregue seu arquivo Excel", type=["xlsx"])

    if uploaded_file is not None:
        # Carregar o arquivo Excel
        try:
            data = pd.read_excel(uploaded_file)
            st.subheader("Dados Carregados para Validação")
            st.dataframe(data)  # Exibir o DataFrame carregado

            # Botão para validar
            validate_button = st.button("Validar Dados")

            if validate_button:
                st.success("Dados validados com sucesso!")
                return data  # Retorna o DataFrame validado
            else:
                st.warning("Por favor, revise os dados e clique em 'Validar'.")
                return None  # Dados não validados
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo: {e}")
            return None  # Retorna None em caso de erro
    else:
        st.info("Por favor, carregue um arquivo Excel para continuar.")
        return None  # Nenhum arquivo carregado

# Inicialização da interface
st.title("Organizador de Bombeios")

# Carregar e validar dados
df = load_and_display_excel()

if df is not None:
    # Se os dados forem validados, prosseguir com o código principal

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
