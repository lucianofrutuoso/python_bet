import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Optional

class BrasilOddsMonitor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.odds_history = []
        self.session = requests.Session()
        
        # Configuração para futebol brasileiro
        self.brasil_sports = {
            'campeonato_brasileiro': 'soccer_brazil_campeonato',
            'copa_do_brasil': 'soccer_brazil_copa_do_brasil',
            'libertadores': 'soccer_copa_libertadores',
            'sul_americana': 'soccer_copa_sudamericana',
            'estaduais': [
                'soccer_brazil_campeonato_paulista',
                'soccer_brazil_carioca',
                'soccer_brazil_gaucho',
                'soccer_brazil_mineiro'
            ]
        }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
    
    def testar_api(self) -> bool:
        """
        Testa se a API está funcionando
        """
        url = f"{self.base_url}/sports"
        params = {'apiKey': self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                print("✅ API conectada com sucesso!")
                return True
            else:
                print(f"❌ Erro na API: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def listar_campeonatos_brasileiros(self):
        """
        Lista todos os campeonatos brasileiros disponíveis
        """
        url = f"{self.base_url}/sports"
        params = {'apiKey': self.api_key}
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            sports = response.json()
            
            print("🏆 CAMPEONATOS BRASILEIROS DISPONÍVEIS:")
            print("-" * 50)
            
            brasileiros = [s for s in sports if 'brazil' in s['key'].lower() or 'copa' in s['key'].lower()]
            
            for sport in brasileiros:
                print(f"⚽ {sport['title']}")
                print(f"   🔑 Key: {sport['key']}")
                print(f"   📍 Regiões: {', '.join(sport['has_outrights'] and ['Sim'] or ['Não'])}")
                print()
            
            return brasileiros
            
        except Exception as e:
            print(f"❌ Erro ao listar campeonatos: {e}")
            return []
    
    def obter_jogos_ao_vivo(self, campeonato_key: str = 'soccer_brazil_campeonato') -> Optional[List[Dict]]:
        """
        Obtém jogos em tempo real do campeonato especificado
        """
        url = f"{self.base_url}/sports/{campeonato_key}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'eu,us',  # Europa e Estados Unidos
            'markets': 'h2h,totals',  # Resultado e Over/Under
            'oddsFormat': 'decimal',
            'dateFormat': 'iso'
        }
        
        try:
            print(f"📡 Buscando jogos do {campeonato_key}...")
            response = self.session.get(url, params=params, timeout=15)
            
            # Verificar uso da API
            remaining = response.headers.get('x-requests-remaining', 'N/A')
            used = response.headers.get('x-requests-used', 'N/A')
            
            print(f"📊 Uso API: {used} usadas, {remaining} restantes")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"✅ {len(dados)} jogos encontrados!")
                return self._processar_jogos_brasileiros(dados, campeonato_key)
            else:
                print(f"❌ Erro na API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erro ao buscar jogos: {e}")
            return None
    
    def _processar_jogos_brasileiros(self, dados_brutos: List[Dict], campeonato: str) -> List[Dict]:
        """
        Processa os dados dos jogos brasileiros
        """
        jogos_processados = []
        
        for jogo in dados_brutos:
            info_jogo = {
                'campeonato': campeonato,
                'titulo_campeonato': jogo.get('sport_title', ''),
                'time_casa': jogo.get('home_team', ''),
                'time_fora': jogo.get('away_team', ''),
                'data_hora': jogo.get('commence_time', ''),
                'timestamp_coleta': datetime.now().isoformat(),
                'casas_apostas': [],
                'melhores_odds': {},
                'analise_valor': {}
            }
            
            # Processar cada casa de aposta
            for casa in jogo.get('bookmakers', []):
                casa_info = {
                    'nome': casa.get('title', ''),
                    'key': casa.get('key', ''),
                    'atualizacao': casa.get('last_update', ''),
                    'mercados': {}
                }
                
                # Mercado Resultado Final (H2H)
                for mercado in casa.get('markets', []):
                    if mercado['key'] == 'h2h':
                        resultados = {}
                        for resultado in mercado['outcomes']:
                            resultados[resultado['name']] = resultado['price']
                        casa_info['mercados']['resultado'] = resultados
                    
                    # Mercado Over/Under
                    elif mercado['key'] == 'totals':
                        over_under = {}
                        for resultado in mercado['outcomes']:
                            over_under[resultado['name']] = resultado['price']
                        casa_info['mercados']['over_under'] = over_under
                
                info_jogo['casas_apostas'].append(casa_info)
            
            # Calcular melhores odds
            info_jogo['melhores_odds'] = self._calcular_melhores_odds(info_jogo['casas_apostas'])
            
            # Análise de valor
            info_jogo['analise_valor'] = self._analisar_valor_odds(info_jogo['melhores_odds'])
            
            jogos_processados.append(info_jogo)
        
        return jogos_processados
    
    def _calcular_melhores_odds(self, casas_apostas: List[Dict]) -> Dict:
        """
        Encontra as melhores odds entre todas as casas
        """
        melhores = {
            'casa': {'odd': 0, 'casa_aposta': ''},
            'empate': {'odd': 0, 'casa_aposta': ''},
            'fora': {'odd': 0, 'casa_aposta': ''},
            'over_25': {'odd': 0, 'casa_aposta': ''},
            'under_25': {'odd': 0, 'casa_aposta': ''}
        }
        
        for casa in casas_apostas:
            # Odds Resultado Final
            resultado = casa['mercados'].get('resultado', {})
            
            if resultado.get(casa['nome'] == 'home' and 'home_team' or casa['nome'] == 'away' and 'away_team' or casa['nome']):
                odd_casa = resultado.get('home')
                if odd_casa and odd_casa > melhores['casa']['odd']:
                    melhores['casa'] = {'odd': odd_casa, 'casa_aposta': casa['nome']}
            
            if resultado.get('away'):
                odd_fora = resultado['away']
                if odd_fora > melhores['fora']['odd']:
                    melhores['fora'] = {'odd': odd_fora, 'casa_aposta': casa['nome']}
            
            if resultado.get('draw'):
                odd_empate = resultado['draw']
                if odd_empate > melhores['empate']['odd']:
                    melhores['empate'] = {'odd': odd_empate, 'casa_aposta': casa['nome']}
            
            # Odds Over/Under
            over_under = casa['mercados'].get('over_under', {})
            if over_under.get('Over 2.5'):
                odd_over = over_under['Over 2.5']
                if odd_over > melhores['over_25']['odd']:
                    melhores['over_25'] = {'odd': odd_over, 'casa_aposta': casa['nome']}
            
            if over_under.get('Under 2.5'):
                odd_under = over_under['Under 2.5']
                if odd_under > melhores['under_25']['odd']:
                    melhores['under_25'] = {'odd': odd_under, 'casa_aposta': casa['nome']}
        
        return melhores
    
    def _analisar_valor_odds(self, melhores_odds: Dict) -> Dict:
        """
        Analisa se existem value bets nas odds
        """
        analise = {
            'value_bets': [],
            'margem_mercado': 0,
            'recomendacao': ''
        }
        
        # Calcular probabilidades implícitas
        odds_validas = []
        
        for mercado in ['casa', 'empate', 'fora']:
            if melhores_odds[mercado]['odd'] > 0:
                odds_validas.append(1 / melhores_odds[mercado]['odd'])
        
        if odds_validas:
            margem = (sum(odds_validas) - 1) * 100
            analise['margem_mercado'] = margem
            
            # Identificar value bets (probabilidade implícita < probabilidade real estimada)
            for mercado in ['casa', 'empate', 'fora']:
                odd = melhores_odds[mercado]['odd']
                if odd > 0:
                    prob_implicita = 1 / odd
                    prob_ajustada = prob_implicita / sum(odds_validas)
                    
                    # Considerar value bet se probabilidade ajustada > 60%
                    if prob_ajustada > 0.6:
                        nome_mercado = {'casa': 'Vitória Casa', 'empate': 'Empate', 'fora': 'Vitória Fora'}[mercado]
                        analise['value_bets'].append({
                            'mercado': nome_mercado,
                            'odd': odd,
                            'probabilidade': f"{prob_ajustada:.1%}",
                            'casa_aposta': melhores_odds[mercado]['casa_aposta']
                        })
        
        # Gerar recomendação
        if analise['value_bets']:
            analise['recomendacao'] = f"🎯 {len(analise['value_bets'])} VALUE BET(S) IDENTIFICADO(S)"
        else:
            analise['recomendacao'] = "⚡ Aguardando melhores oportunidades"
        
        return analise
    
    def exibir_jogos_brasileiros(self, jogos_data: List[Dict]):
        """
        Exibe os jogos brasileiros de forma organizada
        """
        print(f"\n{'='*80}")
        print(f"🇧🇷 JOGOS DO FUTEBOL BRASILEIRO - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(f"{'='*80}")
        
        for jogo in jogos_data:
            print(f"\n⚽ {jogo['time_casa']} 🆚 {jogo['time_fora']}")
            print(f"   🏆 {jogo['titulo_campeonato']}")
            print(f"   🕐 {jogo['data_hora'][:16].replace('T', ' ')}")
            print(f"   📊 {len(jogo['casas_apostas'])} casas analisadas")
            
            # Melhores odds
            melhores = jogo['melhores_odds']
            print(f"\n   🎯 MELHORES ODDS:")
            if melhores['casa']['odd'] > 0:
                print(f"      🏠 Casa: {melhores['casa']['odd']:.2f} ({melhores['casa']['casa_aposta']})")
            if melhores['empate']['odd'] > 0:
                print(f"      🤝 Empate: {melhores['empate']['odd']:.2f} ({melhores['empate']['casa_aposta']})")
            if melhores['fora']['odd'] > 0:
                print(f"      ✈️ Fora: {melhores['fora']['odd']:.2f} ({melhores['fora']['casa_aposta']})")
            
            # Over/Under
            if melhores['over_25']['odd'] > 0:
                print(f"      📈 Over 2.5: {melhores['over_25']['odd']:.2f} ({melhores['over_25']['casa_aposta']})")
            if melhores['under_25']['odd'] > 0:
                print(f"      📉 Under 2.5: {melhores['under_25']['odd']:.2f} ({melhores['under_25']['casa_aposta']})")
            
            # Análise de valor
            analise = jogo['analise_valor']
            print(f"\n   💰 ANÁLISE:")
            print(f"      📊 Margem mercado: {analise['margem_mercado']:.2f}%")
            print(f"      💎 {analise['recomendacao']}")
            
            for value_bet in analise['value_bets'][:2]:  # Mostrar até 2 value bets
                print(f"      ✅ {value_bet['mercado']}: Odd {value_bet['odd']:.2f} (Prob: {value_bet['probabilidade']})")
    
    def monitorar_campeonato_brasileiro(self, campeonato_key: str = 'soccer_brazil_campeonato', 
                                      intervalo_minutos: int = 30, 
                                      iteracoes: int = 8):
        """
        Monitora um campeonato brasileiro específico
        """
        print("🚀 INICIANDO MONITORAMENTO DO CAMPEONATO BRASILEIRO")
        print(f"🎯 Campeonato: {campeonato_key}")
        print(f"⏰ Intervalo: {intervalo_minutos} minutos")
        print(f"🔢 Iterações: {iteracoes}")
        print("=" * 60)
        
        # Testar API primeiro
        if not self.testar_api():
            print("❌ Não foi possível conectar à API. Verifique sua chave.")
            return
        
        for iteracao in range(iteracoes):
            print(f"\n{'#' * 60}")
            print(f"🔍 ITERAÇÃO {iteracao + 1}/{iteracoes}")
            print(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"{'#' * 60}")
            
            # Obter jogos
            jogos = self.obter_jogos_ao_vivo(campeonato_key)
            
            if jogos:
                # Exibir análise
                self.exibir_jogos_brasileiros(jogos)
                
                # Salvar no histórico
                self.odds_history.extend(jogos)
                
                # Salvar dados a cada 2 iterações
                if iteracao % 2 == 0:
                    self.salvar_dados_brasileiros()
            
            # Próxima iteração
            if iteracao < iteracoes - 1:
                proxima_verificacao = datetime.now() + timedelta(minutes=intervalo_minutos)
                print(f"\n⏳ Próxima verificação: {proxima_verificacao.strftime('%H:%M:%S')}")
                time.sleep(intervalo_minutos * 60)
        
        print("\n✅ MONITORAMENTO CONCLUÍDO!")
        self.salvar_dados_brasileiros()
    
    def salvar_dados_brasileiros(self):
        """
        Salva dados dos jogos brasileiros em CSV
        """
        try:
            if not self.odds_history:
                print("📭 Nenhum dado para salvar")
                return
            
            # Criar DataFrame detalhado
            linhas = []
            for jogo in self.odds_history:
                for casa in jogo['casas_apostas']:
                    linha = {
                        'data_coleta': jogo['timestamp_coleta'],
                        'campeonato': jogo['titulo_campeonato'],
                        'time_casa': jogo['time_casa'],
                        'time_fora': jogo['time_fora'],
                        'data_jogo': jogo['data_hora'],
                        'casa_aposta': casa['nome'],
                        'odd_casa': casa['mercados'].get('resultado', {}).get('home'),
                        'odd_empate': casa['mercados'].get('resultado', {}).get('draw'),
                        'odd_fora': casa['mercados'].get('resultado', {}).get('away'),
                        'odd_over_25': casa['mercados'].get('over_under', {}).get('Over 2.5'),
                        'odd_under_25': casa['mercados'].get('over_under', {}).get('Under 2.5')
                    }
                    linhas.append(linha)
            
            df = pd.DataFrame(linhas)
            
            # Salvar com timestamp
            nome_arquivo = f"odds_brasileiro_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            df.to_csv(nome_arquivo, index=False, encoding='utf-8-sig')
            print(f"💾 Dados salvos em {nome_arquivo} ({len(df)} registros)")
            
        except Exception as e:
            print(f"❌ Erro ao salvar dados: {e}")

def main():
    """
    Função principal - CONFIGURE SUA CHAVE API AQUI
    """
    # 🔑 SUA CHAVE API - Obtenha em: https://the-odds-api.com/
    API_KEY = "b2634a9ae53b4c61e99bcbd109ffcf27"  # ← SUBSTITUA POR SUA CHAVE REAL
    
    if API_KEY == "SUA_CHAVE_API_AQUI":
        print("❌ CONFIGURAÇÃO NECESSÁRIA:")
        print("1. Acesse: https://the-odds-api.com/")
        print("2. Cadastre-se gratuitamente")
        print("3. Obtenha sua chave API")
        print("4. Substitua 'SUA_CHAVE_API_AQUI' pela sua chave real")
        return
    
    # Inicializar monitor
    monitor = BrasilOddsMonitor(api_key=API_KEY)
    
    # Listar campeonatos disponíveis
    monitor.listar_campeonatos_brasileiros()
    
    try:
        # Monitorar Campeonato Brasileiro Série A
        monitor.monitorar_campeonato_brasileiro(
            campeonato_key='soccer_brazil_campeonato',  # Brasileirão Série A
            intervalo_minutos=20,  # A cada 20 minutos
            iteracoes=6           # 2 horas de monitoramento
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Monitoramento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    main()