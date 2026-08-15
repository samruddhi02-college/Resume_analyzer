from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import json, os, uuid, hashlib, re
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from collections import Counter

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

app = Flask(__name__)
app.secret_key = 'resumeai_secret_2024'
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'pdf', 'docx', 'txt'}

# ── Helpers ───────────────────────────────────────────────────────────────
def allowed(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED

def extract_text(path):
    ext = path.rsplit('.',1)[-1].lower()
    try:
        if ext == 'pdf' and PDF_SUPPORT:
            with pdfplumber.open(path) as pdf:
                return '\n'.join(p.extract_text() or '' for p in pdf.pages)
        if ext in ('docx','doc') and DOCX_SUPPORT:
            return '\n'.join(p.text for p in DocxDocument(path).paragraphs if p.text.strip())
        if ext == 'txt':
            return open(path, errors='ignore').read()
    except: pass
    return ''

def login_required(f):
    @wraps(f)
    def wrap(*a,**kw):
        if 'user' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return wrap

# ── Data ──────────────────────────────────────────────────────────────────
USERS = {
    "demo@resumeai.com": {
        "password": hashlib.sha256("demo1234".encode()).hexdigest(),
        "name": "Alex Johnson", "company": "TechCorp Inc.", "avatar": "AJ"
    }
}

JOBS = [
    {"id":"j1","title":"Senior Python Developer","dept":"Engineering","location":"Remote",
     "posted":"2024-01-10","applicants":47,"shortlisted":12,"status":"Active",
     "skills":["Python","Django","PostgreSQL","AWS","REST API"]},
    {"id":"j2","title":"Data Scientist","dept":"Analytics","location":"New York",
     "posted":"2024-01-08","applicants":63,"shortlisted":18,"status":"Active",
     "skills":["Python","ML","TensorFlow","SQL","Tableau"]},
    {"id":"j3","title":"Frontend React Developer","dept":"Engineering","location":"San Francisco",
     "posted":"2024-01-05","applicants":38,"shortlisted":9,"status":"Active",
     "skills":["React","TypeScript","CSS","Node.js","GraphQL"]},
    {"id":"j4","title":"DevOps Engineer","dept":"Infrastructure","location":"Austin",
     "posted":"2023-12-28","applicants":29,"shortlisted":7,"status":"Closed",
     "skills":["Docker","Kubernetes","CI/CD","AWS","Terraform"]},
]

CANDIDATES = [
    {"id":"c1","name":"Sarah Chen","email":"sarah@email.com","job_id":"j1","score":94,
     "experience":"6 years","skills":["Python","Django","AWS","PostgreSQL","Docker","REST API"],
     "status":"Shortlisted","applied":"2024-01-11","education":"MS CS, MIT","phone":"+1-555-0101","location":"Seattle, WA"},
    {"id":"c2","name":"Marcus Williams","email":"marcus@email.com","job_id":"j1","score":87,
     "experience":"4 years","skills":["Python","Flask","REST API","MySQL"],
     "status":"Under Review","applied":"2024-01-12","education":"BS SE, Stanford","phone":"+1-555-0102","location":"Austin, TX"},
    {"id":"c3","name":"Priya Sharma","email":"priya@email.com","job_id":"j2","score":96,
     "experience":"5 years","skills":["Python","ML","TensorFlow","SQL","Tableau","PyTorch"],
     "status":"Shortlisted","applied":"2024-01-09","education":"PhD DS, CMU","phone":"+1-555-0103","location":"Pittsburgh, PA"},
    {"id":"c4","name":"James Rodriguez","email":"james@email.com","job_id":"j2","score":72,
     "experience":"2 years","skills":["Python","SQL","Excel"],
     "status":"Rejected","applied":"2024-01-10","education":"BS Stats, UCLA","phone":"+1-555-0104","location":"Los Angeles, CA"},
    {"id":"c5","name":"Emily Watson","email":"emily@email.com","job_id":"j3","score":91,
     "experience":"5 years","skills":["React","TypeScript","GraphQL","Node.js","CSS"],
     "status":"Interview Scheduled","applied":"2024-01-06","education":"BS CS, Berkeley","phone":"+1-555-0105","location":"San Francisco, CA"},
    {"id":"c6","name":"David Kim","email":"david@email.com","job_id":"j1","score":68,
     "experience":"1 year","skills":["Python","Django"],
     "status":"Rejected","applied":"2024-01-13","education":"BS CS, State Univ","phone":"+1-555-0106","location":"Phoenix, AZ"},
]

# ── AI Screening ──────────────────────────────────────────────────────────
ALL_SKILLS = ['Python','JavaScript','TypeScript','React','Vue','Node.js','Django','Flask',
              'PostgreSQL','MySQL','MongoDB','AWS','Docker','Kubernetes','CI/CD','Git',
              'REST API','GraphQL','ML','TensorFlow','PyTorch','SQL','Tableau','Terraform',
              'Linux','Java','Go','R','Redis','Kafka','Elasticsearch']

def ai_screen(text, job_skills):
    t = text.lower()
    matched = [s for s in job_skills if s.lower() in t]
    missing  = [s for s in job_skills if s.lower() not in t]
    base     = (len(matched) / max(len(job_skills),1)) * 100
    bonus    = (sum(5 for kw in ['senior','lead','architect','principal'] if kw in t) +
                sum(4 for kw in ['phd','master','mit','stanford','carnegie'] if kw in t) +
                sum(3 for kw in ['certified','aws certified','azure','pmp'] if kw in t))
    score    = min(int(base + bonus), 99)
    skills   = [s for s in ALL_SKILLS if s.lower() in t]
    yrs      = re.search(r'(\d+)\+?\s*year', t)
    years    = int(yrs.group(1)) if yrs else 0
    email_m  = re.search(r'[\w.+-]+@[\w-]+\.\w+', text)
    lines    = [l.strip() for l in text.split('\n') if l.strip()]
    name     = lines[0][:40] if lines else "Unknown"
    status   = "Shortlisted" if score>=85 else ("Under Review" if score>=70 else "Rejected")

    insights = []
    insights.append(f"{'✅' if len(matched)==len(job_skills) else '🔶'} {len(matched)}/{len(job_skills)} required skills matched")
    if missing: insights.append(f"❌ Missing: {', '.join(missing[:4])}")
    insights.append(f"{'✅' if years>=5 else '🔶' if years>=2 else '❌'} ~{years} years experience detected")
    if bonus>0: insights.append("✅ Bonus signals detected (education/certs/seniority)")

    return dict(score=score, status=status, matched=matched, missing=missing,
                skills=skills, years=years, name=name,
                email=email_m.group(0) if email_m else '', insights=insights)

# ── Data Mining ───────────────────────────────────────────────────────────
def data_mining():
    skill_freq = Counter(s for c in CANDIDATES for s in c['skills'])
    top_skills = skill_freq.most_common(10)

    # Apriori-style pairs
    pairs = Counter()
    for c in CANDIDATES:
        sk = c['skills']
        for i in range(len(sk)):
            for j in range(i+1, len(sk)):
                pairs[(sk[i], sk[j])] += 1
    rules = [(f"{a} → {b}", cnt) for (a,b), cnt in pairs.most_common(6)]

    # Clusters by score
    clusters = {"Elite (90+)":[],"Strong (80-89)":[],"Moderate (70-79)":[],"Below (<70)":[]}
    for c in CANDIDATES:
        s = c['score']
        if s>=90: clusters["Elite (90+)"].append(c['name'])
        elif s>=80: clusters["Strong (80-89)"].append(c['name'])
        elif s>=70: clusters["Moderate (70-79)"].append(c['name'])
        else: clusters["Below (<70)"].append(c['name'])

    return dict(top_skills=top_skills, rules=rules, clusters=clusters,
                total=len(CANDIDATES), avg_score=int(sum(c['score'] for c in CANDIDATES)/max(len(CANDIDATES),1)))

# ── Routes ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = USERS.get(request.form['email'])
        if u and u['password'] == hashlib.sha256(request.form['password'].encode()).hexdigest():
            session.update(user=request.form['email'], user_name=u['name'],
                           company=u['company'], avatar=u['avatar'])
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        e = request.form['email']
        if e in USERS:
            flash('Email already registered', 'error')
        else:
            USERS[e] = dict(password=hashlib.sha256(request.form['password'].encode()).hexdigest(),
                            name=request.form['name'], company=request.form['company'],
                            avatar=request.form['name'][:2].upper())
            flash('Account created! Please sign in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    short = len([c for c in CANDIDATES if c['status']=='Shortlisted'])
    inter = len([c for c in CANDIDATES if c['status']=='Interview Scheduled'])
    avg   = int(sum(c['score'] for c in CANDIDATES)/max(len(CANDIDATES),1))
    return render_template('dashboard.html', total=len(CANDIDATES), shortlisted=short,
                           interviews=inter, avg_score=avg, jobs=JOBS,
                           recent=sorted(CANDIDATES, key=lambda x:x['applied'], reverse=True)[:5],
                           status_data=dict(Counter(c['status'] for c in CANDIDATES)))

@app.route('/jobs')
@login_required
def jobs(): return render_template('jobs.html', jobs=JOBS)

@app.route('/candidates')
@login_required
def candidates():
    jf = request.args.get('job',''); sf = request.args.get('status','')
    filtered = sorted([c for c in CANDIDATES if (not jf or c['job_id']==jf) and
                       (not sf or c['status']==sf)], key=lambda x:x['score'], reverse=True)
    return render_template('candidates.html', candidates=filtered, jobs=JOBS,
                           job_map={j['id']:j['title'] for j in JOBS}, jf=jf, sf=sf)

@app.route('/candidate/<cid>')
@login_required
def candidate_detail(cid):
    c = next((x for x in CANDIDATES if x['id']==cid), None)
    if not c: return redirect(url_for('candidates'))
    job = next((j for j in JOBS if j['id']==c['job_id']), None)
    return render_template('candidate_detail.html', c=c, job=job)

@app.route('/screen', methods=['GET','POST'])
@login_required
def screen():
    result = None; err = None
    if request.method == 'POST':
        job_id = request.form.get('job_id','j1')
        job    = next((j for j in JOBS if j['id']==job_id), JOBS[0])
        text   = ''
        uf = request.files.get('resume_file')
        if uf and uf.filename and allowed(uf.filename):
            p = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(uf.filename))
            uf.save(p); text = extract_text(p)
        if not text: text = request.form.get('resume_text','')
        if text.strip():
            r = ai_screen(text, job['skills'])
            r['job'] = job; r['preview'] = text[:600]
            # Auto-add to pipeline
            CANDIDATES.append({"id":f"c{uuid.uuid4().hex[:6]}","name":r['name'],
                "email":r['email'] or f"upload{len(CANDIDATES)}@auto.com","job_id":job_id,
                "score":r['score'],"experience":f"{r['years']} years","skills":r['skills'],
                "status":r['status'],"applied":datetime.now().strftime('%Y-%m-%d'),
                "education":"From upload","phone":"","location":"Unknown","from_upload":True})
            result = r
        else: err = 'Please upload a file or paste resume text.'
    return render_template('screen.html', jobs=JOBS, result=result, err=err)

@login_required

@app.route('/analytics')
@login_required
def analytics():
    skill_freq = Counter(s for c in CANDIDATES for s in c['skills'])
    score_dist = {"90-100":0,"80-89":0,"70-79":0,"<70":0}
    for c in CANDIDATES:
        s = c['score']
        if s>=90: score_dist["90-100"]+=1
        elif s>=80: score_dist["80-89"]+=1
        elif s>=70: score_dist["70-79"]+=1
        else: score_dist["<70"]+=1
    return render_template('analytics.html', candidates=CANDIDATES, jobs=JOBS,
        top_skills=skill_freq.most_common(8),
        score_dist=list(score_dist.items()),
        status_counts=list(Counter(c['status'] for c in CANDIDATES).items()))

@app.route('/data-mining')
@login_required
def data_mining_page():
    dm = data_mining()
    return render_template('data_mining.html', dm=dm,
        top_skills_json=dm['top_skills'])

@app.route('/about')
@login_required
def about(): return render_template('about.html')

@app.route('/api/update-status', methods=['POST'])
@login_required
def update_status():
    d = request.json
    for c in CANDIDATES:
        if c['id'] == d['id']:
            c['status'] = d['status']; return jsonify(ok=True)
    return jsonify(ok=False)

@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(total=len(CANDIDATES),
        shortlisted=len([c for c in CANDIDATES if c['status']=='Shortlisted']),
        interviews=len([c for c in CANDIDATES if c['status']=='Interview Scheduled']),
        avg_score=int(sum(c['score'] for c in CANDIDATES)/max(len(CANDIDATES),1)))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
