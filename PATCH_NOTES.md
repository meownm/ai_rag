# EPIC-02 Final Patch Notes

Этот архив — overlay + manual merge snippets.

## Как применять
1) Распаковать поверх корня репозитория (с сохранением структуры).
2) Применить ручные изменения из `infra_patches/MERGE_SNIPPETS.md`.
3) Убедиться, что в корне есть `smoke_test_all.bat` и `verify_infra_consistency.bat`. Если они у тебя уже есть, добавь в них блоки из MERGE_SNIPPETS.
4) Запуск:
   - `run.bat infra`
   - `run.bat verify`
   - `run.bat test-worker`
   - `run.bat smoke`

## Что этот патч НЕ делает автоматически
- Не редактирует существующие файлы инфры, потому что их структура у тебя может отличаться.
- Не меняет существующий worker template и shared/appkit в твоих сервисах.
  Этот патч добавляет отдельный `services/test-worker`, который замыкает smoke-цепочку EPIC-02.
