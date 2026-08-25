# News_Anvisa_Scraper
O ANVISA Data Scraper é uma solução automatizada para extração, estruturação e monitoramento de dados regulatórios públicos da Agência Nacional de Vigilância Sanitária. O software transforma bases fragmentadas e portais de consulta complexos em pipelines de dados legíveis por máquina, otimizados para inteligência de mercado, compliance e análise técnica.


🚀 Como Usar — Guia de Instalação e Automação
O ANVISA Data Scraper foi projetado para rodar de forma 100% autônoma em ambientes Windows, sem a necessidade de compilação ou instalação prévia de dependências.

📦 Passo 1: Baixar a Aplicação
Acesse a aba de Releases na página do repositório.

Faça o download da versão mais recente do executável (ex. anvisa_scrapper_v1.0.exe


⏱️ Passo 2: Agendar Execução no Windows
Para garantir que a base de dados permaneça atualizada sem intervenção manual, configure o Agendador de Tarefas do Windows:

🛠️ Configuração Passo a Passo
Pressione Win + R, digite taskschd.msc e pressione Enter.

No painel de Ações (à direita), clique em Criar Tarefa... (ou Create Task).

Na aba Geral:

Nome: ANVISA Data Scrapper Sync

Marque a opção: Executar estando o usuário conectado ou não

Na aba Gatilhos (Triggers):

Clique em Novo... e escolha a frequência (ex: Diariamente às 03:00 AM).

Na aba Ações (Actions):

Clique em Novo... e selecione Iniciar um programa.

Programa/script: C:\Downloads/scraper_anvisa.exe

Clique em Salvar.

