pySpoolerRenamer
================

Небольшая утилита переименовывания файлов, создана для массового ренейма потока файлов.

Зависимости
-----------

Для работы скрипта требуется: \* Python 2.7 \*
`python-configparser <https://rpmfind.net/linux/opensuse/update/leap/42.2/oss/noarch/python-configparser-3.5.0-2.1.noarch.rpm>`__

Настройка
---------

Запуск
~~~~~~

Для корректной работы скрипта необходим конфигурационный файл[ы],
который можно задать через ключ запуска приложения **--config**

::

    spooler_renamer.py --config PATH

Если **--config** не задан, сначала ищется директория ***conf.d***, если
ее нет то файл ***spooler\_renamer.conf***.

Имена конфигурационных файлов должны иметь расширение **.conf или
.cfg**, остальные файлы будут игнорироватся.

Для запуска без внесения изменений предназначен ключ **--dry-run**.

::

    spooler_renamer.py --dry-run --config PATH

Синтаксис конфигурационного файла:
----------------------------------

-  [секция]
-  ключ = значение

Секция main
~~~~~~~~~~~

-  **log\_file** - размещение файла логирования. Не обязательное, по
   умолчанию создает файл spooler\_renamer.log
-  **log\_level** - уровень логирования. По умолчанию INFO.
-  **log\_backup\_count** - количество лог файлов.
-  **log\_max\_bytes** - максимальный размер лог файла в байтах.
-  **log\_write\_exception** - вывод trace лога в стиле python.
-  **delete\_empty\_folder\_level** - уровень удаления вложенных
   директории относительно ***input\_dir***, по умолчанию равняется 2.
-  **mtime** - время изменение файла, по истечениею которого можно
   работать с файлом. В секундах.
-  **input\_dir** - Директория входящих файлов.
-  **input\_format** - формат пути до файла относительно **input\_dir**
   \ ``input_format = {datetime}/{point_id}/{data_name}/{filename}``
   обязательное заключение переменных в фигурные скобки ({}) Возможнные
   значение:

   -  **data\_name** - Название входящего потока(\ **Обязательное
      поле**). для каждого потока можно создать отдельную секцию.
   -  **filename** - имя файла(\ **Обязательное поле**).
   -  **datetime** - если параметр не задан в **input\_format**, будет
      сформировано значение в формате **datetime\_format**, на основе
      **st\_ctime** исходного файла.
   -  **region\_id**
   -  **point\_id**
   -  **type**
   -  **region\_name**
   -  **journal**

Секция default
~~~~~~~~~~~~~~

-  **output\_dir** - Директория куда будут складыватся переименнованые
   файлы.
-  **output\_format\_file** - строка формирования имени файла, принимает
   значение как и для **input\_format**.
-  **output\_format\_hardlink** - строка формирования hardlink(требуется
   для мониторинга.) принимает значение как и для **input\_format**. Если не заполнено ингнорируется.
-  **empty\_delete** - флаг удаление пустых файлов.
-  **datetime\_format** - формат значение **datetime**, по умолчанию
   ``%Y%m%d_%H%M%S``, может принимать следующие
   `значения <https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior>`__.

Так же в данную секции можно добавить следующие переменные: \*
**region\_id** \* **point\_id** \* **type** \* **region\_name** \*
**journal**

Секция *data\_name*
~~~~~~~~~~~~~~~~~~~

Данная секиция принимает те же параметры что и в секции **default**
Предназнначена для отделения потоков по **data\_name** и формирования
отдельных выходных параметров.

Секция *ignore*
~~~~~~~~~~~~~~~

В данную секцию можно внести переменные значения которых требуется
игнорировать например для
``input_format = {datetime}/{point_id}/{data_name}/{filename}``
Требуется исключить директорию **point\_id**

::

    [ignore]
    point_id = test1

Директория которая попадет в значение test1, будет исключена из
обработки.

Формат записи \`ключ = значение[, значение, ...] Можно использовать все
значение из **input\_format**, кроме **datetime**

Example
~~~~~~~

::

    [main]
    log_file = spooler_renamer.log
    log_level = DEBUG
    input_dir = input
    input_format = {point_id}/{data_name}/{filename}
    mtime = 60

    [default]
    region_id = 52
    region_name = test
    empty_delete = y
    output_dir = output
    output_format_file = {datetime}_{data_name}.{unixtime}.{region_id}.{point_id}

    [test1]
    output_dir = output/test1
    journal = news
    output_format_file = {datetime}_{journal}.{unixtime}.{data_name}.{region_name}_{region_id}.{point_id}

