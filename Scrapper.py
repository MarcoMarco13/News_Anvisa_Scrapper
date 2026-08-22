import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import sys
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Tenta importar a biblioteca de notificações
try:
    from plyer import notification
    NOTIFICACOES_DISPONIVEIS = True
except ImportError:
    NOTIFICACOES_DISPONIVEIS = False

class ScraperAnvisa:
    """
    Classe para gerenciar o scraping de notícias da Anvisa
    """
    
    def __init__(self, modo_silencioso=False):
        self.modo_silencioso = modo_silencioso
        self.url = "https://www.gov.br/anvisa/pt-br"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Configuração de caminhos absolutos
        if getattr(sys, 'frozen', False):
            diretorio_base = os.path.dirname(sys.executable)
        else:
            diretorio_base = os.path.dirname(os.path.abspath(__file__))
        
        self.pasta_logs = os.path.join(diretorio_base, "logs")
        os.makedirs(self.pasta_logs, exist_ok=True)
        self.arquivo_log = os.path.join(self.pasta_logs, "ultimas_noticias.txt")
        
        self.ultimas_noticias = []
        
        # Configura sessão com retry automático
        self.sessao = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.sessao.mount('http://', adapter)
        self.sessao.mount('https://', adapter)
        
        # Mensagem inicial (apenas se não estiver em modo silencioso)
        if not self.modo_silencioso and not NOTIFICACOES_DISPONIVEIS:
            print("⚠️ Biblioteca 'plyer' não encontrada. Instale com: pip install plyer")
            print("ℹ️ As notificações serão desabilitadas.")
    
    def log(self, mensagem, tipo="info"):
        """Função para logar sem poluir o console em modo silencioso"""
        if not self.modo_silencioso:
            print(mensagem)
        
        # Opcional: Salvar em arquivo de log separado
        # with open(os.path.join(self.pasta_logs, "execucao.log"), "a", encoding="utf-8") as f:
        #     f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensagem}\n")
    
    def obter_noticias(self, quantidade=3):
        """
        Obtém as últimas N notícias do site da Anvisa.
        
        Args:
            quantidade (int): Número de notícias a serem retornadas (padrão: 3)
        
        Returns:
            list: Lista de dicionários com as notícias
        """
        try:
            self.log(f"🔍 Coletando as últimas {quantidade} notícias da Anvisa...")
            response = self.sessao.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # SELETOR: Procura por tags <a> com as classes do padrão identificado
            noticias = soup.select('a[class*="DefaultTemplate-module"]')
            
            # Filtra apenas os links que são de notícias
            noticias_filtradas = []
            for noticia in noticias:
                href = noticia.get('href', '')
                if '/noticias-anvisa/' in href:
                    noticias_filtradas.append(noticia)
            
            # Fallback se o seletor principal não funcionar
            if not noticias_filtradas:
                self.log("Tentando seletor alternativo...")
                noticias_filtradas = soup.select('a[href*="noticias-anvisa"]')
            
            if not noticias_filtradas:
                self.log("❌ Nenhuma notícia encontrada.")
                return []
            
            # Pega as primeiras N notícias
            noticias_selecionadas = noticias_filtradas[:quantidade]
            
            resultados = []
            for i, noticia in enumerate(noticias_selecionadas, 1):
                # Extrai o link
                link = noticia.get('href')
                if link and not link.startswith('http'):
                    link = f"https://www.gov.br{link}"
                
                # Extrai o título
                titulo_elemento = noticia.select_one('h2')
                if titulo_elemento:
                    titulo = titulo_elemento.text.strip()
                else:
                    # Fallback: pega o texto completo
                    texto_completo = noticia.text.strip()
                    titulo = ' '.join(texto_completo.split()[:15]) + '...' if len(texto_completo.split()) > 15 else texto_completo
                
                # Tenta extrair a data
                data = "Data não disponível"
                data_elemento = noticia.find_parent().select_one('[class*="data"], [class*="date"], [class*="publicado"]')
                if data_elemento:
                    data = data_elemento.text.strip()
                
                # Tenta extrair a descrição
                descricao = ""
                desc_elemento = noticia.select_one('p')
                if desc_elemento:
                    descricao = desc_elemento.text.strip()
                
                resultados.append({
                    'posicao': i,
                    'titulo': titulo,
                    'link': link,
                    'data_publicacao': data,
                    'descricao': descricao,
                    'data_coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            self.ultimas_noticias = resultados
            self.log(f"✅ {len(resultados)} notícias coletadas com sucesso!")
            return resultados
            
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Erro na requisição: {e}")
            return []
        except Exception as e:
            self.log(f"❌ Erro inesperado: {e}")
            return []
    
    def verificar_novas_noticias(self, noticias_atuais):
        """
        Verifica se há notícias novas comparando com o arquivo de log.
        
        Args:
            noticias_atuais (list): Lista de notícias atuais
        
        Returns:
            list: Lista de notícias que ainda não foram salvas
        """
        try:
            with open(self.arquivo_log, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            novas_noticias = []
            for noticia in noticias_atuais:
                if noticia['link'] not in conteudo:
                    novas_noticias.append(noticia)
            
            return novas_noticias
        except FileNotFoundError:
            # Se o arquivo não existe, todas são novas
            return noticias_atuais
        except Exception as e:
            self.log(f"⚠️ Erro ao verificar notícias novas: {e}")
            return noticias_atuais
    
    def salvar_noticias(self, noticias):
        """
        Salva as notícias em um arquivo de log.
        
        Args:
            noticias (list): Lista de notícias para salvar
        """
        try:
            with open(self.arquivo_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{'#'*60}\n")
                f.write(f"📅 COLETA EM: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'#'*60}\n")
                
                for noticia in noticias:
                    f.write(f"\n📰 NOTÍCIA #{noticia['posicao']}\n")
                    f.write(f"Título: {noticia['titulo']}\n")
                    f.write(f"Link: {noticia['link']}\n")
                    f.write(f"Data de publicação: {noticia['data_publicacao']}\n")
                    if noticia['descricao']:
                        f.write(f"Descrição: {noticia['descricao']}\n")
                    f.write(f"{'-'*40}\n")
            
            self.log(f"💾 {len(noticias)} notícias salvas em '{self.arquivo_log}'")
            
        except Exception as e:
            self.log(f"❌ Erro ao salvar notícias: {e}")
    
    def enviar_notificacao(self, noticias):
        """
        Envia uma notificação para o sistema operacional.
        
        Args:
            noticias (list): Lista de notícias novas para notificar
        """
        if not NOTIFICACOES_DISPONIVEIS:
            return
        
        if not noticias:
            return
        
        try:
            # Prepara a mensagem
            if len(noticias) == 1:
                titulo = "📰 Nova Notícia da Anvisa!"
                mensagem = noticias[0]['titulo']
                if len(mensagem) > 100:
                    mensagem = mensagem[:97] + "..."
            else:
                titulo = f"📰 {len(noticias)} Novas Notícias da Anvisa!"
                mensagem = "Últimas:\n"
                for i, noticia in enumerate(noticias[:3], 1):
                    titulo_curto = noticia['titulo']
                    if len(titulo_curto) > 50:
                        titulo_curto = titulo_curto[:47] + "..."
                    mensagem += f"{i}. {titulo_curto}\n"
            
            # Envia a notificação
            notification.notify(
                title=titulo,
                message=mensagem,
                timeout=10,
                app_name="Scraper Anvisa"
            )
            self.log("🔔 Notificação enviada com sucesso!")
            
        except Exception as e:
            self.log(f"❌ Erro ao enviar notificação: {e}")
    
    def executar(self, quantidade=3, enviar_notificacoes=True):
        """
        Executa o fluxo completo do scraper.
        
        Args:
            quantidade (int): Número de notícias a serem coletadas
            enviar_notificacoes (bool): Se deve enviar notificações para novas notícias
        
        Returns:
            dict: Resumo da execução
        """
        self.log("\n" + "="*60)
        self.log("🚀 INICIANDO SCRAPER DA ANVISA")
        self.log("="*60)
        
        # Coleta as notícias
        noticias = self.obter_noticias(quantidade)
        
        if not noticias:
            return {
                'sucesso': False,
                'mensagem': 'Nenhuma notícia encontrada',
                'total_noticias': 0,
                'novas_noticias': 0
            }
        
        # Verifica quais são novas
        novas = self.verificar_novas_noticias(noticias)
        
        # Mostra as notícias na tela (apenas se não for silencioso)
        if not self.modo_silencioso:
            self.mostrar_noticias(noticias)
        
        # Se houver notícias novas
        if novas:
            self.log(f"\n✅ {len(novas)} nova(s) notícia(s) detectada(s)!")
            
            # Salva as notícias novas
            self.salvar_noticias(novas)
            
            # Envia notificação se solicitado
            if enviar_notificacoes:
                self.enviar_notificacao(novas)
        else:
            self.log("\nℹ️ Nenhuma notícia nova desde a última coleta.")
        
        # Mostra resumo
        self.log(f"\n📊 Resumo: {len(noticias)} notícias coletadas, {len(novas)} novas.")
        
        return {
            'sucesso': True,
            'mensagem': 'Execução concluída',
            'total_noticias': len(noticias),
            'novas_noticias': len(novas),
            'noticias': noticias,
            'novas': novas
        }
    
    def mostrar_noticias(self, noticias):
        """
        Exibe as notícias no console.
        
        Args:
            noticias (list): Lista de notícias para exibir
        """
        print("\n📰 ÚLTIMAS NOTÍCIAS DA ANVISA:\n")
        
        for noticia in noticias:
            print(f"{'='*60}")
            print(f"📌 NOTÍCIA #{noticia['posicao']}")
            print(f"Título: {noticia['titulo']}")
            print(f"Link: {noticia['link']}")
            if noticia['descricao']:
                print(f"Descrição: {noticia['descricao']}")
            print(f"Data de publicação: {noticia['data_publicacao']}")
            print(f"Coletado em: {noticia['data_coleta']}")

# --- Execução Principal ---
if __name__ == "__main__":
    # Detecta se está rodando como executável compilado (PyInstaller)
    modo_silencioso = getattr(sys, 'frozen', False)
    
    # Cria uma instância do scraper
    scraper = ScraperAnvisa(modo_silencioso=modo_silencioso)
    
    # Executa o scraper
    resultado = scraper.executar(quantidade=3, enviar_notificacoes=True)
    
    # Se houver erro, finaliza com código de erro
    if not resultado['sucesso']:
        sys.exit(1)
    
    sys.exit(0)