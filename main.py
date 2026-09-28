"""
EnglishCard - Приложение для изучения английского языка
"""

import streamlit as st
import psycopg2
import pandas as pd
import random
import os
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

host = os.getenv('HOST')
database = os.getenv('DATABASE')
user = os.getenv('USER')
password = os.getenv('PASSWORD')
port = os.getenv('PORT')

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# РАБОТА С БАЗОЙ ДАННЫХ
# ============================================================

def get_db_connection():
    """
    TODO: Реализовать подключение к PostgreSQL
    Параметры подключения:
    - host: localhost
    - database: english_card
    - user: postgres
    - password: postgres
    """
    conn = psycopg2.connect(
        host=f'{host}',
        database=f'{database}',
        user=f'{user}',
        password=f'{password}',
        port=f'{port}'
    )
    return conn


def init_database():
    """
    TODO: Реализовать создание таблиц, если они не существуют
    Необходимые таблицы:
    1. users (id, username, created_at)
    2. common_words (id, russian_word, english_word, created_at)
    3. user_words (id, user_id, russian_word, english_word, created_at)
    4. learning_stats (id, user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed)

    Также заполнить common_words начальными словами (минимум 10 слов)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Создать таблицы.
    with open('create_tables.sql', 'r', encoding='utf-8') as sql_file:
        sql_script = sql_file.read()

    cursor.execute(sql_script)

    cursor.execute(
        'SELECT id FROM common_words;'
    )
    result = cursor.fetchall()
    if result is None:
        words = [('красный', 'red'), ('семья', 'family'), ('мы', 'we'), ('собака', 'dog'),
                 ('красивый', 'beautiful'), ('кошка', 'cat'), ('желтый', 'yellow'), ('она', 'she'),
                 ('хороший', 'good'), ('он', 'he')]

        cursor.executemany(
            'INSERT INTO common_words (russian_word, english_word) VALUES (%s, %s);',
            words
        )

    conn.commit()
    cursor.close()


def login_user(conn, username):
    """
    TODO: Реализовать вход пользователя
    Если пользователь существует - вернуть его id
    Если нет - создать нового и вернуть его id
    """
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id, username FROM users WHERE username = %s;',
        (username,)
    )
    user = cursor.fetchone()

    if user is not None:
        if user[1] == username:
            user_id = user[0]
            return user_id
    else:
        cursor.execute(
            'INSERT INTO users (username) VALUES (%s) RETURNING id;',
            (username,)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id

    cursor.close()


def get_user_words(user_id):
    """
    TODO: Получить все слова пользователя (общие + персональные)
    Возвращает список словарей: [{'id': 1, 'russian_word': 'красный', 'english_word': 'red', 'word_type': 'common'}, ...]
    """
    conn = get_db_connection()
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT id AS id, russian_word, english_word, 'common' AS word_type FROM common_words
        UNION ALL
        SELECT id AS id, russian_word, english_word, 'user' AS word_type FROM user_words
        WHERE user_id = %s
    """, (user_id,))

    all_words = [dict(row) for row in cursor.fetchall()]
    return all_words

    cursor.close()


def add_personal_word(user_id, russian_word, english_word):
    """
    TODO: Добавить персональное слово для пользователя
    Проверить, нет ли уже такого слова
    Возвращает True/False
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM user_words
        WHERE user_id = %s AND russian_word = %s AND english_word = %s;
    """, (user_id, russian_word, english_word))

    result = cursor.fetchone()

    if result is not None:
        return True
    else:
        cursor.execute("""
            INSERT INTO user_words (user_id, russian_word, english_word) VALUES (%s, %s, %s);
        """, (user_id, russian_word, english_word))

        conn.commit()

    cursor.close()


def delete_personal_word(user_id, word_id):
    """
    TODO: Удалить персональное слово пользователя
    Возвращает True/False
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM user_words 
        WHERE id = %s;
    """, (word_id,))

    conn.commit()
    cursor.close()


