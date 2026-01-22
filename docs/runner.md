# Runner

## Назначение
Единая точка входа для запуска инфраструктуры и сервисов в локальном контуре.

## Команды
- `run.bat infra` — поднять инфраструктуру
- `run.bat verify` — проверить консистентность (порты, очереди, targets) и сгенерировать отчет
- `run.bat smoke` — smoke с cleanup очередей и batch jobs
- `run.bat urls` — вывести URL Swagger, учитывая `.env`
- `run.bat service <name>` — запустить сервис
- `run.bat worker <name>` — запустить воркер
- `run.bat test-worker` — запустить `services/test-worker`

## Примечания
- `open_urls_all.bat` показывает предупреждение при отличии `APP_PORT` в `.env` от `docs/ports_registry.md`.
