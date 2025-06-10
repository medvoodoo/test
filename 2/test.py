import logging
from multiprocessing.connection import answer_challenge # не используется
from pathlib import Path
import shutil

logger = logging.getLogger()


class UnpackServer():
    """Предоставляет методы для работы с файлами"""

    def __init__(self):
        super().__init__() # похоже это от наследования осталось, здесь ненужно
        self.cache_folder = Path('./nastavnik') # не лучшие практики хранение жестко зашитых данных в ините, тем более путей
        self.storage_folder = Path('./storage')

    def _normalize_filepath(self, *args, extension: str = None) -> Path:
        """Метод создает Path до нового файла в папке cache_folder из переданных аргументов и extension"""
        if len(args) < 1:
            pass # я бы сюда поставил ошибку вызова
        #p = Path( self.cache_folder, *args)
        #if extension:
        #    p = p.with_suffix(extension)
        #return p
        # Я не самым красивым образом переписал, но не хочу сильно переделывать реализацию
        if extension:
            args = list(args)
            # делаю последний элемент строкой, обрезаю последнюю точку и добавляю расширение
            args[len(args)-1] = str(args[len(args)-1]).rstrip('.') + extension
        return Path( self.cache_folder, *args)
    
    def get_common_file(self, params):
        """Метод для переноса файлов из папки storage в папку """
        
        logger.info('Get file')
        # добавляю code в общий список, здесь не проработано поведение, если у меня будет name как код, то я перетру один файл вторым
        files = [{'code': params['code']}] + (params.get('file', None) or [])
        
        # Если честно хочется переписать данный код с нуля, т.к.
        # 1. Неочевидная логика работы
        # 2. Логирование уровня error пишется в инфо, нет информации об именах файлов
    
        filepath_list = []

        for file in files:
            # путь до исходного файла
            storage_filepath = self.storage_folder / file['code']
            #if 'type' in file:
            #    filepath = self._normalize_filepath(file['name'], extension=file['type'])
            if 'name' in file:
                filepath = self._normalize_filepath(file['name'], extension=file['type'] if 'type' in file else None)
            else:
                filepath = self.cache_folder / file['code']
            #if not filepath.exists():
            #   logger.info('File path not exist. Get file from storage.')
            # я здесь в начале купился на то, что вроде бы проверяется файл, но в реальности нет транзакционной целостности, и этот код - ошибка. Поменял сообщение на стандарт
            try:
                shutil.copyfile(storage_filepath, filepath)
            except FileNotFoundError: # замена проверке
                logger.info((f"Error: Source file '{storage_filepath}' not found, or destination directory does not exist.")
            except IsADirectoryError:
                logger.info("Error: Source is a directory.")
            except PermissionError:
                logger.info("Error: Permission denied.")
            except shutil.SameFileError:
                logger.info("Error: Source and destination are the same file.")
            except shutil.Error as e:
                logger.info(f"Error during copy: {e}")
            except OSError as e:
                logger.info(f"OS Error: {e}")
                    
            filepath_list.append(str(filepath))
        #if 'path' in params: # похоже недовыпилили из живого кода, работать не будет, т.к. не определен normalize_path
        #    params['blend_path'] = str(normalize_path(params['path']))

        return {
            'method': 'delayed_remove',
            'params': {**params, 'paths': filepath_list},
            'queue': 'cache_queue',
        }



v = UnpackServer()
answer = v.get_common_file( {'code':'main', 'file': [{'code':'3456dcgbyt', 'name':'45.00.679.0.', 'type':'.svg'}]} )

print(Path(r'./nastavnik/main').exists())
print(Path(r'./nastavnik/45.00.679.0.svg').exists())
