from flask import Flask, request, render_template, redirect, url_for, send_from_directory, session
from db import get_db_connection, init_db
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 관리용 키

# 업로드 폴더 설정
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}    
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def fetch_posts():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM posts ORDER BY created_at DESC;")
            return cursor.fetchall()
    finally:
        connection.close()

@app.route('/')
def index():
    posts = fetch_posts()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    regierror_message = None
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        email = request.form['email']
        name = request.form['name']
        school = request.form['school']

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM users WHERE user_id = %s OR email = %s", (user_id, email))
                if cursor.fetchone():
                    regierror_message = "이미 존재하는 아이디 또는 이메일입니다."
                    return render_template('register.html', regierror_message=regierror_message)

                cursor.execute(
                    "INSERT INTO users (user_id, password, email, name, school) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, password, email, name, school)
                )
            connection.commit()
            return redirect(url_for('login'))
        finally:
            connection.close()

    return render_template('register.html', regierror_message=regierror_message)

    # GET 요청 또는 오류 메시지가 있을 때
    return render_template('register.html', regierror_message=regierror_message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, user_id FROM users WHERE user_id = %s AND password = %s", (user_id, password))
                user = cursor.fetchone()
                if user:
                    session['user_id'] = user['user_id']  # 세션에 user_id 저장
                    return redirect(url_for('index'))
                else:
                    return "아이디 또는 비밀번호가 잘못되었습니다.", 400
        finally:
            connection.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # 세션 초기화
    return redirect(url_for('login'))

@app.route('/findid', methods=['GET', 'POST'])
def findid():
    message = None
    if request.method == 'POST':
        email = request.form['email']
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email))
                user = cursor.fetchone()
                if user:
                    message = f"아이디는 '{user['user_id']}' 입니다."
                else:
                    message = "등록된 이메일이 없습니다."
        finally:
            connection.close()
    return render_template('findid.html', message=message)

@app.route('/findpw', methods=['GET', 'POST'])
def findpw():
    message = None
    if request.method == 'POST':
        user_id = request.form['user_id']
        email = request.form['email']
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE user_id = %s AND email = %s", (user_id, email))
                user = cursor.fetchone()
                if user:
                    message = f"비밀번호는 '{user['password']}' 입니다."
                else:
                    message = "아이디 또는 이메일 정보가 일치하지 않습니다."
        finally:
            connection.close()
    return render_template('findpw.html', message=message)

@app.route('/create', methods=['GET', 'POST'])
def create():
    # 세션에서 user_id 가져오기
    user_identifier = session.get('user_id')
    if not user_identifier:
        return redirect(url_for('login'))

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name FROM users WHERE user_id = %s", (user_identifier,))
            user = cursor.fetchone()
            if not user:
                return "사용자를 찾을 수 없습니다.", 404

            user_id = user['id']
            author_name = user['name']
    finally:
        connection.close()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        password = request.form.get('password') or None
        file = request.files.get('file')
        filename = None

        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO posts (title, content, password, filename, user_id, author_name) VALUES (%s, %s, %s, %s, %s, %s);",
                    (title, content, password, filename, user_id, author_name)
                )
            connection.commit()
        finally:
            connection.close()

        return redirect(url_for('index'))

    return render_template('create.html')



@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/update/<int:post_id>', methods=['GET', 'POST'])
def update(post_id):
    user_identifier = session.get('user_id')  # 세션에서 user_id 가져오기
    if not user_identifier:
        return redirect(url_for('login'))  # 로그인하지 않았다면 로그인 페이지로 이동

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 게시글 정보 가져오기
            cursor.execute("""
                SELECT posts.id, posts.title, posts.content, posts.user_id, users.user_id AS author_identifier
                FROM posts
                JOIN users ON posts.user_id = users.id
                WHERE posts.id = %s
            """, (post_id,))
            post = cursor.fetchone()

            if not post:
                return "게시글을 찾을 수 없습니다.", 404

            # 현재 로그인한 사용자가 작성자인지 확인
            if post['author_identifier'] != user_identifier:
                return "수정 권한이 없습니다.", 403

        if request.method == 'POST':
            # 업데이트 요청
            title = request.form['title']
            content = request.form['content']

            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE posts SET title = %s, content = %s WHERE id = %s",
                    (title, content, post_id)
                )
            connection.commit()
            return redirect(url_for('index'))
    finally:
        connection.close()

    return render_template('update.html', post=post)



