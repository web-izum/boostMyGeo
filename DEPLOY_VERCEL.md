# AI Visibility MVP - Деплой на Vercel

Пошаговое руководство по развертыванию AI Visibility MVP на Vercel.

## 📁 Структура проекта для Vercel

```
ai-visibility-mvp/
├── api/
│   ├── main.py                    # Главное FastAPI приложение
│   ├── config.py                  # Конфигурация
│   ├── database.py                # SQLite база данных  
│   ├── file_processor.py          # Обработка файлов
│   ├── metrics.py                 # Расчет метрик
│   ├── openai_client.py           # OpenAI API клиент
│   └── email_service.py           # Email сервис
├── vercel.json                    # Конфигурация Vercel
├── requirements.txt               # Python зависимости
└── README.md                      # Документация
```

## 🚀 Шаги деплоя

### 1. Подготовка проекта

1. **Создайте новый репозиторий** на GitHub
2. **Склонируйте репозиторий** локально:
   ```bash
   git clone https://github.com/yourusername/ai-visibility-mvp.git
   cd ai-visibility-mvp
   ```

3. **Создайте структуру файлов** согласно списку выше
4. **Скопируйте все файлы** из этого проекта в соответствующие папки

### 2. Настройка переменных окружения

В Vercel Dashboard:
1. Перейдите в **Settings → Environment Variables**
2. Добавьте следующие переменные:

```bash
# OpenAI настройки
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o

# SMTP настройки для email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=noreply@yourcompany.com
SMTP_TLS=true

# Опциональные настройки
MAX_UPLOAD_MB=10
ALLOW_RETRY_SAME_FILE=false
```

### 3. Настройка SMTP (Gmail)

1. **Включите 2FA** в Google Account
2. **Создайте App Password**:
   - Google Account → Security → App passwords
   - Выберите "Mail" и создайте пароль
3. **Используйте App Password** как `SMTP_PASS`

### 4. Деплой на Vercel

#### Вариант A: Через Vercel Dashboard
1. Зайдите на [vercel.com](https://vercel.com)
2. Нажмите **"New Project"**
3. **Import** ваш GitHub репозиторий
4. Vercel автоматически определит настройки
5. Нажмите **"Deploy"**

#### Вариант B: Через Vercel CLI
```bash
# Установка Vercel CLI
npm i -g vercel

# Логин в Vercel
vercel login

# Деплой проекта
vercel --prod
```

### 5. После деплоя

1. **Проверьте функциональность**:
   - Откройте ваш домен: `https://your-project.vercel.app`
   - Протестируйте скачивание шаблона
   - Проверьте загрузку файла

2. **Настройте кастомный домен** (опционально):
   - В Vercel Dashboard → Settings → Domains
   - Добавьте ваш домен

## ⚠️ Важные особенности Vercel

### Ограничения serverless
- **Время выполнения**: макс 10 секунд на Free плане
- **Память**: ограничена для serverless функций
- **Файловая система**: только `/tmp` доступен для записи
- **База данных**: SQLite может работать нестабильно

### Рекомендации
1. **Используйте внешние сервисы**:
   - База данных: Supabase, PlanetScale
   - File storage: S3, Cloudinary
   - Email: SendGrid, Resend

2. **Оптимизация холодного старта**:
   - Минимизируйте импорты
   - Используйте кэширование

## 🔧 Альтернативная конфигурация с внешними сервисами

### Supabase вместо SQLite

1. **Создайте проект** на [supabase.com](https://supabase.com)
2. **Добавьте переменные** в Vercel:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   ```

3. **Обновите database.py** для работы с PostgreSQL

### SendGrid для email

1. **Зарегистрируйтесь** на [sendgrid.com](https://sendgrid.com)
2. **Получите API ключ**
3. **Обновите переменные**:
   ```bash
   SENDGRID_API_KEY=your-sendgrid-key
   ```

## 📊 Мониторинг и отладка

### Vercel функции
- **Logs**: Vercel Dashboard → Functions → View Function Logs
- **Analytics**: встроенная аналитика трафика
- **Edge Network**: глобальное распределение

### Отладка проблем
1. **Проверьте логи** в Vercel Dashboard
2. **Валидируйте переменные окружения**
3. **Тестируйте локально** перед деплоем:
   ```bash
   vercel dev
   ```

## ✅ Чеклист готовности

- [ ] Все файлы загружены в репозиторий
- [ ] vercel.json настроен правильно
- [ ] requirements.txt содержит все зависимости
- [ ] Переменные окружения настроены в Vercel
- [ ] SMTP настроен и протестирован
- [ ] OpenAI API ключ действителен
- [ ] Проект успешно деплоится
- [ ] Лендинг открывается корректно
- [ ] Скачивание шаблона работает
- [ ] Загрузка файлов функционирует

## 🎯 Результат

После успешного деплоя у вас будет:
- ✅ Рабочий лендинг на вашем домене
- ✅ Функция скачивания CSV шаблона
- ✅ Обработка файлов с анализом AI видимости
- ✅ Отправка результатов на email
- ✅ Геотаргетированный анализ по странам
- ✅ Автоматический расчет AIV-Score