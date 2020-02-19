#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
    Filename : spooler_renamer.py
    Date: 17.11.2017 07:02
    Project: pySpoolerRenamer
    AUTHOR : Sergey Utkin
"""

import logging
from logging import handlers, Formatter
import os
import sys
import datetime
import time
from ConfigParser import ConfigParser, MissingSectionHeaderError
import shutil

try:
    import argparse
except ImportError:
    print("Не доступна библиотека python-argparse, просьба установить из rmp")
    sys.exit(1)

__author__ = "Sergey V. Utkin"
__version__ = "0.1.11"
__email__ = "utkins01@gmail.com"

__TMPDIR__ = '/tmp/pySpoolerRenamer'
__TMPFILES__ = {"run": "pySpoolerRenamer.pid"}

# Исключение fallback для python2
__DEFAULT_CONFIG__ = {
    "main_log_file": 'spooler_renamer.log',
    "main_log_level": 'INFO',
    "main_log_backup_count": 5,
    "main_log_max_bytes": 10485760,
    "main_mtime": 60,
    "main_log_write_exception": 'False',
    "main_delete_empty_folder_level": 2

}


class Log:
    def __init__(self, log_file, log_level, backup_count, max_bytes, dry=False):
        self.logger = logging.getLogger()
        if log_level == 'CRITICAL':
            self.logger.setLevel(logging.CRITICAL)
        elif log_level == 'ERROR':
            self.logger.setLevel(logging.ERROR)
        elif log_level == 'WARNING':
            self.logger.setLevel(logging.WARNING)
        elif log_level == 'INFO':
            self.logger.setLevel(logging.INFO)
        elif log_level == 'DEBUG':
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.NOTSET)
        if dry:
            self.handler = logging.StreamHandler(sys.stdout)
            self.logger.setLevel(logging.DEBUG)
        else:
            self.handler = handlers.RotatingFileHandler(log_file, backupCount=backup_count, maxBytes=max_bytes)
        log_format = Formatter('[%(asctime)s] [%(levelname)-8s] - %(message)s')
        self.handler.setFormatter(log_format)
        self.logger.addHandler(self.handler)

    def error(self, text, exc_info=False):
        self.logger.error(text, exc_info=exc_info)

    def info(self, text, exc_info=False):
        self.logger.info(text, exc_info=exc_info)

    def warning(self, text, exc_info=False):
        self.logger.warning(text, exc_info=exc_info)

    def debug(self, text, exc_info=False):
        self.logger.debug(text, exc_info=exc_info)

    def __del__(self):
        self.logger.removeHandler(self.handler)


class File:
    datetime = None
    region_id = None
    point_id = None
    region_name = None
    data_name = None
    type = None
    journal = None
    filename = None
    unixtime = None
    path = None
    full_path = None
    output_format_file = None
    output_format_hardlink = None
    output_dir = None

    def __init__(self, file_path, path_map, file_config):
        self.path = file_path
        self.path_map = path_map
        self.data_name = self.path_map['{data_name}']
        self.filename = self.path_map['{filename}']
        self.output_format_file = get_config(file_config, self.data_name, 'output_format_file')
        self.output_dir = get_config(file_config, self.data_name, 'output_dir')
        self.output_format_hardlink = get_config(file_config, self.data_name, 'output_format_hardlink')
        self.full_path = os.path.join(get_config(file_config, 'main', 'input_dir'), self.path)

        self.datetime = self.get_map('{datetime}')
        if self.datetime is None:
            m_time = os.stat(self.full_path).st_mtime
            m_time = datetime.datetime.fromtimestamp(m_time)
            if get_config(file_config, self.data_name, 'datetime_format') is None:
                date_format = '%Y%m%d_%H%M%S'
            else:
                date_format = get_config(file_config, self.data_name, 'datetime_format')
            self.datetime = str(m_time.strftime(date_format))

        if get_config(file_config, self.data_name, 'region_id') is not None:
            self.region_id = get_config(file_config, self.data_name, 'region_id')
        else:
            self.region_id = self.get_map('{region_id}')

        if get_config(file_config, self.data_name, 'point_id') is not None:
            self.point_id = get_config(file_config, self.data_name, 'point_id')
        else:
            self.point_id = self.get_map('{point_id}')

        if get_config(file_config, self.data_name, 'type') is not None:
            self.type = get_config(file_config, self.data_name, 'type')
        else:
            self.type = self.get_map('{type}')

        if get_config(file_config, self.data_name, 'region_name') is not None:
            self.region_name = get_config(file_config, self.data_name, 'region_name')
        else:
            self.region_name = self.get_map('{region_name}')

        if get_config(file_config, self.data_name, 'journal') is not None:
            self.journal = get_config(file_config, self.data_name, 'journal')
        else:
            self.journal = self.get_map('{journal}')

    def get_map(self, m):
        try:
            return self.path_map[m]
        except KeyError:
            return None

    def output_file(self):
        self.unixtime = int(time.time())
        filename = str(self.output_format_file).format(**self.__dict__)
        return os.path.join(self.output_dir, filename)

    def hardlink_file(self):
        self.unixtime = int(time.time())
        filename = str(self.output_format_hardlink).format(**self.__dict__)
        return filename

    def check_lz4(self):
        pass

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


def list_subtraction(list1, list2):
    """
    Разница между list1 и list2
    :param list1: list
    :param list2: list
    :return: list
    """
    results = list1[:]
    results.reverse()
    for loop in range(0, len(list2)):
        if list2[loop] == list1[loop]:
            results.pop()
    results.reverse()
    return results


def find_file(directory, modify_time):
    files = []
    for list_dir in os.listdir(directory):
        f_mtime = os.stat(os.path.join(directory, list_dir)).st_mtime
        unixtime = int(time.time())
        if os.path.isfile(os.path.join(directory, list_dir)) and unixtime - f_mtime > int(modify_time):
            files.append(os.path.join(directory, list_dir))
        elif os.path.isdir(os.path.join(directory, list_dir)):
            files += find_file(os.path.join(directory, list_dir), modify_time)
    return files


def find_folder(directory, modify_time):
    folder_list = []
    for list_dir in os.listdir(directory):
        d_mtime = os.stat(os.path.join(directory, list_dir)).st_mtime
        unixtime = int(time.time())
        if os.path.isdir(os.path.join(directory, list_dir)) and int(unixtime) - int(d_mtime) > int(modify_time):
            folder_list.append(os.path.join(directory, list_dir))
        if os.path.isdir(os.path.join(directory, list_dir)):
            folder_list += find_folder(os.path.join(directory, list_dir), modify_time)
    folder_list.sort(key=len, reverse=True)
    return folder_list


def get_config(file_config, section, option, type_value=str):
    if file_config.has_option(section, option):
        return type_value(file_config.get(section, option, raw=True))
    elif file_config.has_option('default', option):
        return type_value(file_config.get('default', option, raw=True))
    elif "{0}_{1}".format(section, option) in __DEFAULT_CONFIG__:
        return type_value(__DEFAULT_CONFIG__["{0}_{1}".format(section, option)])
    else:
        return None


def str2bool(s):
    if str(s).lower() in ['true', '1', 't', 'y', 'yes']:
        return True
    else:
        return False


def check_ignore(mapper_file, file_config):
    if file_config.has_option('ignore', 'region_id'):
        for ignore in str(file_config.get('ignore', 'region_id')).split(','):
            if ignore == mapper_file['{region_id}']:
                return False
    if file_config.has_option('ignore', 'point_id'):
        for ignore in str(file_config.get('ignore', 'point_id')).split(','):
            if ignore == mapper_file['{point_id}']:
                return False
    if file_config.has_option('ignore', 'region_name'):
        for ignore in str(file_config.get('ignore', 'region_name')).split(','):
            if ignore == mapper_file['{region_name}']:
                return False
    if file_config.has_option('ignore', 'data_name'):
        for ignore in str(file_config.get('ignore', 'data_name')).split(','):
            if ignore == mapper_file['{data_name}']:
                return False
    if file_config.has_option('ignore', 'type'):
        for ignore in str(file_config.get('ignore', 'type')).split(','):
            if ignore == mapper_file['{type}']:
                return False
    if file_config.has_option('ignore', 'journal'):
        for ignore in str(file_config.get('ignore', 'journal')).split(','):
            if ignore == mapper_file['{journal}']:
                return False
    if file_config.has_option('ignore', 'filename'):
        for ignore in str(file_config.get('ignore', 'filename')).split(','):
            if ignore == mapper_file['{filename}']:
                return False
    return True


def get_cmdline(p):
    cmdline = "/proc/{pid}/cmdline"
    if not os.path.isfile(cmdline.format(pid=p)):
        return []
    with open(cmdline.format(pid=p)) as openfile:
        cmd = openfile.readline()

    return cmd.split('\x00')


def check_run_app(cmdline):
    for i in cmdline:
        if str(i).split(os.sep) == str(__file__).split(os.sep)[-1]:
            return False
    return True


def check_cross_device(file1, file2):
    """
    Возвращает True если файлы/директории находятся на 1 фаловой системе
    :param file1: path
    :param file2: path
    :return: bool
    """
    if os.stat(os.path.dirname(file1)).st_dev == os.stat(os.path.dirname(file2)).st_dev:
        return True
    return False


def main(conf):
    if not os.path.isfile(conf):
        print('Ошибка чтения конфигурационного файла: {f}'.format(f=conf))
        sys.exit(1)
    configuration = ConfigParser()
    try:
        configuration.read(conf)
    except MissingSectionHeaderError:
        print('Ошибка чтения конфигурационного файла: {f}'.format(f=conf))
        sys.exit(1)

    if not os.path.isdir(os.path.dirname(get_config(configuration, 'main', 'log_file'))):
        print('Ошибка создания файла логирования: {flog}'.format(flog=get_config(configuration, 'main', 'log_file')))
        sys.exit(1)

    try:
        logger = Log(get_config(configuration, 'main', 'log_file'),
                     get_config(configuration, 'main', 'log_level'),
                     get_config(configuration, 'main', 'log_backup_count', type_value=int),
                     get_config(configuration, 'main', 'log_max_bytes', type_value=int),
                     dry=settings['dry_run'])
    except IOError, err:
        print(err)
        sys.exit(1)

    dry_run = settings['dry_run']
    # Проверка запущенного приложения
    if dry_run:
        pass
    elif not os.path.isfile(os.path.join(__TMPDIR__, __TMPFILES__["run"])):
        f = open(os.path.join(__TMPDIR__, __TMPFILES__["run"]), 'w')
        f.write(str(os.getpid()))
        f.close()
    else:
        with open(os.path.join(__TMPDIR__, __TMPFILES__["run"]), 'r') as f:
            tmp_pid = f.readline()
        if check_run_app(get_cmdline(tmp_pid)):
            logger.error('Остался не удаленный pid файл: {0}'.
                         format(os.path.join(__TMPDIR__, __TMPFILES__["run"])))
            if not dry_run:
                os.remove(os.path.join(__TMPDIR__, __TMPFILES__["run"]))
                f = open(os.path.join(__TMPDIR__, __TMPFILES__["run"]), 'w')
                f.write(str(os.getpid()))
                f.close()
        else:
            logger.warning('Приложение уже запущено!!! PID: {pid}'.format(pid=tmp_pid))
            sys.exit(0)

    logger.debug('Запуск pySpoolerRenamer: {0}'.format(__version__))
    logger.debug('Конфигурационный файл: {0}'.format(conf))
    input_dir = get_config(configuration, 'main', 'input_dir')
    mtime = get_config(configuration, 'main', 'mtime', type_value=int)
    exception = str2bool(get_config(configuration, 'main', 'log_write_exception'))
    delete_empty_folder_level = get_config(configuration, 'main', 'delete_empty_folder_level', type_value=int)

    if not os.path.isdir(__TMPDIR__):
        os.mkdir(__TMPDIR__)

    if not os.path.isdir(input_dir):
        logger.error('Отсутствует входной каталог: {0}'.format(input_dir))
        if not dry_run:
            os.remove(os.path.join(__TMPDIR__, __TMPFILES__["run"]))
        sys.exit(1)

    file_list = []
    for i in find_file(input_dir, mtime):
        if len(str(get_config(configuration, 'main', 'input_format')).split('/')) != \
                len(str(os.path.relpath(i, input_dir)).split('/')):
            logger.debug('Некорректно задан формат для директории: {0}'.format(os.path.relpath(i, input_dir)))
        else:
            mapper = dict(zip(str(get_config(configuration, 'main', 'input_format')).split('/'),
                              str(os.path.relpath(i, input_dir)).split('/')))
            if check_ignore(mapper, configuration):
                file_list.append(File(os.path.relpath(i, input_dir), mapper, configuration))
            else:
                logger.debug('Файл проигнорирован: {0}'.format(os.path.relpath(i, input_dir)))

    logger.debug('Найдено файлов: {0}'.format(len(file_list)))
    for f in file_list:
        flag_success = True
        empty_delete = get_config(configuration, f.data_name, 'empty_delete')

        if not os.path.isdir(os.path.split(f.output_file())[0]):
            try:
                os.mkdir(os.path.split(f.output_file())[0])
                logger.debug('Создана выходная директория: {0}'.format(os.path.split(f.output_file())[0]))
            except OSError:
                logger.error('Не удалось создать директорию: {0}'.format(os.path.split(f.output_file())[0]))

        if os.path.isfile(f.output_file()) and os.path.getsize(os.path.join(input_dir, f.path)) != 0:
            logger.warning('Не удалось переместить файл: {0}. Файл существует: {1}'.format(
                os.path.join(input_dir, f.path),
                f.output_file()))
        else:
            src = os.path.join(input_dir, f.path)
            dst = f.output_file()
            if not dry_run:
                if f.output_format_hardlink:
                    try:
                        if os.path.isfile(f.hardlink_file()):
                            os.remove(f.hardlink_file())
                        os.link(str(src), str(f.hardlink_file()))
                    except OSError:
                        logger.warning('Не удалось создать hardlink: {0}'.format(f.hardlink_file()), exc_info=exception)

                if os.path.getsize(os.path.join(input_dir, f.path)) == 0 and str2bool(empty_delete):
                    if not dry_run:
                        os.remove(os.path.join(input_dir, f.path))
                    logger.debug('Удален пустой файл: {0}'.format(os.path.join(input_dir, f.path)))
                    flag_success = False
                else:
                    # Проверка файловых систем
                    if check_cross_device(str(src), str(dst)):
                        try:
                            os.rename(str(src), str(dst))
                        except OSError:
                            logger.warning('Не удалось переименновать файл: {0} -> {1}'.format(src, dst),
                                           exc_info=exception)
                            flag_success = False
                    else:
                        try:
                            shutil.move(str(src), str(dst))
                        except OSError:
                            logger.warning('Не удалось переименновать файл: {0} -> {1}'.format(src, dst),
                                           exc_info=exception)
                            flag_success = False

            if flag_success:
                logger.info('Файл {0} переименован {1}'.format(src, dst))

    # Очистка пустых директорий.
    folder = find_folder(input_dir, mtime)
    for f in folder:
        if len(os.listdir(f)) == 0 \
                and len(list_subtraction(f.split(os.sep), input_dir.split(os.sep))) >= delete_empty_folder_level:
            try:
                if not dry_run:
                    os.rmdir(f)
                logger.debug('Удалена пустая директория: {0}'.format(f))
            except OSError:
                logger.warning('Не удалось удалить пустую директорию: {0}'.format(f), exc_info=exception)

    logger.debug('Работа pySpoolerRenamer завершена')
    if not dry_run:
        os.remove(os.path.join(__TMPDIR__, __TMPFILES__["run"]))
    del configuration
    del logger


parser = argparse.ArgumentParser(description='Сборщик IDR файлов с файлового спулера и Сонаты.')
parser.add_argument('--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))
parser.add_argument('--config', type=str, action="store", help='Директория конфигурационных файлов')
parser.add_argument('--dry-run', action="store_true", help='Проверка работы, без внесения изменений')
settings = vars(parser.parse_args())
script_path = os.path.dirname(os.path.abspath(sys.argv[0]))

if not os.path.isdir(__TMPDIR__):
    os.mkdir(__TMPDIR__)

if settings['config']:
    config = settings['config']
else:
    if os.path.isdir(os.path.join(script_path, 'conf.d')):
        config = os.path.join(script_path, 'conf.d')
    elif os.path.isfile(os.path.join(script_path, 'spooler_renamer.conf')):
        config = os.path.join(script_path, 'spooler_renamer.conf')
    else:
        config = False

if os.path.isfile(config) and os.path.split(config)[-1].split('.')[-1] in ["cfg", "conf"]:
    main(config)
elif os.path.isdir(config):
    for config_file in os.listdir(config):
        if os.path.split(config_file)[-1].split('.')[-1] in ["cfg", "conf"]:
            main(os.path.join(config, config_file))
else:
    print('Отсутствует конфигурационный файл!!!')
    print('Работа приложения остановлена!!!')


sys.exit(0)
