# Deployment (локальный контур)

## Предусловия

- Docker Desktop запущен.
- Доступны команды `docker`, `docker compose`, `curl`.

## Команды

1. Создать `.env` (если отсутствует):

- `infra\install_infra.bat` (или `infra\install.bat`)

2. Запустить инфраструктуру:

- `infra\start_infra.bat` (или `infra\start.bat`)

3. Проверить:

- `infra\smoke_test.bat`
- `infra\status.bat`

4. Остановить:

- `infra\stop_infra.bat` (или `infra\stop_all.bat`)

5. Полный сброс (удалит volumes):

- `infra\reset_infra.bat` (или `infra\reset_all.bat`)
