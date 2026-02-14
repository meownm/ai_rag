# Refactor Orchestrator Run Report

Generated at: `2026-02-14T15:38:46.659795+00:00`

| stage | agent | checks | status |
|---|---|---|---|
| discovery | codebase-cartographer | `pytest -q` → warn | warn |
| requirements | requirements-miner | `pytest -q` → warn | warn |
| redesign_refactor | refactor-architect | `pytest -q` → warn | warn |
| simplify | duplication-slayer | `pytest -q` → warn | warn |
| document | contract-scribe | `pytest -q` → warn | warn |
| verify | quality-gatekeeper | `pytest -q` → warn<br>`python tools/drift_check.py` → fail | fail |

## Check outputs

### discovery

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.79s
```

### requirements

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.78s
```

### redesign_refactor

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.89s
```

### simplify

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.98s
```

### document

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.78s
```

### verify

#### `pytest -q` (warn, rc=2)
```
<clipped 19 lines>
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py:5: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_anti_hallucination.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_anti_hallucination.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_anti_hallucination.py:3: in <module>
    from app.services import anti_hallucination
services/corporate-rag-service/app/services/anti_hallucination.py:7: in <module>
    from app.services.retrieval import lexical_score, vector_score
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_confluence_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_confluence_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_confluence_connector.py:4: in <module>
    from app.services.connectors.confluence import ConfluencePagesConnector, storage_html_to_markdown
services/corporate-rag-service/app/services/connectors/confluence.py:16: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_file_catalog_connector.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_file_catalog_connector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_file_catalog_connector.py:4: in <module>
    from app.services.connectors.file_catalog import FileCatalogConnector
services/corporate-rag-service/app/services/connectors/file_catalog.py:11: in <module>
    from app.services.file_ingestion import FileByteIngestor
services/corporate-rag-service/app/services/file_ingestion.py:8: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_fts_retrieval.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_fts_retrieval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_fts_retrieval.py:1: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_ingest_worker.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_ingest_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_ingest_worker.py:3: in <module>
    from app.workers import ingest_worker
services/corporate-rag-service/app/workers/ingest_worker.py:7: in <module>
    from sqlalchemy import text
E   ModuleNotFoundError: No module named 'sqlalchemy'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_telemetry_latency.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_telemetry_latency.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_telemetry_latency.py:3: in <module>
    from app.services.telemetry import emit_metric, log_stage_latency, metric_samples, reset_metrics
services/corporate-rag-service/app/services/telemetry.py:5: in <module>
    from app.core.logging import log_event
services/corporate-rag-service/app/core/logging.py:9: in <module>
    from pythonjsonlogger import jsonlogger
E   ModuleNotFoundError: No module named 'pythonjsonlogger'
_ ERROR collecting services/corporate-rag-service/tests/unit/test_tenant_isolation.py _
ImportError while importing test module '/workspace/ai_rag/services/corporate-rag-service/tests/unit/test_tenant_isolation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/root/.pyenv/versions/3.10.19/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
services/corporate-rag-service/tests/unit/test_tenant_isolation.py:5: in <module>
    from app.services.retrieval import hybrid_rank
services/corporate-rag-service/app/services/retrieval.py:5: in <module>
    from app.core.config import settings
services/corporate-rag-service/app/core/config.py:4: in <module>
    from pydantic import AliasChoices, Field, computed_field, field_validator, model_validator
E   ModuleNotFoundError: No module named 'pydantic'
=========================== short test summary info ============================
ERROR services/corporate-rag-service/tests/integration/test_confluence_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/integration/test_file_catalog_structure_regression_integration.py
ERROR services/corporate-rag-service/tests/unit/test_anti_hallucination.py
ERROR services/corporate-rag-service/tests/unit/test_confluence_connector.py
ERROR services/corporate-rag-service/tests/unit/test_file_catalog_connector.py
ERROR services/corporate-rag-service/tests/unit/test_fts_retrieval.py
ERROR services/corporate-rag-service/tests/unit/test_ingest_worker.py
ERROR services/corporate-rag-service/tests/unit/test_telemetry_latency.py
ERROR services/corporate-rag-service/tests/unit/test_tenant_isolation.py
!!!!!!!!!!!!!!!!!!! Interrupted: 9 errors during collection !!!!!!!!!!!!!!!!!!!!
28 skipped, 9 errors in 0.77s
```

#### `python tools/drift_check.py` (fail, rc=1)
```
<clipped 100 lines>
        "python-json-logger",
        "sentence-transformers",
        "uvicorn"
      ],
      "aligned": [
        "fastapi:^0.115.0",
        "pydantic-settings:^2.6.1",
        "python-json-logger:^2.0.7",
        "sentence-transformers:^3.3.1",
        "uvicorn:^0.30.0"
      ],
      "mismatches": [],
      "ok": true
    },
    {
      "name": "enum:source_type",
      "missing_in_code": [],
      "extra_in_code": [
        "FILE_UPLOAD_OBJECT"
      ],
      "ok": false
    },
    {
      "name": "enum:source_status",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:tenant_role",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:citations_mode",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:only_sources_mode",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:job_type",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:job_status",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:link_type",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:pipeline_stage",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:pipeline_stage_status",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:event_type",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:log_data_mode",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:error_code",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:only_sources_verdict",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:health_status",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:embeddings_encoding_format",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    },
    {
      "name": "enum:embeddings_response_object",
      "missing_in_code": [],
      "extra_in_code": [],
      "ok": true
    }
  ]
}
```
