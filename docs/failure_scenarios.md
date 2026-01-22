# Failure scenarios

## Docker Desktop не запущен
**Симптом:** `install_prereqs.bat` сообщает, что Docker недоступен.  
**Действие:** запустить Docker Desktop и повторить.

## Порт занят
**Симптом:** `docker compose up` падает из-за binding error.  
**Действие:** изменить соответствующий `*_HOST_PORT` в `.env`, обновить `ports_registry.md` при принятом изменении.

## PostgreSQL не становится healthy
**Симптом:** `db-migrator` не стартует из-за `depends_on` healthcheck.  
**Действие:** `docker logs <project>-postgres`, проверить пароль/диск, затем `infra\reset_all.bat` и повторить.

## MinIO init не создаёт бакеты
**Симптом:** `minio-init` падает или бакетов нет.  
**Действие:** проверить `MINIO_ROOT_USER/MINIO_ROOT_PASSWORD`, затем повторить `docker compose run --rm minio-init`.
