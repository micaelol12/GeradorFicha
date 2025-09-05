import pandas as pd
import pyodbc
import warnings
import os
from dotenv import load_dotenv
import math

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv() 

server = os.getenv("SERVER")
database = os.getenv("DATABASE")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

matriculas = [(1170597,1),(1160290,1),(1164783,1),(1153544,1),(1142356,1),(1148290,1),(1166913,1),(1148664,1),(1164040,1),(1023047,1)]
tabela_destino = "FICHAFINANCEIRA"
competencia_inicial = '2025-06-01'
competencia_final = '2025-08-01'
max_linhas_por_arquivo = 150

conn = pyodbc.connect(
    f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
)

output_dir = "sql_inserts"
os.makedirs(output_dir, exist_ok=True)

for matricula,contrato in matriculas:
    try:
        query = f"""
            SELECT * 
            FROM {tabela_destino}
            WHERE cdMatricula = ? 
            AND sqContrato = ?
            AND dtCompetencia BETWEEN ? AND ?
        """
        
        result = pd.read_sql(query, conn,params=(matricula, contrato, competencia_inicial, competencia_final))
        
        colunas = result.columns.tolist()
        colunas_str = ", ".join(colunas)

        valores_linhas = []
        for _, row in result.iterrows():
            valores = []
            for c in colunas:
                v = row[c]
                if pd.isna(v):
                    valores.append("NULL")
                elif isinstance(v, str):
                    escaped = v.replace("'", "''")
                    valores.append(f"'{escaped}'")
                elif hasattr(v, "strftime"):
                    valores.append(f"'{v.strftime('%Y-%m-%d %H:%M:%S')}'")
                else:
                    valores.append(str(v))
            valores_str = "(" + ", ".join(valores) + ")"
            valores_linhas.append(valores_str)
            
        total_blocos = math.ceil(len(valores_linhas) / max_linhas_por_arquivo)
        
        for i in range(total_blocos):
            bloco = valores_linhas[i*max_linhas_por_arquivo:(i+1)*max_linhas_por_arquivo]
            insert_sql = f"INSERT INTO {tabela_destino} ({colunas_str}) VALUES\n" + ",\n".join(bloco) + ";"
            path = os.path.join(output_dir, f"insert_matricula_{matricula}_{contrato}_part{i+1}.sql")
            with open(path, "w", encoding="utf-8") as f:
                f.write(insert_sql)

        print(f"Insert único gerado com {len(valores_linhas)} registros!")
    except Exception as e:
        print(f"Ocorreu um erro ao gerar o insert da matricula {matricula}-{contrato}: {e}")
