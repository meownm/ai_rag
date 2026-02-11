\# Chunking Specification v1



\## 1. Назначение



Определить детерминированную стратегию чанкирования для корпоративного RAG:



\- сохранять структуру документа (Markdown)

\- обеспечивать стабильные ссылки для цитирования

\- давать предсказуемое качество retrieval + rerank

\- быть совместимой с Confluence и файловыми документами (PDF/DOC/DOCX/XLS/PPT) после нормализации в Markdown



LLM на этапе preprocessing запрещён.



---



\## 2. Термины



\- \*\*md\_document\*\* — нормализованный Markdown текст документа.

\- \*\*block\*\* — структурный элемент Markdown (heading, paragraph, list, table, codeblock, quote).

\- \*\*section\*\* — диапазон блоков под одним заголовком (headings\_path).

\- \*\*chunk\*\* — итоговая единица индексации (md\_text + metadata + boundaries).



---



\## 3. Вход и выход



\### 3.1 Вход



\- md\_document (строка)

\- metadata (tenant\_id, source\_type, source\_url, title, author, updated\_at, labels, space/page ids, file\_path и т.п.)



\### 3.2 Выход (chunk)



Для каждого chunk обязательно:



\- `chunk\_id` (stable id)

\- `tenant\_id`

\- `document\_id`

\- `chunk\_type` (enum): `paragraph | list | table | code | quote | mixed`

\- `headings\_path` (array of strings)

\- `md\_text` (string)

\- `char\_start`, `char\_end` (позиции в md\_document)

\- `block\_start\_idx`, `block\_end\_idx` (позиции в массиве blocks)

\- `token\_estimate` (integer)

\- `source\_url` / `file\_path` (в зависимости от источника)



---



\## 4. Параметры (фиксированные значения v1)



\### 4.1 Token budgets



\- `MAX\_TOKENS\_PER\_CHUNK = 900`

\- `TARGET\_TOKENS\_PER\_CHUNK = 650`

\- `MIN\_TOKENS\_PER\_CHUNK = 120`

\- `OVERLAP\_TOKENS = 80`



\### 4.2 Overlap policy



Overlap применяется \*\*только\*\* для chunk\_type `paragraph` и `mixed`.

Для `table` и `list` overlap запрещён (чтобы не плодить дубли).



---



\## 5. Парсинг Markdown в blocks



Markdown разбирается в последовательность blocks:



\- Heading (H1..H6)

\- Paragraph

\- List (включая вложенные)

\- Table

\- CodeBlock

\- Quote

\- HorizontalRule (как boundary, не входит в чанки)



Каждый block имеет:

\- type

\- raw\_md\_text

\- char\_start/char\_end

\- token\_estimate



---



\## 6. Правила формирования sections (headings\_path)



\- `headings\_path` обновляется на каждом Heading.

\- Heading блок \*\*не включается\*\* в chunk как самостоятельный chunk.

\- Heading текст добавляется в metadata `headings\_path`.

\- Если после Heading идёт контент — он чанкируется в рамках этой секции.

\- Если документ не содержит Heading — `headings\_path = \[]`.



---



\## 7. Правила чанкирования по типам



\### 7.1 Paragraph blocks



\- Абзацы объединяются в chunk до достижения `TARGET\_TOKENS\_PER\_CHUNK`.

\- Если объединение превысит `MAX\_TOKENS\_PER\_CHUNK`, chunk закрывается до добавления абзаца.

\- Если отдельный абзац > `MAX\_TOKENS\_PER\_CHUNK`:

&nbsp; - он делится по предложениям (sentence split) до `MAX\_TOKENS\_PER\_CHUNK`

&nbsp; - sentence split использует не-LLM библиотеку (например, razdel/nltk/punkt), язык определяется эвристически



\### 7.2 List blocks



\- Один list блок формирует один chunk типа `list`, если он <= `MAX\_TOKENS\_PER\_CHUNK`.

\- Если list > `MAX\_TOKENS\_PER\_CHUNK`:

&nbsp; - делить по верхнеуровневым bullet items

&nbsp; - вложенные элементы остаются с родительским item

\- `list` chunks не имеют overlap.



\### 7.3 Table blocks



\- Таблица формирует один chunk типа `table`, если <= `MAX\_TOKENS\_PER\_CHUNK`.

\- Если таблица > `MAX\_TOKENS\_PER\_CHUNK`:

&nbsp; - таблица разбивается по строкам, заголовок таблицы (header row) повторяется в каждом table-chunk

&nbsp; - размер table-chunk целится в `TARGET\_TOKENS\_PER\_CHUNK`, но не превышает `MAX\_TOKENS\_PER\_CHUNK`

\- `table` chunks не имеют overlap.



\### 7.4 Code blocks / Quote blocks



\- CodeBlock → chunk\_type `code`

\- Quote → chunk\_type `quote`

\- если превышает лимит — делить по строкам/абзацам с соблюдением `MAX\_TOKENS\_PER\_CHUNK`

\- overlap запрещён



\### 7.5 Mixed chunks



Если внутри одной секции идёт короткая последовательность разных блоков (например, paragraph + short list),

и общий размер < `TARGET\_TOKENS\_PER\_CHUNK`, разрешено объединение в `mixed`.

Приоритет:

\- не смешивать `table` с другими типами (table всегда отдельный)

\- не смешивать `code` с другими типами



---



\## 8. Boundary rules (когда закрывать chunk)



Chunk закрывается, если:



\- следующий block — Heading (смена секции)

\- добавление следующего блока превысит `MAX\_TOKENS\_PER\_CHUNK`

\- текущий chunk уже >= `TARGET\_TOKENS\_PER\_CHUNK` и следующий блок начинается с “тяжёлого” типа:

&nbsp; - table

&nbsp; - list

&nbsp; - code



---



\## 9. Stable chunk\_id



`chunk\_id` должен быть стабильным при повторной индексации, если md\_document не изменился.



Рекомендуемая формула:



`chunk\_id = sha256(document\_id + ":" + block\_start\_idx + ":" + block\_end\_idx + ":" + char\_start + ":" + char\_end)`



(sha256 в hex)



---



\## 10. Quality checks (детерминированные)



После чанкирования:



\- каждый chunk:

&nbsp; - `token\_estimate <= MAX\_TOKENS\_PER\_CHUNK` (кроме редких случаев sentence-split ошибок, которые считаются bug)

&nbsp; - `token\_estimate >= MIN\_TOKENS\_PER\_CHUNK`  

&nbsp;   исключения: последний chunk секции или одиночный table/list/code

\- `char\_start/char\_end` монотонно возрастают

\- chunks не перекрываются по char-диапазонам, кроме overlap (paragraph/mixed)

\- overlap корректно применяется по токен-границе, не ломая markdown (не разрывать таблицы и списки)



---



\## 11. Тестовые случаи (обязательные)



1\) Документ с H1/H2/H3 + абзацы  

2\) Документ с вложенными списками  

3\) Документ с большой таблицей > 200 строк  

4\) Документ без заголовков (только текст)  

5\) Документ с code block  

6\) Confluence страница с несколькими секциями и ссылками  

7\) PDF после нормализации: таблица + списки + абзацы  



Для каждого теста проверять:

\- число чанков

\- типы чанков

\- лимиты токенов

\- стабильность chunk\_id при повторном прогоне



---



\## 12. Совместимость с ранжированием



Рекомендуемые boosts (не реализация, а контракт ожиданий):



\- boost по `headings\_path` совпадению с запросом

\- boost по `title` совпадению

\- boost по `labels`

\- boost по связанности Confluence (outgoing/incoming links)



