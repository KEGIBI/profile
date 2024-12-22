import pymysql

def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1',  # XAMPP MySQL의 기본 호스트
        user='root',       # 기본 사용자 이름
        password='',       # XAMPP 기본 비밀번호는 없음
        database='board',  # 데이터베이스 이름
        cursorclass=pymysql.cursors.DictCursor
    )

# 데이터베이스 초기화 (테이블 생성)
def init_db():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # users 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    email VARCHAR(50) UNIQUE,
                    name VARCHAR(100),
                    school VARCHAR(100),
                    profile_image VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            # posts 테이블 생성 및 user_id 컬럼 추가
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    password VARCHAR(255),
                    filename VARCHAR(255),
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(50) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            ''')
    finally:
        connection.close()
