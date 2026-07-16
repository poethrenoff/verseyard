# API Auth

## Общая информация

**Базовый путь:** `/api/auth/`

**Формат ошибок:**

```json
{
  "error": {
    "message": "Текст ошибки",
    "type": "ErrorType",
    "code": 400,
    "form_errors": {
      "field": [
        "Описание ошибки поля"
      ]
    }
  }
}
```

---

## 1. Вход

Вход в систему по email и паролю.

**`POST /api/auth/login/`**

### Тело запроса

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `email` | `string` | Да | Email автора |
| `password` | `string` | Да | Пароль |

### Ответ `200 OK`

```json
{
  "token": "jwt_token",
  "refresh_token": "refresh_token_string"
}
```

### Ошибки

| Код | Type | Сообщение | Условие |
|-----|------|-----------|---------|
| `400` | `InvalidFormError` | Invalid form | Ошибка валидации формы |
| `400` | `AuthorNotFoundError` | Author not found | Автор не найден |
| `401` | `InvalidPasswordError` | Invalid password | Неверный пароль |
| `403` | `AuthorIsBlockedError` | Author is blocked | Автор заблокирован |

---

## 2. Обновление токена

Обновление JWT-токена доступа по refresh-токену.

**`POST /api/auth/token/refresh/`**

### Тело запроса

```json
{
  "refresh_token": "refresh_token_string"
}
```

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `refresh_token` | `string` | Да | Токен обновления |

### Ответ `200 OK`

```json
{
  "token": "new_jwt_token",
  "refresh_token": "new_refresh_token_string"
}
```

### Ошибки

| Код | Type | Сообщение | Условие |
|-----|------|-----------|---------|
| `400` | `InvalidFormError` | Invalid form | Ошибка валидации формы |
| `400` | `RefreshTokenNotFoundError` | Refresh token not found | Токен обновления не найден |
| `401` | `RefreshTokenExpiredError` | Refresh token expired | Срок действия токена обновления истёк |
| `403` | `AuthorIsBlockedError` | Author is blocked | Автор заблокирован |

---

## 3. Информация об авторе

Получение информации о текущем авторизованном авторе.

**`GET /api/auth/info/`**

### Запрос

Заголовок `Authorization: Bearer <token>`

### Ответ `200 OK`

```json
{
  "id": 1,
  "name": "Имя Автора",
  "email": "user@example.com"
}
```

### Ошибки

| Код | Type | Сообщение | Условие |
|-----|------|-----------|---------|
| `401` | `InvalidJWTTokenError` | Invalid JWT token | Неверный или отсутствующий JWT токен |
| `403` | `AuthorIsBlockedError` | Author is blocked | Автор заблокирован |

---

## Сводная таблица эндпоинтов

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/auth/login/` | Вход в систему |
| `POST` | `/api/auth/token/refresh/` | Обновление токена |
| `GET` | `/api/auth/info/` | Информация об авторе |
