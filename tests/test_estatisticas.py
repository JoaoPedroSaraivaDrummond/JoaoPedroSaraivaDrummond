"""Testes do gerador dos cards (.github/scripts/estatisticas.py). Rodar: python3 -m unittest discover -s tests"""

import importlib.util
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest import mock

_caminho = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "estatisticas.py"
_spec = importlib.util.spec_from_file_location("estatisticas", _caminho)
est = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(est)


def dias(*datas: str) -> dict[str, int]:
    return {d: 1 for d in datas}


class Sequencias(unittest.TestCase):
    def test_hoje_sem_contribuicao_nao_quebra_a_sequencia_de_ontem(self):
        r = est.sequencias(dias("2026-10-23", "2026-10-24", "2026-10-25"), date(2026, 10, 26))
        self.assertEqual(r["sequencia_atual"], 3)

    def test_dia_vazio_no_meio_quebra_a_sequencia(self):
        r = est.sequencias(dias("2026-10-20", "2026-10-21", "2026-10-25", "2026-10-26"), date(2026, 10, 26))
        self.assertEqual(r, {"sequencia_atual": 2, "maior_sequencia": 2})

    def test_dois_dias_sem_contribuicao_zeram_a_atual(self):
        r = est.sequencias(dias("2026-10-20", "2026-10-21", "2026-10-22"), date(2026, 10, 26))
        self.assertEqual(r, {"sequencia_atual": 0, "maior_sequencia": 3})

    def test_calendario_em_utc_ja_no_dia_seguinte(self):
        # A API já registrou o dia 27 (UTC) enquanto em Brasília ainda é 26
        r = est.sequencias(dias("2026-10-25", "2026-10-26", "2026-10-27"), date(2026, 10, 26))
        self.assertEqual(r["sequencia_atual"], 3)

    def test_dias_com_zero_contribuicoes_nao_contam(self):
        r = est.sequencias({"2026-10-25": 0, "2026-10-26": 2}, date(2026, 10, 26))
        self.assertEqual(r["sequencia_atual"], 1)


class Linguagens(unittest.TestCase):
    def repo(self, *pares):
        return {"languages": {"edges": [{"size": t, "node": {"name": n, "color": c}} for n, c, t in pares]}}

    def test_soma_entre_repositorios_e_calcula_porcentagem(self):
        r = est.linguagens([self.repo(("Python", "#3572A5", 300)), self.repo(("Python", "#3572A5", 100), ("CSS", "#563d7c", 100))])
        self.assertEqual(r, [("Python", "#3572A5", 80.0), ("CSS", "#563d7c", 20.0)])

    def test_mostra_no_maximo_as_8_maiores(self):
        r = est.linguagens([self.repo(*[(f"L{i}", "#000000", i + 1) for i in range(12)])])
        self.assertEqual(len(r), est.MAX_LINGUAGENS)
        self.assertEqual(r[0][0], "L11")

    def test_sem_repositorios_nao_divide_por_zero(self):
        self.assertEqual(est.linguagens([]), [])

    def test_cor_ausente_ou_estranha_vira_cinza(self):
        r = est.linguagens([self.repo(("A", None, 1), ("B", '#fff" onload="x', 1), ("C", "#ABC", 1))])
        self.assertEqual({nome: cor for nome, cor, _ in r}, {"A": "#858585", "B": "#858585", "C": "#ABC"})


class Formatacao(unittest.TestCase):
    def test_milhar_com_ponto(self):
        self.assertEqual(est.numero(1234567), "1.234.567")

    def test_dia_no_singular_e_no_plural(self):
        self.assertEqual(est.dias_texto(1), "1 dia")
        self.assertEqual(est.dias_texto(0), "0 dias")
        self.assertEqual(est.dias_texto(1200), "1.200 dias")


class Svg(unittest.TestCase):
    dados = {
        "ultimo_ano": 1500, "primeiro_ano": 2021, "total": 4000, "sequencia_atual": 3, "maior_sequencia": 40,
        "prs": 12, "issues": 4, "estrelas": 7, "atualizado": date(2026, 10, 26),
        "linguagens": [("C++ & <script>", "#f34b7d", 60.0), ("Python", "#3572A5", 40.0)],
    }

    def test_card_de_estatisticas_e_xml_valido_e_escapa_o_titulo(self):
        svg = est.svg_estatisticas(self.dados, 'Título com <tags> & "aspas"')
        raiz = ET.fromstring(svg)
        self.assertEqual(raiz.get("width"), str(est.LARGURA))
        self.assertIn("Título com <tags> &", "".join(raiz.itertext()))
        self.assertIn("1.500", svg)
        self.assertIn("26/10/2026", svg)

    def test_card_de_linguagens_escapa_o_nome_e_usa_virgula_decimal(self):
        svg = est.svg_linguagens(self.dados)
        ET.fromstring(svg)
        self.assertNotIn("<script>", svg)
        self.assertIn("60,0%", svg)

    def test_os_dois_cards_tem_o_mesmo_tamanho(self):
        a = ET.fromstring(est.svg_estatisticas(self.dados, "t"))
        b = ET.fromstring(est.svg_linguagens(self.dados))
        self.assertEqual((a.get("width"), a.get("height")), (b.get("width"), b.get("height")))


class Coletar(unittest.TestCase):
    def test_ultimo_ano_soma_so_os_365_dias_ate_hoje(self):
        respostas = [
            {"user": {"name": None, "contributionsCollection": {"contributionYears": [2025]},
                      "repositories": {"nodes": [{"stargazerCount": 2, "languages": {"edges": []}}]}}},
            {"user": {"contributionsCollection": {
                "totalPullRequestContributions": 1, "totalIssueContributions": 0,
                "contributionCalendar": {"totalContributions": 7, "weeks": [{"contributionDays": [
                    {"date": "2025-10-26", "contributionCount": 5},  # exatamente 365 dias antes: fora
                    {"date": "2025-10-27", "contributionCount": 2},
                ]}]}}}},
        ]
        with mock.patch.object(est, "graphql", side_effect=respostas), \
             mock.patch.object(est, "datetime") as dt:
            dt.now.return_value.date.return_value = date(2026, 10, 26)
            r = est.coletar("alguem")
        self.assertEqual((r["nome"], r["total"], r["ultimo_ano"], r["estrelas"]), ("alguem", 7, 2, 2))


if __name__ == "__main__":
    unittest.main()
