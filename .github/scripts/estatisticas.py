#!/usr/bin/env python3
"""Gera o card de estatísticas do perfil (SVG) a partir da API GraphQL do GitHub.

Usa só dados que o GitHub já mostra publicamente no perfil: o gráfico de contribuições
(que inclui a contagem anônima das contribuições privadas, porque a opção "Private
contributions" está ligada) e os PRs, issues e estrelas dos repositórios públicos.
Basta o GITHUB_TOKEN do próprio Actions; nenhum token pessoal, nenhum acesso a código privado.

Uso: GITHUB_TOKEN=... python3 estatisticas.py <usuario> <saida.svg> ["título"]
"""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

API = "https://api.github.com/graphql"
FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo (sem horário de verão)


def graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
            "User-Agent": "estatisticas-do-perfil",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise SystemExit(f"Erro da API: {data['errors'][0].get('message')}")
    return data["data"]


def coletar(usuario: str) -> dict:
    perfil = graphql(
        """query($login: String!) {
          user(login: $login) {
            name
            contributionsCollection { contributionYears }
            repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
              nodes { stargazerCount }
            }
          }
        }""",
        {"login": usuario},
    )["user"]

    total = prs = issues = 0
    dias: dict[str, int] = {}
    for ano in perfil["contributionsCollection"]["contributionYears"]:
        colecao = graphql(
            """query($login: String!, $de: DateTime!, $ate: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $de, to: $ate) {
                  totalPullRequestContributions
                  totalIssueContributions
                  contributionCalendar {
                    totalContributions
                    weeks { contributionDays { date contributionCount } }
                  }
                }
              }
            }""",
            {"login": usuario, "de": f"{ano}-01-01T00:00:00Z", "ate": f"{ano}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]
        total += colecao["contributionCalendar"]["totalContributions"]
        prs += colecao["totalPullRequestContributions"]
        issues += colecao["totalIssueContributions"]
        for semana in colecao["contributionCalendar"]["weeks"]:
            for dia in semana["contributionDays"]:
                dias[dia["date"]] = dia["contributionCount"]

    hoje = datetime.now(FUSO).date()
    ultimo_ano = sum(n for d, n in dias.items() if hoje - timedelta(days=365) < date.fromisoformat(d) <= hoje)
    return {
        "nome": perfil["name"] or usuario,
        "primeiro_ano": min(perfil["contributionsCollection"]["contributionYears"]),
        "total": total,
        "ultimo_ano": ultimo_ano,
        "prs": prs,
        "issues": issues,
        "estrelas": sum(r["stargazerCount"] for r in perfil["repositories"]["nodes"]),
        **sequencias(dias, hoje),
        "atualizado": hoje,
    }


def sequencias(dias: dict[str, int], hoje: date) -> dict:
    """Sequência atual (hoje ainda sem contribuição não quebra a de ontem) e a maior de todas."""
    ativos = {date.fromisoformat(d) for d, n in dias.items() if n > 0}
    maior = atual_corrida = 0
    for d in sorted(ativos):
        atual_corrida = atual_corrida + 1 if d - timedelta(days=1) in ativos else 1
        maior = max(maior, atual_corrida)
    dia = hoje if hoje in ativos else hoje - timedelta(days=1)
    atual = 0
    while dia in ativos:
        atual += 1
        dia -= timedelta(days=1)
    return {"sequencia_atual": atual, "maior_sequencia": maior}


def numero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def dias_texto(n: int) -> str:
    return f"{numero(n)} dia" if n == 1 else f"{numero(n)} dias"


def svg(e: dict, titulo: str) -> str:
    linhas = [
        ("Contribuições no último ano", numero(e["ultimo_ano"])),
        (f"Contribuições desde {e['primeiro_ano']}", numero(e["total"])),
        ("Sequência atual", dias_texto(e["sequencia_atual"])),
        ("Maior sequência", dias_texto(e["maior_sequencia"])),
        ("Pull requests", numero(e["prs"])),
        ("Issues", numero(e["issues"])),
        ("Estrelas", numero(e["estrelas"])),
    ]
    altura = 70 + 25 * len(linhas) + 20
    corpo = "\n".join(
        f'    <g transform="translate(25, {70 + 25 * i})">'
        f'<text class="rotulo">{escape(rotulo)}:</text>'
        f'<text class="valor" x="417" text-anchor="end">{escape(valor)}</text></g>'
        for i, (rotulo, valor) in enumerate(linhas)
    )
    titulo = escape(titulo)
    rodape = escape(f"Inclui contribuições privadas (anônimas) · atualizado em {e['atualizado']:%d/%m/%Y}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="467" height="{altura}" viewBox="0 0 467 {altura}" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <style>
    .titulo {{ font: 600 17px 'Segoe UI', Ubuntu, sans-serif; fill: #70a5fd; }}
    .rotulo {{ font: 600 14px 'Segoe UI', Ubuntu, sans-serif; fill: #38bdae; }}
    .valor {{ font: 700 14px 'Segoe UI', Ubuntu, sans-serif; fill: #38bdae; }}
    .rodape {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #a9b1d6; opacity: 0.7; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" width="466" height="{altura - 1}" fill="#1a1b27" stroke="#e4e2e2" stroke-opacity="0"/>
  <text class="titulo" x="25" y="38">{titulo}</text>
{corpo}
  <text class="rodape" x="25" y="{altura - 15}">{rodape}</text>
</svg>
"""


def main() -> None:
    usuario, saida = sys.argv[1], sys.argv[2]
    estatisticas = coletar(usuario)
    titulo = sys.argv[3] if len(sys.argv) > 3 else f"Estatísticas do GitHub de {estatisticas['nome']}"
    os.makedirs(os.path.dirname(saida) or ".", exist_ok=True)
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write(svg(estatisticas, titulo))
    # Só números que o perfil já mostra publicamente
    print({k: v for k, v in estatisticas.items() if k != "atualizado"})


if __name__ == "__main__":
    main()
