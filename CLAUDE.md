# CLAUDE.md — JoaoPedroSaraivaDrummond (README do perfil)

Repositório especial do GitHub: o `README.md` daqui aparece no topo de github.com/JoaoPedroSaraivaDrummond. Só funciona porque o repositório tem **exatamente** o nome do usuário e é **público**; não renomeie.

- **Visibilidade:** **PÚBLICO**. O Claude pode commitar e dar push sem pedir confirmação, sempre na `dev`. Antes de cada commit, revise `git diff --cached`: nada de dados pessoais, tokens ou caminhos locais.
- **Branches:** `dev` é a padrão no GitHub (é dela que o perfil lê o README); `main` só recebe merge quando o usuário pedir.
- **Conteúdo:** só o README. Se algum projeto privado for citado, vai sem link e sem domínio. Nada de dados pessoais além do LinkedIn e do e-mail já publicados.
- **Cards de estatísticas e linguagens:** gerados por `.github/scripts/estatisticas.py` no workflow `snake.yml` (a cada 6 h), com o mesmo tamanho e tema, e publicados na branch `output` junto com a cobrinha. As linguagens contam só os repositórios públicos. Usa só o `GITHUB_TOKEN` do Actions e dados que o perfil já mostra publicamente (inclui a contagem anônima das contribuições privadas). Não troque por uma solução que exija token pessoal: o repositório é público e os logs das Actions também.
- **Ícones de IA:** `assets/ferramentas-ia.svg` (Gemini, Claude, ChatGPT e DeepSeek) imita o estilo do skillicons.dev, que não tem essas marcas. Os desenhos vêm do Simple Icons (CC0); para trocar um ícone, substitua o `<path>` do bloco correspondente.
- O README não lista projetos (a seção de projetos foi removida); os repositórios públicos aparecem nos "Pinned" do perfil.

## Conta de teste (login)

Hoje esta aplicação não tem login. Se passar a ter login ou cadastro, o Claude usa a conta **`admin@claude.local` / `admin123`** para entrar, testar e tirar prints. Se ela ainda não existir no banco de desenvolvimento, crie pelo cadastro da própria aplicação (ou pelo seed). A conta é só de desenvolvimento: nunca a crie nem a deixe ativa em produção.

## Versionamento

Todos os projetos seguem **MAJOR.MINOR.PATCH** (MAJOR: mudança incompatível; MINOR: funcionalidade nova compatível; PATCH: correção de bug; ao subir um número, os da direita voltam a zero). Este repositório é só um README, sem `package.json`, então não tem número de versão. Ao citar a versão de algum projeto no README, use esse formato.
