import requests

try:
    print("Пробуем достучаться до 7TV...")
    r = requests.get("https://7tv.io", timeout=5)
    print(f"Статус главной страницы: {r.status_code}")

    print("Пробуем отправить GraphQL запрос...")
    payload = {"query": "{ users(query: \"5opka\", limit: 1) { id } }"}
    r_gql = requests.post("https://7tv.io/v3/gql", json=payload, timeout=5)
    print(f"Статус API GQL: {r_gql.status_code}")
    print(f"Ответ сервера: {r_gql.json()}")
except Exception as e:
    print(f"\n❌ СЕТЕВАЯ ОШИБКА: {e}")