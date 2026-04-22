
 Подключение к TimeWeb (ссылку даст TimeWeb после регистрации)
ssh u123456@ваш_сервер.timeweb.ru

# Создаем папку и скачиваем код
git clone https://github.com/shubin0/bettingo.git ~/www/bot
cd ~/www/bot

# Создаем файл с токенами
cat > config.py << EOF
VK_TOKEN = vk1.a.2A_kXCYEE0IOBnwXIIt1w0GxuFZODotUAHGWR2OadsEVOaqN4pZJzEbg9W2xK08aR5z1oczMOzCr3ZCfCuwULpnB0Yn55pXl7FJxetvGpHTylL0__rdjMcwY0goSs3xE0j4Uxi6b0GNzCcfroHbWj-0OeyWfEb-MUwpuVZu0wYXM1_TIx_sUr9Lv-OPH61dJptim8YKgDDv9ljQq2BZ3QA
RAPIDAPI_KEY = "скопированный_rapidapi_ключ"
ODDS_API_KEY = ""
EOF