def update_stats(user_id, word_id, word_type, is_correct):
    """
    TODO: Обновить статистику изучения слова
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT word_id FROM learning_stats
        WHERE word_id = %s;
    """, (word_id,))
    result = cursor.fetchone()

    if result is not None:
        if is_correct:
            cursor.execute("""
                UPDATE learning_stats
                SET correct_answers = correct_answers + 1, total_attempts = total_attempts + 1,
                last_reviewed = NOW()
                WHERE word_id = %s;
            """, (word_id,))
        else:
            cursor.execute("""
                UPDATE learning_stats
                SET total_attempts = total_attempts + 1, last_reviewed = NOW()
                WHERE word_id = %s;
            """, (word_id,))
    else:
        if is_correct:
            cursor.execute("""
                INSERT INTO learning_stats (user_id, word_id, word_type, correct_answers, total_attempts,
                last_reviewed) VALUES (%s, %s, %s, %s, %s, NOW());
            """, (user_id, word_id, word_type, 1, 1))
        else:
            cursor.execute("""
                INSERT INTO learning_stats (user_id, word_id, word_type, correct_answers, total_attempts,
                last_reviewed) VALUES (%s, %s, %s, %s, %s, NOW());
            """, (user_id, word_id, word_type, 0, 1))

    conn.commit()
    cursor.close()


def get_statistics(user_id):
    """
    TODO: Получить статистику пользователя
    Возвращает словарь со статистикой
    """
    conn = get_db_connection()
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed
        FROM learning_stats
        WHERE user_id = %s;
    """, (user_id,))

    user_stats = [dict(row) for row in cursor.fetchall()]
    return user_stats

    cursor.close()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def generate_options(correct_word, all_words):
    """
    TODO: Сгенерировать 4 варианта ответа для викторины
    Один вариант - правильный перевод, остальные - случайные слова из словаря
    Если слов не хватает, можно добавить слова-заглушки
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    num_words = len(all_words)
    answers = {correct_word}
    options = random.sample(range(0, num_words - 1), 3)
    for option in options:
        answers.add(all_words[option]['english_word'])

    while len(answers) < 4:
        option = random.randint(0, num_words - 1)
        answers.add(all_words[option]['english_word'])

    answers = list(answers)
    return answers

    cursor.close()


# ============================================================
# ИНТЕРФЕЙС ПРИЛОЖЕНИЯ
# ============================================================

def render_sidebar():
    """
    TODO: Реализовать боковую панель с авторизацией
    - Поле для ввода имени
    - Кнопка входа
    - Приветствие после входа
    - Кнопка выхода
    """
    conn = get_db_connection()
    sidebar = st.sidebar
    sidebar.title('Авторизация')
    username = sidebar.text_input('Введите ваше имя: ')
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button('Войти'):
            if username.strip():
                st.session_state.user_id = login_user(conn, username)
                sidebar.write(f'Вы вошли как: {username}')
            else:
                st.error('Ошибка! Введите имя!')
        with col2:
            if st.button('Выйти'):
                sidebar.write('Вы вышли!')
                st.session_state.user_id = None
                st.session_state.username = None


def render_study_tab(words):
    """
    TODO: Реализовать вкладку изучения слов
    - Отображение текущего слова на русском
    - 4 кнопки с вариантами перевода
    - Обработка правильных/неправильных ответов
    - Кнопка следующего слова
    """
    if 'current_word' not in st.session_state or not st.session_state.get('options'):
        st.session_state.current_word = random.choice(words)
        st.session_state.correct_word = st.session_state.current_word['english_word']
        st.session_state.options = generate_options(st.session_state.correct_word, words)

    st.markdown("""
        ### 📖 Изучаем слова
    """)
    st.markdown(f"""
        #### Слово: {st.session_state.current_word['russian_word']}
    """)
    st.markdown("""
        #### Как будет по-английски?
    """)
    st.markdown("""
        #### Выберите перевод:
    """)

    cols = st.columns(4)
    for i, option in enumerate(st.session_state.options):
        click = cols[i].button(option, key=f'btn_{i}', use_container_width=True)
        if click:
            if option == st.session_state.correct_word:
                st.session_state.correct = True
                st.success('Это правильный ответ!')
                update_stats(
                    st.session_state.user_id,
                    st.session_state.current_word['id'],
                    st.session_state.current_word['word_type'],
                    st.session_state.correct)
            else:
                st.session_state.correct = False
                st.error('Это неправильный ответ! Попробуйте снова.')
                update_stats(
                    st.session_state.user_id,
                    st.session_state.current_word['id'],
                    st.session_state.current_word['word_type'],
                    st.session_state.correct)

    next = st.button('Следующее слово', use_container_width=True)
    if next:
        st.session_state.current_word = random.choice(words)
        st.session_state.options = []
        st.rerun()