@app.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    user_identifier = session.get('user_id')  # 세션에서 user_id 가져오기
    if not user_identifier:
        return redirect(url_for('login'))  # 로그인하지 않았다면 로그인 페이지로 이동

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 게시글 정보 가져오기
            cursor.execute("""
                SELECT posts.id, posts.user_id, users.user_id AS author_identifier
                FROM posts
                JOIN users ON posts.user_id = users.id
                WHERE posts.id = %s
            """, (post_id,))
            post = cursor.fetchone()

            if not post:
                return "게시글을 찾을 수 없습니다.", 404

            # 현재 로그인한 사용자가 작성자인지 확인
            if post['author_identifier'] != user_identifier:
                return "삭제 권한이 없습니다.", 403

            # 삭제 수행
            cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for('index'))



@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    criteria = request.args.get('criteria', 'all')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM posts WHERE "
            if criteria == 'title':
                sql = "SELECT * FROM posts WHERE title LIKE %s"
                cursor.execute(sql, (f"%{query}%",))
            elif criteria == 'content':
                sql = "SELECT * FROM posts WHERE content LIKE %s"
                cursor.execute(sql, (f"%{query}%",))
            else:
                sql = "SELECT * FROM posts WHERE title LIKE %s OR content LIKE %s"
                cursor.execute(sql, (f"%{query}%", f"%{query}%"))
            posts = cursor.fetchall()
    finally:
        connection.close()
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 게시글 데이터 가져오기
            cursor.execute("""
                SELECT posts.id, posts.title, posts.content, posts.password, posts.filename,
                       posts.created_at, users.name AS author_name
                FROM posts
                LEFT JOIN users ON posts.user_id = users.id
                WHERE posts.id = %s;
            """, (post_id,))
            post = cursor.fetchone()

        if not post:
            return "게시글을 찾을 수 없습니다.", 404

        # 비밀번호가 없는 경우 바로 게시글 보여줌
        if not post['password']:
            return render_template('post.html', post=post)

        error_message = None
        if request.method == 'POST':
            input_password = request.form['password']
            if input_password == post['password']:
                return render_template('post.html', post=post)
            else:
                error_message = "비밀번호가 잘못되었습니다."

        return render_template('checkpw.html', post_id=post_id, error_message=error_message)

    finally:
        connection.close() 

@app.route('/myprofile', methods=['GET', 'POST'])
def myprofile():
    user_id = session.get('user_id')  # 세션에서 user_id 가져오기
    if not user_id:
        return redirect(url_for('login'))  # 세션에 user_id 없으면 로그인 페이지로 이동

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name, school, profile_image FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()

        if not user:
            return "사용자를 찾을 수 없습니다.", 404

        if request.method == 'POST':
            name = request.form['name']
            school = request.form['school']
            profile_image = request.files.get('profile_image')

            if profile_image and profile_image.filename != '':
                image_filename = profile_image.filename
                profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET name = %s, school = %s, profile_image = %s WHERE user_id = %s",
                        (name, school, image_filename, user_id)
                    )
            else:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users SET name = %s, school = %s WHERE user_id = %s",
                        (name, school, user_id)
                    )

            connection.commit()
            return redirect(url_for('myprofile'))

    finally:
        connection.close()

    return render_template('myprofile.html', user=user)

@app.route('/viewprofile/<user_id>')
def viewprofile(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 데이터베이스에서 user_id에 해당하는 사용자 정보 가져오기
            cursor.execute("SELECT name, school, profile_image FROM users WHERE user_id = %s;", (user_id,))
            user = cursor.fetchone()

        if not user:
            # 사용자 정보가 없으면 404 오류 반환
            return "사용자를 찾을 수 없습니다.", 404

    finally:
        connection.close()

    # 템플릿에 사용자 정보 전달
    return render_template('viewprofile.html', user=user)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
