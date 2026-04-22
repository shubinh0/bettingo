import requests
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import time
from typing import Dict, List, Optional, Tuple
import os

# Импортируем конфиг
try:
    from config import VK_TOKEN, RAPIDAPI_KEY, ODDS_API_KEY
except ImportError:
    VK_TOKEN = os.environ.get('VK_TOKEN')
    RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY')
    ODDS_API_KEY = os.environ.get('ODDS_API_KEY')

class FootballAnalyzer:
    def __init__(self, rapidapi_key: str):
        self.headers = {
            "X-RapidAPI-Key": rapidapi_key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
    
    def get_live_matches(self) -> List[Dict]:
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        try:
            response = requests.get(url, headers=self.headers, params={"live": "all"}, timeout=10)
            data = response.json()
            if data.get('response'):
                return data['response']
        except Exception as e:
            print(f"Ошибка получения матчей: {e}")
        return []
    
    def get_match_statistics(self, fixture_id: int) -> Dict:
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
        try:
            response = requests.get(url, headers=self.headers, params={"fixture": fixture_id}, timeout=10)
            data = response.json()
            if data.get('response'):
                return self._parse_statistics(data['response'])
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
        return {}
    
    def _parse_statistics(self, stats_data: List) -> Dict:
        result = {'home': {}, 'away': {}, 'total': {}}
        
        for team_data in stats_data:
            team_type = 'home' if team_data['team']['type'] == 'home' else 'away'
            
            for stat in team_data['statistics']:
                stat_type = stat['type']
                value = stat['value']
                
                if value and '%' in str(value):
                    value = int(value.replace('%', ''))
                elif value and isinstance(value, str) and value.isdigit():
                    value = int(value)
                
                result[team_type][stat_type] = value
        
        result['home']['All Shots'] = (result['home'].get('Shots on Goal', 0) + 
                                       result['home'].get('Shots off Goal', 0) +
                                       result['home'].get('Blocked Shots', 0))
        
        result['away']['All Shots'] = (result['away'].get('Shots on Goal', 0) + 
                                       result['away'].get('Shots off Goal', 0) +
                                       result['away'].get('Blocked Shots', 0))
        
        return result
    
    def calculate_advantage_levels(self, stats: Dict) -> Tuple[int, List[str], Optional[str]]:
        if not stats or 'home' not in stats or 'away' not in stats:
            return 0, [], None
        
        home_stats = stats['home']
        away_stats = stats['away']
        
        home_advantages = []
        away_advantages = []
        
        # Уровень 1: Удары
        home_shots = home_stats.get('All Shots', 0)
        away_shots = away_stats.get('All Shots', 0)
        total_shots = home_shots + away_shots
        
        if total_shots > 0:
            home_shot_pct = (home_shots / total_shots) * 100
            if home_shot_pct >= 60:
                home_advantages.append(('Удары', f"{home_shots} vs {away_shots} ({home_shot_pct:.1f}%)", 1))
            elif (100 - home_shot_pct) >= 60:
                away_advantages.append(('Удары', f"{away_shots} vs {home_shots} ({100-home_shot_pct:.1f}%)", 1))
        
        # Уровень 2: Угловые
        home_corners = home_stats.get('Corner Kicks', 0)
        away_corners = away_stats.get('Corner Kicks', 0)
        total_corners = home_corners + away_corners
        
        if total_corners > 0:
            home_corner_pct = (home_corners / total_corners) * 100
            if home_corner_pct >= 60:
                home_advantages.append(('Угловые', f"{home_corners} vs {away_corners} ({home_corner_pct:.1f}%)", 2))
            elif (100 - home_corner_pct) >= 60:
                away_advantages.append(('Угловые', f"{away_corners} vs {home_corners} ({100-home_corner_pct:.1f}%)", 2))
        
        # Уровень 3: Владение
        home_possession = home_stats.get('Ball Possession', 0)
        away_possession = away_stats.get('Ball Possession', 0)
        
        if home_possession > 0 and away_possession > 0:
            if home_possession >= 60:
                home_advantages.append(('Владение', f"{home_possession}% vs {away_possession}%", 3))
            elif away_possession >= 60:
                away_advantages.append(('Владение', f"{away_possession}% vs {home_possession}%", 3))
        
        if len(home_advantages) > len(away_advantages):
            max_level = max([level for _, _, level in home_advantages])
            details = [f"{stat}: {value}" for stat, value, _ in home_advantages]
            return max_level, details, 'home'
        elif len(away_advantages) > len(home_advantages):
            max_level = max([level for _, _, level in away_advantages])
            details = [f"{stat}: {value}" for stat, value, _ in away_advantages]
            return max_level, details, 'away'
        
        return 0, [], None
    
    def get_match_odds(self, home_team: str, away_team: str) -> Dict:
        return {
            'home_win': 4.5,
            'away_win': 1.75,
            'home_or_draw': 2.1,
            'away_or_draw': 1.2
        }
    
    def find_betting_opportunities(self) -> List[Dict]:
        opportunities = []
        matches = self.get_live_matches()
        
        for match in matches:
            fixture_id = match['fixture']['id']
            home_team = match['teams']['home']['name']
            away_team = match['teams']['away']['name']
            league = match['league']['name']
            score = f"{match['goals']['home']}:{match['goals']['away']}"
            minute = match['fixture']['status']['elapsed']
            
            stats = self.get_match_statistics(fixture_id)
            level, advantages, dominant_team = self.calculate_advantage_levels(stats)
            
            if level < 1 or not dominant_team:
                continue
            
            odds = self.get_match_odds(home_team, away_team)
            
            if dominant_team == 'home':
                if odds['home_win'] > 4.0:
                    opportunities.append(self._format_opportunity(
                        match, league, score, minute, level, advantages,
                        stats, dominant_team, "Победа", odds['home_win']
                    ))
                elif odds['home_or_draw'] > 4.0:
                    opportunities.append(self._format_opportunity(
                        match, league, score, minute, level, advantages,
                        stats, dominant_team, "Победа или ничья (1X)", odds['home_or_draw']
                    ))
            else:
                if odds['away_win'] > 4.0:
                    opportunities.append(self._format_opportunity(
                        match, league, score, minute, level, advantages,
                        stats, dominant_team, "Победа", odds['away_win']
                    ))
                elif odds['away_or_draw'] > 4.0:
                    opportunities.append(self._format_opportunity(
                        match, league, score, minute, level, advantages,
                        stats, dominant_team, "Победа или ничья (X2)", odds['away_or_draw']
                    ))
        
        return opportunities
    
    def _format_opportunity(self, match, league, score, minute, level, 
                           advantages, stats, dominant_team, bet_type, bet_odds) -> Dict:
        if dominant_team == 'home':
            team_name = match['teams']['home']['name']
            opponent = match['teams']['away']['name']
            team_stats = stats['home']
            opponent_stats = stats['away']
        else:
            team_name = match['teams']['away']['name']
            opponent = match['teams']['home']['name']
            team_stats = stats['away']
            opponent_stats = stats['home']
        
        stats_text = f"""
📊 Статистика ({team_name} vs {opponent}):

🎯 Удары в створ: {team_stats.get('Shots on Goal', 0)} - {opponent_stats.get('Shots on Goal', 0)}
💨 Удары мимо: {team_stats.get('Shots off Goal', 0)} - {opponent_stats.get('Shots off Goal', 0)}
⚽ Всего ударов: {team_stats.get('All Shots', 0)} - {opponent_stats.get('All Shots', 0)}
🔄 Владение: {team_stats.get('Ball Possession', 0)}% - {opponent_stats.get('Ball Possession', 0)}%
🚩 Угловые: {team_stats.get('Corner Kicks', 0)} - {opponent_stats.get('Corner Kicks', 0)}
⚡ Опасные атаки: {team_stats.get('Dangerous Attacks', 0)} - {opponent_stats.get('Dangerous Attacks', 0)}
        """
        
        return {
            'level': level,
            'league': league,
            'match': f"{match['teams']['home']['name']} vs {match['teams']['away']['name']}",
            'score': score,
            'minute': minute,
            'advantages': advantages,
            'stats': stats_text,
            'bet_type': bet_type,
            'bet_odds': bet_odds,
            'team': team_name
        }


class VKBettingBot:
    def __init__(self, vk_token: str, rapidapi_key: str):
        self.vk_session = vk_api.VkApi(token=vk_token)
        self.analyzer = FootballAnalyzer(rapidapi_key)
        
    def send_message(self, user_id: int, message: str):
        try:
            vk = self.vk_session.get_api()
            vk.messages.send(
                user_id=user_id,
                message=message,
                random_id=int(time.time() * 1000)
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
    
    def format_opportunity_message(self, opp: Dict) -> str:
        stars = "⭐" * opp['level']
        
        message = f"""
{stars} УРОВЕНЬ {opp['level']} {stars}

🏆 Лига: {opp['league']}
⚽ Матч: {opp['match']}
📊 Счет: {opp['score']} ({opp['minute']}')

✅ Преимущество:
{chr(10).join(['• ' + adv for adv in opp['advantages']])}

🎯 Рекомендуемая ставка:
{opp['bet_type']} на команду {opp['team']}
📈 Коэффициент: {opp['bet_odds']}

{opp['stats']}

⚠️ Ставка с высоким коэффициентом (>4.0) при статистическом преимуществе
        """
        return message.strip()
    
    def run(self):
        print("🤖 Бот запущен и готов к работе")
        
        longpoll = VkLongPoll(self.vk_session)
        
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                command = event.text.lower().strip()
                
                if command == "анализ" or command == "start":
                    self.send_message(user_id, "🔍 Начинаю анализ live матчей...")
                    
                    opportunities = self.analyzer.find_betting_opportunities()
                    
                    if opportunities:
                        for opp in opportunities:
                            message = self.format_opportunity_message(opp)
                            self.send_message(user_id, message)
                            time.sleep(1)
                    else:
                        self.send_message(user_id, "😔 Подходящих матчей с коэффициентом >4.0 не найдено")
                
                elif command == "помощь" or command == "help":
                    help_text = """
📚 Доступные команды:

• Анализ - найти матчи с преимуществом 20%+ и кэфом >4.0
• Помощь - показать это сообщение

Алгоритм:
✅ Уровень 1: Преимущество по ударам (20%+)
✅ Уровень 2: Преимущество по угловым
✅ Уровень 3: Преимущество по владению

Ищем ставки на победу или победа/ничья с коэффициентом >4.0
                    """
                    self.send_message(user_id, help_text.strip())
                
                else:
                    self.send_message(user_id, "❓ Неизвестная команда. Напишите 'Помощь'")


if __name__ == "__main__":
    if not VK_TOKEN or not RAPIDAPI_KEY:
        print("❌ Ошибка: Не указаны VK_TOKEN или RAPIDAPI_KEY")
        print("Создайте файл config.py или укажите переменные окружения")
        exit(1)
    
    bot = VKBettingBot(VK_TOKEN, RAPIDAPI_KEY)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
