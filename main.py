from datetime import datetime
from flask import Flask,render_template, request,session,redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from flask_mail import Mail
import json 
import os
import math
from werkzeug.utils import secure_filename
import requests

with open('config.json','r' ) as c:
    params=json.load(c)["params"]
    
local_server=params['local_server']


class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)



app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['upload_folder']=params['upload_location']

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-mail'],
    MAIL_PASSWORD=params['gmail-pass']
)

mail=Mail(app)

if(local_server):
 app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
 
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']
 
db.init_app(app)


class Contacts(db.Model):
    sno: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50),nullable=False)
    phone: Mapped[str]=mapped_column(String(12),nullable=False)
    mesg: Mapped[str]=mapped_column(String(120),nullable=False)
    date: Mapped[str]=mapped_column(String(12),nullable=True)
    email:Mapped[str]=mapped_column(String(20),nullable=False)
    
    
    
class Posts(db.Model):
    sno: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(50),nullable=False)
    slug: Mapped[str]=mapped_column(String(25),nullable=False)
    content: Mapped[str]=mapped_column(String(120),nullable=False)
    date: Mapped[str]=mapped_column(String(12),nullable=True)
    img_file: Mapped[str]=mapped_column(String(25),nullable=False)
    tagline: Mapped[str]=mapped_column(String(25),nullable=False)


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)
    
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)

@app.route("/edit/<string:sno>",methods=['GET','POST'])
def edit(sno):
    if 'user' in session and session['user']==params['admin_user']:
          if( request.method=='POST'):
              box_title=request.form.get('title')
              tline=request.form.get('tline')
              slug=request.form.get('slug')
              content=request.form.get('content')
              img_file=request.form.get('img_file')
              date=datetime.now()
              if sno=='0':
                  post=Posts(title=box_title,slug=slug,content=content,img_file=img_file,tagline=tline,date=date)
                  db.session.add(post)
                  db.session.commit()
              else:
                  post=Posts.query.filter_by(sno=sno).first()
                  post.title=box_title
                  post.slug=slug
                  post.content=content
                  post.img_file=img_file
                  post.tagline=tline
                  post.date=date
                  db.session.commit()   
                  return redirect('/edit/'+sno)
                   
    post=Posts.query.filter_by(sno=sno).first()
    return render_template('edit.html',params=params,post=post,sno=sno)

@app.route("/delete/<string:sno>",methods=['GET','POST'])
def delete(sno):
    if 'user' in session and session['user']==params['admin_user']:
        post=Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')    
              
@app.route("/uploader",methods=['GET','POST'])
def uploader():
     if 'user' in session and session['user']==params['admin_user']:
         if( request.method=='POST'):
            f=request.files.get('file1')
            f.save(os.path.join(app.config['upload_folder'],secure_filename(f.filename))) 
            return "uploaded"
                     
@app.route("/logout")
def logout():
    session.pop('user')
    return  redirect('/dashboard')               
     

@app.route("/contact",methods=['GET','POST'])
def contact():
    
    
    if( request.method=='POST'):
       
       '''add to database'''
       name = request.form.get('name')
       email =request.form.get('email')
       phone= request.form.get('phone')
       message=request.form.get('message')
       
       entry=Contacts(name=name,phone=phone,mesg=message,email=email,date=datetime.now())
       db.session.add(entry)
       db.session.commit()
       mail.send_message('New message from '+name,
                         sender=email,
                         recipients=[params['gmail-mail']],
                         body=message+"\n"+phone
           
       )
 
    return render_template('contact.html',params=params)

@app.route("/about")
def about():
    return render_template('about.html',params=params)

@app.route("/dashboard",methods=['GET','POST']  )
def dashboard():
    
    
    if 'user' in session and session['user']==params['admin_user']:
        posts=Posts.query.all()
        return render_template ('dashboard.html',params=params,posts=posts)
    
    if (request.method=='POST'):
        username=request.form.get('uname')
        userpass=request.form.get('pass')
        
        if username==params['admin_user'] and userpass==params['admin_password']:
            session['user']=username
            posts=Posts.query.all()
            return render_template ('dashboard.html',params=params,posts=posts)
    
    
    return render_template('login.html',params=params)

@app.route("/post/<string:post_slug>")
def post_route(post_slug,methods=['GET']):
    post=Posts.query.filter_by(slug=post_slug).first()
    
    
    return render_template('post.html',params=params,post=post)

def fetch_tech_blogs():
    api_key = params['news_api_key']
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={api_key}"
    response = requests.get(url)
    
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        # Filter out blogs with null title, description, or content
        filtered_blogs = [blog for blog in articles if blog.get('title') and blog.get('description') and blog.get('content')]
        return filtered_blogs
    else:
        return []

    
    
@app.route("/tech-blogs")
def tech_blogs():
    blogs = fetch_tech_blogs()
    return render_template('tech_blogs.html', params=params, blogs=blogs)

@app.route("/blog/<int:blog_id>")
def blog_detail(blog_id):
    blogs = fetch_tech_blogs()
    if 0 <= blog_id < len(blogs):
        blog = blogs[blog_id]
        return render_template('blog.html', params=params, blog=blog)
    else:
        return "Blog not found", 404

app.run(debug=True)
