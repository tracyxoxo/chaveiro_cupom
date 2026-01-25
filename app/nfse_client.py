import re
from datetime import datetime
from bs4 import BeautifulSoup
import requests


class NFSeClient:
    def __init__(self):
        self.session = requests.Session()
        self.ultima_nota_id = None
        self.tomador = None

    # -----------------------------------------------------
    # LOGIN
    # -----------------------------------------------------
    def login(self, inscricao, senha):
        url = "https://www.nfse.gov.br/EmissorNacional/Login"

        resp = self.session.get(url)

        soup = BeautifulSoup(resp.text, "html.parser")

        token = soup.find("input", {"name": "__RequestVerificationToken"})
        if not token:
            raise Exception("Token antiforgery não encontrado")

        payload = {
            "__RequestVerificationToken": token["value"],
            "Inscricao": inscricao,
            "Senha": senha
        }

        r = self.session.post(url, data=payload)

        if "Sair" not in r.text:
            raise Exception("Falha no login")

        print("Login realizado")

    # -----------------------------------------------------
    # ABRIR CONTEXTO DPS
    # -----------------------------------------------------
    def abrir_emissao(self, data: datetime):
        url = "https://www.nfse.gov.br/EmissorNacional/DPS/Simplificada"

        params = {
            "data": data.strftime("%Y-%m-%d")
        }

        r = self.session.get(url, params=params)

        if r.status_code != 200:
            raise Exception("Erro ao abrir DPS")

        print("Contexto da DPS criado")

    # -----------------------------------------------------
    # LOOKUP TOMADOR
    # -----------------------------------------------------
    def lookup_tomador(self, cpf_cnpj):
        url = (
            "https://www.nfse.gov.br/"
            "emissornacional/api/EmissaoDPS/RecuperarInfoInscricao/"
            f"{cpf_cnpj}?data={datetime.now().strftime('%Y-%m-%d')}"
        )

        r = self.session.get(url)

        if r.status_code != 200:
            raise Exception("Erro ao buscar tomador")

        data = r.json()

        self.tomador = {
            "inscricao": data.get("inscricao", cpf_cnpj),
            "nome": data.get("nomerazaosocial", ""),
            "cpf_cnpj": cpf_cnpj
        }

        print(f"Tomador: {self.tomador['nome']}")

    # -----------------------------------------------------
    # EMITIR NOTA
    # -----------------------------------------------------
    def emitir_nota(self, dados, data_competencia: datetime):
        url = "https://www.nfse.gov.br/EmissorNacional/DPS/Simplificada"

        # Valida se tem tomador
        if not self.tomador:
            raise Exception("Tomador não foi carregado. Execute lookup_tomador() antes.")

        # Valida IdServicoFavorito
        id_servico = dados.get("IdServicoFavorito")
        if not id_servico or id_servico == "00000000-0000-0000-0000-000000000000":
            raise Exception(
                "IdServicoFavorito é obrigatório e deve ser um GUID válido de um serviço favorito cadastrado. "
                "Cadastre um serviço em 'Serviços Favoritos' no portal e use o ID dele."
            )

        # Formata valor monetário (brasileiro: vírgula como decimal)
        valor_servico = str(dados.get("ValorServico", "")).replace(".", ",")

        # Monta payload completo
        payload = {
            "EmitenteEhMEINaDataAtual": dados.get("EmitenteEhMEINaDataAtual", "True"),
            "DataCompetencia": data_competencia.strftime("%d/%m/%Y %H:%M:%S"),
            "InscricaoCliente": self.tomador["cpf_cnpj"],
            "NomeCliente": self.tomador["nome"],
            "IdServicoFavorito": id_servico,
            "Descricao": dados.get("Descricao", ""),
            "ValorServico": valor_servico,
            "HaRetencaoISSQNNaFonte": dados.get("HaRetencaoISSQNNaFonte", "0"),
            "AliquotaRetencao": "",
            "ValorDeRetencao": "",
            # Obra
            "Obra.EhObrigatorio": "False",
            "Obra.CodigoObra": "",
            "Obra.CodigoMunicipioPrestacao": "",
            "Obra.CEP": "",
            "Obra.CodigoMunicipio": "",
            "Obra.NomeMunicipio": "",
            "Obra.Bairro": "",
            "Obra.Logradouro": "",
            "Obra.Numero": "",
            "Obra.Complemento": "",
            # AtvEvento
            "AtvEvento.EhObrigatorio": "False",
            "AtvEvento.DataInicial": "",
            "AtvEvento.DataFinal": "",
            "AtvEvento.Identificacao": "",
            "AtvEvento.CodigoMunicipioPrestacao": "",
            "AtvEvento.CEP": "",
            "AtvEvento.CodigoMunicipio": "",
            "AtvEvento.NomeMunicipio": "",
            "AtvEvento.Bairro": "",
            "AtvEvento.Logradouro": "",
            "AtvEvento.Numero": "",
            "AtvEvento.Complemento": "",
            # InfoComplementar
            "InfoComplementar.EhObrigatorio": "False",
            "InfoComplementar.CodigoMunicipio": "",
        }

        print(f"📤 Enviando nota fiscal...")
        print(f"   Tomador: {self.tomador['nome']}")
        print(f"   Valor: R$ {valor_servico}")
        print(f"   Data: {payload['DataCompetencia']}")
        
        r = self.session.post(url, data=payload)

        soup = BeautifulSoup(r.text, "html.parser")

        # ❌ validação do backend
        erro = soup.find("div", class_="validation-summary-errors")
        if erro:
            raise Exception(
                "Erro de validação na emissão:\n"
                + erro.get_text(strip=True)
            )

        # ✅ captura link da nota
        btn = soup.find("a", id="btnDownloadDANFSE")
        
        if not btn:
            # Tenta outros seletores comuns
            btn = soup.find("a", href=re.compile(r"/Download/DANFSe/"))
            
        if not btn:
            # Salva HTML para debug
            with open("resposta_emissao_debug.html", "w", encoding="utf-8") as f:
                f.write(r.text)
            raise Exception(
                "A requisição retornou 200, mas nenhum link de download foi encontrado. "
                "Verifique o arquivo 'resposta_emissao_debug.html' para mais detalhes."
            )

        href = btn.get("href")
        self.ultima_nota_id = href.split("/")[-1]

        print(f"Nota emitida com sucesso (ID: {self.ultima_nota_id})")

    # -----------------------------------------------------
    # DOWNLOAD DANFSE
    # -----------------------------------------------------
    def baixar_danfse(self, nome_arquivo="DANFSE.pdf"):
        if not self.ultima_nota_id:
            raise Exception("Nenhuma nota emitida")

        url = (
            "https://www.nfse.gov.br"
            f"/EmissorNacional/Notas/Download/DANFSe/{self.ultima_nota_id}"
        )

        r = self.session.get(url)

        if r.status_code != 200:
            raise Exception(f"Erro ao baixar DANFSe: {r.status_code}")

        with open(nome_arquivo, "wb") as f:
            f.write(r.content)

        print(f"DANFSe baixada: {nome_arquivo}")