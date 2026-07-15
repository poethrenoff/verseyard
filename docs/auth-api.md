# Auth API

## POST /api/auth/login

Вход в систему.

### Запрос

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

### Ответ

```json
{
  "token": "jwt_token",
  "refresh_token": "refresh_token_string"
}
```

### Ошибки

- `InvalidFormError` (400): Ошибка валидации формы.
- `AuthorNotFoundError` (400): Автор не найден.
- `InvalidPasswordError` (401): Неверный пароль.
- `AuthorIsBlockedError` (403): Автор заблокирован.

## POST /api/auth/token/refresh/

Обновление токена доступа.

### Запрос

```json
{
  "refresh_token": "refresh_token_string"
}
```

### Ответ

```json
{
  "token": "new_jwt_token",
  "refresh_token": "new_refresh_token_string"
}
```

### Ошибки

- `InvalidFormError` (400): Ошибка валидации формы.
- `RefreshTokenNotFoundError` (400): Токен обновления не найден.
- `RefreshTokenExpiredError` (401): Срок действия токена обновления истек.
- `AuthorIsBlockedError` (403): Автор заблокирован.

## GET /api/auth/info/

Получение информации о текущем авторизованном авторе.

### Запрос

Заголовок `Authorization: Bearer <token>`

### Ответ

```json
{
  "id": 1,
  "name": "Имя Автора",
  "email": "user@example.com"
}
```

### Ошибки

- `InvalidJWTTokenError` (401): Неверный или отсутствующий JWT токен.
- `AuthorIsBlockedError` (403): Автор заблокирован.
