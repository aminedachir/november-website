from flask import Flask, render_template, request, session, redirect, url_for
import json
import os
from datetime import datetime
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['DATABASE'] = 'students.db'

# Database setup
def init_db():
    try:
        with app.app_context():
            conn = sqlite3.connect(app.config['DATABASE'])
            cursor = conn.cursor()
            
            # Drop tables if they exist (for clean reset)
            cursor.execute('DROP TABLE IF EXISTS quiz_attempts')
            cursor.execute('DROP TABLE IF EXISTS students')
            cursor.execute('DROP TABLE IF EXISTS challenger_votes')
            cursor.execute('DROP TABLE IF EXISTS poetry_votes')
            
            # Create students table
            cursor.execute('''
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create quiz_attempts table
            cursor.execute('''
                CREATE TABLE quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    score INTEGER,
                    total_questions INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            ''')
            
            # Create challenger_votes table
            cursor.execute('''
                CREATE TABLE challenger_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voter_first_name TEXT NOT NULL,
                    voter_last_name TEXT NOT NULL,
                    challenger_name TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create poetry_votes table
            cursor.execute('''
                CREATE TABLE poetry_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voter_first_name TEXT NOT NULL,
                    voter_last_name TEXT NOT NULL,
                    contestant_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")

@contextmanager
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Quiz questions about Algerian War of Independence
QUESTIONS = [
    {
        'id': 1,
        'question': 'متى بدأت حرب الاستقلال الجزائرية؟',
        'options': ['5 يوليو 1962','1 نوفمبر 1954',  '19 مارس 1962', '8 مايو 1945'],
        'correct': '1 نوفمبر 1954'
    },
    {
        'id': 2,
        'question': 'أي منظمة قادت حركة استقلال الجزائر؟',
        'options': ['جبهة التحرير الوطني (FLN)', 'الجيش الوطني للتحرير (ALN)', 'الحكومة المؤقتة للجمهورية الجزائرية (GPRA)', 'جميع ما سبق'],
        'correct': 'جميع ما سبق'
    },
    {
        'id': 3,
        'question': 'من كان أول رئيس للجزائر المستقلة؟',
        'options': ['هواري بومدين','أحمد بن بلة',  'فرحات عباس', 'محمد بوضياف'],
        'correct': 'أحمد بن بلة'
    },
    {
        'id': 4,
        'question': 'ما اسم النظام الاستعماري الفرنسي في الجزائر؟',
        'options': ['الإدارة الاستعمارية', 'الجزائر الفرنسية', 'Algérie française', 'إقليم شمال إفريقيا'],
        'correct': 'Algérie française'
    },
    {
        'id': 5,
        'question': 'أي معركة مشهورة حدثت في الجزائر العاصمة عام 1957؟',
        'options': [ 'انتفاضة الجزائر', 'صراع القصبة','معركة الجزائر', 'حصار الجزائر'],
        'correct': 'معركة الجزائر'
    },
    {
        'id': 6,
        'question': 'متى حصلت الجزائر على استقلالها؟',
        'options': ['5 يوليو 1962', '1 نوفمبر 1954', '19 مارس 1962', '31 ديسمبر 1962'],
        'correct': '5 يوليو 1962'
    },
    {
        'id': 7,
        'question': 'ماذا يعني اختصار FLN؟',
        'options': ['قوات التحرير الوطني','جبهة التحرير الوطني',  'جبهة من أجل الحرية الوطنية', 'قوات الأمة الحرة'],
        'correct': 'جبهة التحرير الوطني'
    },
    {
        'id': 8,
        'question': 'أي مدينة كانت عاصمة مؤقتة للحكومة المؤقتة للجمهورية الجزائرية (GPRA)؟',
        'options': ['القاهرة', 'الرباط','تونس',  'دمشق'],
        'correct': 'تونس'
    },
    {
        'id': 9,
        'question': 'ما الاسم الذي أُطلق على مقاتلي استقلال الجزائر؟',
        'options': [ 'مقاتلو الحرية', 'ثوار', 'مجاهدون','المحررون'],
        'correct': 'مجاهدون'
    },
    {
        'id': 10,
        'question': 'أي دولة أوروبية استعمرت الجزائر؟',
        'options': [ 'إسبانيا', 'إيطاليا', 'البرتغال','فرنسا',],
        'correct': 'فرنسا'
    },
    {
        'id': 11,
        'question': 'كم استمرت حرب الجزائر؟',
        'options': ['5 سنوات', '10 سنوات''7 سنوات  و7 أشهر', '8 سنوات'],
        'correct': '7 سنوات و7 أشهر'
    },
    {
        'id': 12,
        'question': 'ما هي اتفاقيات إيفيان؟',
        'options': ['اتفاقيات سلام أنهت الحرب', 'اتفاقيات تجارية', 'تحالفات عسكرية', 'تبادلات ثقافية'],
        'correct': 'اتفاقيات سلام أنهت الحرب'
    },
    {
        'id': 13,
        'question': 'أي ثوري مشهور كان يُعرف بـ "سي محمد"؟',
        'options': ['العربي بن مهيدي', 'أحمد بن بلة', 'كريم بلقاسم', 'محمد بوضياف'],
        'correct': 'العربي بن مهيدي'
    },
    {
        'id': 14,
        'question': 'ما هو مؤتمر صومام؟',
        'options': ['اجتماع استراتيجي رئيسي لجبهة التحرير الوطني', 'مؤتمر سلام', 'مهرجان ثقافي', 'عملية عسكرية'],
        'correct': 'اجتماع استراتيجي رئيسي لجبهة التحرير الوطني'
    },
    {
        'id': 15,
        'question': 'أي مدينة جزائرية شهدت أولى الاشتباكات في 1 نوفمبر 1954؟',
        'options': ['وهران', 'قسنطينة','جبال الأوراس', 'الجزائر العاصمة'],
        'correct': 'جبال الأوراس'
    },
    {
        'id': 16,
        'question': 'ماذا يعني اختصار ALN؟',
        'options': ['الجيش الوطني للتحرير', 'الجيش من أجل الحرية الوطنية', 'تحالف التحرير الوطني', 'جمعية التحرير الوطني'],
        'correct': 'الجيش الوطني للتحرير'
    },
    {
        'id': 17,
        'question': 'من كان رئيس فرنسا خلال معظم فترة الحرب؟',
        'options': ['شارل ديغول', 'فرنسوا ميتران', 'جورج بومبيدو', 'بيير منديس فرانس'],
        'correct': 'شارل ديغول'
    },
    {
        'id': 18,
        'question': 'ما هو العدد المقدر لشهداء الجزائر؟',
        'options': ['1.5 مليون', '500,000', '2 مليون', '800,000'],
        'correct': '1.5 مليون'
    },
    {
        'id': 19,
        'question': 'أي تاريخ يُحتفل به بيوم النصر في الجزائر؟',
        'options': ['5 جويلية','19 مارس', '1 نوفمبر', '8 مايو'],
        'correct': '19 مارس'
    },
    {
        'id': 20,
        'question': 'ما كان الهدف الرئيسي للثورة الجزائرية؟',
        'options': ['الاستقلال عن فرنسا', 'الإصلاحات الاقتصادية', 'النهضة الثقافية', 'الاستقلال السياسي'],
        'correct': 'الاستقلال عن فرنسا'
    }
]

# Poetry Competition Contestants
POETRY_CONTESTANTS = [
    {
        'id': 'contestant_1',
        'name': 'رحاب رأس الماء',
        'poem_title': 'فجر الجزائر',
        'poem_excerpt': """
            يا فجرَ نوفمبر... حَدِّثْهُم عن الجزائر
            يا فجرَ نوفمبرَ... حَدِّثْهُم عن الجزائرْ،
            عن وطنٍ نهضَ من رمادِ القهرِ،
            وقالَ: لن أموتْ... وإنْ ماتَ الرجالْ!
            يا فجرَ نوفمبر...
            قُلْ للريحِ إنّا هنا،
            وأنّنا ما زلنا نحرسُ الحلمَ،
            الذي كتبوهُ بدمائهم... أولئك الستّةُ الأبطالْ!
            قُلْ لهم...
            أنّ دّيدوشَ مرادًا لم يمتْ،
            بل صارَ شُعلةً في قلبِ العاصمةِ،
            تضيءُ كلَّ ليلٍ غادرٍ بالعزمِ واليقينْ!
            وقُلْ لهم...
            أنّ بوضيافَ ما زالَ يخطبُ في الترابْ،
            صوتهُ يهتفُ: الجزائرُ لنا... وإنْ طالَ العذابْ!
            كانَ الحلمُ وطنًا، فصارَ الوطنُ حُلمًا تحقّقَ بعدَ الغيابْ.
            واذكرْ لهم...
            مصطفى بن بولعيد،
            ذلك الصقرُ الذي علَّمَ الجبالَ كيفَ تصرخُ: حرّيّة!
            نامَ جسدُهُ في الأوراسْ...
            لكنّ روحهُ ما زالتْ تسكنُ الرصاصْ!
            ويا العربي بن مهيدي... يا أيّها الباسمُ في وجهِ الموتِ!
            حينَ وضعوا الحبلَ في عنقِك،
            لم تبكِ، لم تصرخْ... بل قلتَ:
            ارموا بالثورةِ إلى الشارع، سيحتضنُها الشعبْ!
            فكانَتِ المعجزةْ... وكانتِ الجزائرْ!
            ثمّ كريمُ بلقاسم، يا ليلَ المفاوضاتِ الصّعبْ،
            يا منْ وقّعتَ باسمِ وطنٍ جريحٍ،
            وابتسمتَ رغمَ التعبْ...
            نمْ هانئًا، فحروفُ اسمِك صارتْ نجومًا في علمِ العربْ.
            ورابحُ بيطاطُ... يا ظلَّ الشهداءِ في السجونْ،
            يا منْ جعلتَ الحديدَ يلينُ إذا نطقتَ بالوطنْ،
            علّمتَنا أنَّ القيودَ...
            لا تُقيدُ إلا الجبناءْ،
            وأنتَ كنتَ من معدنِ الإباءْ!
            ستّةٌ...
            لكنّهم كانوا وطنًا واحدًا،
            يصرخُ باسمِ الجزائرِ من كلِّ جبلٍ وسهلْ،
            كأنَّ اللهَ حينَ خلقَهم...
            قالَ: كونوا فجرَ هذا الوطن!
            يا أوّلَ نوفمبرْ...
            يا ميلادَ الحرّيّةِ،
            يا آيةَ الشهادةِ الخالدةْ،
            كلُّ عامٍ، والجزائرُ
            تحملُ دموعَها على كتفِ الفخرْ،
            وتقولُ للعالمِ بصوتِها الجريحْ:
            هنا بدأنا... وهنا سنبقى... ما دام فينا نفسٌ يصيحْ
            """,
        'class': ' كلية الاداب و اللغات ',
        'image': 'contestant1.jpg'
    },
    {
        'id': 'contestant_2',
        'name': 'أنجوح أميمة',
        'poem_title': 'نوفمبرُ ارتدى عباءةَ الحريةِ',
        'poem_excerpt': """
            نوفمبرُ ارتدى عباءةَ الحريةِ،
            وصارَ في عيوننا نورَ البداية.
            على دروبِ الوطنِ تزهرُ الأحلامُ،
            وتكتبُ الأيامُ اسمَ الاستقلالِ.
            رياحُ نوفمبرَ تعانقُ الجبالَ،
            وتهمسُ لنا: "لقد ولدت الحرية".
            كلُّ ورقةٍ سقطتْ من الشجرِ القديم،
            تحملُ ذكرياتِ دمٍ وصوتٍ لا يموتُ.
            وفي المساء، تلمعُ الشموعُ في الساحاتِ،
            تذكرُنا بأنَّ النصرَ ثمنُ صبرٍ طويل.
            الأنهارُ تهتفُ بأغاني الفرحِ،
            والطيورُ تحلقُ في سماءِ الوطنِ الصافي.
            نوفمبرُ، يا شهرَ العزِّ والأملِ،
            سنظلُّ نحيا باسمك، واسمُك في القلبِ خالدٌ.
            كلُّ حجرٍ في أرضِنا يحكي قصةَ أبطالٍ،
            كلُّ نسمةٍ تروي حكايةَ دمٍ لم يضِعْ.
            نرفعُ راياتِنا عالياً في الرياحِ،
            ونرددُ نشيدَ الأرضِ والسماءِ معاً.
            الليلُ لا يُخيفُنا، فالنجومُ شاهدةٌ،
            والقمرُ يحرسُ أحلامَنا وذكرياتِنا.
            يا نوفمبرُ، يا زمنَ الشجاعةِ والصمودِ،
            في قلبكِ يولدُ الأملُ، وفيكِ يزهرُ الوطنُ.
            نحمي الحريةَ كما نحمي قلبَنا،
            ونكتبُ على كلِّ جدارٍ، أنّنا أحرارٌ.
            """,
        'class': 'اولى ماستر هياكل',
        'image': 'contestant2.jpg'
    },
]


def save_student_result(first_name, last_name, score, total_questions):
    """Save student result to database and return student info"""
    percentage = (score / total_questions) * 100
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if student already exists
        cursor.execute(
            'SELECT id, score, total_questions FROM students WHERE first_name = ? AND last_name = ?',
            (first_name, last_name)
        )
        existing_student = cursor.fetchone()
        
        if existing_student:
            # Update if new score is higher
            if score > existing_student['score']:
                cursor.execute(
                    'UPDATE students SET score = ?, total_questions = ?, percentage = ?, timestamp = CURRENT_TIMESTAMP WHERE id = ?',
                    (score, total_questions, percentage, existing_student['id'])
                )
                student_id = existing_student['id']
            else:
                student_id = existing_student['id']
        else:
            # Insert new student
            cursor.execute(
                'INSERT INTO students (first_name, last_name, score, total_questions, percentage) VALUES (?, ?, ?, ?, ?)',
                (first_name, last_name, score, total_questions, percentage)
            )
            student_id = cursor.lastrowid
        
        # Record quiz attempt
        cursor.execute(
            'INSERT INTO quiz_attempts (student_id, score, total_questions) VALUES (?, ?, ?)',
            (student_id, score, total_questions)
        )
        
        conn.commit()
    
    return student_id

def get_leaderboard(limit=50):
    """Get leaderboard sorted by score (descending) and name"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT first_name, last_name, score, total_questions, percentage, timestamp
            FROM students 
            ORDER BY score DESC, percentage DESC, last_name ASC, first_name ASC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

def get_student_rank(first_name, last_name):
    """Get student's rank in the leaderboard"""
    leaderboard = get_leaderboard(1000)  # Get all students
    for rank, student in enumerate(leaderboard, 1):
        if student['first_name'] == first_name and student['last_name'] == last_name:
            return rank, len(leaderboard)
    return None, len(leaderboard)

def get_student_stats(first_name, last_name):
    """Get detailed statistics for a student"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.first_name, s.last_name, s.score, s.total_questions, s.percentage, s.timestamp,
                   COUNT(qa.id) as attempts,
                   MAX(qa.score) as best_score,
                   AVG(qa.score) as average_score
            FROM students s
            LEFT JOIN quiz_attempts qa ON s.id = qa.student_id
            WHERE s.first_name = ? AND s.last_name = ?
            GROUP BY s.id
        ''', (first_name, last_name))
        return cursor.fetchone()

def get_rank_info(score, total_questions):
    """Determine rank based on score"""
    percentage = (score / total_questions) * 100
    
    if percentage >= 95:
        return {"rank": "Revolution Leader", "level": "elite", "icon": "🥇", "color": "#FFD700"}
    elif percentage >= 85:
        return {"rank": "Freedom Fighter", "level": "expert", "icon": "🥈", "color": "#C0C0C0"}
    elif percentage >= 75:
        return {"rank": "Independence Hero", "level": "advanced", "icon": "🥉", "color": "#CD7F32"}
    elif percentage >= 60:
        return {"rank": "Resistance Member", "level": "intermediate", "icon": "⭐", "color": "#006233"}
    elif percentage >= 50:
        return {"rank": "Supporter", "level": "beginner", "icon": "📚", "color": "#007BFF"}
    else:
        return {"rank": "Learner", "level": "new", "icon": "🌱", "color": "#6C757D"}

def has_user_voted_poetry(first_name, last_name):
    """Check if user has already voted in poetry competition"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM poetry_votes WHERE voter_first_name = ? AND voter_last_name = ?',
            (first_name, last_name)
        )
        return cursor.fetchone() is not None

def save_poetry_vote(first_name, last_name, contestant_id):
    """Save user's poetry competition vote"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO poetry_votes (voter_first_name, voter_last_name, contestant_id) VALUES (?, ?, ?)',
            (first_name, last_name, contestant_id)
        )
        conn.commit()

