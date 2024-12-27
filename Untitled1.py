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
    
    # Quantidade de tanques por produto e companhia
    TANKS_BY_COMPANY_AND_PRODUCT = {
        "TORRÃO": {"GASOLINA": 1, "DIESEL S10": 1, "DIESEL S500": 1},
        "FIC": {"GASOLINA": 2, "DIESEL S10": 2, "DIESEL S500": 1},
        "TRANSO": {"GASOLINA": 2, "DIESEL S10": 3, "DIESEL S500": 3},
        "TERRANA": {"GASOLINA": 2, "DIESEL S10": 2, "DIESEL S500": 2},
        "D'MAIS": {"GASOLINA": 2, "DIESEL S10": 1, "DIESEL S500": 1},
        "PETROSUL": {"GASOLINA": 1, "DIESEL S10": 1, "DIESEL S500": 1},
        "TCT": {"GASOLINA": 1, "DIESEL S10": 2, "DIESEL S500": 2},
        "SIMARELLI": {"GASOLINA": 1, "DIESEL S10": 1, "DIESEL S500": 2},
        "RUFF/CJ": {"GASOLINA": 2, "DIESEL S10": 2, "DIESEL S500": 1},
        "RM": {"GASOLINA": 1, "DIESEL S10": 1, "DIESEL S500": 1},
        "CROSS": {"GASOLINA": 1, "DIESEL S10": 1, "DIESEL S500": 1},
        "OPLA": {"DIESEL S10": 1, "QAV-1 JET": 1},
        "RAIZEN": {"QAV-1 JET": 3},
        "POOL": {"GASOLINA": 2, "DIESEL S10": 2, "DIESEL S500": 2, "OCB1": 1},
        "VIBRA": {"GASOLINA": 2, "DIESEL S10": 2, "DIESEL S500": 2, "OCB1": 1, "QAV-1 JET": 3}
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
            company = row["Companhia"]
            product = row["Produto"]
            tanks = TANKS_BY_COMPANY_AND_PRODUCT.get(company, {}).get(product, 1)  # Padrão de 1 tanque
            score -= tanks * 10
    
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
    
    # Inicialização da interface
    st.title("Organizador de Bombeios")
    
    # Upload de arquivo Excel
    uploaded_file = st.file_uploader("Envie o arquivo Excel com os dados:", type=["xlsx"])
    
    if uploaded_file is not None:
        # Leitura do arquivo Excel
        input_data = pd.read_excel(uploaded_file)
        st.write("Dados carregados com sucesso:")
        st.dataframe(input_data)
    
        # Processamento dos dados carregados
        input_data = adjust_product_priority(input_data)
        ranked_data = rank_companies(input_data)
    
        # Planejamento do horário dos bombeios
        start_time = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
        end_of_day = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 59))
        schedule = []
        for _, row in ranked_data.iterrows():
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
        schedule_df = pd.DataFrame(schedule)
        st.subheader("Planejamento do Dia")
        st.dataframe(schedule_df)
    
        # Atualização do histórico
        update_historical_data(schedule_df)

        # Entrada dos dados reais ao final do dia
        st.subheader("Entrada dos dados reais ao final do dia")
        
        if "schedule_df" in locals() or "schedule_df" in globals():
            real_data = []
        
            for i, row in schedule_df.iterrows():
                st.markdown(f"### {row['Companhia']} - {row['Produto']}")
                real_start = st.time_input(f"Horário real de início ({row['Companhia']} - {row['Produto']})", key=f"real_start_{i}")
                real_end = st.time_input(f"Horário real de término ({row['Companhia']} - {row['Produto']})", key=f"real_end_{i}")
                
                # Armazenando os dados reais no formato correto
                real_data.append({
                    "Companhia": row["Companhia"],
                    "Produto": row["Produto"],
                    "Início Planejado": row["Início"],
                    "Fim Planejado": row["Fim"],
                    "Início Real": real_start.strftime("%H:%M"),
                    "Fim Real": real_end.strftime("%H:%M"),
                })
        
            if st.button("Salvar Dados Reais"):
                # Convertendo os dados reais para um DataFrame
                real_data_df = pd.DataFrame(real_data)
        
                # Salvando no arquivo histórico
                update_historical_data(real_data_df)
        
                st.success("Dados reais salvos com sucesso!")
                st.dataframe(real_data_df)  # Exibindo os dados reais salvos
        else:
            st.warning("Por favor, organize o dia antes de inserir os dados reais.")
