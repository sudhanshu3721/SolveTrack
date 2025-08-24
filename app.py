from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# DB URL – default to SQLite for local, can switch to Postgres on Render later
db_url = os.environ.get("DATABASE_URL", "sqlite:///dsa.db")
# Render/Heroku sometimes use postgres://; SQLAlchemy expects postgresql://
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///dsa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
app.secret_key = "supersecretkey123"  

class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(200),unique = True,nullable=False)
    password = db.Column(db.String(200),nullable=False)
    dsa_problems = db.relationship('DSA',backref='User',lazy=True)



# Database model
class DSA(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    problem_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    date_solved = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    

    def __repr__(self):
        return f"{self.sno} - {self.problem_name} - {self.difficulty}"
    

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route("/", methods=['GET'])
def home():
    return redirect(url_for('register'))

@app.route("/dashboard", methods=['GET'])
@login_required
def dashboard():
    user_id = session['user_id']
    alldsa = DSA.query.filter_by(user_id=user_id).all()
    return render_template("index.html", alldsa=alldsa)

    

@app.route("/register",methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error="Email already taken")
        new_user = User(email=email,password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid credentials!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id',None)
    return redirect(url_for('login'))
        


@app.route("/add", methods=['GET', 'POST'])
@login_required
def add():
    
    if request.method == 'POST':
        prob = DSA(
            problem_name=request.form['problem_name'],
            description=request.form['description'],
            difficulty=request.form['difficulty'],
            link=request.form['link'],
            date_solved=request.form['date'] or None,
            user_id=session['user_id']
        )
        db.session.add(prob)
        db.session.commit()
        return redirect("/dashboard")
    return render_template("add.html")

@app.route("/update/<int:sno>", methods=['GET', 'POST'])
@login_required
def update(sno):
    prob = DSA.query.filter_by(sno=sno, user_id=session['user_id']).first()  # ensure user owns it
    if not prob:
        return "Unauthorized or Not Found", 403
    
    if request.method == 'POST':
        prob.problem_name = request.form['problem_name']
        prob.description = request.form['description']
        prob.difficulty = request.form['difficulty']
        prob.link = request.form['link']
        date_solved = request.form['date_solved']
        if date_solved:
            prob.date_solved = datetime.strptime(date_solved, "%Y-%m-%d")
        prob.user_id = session['user_id']
        db.session.commit()
        return redirect("/dashboard")
    return render_template("update.html", prob=prob)

@app.route("/delete/<int:sno>")
@login_required
def delete(sno):
    prob = DSA.query.filter_by(sno=sno, user_id=session['user_id']).first()
    if not prob:
        return "Unauthorized or Not Found", 403
    
    db.session.delete(prob)
    db.session.commit()
    return redirect("/dashboard")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
