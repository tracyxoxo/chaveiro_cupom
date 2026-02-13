import argparse
from datetime import datetime
from nfse_client import NFSeClient


def main():
    parser = argparse.ArgumentParser(
        description="Emissor de NFSe (Emissor Nacional)"
    )

    parser.add_argument("--inscricao", required=True)
    parser.add_argument("--senha", required=True)
    parser.add_argument("--tomador", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--valor", required=True)
    parser.add_argument("--descricao", required=True, help="Descrição do serviço prestado")
    
    parser.add_argument(
        "--servico-id", 
        required=True,
        help="GUID do serviço favorito (cadastre em 'Serviços Favoritos' no portal)"
    )

    args = parser.parse_args()

    data_competencia = datetime.strptime(args.data, "%Y-%m-%d")

    tomador = (
        args.tomador
        .replace(".", "")
        .replace("-", "")
        .replace("/", "")
    )

    client = NFSeClient()

    client.login(args.inscricao, args.senha)
    client.abrir_emissao(data_competencia)
    client.lookup_tomador(tomador)

    dados = {
        "EmitenteEhMEINaDataAtual": "True",
        "IdServicoFavorito": args.servico_id,
        "ValorServico": args.valor,
        "Descricao": args.descricao,
        "HaRetencaoISSQNNaFonte": "0"
    }

    client.emitir_nota(dados, data_competencia)
    client.baixar_danfse()


if __name__ == "__main__":
    main()