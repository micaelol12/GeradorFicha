import os
import pandas as pd
import math

def gerar_inserts(
    conn,
    matriculas,  # [(matricula, contrato)]
    tabela,
    competencia_inicial,
    competencia_final,
    max_linhas_por_arquivo,
    identity_insert,
    output_dir,
    log_callback,
    progress_callback
):
    total = len(matriculas)
    
    for idx, (matricula, contrato) in enumerate(matriculas, start=1):
        try:
            log_callback(f"Processando matrícula {matricula}-{contrato}")
            
            folderpath = os.path.join(output_dir, f"{matricula}_{contrato}")
            
            os.makedirs(folderpath, exist_ok=True)

            query = f"""
                SELECT * 
                FROM {tabela}
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
                raise Exception(f"Nenhum valor encontrado na tabela {tabela} para a matricula {matricula}-{contrato}") 
                
            if max_linhas_por_arquivo:
                total_blocos = math.ceil(len(valores_linhas) / max_linhas_por_arquivo)
            else:
                total_blocos = 1 
                    
            for i in range(total_blocos):
                insert_sql = ""
                
                if max_linhas_por_arquivo:
                    bloco = valores_linhas[i*max_linhas_por_arquivo:(i+1)*max_linhas_por_arquivo]
                else:
                    bloco = valores_linhas
                
                if identity_insert:
                    insert_sql += f"SET IDENTITY_INSERT {tabela} ON;\n"
                    
                insert_sql += f"INSERT INTO {tabela} ({colunas_str}) VALUES\n" + ",\n".join(bloco) + ";"
                
                if identity_insert:
                    insert_sql += f"\nSET IDENTITY_INSERT {tabela} OFF;"
                    
                if total_blocos > 1:
                    file_name = f"insert_{tabela}_part{i+1}.sql"
                else:
                    file_name = f"insert_{tabela}.sql"
                
                path = os.path.join(folderpath,file_name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(insert_sql)
                    
                progress_callback((i / total_blocos) * 100)
                    
            progress_callback((idx / total) * 100)
            
        except Exception as e:
            log_callback(f"Ocorreu um erro ao gerar o insert da matricula {matricula}-{contrato}: {e}")
        
        log_callback("Todos os inserts foram gerados com sucesso.")
        