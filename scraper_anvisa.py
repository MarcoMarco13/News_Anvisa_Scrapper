import os
import re
import sys
import time
import base64
import subprocess
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ScraperAnvisa:

    def __init__(self, modo_silencioso=False):
        self.modo_silencioso = modo_silencioso
        self.url = "https://www.gov.br/anvisa/pt-br"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        if getattr(sys, 'frozen', False):
            diretorio_base = os.path.dirname(sys.executable)
        else:
            diretorio_base = os.path.dirname(os.path.abspath(__file__))

        self.pasta_logs = os.path.join(diretorio_base, "logs")
        os.makedirs(self.pasta_logs, exist_ok=True)
        self.arquivo_log = os.path.join(self.pasta_logs, "ultimas_noticias.txt")

        self.ultimas_noticias = []

        self.sessao = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.sessao.mount('http://', adapter)
        self.sessao.mount('https://', adapter)

        if not self.modo_silencioso:
            print("📢 Notificações Windows ativas via PowerShell")

    def log(self, mensagem, tipo="info"):
        if not self.modo_silencioso:
            print(mensagem)

    def enviar_notificacao_nativa(self, titulo, mensagem):
        try:
            def xml_escape(text):
                return (text.replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                            .replace('"', '&quot;')
                            .replace("'", "&apos;"))

            titulo_clean = xml_escape(titulo)
            mensagem_clean = xml_escape(mensagem)

            app_id = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe"

            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $nodes = $template.GetElementsByTagName("text")
            $nodes.Item(0).AppendChild($template.CreateTextNode("{titulo_clean}")) > $null
            $nodes.Item(1).AppendChild($template.CreateTextNode("{mensagem_clean}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app_id}").Show($toast)
            '''

            encoded_cmd = base64.b64encode(ps_script.encode('utf-16le')).decode('utf-8')

            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_cmd],
                capture_output=True,
                creationflags=0x08000000
            )
            self.log("🔔 Notificação enviada com sucesso!")
            return True
        except Exception as e:
            self.log(f"⚠️ Erro ao enviar notificação via PowerShell: {e}")
            return False

    def obter_noticias(self, quantidade=8):
        try:
            self.log(f"🔍 Coletando as últimas {quantidade} notícias da Anvisa...")
            response = self.sessao.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.text, 'html.parser')

            noticias = soup.select('a[class*="DefaultTemplate-module"]')

            noticias_filtradas = []
            for noticia in noticias:
                href = noticia.get('href', '')
                if '/noticias-anvisa/' in href:
                    noticias_filtradas.append(noticia)

            if not noticias_filtradas:
                self.log("Tentando seletor alternativo...")
                noticias_filtradas = soup.select('a[href*="noticias-anvisa"]')

            if not noticias_filtradas:
                self.log("❌ Nenhuma notícia encontrada.")
                return []

            noticias_selecionadas = noticias_filtradas[:quantidade]

            resultados = []
            for i, noticia in enumerate(noticias_selecionadas, 1):
                link = noticia.get('href')
                if link and not link.startswith('http'):
                    link = f"https://www.gov.br{link}"

                titulo_elemento = noticia.select_one('h2')
                if titulo_elemento:
                    titulo = titulo_elemento.text.strip()
                else:
                    texto_completo = noticia.text.strip()
                    titulo = ' '.join(texto_completo.split()[:15]) + '...' if len(texto_completo.split()) > 15 else texto_completo

                data = "Data não disponível"
                data_elemento = noticia.find_parent().select_one('[class*="data"], [class*="date"], [class*="publicado"]')
                if data_elemento:
                    data = data_elemento.text.strip()

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
        try:
            with open(self.arquivo_log, 'r', encoding='utf-8') as f:
                conteudo = f.read()

            novas_noticias = []
            for noticia in noticias_atuais:
                if noticia['link'] not in conteudo:
                    novas_noticias.append(noticia)

            return novas_noticias
        except FileNotFoundError:
            return noticias_atuais
        except Exception as e:
            self.log(f"⚠️ Erro ao verificar notícias novas: {e}")
            return noticias_atuais

    def salvar_noticias(self, noticias):
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

    def executar(self, quantidade=3, enviar_notificacoes=True):
        self.log("\n" + "="*60)
        self.log("🚀 INICIANDO SCRAPER DA ANVISA")
        self.log("="*60)

        noticias = self.obter_noticias(quantidade)

        if not noticias:
            if enviar_notificacoes:
                self.enviar_notificacao_nativa(
                    titulo="⚠️ Erro no Scraper Anvisa",
                    mensagem="Não foi possível obter notícias. Verifique sua conexão."
                )

            return {
                'sucesso': False,
                'mensagem': 'Nenhuma notícia encontrada',
                'total_noticias': 0,
                'novas_noticias': 0
            }

        novas = self.verificar_novas_noticias(noticias)

        if not self.modo_silencioso:
            self.mostrar_noticias(noticias)

        if novas:
            self.log(f"\n✅ {len(novas)} nova(s) notícia(s) detectada(s)!")
            self.salvar_noticias(novas)
        else:
            self.log("\nℹ️ Nenhuma notícia nova desde a última coleta.")

        if enviar_notificacoes:
            if novas:
                mensagem = f"✅ {len(novas)} nova(s) notícia(s) encontrada(s)!\n\n"
                for i, noticia in enumerate(novas[:5], 1):
                    titulo_curto = noticia['titulo']
                    if len(titulo_curto) > 45:
                        titulo_curto = titulo_curto[:42] + "..."
                    mensagem += f"{i}. {titulo_curto}\n"

                if len(novas) > 5:
                    mensagem += f"... e mais {len(novas) - 5} notícias"
            else:
                mensagem = f"ℹ️ Nenhuma notícia nova encontrada.\nÚltima verificação: {datetime.now().strftime('%H:%M:%S')}"

            titulo = f"📊 Anvisa - {len(noticias)} notícias consultadas"
            self.enviar_notificacao_nativa(titulo, mensagem)

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


if __name__ == "__main__":
    modo_silencioso = getattr(sys, 'frozen', False)

    scraper = ScraperAnvisa(modo_silencioso=modo_silencioso)
    resultado = scraper.executar(quantidade=9, enviar_notificacoes=True)

    if not resultado['sucesso']:
        sys.exit(1)

    sys.exit(0)