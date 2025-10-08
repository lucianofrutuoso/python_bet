import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional

class ProfessionalOddsMonitor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.odds_history = []
        self.session = requests.Session()
        
        # Configurar headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def get_available_sports(self) -> List[Dict]:
        """
        Obtém lista de esportes disponíveis
        """
        url = f"{self.base_url}/sports"
        params = {'apiKey': self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            sports = response.json()
            print(f"🎯 Esportes disponíveis: {len(sports)}")
            
            # Filtrar esportes populares
            popular_sports = [s for s in sports if s['key'] in [
                'soccer_brazil_campeonato', 'soccer_england_pl', 'soccer_spain_la_liga',
                'soccer_italy_serie_a', 'soccer_germany_bundesliga', 'soccer_france_ligue_one',
                'soccer_uefa_champs_league', 'basketball_nba', 'americanfootball_nfl'
            ]]
            
            for sport in popular_sports[:8]:  # Mostrar 8 esportes
                print(f"  ⚽ {sport['title']} (key: {sport['key']})")
            
            return sports
            
        except Exception as e:
            print(f"❌ Erro ao obter esportes: {e}")
            return []
    
    def get_sport_odds(self, sport_key: str, regions: str = 'eu', markets: str = 'h2h') -> Optional[List[Dict]]:
        """
        Obtém odds para um esporte específico
        """
        url = f"{self.base_url}/sports/{sport_key}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets,
            'oddsFormat': 'decimal',
            'dateFormat': 'iso'
        }
        
        try:
            print(f"📡 Obtendo odds para {sport_key}...")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            # Informações de uso da API
            remaining_requests = response.headers.get('x-requests-remaining', 'N/A')
            used_requests = response.headers.get('x-requests-used', 'N/A')
            
            print(f"📊 API Usage: {used_requests} used, {remaining_requests} remaining")
            
            data = response.json()
            print(f"✅ {len(data)} jogos encontrados")
            
            return self._process_odds_data(data, sport_key)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro ao processar odds: {e}")
            return None
    
    def _process_odds_data(self, raw_data: List[Dict], sport_key: str) -> List[Dict]:
        """
        Processa e organiza os dados das odds
        """
        processed_games = []
        
        for game in raw_data:
            game_info = {
                'id': game.get('id'),
                'sport_key': sport_key,
                'sport_title': game.get('sport_title'),
                'home_team': game.get('home_team'),
                'away_team': game.get('away_team'),
                'commence_time': game.get('commence_time'),
                'timestamp': datetime.now().isoformat(),
                'bookmakers': [],
                'best_odds': {}
            }
            
            # Coletar odds de todas as casas de apostas
            bookmakers_data = []
            for bookmaker in game.get('bookmakers', []):
                bookmaker_info = {
                    'key': bookmaker.get('key'),
                    'title': bookmaker.get('title'),
                    'last_update': bookmaker.get('last_update'),
                    'markets': {}
                }
                
                # Processar mercados
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        outcomes = {}
                        for outcome in market['outcomes']:
                            outcomes[outcome['name']] = outcome['price']
                        bookmaker_info['markets']['h2h'] = outcomes
                
                bookmakers_data.append(bookmaker_info)
            
            game_info['bookmakers'] = bookmakers_data
            
            # Calcular melhores odds
            game_info['best_odds'] = self._calculate_best_odds(bookmakers_data)
            
            processed_games.append(game_info)
        
        return processed_games
    
    def _calculate_best_odds(self, bookmakers_data: List[Dict]) -> Dict:
        """
        Calcula as melhores odds entre todas as casas
        """
        best_odds = {
            'home': {'odd': 0, 'bookmaker': ''},
            'away': {'odd': 0, 'bookmaker': ''},
            'draw': {'odd': 0, 'bookmaker': ''}
        }
        
        for bookmaker in bookmakers_data:
            h2h_market = bookmaker['markets'].get('h2h', {})
            
            # Home win
            home_odd = h2h_market.get(bookmaker['title'] == 'home' and 'home_team' or bookmaker['title'] == 'away' and 'away_team' or bookmaker['title'])
            if home_odd and home_odd > best_odds['home']['odd']:
                best_odds['home'] = {'odd': home_odd, 'bookmaker': bookmaker['title']}
            
            # Away win
            away_odd = h2h_market.get('away')
            if away_odd and away_odd > best_odds['away']['odd']:
                best_odds['away'] = {'odd': away_odd, 'bookmaker': bookmaker['title']}
            
            # Draw
            draw_odd = h2h_market.get('draw')
            if draw_odd and draw_odd > best_odds['draw']['odd']:
                best_odds['draw'] = {'odd': draw_odd, 'bookmaker': bookmaker['title']}
        
        return best_odds
    
    def display_odds_analysis(self, games_data: List[Dict]):
        """
        Exibe análise completa das odds
        """
        print(f"\n{'='*100}")
        print(f"📊 ANÁLISE PROFISSIONAL DE ODDS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"{'='*100}")
        
        for game in games_data[:6]:  # Mostrar 6 jogos
            print(f"\n⚽ {game['home_team']} 🆚 {game['away_team']}")
            print(f"   🏆 {game['sport_title']} | 🕐 {game['commence_time'][:16].replace('T', ' ')}")
            print(f"   📊 Casas de apostas analisadas: {len(game['bookmakers'])}")
            
            # Melhores odds
            best = game['best_odds']
            print(f"   🎯 MELHORES ODDS:")
            if best['home']['odd'] > 0:
                print(f"      🏠 Casa: {best['home']['odd']:.2f} ({best['home']['bookmaker']})")
            if best['draw']['odd'] > 0:
                print(f"      🤝 Empate: {best['draw']['odd']:.2f} ({best['draw']['bookmaker']})")
            if best['away']['odd'] > 0:
                print(f"      ✈️ Fora: {best['away']['odd']:.2f} ({best['away']['bookmaker']})")
            
            # Análise de valor
            self._display_value_analysis(game)
    
    def _display_value_analysis(self, game: Dict):
        """
        Exibe análise de valor das odds
        """
        best = game['best_odds']
        
        # Calcular probabilidades implícitas
        total_prob = 0
        probs = {}
        
        for outcome in ['home', 'draw', 'away']:
            if best[outcome]['odd'] > 0:
                prob = 1 / best[outcome]['odd']
                probs[outcome] = prob
                total_prob += prob
        
        if total_prob > 0:
            # Ajustar para 100%
            market_margin = (total_prob - 1) * 100
            print(f"   📈 Margem do mercado: {market_margin:.2f}%")
            
            # Identificar value bets
            for outcome, prob in probs.items():
                fair_prob = prob / total_prob
                if fair_prob > 0.6:  # Threshold para value bet
                    outcome_name = {'home': 'Casa', 'draw': 'Empate', 'away': 'Fora'}[outcome]
                    print(f"   💎 POSSÍVEL VALUE BET: {outcome_name} (Prob. Justa: {fair_prob:.1%})")
    
    def monitor_multiple_sports(self, sport_keys: List[str], interval_minutes: int = 30, iterations: int = 12):
        """
        Monitora múltiplos esportes
        """
        print("🚀 INICIANDO MONITORAMENTO PROFISSIONAL")
        print(f"🎯 Esportes: {', '.join(sport_keys)}")
        print(f"⏰ Intervalo: {interval_minutes} minutos")
        print(f"🔢 Iterações: {iterations}")
        print("=" * 80)
        
        # Obter esportes disponíveis primeiro
        available_sports = self.get_available_sports()
        
        for iteration in range(iterations):
            print(f"\n{'#' * 80}")
            print(f"🔍 ITERAÇÃO {iteration + 1}/{iterations}")
            print(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"{'#' * 80}")
            
            all_games = []
            
            for sport_key in sport_keys:
                print(f"\n📡 Analisando {sport_key}...")
                games_data = self.get_sport_odds(sport_key)
                
                if games_data:
                    all_games.extend(games_data)
                    
                    # Exibir análise para este esporte
                    self.display_odds_analysis(games_data)
                    
                    # Salvar no histórico
                    self.odds_history.extend(games_data)
            
            # Salvar dados a cada 3 iterações
            if iteration % 3 == 0:
                self.save_comprehensive_data()
            
            # Próxima iteração
            if iteration < iterations - 1:
                next_time = datetime.now() + timedelta(minutes=interval_minutes)
                print(f"\n⏳ Próxima verificação: {next_time.strftime('%H:%M:%S')}")
                time.sleep(interval_minutes * 60)
        
        print("\n✅ MONITORAMENTO CONCLUÍDO!")
        self.save_comprehensive_data()
    
    def save_comprehensive_data(self):
        """
        Salva dados completos em CSV
        """
        try:
            if not self.odds_history:
                print("📭 Nenhum dado para salvar")
                return
            
            # Criar DataFrame detalhado
            rows = []
            for game in self.odds_history:
                base_info = {
                    'timestamp': game['timestamp'],
                    'sport_key': game['sport_key'],
                    'sport_title': game['sport_title'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'commence_time': game['commence_time']
                }
                
                # Adicionar informações de cada bookmaker
                for bookmaker in game['bookmakers']:
                    row = base_info.copy()
                    row['bookmaker'] = bookmaker['title']
                    
                    # Odds H2H
                    h2h = bookmaker['markets'].get('h2h', {})
                    row['home_odd'] = h2h.get('home')
                    row['draw_odd'] = h2h.get('draw')
                    row['away_odd'] = h2h.get('away')
                    
                    rows.append(row)
            
            df = pd.DataFrame(rows)
            
            # Salvar com timestamp no filename
            filename = f"odds_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"💾 Dados salvos em {filename} ({len(df)} registros)")
            
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")

def main():
    """
    Função principal - COLOQUE SUA CHAVE API AQUI
    """
    # 🔑 SUA CHAVE API - Obtenha em: https://the-odds-api.com/
    API_KEY = "b2634a9ae53b4c61e99bcbd109ffcf27"  # ← SUBSTITUA POR SUA CHAVE
    
    if API_KEY == "SUA_CHAVE_API_AQUI":
        print("❌ POR FAVOR, CONFIGURE SUA CHAVE API!")
        print("1. Acesse: https://the-odds-api.com/")
        print("2. Cadastre-se gratuitamente")
        print("3. Obtenha sua chave API")
        print("4. Substitua 'SUA_CHAVE_API_AQUI' pela sua chave real")
        return
    
    # Inicializar monitor
    monitor = ProfessionalOddsMonitor(api_key=API_KEY)
    
    # Esportes para monitorar
    SPORTS_TO_MONITOR = [
        'soccer_brazil_campeonato',      # Brasileirão
        'soccer_england_pl',             # Premier League
        'soccer_uefa_champs_league',     # Champions League
        'basketball_nba'                 # NBA
    ]
    
    try:
        # Iniciar monitoramento
        monitor.monitor_multiple_sports(
            sport_keys=SPORTS_TO_MONITOR,
            interval_minutes=15,     # A cada 15 minutos
            iterations=8             # 2 horas de monitoramento
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoramento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no monitoramento: {e}")
    finally:
        print("📊 Análise concluída!")

if __name__ == "__main__":
    main()
