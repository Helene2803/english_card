CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS common_words(
    id SERIAL PRIMARY KEY,
    russian_word VARCHAR(40) UNIQUE NOT NULL,
    english_word VARCHAR(40) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_words(
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    russian_word VARCHAR(40) NOT NULL,
    english_word VARCHAR(40) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_user_words
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_stats(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    word_id INTEGER NOT NULL,
    word_type VARCHAR(40) NOT NULL,
    correct_answers INTEGER,
    total_attempts INTEGER,
    last_reviewed TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

