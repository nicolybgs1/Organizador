import streamlit as st
import pandas as pd
import datetime
import openpyxl

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

# Função para calcular tempo de bombeio com base no produto e volume
def calculate_bombeio_time(product, volume):
    rate = RATE_BY_PRODUCT.get(product, 500)
    if volume <= 0:  # Verifica se o volume é inválido
        return 0
    duration = volume / rate  # duração em horas
    return duration * 60  # duração em minutos

# Função para calcular o horário de fim com base no horário de início e tempo de bombeio
def calculate_end_time(start_time, duration_minutes):
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    return end_time

# Função para priorizar companhias com base nas regras
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

        # Regra 4: Preferência de produto por companhia (Prioridade adicional)
        preferred_product = PRODUCT_PRIORITY.get(row["Companhia"])
        
        if preferred_product:
            if row["Produto"] == preferred_product:
                score -= 500  # O produto preferido recebe maior prioridade
            else:
                score += 500  # Outros produtos têm menor prioridade
        else:
            score += 1000  # Caso não haja preferência, penaliza mais

        return score

    data["Prioridade"] = data.apply(priority_score, axis=1)
    
    # Corrigido para usar apenas "Prioridade" na ordenação
    return data.sort_values(by=["Prioridade"], ascending=True)
    
# Função para gerar o planejamento do dia com base nas prioridades e volumes
def generate_bombeio_schedule(data):
    schedule = []
    start_time = datetime.datetime.strptime("00:00", "%H:%M")  # O primeiro bombeio começa às 00:00
    
    # Classificar os dados com base na priorização das companhias
    data = rank_companies(data)
    
    for i, row in data.iterrows():
        product = row['Produto']
        volume = row['Volume']
        company = row['Companhia']
        
        # Calcular o tempo de bombeio para esse produto e volume
        duration_minutes = calculate_bombeio_time(product, volume)
        
        # Calcular horário de fim com base no horário de início atual
        end_time = start_time + datetime.timedelta(minutes=duration_minutes)
        
        # Verificar se o bombeio ultrapassa o limite de 23:59
        if end_time > datetime.datetime.strptime("23:59", "%H:%M"):
            print(f"Bombeio para {company} às {start_time.strftime('%H:%M')} não pode ser agendado (ultrapassa o limite do dia).")
            break
        
        # Adicionar ao planejamento
        schedule.append({
            'Companhia': company,
            'Produto': product,
            'Volume': volume,
            'Hora de Início': start_time.strftime("%H:%M"),
            'Hora de Fim': end_time.strftime("%H:%M"),
        })
        
        # Atualizar o horário de início para o próximo bombeio, respeitando o intervalo de 10 minutos
        start_time = end_time + datetime.timedelta(minutes=10)
    
    return pd.DataFrame(schedule)


# Inicialização da interface
st.title("Planejamento e Registro de Bombeios")

# Upload de arquivo Excel
uploaded_file = st.file_uploader("Envie o arquivo Excel com os dados:", type=["xlsx"])

if uploaded_file is not None:
    # Leitura das planilhas do arquivo Excel
    excel_data = pd.ExcelFile(uploaded_file)
    
    # Iteração sobre cada planilha (produto)
    all_data = []
    for sheet_name in excel_data.sheet_names:
        # Leitura dos dados de cada planilha (produto)
        sheet_data = excel_data.parse(sheet_name)
        sheet_data["Produto"] = sheet_name  # Adiciona uma coluna 'Produto' com o nome da planilha
        
        # Adiciona os dados da planilha à lista
        all_data.append(sheet_data)
    
    # Combina todos os dados em um único DataFrame
    input_data = pd.concat(all_data, ignore_index=True)
    
    # Filtra os dados para garantir que apenas volumes válidos (maiores que 0) sejam considerados
    valid_data = input_data[input_data["Volume"] > 0]

    # Exibe os dados filtrados
    st.write("Dados filtrados (Volume > 0):")
    st.dataframe(valid_data)
    
    # Adicionar colunas interativas de estoque e prioridade
    valid_data['Estoque'] = valid_data['Produto'].apply(lambda x: 'Sim' if x in ['GASOLINA', 'DIESEL S10', 'DIESEL S500'] else 'Não')
    valid_data['Prioridade Adicional (Nível)'] = valid_data['Companhia'].apply(lambda x: 3 if x in PRODUCT_PRIORITY else 1)
    valid_data['Tanques'] = valid_data.apply(lambda row: TANKS_BY_COMPANY_AND_PRODUCT.get(row['Companhia'], {}).get(row['Produto'], 1), axis=1)

    # Exibe a tabela interativa para edição dos campos de estoque e prioridade
    st.write("Dados com informações de estoque e prioridade (Edite os valores):")
    edited_data = st.data_editor(valid_data, num_rows="dynamic", use_container_width=True)

    # Agrupar os dados por companhia e produto
    grouped_data = edited_data.groupby(['Companhia', 'Produto']).apply(generate_bombeio_schedule).reset_index(drop=True)

    # Exibe o planejamento de bombeios para cada combinação de companhia e produto
    st.write("Planejamento de Bombeios por Produto e Companhia:")
    st.dataframe(grouped_data, use_container_width=True)

    # Permitir que o usuário edite diretamente os dados reais de bombeio
    st.write("Dados Reais de Bombeio (Edite os horários reais):")
    edited_bombeio_schedule = st.data_editor(grouped_data, num_rows="dynamic", use_container_width=True)

    # Permitir download dos dados reais de bombeio
    st.download_button(
        label="Baixar os dados reais de bombeio",
        data=edited_bombeio_schedule.to_csv(index=False).encode('utf-8'),
        file_name="dados_reais_bombeio.csv",
        mime="text/csv"
    )
    st.success("Dados reais de bombeio salvos com sucesso!")
