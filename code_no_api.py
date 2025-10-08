import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from datetime import datetime
import logging

class BetMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.odds_history = []
        
    def get_page_content(self, url):
        """
        Faz a requisição HTTP para a página
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao acessar a página: {e}")
            return None
    
    def parse_odds(self, html, game_identifier):
        """
        Analisa o HTML e extrai as odds (implementação específica por site)
        """
        soup = BeautifulSoup(html, 'html.parser')
        odds_data = {}
        
        try:
            # EXEMPLO: Encontrar o jogo específico
            game_element = soup.find('div', text=game_identifier)
            if not game_element:
                logging.warning("Jogo não encontrado")
                return None
            
            # EXEMPLO: Extrair odds (adaptar conforme estrutura do site)
            # Time 1 (Casa)
            home_odds = game_element.find_next('span', class_='odds-home')
            odds_data['home'] = float(home_odds.text) if home_odds else None
            
            # Empate
            draw_odds = game_element.find_next('span', class_='odds-draw')
            odds_data['draw'] = float(draw_odds.text) if draw_odds else None
            
            # Time 2 (Fora)
            away_odds = game_element.find_next('span', class_='odds-away')
            odds_data['away'] = float(away_odds.text) if away_odds else None
            
            # Timestamp
            odds_data['timestamp'] = datetime.now()
            
            return odds_data
            
        except Exception as e:
            logging.error(f"Erro ao parsear odds: {e}")
            return None
    
    def monitor_odds(self, url, game_identifier, interval_minutes=5, max_iterations=None):
        """
        Monitora as odds em intervalos regulares
        """
        iteration = 0
        
        while True:
            if max_iterations and iteration >= max_iterations:
                break
                
            print(f"\n--- Verificação {iteration + 1} - {datetime.now().strftime('%H:%M:%S')} ---")
            
            html = self.get_page_content(url)
            if html:
                odds = self.parse_odds(html, game_identifier)
                if odds:
                    self.odds_history.append(odds)
                    self.display_current_odds(odds)
                    self.analyze_trend()
            
            iteration += 1
            time.sleep(interval_minutes * 60)
    
    def display_current_odds(self, odds):
        """
        Exibe as odds atuais
        """
        print(f"Casa: {odds.get('home', 'N/A')}")
        print(f"Empate: {odds.get('draw', 'N/A')}")
        print(f"Fora: {odds.get('away', 'N/A')}")
    
    def analyze_trend(self):
        """
        Analisa a tendência das odds
        """
        if len(self.odds_history) < 2:
            return
        
        current = self.odds_history[-1]
        previous = self.odds_history[-2]
        
        print("\n--- Análise de Tendência ---")
        
        for market in ['home', 'draw', 'away']:
            if current.get(market) and previous.get(market):
                change = current[market] - previous[market]
                trend = "↑" if change > 0 else "↓" if change < 0 else "→"
                print(f"{market}: {current[market]} ({trend} {abs(change):.2f})")
    
    def save_to_csv(self, filename="odds_history.csv"):
        """
        Salva o histórico em CSV
        """
        if self.odds_history:
            df = pd.DataFrame(self.odds_history)
            df.to_csv(filename, index=False)
            print(f"\nHistórico salvo em {filename}")

# Exemplo de uso adaptado para um site específico
class Bet365Monitor(BetMonitor):
    def parse_odds(self, html, game_identifier):
        """
        Exemplo específico para Bet365 (estrutura fictícia)
        """
        soup = BeautifulSoup(html, 'html.parser')
        odds_data = {}
        
        try:
            # Encontrar a seção do jogo (adaptar selectors reais)
            game_section = soup.find('div', class_='event', string=lambda text: game_identifier in text if text else False)
            
            if game_section:
                # Odds para resultado final (1X2)
                odds_elements = game_section.find_next('div', class_='odds').find_all('span', class_='odds-button')
                
                if len(odds_elements) >= 3:
                    odds_data['home'] = float(odds_elements[0].text)
                    odds_data['draw'] = float(odds_elements[1].text)
                    odds_data['away'] = float(odds_elements[2].text)
                    odds_data['timestamp'] = datetime.now()
                    
                    return odds_data
                    
        except Exception as e:
            logging.error(f"Erro no parsing Bet365: {e}")
            
        return None

# Função principal
def main():
    # Configuração
    logging.basicConfig(level=logging.INFO)
    
    # URL do site (SUBSTITUA pela URL real)
    #URL = "https://exemplo-site-apostas.com/partida-especifica"
    URL = "https://br.netbet.com/futebol/brazil-serie-a/atletico-mg-vs-sport-28078674/"
    
    # Identificador do jogo (nome dos times, etc)
    GAME_IDENTIFIER = "Time A vs Time B"
    
    # Criar monitor
    monitor = Bet365Monitor()
    
    try:
        print(f"Iniciando monitoramento do jogo: {GAME_IDENTIFIER}")
        print("Pressione Ctrl+C para parar")
        
        # Monitorar por 1 hora (12 verificações de 5 minutos)
        monitor.monitor_odds(URL, GAME_IDENTIFIER, interval_minutes=5, max_iterations=12)
        
    except KeyboardInterrupt:
        print("\nMonitoramento interrompido pelo usuário")
    finally:
        # Salvar dados
        monitor.save_to_csv()
        print("Monitoramento finalizado")

if __name__ == "__main__":
    main()