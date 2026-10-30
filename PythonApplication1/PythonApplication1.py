import pandas as pd
import requests
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import queue
import threading
import sys

# Oculta o console quando o programa é executado no Windows.
# A aplicação passa a ficar disponível somente pela interface gráfica.
if sys.platform == "win32":
    import ctypes

    janela_console = ctypes.windll.kernel32.GetConsoleWindow()
    if janela_console:
        ctypes.windll.user32.ShowWindow(janela_console, 0)

# === CONFIGURAÇÕES DA API ===
API_KEY = "8ce9417ba73ead784237115d15b9d43e3ee94cdd"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7ImlkIjoxMDgzLCJ1dWlkIjoiZjk1YzU5ZmEtNmE3Yy00ZDBmLWFhZjgtZTYwOTY1YTg0MzNiIiwibmFtZSI6IkFuZGVyc29uIEFwYXJlY2lkbyBDb3V0byIsImVtYWlsIjoiYW5kZXJzb25jQGNvbXB0ay5jb20iLCJpbWFnZSI6Imh0dHBzOi8vZmlsZXMuY3Vyc2VkdWNhLmNvbS9iZmUwMjYxYi1jZjQwLTQ1MmYtYWM5Mi0zMjZmZjNmNGViOWYvOTJjYTUxN2Iud2VicCIsInJvbGVzIjpbIkFETUlOIl0sInRlbmFudHMiOlsxLDRdfSwiYWRtaW5fcGVybWlzc2lvbnMiOltdLCJ0ZW5hbnRfcGVybWlzc2lvbnMiOnt9LCJpc19jdXJzZWR1Y2FfYWRtaW4iOmZhbHNlLCJpYXQiOjE3OTMxMjMxNjYsImV4cCI6MTc5MzcyNzk2Nn0.6T5-5tVfc3tZ1wp9K0gnj04Z_O2UGr0VhG0opIgG9ko"

URL_BASE = "https://prof.curseduca.pro/api/v1/members"
def cadastrar_aluno(nome, email, password, group_id):
    headers = {
        "api_key": API_KEY,
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "name": str(nome).strip(),
        "email": str(email).strip(),
        "group": {
            "id": int(group_id)
        },
        "notifications": [{"type": "EMAIL"}]
    }

    # Adiciona a senha apenas se ela estiver preenchida na planilha
    if pd.notna(password) and str(password).strip():
        payload["password"] = str(password).strip()

    try:
        response = requests.post(URL_BASE, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 201:
            dados = response.json()
            return f"✅ Criado | ID: {dados.get('id')}"
        elif response.status_code == 409:
            return "⚠️ Erro (409): E-mail já cadastrado e ativo na plataforma."
        else:
            return f"❌ Erro ({response.status_code}): {response.text}"

    except Exception as e:
        return f"❌ Erro de conexão: {e}"

def processar_planilha(nome_arquivo, eventos):
    try:
        eventos.put(("log", f"Lendo o arquivo: {nome_arquivo}"))
        df = pd.read_excel(nome_arquivo)

        colunas_esperadas = {'nome', 'email', 'senha', 'grupo_de_acesso'}
        if not colunas_esperadas.issubset(df.columns):
            faltantes = colunas_esperadas - set(df.columns)
            raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(sorted(faltantes))}")

        total_alunos = len(df)
        eventos.put(("total", total_alunos))
        eventos.put(("log", f"Encontrados {total_alunos} alunos para cadastrar."))

        for index, linha in df.iterrows():
            nome = linha['nome']
            email = linha['email']
            senha = linha['senha']
            grupo = linha['grupo_de_acesso']

            if pd.isna(nome) or pd.isna(email) or pd.isna(grupo):
                mensagem = f"Linha {index + 1}: ignorada (campos obrigatórios ausentes)."
            else:
                eventos.put(("log", f"[{index + 1}/{total_alunos}] Processando: {nome} ({email})"))
                mensagem = cadastrar_aluno(nome, email, senha, grupo)

            eventos.put(("log", f"  ↳ {mensagem}"))
            eventos.put(("progress", index + 1))
            time.sleep(0.3)

        eventos.put(("log", "Processamento concluído com sucesso!"))
        eventos.put(("finished", True))

    except Exception as e:
        eventos.put(("error", str(e)))
        eventos.put(("finished", False))


