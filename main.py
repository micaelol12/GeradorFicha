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

matriculas = [(14630,1),(14671,1),(15942,1),(16057,1),(14200,1),(16594,1),(17104,1),(17112,1),(17196,1)]
tabela_destino = "FichaFinanceiraCalculo"
competencia_inicial = '2005-01-01'
competencia_final = '2026-01-01'
max_linhas_por_arquivo = None # maximo 150
output_dir = "sql_inserts"

conn = pyodbc.connect(
    f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
)

for matricula,contrato in matriculas:
    try:
        folderpath = os.path.join(output_dir, f"{matricula}_{contrato}")
        
        os.makedirs(folderpath, exist_ok=True)

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
        
        if len(valores_linhas) == 0:
            raise Exception(f"Nenhum valor encontrado na tabela {tabela_destino} para a matricula {matricula}-{contrato}") 
            
        if max_linhas_por_arquivo:
            total_blocos = math.ceil(len(valores_linhas) / max_linhas_por_arquivo)
        else:
            total_blocos = 1 
                   
        for i in range(total_blocos):
            
            if max_linhas_por_arquivo:
                bloco = valores_linhas[i*max_linhas_por_arquivo:(i+1)*max_linhas_por_arquivo]
            else:
                bloco = valores_linhas
                
            insert_sql = f"INSERT INTO {tabela_destino} ({colunas_str}) VALUES\n" + ",\n".join(bloco) + ";"
            
            if total_blocos > 1:
                file_name = f"insert_{tabela_destino}_part{i+1}.sql"
            else:
                file_name = f"insert_{tabela_destino}.sql"
            
            path = os.path.join(folderpath,file_name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(insert_sql)

        print(f"Insert único gerado com {len(valores_linhas)} registros da matricula {matricula}-{contrato}!")
    except Exception as e:
        print(f"Ocorreu um erro ao gerar o insert da matricula {matricula}-{contrato}: {e}")
