# Avos · Painel da Diretoria

Dashboard executivo com o resumo das abas visíveis de três planilhas:

| Planilha | Abas resumidas |
|---|---|
| Análise de Caixa Avos | Painel executivo, Fluxo grupo, DRE por empreendimento, Intercompany, Investimento, Sócios e Terceiros, Impostos |
| Análise de VGV | Dashboard, Resumo |
| Contas a receber geral | 1_Dashboard, 2_Carteira, 3_Cobranca, 4_Fluxo, Base_Resumo |

Páginas do painel: Visão geral · Caixa e resultado · DRE Bambuzal · VGV e vendas · Contas a receber · Cobrança · Sócios, grupo e impostos.

## Acesso

A página pede **usuário e senha** (fornecidos à diretoria em separado). Os números **não ficam em texto aberto** no repositório: o arquivo `dados/dados.enc.js` é criptografado com AES-256-GCM, e a chave é derivada do usuário + senha (PBKDF2-SHA256, 600.000 iterações). Sem a senha correta, o navegador não consegue ler nada.

## Publicar no GitHub Pages (uma vez)

1. Crie um repositório novo no GitHub (ex.: `painel-diretoria`).
2. Envie **todos os arquivos desta pasta** (arraste em *Add file → Upload files* ou use `git push`). Mantenha a estrutura de pastas.
3. Em **Settings → Pages**, escolha *Deploy from a branch*, branch `main`, pasta `/ (root)` e salve.
4. Em 1–2 minutos o link aparece no topo da mesma tela: `https://SEU-USUARIO.github.io/painel-diretoria/`.

## Atualizar os números (todo mês)

```bash
pip install pyxlsb openpyxl cryptography
python ferramentas/atualizar_dados.py "Analise_Caixa_Avos.xlsb" "Analise_VGV.xlsx" "Contas_a_receber_geral.xlsb" --usuario avos --senha SUA_SENHA
```

O script lê as mesmas abas e células, recria `dados/dados.enc.js` e basta enviar esse arquivo ao GitHub. Para **trocar a senha**, rode o script com a nova senha. Se a estrutura das planilhas mudar (linhas ou colunas novas), o script precisa ser ajustado.

> **Nunca** envie as planilhas ao repositório (o `.gitignore` já bloqueia `.xlsb`/`.xlsx`).

## Estrutura

```
index.html                 tela de login + painel
assets/app.js              descriptografia, navegação e gráficos
assets/style.css           visual
assets/chart.umd.min.js    Chart.js 4 (local, sem depender de CDN)
assets/logo-avos-*.png     logo
dados/dados.enc.js         dados criptografados
ferramentas/atualizar_dados.py
```