class Aplicacao:
    def __init__(self, root):
        self.root = root
        self.root.title("Criação de membros")
        self.root.geometry("760x540")
        self.root.minsize(620, 420)
        self.eventos = queue.Queue()
        self.arquivo = tk.StringVar()
        self.status = tk.StringVar(value="Selecione uma planilha para começar.")

        self._criar_interface()
        self.root.after(100, self._processar_eventos)

    def _criar_interface(self):
        principal = ttk.Frame(self.root, padding=16)
        principal.pack(fill="both", expand=True)

        ttk.Label(principal, text="Criação de membros", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(principal, text="Selecione a planilha e acompanhe o processamento abaixo.").pack(anchor="w", pady=(2, 14))

        selecao = ttk.LabelFrame(principal, text="Planilha de entrada", padding=10)
        selecao.pack(fill="x")
        ttk.Entry(selecao, textvariable=self.arquivo, state="readonly").pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.botao_selecionar = ttk.Button(selecao, text="Selecionar...", command=self._selecionar_arquivo)
        self.botao_selecionar.pack(side="right")

        self.botao_iniciar = ttk.Button(principal, text="Iniciar criação", command=self._iniciar, state="disabled")
        self.botao_iniciar.pack(anchor="w", pady=12)

        self.progresso = ttk.Progressbar(principal, mode="determinate")
        self.progresso.pack(fill="x")
        ttk.Label(principal, textvariable=self.status).pack(anchor="w", pady=(4, 8))

        log_frame = ttk.LabelFrame(principal, text="Log do processamento", padding=6)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=14, state="disabled", wrap="word", background="#fafafa")
        barra = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=barra.set)
        self.log.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    def _selecionar_arquivo(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione a planilha de alunos",
            filetypes=[("Planilhas Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")]
        )
        if arquivo:
            self.arquivo.set(arquivo)
            self.botao_iniciar.config(state="normal")
            self.status.set("Planilha selecionada. Pronto para iniciar.")

    def _iniciar(self):
        self.botao_iniciar.config(state="disabled")
        self.botao_selecionar.config(state="disabled")
        self.progresso.config(value=0, maximum=1)
        self._escrever_log("Iniciando processamento...\n")
        threading.Thread(target=processar_planilha, args=(self.arquivo.get(), self.eventos), daemon=True).start()

    def _processar_eventos(self):
        try:
            while True:
                tipo, valor = self.eventos.get_nowait()
                if tipo == "log":
                    self._escrever_log(valor)
                elif tipo == "total":
                    self.progresso.config(maximum=max(valor, 1))
                    self.status.set(f"Processando {valor} membro(s)...")
                elif tipo == "progress":
                    self.progresso.config(value=valor)
                    self.status.set(f"Processados: {valor}/{int(self.progresso['maximum'])}")
                elif tipo == "error":
                    self._escrever_log(f"ERRO: {valor}")
                    messagebox.showerror("Erro no processamento", valor)
                elif tipo == "finished":
                    self.botao_selecionar.config(state="normal")
                    self.botao_iniciar.config(state="normal")
                    if valor:
                        self.status.set("Processamento concluído.")
                    else:
                        self.status.set("Processamento encerrado com erro.")
        except queue.Empty:
            pass
        self.root.after(100, self._processar_eventos)

    def _escrever_log(self, mensagem):
        self.log.config(state="normal")
        self.log.insert("end", mensagem + "\n")
        self.log.see("end")
        self.log.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    Aplicacao(root)
    root.mainloop()