def render_add_word_tab():
    """
    TODO: Реализовать вкладку добавления слова
    - Поле для ввода слова на русском
    - Поле для ввода перевода
    - Кнопка добавления
    - Уведомление об успешном добавлении
    """
    if 'personal_words' not in st.session_state:
        st.session_state.personal_words = []
    if 'clicked' not in st.session_state:
        st.session_state.clicked = False

    words = get_user_words(st.session_state.user_id)

    personal_words = []
    user_words = 0
    for i in range(len(words)):
        if words[i]['word_type'] == 'user':
            personal_words.append(words[i]['russian_word'])
            user_words += 1

    st.markdown("""
        #### Новое слово
    """)
    russian_word = st.text_input('Введите слово на русском языке: ')
    st.markdown("""
        #### Перевод
    """)
    english_word = st.text_input('Введите перевод на английский язык: ')

    if st.button('Добавить', use_container_width=True):
        st.session_state.clicked = True
        new_word = add_personal_word(st.session_state.user_id, russian_word, english_word)
        if new_word:
            st.write('Такое слово уже есть в базе.')
        else:
            st.session_state.personal_words = []
        st.rerun()

    if st.session_state.clicked:
        st.write(f'Слово добавлено. Количество изучаемых слов: {user_words + 1}.')


def render_delete_word_tab(words):
    """
    TODO: Реализовать вкладку удаления слова
    - Выпадающий список с персональными словами пользователя
    - Кнопка удаления
    - Подтверждение удаления
    """
    if 'personal_words' not in st.session_state:
        st.session_state.personal_words = []

    personal_words = []
    for i in range(len(words)):
        if words[i]['word_type'] == 'user':
            personal_words.append(words[i]['russian_word'])

    selected_word = st.selectbox('Выберите слово: ', personal_words)
    for i in range(len(words)):
        if selected_word == words[i]['russian_word']:
            word_id = words[i]['id']
    deleted_word = st.button('Удалить слово', use_container_width=True)
    if deleted_word:
        st.write('Слово удалено!')
        delete_personal_word(st.session_state.user_id, word_id)
        st.session_state.personal_words = []
        st.rerun()


def render_statistics_tab(user_id):
    """
    TODO: Реализовать вкладку статистики (дополнительное требование)
    - Количество изученных слов
    - Количество попыток
    - Процент правильных ответов
    - История последних попыток
    """
    stats = get_statistics(st.session_state.user_id)
    st.write(f'Количество изученных слов: {len(stats)}')
    total_attempts = sum(item['total_attempts'] for item in stats)
    if total_attempts > 0:
        correct_answers = sum(item['correct_answers'] for item in stats) / total_attempts * 100
        st.write(f'Количество попыток: {total_attempts}')
        st.write(f'Процент правильных ответов: {correct_answers:.1f}%')
    else:
        st.write('Количество попыток: 0')
        st.write(f'Процент правильных ответов: 0%')
    last_reviewed = [item['last_reviewed'].strftime('%d.%m.%Y') for item in stats]
    st.write('История последних попыток:')
    for item in last_reviewed:
        st.write('-', item)


def render_schema():
    """
    TODO: Реализовать отображение схемы базы данных (дополнительное требование)
    """
    image = Image.open(r'C:\Users\Пользователь\Desktop\english_card\english_card (schema).png')
    if 'show_image' not in st.session_state:
        st.session_state.show_image = False
    if st.button('Схема базы данных', use_container_width=True):
        st.session_state.show_image = not st.session_state.show_image
    if st.session_state.show_image:
        st.image(image)


# ============================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================

def main():
    """
    Главная функция приложения
    TODO: Реализовать основную логику:
    1. Инициализация БД
    2. Авторизация пользователя
    3. Отображение вкладок с функционалом
    4. Приветственное сообщение для неавторизованных пользователей
    """

    st.title("📚 EnglishCard - Изучай английский с удовольствием!")

    # TODO: Инициализация состояния сессии
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None

    # TODO: Инициализация БД
    init_database()

    # TODO: Боковая панель с авторизацией
    render_sidebar()

    # TODO: Основной контент в зависимости от авторизации
    if st.session_state.user_id:
        words = get_user_words(st.session_state.user_id)
        # Создание вкладок
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Изучение", "➕ Добавить слово", "🗑️ Удалить слово", "📊 Статистика"])
        with tab1:
            render_study_tab(words)
        with tab2:
            render_add_word_tab()
        with tab3:
            render_delete_word_tab(words)
        with tab4:
            render_statistics_tab(st.session_state.user_id)

        render_schema()
    else:
        # Приветственное сообщение
        st.write(f"""
            Привет 👋 Давай попрактикуемся в английском языке. 
            Тренировки можешь проходить в удобном для себя темпе.
            У тебя есть возможность использовать тренажёр, как конструктор, 
            и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:
            добавить слово ➕,
            удалить слово 🗑️.
            Ну что, начнём ⬇️
        """)


if __name__ == "__main__":
    main()