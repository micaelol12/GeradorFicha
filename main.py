import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import pyodbc

from Config import carregar_config,salvar_config
from Gerador import gerar_inserts

CONFIG_FILE = "config.json"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gerador de INSERT SQL")
        self.geometry("700x700")
        self.resizable(False, False)

        self.config_data = carregar_config()

        self._criar_variaveis()
        self._criar_layout()

    def _criar_variaveis(self):
        self.server = tk.StringVar(value=self.config_data.get("server", ""))
        self.database = tk.StringVar(value=self.config_data.get("database", ""))
        self.username = tk.StringVar(value=self.config_data.get("username", ""))
        self.password = tk.StringVar(value=self.config_data.get("password", ""))

        self.tabela = tk.StringVar(value=self.config_data.get("tabela", "BaseEncargos"))
        self.comp_ini = tk.StringVar(value="2026-01-01")
        self.comp_fim = tk.StringVar(value="2026-01-01")
        self.max_linhas = tk.StringVar(value=str(self.config_data.get("max_linhas", 150)))
        self.identity = tk.BooleanVar(value=self.config_data.get("identity", False))
        self.output_dir = tk.StringVar(value=self.config_data.get("output_dir", "sql_inserts"))

    def _criar_layout(self):
        frame_conn = ttk.LabelFrame(self, text="Conexão SQL Server")
        frame_conn.pack(fill="x", padx=10, pady=10)

        self._campo(frame_conn, "Server", self.server, 0)
        self._campo(frame_conn, "Database", self.database, 1)
        self._campo(frame_conn, "Usuário", self.username, 2)

        ttk.Label(frame_conn, text="Senha").grid(row=3, column=0, sticky="w", padx=5)
        ttk.Entry(frame_conn, textvariable=self.password, show="*", width=40)\
            .grid(row=3, column=1, padx=5)

        ttk.Button(frame_conn, text="Testar conexão", command=self._testar_conexao)\
            .grid(row=4, column=1, sticky="w", padx=5, pady=5)

        frame_lista = ttk.LabelFrame(self, text="Matrículas / Contratos")
        frame_lista.pack(fill="x", padx=10)

        self.tree = ttk.Treeview(
            frame_lista,
            columns=("matricula", "contrato"),
            show="headings",
            height=6
        )
        self.tree.heading("matricula", text="Matrícula")
        self.tree.heading("contrato", text="Contrato")
        self.tree.column("matricula", width=120, anchor="center")
        self.tree.column("contrato", width=120, anchor="center")
        self.tree.pack(side="left", padx=5, pady=5)
        
        for mat in self.config_data.get("matriculas", []):
            self.tree.insert("", "end", values=(mat[0], mat[1]))

        btns = ttk.Frame(frame_lista)
        btns.pack(side="left", padx=10)

        ttk.Button(btns, text="Adicionar", command=self._adicionar).pack(fill="x", pady=2)
        ttk.Button(btns, text="Remover", command=self._remover).pack(fill="x", pady=2)
        ttk.Button(btns, text="Remover todas", command=self._remover_todas).pack(fill="x", pady=2)

        frame = ttk.LabelFrame(self, text="Parâmetros")
        frame.pack(fill="x", padx=10, pady=10)

        self._campo(frame, "Tabela destino", self.tabela, 0)
        self._campo(frame, "Competência inicial", self.comp_ini, 1)
        self._campo(frame, "Competência final", self.comp_fim, 2)
        
        ttk.Label(frame, text="Máximo de linhas p/ arquivo").grid(row=3, column=0, sticky="w", padx=5,pady=5)
        ttk.Spinbox(
            frame,
            from_=1,
            to=1000,
            textvariable=self.max_linhas,
            width=38
        ).grid(row=3, column=1, padx=2)
        
        ttk.Checkbutton(frame, text="Usar IDENTITY_INSERT", variable=self.identity)\
            .grid(row=4, column=1, sticky="w", padx=5)

        ttk.Label(frame, text="Diretório saída").grid(row=5, column=0, sticky="w", padx=5)
        dir_frame = ttk.Frame(frame)
        dir_frame.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        ttk.Entry(dir_frame, textvariable=self.output_dir, width=35)\
            .pack(side="left", fill="x", expand=True)
        ttk.Button(dir_frame, text="Procurar", command=self._escolher_diretorio)\
            .pack(side="right")

        # ===== EXECUÇÃO =====
        self.btn_executar = ttk.Button(self, text="GERAR INSERTS", command=self._iniciar)
        self.btn_executar.pack(pady=10)

        self.progress = ttk.Progressbar(self, length=660)
        self.progress.pack(padx=10, pady=5)

        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log = tk.Text(log_frame, height=10, state="disabled")
        self.log.pack(fill="both", expand=True)

    def _campo(self, frame, label, var, row):
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=5,pady=5)
        ttk.Entry(frame, textvariable=var, width=40)\
            .grid(row=row, column=1, padx=2)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _escolher_diretorio(self):
        path = filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _adicionar(self):
        win = tk.Toplevel(self)
        win.title("Adicionar matrícula")
        win.geometry("260x150")

        mat = tk.StringVar()
        con = tk.StringVar()

        ttk.Label(win, text="Matrícula").pack(pady=5)
        ttk.Entry(win, textvariable=mat).pack()

        ttk.Label(win, text="Contrato").pack(pady=5)
        ttk.Entry(win, textvariable=con).pack()

        def salvar():
            try:
                self.tree.insert("", "end", values=(int(mat.get()), int(con.get())))
                self._salvar_config()
                win.destroy()
            except ValueError:
                messagebox.showerror("Erro", "Valores inválidos.")

        ttk.Button(win, text="Adicionar", command=salvar).pack(pady=10)

    def _remover(self):
        sel = self.tree.selection()
        if sel:
            self.tree.delete(sel[0])
            self._salvar_config()

    def _remover_todas(self):
        if not self.tree.get_children():
            return

        if messagebox.askyesno(
            "Confirmação",
            "Deseja remover TODAS as matrículas?"
        ):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self._salvar_config()

    # -------- CONEXÃO --------
    def _testar_conexao(self):
        try:
            conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={self.server.get()};"
                f"DATABASE={self.database.get()};"
                f"UID={self.username.get()};"
                f"PWD={self.password.get()}",
                timeout=5
            )
            conn.close()
            messagebox.showinfo("Conexão", "Conexão realizada com sucesso!")
            self._salvar_config()
        except Exception as e:
            messagebox.showerror("Erro de conexão", str(e))

    def _salvar_config(self):
        salvar_config({
            "server": self.server.get(),
            "database": self.database.get(),
            "username": self.username.get(),
            "password": self.password.get(),
            "output_dir": self.output_dir.get(),
            "tabela": self.tabela.get(),
            "max_linhas": int(self.max_linhas.get()),
            "identity": self.identity.get(),
            "matriculas": [
            list(self.tree.item(i)["values"])
            for i in self.tree.get_children()
        ]
        })

    def _iniciar(self):
        matriculas = [
            tuple(map(int, self.tree.item(i)["values"]))
            for i in self.tree.get_children()
        ]

        if not matriculas:
            messagebox.showwarning("Atenção", "Adicione ao menos uma matrícula.")
            return

        try:
            conn = pyodbc.connect(
                f"DRIVER={{SQL Server}};"
                f"SERVER={self.server.get()};"
                f"DATABASE={self.database.get()};"
                f"UID={self.username.get()};"
                f"PWD={self.password.get()}"
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na conexão:\n{e}")
            return

        self._salvar_config()
        self.btn_executar["state"] = "disabled"
        self.progress["value"] = 0
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        threading.Thread(
            target=self._executar,
            args=(conn, matriculas),
            daemon=True
        ).start()

    def _executar(self, conn, matriculas):
        try:
            gerar_inserts(
                conn,
                matriculas,
                self.tabela.get(),
                self.comp_ini.get(),
                self.comp_fim.get(),
                int(self.max_linhas.get()),
                self.identity.get(),
                self.output_dir.get(),
                self._log,
                lambda v: self.progress.config(value=v)
            )
            messagebox.showinfo("Sucesso", "Processo concluído.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))
        finally:
            conn.close()
            self.btn_executar["state"] = "normal"


if __name__ == "__main__":
    App().mainloop()
