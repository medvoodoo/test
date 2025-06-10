import os
from aiohttp import web
import jwt
import uuid
import datetime
import asyncpg
from dotenv import load_dotenv


# Загружаем переменные среды из .env-файла
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
ALGORITHM = 'HS256'
DB_URL = os.getenv('DATABASE_URL') or 'postgresql://medved:pass@localhost/test_time'

# Создаем пул соединений к БД
async def init_db(app):
    app['db'] = await asyncpg.create_pool(DB_URL)

# Закрываем соединение с БД
async def close_db(app):
    await app['db'].close()


@web.middleware
async def auth_middleware(request, handler):
    '''проверяем наличие открытой сессии'''
    token = request.headers.get('Authorization', None)
    if not token:
        raise web.HTTPUnauthorized(text='Missing authorization header.')

    try:
        decoded_token = jwt.decode(token.split()[1], SECRET_KEY, algorithms=ALGORITHM)
        user_id = int(decoded_token.get('user_id'))
        # Проверяем наличие токена в таблице SESSIONS
        async with request.app['db'].acquire() as conn:
            session_exists = await conn.fetchval(
                ''' SELECT COUNT(*) FROM SESSIONS WHERE id=$1 AND users_id=$2 AND logining_is=true ''',
                uuid.UUID(decoded_token.get('session_id')), user_id
            )

            if session_exists < 1:
                raise web.HTTPForbidden(text="Invalid session.")

        return await handler(request, user_id=user_id)
    except Exception as e:
        print(e)
        raise web.HTTPUnauthorized(text=str(e))

# Обработчик GET-запросов для получения расписания уроков
async def my_timetable_handler(request, *, user_id=None):
    date_str = request.query.get('date')
    if not date_str:
        raise web.HTTPBadRequest(text="Date parameter is required.")

    try:
        requested_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid date format. Use YYYY-MM-DD.")

    async with request.app['db'].acquire() as conn:
        rows = await conn.fetch(
            """ SELECT tt.id, u.surname || ' ' || u.name AS teacher, g.name AS group_name, st.name AS time_slot, tt.data, tt.room, tt.discipline_name FROM TIMETABLES tt JOIN USERS u ON tt.users_id=u.id JOIN GROUPS g ON tt.groups_id=g.id JOIN START_TIMES st ON tt.start_times_id=st.id WHERE tt.data=$1 AND tt.users_id=$2 ORDER BY st.name ASC """,
            requested_date, user_id
        )
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'teacher': row['teacher'],
            'group': row['group_name'],
            'start_time': row['time_slot'],
            'date': str(row['data']),
            'room': row['room'],
            'discipline': row['discipline_name']
        })

    return web.json_response(result)

# Основной запуск приложения
if __name__ == '__main__':
    print(jwt.encode({"user_id": '2', "session_id": "dfdc66fa-9a36-4247-a130-67f7b1988cd7"}, SECRET_KEY, algorithm=ALGORITHM))
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get('/timetables/my', my_timetable_handler)
    app.on_startup.append(init_db)
    app.on_cleanup.append(close_db)
    web.run_app(app, port=8080)