def get_poetry_vote_results():
    """Get poetry competition voting results"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT contestant_id, COUNT(*) as vote_count
            FROM poetry_votes 
            GROUP BY contestant_id 
            ORDER BY vote_count DESC
        ''')
        results = cursor.fetchall()
        
        # Convert to dictionary for easier lookup
        vote_dict = {row['contestant_id']: row['vote_count'] for row in results}
        
        # Get total votes
        total_votes = sum(vote_dict.values())
        
        return vote_dict, total_votes


@app.route('/')
def index():
    # Get top 5 students for homepage preview
    top_students = get_leaderboard(5)
    return render_template('index.html', top_students=top_students)

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        # Store user info in session
        session['first_name'] = request.form['first_name'].strip().title()
        session['last_name'] = request.form['last_name'].strip().title()
        session['score'] = 0
        session['current_question'] = 0
        session['answers'] = []
        return redirect(url_for('question'))
    
    # Check if user info already exists in session
    if 'first_name' in session and 'last_name' in session:
        # User already entered their name, start quiz directly
        session['score'] = 0
        session['current_question'] = 0
        session['answers'] = []
        return redirect(url_for('question'))
    
    return render_template('quiz.html')

@app.route('/question', methods=['GET', 'POST'])
def question():
    if 'first_name' not in session:
        return redirect(url_for('quiz'))
    
    if request.method == 'POST':
        # Check answer
        user_answer = request.form.get('answer')
        current_q_index = session['current_question']
        correct_answer = QUESTIONS[current_q_index]['correct']
        
        session['answers'].append({
            'question': QUESTIONS[current_q_index]['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': user_answer == correct_answer
        })
        
        if user_answer == correct_answer:
            session['score'] += 1
        
        session['current_question'] += 1
        
        if session['current_question'] >= len(QUESTIONS):
            # Save student result when quiz is completed
            save_student_result(session['first_name'], session['last_name'], session['score'], len(QUESTIONS))
            return redirect(url_for('results'))
    
    if session['current_question'] >= len(QUESTIONS):
        return redirect(url_for('results'))
    
    question_data = QUESTIONS[session['current_question']]
    return render_template('question.html', 
                         question=question_data,
                         question_number=session['current_question'] + 1,
                         total_questions=len(QUESTIONS))

@app.route('/results')
def results():
    if 'first_name' not in session:
        return redirect(url_for('quiz'))
    
    score = session['score']
    total = len(QUESTIONS)
    
    # Get rank information
    rank_info = get_rank_info(score, total)
    
    # Get student's rank and total students
    student_rank, total_students = get_student_rank(session['first_name'], session['last_name'])
    
    # Get student statistics
    student_stats = get_student_stats(session['first_name'], session['last_name'])
    
    # Get leaderboard for preview
    leaderboard = get_leaderboard(10)
    
    return render_template('results.html',
                         first_name=session['first_name'],
                         last_name=session['last_name'],
                         score=score,
                         total=total,
                         answers=session['answers'],
                         rank_info=rank_info,
                         student_rank=student_rank,
                         total_students=total_students,
                         student_stats=student_stats,
                         leaderboard=leaderboard)

@app.route('/leaderboard')
def leaderboard():
    # Get all parameters for filtering
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20
    
    # Get leaderboard
    all_students = get_leaderboard(1000)  # Get all students
    
    # Filter by search
    if search:
        filtered_students = [
            student for student in all_students 
            if search.lower() in f"{student['first_name']} {student['last_name']}".lower()
        ]
    else:
        filtered_students = all_students
    
    # Pagination
    total_students = len(filtered_students)
    total_pages = (total_students + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    students_page = filtered_students[start_idx:end_idx]
    
    return render_template('leaderboard.html', 
                         leaderboard=students_page,
                         total_students=total_students,
                         page=page,
                         total_pages=total_pages,
                         search=search)


@app.route('/six-members')
def six_members():
    return render_template('six_members.html')

@app.route('/poetry-competition', methods=['GET', 'POST'])
def poetry_competition():
    """Route for poetry competition voting"""
    if request.method == 'POST':
        # If submitting a vote
        contestant_id = request.form.get('contestant_id')
        
        # Get user info from session
        first_name = session.get('first_name', '').strip().title()
        last_name = session.get('last_name', '').strip().title()
        
        if not first_name or not last_name:
            # This shouldn't happen, but just in case
            return render_template('poetry_competition.html',
                                 contestants=POETRY_CONTESTANTS,
                                 error='الرجاء إدخال الاسم واللقب',
                                 ask_name=True)
        
        if has_user_voted_poetry(first_name, last_name):
            return render_template('poetry_competition.html',
                                 contestants=POETRY_CONTESTANTS,
                                 error='لقد قمت بالتصويت مسبقاً',
                                 user_name=f"{first_name} {last_name}")
        
        if contestant_id:
            save_poetry_vote(first_name, last_name, contestant_id)
            return redirect(url_for('poetry_results'))
    
    # Check if user info exists in session
    if 'first_name' in session and 'last_name' in session:
        # User already entered their name
        first_name = session['first_name']
        last_name = session['last_name']
        
        # Check if already voted
        if has_user_voted_poetry(first_name, last_name):
            return render_template('poetry_competition.html',
                                 contestants=POETRY_CONTESTANTS,
                                 error='لقد قمت بالتصويت مسبقاً',
                                 user_name=f"{first_name} {last_name}")
        
        return render_template('poetry_competition.html',
                             contestants=POETRY_CONTESTANTS,
                             user_name=f"{first_name} {last_name}")
    
    # Need to ask for name
    return render_template('poetry_competition.html',
                         contestants=POETRY_CONTESTANTS,
                         ask_name=True)

@app.route('/save-user-info', methods=['POST'])
def save_user_info():
    """Save user info to session from poetry page"""
    first_name = request.form.get('first_name', '').strip().title()
    last_name = request.form.get('last_name', '').strip().title()
    
    if first_name and last_name:
        session['first_name'] = first_name
        session['last_name'] = last_name
    
    return redirect(url_for('poetry_competition'))

@app.route('/vote_results')
def poetry_results():
    """Show poetry competition results"""
    vote_dict, total_votes = get_poetry_vote_results()
    
    # Add vote counts to contestants
    contestants_with_votes = []
    for contestant in POETRY_CONTESTANTS:
        contestant_copy = contestant.copy()
        votes = vote_dict.get(contestant['id'], 0)
        contestant_copy['votes'] = votes
        contestant_copy['percentage'] = (votes / total_votes * 100) if total_votes > 0 else 0
        contestants_with_votes.append(contestant_copy)
    
    # Sort by votes
    contestants_with_votes.sort(key=lambda x: x['votes'], reverse=True)
    
    return render_template('poetry_results.html',
                         contestants=contestants_with_votes,
                         total_votes=total_votes)

@app.route('/restart')
def restart():
    session.clear()
    return redirect(url_for('quiz'))

@app.route('/reset-db')
def reset_db():
    """Route to reset and recreate the database (for development only)"""
    try:
        # Remove existing database file
        if os.path.exists(app.config['DATABASE']):
            os.remove(app.config['DATABASE'])
            print(f"Removed existing database: {app.config['DATABASE']}")
        
        # Reinitialize database
        init_db()
        return "Database reset successfully! <a href='/'>Go Home</a>"
    except Exception as e:
        return f"Error resetting database: {str(e)}"

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
