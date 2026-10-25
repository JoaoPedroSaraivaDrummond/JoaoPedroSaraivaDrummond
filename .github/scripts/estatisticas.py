#!/usr/bin/env python3
"""Gera os cards de estatísticas e de linguagens do perfil (SVG) a partir da API GraphQL do GitHub.

Usa só dados que o GitHub já mostra publicamente no perfil: o gráfico de contribuições
(que inclui a contagem anônima das contribuições privadas, porque a opção "Private
contributions" está ligada) e os PRs, issues, estrelas e linguagens dos repositórios públicos.
Basta o GITHUB_TOKEN do próprio Actions; nenhum token pessoal, nenhum acesso a código privado.

Uso: GITHUB_TOKEN=... python3 estatisticas.py <usuario> <pasta> ["título"]
Grava <pasta>/github-stats.svg e <pasta>/github-langs.svg, com o mesmo tamanho.
"""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

API = "https://api.github.com/graphql"
FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo (sem horário de verão)
LARGURA, ALTURA = 400, 265  # os dois cards ficam lado a lado no README, com a mesma altura
MAX_LINGUAGENS = 8


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
              nodes {
                stargazerCount
                languages(first: 20, orderBy: { field: SIZE, direction: DESC }) {
                  edges { size node { name color } }
                }
              }
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
        "linguagens": linguagens(perfil["repositories"]["nodes"]),
        **sequencias(dias, hoje),
        "atualizado": hoje,
    }


def linguagens(repositorios: list[dict]) -> list[tuple[str, str, float]]:
    """(nome, cor, %) das linguagens mais usadas nos repositórios públicos, por tamanho de código."""
    tamanhos: dict[str, int] = {}
    cores: dict[str, str] = {}
    for repositorio in repositorios:
        for aresta in repositorio["languages"]["edges"]:
            nome = aresta["node"]["name"]
            tamanhos[nome] = tamanhos.get(nome, 0) + aresta["size"]
            cores[nome] = aresta["node"]["color"] or "#858585"
    total = sum(tamanhos.values()) or 1
    maiores = sorted(tamanhos.items(), key=lambda item: item[1], reverse=True)[:MAX_LINGUAGENS]
    return [(nome, cores[nome], 100 * tamanho / total) for nome, tamanho in maiores]


def sequencias(dias: dict[str, int], hoje: date) -> dict:
    """Sequência atual (hoje ainda sem contribuição não quebra a de ontem) e a maior de todas."""
    ativos = {date.fromisoformat(d) for d, n in dias.items() if n > 0}
    maior = atual_corrida = 0
    for d in sorted(ativos):
        atual_corrida = atual_corrida + 1 if d - timedelta(days=1) in ativos else 1
        maior = max(maior, atual_corrida)
    # O calendário da API pode estar em UTC e já ter o dia seguinte ao de Brasília
    hoje = max([hoje, *ativos])
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


def cartao(titulo: str, corpo: str, rodape: str) -> str:
    """Moldura comum aos dois cards (tema tokyonight, sem borda)."""
    titulo, rodape = escape(titulo), escape(rodape)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{ALTURA}" viewBox="0 0 {LARGURA} {ALTURA}" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <style>
    .titulo {{ font: 600 15px 'Segoe UI', Ubuntu, sans-serif; fill: #70a5fd; }}
    .rotulo {{ font: 600 14px 'Segoe UI', Ubuntu, sans-serif; fill: #38bdae; }}
    .valor {{ font: 700 14px 'Segoe UI', Ubuntu, sans-serif; fill: #38bdae; }}
    .rodape {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #a9b1d6; opacity: 0.7; }}
  </style>
  <rect width="{LARGURA}" height="{ALTURA}" rx="6" fill="#1a1b27"/>
  <text class="titulo" x="25" y="36">{titulo}</text>
{corpo}
  <text class="rodape" x="25" y="{ALTURA - 15}">{rodape}</text>
</svg>
"""


def svg_estatisticas(e: dict, titulo: str) -> str:
    linhas = [
        ("Contribuições no último ano", numero(e["ultimo_ano"])),
        (f"Contribuições desde {e['primeiro_ano']}", numero(e["total"])),
        ("Sequência atual", dias_texto(e["sequencia_atual"])),
        ("Maior sequência", dias_texto(e["maior_sequencia"])),
        ("Pull requests", numero(e["prs"])),
        ("Issues", numero(e["issues"])),
        ("Estrelas", numero(e["estrelas"])),
    ]
    corpo = "\n".join(
        f'  <g transform="translate(25, {68 + 25 * i})">'
        f'<text class="rotulo">{escape(rotulo)}:</text>'
        f'<text class="valor" x="{LARGURA - 50}" text-anchor="end">{escape(valor)}</text></g>'
        for i, (rotulo, valor) in enumerate(linhas)
    )
    rodape = f"Inclui contribuições privadas (anônimas) · atualizado em {e['atualizado']:%d/%m/%Y}"
    return cartao(titulo, corpo, rodape)


def svg_linguagens(e: dict) -> str:
    largura_barra = LARGURA - 50
    partes, x = [], 25.0
    for _, cor, pct in e["linguagens"]:
        w = largura_barra * pct / 100
        partes.append(f'<rect x="{x:.2f}" y="56" width="{w:.2f}" height="10" fill="{cor}"/>')
        x += w
    barra = (
        '  <clipPath id="barra"><rect x="25" y="56" width="%d" height="10" rx="5"/></clipPath>\n'
        '  <rect x="25" y="56" width="%d" height="10" rx="5" fill="#2a2c3d"/>\n'
        '  <g clip-path="url(#barra)">%s</g>' % (largura_barra, largura_barra, "".join(partes))
    )
    itens = []
    for i, (nome, cor, pct) in enumerate(e["linguagens"]):
        coluna, linha = divmod(i, (MAX_LINGUAGENS + 1) // 2)
        x, y = 25 + coluna * (largura_barra // 2), 100 + linha * 32
        porcentagem = f"{pct:.1f}".replace(".", ",")
        itens.append(
            f'  <circle cx="{x + 5}" cy="{y - 5}" r="5" fill="{cor}"/>'
            f'<text class="rotulo" x="{x + 16}" y="{y}">{escape(nome)} '
            f'<tspan class="valor">{porcentagem}%</tspan></text>'
        )
    rodape = f"Repositórios públicos · atualizado em {e['atualizado']:%d/%m/%Y}"
    return cartao("Linguagens", barra + "\n" + "\n".join(itens), rodape)


def main() -> None:
    usuario, pasta = sys.argv[1], sys.argv[2]
    estatisticas = coletar(usuario)
    titulo = sys.argv[3] if len(sys.argv) > 3 else f"Estatísticas do GitHub de {estatisticas['nome']}"
    os.makedirs(pasta, exist_ok=True)
    for nome, conteudo in (
        ("github-stats.svg", svg_estatisticas(estatisticas, titulo)),
        ("github-langs.svg", svg_linguagens(estatisticas)),
    ):
        with open(os.path.join(pasta, nome), "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)
    # Só números que o perfil já mostra publicamente
    print({k: v for k, v in estatisticas.items() if k != "atualizado"})


if __name__ == "__main__":
    main()
